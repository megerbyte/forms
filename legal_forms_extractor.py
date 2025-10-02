"""
Legal Forms Placeholder Extraction System

This module extracts placeholders from legal form templates (DOCX, TXT, PDF),
canonicalizes field names using fuzzy and optional semantic similarity,
infers data types, detects option sets and paragraph choose-one groups,
and stores everything in a normalized MySQL schema with a dynamic wide table.

Features:
- DOCX parsing with italic formatting enforcement (configurable)
- TXT/PDF placeholder extraction
- Fuzzy string matching for deduplication (RapidFuzz)
- Optional semantic similarity (sentence-transformers)
- Automatic tooltip generation
- Option set detection (Yes|No|N/A, plaintiff/defendant, etc.)
- Paragraph choose-one group detection
- Dynamic ALTER TABLE for form_field_values_wide

Author: Legal Forms Extraction System
Date: 2025-10-02
"""

import os
import re
import logging
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
from pathlib import Path

# Document processing
import docx
import PyPDF2

# Database
import mysql.connector
from mysql.connector import Error as MySQLError

# Fuzzy matching
from rapidfuzz import fuzz, process

# Environment variables
from dotenv import load_dotenv

# Optional semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    SentenceTransformer = None

# Load environment variables
load_dotenv()

# Configuration
FUZZY_THRESHOLD = int(os.getenv('FUZZY_THRESHOLD', '85'))
SEMANTIC_THRESHOLD = float(os.getenv('SEMANTIC_THRESHOLD', '0.85'))
ENABLE_SEMANTICS = os.getenv('ENABLE_SEMANTICS', 'false').lower() == 'true'
SEMANTIC_MODEL_NAME = os.getenv('SEMANTIC_MODEL', 'all-MiniLM-L6-v2')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'legal_forms.log')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles database connections and operations."""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '3306'))
        self.user = os.getenv('DB_USER', 'forms_user')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'legal_forms')
        self.connection = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            logger.info("Database connection established")
            return self.connection
        except MySQLError as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")
    
    def execute_query(self, query: str, params: tuple = None):
        """Execute a query and return cursor."""
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor
        except MySQLError as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def commit(self):
        """Commit transaction."""
        if self.connection:
            self.connection.commit()


class SemanticMatcher:
    """Handles semantic similarity matching using sentence transformers."""
    
    def __init__(self):
        self.model = None
        if ENABLE_SEMANTICS and SEMANTIC_AVAILABLE:
            try:
                logger.info(f"Loading semantic model: {SEMANTIC_MODEL_NAME}")
                self.model = SentenceTransformer(SEMANTIC_MODEL_NAME)
                logger.info("Semantic model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load semantic model: {e}")
                self.model = None
    
    def is_available(self) -> bool:
        """Check if semantic matching is available."""
        return self.model is not None
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        if not self.is_available():
            return 0.0
        
        try:
            embeddings = self.model.encode([text1, text2])
            # Cosine similarity
            from numpy import dot
            from numpy.linalg import norm
            similarity = dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1]))
            return float(similarity)
        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}")
            return 0.0


class PlaceholderExtractor:
    """Extracts placeholders from legal form templates."""
    
    # Pattern for placeholders: {text inside braces}
    PLACEHOLDER_PATTERN = re.compile(r'\{([^}]+)\}')
    
    # Pattern for option sets: {option1|option2|option3} or {option1/option2}
    OPTION_PATTERN = re.compile(r'^([^|/]+(?:[|/][^|/]+)+)$')
    
    # Pattern for choose-one instructions
    CHOOSE_ONE_PATTERN = re.compile(
        r'\{.*?CHOOSE\s+(?:APPROPRIATE|ONE|ANY).*?\}',
        re.IGNORECASE
    )
    
    def __init__(self, enforce_italic_docx: bool = True):
        self.enforce_italic_docx = enforce_italic_docx
    
    def extract_from_docx(self, file_path: str) -> List[Dict]:
        """Extract placeholders from DOCX file."""
        logger.info(f"Extracting from DOCX: {file_path}")
        doc = docx.Document(file_path)
        placeholders = []
        
        for para_idx, para in enumerate(doc.paragraphs):
            text = para.text
            
            # Find all placeholders in paragraph
            for match in self.PLACEHOLDER_PATTERN.finditer(text):
                placeholder_text = match.group(1).strip()
                
                # Check if italic (if enforcement enabled)
                is_italic = self._check_italic_in_para(para, match.start(), match.end())
                
                if self.enforce_italic_docx and not is_italic:
                    logger.debug(f"Skipping non-italic placeholder: {{{placeholder_text}}}")
                    continue
                
                placeholders.append({
                    'text': placeholder_text,
                    'paragraph_index': para_idx,
                    'is_italic': is_italic,
                    'source_file': os.path.basename(file_path)
                })
        
        logger.info(f"Extracted {len(placeholders)} placeholders from DOCX")
        return placeholders
    
    def _check_italic_in_para(self, para, start: int, end: int) -> bool:
        """Check if text range in paragraph is italic."""
        # Check each run in the paragraph
        current_pos = 0
        for run in para.runs:
            run_len = len(run.text)
            run_end = current_pos + run_len
            
            # Check if this run overlaps with the placeholder
            if current_pos <= start < run_end or current_pos < end <= run_end:
                if run.italic:
                    return True
            
            current_pos = run_end
        
        return False
    
    def extract_from_txt(self, file_path: str) -> List[Dict]:
        """Extract placeholders from TXT file."""
        logger.info(f"Extracting from TXT: {file_path}")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        placeholders = []
        for match in self.PLACEHOLDER_PATTERN.finditer(text):
            placeholder_text = match.group(1).strip()
            placeholders.append({
                'text': placeholder_text,
                'paragraph_index': -1,
                'is_italic': False,
                'source_file': os.path.basename(file_path)
            })
        
        logger.info(f"Extracted {len(placeholders)} placeholders from TXT")
        return placeholders
    
    def extract_from_pdf(self, file_path: str) -> List[Dict]:
        """Extract placeholders from PDF file."""
        logger.info(f"Extracting from PDF: {file_path}")
        placeholders = []
        
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    
                    for match in self.PLACEHOLDER_PATTERN.finditer(text):
                        placeholder_text = match.group(1).strip()
                        placeholders.append({
                            'text': placeholder_text,
                            'paragraph_index': page_num,
                            'is_italic': False,
                            'source_file': os.path.basename(file_path)
                        })
        except Exception as e:
            logger.error(f"Failed to extract from PDF: {e}")
        
        logger.info(f"Extracted {len(placeholders)} placeholders from PDF")
        return placeholders
    
    def extract_from_file(self, file_path: str) -> List[Dict]:
        """Extract placeholders from any supported file type."""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.docx':
            return self.extract_from_docx(file_path)
        elif ext == '.txt':
            return self.extract_from_txt(file_path)
        elif ext == '.pdf':
            return self.extract_from_pdf(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return []
    
    def detect_options(self, placeholder_text: str) -> Optional[List[str]]:
        """Detect option sets in placeholder text."""
        match = self.OPTION_PATTERN.match(placeholder_text)
        if match:
            options_str = match.group(1)
            # Split by | or /
            options = re.split(r'[|/]', options_str)
            return [opt.strip() for opt in options if opt.strip()]
        return None
    
    def detect_choose_one_groups(self, placeholders: List[Dict]) -> List[Dict]:
        """Detect paragraph choose-one groups."""
        groups = []
        
        for i, placeholder in enumerate(placeholders):
            if self.CHOOSE_ONE_PATTERN.match('{' + placeholder['text'] + '}'):
                # Found a choose-one instruction
                # Group subsequent paragraphs until we hit another instruction or significant gap
                group = {
                    'instruction': placeholder['text'],
                    'start_paragraph': placeholder['paragraph_index'],
                    'member_placeholders': []
                }
                
                # Look ahead for related placeholders
                for j in range(i + 1, min(i + 10, len(placeholders))):
                    next_ph = placeholders[j]
                    if next_ph['paragraph_index'] > placeholder['paragraph_index'] + 5:
                        break
                    group['member_placeholders'].append(next_ph['text'])
                
                groups.append(group)
        
        return groups


class FieldCanonicalizer:
    """Canonicalizes field names using fuzzy and semantic matching."""
    
    def __init__(self, db: DatabaseManager, semantic_matcher: SemanticMatcher):
        self.db = db
        self.semantic_matcher = semantic_matcher
        self.canonical_fields = self._load_canonical_fields()
    
    def _load_canonical_fields(self) -> List[str]:
        """Load existing canonical fields from database."""
        try:
            cursor = self.db.execute_query("SELECT canonical_name FROM canonical_fields")
            fields = [row['canonical_name'] for row in cursor.fetchall()]
            cursor.close()
            return fields
        except MySQLError:
            return []
    
    def canonicalize(self, field_text: str) -> str:
        """Find or create canonical name for a field."""
        # Normalize the field text
        normalized = self._normalize_field(field_text)
        
        # Check for exact match first
        if normalized in self.canonical_fields:
            return normalized
        
        # Fuzzy match against existing canonical fields
        best_match = self._find_best_match(normalized)
        
        if best_match:
            return best_match
        
        # No match found, this becomes a new canonical field
        self.canonical_fields.append(normalized)
        return normalized
    
    def _normalize_field(self, text: str) -> str:
        """Normalize field text for comparison."""
        # Convert to lowercase, remove extra whitespace
        normalized = ' '.join(text.lower().split())
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(name of |date of |amount )', '', normalized)
        return normalized
    
    def _find_best_match(self, field_text: str) -> Optional[str]:
        """Find best matching canonical field."""
        if not self.canonical_fields:
            return None
        
        # Fuzzy match
        fuzzy_result = process.extractOne(
            field_text,
            self.canonical_fields,
            scorer=fuzz.token_sort_ratio
        )
        
        if fuzzy_result and fuzzy_result[1] >= FUZZY_THRESHOLD:
            best_fuzzy = fuzzy_result[0]
            
            # If semantic matching is available, verify
            if self.semantic_matcher.is_available():
                semantic_score = self.semantic_matcher.get_similarity(field_text, best_fuzzy)
                if semantic_score >= SEMANTIC_THRESHOLD:
                    logger.debug(f"Semantic match: {field_text} -> {best_fuzzy} (score: {semantic_score:.2f})")
                    return best_fuzzy
                else:
                    logger.debug(f"Fuzzy matched but semantic rejected: {field_text} -> {best_fuzzy}")
                    return None
            else:
                # No semantic matching, accept fuzzy match
                logger.debug(f"Fuzzy match: {field_text} -> {best_fuzzy} (score: {fuzzy_result[1]})")
                return best_fuzzy
        
        return None


class DataTypeInferencer:
    """Infers data types for form fields."""
    
    TYPE_PATTERNS = {
        'date': re.compile(r'\b(date|day|month|year|time|when)\b', re.IGNORECASE),
        'number': re.compile(r'\b(number|amount|quantity|count|age|#|no\.)\b', re.IGNORECASE),
        'email': re.compile(r'\b(email|e-mail)\b', re.IGNORECASE),
        'phone': re.compile(r'\b(phone|telephone|mobile|cell)\b', re.IGNORECASE),
        'address': re.compile(r'\b(address|street|city|state|zip|county)\b', re.IGNORECASE),
        'currency': re.compile(r'\b(price|cost|fee|payment|dollar|USD|\$)\b', re.IGNORECASE),
        'boolean': re.compile(r'\b(yes|no|true|false|check|checkbox)\b', re.IGNORECASE),
    }
    
    def infer_type(self, field_text: str) -> str:
        """Infer data type from field text."""
        for data_type, pattern in self.TYPE_PATTERNS.items():
            if pattern.search(field_text):
                return data_type
        
        return 'text'  # Default type


class LegalFormsExtractor:
    """Main extraction system coordinator."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.semantic_matcher = SemanticMatcher()
        self.placeholder_extractor = PlaceholderExtractor()
        self.type_inferencer = DataTypeInferencer()
        self.canonical_fields_cache = {}
    
    def extract_from_directory(self, directory: str):
        """Extract placeholders from all supported files in directory."""
        logger.info(f"Starting extraction from directory: {directory}")
        
        try:
            self.db.connect()
            self._initialize_schema()
            
            # Process all supported files
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in ['.docx', '.txt', '.pdf']:
                    self.process_file(str(file_path))
            
            logger.info("Extraction completed successfully")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise
        finally:
            self.db.disconnect()
    
    def process_file(self, file_path: str):
        """Process a single file."""
        logger.info(f"Processing file: {file_path}")
        
        # Extract placeholders
        placeholders = self.placeholder_extractor.extract_from_file(file_path)
        
        if not placeholders:
            logger.warning(f"No placeholders found in {file_path}")
            return
        
        # Canonicalize and store
        field_canonicalizer = FieldCanonicalizer(self.db, self.semantic_matcher)
        
        for placeholder in placeholders:
            self._process_placeholder(placeholder, field_canonicalizer)
        
        self.db.commit()
    
    def _process_placeholder(self, placeholder: Dict, canonicalizer: FieldCanonicalizer):
        """Process a single placeholder."""
        field_text = placeholder['text']
        
        # Check for options
        options = self.placeholder_extractor.detect_options(field_text)
        
        # Canonicalize
        canonical_name = canonicalizer.canonicalize(field_text)
        
        # Infer type
        data_type = self.type_inferencer.infer_type(field_text)
        
        # Store in database
        self._store_field(canonical_name, field_text, data_type, options, placeholder)
    
    def _store_field(self, canonical_name: str, original_text: str, 
                     data_type: str, options: Optional[List[str]], placeholder: Dict):
        """Store field information in database."""
        # Store canonical field if not exists
        if canonical_name not in self.canonical_fields_cache:
            cursor = self.db.execute_query(
                """INSERT IGNORE INTO canonical_fields 
                   (canonical_name, data_type, tooltip, created_at) 
                   VALUES (%s, %s, %s, %s)""",
                (canonical_name, data_type, self._generate_tooltip(canonical_name), datetime.now())
            )
            cursor.close()
            self.canonical_fields_cache[canonical_name] = True
            
            # Add column to wide table
            self._add_column_to_wide_table(canonical_name, data_type)
        
        # Store synonym
        cursor = self.db.execute_query(
            """INSERT IGNORE INTO field_synonyms 
               (original_text, canonical_name, source_file, created_at) 
               VALUES (%s, %s, %s, %s)""",
            (original_text, canonical_name, placeholder['source_file'], datetime.now())
        )
        cursor.close()
        
        # Store options if any
        if options:
            for option in options:
                cursor = self.db.execute_query(
                    """INSERT IGNORE INTO field_options 
                       (canonical_name, option_value, display_order) 
                       VALUES (%s, %s, %s)""",
                    (canonical_name, option, options.index(option))
                )
                cursor.close()
    
    def _generate_tooltip(self, canonical_name: str) -> str:
        """Generate automatic tooltip for field."""
        words = canonical_name.split()
        return f"Enter the {' '.join(words)}"
    
    def _add_column_to_wide_table(self, canonical_name: str, data_type: str):
        """Dynamically add column to wide table."""
        # Map data types to SQL types
        sql_type_map = {
            'text': 'TEXT',
            'date': 'DATE',
            'number': 'INT',
            'email': 'VARCHAR(255)',
            'phone': 'VARCHAR(50)',
            'address': 'TEXT',
            'currency': 'DECIMAL(15,2)',
            'boolean': 'BOOLEAN',
        }
        
        sql_type = sql_type_map.get(data_type, 'TEXT')
        column_name = re.sub(r'[^a-z0-9_]', '_', canonical_name.lower())
        
        try:
            alter_query = f"ALTER TABLE form_field_values_wide ADD COLUMN `{column_name}` {sql_type}"
            cursor = self.db.execute_query(alter_query)
            cursor.close()
            logger.info(f"Added column to wide table: {column_name}")
        except MySQLError as e:
            if "Duplicate column" in str(e):
                logger.debug(f"Column already exists: {column_name}")
            else:
                logger.error(f"Failed to add column: {e}")
    
    def _initialize_schema(self):
        """Initialize database schema if not exists."""
        schema_queries = [
            """CREATE TABLE IF NOT EXISTS canonical_fields (
                id INT AUTO_INCREMENT PRIMARY KEY,
                canonical_name VARCHAR(255) UNIQUE NOT NULL,
                data_type VARCHAR(50) DEFAULT 'text',
                tooltip TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_canonical_name (canonical_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            
            """CREATE TABLE IF NOT EXISTS field_synonyms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                original_text VARCHAR(255) NOT NULL,
                canonical_name VARCHAR(255) NOT NULL,
                source_file VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (canonical_name) REFERENCES canonical_fields(canonical_name) ON DELETE CASCADE,
                INDEX idx_canonical_name (canonical_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            
            """CREATE TABLE IF NOT EXISTS field_options (
                id INT AUTO_INCREMENT PRIMARY KEY,
                canonical_name VARCHAR(255) NOT NULL,
                option_value VARCHAR(255) NOT NULL,
                display_order INT DEFAULT 0,
                FOREIGN KEY (canonical_name) REFERENCES canonical_fields(canonical_name) ON DELETE CASCADE,
                INDEX idx_canonical_name (canonical_name),
                UNIQUE KEY unique_option (canonical_name, option_value)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            
            """CREATE TABLE IF NOT EXISTS paragraph_groups (
                id INT AUTO_INCREMENT PRIMARY KEY,
                instruction_text TEXT,
                source_file VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            
            """CREATE TABLE IF NOT EXISTS form_field_values_wide (
                id INT AUTO_INCREMENT PRIMARY KEY,
                form_id VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_form_id (form_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
        ]
        
        for query in schema_queries:
            try:
                cursor = self.db.execute_query(query)
                cursor.close()
            except MySQLError as e:
                logger.error(f"Schema initialization failed: {e}")


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python legal_forms_extractor.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    extractor = LegalFormsExtractor()
    extractor.extract_from_directory(directory)


if __name__ == '__main__':
    main()

# Legal Forms Placeholder Extraction System

Comprehensive documentation for the Legal Form Placeholder Extraction System and supporting infrastructure.

## Table of Contents

1. [Overview](#overview)
2. [Components](#components)
3. [Environment Setup](#environment-setup)
4. [Database Schema](#database-schema)
5. [Extraction Rules](#extraction-rules)
6. [Usage](#usage)
7. [Admin UI](#admin-ui)
8. [Troubleshooting](#troubleshooting)
9. [Roadmap](#roadmap)

## Overview

The Legal Forms Placeholder Extraction System is a comprehensive solution for extracting, normalizing, and managing form fields from legal document templates. It supports DOCX, TXT, and PDF formats, and includes advanced features like fuzzy matching, optional semantic similarity, option set detection, and dynamic database schema management.

### Key Features

- **Multi-format Support**: Extract placeholders from DOCX, TXT, and PDF files
- **Italic Enforcement**: Optional enforcement of italic formatting for DOCX placeholders
- **Smart Deduplication**: Fuzzy string matching (RapidFuzz) with optional semantic similarity (sentence-transformers)
- **Automatic Type Inference**: Detects field types (text, date, number, email, phone, address, currency, boolean)
- **Option Set Detection**: Identifies choice fields like {Yes|No|N/A} or {plaintiff/defendant}
- **Paragraph Groups**: Detects "choose one" paragraph groups
- **Dynamic Schema**: Automatically adds columns to wide table for new fields
- **Admin Interface**: Flask-based UI for field management
- **Case Law Integration**: Optional case crawler for building citation graphs

## Components

### Core Modules

1. **legal_forms_extractor.py** - Main extraction engine
   - Placeholder extraction from documents
   - Field canonicalization
   - Type inference
   - Database storage

2. **citation_patterns.py** - Legal citation utilities
   - Regex patterns for Southwestern, Federal, and U.S. Reports
   - Citation context extraction
   - Treatment signal detection

3. **case_crawler.py** - Case law ingestion
   - CourtListener API integration
   - Citation graph construction
   - Texas/5th Circuit priority

4. **admin_app.py** - Flask admin interface
   - Field management
   - Tooltip editing
   - Synonym viewing
   - Option list management

### Configuration Files

- **.env.example** - Environment variable template
- **requirements.txt** - Full dependencies (with semantic matching)
- **requirements-lite.txt** - Minimal dependencies (fuzzy only)

### Documentation

- **README_LEGAL_FORMS.md** - This file
- **CASE_CRAWLER_README.md** - Case crawler documentation
- **forms/README_PLACEHOLDER.txt** - Form template guidance

### Database Migrations

- **migrations/20251002_add_cases_tables.sql** - Case law schema

## Environment Setup

### Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd forms
   ```

2. **Choose dependency set**
   
   For full semantic matching support:
   ```bash
   pip install -r requirements.txt
   ```
   
   For lightweight fuzzy-only matching:
   ```bash
   pip install -r requirements-lite.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Set up database**
   ```sql
   CREATE DATABASE legal_forms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'forms_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON legal_forms.* TO 'forms_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. **Run migrations** (optional, for case law features)
   ```bash
   mysql -u forms_user -p legal_forms < migrations/20251002_add_cases_tables.sql
   ```

### Environment Variables

Key variables in `.env`:

```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=forms_user
DB_PASSWORD=your_password
DB_NAME=legal_forms

# Semantic Matching (optional)
ENABLE_SEMANTICS=false  # Set to 'true' to enable
SEMANTIC_MODEL=all-MiniLM-L6-v2

# Field Matching Thresholds
FUZZY_THRESHOLD=85      # 0-100
SEMANTIC_THRESHOLD=0.85 # 0.0-1.0

# Flask Admin
FLASK_SECRET_KEY=your_random_secret_key
FLASK_PORT=5000
FLASK_DEBUG=False

# CourtListener (for case crawler)
COURTLISTENER_API_KEY=your_api_key
COURTLISTENER_USER_AGENT=LegalFormsExtractor/1.0 (your-email@example.com)
```

## Database Schema

### Core Tables

#### canonical_fields
Stores deduplicated canonical field names.

```sql
- id (INT, PK, AUTO_INCREMENT)
- canonical_name (VARCHAR(255), UNIQUE)
- data_type (VARCHAR(50)) - text, date, number, email, phone, address, currency, boolean
- tooltip (TEXT)
- created_at (TIMESTAMP)
```

#### field_synonyms
Maps original placeholder text to canonical fields.

```sql
- id (INT, PK)
- original_text (VARCHAR(255))
- canonical_name (VARCHAR(255), FK)
- source_file (VARCHAR(255))
- created_at (TIMESTAMP)
```

#### field_options
Stores option sets for choice fields.

```sql
- id (INT, PK)
- canonical_name (VARCHAR(255), FK)
- option_value (VARCHAR(255))
- display_order (INT)
```

#### paragraph_groups
Stores "choose one" paragraph groupings.

```sql
- id (INT, PK)
- instruction_text (TEXT)
- source_file (VARCHAR(255))
- created_at (TIMESTAMP)
```

#### form_field_values_wide
Dynamic wide table for form data. Columns are added automatically as new canonical fields are discovered.

```sql
- id (INT, PK)
- form_id (VARCHAR(100))
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- [dynamic columns for each canonical field]
```

### Case Law Tables

See `migrations/20251002_add_cases_tables.sql` and `CASE_CRAWLER_README.md` for details.

## Extraction Rules

### Placeholder Format

Placeholders must be enclosed in curly braces: `{placeholder text}`

### DOCX-Specific Rules

1. **Italic Enforcement** (default: enabled)
   - Only italic text in braces is recognized
   - Configure via `enforce_italic_docx` parameter
   
2. **Example Valid Placeholders**
   ```
   {name of plaintiff}
   {date of incident}
   {amount in controversy}
   ```

3. **Example Invalid (if italic enforcement enabled)**
   ```
   {non-italic text} - will be skipped
   ```

### Option Set Detection

The system automatically detects option sets using these patterns:

1. **Pipe separator**: `{option1|option2|option3}`
   - Example: `{Yes|No|N/A}`
   
2. **Slash separator**: `{option1/option2}`
   - Example: `{plaintiff/defendant}`

Detected options are stored in `field_options` table.

### Paragraph Choose-One Groups

The system detects instructions like:
- `{CHOOSE APPROPRIATE PARAGRAPH 5}`
- `{CHOOSE ONE OF THE FOLLOWING}`

Subsequent paragraphs are grouped together for guided form filling.

### Field Canonicalization

1. **Normalization**
   - Convert to lowercase
   - Remove extra whitespace
   - Strip common prefixes (e.g., "name of ", "date of ")

2. **Fuzzy Matching**
   - Uses RapidFuzz token_sort_ratio
   - Threshold configurable (default: 85)
   - Matches similar variations: "plaintiff name" ≈ "name of plaintiff"

3. **Semantic Matching** (optional)
   - Requires sentence-transformers
   - Uses cosine similarity of embeddings
   - Threshold configurable (default: 0.85)
   - Validates fuzzy matches semantically

### Type Inference

The system infers data types based on field text patterns:

| Type     | Keywords                                   |
|----------|-------------------------------------------|
| date     | date, day, month, year, time, when        |
| number   | number, amount, quantity, count, age, #   |
| email    | email, e-mail                             |
| phone    | phone, telephone, mobile, cell            |
| address  | address, street, city, state, zip, county |
| currency | price, cost, fee, payment, dollar, USD, $ |
| boolean  | yes, no, true, false, check, checkbox     |
| text     | (default for all others)                  |

## Usage

### Extracting Placeholders

```bash
python legal_forms_extractor.py /path/to/forms/directory
```

This will:
1. Scan all DOCX, TXT, and PDF files in the directory
2. Extract placeholders according to the rules
3. Canonicalize field names
4. Store results in the database
5. Add columns to the wide table

### Running the Admin UI

```bash
python admin_app.py
```

Then open http://localhost:5000 in your browser.

### Crawling Case Law

```bash
# Crawl Texas cases (default)
python case_crawler.py Texas 50

# Crawl 5th Circuit cases
python case_crawler.py "5th Circuit" 30

# Crawl Supreme Court cases
python case_crawler.py "Supreme Court" 20
```

## Admin UI

### Features

1. **Dashboard**
   - System statistics
   - Quick actions
   - System configuration display

2. **Fields Page**
   - List all canonical fields
   - View data types and tooltips
   - See synonym and option counts
   - Edit field properties

3. **Field Edit Page**
   - Update data type
   - Edit tooltip text
   - View all synonyms
   - View all options

4. **Synonyms Page**
   - Browse all field synonyms
   - See source files
   - Link to canonical fields

5. **Options Page**
   - View all option sets
   - Grouped by field

### API Endpoints

- `GET /api/fields` - List all fields (JSON)
- `GET /api/fields/<name>/options` - Get field options (JSON)

### Security Note

⚠️ **WARNING**: The admin UI is intentionally minimal and **unauthenticated** for internal development use only.

For production deployment, implement:
- Authentication/authorization
- HTTPS/TLS encryption
- CSRF protection
- Input validation and sanitization
- Rate limiting
- Audit logging

## Troubleshooting

### Semantic Model Issues

If semantic matching fails to load:

1. Check `ENABLE_SEMANTICS` is set to `true` in `.env`
2. Verify `sentence-transformers` is installed:
   ```bash
   pip install sentence-transformers
   ```
3. Check model download location (default: `~/.cache/torch/sentence_transformers/`)
4. Ensure sufficient disk space for model files (~80-500MB depending on model)

**Fallback**: Set `ENABLE_SEMANTICS=false` to use fuzzy matching only.

### Database Connection Errors

1. Verify MySQL is running:
   ```bash
   sudo systemctl status mysql
   ```

2. Test connection:
   ```bash
   mysql -u forms_user -p -h localhost legal_forms
   ```

3. Check credentials in `.env`

4. Verify user permissions:
   ```sql
   SHOW GRANTS FOR 'forms_user'@'localhost';
   ```

### No Placeholders Extracted

1. **DOCX files**: Check italic formatting
   - Solution: Set `enforce_italic_docx=False` or format placeholders as italic

2. **PDF files**: Text extraction may fail for scanned documents
   - Solution: Use OCR or convert to DOCX

3. **Placeholder format**: Ensure curly braces are used correctly

### Wide Table ALTER Errors

If column addition fails:

1. Check for MySQL reserved words
2. Verify column name generation (alphanumeric + underscore only)
3. Check for duplicate column names
4. Review MySQL error logs

## Roadmap

### Completed (This PR)

- ✅ Placeholder extraction (DOCX, TXT, PDF)
- ✅ Fuzzy + optional semantic matching
- ✅ Type inference
- ✅ Option set detection
- ✅ Paragraph group detection
- ✅ Dynamic wide table
- ✅ Admin UI
- ✅ Case crawler (CourtListener)
- ✅ Citation graph
- ✅ Treatment inference

### Future Enhancements

1. **Questionnaire Flow Engine**
   - Conditional logic
   - Field dependencies
   - Progress tracking
   - Validation rules

2. **Enhanced Case Resolution**
   - Search API fallback
   - Reporter normalization
   - Parallel citation handling
   - Shepardizing integration

3. **Texas-Specific Scraper**
   - HTML opinion parsing
   - robots.txt compliance
   - Rate limiting
   - ToS adherence

4. **UI Improvements**
   - Case browser
   - Field-to-case linking interface
   - Citation graph visualization
   - Field usage analytics

5. **Production Hardening**
   - Authentication system
   - HTTPS/TLS setup
   - CSRF protection
   - Input validation
   - Rate limiting
   - Audit logging

6. **API Enhancements**
   - RESTful API for all operations
   - Field search endpoint
   - Bulk import/export
   - Webhook support

## Support

For issues, questions, or contributions, please refer to the project's issue tracker.

## License

[Specify license here]

## Acknowledgments

- RapidFuzz for fuzzy string matching
- sentence-transformers for semantic similarity
- CourtListener for case law data
- Flask for admin UI framework

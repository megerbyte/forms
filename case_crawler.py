"""
Case Law Crawler and Citation Graph Builder

This module provides on-demand case law ingestion from CourtListener API,
with priority for Texas state courts and 5th Circuit. It extracts citations
from case text, builds the citation graph, and performs naive treatment
inference from context.

Features:
- CourtListener API integration
- Texas priority crawling
- Citation extraction using citation_patterns module
- Citation graph construction
- Naive treatment inference
- Unresolved citation tracking

Author: Legal Forms Extraction System
Date: 2025-10-02
"""

import os
import re
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

# Local imports
from citation_patterns import (
    extract_citations_with_treatment,
    parse_citation_string,
    build_citation_string,
    is_valid_citation
)

# Database
import mysql.connector
from mysql.connector import Error as MySQLError

# Environment variables
from dotenv import load_dotenv

load_dotenv()

# Configuration
COURTLISTENER_API_KEY = os.getenv('COURTLISTENER_API_KEY', '')
COURTLISTENER_USER_AGENT = os.getenv('COURTLISTENER_USER_AGENT', 'LegalFormsExtractor/1.0')
CRAWLER_MAX_RETRIES = int(os.getenv('CRAWLER_MAX_RETRIES', '3'))
CRAWLER_RETRY_DELAY = int(os.getenv('CRAWLER_RETRY_DELAY', '5'))
CRAWLER_REQUEST_TIMEOUT = int(os.getenv('CRAWLER_REQUEST_TIMEOUT', '30'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles database connections for case crawler."""
    
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


class CourtListenerClient:
    """Client for CourtListener API."""
    
    BASE_URL = "https://www.courtlistener.com/api/rest/v3"
    
    def __init__(self, api_key: str = None, user_agent: str = None):
        self.api_key = api_key or COURTLISTENER_API_KEY
        self.user_agent = user_agent or COURTLISTENER_USER_AGENT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Authorization': f'Token {self.api_key}' if self.api_key else ''
        })
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        """Make API request with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}/"
        
        for attempt in range(CRAWLER_MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=CRAWLER_REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < CRAWLER_MAX_RETRIES - 1:
                    time.sleep(CRAWLER_RETRY_DELAY)
                else:
                    logger.error(f"Request failed after {CRAWLER_MAX_RETRIES} attempts")
                    return None
    
    def search_opinions(self, query: str, court: str = None, 
                       jurisdiction: str = None, limit: int = 20) -> List[Dict]:
        """Search for opinions."""
        params = {
            'q': query,
            'order_by': 'dateFiled',
            'stat_Precedential': 'Published',
            'type': 'o',
            'page_size': limit
        }
        
        if court:
            params['court'] = court
        
        logger.info(f"Searching opinions: query={query}, court={court}, jurisdiction={jurisdiction}")
        
        result = self._make_request('search', params)
        if result and 'results' in result:
            return result['results']
        return []
    
    def get_opinion(self, opinion_id: int) -> Optional[Dict]:
        """Get specific opinion by ID."""
        logger.info(f"Fetching opinion: {opinion_id}")
        return self._make_request(f'opinions/{opinion_id}')
    
    def get_cluster(self, cluster_id: int) -> Optional[Dict]:
        """Get opinion cluster (case) by ID."""
        logger.info(f"Fetching cluster: {cluster_id}")
        return self._make_request(f'clusters/{cluster_id}')


class CaseCrawler:
    """Main case crawler with citation graph building."""
    
    JURISDICTION_PRIORITY = {
        'Texas': 100,
        '5th Circuit': 90,
        'Supreme Court': 85,
    }
    
    def __init__(self):
        self.db = DatabaseManager()
        self.cl_client = CourtListenerClient()
        self.citation_cache = {}
    
    def crawl_by_jurisdiction(self, jurisdiction: str, limit: int = 50):
        """Crawl cases for a specific jurisdiction."""
        logger.info(f"Starting crawl for jurisdiction: {jurisdiction}")
        
        try:
            self.db.connect()
            
            # Get court codes for jurisdiction
            courts = self._get_courts_for_jurisdiction(jurisdiction)
            
            for court in courts:
                logger.info(f"Crawling court: {court}")
                self._crawl_court(court, jurisdiction, limit)
            
            logger.info(f"Completed crawl for jurisdiction: {jurisdiction}")
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            raise
        finally:
            self.db.disconnect()
    
    def _get_courts_for_jurisdiction(self, jurisdiction: str) -> List[str]:
        """Get court codes for jurisdiction."""
        # Mapping of jurisdictions to court codes
        court_map = {
            'Texas': ['tex', 'texapp', 'texcrimapp', 'texag', 'texreview'],
            '5th Circuit': ['ca5'],
            'Supreme Court': ['scotus'],
            '1st Circuit': ['ca1'],
            '2nd Circuit': ['ca2'],
            '3rd Circuit': ['ca3'],
            '4th Circuit': ['ca4'],
            '6th Circuit': ['ca6'],
            '7th Circuit': ['ca7'],
            '8th Circuit': ['ca8'],
            '9th Circuit': ['ca9'],
            '10th Circuit': ['ca10'],
            '11th Circuit': ['ca11'],
            'DC Circuit': ['cadc'],
            'Federal Circuit': ['cafc'],
        }
        
        return court_map.get(jurisdiction, [])
    
    def _crawl_court(self, court: str, jurisdiction: str, limit: int):
        """Crawl cases from a specific court."""
        # Search for recent opinions
        opinions = self.cl_client.search_opinions(
            query='*',  # All cases
            court=court,
            limit=limit
        )
        
        for opinion_data in opinions:
            try:
                self._process_opinion(opinion_data, jurisdiction)
            except Exception as e:
                logger.error(f"Failed to process opinion: {e}")
                continue
    
    def _process_opinion(self, opinion_data: Dict, jurisdiction: str):
        """Process a single opinion."""
        # Extract case information
        case_name = opinion_data.get('caseName', 'Unknown')
        citation = opinion_data.get('citation', '')
        court = opinion_data.get('court', '')
        decision_date = opinion_data.get('dateFiled')
        docket_number = opinion_data.get('docketNumber', '')
        
        # Get full text
        plain_text = opinion_data.get('plain_text', '')
        html_content = opinion_data.get('html', '')
        
        # Extract text from HTML if plain text not available
        if not plain_text and html_content:
            plain_text = self._extract_text_from_html(html_content)
        
        if not plain_text:
            logger.warning(f"No text available for case: {case_name}")
            return
        
        # Store case
        case_id = self._store_case(
            case_name=case_name,
            citation=citation,
            court=court,
            jurisdiction=jurisdiction,
            decision_date=decision_date,
            docket_number=docket_number,
            full_text=plain_text,
            url=opinion_data.get('absolute_url', '')
        )
        
        if case_id:
            # Extract and store citations
            self._extract_and_store_citations(case_id, plain_text)
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    
    def _store_case(self, case_name: str, citation: str, court: str,
                    jurisdiction: str, decision_date: str, docket_number: str,
                    full_text: str, url: str) -> Optional[int]:
        """Store case in database."""
        try:
            # Check if case already exists
            cursor = self.db.execute_query(
                "SELECT id FROM cases WHERE citation = %s AND court = %s",
                (citation, court)
            )
            existing = cursor.fetchone()
            cursor.close()
            
            if existing:
                logger.info(f"Case already exists: {citation}")
                return existing['id']
            
            # Parse decision date
            parsed_date = None
            if decision_date:
                try:
                    parsed_date = datetime.fromisoformat(decision_date.replace('Z', '+00:00')).date()
                except:
                    pass
            
            # Insert new case
            cursor = self.db.execute_query(
                """INSERT INTO cases 
                   (case_name, citation, court, jurisdiction, decision_date, 
                    docket_number, full_text, url, source, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (case_name, citation, court, jurisdiction, parsed_date,
                 docket_number, full_text, url, 'courtlistener', datetime.now())
            )
            
            case_id = cursor.lastrowid
            cursor.close()
            self.db.commit()
            
            logger.info(f"Stored case: {case_name} ({citation}) with ID {case_id}")
            return case_id
            
        except MySQLError as e:
            logger.error(f"Failed to store case: {e}")
            return None
    
    def _extract_and_store_citations(self, citing_case_id: int, text: str):
        """Extract citations from text and store citation relationships."""
        citations = extract_citations_with_treatment(text)
        
        logger.info(f"Extracted {len(citations)} citations from case {citing_case_id}")
        
        for citation in citations:
            # Try to resolve citation to a case in database
            cited_case_id = self._resolve_citation(citation)
            
            if cited_case_id:
                # Store citation relationship
                self._store_citation_relationship(
                    citing_case_id,
                    cited_case_id,
                    citation['full_citation'],
                    citation['full_context'],
                    citation['treatment']
                )
            else:
                # Store as unresolved
                self._store_unresolved_citation(
                    citing_case_id,
                    citation
                )
    
    def _resolve_citation(self, citation: Dict) -> Optional[int]:
        """Try to resolve citation to a case in database."""
        citation_str = citation['full_citation']
        
        # Check cache first
        if citation_str in self.citation_cache:
            return self.citation_cache[citation_str]
        
        # Search database
        try:
            cursor = self.db.execute_query(
                "SELECT id FROM cases WHERE citation = %s LIMIT 1",
                (citation_str,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                case_id = result['id']
                self.citation_cache[citation_str] = case_id
                return case_id
        except MySQLError as e:
            logger.error(f"Citation resolution failed: {e}")
        
        return None
    
    def _store_citation_relationship(self, citing_case_id: int, cited_case_id: int,
                                    citation_text: str, context: str, treatment: str):
        """Store citation relationship."""
        try:
            cursor = self.db.execute_query(
                """INSERT INTO case_citations 
                   (citing_case_id, cited_case_id, citation_text, context_text, 
                    treatment, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (citing_case_id, cited_case_id, citation_text, context, 
                 treatment, datetime.now())
            )
            cursor.close()
            self.db.commit()
            
            logger.debug(f"Stored citation: {citing_case_id} -> {cited_case_id} ({treatment})")
        except MySQLError as e:
            logger.error(f"Failed to store citation relationship: {e}")
    
    def _store_unresolved_citation(self, citing_case_id: int, citation: Dict):
        """Store unresolved citation."""
        try:
            cursor = self.db.execute_query(
                """INSERT INTO unresolved_citations 
                   (citing_case_id, citation_text, context_text, reporter, 
                    volume, page, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (citing_case_id, citation['full_citation'], citation['full_context'],
                 citation['reporter'], citation['volume'], citation['page'],
                 datetime.now())
            )
            cursor.close()
            self.db.commit()
            
            logger.debug(f"Stored unresolved citation: {citation['full_citation']}")
        except MySQLError as e:
            logger.error(f"Failed to store unresolved citation: {e}")
    
    def resolve_unresolved_citations(self):
        """Attempt to resolve previously unresolved citations."""
        logger.info("Resolving unresolved citations...")
        
        try:
            self.db.connect()
            
            # Get all unresolved citations
            cursor = self.db.execute_query(
                "SELECT * FROM unresolved_citations WHERE resolution_attempted_at IS NULL"
            )
            unresolved = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Found {len(unresolved)} unresolved citations")
            
            for citation_record in unresolved:
                citation_text = citation_record['citation_text']
                
                # Try to resolve
                citation = parse_citation_string(citation_text)
                if citation:
                    cited_case_id = self._resolve_citation(citation)
                    
                    if cited_case_id:
                        # Move to case_citations
                        self._store_citation_relationship(
                            citation_record['citing_case_id'],
                            cited_case_id,
                            citation_text,
                            citation_record['context_text'],
                            'neutral'  # Default treatment for resolved citations
                        )
                        
                        # Delete from unresolved
                        cursor = self.db.execute_query(
                            "DELETE FROM unresolved_citations WHERE id = %s",
                            (citation_record['id'],)
                        )
                        cursor.close()
                        
                        logger.info(f"Resolved citation: {citation_text}")
                
                # Mark as attempted
                cursor = self.db.execute_query(
                    "UPDATE unresolved_citations SET resolution_attempted_at = %s WHERE id = %s",
                    (datetime.now(), citation_record['id'])
                )
                cursor.close()
            
            self.db.commit()
            logger.info("Unresolved citation resolution completed")
            
        except Exception as e:
            logger.error(f"Citation resolution failed: {e}")
        finally:
            self.db.disconnect()


def main():
    """Main entry point."""
    import sys
    
    crawler = CaseCrawler()
    
    if len(sys.argv) > 1:
        jurisdiction = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        crawler.crawl_by_jurisdiction(jurisdiction, limit)
    else:
        # Default: crawl Texas cases
        logger.info("No jurisdiction specified, crawling Texas cases")
        crawler.crawl_by_jurisdiction('Texas', 50)
        
        # Resolve unresolved citations
        crawler.resolve_unresolved_citations()


if __name__ == '__main__':
    main()

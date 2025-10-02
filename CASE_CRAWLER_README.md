# Case Law Crawler Documentation

Comprehensive guide for the Legal Forms Case Law Crawler and Citation Graph Builder.

## Overview

The Case Law Crawler provides on-demand ingestion of case law opinions from CourtListener, with priority handling for Texas state courts and the 5th Circuit. It builds a citation graph by extracting citations from case text and performs naive treatment inference based on context.

## Features

- **CourtListener Integration**: Direct API access to case law database
- **Jurisdiction Priority**: Configurable priority levels (Texas > 5th Circuit > Other)
- **Citation Extraction**: Automatic identification of legal citations in text
- **Citation Graph**: Builds relationships between citing and cited cases
- **Treatment Inference**: Naive detection of how cases treat prior cases
- **Unresolved Citations**: Tracks citations that couldn't be matched to database cases
- **Batch Processing**: Efficient crawling of multiple jurisdictions

## Architecture

### Components

1. **CourtListenerClient** - API wrapper for CourtListener
2. **CaseCrawler** - Main crawling and processing logic
3. **citation_patterns module** - Citation extraction utilities
4. **DatabaseManager** - Database operations

### Data Flow

```
CourtListener API
       ↓
CourtListenerClient
       ↓
CaseCrawler (process opinion)
       ↓
Citation Extraction (citation_patterns)
       ↓
Citation Resolution
       ↓
Database Storage (cases, case_citations, unresolved_citations)
```

## Database Schema

### cases

Stores case law opinions.

```sql
- id (INT, PK, AUTO_INCREMENT)
- case_name (VARCHAR(500))
- citation (VARCHAR(255))
- court (VARCHAR(255))
- jurisdiction (VARCHAR(100))
- decision_date (DATE)
- docket_number (VARCHAR(255))
- full_text (LONGTEXT) - Raw opinion text (no paraphrases)
- summary (TEXT) - Optional case summary
- url (VARCHAR(500))
- source (VARCHAR(100)) - 'courtlistener', 'texas_courts', etc.
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

**Indexes**: citation, court, jurisdiction, decision_date, source

### case_citations

Citation relationships between cases.

```sql
- id (INT, PK, AUTO_INCREMENT)
- citing_case_id (INT, FK to cases.id)
- cited_case_id (INT, FK to cases.id, nullable)
- citation_text (VARCHAR(255))
- context_text (TEXT) - Surrounding text from opinion
- treatment (VARCHAR(50)) - overruled, distinguished, followed, etc.
- page_number (INT) - Optional page reference
- created_at (TIMESTAMP)
```

**Indexes**: citing_case_id, cited_case_id, treatment

### unresolved_citations

Citations that couldn't be matched to database cases.

```sql
- id (INT, PK, AUTO_INCREMENT)
- citing_case_id (INT, FK to cases.id)
- citation_text (VARCHAR(255))
- context_text (TEXT)
- reporter (VARCHAR(100))
- volume (INT)
- page (INT)
- resolution_attempted_at (TIMESTAMP, nullable)
- created_at (TIMESTAMP)
```

**Indexes**: citing_case_id, citation_text, reporter

### field_case_links

Links form fields to relevant cases (for future use).

```sql
- id (INT, PK, AUTO_INCREMENT)
- canonical_field_name (VARCHAR(255))
- case_id (INT, FK to cases.id)
- relevance_score (DECIMAL(3,2))
- notes (TEXT)
- created_by (VARCHAR(100))
- created_at (TIMESTAMP)
```

### jurisdiction_priority

Configures crawling priorities.

```sql
- id (INT, PK, AUTO_INCREMENT)
- jurisdiction_name (VARCHAR(100), UNIQUE)
- priority_level (INT) - Higher = more important
- is_active (BOOLEAN)
- notes (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

## Citation Extraction

### Supported Reporters

1. **Southwestern Reporter**
   - S.W. (original series)
   - S.W.2d (second series)
   - S.W.3d (third series)
   - Format: `123 S.W.2d 456`

2. **Federal Reporters**
   - F. (original series)
   - F.2d, F.3d, F.4th
   - Format: `789 F.3d 123`

3. **U.S. Reports**
   - U.S.
   - Format: `347 U.S. 483`

### Citation Context

The system captures text surrounding each citation (default: 200 characters before and after) to enable treatment analysis.

### Treatment Detection

Naive pattern matching identifies treatment signals:

| Treatment     | Keywords                                |
|---------------|----------------------------------------|
| overruled     | overruled, overruling                  |
| distinguished | distinguished, distinguishing          |
| followed      | followed, following, affirmed, affirming |
| questioned    | questioned, questioning, doubted       |
| criticized    | criticized, criticizing                |
| limited       | limited, limiting                      |
| explained     | explained, explaining                  |
| cited         | cited, citing                          |
| neutral       | (default if no signal detected)        |

**Note**: This is naive detection. Production systems should use more sophisticated NLP or rely on professional citator services (Shepard's, KeyCite).

## Usage

### Basic Crawling

```bash
# Crawl Texas cases (default)
python case_crawler.py Texas 50

# Crawl 5th Circuit
python case_crawler.py "5th Circuit" 30

# Crawl U.S. Supreme Court
python case_crawler.py "Supreme Court" 20
```

### Programmatic Usage

```python
from case_crawler import CaseCrawler

crawler = CaseCrawler()

# Crawl by jurisdiction
crawler.crawl_by_jurisdiction('Texas', limit=50)

# Resolve unresolved citations
crawler.resolve_unresolved_citations()
```

### CourtListener Client

```python
from case_crawler import CourtListenerClient

client = CourtListenerClient(
    api_key='your_api_key',
    user_agent='YourApp/1.0 (email@example.com)'
)

# Search opinions
results = client.search_opinions(
    query='forum non conveniens',
    court='tex',
    limit=10
)

# Get specific opinion
opinion = client.get_opinion(opinion_id=12345)

# Get cluster (case)
cluster = client.get_cluster(cluster_id=67890)
```

## Configuration

### Environment Variables

```bash
# CourtListener API
COURTLISTENER_API_KEY=your_key_here
COURTLISTENER_USER_AGENT=LegalFormsExtractor/1.0 (your-email@example.com)

# Crawler Settings
CRAWLER_MAX_RETRIES=3
CRAWLER_RETRY_DELAY=5  # seconds
CRAWLER_REQUEST_TIMEOUT=30  # seconds

# Database (same as main system)
DB_HOST=localhost
DB_PORT=3306
DB_USER=forms_user
DB_PASSWORD=your_password
DB_NAME=legal_forms
```

### Jurisdiction Mapping

The crawler maps jurisdictions to CourtListener court codes:

```python
{
    'Texas': ['tex', 'texapp', 'texcrimapp', 'texag', 'texreview'],
    '5th Circuit': ['ca5'],
    'Supreme Court': ['scotus'],
    '1st Circuit': ['ca1'],
    '2nd Circuit': ['ca2'],
    # ... etc.
}
```

To add custom mappings, edit the `_get_courts_for_jurisdiction` method in `case_crawler.py`.

## CourtListener API

### Getting an API Key

1. Create account at https://www.courtlistener.com/
2. Navigate to Profile → API Access
3. Generate a new API token
4. Add to `.env` as `COURTLISTENER_API_KEY`

### User Agent Requirements

CourtListener requires a descriptive User-Agent header:
```
LegalFormsExtractor/1.0 (your-email@example.com)
```

Set in `.env` as `COURTLISTENER_USER_AGENT`.

### Rate Limits

- Free tier: 5,000 requests/day
- Authenticated: Higher limits (check CourtListener docs)
- The crawler includes automatic retry with exponential backoff

### Terms of Service

Review CourtListener's Terms of Service: https://www.courtlistener.com/terms/

Key points:
- Attribute CourtListener as source
- Don't abuse the API
- Respect rate limits
- Use descriptive User-Agent

## Citation Graph Analysis

### Querying the Graph

```sql
-- Find all cases citing a specific case
SELECT 
    c1.case_name as citing_case,
    c2.case_name as cited_case,
    cc.treatment,
    cc.context_text
FROM case_citations cc
JOIN cases c1 ON cc.citing_case_id = c1.id
JOIN cases c2 ON cc.cited_case_id = c2.id
WHERE c2.citation = '123 S.W.2d 456';

-- Find most cited cases
SELECT 
    c.case_name,
    c.citation,
    COUNT(cc.id) as citation_count
FROM cases c
JOIN case_citations cc ON c.id = cc.cited_case_id
GROUP BY c.id
ORDER BY citation_count DESC
LIMIT 10;

-- Find overruled cases
SELECT DISTINCT
    c.case_name,
    c.citation
FROM cases c
JOIN case_citations cc ON c.id = cc.cited_case_id
WHERE cc.treatment = 'overruled';
```

### Treatment Statistics

```sql
-- Treatment distribution
SELECT 
    treatment,
    COUNT(*) as count
FROM case_citations
GROUP BY treatment
ORDER BY count DESC;
```

### Unresolved Citations

```sql
-- View unresolved citations
SELECT 
    c.case_name as citing_case,
    uc.citation_text,
    uc.reporter,
    uc.volume,
    uc.page
FROM unresolved_citations uc
JOIN cases c ON uc.citing_case_id = c.id
WHERE uc.resolution_attempted_at IS NULL;
```

## Resolution Process

When a citation cannot be matched to a case in the database, it's stored in `unresolved_citations`. The resolution process:

1. **Initial Extraction**: Citation found in text but not in database
2. **Storage**: Saved to `unresolved_citations` table
3. **Periodic Resolution**: Run `resolve_unresolved_citations()` after adding more cases
4. **Success**: If resolved, moved to `case_citations` and removed from `unresolved_citations`
5. **Failure**: Marked with `resolution_attempted_at` timestamp

### Running Resolution

```bash
python case_crawler.py
# Or programmatically:
from case_crawler import CaseCrawler
crawler = CaseCrawler()
crawler.resolve_unresolved_citations()
```

## Texas Courts (Future Enhancement)

The schema includes support for Texas-specific court scraping. This feature is **stubbed** in the current implementation and requires:

1. **robots.txt Compliance**: Check each Texas court site
2. **Terms of Service**: Review and comply with ToS
3. **HTML Parsing**: Custom parsers for each court's format
4. **Rate Limiting**: Respectful crawling delays
5. **Error Handling**: Robust handling of format changes

Example stub configuration:
```bash
TEXAS_SCRAPER_ENABLED=false
TEXAS_SCRAPER_DELAY=2  # seconds between requests
```

## Performance Considerations

### Batch Size

Adjust `limit` parameter based on:
- API rate limits
- Database capacity
- Processing time requirements

Recommended: 20-50 cases per batch

### Text Storage

Case full text is stored as `LONGTEXT` (up to 4GB per case). Monitor disk usage:

```sql
-- Check database size
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = 'legal_forms'
ORDER BY size_mb DESC;
```

### Citation Extraction Performance

- Average: 10-50 citations per case
- Processing: ~0.1-1 second per case (depends on text length)
- Regex matching is efficient for typical case sizes

## Troubleshooting

### API Connection Issues

1. **Check API key**: Verify `COURTLISTENER_API_KEY` in `.env`
2. **Test connection**:
   ```python
   from case_crawler import CourtListenerClient
   client = CourtListenerClient()
   results = client.search_opinions('test', limit=1)
   print(results)
   ```
3. **Review rate limits**: Check CourtListener account status
4. **User-Agent**: Ensure `COURTLISTENER_USER_AGENT` is set

### No Cases Found

1. **Court codes**: Verify jurisdiction to court code mapping
2. **Date ranges**: Some courts have limited historical data
3. **Query syntax**: Check CourtListener search syntax

### Citation Resolution Failures

Common reasons:
1. **Case not in database**: Run broader crawls
2. **Citation format variations**: Parallel citations, reporter changes
3. **OCR errors**: Scanned documents may have corrupted citations
4. **Unofficial reporters**: Only official reporters are supported

### Database Performance

For large datasets (10,000+ cases):

1. **Add indexes**:
   ```sql
   CREATE INDEX idx_cases_citation_court ON cases(citation, court);
   CREATE INDEX idx_citations_text ON case_citations(citation_text);
   ```

2. **Optimize queries**: Use EXPLAIN to analyze slow queries

3. **Consider partitioning**: Partition by decision_date for very large tables

## Best Practices

1. **Incremental Crawling**: Start with high-priority jurisdictions
2. **Regular Resolution**: Run `resolve_unresolved_citations()` weekly
3. **Monitor Storage**: Set up alerts for database size
4. **Respect Rate Limits**: Use delays between batches
5. **Backup Data**: Regular backups of cases table
6. **Cite Sources**: Always attribute CourtListener

## Future Enhancements

1. **Advanced Treatment Detection**: ML-based classification
2. **Parallel Citations**: Handle multiple citations for same case
3. **Reporter Normalization**: Map variations to standard format
4. **Search API Fallback**: Use CourtListener search for unresolved citations
5. **Shepardizing Integration**: Connect to commercial citator services
6. **Citation Network Visualization**: Graph database integration
7. **Relevance Scoring**: ML-based field-to-case matching

## References

- CourtListener API: https://www.courtlistener.com/api/
- CourtListener Documentation: https://www.courtlistener.com/help/api/
- Bluebook Citation Guide: https://www.legalbluebook.com/
- Federal Courts: https://www.uscourts.gov/
- Texas Courts: https://www.txcourts.gov/

## Support

For issues related to:
- CourtListener API: https://www.courtlistener.com/contact/
- This crawler: [Project issue tracker]

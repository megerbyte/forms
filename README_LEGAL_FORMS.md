# Legal Forms Field Extraction & Schema System

A comprehensive Python-based system for extracting placeholder fields from legal form templates and managing metadata in a structured MySQL database. This system supports multiple document formats (HTML, DOCX, TXT, PDF) and provides intelligent field deduplication, data type inference, and a user-friendly admin interface.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Placeholder Rules](#placeholder-rules)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Extraction](#running-the-extraction)
- [Admin UI Usage](#admin-ui-usage)
- [Database Schema](#database-schema)
- [Query Examples](#query-examples)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)
- [Disclaimer](#disclaimer)

## Overview

This system automates the extraction and management of variable fields (placeholders) from legal form templates. It creates a normalized database schema that enables:

- **Automated field detection** from multiple document formats
- **Intelligent deduplication** using fuzzy matching and optional semantic embeddings
- **Canonical naming** for consistent field identification across forms
- **Data type inference** (date, currency, email, phone, etc.)
- **Option detection** (e.g., plaintiff/defendant alternatives)
- **Paragraph group detection** ("CHOOSE ONE" style selections)
- **Dynamic wide table** for ad-hoc reporting and analysis
- **Web-based admin UI** for metadata editing

## Features

### Core Functionality
- ✅ **Multi-Format Support**: Extract from HTML, DOCX, TXT, and PDF files
- ✅ **Smart Deduplication**: Fuzzy string matching + optional semantic similarity
- ✅ **Canonical Naming**: Human-friendly field names with SQL compatibility
- ✅ **Data Type Inference**: Automatic classification (date, integer, decimal, currency, email, phone, boolean, text)
- ✅ **Option Detection**: Identifies slash-separated alternatives (e.g., `plaintiff/defendant`)
- ✅ **Paragraph Groups**: Detects "CHOOSE ONE" style enumerated options
- ✅ **Dynamic Schema**: Automatically creates columns in wide table for new fields
- ✅ **Metadata Management**: Edit tooltips, display names, and data types via admin UI

### Advanced Features
- 🔍 **Semantic Embeddings**: Optional ML-based field similarity (requires `sentence-transformers`)
- 📊 **Relational Schema**: Normalized database design with proper foreign keys
- 🌐 **Web Admin**: Flask-based interface for easy metadata management
- 🔄 **Synonym Tracking**: Maps field variations to canonical names
- 📈 **Wide Table**: SQL-friendly denormalized view for reporting

## Placeholder Rules

### HTML Forms
**Pattern**: `{<i>field description</i>}`

The system extracts text inside curly braces `{}` that is also wrapped in italic `<i>` tags.

**Examples**:
```html
{<i>plaintiff name</i>}
{<i>defendant/respondent</i>}
{<i>date</i>}
{<i>CHOOSE APPROPRIATE JURISDICTION</i>}
```

### DOCX Files
**Pattern**: `{field description}` (must be italicized)

By default, the system only extracts placeholders that are:
1. Wrapped in curly braces `{}`
2. Fully italicized in the document

**Configuration**: Set `ACCEPT_NON_ITALIC_DOCX=True` to extract all brace-wrapped text regardless of formatting.

### TXT Files
**Pattern**: `{field description}`

Simple brace-wrapped text extraction. Italics cannot be detected in plain text.

**Configuration**: Set `ACCEPT_BRACES_TXT=False` to disable TXT extraction.

### PDF Files
**Pattern**: `{field description}`

Extracts brace-wrapped text using `pdfplumber`. Note: Italic formatting is typically lost in PDF text extraction.

**Configuration**: 
- Set `ACCEPT_BRACES_PDF=False` to disable PDF extraction
- Set `PDF_STRICT_MODE=True` for more precise extraction (experimental)

**Limitation**: Scanned/image-based PDFs require OCR (see [Future Enhancements](#future-enhancements))

## System Requirements

### Required Software
- **Python**: Version 3.9 or higher
- **MySQL**: Version 5.7 or higher (8.0+ recommended)
- **Operating System**: Windows, macOS, or Linux

### Required Python Packages
All packages are listed in `requirements.txt`:
- `python-docx` - DOCX parsing
- `rapidfuzz` - Fuzzy string matching
- `mysql-connector-python` - MySQL database connector
- `python-slugify` - Canonical name generation
- `pdfplumber` - PDF text extraction
- `sentence-transformers` - Optional semantic embeddings
- `torch` - Required for sentence-transformers
- `Flask` - Admin web interface
- `python-dotenv` - Environment variable management
- `beautifulsoup4` - HTML parsing
- `lxml` - HTML/XML parser backend

## Installation

### Step 1: Install Python

**Verify Installation**:
```bash
python --version
# Should show Python 3.9 or higher
```

**If Python is not installed**:
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **macOS**: Use Homebrew: `brew install python3`
- **Linux**: Use package manager: `sudo apt install python3 python3-pip`

### Step 2: Install MySQL

**Verify Installation**:
```bash
mysql --version
# Should show MySQL version 5.7 or higher
```

**If MySQL is not installed**:
- **Windows**: Download MySQL Installer from [mysql.com](https://dev.mysql.com/downloads/installer/)
- **macOS**: Use Homebrew: `brew install mysql`
- **Linux**: `sudo apt install mysql-server`

**Start MySQL Service**:
```bash
# Windows: Start from Services panel or run
net start MySQL80

# macOS
brew services start mysql

# Linux
sudo systemctl start mysql
```

### Step 3: Create MySQL Database and User

**Connect to MySQL**:
```bash
mysql -u root -p
# Enter your root password
```

**Create Database**:
```sql
CREATE DATABASE legal_forms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Create User** (recommended for security):
```sql
CREATE USER 'legal_forms_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT CREATE, ALTER, INSERT, UPDATE, SELECT, DELETE ON legal_forms.* TO 'legal_forms_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Test Connection**:
```bash
mysql -u legal_forms_user -p legal_forms
# Enter the password you set above
# If successful, you'll see the MySQL prompt
EXIT;
```

### Step 4: Clone Repository

```bash
git clone https://github.com/megerbyte/forms.git
cd forms
```

### Step 5: Configure Environment

**Copy the example configuration**:
```bash
cp .env.example .env
```

**Edit `.env` with your settings**:
```bash
# Use your preferred text editor
nano .env
# or
vim .env
# or on Windows
notepad .env
```

**Required settings**:
```bash
DB_HOST=localhost
DB_USER=legal_forms_user
DB_PASSWORD=your_secure_password
DB_NAME=legal_forms
FORMS_DIR=./
```

### Step 6: Create Virtual Environment

**Create virtual environment**:
```bash
# Windows
python -m venv venv

# macOS/Linux
python3 -m venv venv
```

**Activate virtual environment**:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

You should see `(venv)` in your command prompt.

### Step 7: Install Python Dependencies

**Install all packages**:
```bash
pip install -r requirements.txt
```

**If torch installation fails** (especially on Windows):
```bash
# Disable semantic features
# Edit .env and set:
ENABLE_SEMANTICS=False

# Then install without torch/sentence-transformers
pip install python-docx rapidfuzz mysql-connector-python python-slugify pdfplumber Flask python-dotenv beautifulsoup4 lxml
```

### Step 8: Verify Installation

```bash
python -c "import mysql.connector; print('MySQL connector: OK')"
python -c "from docx import Document; print('python-docx: OK')"
python -c "import pdfplumber; print('pdfplumber: OK')"
python -c "from flask import Flask; print('Flask: OK')"
```

If all print "OK", you're ready to proceed!

## Configuration

### Environment Variables

All configuration is done via the `.env` file:

#### Database Settings
```bash
DB_HOST=localhost          # MySQL server hostname
DB_USER=legal_forms_user   # MySQL username
DB_PASSWORD=password       # MySQL password
DB_NAME=legal_forms        # Database name
```

#### Directory Settings
```bash
FORMS_DIR=./               # Directory containing form files
                          # Can be absolute or relative path
```

#### Feature Toggles
```bash
# Enable semantic embeddings for better deduplication (requires torch)
ENABLE_SEMANTICS=True

# Accept non-italic placeholders in DOCX files
# Default: False (only italicized placeholders)
ACCEPT_NON_ITALIC_DOCX=False

# Accept brace placeholders in TXT files
ACCEPT_BRACES_TXT=True

# Accept brace placeholders in PDF files
ACCEPT_BRACES_PDF=True

# PDF strict mode (experimental - more precise but may miss fields)
PDF_STRICT_MODE=False
```

#### Deduplication Thresholds
```bash
# Fuzzy matching threshold (0-100)
# Higher = more strict matching
FUZZY_THRESHOLD=85

# Semantic similarity threshold (0.0-1.0)
# Higher = more strict matching
SEMANTIC_THRESHOLD=0.85
```

## Running the Extraction

### Basic Usage

**Run the extraction script**:
```bash
python legal_forms_extractor.py
```

**Expected Output**:
```
============================================================
Legal Forms Field Extraction System
============================================================

=== Configuration ===
Database: legal_forms@localhost
Forms directory: ./
Semantic deduplication: Enabled
Accept non-italic DOCX: False

✓ Connected to MySQL database 'legal_forms'

=== Creating Database Schema ===
✓ Created 'forms' table
✓ Created 'fields' table
✓ Created 'synonyms' table
✓ Created 'form_fields' table
✓ Created 'field_options' table
✓ Created 'paragraph_groups' table
✓ Created 'paragraph_options' table
✓ Created 'paragraph_option_fields' table
✓ Created 'form_paragraph_groups' table
✓ Created 'form_field_values_wide' table
✓ Schema creation complete

=== Processing Forms in: ./ ===
Found 98 files to process

• Processing: Form_1B-11_Certificate_of_Conference.html
  ✓ Extracted 12 raw placeholders
  ✓ Added wide table column: plaintiff_name
  ✓ Added wide table column: defendant_name
  ✓ Stored 10 unique fields

• Processing: Form_2B-20_Jurisdiction.html
  ✓ Extracted 23 raw placeholders
  ✓ Stored 18 unique fields

...

=== Extraction Summary ===
✓ Total forms processed: 98
✓ Total unique fields: 247
✓ Total field synonyms: 1,432

✓ Extraction complete!

Next steps:
1. Run admin UI: FLASK_APP=admin_app.py flask run --port 5000
2. Review and edit field tooltips in the admin interface
3. Query the database for reporting and analysis

✓ Database connection closed
```

### Re-running Extraction

The script is **idempotent** - you can run it multiple times safely:
- Existing forms are updated (not duplicated)
- New fields are added
- Existing field metadata is preserved
- Wide table columns are added as needed

**When to re-run**:
- After adding new form templates
- After modifying existing forms
- After changing configuration (e.g., enabling non-italic extraction)

### Error Handling

The script continues processing even if individual files fail:
```
• Processing: Problem_Form.docx
  ⚠ Error extracting from DOCX: File may be corrupted
  ℹ No fields found
```

Non-fatal errors are logged but don't stop the entire extraction.

## Admin UI Usage

### Starting the Admin Interface

```bash
# Method 1: Using Flask directly
FLASK_APP=admin_app.py flask run --port 5000

# Method 2: Running as Python script
python admin_app.py
```

**Access the UI**:
Open your web browser to: http://localhost:5000

### Dashboard

The dashboard shows:
- **Statistics**: Total forms, fields, synonyms, and options
- **Recent Forms**: List of recently processed forms
- **Quick Start Guide**: Setup instructions

### Fields Section

**View all extracted fields**:
- Lists all canonical field names
- Shows data types and tooltips
- Displays synonym counts
- Searchable interface

**Edit a field**:
1. Click "Edit" next to any field
2. Modify:
   - Display name
   - Data type (text, date, integer, decimal, currency, email, phone, boolean)
   - Tooltip/help text
3. Click "Save Changes"

**View synonyms**:
- See all variations of a field name
- Track which forms use each variation

### Forms Section

**View all forms**:
- Lists all processed forms
- Shows file type and field count
- Displays last update timestamp

**View form details**:
1. Click "View" next to any form
2. See:
   - Form metadata (filename, path, type, dates)
   - All fields in the form
   - Field occurrences count
3. Click "Edit" next to any field to modify its metadata

### Stopping the Admin UI

Press `Ctrl+C` in the terminal where Flask is running.

## Database Schema

### Tables Overview

| Table | Purpose |
|-------|---------|
| `forms` | Master list of processed form files |
| `fields` | Canonical field definitions |
| `synonyms` | Field name variations |
| `form_fields` | Many-to-many relationship: forms ↔ fields |
| `field_options` | Choice values for fields (e.g., plaintiff/defendant) |
| `paragraph_groups` | "CHOOSE ONE" style option groups |
| `paragraph_options` | Individual options within a group |
| `paragraph_option_fields` | Fields within paragraph options |
| `form_paragraph_groups` | Many-to-many relationship: forms ↔ groups |
| `form_field_values_wide` | Denormalized wide table for reporting |

### Detailed Schema

#### forms
```sql
CREATE TABLE forms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_type VARCHAR(50) NOT NULL,           -- html, docx, txt, pdf
    form_title VARCHAR(512),
    extraction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_filename (filename)
);
```

#### fields
```sql
CREATE TABLE fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,     -- e.g., plaintiff_name
    display_name VARCHAR(512),                -- e.g., "Plaintiff Name"
    data_type VARCHAR(50) DEFAULT 'text',     -- text, date, integer, etc.
    tooltip TEXT,                             -- Help text for users
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_canonical (canonical_name)
);
```

#### synonyms
```sql
CREATE TABLE synonyms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    field_id INT NOT NULL,                    -- Links to fields.id
    raw_text VARCHAR(1024) NOT NULL,          -- Original placeholder text
    source_form_id INT,                       -- Links to forms.id
    FOREIGN KEY (field_id) REFERENCES fields(id) ON DELETE CASCADE,
    FOREIGN KEY (source_form_id) REFERENCES forms(id) ON DELETE SET NULL,
    UNIQUE KEY unique_synonym (field_id, raw_text(255))
);
```

#### form_fields
```sql
CREATE TABLE form_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    form_id INT NOT NULL,
    field_id INT NOT NULL,
    occurrence_count INT DEFAULT 1,           -- How many times field appears
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE,
    FOREIGN KEY (field_id) REFERENCES fields(id) ON DELETE CASCADE,
    UNIQUE KEY unique_form_field (form_id, field_id)
);
```

#### form_field_values_wide
Dynamic columns are added as new fields are discovered:
```sql
CREATE TABLE form_field_values_wide (
    id INT AUTO_INCREMENT PRIMARY KEY,
    form_id INT NOT NULL,
    -- Dynamic columns added at runtime:
    plaintiff_name TEXT,
    defendant_name TEXT,
    case_number TEXT,
    date_field TEXT,
    -- ... many more columns
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE,
    UNIQUE KEY unique_form (form_id)
);
```

## Query Examples

### List all forms with field counts
```sql
SELECT 
    f.filename,
    f.file_type,
    COUNT(ff.field_id) as field_count,
    f.last_updated
FROM forms f
LEFT JOIN form_fields ff ON f.id = ff.form_id
GROUP BY f.id
ORDER BY f.filename;
```

### Find all synonyms for a field
```sql
SELECT 
    fld.canonical_name,
    syn.raw_text,
    frm.filename
FROM fields fld
JOIN synonyms syn ON fld.id = syn.field_id
LEFT JOIN forms frm ON syn.source_form_id = frm.id
WHERE fld.canonical_name = 'plaintiff_name'
ORDER BY syn.raw_text;
```

### Fields by data type
```sql
SELECT 
    data_type,
    COUNT(*) as count
FROM fields
GROUP BY data_type
ORDER BY count DESC;
```

### Most common fields across forms
```sql
SELECT 
    f.canonical_name,
    f.display_name,
    COUNT(DISTINCT ff.form_id) as form_count
FROM fields f
JOIN form_fields ff ON f.id = ff.field_id
GROUP BY f.id
ORDER BY form_count DESC
LIMIT 20;
```

### Fields with options (alternatives)
```sql
SELECT 
    f.canonical_name,
    GROUP_CONCAT(fo.option_value SEPARATOR ', ') as options
FROM fields f
JOIN field_options fo ON f.id = fo.field_id
GROUP BY f.id
HAVING COUNT(fo.id) > 0;
```

### Wide table report (example)
```sql
SELECT 
    f.filename,
    w.plaintiff_name,
    w.defendant_name,
    w.case_number,
    w.date_field
FROM form_field_values_wide w
JOIN forms f ON w.form_id = f.id
WHERE w.plaintiff_name IS NOT NULL;
```

## Troubleshooting

### MySQL Connection Errors

**Error**: `Access denied for user 'legal_forms_user'@'localhost'`

**Solutions**:
1. Verify credentials in `.env` file
2. Check user exists and has correct permissions:
   ```sql
   SELECT user, host FROM mysql.user WHERE user = 'legal_forms_user';
   ```
3. Ensure user has permission from 'localhost':
   ```sql
   GRANT ALL ON legal_forms.* TO 'legal_forms_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

**Error**: `Can't connect to MySQL server on 'localhost'`

**Solutions**:
1. Ensure MySQL service is running:
   ```bash
   # Linux
   sudo systemctl status mysql
   
   # macOS
   brew services list
   
   # Windows
   services.msc (look for MySQL80)
   ```
2. Check MySQL is listening on port 3306:
   ```bash
   netstat -an | grep 3306
   ```

### Torch Installation Issues

**Error**: `Could not find a version that satisfies the requirement torch`

**Solution** (especially on Windows):
1. Edit `.env` and set:
   ```bash
   ENABLE_SEMANTICS=False
   ```
2. Install without torch:
   ```bash
   pip install python-docx rapidfuzz mysql-connector-python python-slugify pdfplumber Flask python-dotenv beautifulsoup4 lxml
   ```

Alternatively, install CPU-only torch:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### No Fields Found

**Issue**: Extraction completes but no fields are detected

**Solutions**:

1. **For HTML forms**: Verify placeholders use pattern `{<i>text</i>}`
   
2. **For DOCX forms**: 
   - Verify placeholders are italicized
   - Or enable non-italic mode: `ACCEPT_NON_ITALIC_DOCX=True` in `.env`
   
3. **For PDF forms**:
   - Ensure PDF is text-based (not scanned image)
   - Try opening in a text editor - if you see gibberish, it may require OCR
   
4. **Check configuration**:
   ```bash
   # Ensure correct file types are enabled
   ACCEPT_BRACES_TXT=True
   ACCEPT_BRACES_PDF=True
   ```

5. **Verify file extensions**: Script only processes `.html`, `.htm`, `.docx`, `.txt`, `.pdf`

### Duplicate Column Errors

**Error**: `Duplicate column name 'field_name' in form_field_values_wide`

**Cause**: Field name collision (rare but possible)

**Solution**: 
1. Identify the conflicting field in the database:
   ```sql
   SELECT canonical_name FROM fields WHERE canonical_name = 'field_name';
   ```
2. Manually rename in the database or adjust the original template

### PDF Not Parsing

**Issue**: PDF files show 0 fields extracted

**Solutions**:
1. Check if PDF is text-based:
   ```python
   import pdfplumber
   with pdfplumber.open('your_form.pdf') as pdf:
       print(pdf.pages[0].extract_text())
   ```
   If output is empty/minimal, PDF may be image-based
   
2. For scanned PDFs: See [Future Enhancements](#future-enhancements) for OCR support

3. Verify pdfplumber installation:
   ```bash
   pip show pdfplumber
   ```

### Admin UI Won't Start

**Error**: `Address already in use`

**Solution**: Port 5000 is occupied. Use a different port:
```bash
FLASK_APP=admin_app.py flask run --port 5001
```

**Error**: `No module named flask`

**Solution**: Activate virtual environment and install Flask:
```bash
# Activate venv first (see Step 6)
pip install Flask
```

### Database Already Exists Error

**Issue**: Script fails because tables already exist with different structure

**Solution**: Drop and recreate database (⚠️ destroys all data):
```sql
DROP DATABASE legal_forms;
CREATE DATABASE legal_forms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then re-run extraction script.

## Future Enhancements

### Planned Features

1. **OCR Support for Scanned PDFs**
   - Integration with Tesseract OCR
   - Automatic detection of image-based PDFs
   - Preprocessing for better accuracy

2. **RTF File Support**
   - Parse Rich Text Format documents
   - Extract formatted placeholders

3. **Value Population**
   - Script to populate wide table from filled forms
   - Automated data entry from completed documents
   - Differential detection (template vs. filled)

4. **Advanced Paragraph Parsing**
   - Improved detection of nested options
   - Multi-level enumeration support
   - Complex conditional logic extraction

5. **Enhanced Admin UI**
   - Field merging interface (combine duplicates)
   - Field splitting (separate compound fields)
   - Data type override with validation
   - Bulk editing capabilities
   - Export functionality (CSV, JSON)

6. **Template Generation**
   - Reverse operation: generate blank forms from schema
   - Mail merge functionality
   - Template validation

7. **API Endpoints**
   - REST API for field queries
   - Integration with form-filling applications
   - Webhook support for updates

8. **Field Validation Rules**
   - Define regex patterns for validation
   - Required vs. optional marking
   - Cross-field dependencies

9. **Version Control**
   - Track form template changes over time
   - Field history and evolution
   - Migration scripts for schema updates

10. **Search and Analytics**
    - Full-text search across forms
    - Field usage analytics
    - Similarity detection between forms

### Contributing Ideas

To suggest or implement an enhancement:
1. Open an issue in the GitHub repository
2. Describe the use case and expected behavior
3. Submit a pull request with implementation

## Disclaimer

This system is provided as-is for legal form management and metadata extraction. While designed for legal forms, it can be adapted for any document type with placeholders.

**Important Notes**:
- This tool extracts **metadata** (field definitions), not actual data values
- Always verify extracted fields match your requirements
- Review and edit auto-generated tooltips and data types
- Backup your database regularly
- Use appropriate security measures for production deployments
- This is not a replacement for legal advice or professional document review

**Database Backups**:
```bash
# Backup database
mysqldump -u legal_forms_user -p legal_forms > backup_$(date +%Y%m%d).sql

# Restore from backup
mysql -u legal_forms_user -p legal_forms < backup_20240101.sql
```

**Security Recommendations**:
- Use strong passwords for MySQL users
- Don't commit `.env` file to version control
- Use HTTPS if deploying admin UI publicly
- Restrict database access to localhost in production
- Regularly update dependencies for security patches

## Support

For issues, questions, or suggestions:
1. Check this README first
2. Review the [Troubleshooting](#troubleshooting) section
3. Open an issue on GitHub: https://github.com/megerbyte/forms/issues
4. Include:
   - Error messages (full traceback)
   - Python version (`python --version`)
   - MySQL version (`mysql --version`)
   - Operating system
   - Steps to reproduce

## License

MIT License - See repository for full license text.

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Maintainer**: Legal Forms Extraction System Project

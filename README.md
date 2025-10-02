# Legal Forms Repository

This repository contains legal form templates and the Legal Forms Placeholder Extraction System.

## Contents

### Form Templates
- HTML legal form templates for Texas civil practice
- Various petition forms, motions, and responses
- Located in the root directory

### Legal Forms Extraction System
A comprehensive system for extracting, normalizing, and managing form fields from legal document templates.

**Key Features:**
- Multi-format support (DOCX, TXT, PDF)
- Intelligent field deduplication (fuzzy + optional semantic matching)
- Automatic type inference and option set detection
- Flask admin UI for field management
- Case law crawler with citation graph building

**Documentation:**
- [README_LEGAL_FORMS.md](README_LEGAL_FORMS.md) - Main system documentation
- [CASE_CRAWLER_README.md](CASE_CRAWLER_README.md) - Case crawler guide
- [forms/README_PLACEHOLDER.txt](forms/README_PLACEHOLDER.txt) - Form template guidance

**Quick Start:**
```bash
# Install dependencies
pip install -r requirements-lite.txt  # or requirements.txt for full features

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Extract placeholders
python legal_forms_extractor.py forms/

# Run admin UI
python admin_app.py
```

See [README_LEGAL_FORMS.md](README_LEGAL_FORMS.md) for complete setup and usage instructions.

## License

[Specify license]
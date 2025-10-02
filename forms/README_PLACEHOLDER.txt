Legal Form Templates Placeholder Guide
=======================================

This directory is intended to contain legal form templates for placeholder extraction.

Supported Formats:
------------------
- DOCX (Microsoft Word documents)
- TXT (Plain text files)
- PDF (Portable Document Format - with text extraction)

Placeholder Format:
-------------------
Placeholders should be in the format: {placeholder_text}

For DOCX files:
- Placeholders should be italicized and enclosed in curly braces
- Example: {name of plaintiff}
- The extractor enforces italic formatting by default (configurable)

For TXT/PDF files:
- Placeholders are identified by curly braces: {placeholder_text}
- Italic formatting is not required for these formats

Option Sets:
------------
The system can detect option sets within placeholders, such as:
- {Yes|No|N/A}
- {plaintiff/defendant}
- {2/3}

These will be extracted as separate options and stored in the field_options table.

Paragraph Choose-One Groups:
-----------------------------
The system can detect multiple choice instructions like:
- {CHOOSE APPROPRIATE PARAGRAPH 5}
- {CHOOSE ONE OF THE FOLLOWING}

Paragraphs following such instructions will be grouped together.

How to Add Forms:
-----------------
1. Place your legal form template files in this directory
2. Run the legal_forms_extractor.py script to extract placeholders
3. Review extracted fields in the admin UI
4. Edit tooltips and field metadata as needed

Best Practices:
---------------
- Use clear, descriptive placeholder names
- Be consistent with naming conventions
- Use lowercase for placeholders where possible
- Separate words with spaces or underscores
- Avoid special characters except |, /, and -

Examples:
---------
Good placeholders:
- {name of plaintiff}
- {date of incident}
- {amount in controversy}
- {county name}

Option set placeholders:
- {plaintiff/defendant}
- {Yes|No|N/A}
- {Type A|Type B|Type C}

For more information, see README_LEGAL_FORMS.md

#!/usr/bin/env python3
"""
Demo Script - Legal Forms Field Extraction

This script demonstrates the extraction functionality without requiring
a MySQL database connection. It processes a few sample forms and displays
the extracted fields.

Usage: python demo_extraction.py
"""

import re
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from slugify import slugify

# Placeholder patterns
BRACE_PATTERN = re.compile(r'\{([^}]+)\}')

# Canonical field name mappings
CANONICAL_MAPPINGS = {
    'plaintiff': 'plaintiff_name',
    'defendant': 'defendant_name',
    'case number': 'case_number',
    'cause number': 'cause_number',
    'court': 'court_name',
    'county': 'county_name',
    'date': 'date_field',
    'time': 'time_field',
    'amount': 'amount_value',
    'attorney': 'attorney_name',
    'address': 'address_field',
    'phone': 'phone_number',
    'email': 'email_address',
    'name of': 'name',
    'style of the case': 'case_style',
}


def extract_from_html(file_path):
    """Extract placeholders from HTML files."""
    fields = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'lxml')
        
        # Find all italic tags that might contain placeholders
        for italic_tag in soup.find_all('i'):
            text = italic_tag.get_text()
            parent_text = italic_tag.parent.get_text() if italic_tag.parent else text
            matches = BRACE_PATTERN.findall(parent_text)
            for match in matches:
                if text.strip() in match:
                    fields.add(match.strip())
        
        # Also find direct brace patterns
        matches = BRACE_PATTERN.findall(content)
        for match in matches:
            if len(match.strip()) > 0:
                fields.add(match.strip())
                    
    except Exception as e:
        print(f"  ⚠ Error: {e}")
    
    return fields


def generate_canonical_name(raw_text):
    """Generate a canonical field name from raw text."""
    text = raw_text.lower().strip()
    
    # Apply canonical mappings
    for key, value in CANONICAL_MAPPINGS.items():
        if key in text:
            text = text.replace(key, value)
    
    # Create slug
    canonical = slugify(text, separator='_')
    
    # Ensure it starts with a letter
    if canonical and not canonical[0].isalpha():
        canonical = 'field_' + canonical
    
    # Limit length
    if len(canonical) > 200:
        canonical = canonical[:200]
    
    return canonical or 'field_unknown'


def infer_data_type(field_text):
    """Infer data type from field text."""
    field_lower = field_text.lower()
    
    if any(w in field_lower for w in ['date', 'day', 'month', 'year']):
        return 'date'
    elif any(w in field_lower for w in ['email', 'e-mail']):
        return 'email'
    elif any(w in field_lower for w in ['phone', 'telephone', 'fax']):
        return 'phone'
    elif any(w in field_lower for w in ['amount', 'dollar', 'price', 'cost', 'fee', 'payment']):
        return 'currency'
    elif any(w in field_lower for w in ['number', 'count', 'quantity']):
        return 'integer'
    elif 'yes/no' in field_lower or 'true/false' in field_lower:
        return 'boolean'
    
    return 'text'


def detect_options(raw_text):
    """Detect if field contains options (e.g., plaintiff/defendant)."""
    options = []
    
    if '/' in raw_text:
        parts = raw_text.split('/')
        if len(parts) <= 5:
            options = [p.strip() for p in parts if p.strip()]
    
    return options


def main():
    """Main demo."""
    print("=" * 70)
    print("Legal Forms Field Extraction - DEMO")
    print("=" * 70)
    print()
    print("This demo extracts fields from sample HTML forms without requiring")
    print("a MySQL database. It demonstrates the extraction and naming logic.")
    print()
    
    # Find sample HTML files
    path = Path('.')
    html_files = list(path.glob('Form_*.html'))[:5]  # Process first 5 files
    
    if not html_files:
        print("No Form_*.html files found in current directory.")
        return
    
    print(f"Processing {len(html_files)} sample files...\n")
    
    all_fields = {}
    field_to_canonical = {}
    
    for html_file in html_files:
        print(f"📄 {html_file.name}")
        fields = extract_from_html(html_file)
        print(f"   Found {len(fields)} raw placeholders")
        
        all_fields[html_file.name] = fields
        
        # Process some fields for demo
        for field in list(fields)[:3]:
            canonical = generate_canonical_name(field)
            data_type = infer_data_type(field)
            options = detect_options(field)
            
            field_to_canonical[field] = {
                'canonical': canonical,
                'type': data_type,
                'options': options
            }
        
        print()
    
    # Summary
    print("=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print()
    
    total_raw = sum(len(fields) for fields in all_fields.values())
    unique_canonical = set(info['canonical'] for info in field_to_canonical.values())
    
    print(f"Total raw placeholders: {total_raw}")
    print(f"Sample unique canonical fields: {len(unique_canonical)}")
    print()
    
    # Show some examples
    print("SAMPLE FIELD MAPPINGS:")
    print("-" * 70)
    print(f"{'Raw Field':<40} {'Canonical Name':<25} {'Type':<10}")
    print("-" * 70)
    
    for raw_field, info in list(field_to_canonical.items())[:15]:
        raw_display = (raw_field[:37] + '...') if len(raw_field) > 40 else raw_field
        print(f"{raw_display:<40} {info['canonical']:<25} {info['type']:<10}")
        if info['options']:
            print(f"  └─ Options: {', '.join(info['options'][:3])}")
    
    if len(field_to_canonical) > 15:
        print(f"... and {len(field_to_canonical) - 15} more fields")
    
    print()
    print("=" * 70)
    print("✓ Demo complete!")
    print()
    print("To run the full extraction with database:")
    print("  1. Configure .env file with MySQL credentials")
    print("  2. Run: python legal_forms_extractor.py")
    print()
    print("To launch the admin UI:")
    print("  1. Complete the extraction first")
    print("  2. Run: python admin_app.py")
    print("=" * 70)


if __name__ == '__main__':
    main()

"""
Citation Pattern Recognition Utilities

This module provides regex patterns and extraction functions for identifying
legal citations in case law text, including:
- Southwestern Reporter citations (S.W., S.W.2d, S.W.3d)
- Federal Reporter citations (F., F.2d, F.3d, F.4th)
- U.S. Reports citations (U.S.)
- Context capture around citations

Author: Legal Forms Extraction System
Date: 2025-10-02
"""

import re
from typing import List, Dict, Tuple, Optional


# Citation pattern for Southwestern Reporter (Texas primary reporter)
SOUTHWESTERN_PATTERN = r'\b(\d+)\s+(S\.W\.(?:2d|3d)?)\s+(\d+)\b'

# Citation pattern for Federal Reporters (F., F.2d, F.3d, F.4th)
FEDERAL_PATTERN = r'\b(\d+)\s+(F\.(?:2d|3d|4th)?)\s+(\d+)\b'

# Citation pattern for U.S. Reports
US_REPORTS_PATTERN = r'\b(\d+)\s+(U\.S\.)\s+(\d+)\b'

# Combined pattern for all supported reporters
COMBINED_PATTERN = (
    r'\b(\d+)\s+(S\.W\.(?:2d|3d)?|F\.(?:2d|3d|4th)?|U\.S\.)\s+(\d+)\b'
)

# Treatment signal patterns (for naive treatment detection)
TREATMENT_PATTERNS = {
    'overruled': r'\b(overruled?|overruling)\b',
    'distinguished': r'\b(distinguished?|distinguishing)\b',
    'followed': r'\b(followed?|following|affirmed?|affirming)\b',
    'questioned': r'\b(questioned?|questioning|doubted?|doubting)\b',
    'criticized': r'\b(criticized?|criticizing)\b',
    'limited': r'\b(limited?|limiting)\b',
    'explained': r'\b(explained?|explaining)\b',
    'cited': r'\b(cited?|citing)\b',
}

# Context window size (characters before and after citation)
CONTEXT_WINDOW = 200


def extract_citations(text: str) -> List[Dict[str, any]]:
    """
    Extract all legal citations from text.
    
    Args:
        text: The text to search for citations
        
    Returns:
        List of dictionaries containing citation information:
        - volume: Volume number
        - reporter: Reporter abbreviation
        - page: Page number
        - full_citation: Complete citation string
        - start_pos: Starting position in text
        - end_pos: Ending position in text
    """
    citations = []
    
    for match in re.finditer(COMBINED_PATTERN, text, re.IGNORECASE):
        volume = match.group(1)
        reporter = match.group(2)
        page = match.group(3)
        
        citation = {
            'volume': int(volume),
            'reporter': reporter,
            'page': int(page),
            'full_citation': match.group(0),
            'start_pos': match.start(),
            'end_pos': match.end()
        }
        
        citations.append(citation)
    
    return citations


def extract_citation_with_context(text: str, window_size: int = CONTEXT_WINDOW) -> List[Dict[str, any]]:
    """
    Extract citations along with surrounding context text.
    
    Args:
        text: The text to search for citations
        window_size: Number of characters to capture before and after citation
        
    Returns:
        List of dictionaries containing citation and context information:
        - volume, reporter, page, full_citation (as in extract_citations)
        - context_before: Text before the citation
        - context_after: Text after the citation
        - full_context: Combined context
    """
    citations = extract_citations(text)
    
    for citation in citations:
        start = max(0, citation['start_pos'] - window_size)
        end = min(len(text), citation['end_pos'] + window_size)
        
        citation['context_before'] = text[start:citation['start_pos']].strip()
        citation['context_after'] = text[citation['end_pos']:end].strip()
        citation['full_context'] = text[start:end].strip()
    
    return citations


def detect_treatment(context: str) -> Optional[str]:
    """
    Detect treatment signal in citation context using naive pattern matching.
    
    Args:
        context: The context text around a citation
        
    Returns:
        Treatment type string if detected, None otherwise.
        Possible values: 'overruled', 'distinguished', 'followed', 'questioned',
                        'criticized', 'limited', 'explained', 'cited', 'neutral'
    """
    if not context:
        return 'neutral'
    
    context_lower = context.lower()
    
    # Check each treatment pattern
    for treatment, pattern in TREATMENT_PATTERNS.items():
        if re.search(pattern, context_lower):
            return treatment
    
    return 'neutral'


def normalize_reporter(reporter: str) -> str:
    """
    Normalize reporter abbreviations to standard format.
    
    Args:
        reporter: Reporter abbreviation (may have inconsistent spacing/casing)
        
    Returns:
        Normalized reporter string
    """
    reporter = reporter.upper().strip()
    
    # Handle common variations
    reporter = re.sub(r'\s+', ' ', reporter)  # Normalize whitespace
    reporter = reporter.replace('S. W.', 'S.W.')
    reporter = reporter.replace('U. S.', 'U.S.')
    
    return reporter


def parse_citation_string(citation_str: str) -> Optional[Dict[str, any]]:
    """
    Parse a citation string into its components.
    
    Args:
        citation_str: A citation string like "123 S.W.2d 456"
        
    Returns:
        Dictionary with volume, reporter, page keys, or None if invalid
    """
    match = re.match(COMBINED_PATTERN, citation_str.strip(), re.IGNORECASE)
    
    if match:
        return {
            'volume': int(match.group(1)),
            'reporter': normalize_reporter(match.group(2)),
            'page': int(match.group(3)),
            'full_citation': citation_str.strip()
        }
    
    return None


def build_citation_string(volume: int, reporter: str, page: int) -> str:
    """
    Build a properly formatted citation string.
    
    Args:
        volume: Volume number
        reporter: Reporter abbreviation
        page: Page number
        
    Returns:
        Formatted citation string
    """
    return f"{volume} {normalize_reporter(reporter)} {page}"


def extract_citations_with_treatment(text: str, window_size: int = CONTEXT_WINDOW) -> List[Dict[str, any]]:
    """
    Extract citations with context and treatment detection.
    
    Args:
        text: The text to search for citations
        window_size: Number of characters to capture before and after citation
        
    Returns:
        List of dictionaries with citation info, context, and detected treatment
    """
    citations = extract_citation_with_context(text, window_size)
    
    for citation in citations:
        citation['treatment'] = detect_treatment(citation['full_context'])
    
    return citations


def is_valid_citation(volume: any, reporter: str, page: any) -> bool:
    """
    Validate citation components.
    
    Args:
        volume: Volume number (should be positive integer)
        reporter: Reporter abbreviation
        page: Page number (should be positive integer)
        
    Returns:
        True if citation appears valid, False otherwise
    """
    try:
        vol = int(volume)
        pg = int(page)
        
        if vol <= 0 or pg <= 0:
            return False
        
        # Check if reporter is recognized
        test_citation = f"{vol} {reporter} {pg}"
        return parse_citation_string(test_citation) is not None
        
    except (ValueError, TypeError):
        return False


# Example usage and testing
if __name__ == '__main__':
    # Test text with multiple citations
    test_text = """
    In Smith v. Jones, 123 S.W.2d 456, the court overruled the earlier
    decision in Doe v. Roe, 100 S.W. 234. The Supreme Court in Brown v. Board,
    347 U.S. 483, followed the reasoning. The Fifth Circuit in Garcia v. United States,
    789 F.3d 123, distinguished this holding.
    """
    
    print("Testing citation extraction...")
    citations = extract_citations_with_treatment(test_text)
    
    for i, cit in enumerate(citations, 1):
        print(f"\nCitation {i}:")
        print(f"  Full: {cit['full_citation']}")
        print(f"  Volume: {cit['volume']}, Reporter: {cit['reporter']}, Page: {cit['page']}")
        print(f"  Treatment: {cit['treatment']}")
        print(f"  Context: ...{cit['full_context'][:100]}...")
    
    print("\n" + "="*50)
    print("Testing citation parsing...")
    test_citations = [
        "123 S.W.2d 456",
        "347 U.S. 483",
        "789 F.3d 123",
        "invalid citation"
    ]
    
    for test in test_citations:
        result = parse_citation_string(test)
        print(f"\nParsing '{test}': {result}")

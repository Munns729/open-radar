"""
Shared utilities.
"""
import re

def clean_company_name(text: str) -> str:
    """
    Clean company name from web titles/snippets.
    """
    if not text:
        return ""
        
    s = text.strip()
    
    # Common separators in page titles
    separators = [" - ", " | ", " : ", " – "]
    for sep in separators:
        if sep in s:
            s = s.split(sep)[0] # Take the first part usually
            
    # Remove common suffixes/prefixes
    s = re.sub(r'^(Home|Welcome) to ', '', s, flags=re.IGNORECASE)
    s = re.sub(r'Official Website', '', s, flags=re.IGNORECASE)
    
    return s.strip()

def normalize_name(name: str) -> str:
    """
    Normalize company name for deduplication.
    - Lowercase
    - Remove accents
    - Remove legal suffixes
    - Remove punctuation
    """
    import unicodedata
    import string
    
    if not name:
        return ""
        
    # 1. Lowercase and remove accents
    s = name.lower().strip()
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    
    # 2. Remove punctuation
    s = s.translate(str.maketrans('', '', string.punctuation))
    
    # 3. Remove common legal suffixes (padded with spaces to avoid partial matches)
    # Sorted by length to match longer ones first
    suffixes = [
        "limited", "ltd", "plc", "llc", "inc", "incorporated", "corporation", "corp",
        "gmbh", "ag", "sa", "sas", "sarl", "srl", "bv", "nv", "spa", "ab", "oy", "as", "se"
    ]
    
    words = s.split()
    if len(words) > 1 and words[-1] in suffixes:
        words.pop()
        
    return " ".join(words)

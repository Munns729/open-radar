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


def fuzzy_match_company(
    name: str,
    candidates: list[tuple[int, str]],
    threshold: int = 80,
) -> tuple[int, int] | None:
    """
    Find the best-matching existing company by name (e.g. "Acme Ltd" vs "Acme Limited").
    candidates: list of (company_id, company_name).
    Returns (company_id, score) if best score >= threshold, else None.
    Uses token_set_ratio to handle word order and legal suffixes. 80 catches Ltd/Limited.
    """
    if not name or not name.strip() or not candidates:
        return None
    from rapidfuzz import fuzz
    from rapidfuzz.process import extractOne
    names = [c[1] or "" for c in candidates]
    out = extractOne(name, names, scorer=fuzz.token_set_ratio, score_cutoff=threshold)
    if out is None:
        return None
    _best_name, score, index = out
    return (candidates[index][0], score)

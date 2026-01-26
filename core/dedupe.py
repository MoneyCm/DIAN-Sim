import hashlib
import re
import unicodedata
from rapidfuzz import fuzz, process

def normalize_text(text: str) -> str:
    """
    Normalize text: lower case, remove accents, collapse spaces, remove redundant punctuation.
    """
    text = text.lower()
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    # Remove non-alphanumeric chars (keep basic punctuation for readability but simplified)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compute_hash(text: str) -> str:
    """
    Compute SHA256 of normalized text.
    """
    norm = normalize_text(text)
    return hashlib.sha256(norm.encode('utf-8')).hexdigest()

def find_duplicates(new_stem: str, existing_stems: list[str], threshold: int = 90) -> list[tuple[str, int]]:
    """
    Compare new question stem against existing ones.
    Returns list of matches (existing_stem, score) above threshold.
    """
    norm_new = normalize_text(new_stem)
    # We compare normalized versions for better accuracy
    # But usually rapidfuzz does well with raw text too. For performance on large sets,
    # passing normalized list is better.
    
    # Assuming existing_stems are raw strings, we normalize on the fly or pre-normalize?
    # For small local usage, on-the-fly normalization for existing list might be slow if huge,
    # but fine for 1000s items.
    
    results = process.extract(
        norm_new, 
        [normalize_text(s) for s in existing_stems], 
        scorer=fuzz.token_sort_ratio, 
        limit=5
    )
    
    # Filter by threshold
    return [(match[0], match[1]) for match in results if match[1] >= threshold]

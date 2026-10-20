"""Bilingual Unicode-aware normalization and tokenization utilities.

Supports English, Bangla (বাংলা), numbers, and technical symbols (e.g. C++, C#, .NET).
Maintains strict determinism without destructive stemming or loss of meaning.
"""

import re
import unicodedata
from typing import List, Optional, Set, Tuple


def normalize_unicode_nfc(text: str) -> str:
    """Normalize text using Unicode Standard Form NFC (Canonical Decomposition followed by Canonical Composition).

    Essential for correct Bengali script handling (nuktas, hasants, and vowel diacritics).
    """
    if not text:
        return ""
    return unicodedata.normalize("NFC", text)


def normalize_whitespace(text: str) -> str:
    """Trim leading/trailing whitespace and collapse internal consecutive whitespace to a single space."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_keyword_display(text: str) -> str:
    """Normalize a keyword for user display:
    - Normalizes Unicode to NFC.
    - Strips leading and trailing whitespace.
    - Collapses multiple internal spaces.
    - Preserves original case, punctuation, numbers, and symbols.
    """
    if not text:
        return ""
    nfc = normalize_unicode_nfc(text)
    return normalize_whitespace(nfc)


def normalize_keyword_key(text: str) -> str:
    """Produce a canonical key for comparison, deduplication, and database indexing:
    - Normalizes Unicode to NFC.
    - Collapses whitespace.
    - Converts to lower case (case-folding) while preserving meaningful symbols and Bengali script.
    - Does not perform destructive stemming or remove meaningful words.
    """
    if not text:
        return ""
    display = normalize_keyword_display(text)
    return display.lower()


# Regex pattern to match meaningful tokens:
# 1. Words with technical symbols: e.g. C++, C#, .NET, Node.js, F#, ASP.NET
# 2. Versioned numbers and decimals: e.g. 3.12, 10.5, 2026, ৩.১২
# 3. Standard alphanumeric words in English or Bengali (\w+ in Python matches Unicode letters/digits)
TOKEN_PATTERN = re.compile(
    r"""
    (?:[A-Za-z0-9\u0980-\u09ff]+(?:\.[A-Za-z0-9\u0980-\u09ff]+)+(?:[+#]+)?)  # e.g. node.js, asp.net, 3.12, ৩.১২
    | (?:\.[A-Za-z0-9\u0980-\u09ff]+(?:[+#]+)?)                                 # e.g. .net, .env
    | (?:[A-Za-z0-9\u0980-\u09ff]+[+#]+)                                        # e.g. c++, c#, f#
    | (?:[A-Za-z0-9\u0980-\u09ff]+(?:-[A-Za-z0-9\u0980-\u09ff]+)+)            # e.g. step-by-step, how-to
    | (?:[A-Za-z0-9\u0980-\u09ff]+)                                             # Standard English or Bangla words
    """,
    re.VERBOSE | re.UNICODE,
)


def tokenize_keyword(text: str) -> List[str]:
    """Tokenize a keyword in a Unicode-aware manner for English and Bangla.

    Preserves technical symbols (+, #), decimal version numbers (3.12, ৩.১২),
    and hyphenated compounds without mangling Bengali diacritics.
    """
    if not text:
        return []
    normalized = normalize_keyword_display(text)
    # If the text has words split by whitespace, find all matched tokens
    tokens = TOKEN_PATTERN.findall(normalized)
    if not tokens:
        # Fallback to whitespace split if regex found nothing
        tokens = normalized.split()
    return tokens


def count_tokens(text: str) -> int:
    """Count the number of meaningful tokens/words in a keyword.

    Handles English, Bangla (বাংলা), mixed languages, numbers, and technical symbols.
    """
    if not text:
        return 0
    return len(tokenize_keyword(text))


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein distance between two strings using dynamic programming."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0, v1 = v1, v0

    return v0[len(s2)]


def fuzzy_similarity(s1: str, s2: str) -> float:
    """Compute a normalized similarity score in [0.0, 1.0] between two strings.

    1.0 means exact match, 0.0 means completely different.
    """
    k1 = normalize_keyword_key(s1)
    k2 = normalize_keyword_key(s2)
    if k1 == k2:
        return 1.0
    max_len = max(len(k1), len(k2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(k1, k2)
    return max(0.0, 1.0 - (dist / max_len))


def find_fuzzy_duplicates(
    keywords: List[str], threshold: float = 0.85
) -> List[Tuple[str, str, float]]:
    """Identify potential fuzzy duplicate pairs above the specified similarity threshold.

    Returns a list of (keyword1, keyword2, similarity_score).
    This function is completely non-destructive: it only reports suggestions without modifying data.
    """
    if not keywords or len(keywords) < 2:
        return []

    # Filter unique canonical keys first
    unique_map = {}
    for kw in keywords:
        key = normalize_keyword_key(kw)
        if key not in unique_map:
            unique_map[key] = kw

    unique_keys = list(unique_map.keys())
    results: List[Tuple[str, str, float]] = []

    for i in range(len(unique_keys)):
        for j in range(i + 1, len(unique_keys)):
            k1 = unique_keys[i]
            k2 = unique_keys[j]
            # Quick length heuristic: if length difference ratio is large, skip
            if abs(len(k1) - len(k2)) / max(len(k1), len(k2)) > (1.0 - threshold):
                continue
            sim = fuzzy_similarity(k1, k2)
            if sim >= threshold:
                results.append((unique_map[k1], unique_map[k2], round(sim, 3)))

    return sorted(results, key=lambda x: x[2], reverse=True)

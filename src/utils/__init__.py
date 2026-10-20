"""Utilities package for logging, input validation, and normalization."""

from src.utils.logging import get_logger
from src.utils.normalization import (
    count_tokens,
    find_fuzzy_duplicates,
    fuzzy_similarity,
    normalize_keyword_display,
    normalize_keyword_key,
    normalize_unicode_nfc,
    normalize_whitespace,
    tokenize_keyword,
)
from src.utils.validators import sanitize_seed_keyword, validate_crawl_parameters

__all__ = [
    "get_logger",
    "sanitize_seed_keyword",
    "validate_crawl_parameters",
    "normalize_unicode_nfc",
    "normalize_whitespace",
    "normalize_keyword_display",
    "normalize_keyword_key",
    "tokenize_keyword",
    "count_tokens",
    "fuzzy_similarity",
    "find_fuzzy_duplicates",
]

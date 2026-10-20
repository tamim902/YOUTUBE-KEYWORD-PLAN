"""Input validation and sanitization utilities.

Provides Unicode-safe keyword sanitization supporting English, Bangla (বাংলা),
and other multi-lingual scripts, alongside parameter range validation.
"""

import re
import unicodedata
from typing import Optional, Tuple

from src.config import config


def sanitize_seed_keyword(text: Optional[str]) -> Tuple[bool, str, str]:
    """Validate and sanitize a user-supplied seed keyword.

    Supports Unicode characters (including Bangla, Hindi, Arabic, Latin, etc.),
    removes dangerous control characters, and enforces length bounds.

    Returns:
        (is_valid, sanitized_text, error_message)
    """
    if not text:
        return False, "", "Seed keyword cannot be empty."

    # Normalize Unicode (NFC form prevents decomposition issues in Bangla)
    normalized = unicodedata.normalize("NFC", text)

    # Strip control characters (ASCII 0-31, 127, and Unicode Cc/Cf except standard spaces)
    cleaned = "".join(
        ch for ch in normalized if not unicodedata.category(ch).startswith("C")
    )

    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return False, "", "Seed keyword contains only whitespace or unsupported characters."

    if len(cleaned) < 2:
        return False, cleaned, "Seed keyword must be at least 2 characters long."

    if len(cleaned) > 150:
        return False, cleaned[:150], "Seed keyword cannot exceed 150 characters."

    return True, cleaned, ""


def validate_crawl_parameters(
    max_depth: int, request_budget: int
) -> Tuple[bool, str]:
    """Validate recursion depth and request budget limits."""
    if max_depth < 0 or max_depth > config.max_allowed_depth:
        return (
            False,
            f"Max depth must be between 0 and {config.max_allowed_depth}.",
        )

    if request_budget < 1 or request_budget > config.max_allowed_budget:
        return (
            False,
            f"Request budget must be between 1 and {config.max_allowed_budget}.",
        )

    return True, ""

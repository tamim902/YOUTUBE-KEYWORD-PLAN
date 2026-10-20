"""Smart Keyword Pattern Generator package."""

from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import (
    GeneratedKeyword,
    PatternCategory,
    PatternConfig,
    PatternLanguage,
    normalize_keyword_key,
)
from src.patterns.templates import (
    BN_TEMPLATES,
    COMPARISON_GENERAL_BN,
    COMPARISON_GENERAL_EN,
    COMPARISON_SPECIFIC_BN,
    COMPARISON_SPECIFIC_EN,
    EN_TEMPLATES,
)

__all__ = [
    "SmartKeywordPatternGenerator",
    "GeneratedKeyword",
    "PatternCategory",
    "PatternConfig",
    "PatternLanguage",
    "normalize_keyword_key",
    "EN_TEMPLATES",
    "BN_TEMPLATES",
    "COMPARISON_GENERAL_EN",
    "COMPARISON_SPECIFIC_EN",
    "COMPARISON_GENERAL_BN",
    "COMPARISON_SPECIFIC_BN",
]

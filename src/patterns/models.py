"""Domain models and configuration for smart keyword pattern generation."""

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.keyword import ClassificationType, KeywordItem, SourceType


class PatternCategory(str, Enum):
    """Supported pattern variation categories."""

    LISTICLES = "listicles"
    BEST_BUYING = "best_buying"
    REVIEWS = "reviews"
    HOW_TO = "how_to"
    COMPARISON = "comparison"
    QUESTIONS = "questions"
    AUDIENCE = "audience"
    TIME_MODIFIERS = "time_modifiers"


class PatternLanguage(str, Enum):
    """Language output modes for generated patterns."""

    EN = "en"
    BN = "bn"
    BOTH = "both"


def normalize_keyword_key(text: str) -> str:
    """Canonical key for keyword comparison and deduplication (NFC Unicode, lowercased, single-spaced)."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text)
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    return collapsed.lower()


@dataclass
class GeneratedKeyword:
    """Represents an algorithmically generated keyword variation."""

    keyword: str
    normalized_key: str
    pattern_category: PatternCategory
    pattern_template: str
    seed_keyword: str
    language: str = "en"
    source_type: str = "generated"
    source_name: str = "pattern_generator"
    generation_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        self.keyword = unicodedata.normalize("NFC", self.keyword.strip())
        if not self.normalized_key:
            self.normalized_key = normalize_keyword_key(self.keyword)

    def to_dict(self) -> Dict[str, Any]:
        """Convert keyword to dictionary representation for UI tables."""
        data = asdict(self)
        data["category"] = (
            self.pattern_category.value
            if isinstance(self.pattern_category, PatternCategory)
            else str(self.pattern_category)
        )
        return data

    def to_keyword_item(self) -> KeywordItem:
        """Convert to KeywordItem for database persistence."""
        cat_map = {
            PatternCategory.LISTICLES: ClassificationType.LISTICLE,
            PatternCategory.REVIEWS: ClassificationType.REVIEW,
            PatternCategory.HOW_TO: ClassificationType.HOW_TO,
            PatternCategory.COMPARISON: ClassificationType.COMPARISON,
            PatternCategory.QUESTIONS: ClassificationType.QUESTION,
        }
        classification = cat_map.get(self.pattern_category, ClassificationType.GENERAL)
        return KeywordItem(
            keyword=self.keyword,
            seed_keyword=self.seed_keyword,
            source=SourceType.GENERATED,
            classification=classification,
            depth=0,
            parent_keyword=self.seed_keyword,
            language=self.language,
        )


@dataclass
class PatternConfig:
    """Runtime configuration for keyword pattern generation."""

    seeds: List[str]
    categories: List[PatternCategory] = field(
        default_factory=lambda: list(PatternCategory)
    )
    language_mode: PatternLanguage = PatternLanguage.BOTH
    alternatives: Optional[List[str]] = None
    include_current_year: bool = True
    current_year: Optional[int] = None
    max_generated: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate pattern configuration."""
        if not self.seeds:
            raise ValueError("At least one seed keyword is required.")
        # Filter and sanitize seeds
        cleaned_seeds = [
            unicodedata.normalize("NFC", s.strip()) for s in self.seeds if s and s.strip()
        ]
        if not cleaned_seeds:
            raise ValueError("At least one non-empty seed keyword is required.")
        self.seeds = cleaned_seeds

        if not self.categories:
            raise ValueError("At least one pattern category must be enabled.")

        if self.max_generated is not None and self.max_generated <= 0:
            raise ValueError("max_generated must be positive if specified.")

        if self.current_year is not None and self.current_year < 2000:
            raise ValueError("current_year must be valid (>= 2000).")

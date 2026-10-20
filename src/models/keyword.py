"""Domain models for keywords, classifications, and source attribution.

Maintains strict data integrity by clearly separating:
- Live autocomplete results
- Cached autocomplete results
- Algorithmically generated keyword variations

No synthetic metrics (CPC, search volume, difficulty scores) are generated.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    """Source provenance for discovered keywords."""

    AUTOCOMPLETE = "autocomplete"
    GENERATED = "generated"
    LIVE = "live"
    CACHED = "cached"
    ALGORITHMIC = "algorithmic"
    LIVE_AUTOCOMPLETE = "LIVE_AUTOCOMPLETE"
    CACHED_AUTOCOMPLETE = "CACHED_AUTOCOMPLETE"
    GENERATED_PATTERN = "GENERATED_PATTERN"



class ClassificationType(str, Enum):
    """Classification categories for search terms."""

    SHORT_TAIL = "Short-tail"
    MEDIUM_TAIL = "Medium-tail"
    LONG_TAIL = "Long-tail"
    QUESTION = "Question"
    LISTICLE = "Listicle"
    REVIEW = "Review"
    HOW_TO = "How-to"
    COMPARISON = "Comparison"
    GENERAL = "General"


def calculate_word_count(text: str) -> int:
    """Calculate word count with Unicode and multi-language support (English & Bangla)."""
    if not text:
        return 0
    words = text.strip().split()
    return len(words)


def infer_tail_length(word_count: int) -> ClassificationType:
    """Classify tail length based on word count."""
    if word_count <= 2:
        return ClassificationType.SHORT_TAIL
    elif word_count <= 4:
        return ClassificationType.MEDIUM_TAIL
    else:
        return ClassificationType.LONG_TAIL


@dataclass
class KeywordItem:
    """Represents a discovered or generated keyword item with source attribution."""

    keyword: str
    seed_keyword: str
    source: SourceType
    classification: ClassificationType = ClassificationType.GENERAL
    depth: int = 0
    parent_keyword: Optional[str] = None
    language: str = "en"
    country: str = "US"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    normalized_key: Optional[str] = None
    tail_length: Optional[str] = None
    intent_labels: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    relevance_score: float = 0.0
    cluster_name: str = "Core Seed Variations"
    intent_explanation: str = ""

    def __post_init__(self) -> None:
        """Validate and normalize keyword item."""
        self.keyword = self.keyword.strip()
        self.seed_keyword = self.seed_keyword.strip()
        if not self.keyword:
            raise ValueError("Keyword string cannot be empty.")
        if not self.seed_keyword:
            raise ValueError("Seed keyword cannot be empty.")
        if self.depth < 0:
            raise ValueError("Depth must be non-negative.")
        if not self.normalized_key:
            from src.utils.normalization import normalize_keyword_key
            self.normalized_key = normalize_keyword_key(self.keyword)
        if not self.sources:
            self.sources = [self.source.value]

    @property
    def word_count(self) -> int:
        """Number of words in keyword."""
        return calculate_word_count(self.keyword)

    def to_dict(self) -> Dict[str, Any]:
        """Convert keyword to dictionary representation for pandas/UI."""
        data = asdict(self)
        data["source"] = self.source.value
        data["classification"] = self.classification.value
        data["word_count"] = self.word_count
        data["created_at"] = self.created_at.isoformat()
        data["normalized_key"] = self.normalized_key
        data["tail_length"] = self.tail_length or infer_tail_length(self.word_count).value
        data["intent_labels"] = self.intent_labels
        data["sources"] = self.sources
        data["relevance_score"] = round(self.relevance_score, 1)
        data["cluster_name"] = self.cluster_name
        data["intent_explanation"] = self.intent_explanation
        return data


@dataclass
class AutocompleteResult:
    """Structured result returned by an autocomplete provider."""

    keyword: str
    source_type: str = "autocomplete"
    source_name: str = "youtube_autocomplete"
    language: str = "en"
    country: str = "US"
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    discovery_query: str = ""
    is_cached: bool = False

    def __post_init__(self) -> None:
        self.keyword = self.keyword.strip()
        if not self.keyword:
            raise ValueError("Keyword string cannot be empty.")

    @property
    def strict_source_type(self) -> str:
        """Strict provenance label: LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, or GENERATED_PATTERN."""
        if self.is_cached or self.source_type in ("cached", "CACHED_AUTOCOMPLETE"):
            return "CACHED_AUTOCOMPLETE"
        if self.source_type in ("generated", "GENERATED_PATTERN"):
            return "GENERATED_PATTERN"
        return "LIVE_AUTOCOMPLETE"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        data = asdict(self)
        data["strict_source_type"] = self.strict_source_type
        return data

    def to_keyword_item(self, seed_keyword: Optional[str] = None) -> KeywordItem:
        """Convert to KeywordItem for database persistence."""
        seed = seed_keyword if seed_keyword else (self.discovery_query or self.keyword)
        src = (
            SourceType.CACHED_AUTOCOMPLETE
            if self.is_cached
            else SourceType.AUTOCOMPLETE
        )
        return KeywordItem(
            keyword=self.keyword,
            seed_keyword=seed,
            source=src,
            language=self.language,
            country=self.country,
        )


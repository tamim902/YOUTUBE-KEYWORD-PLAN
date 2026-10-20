"""Domain models, configurations, and progress data structures for recursive crawling."""

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.models.keyword import KeywordItem, SourceType


class StopReason(str, Enum):
    """Reason why the recursive crawler stopped execution."""

    QUEUE_EXHAUSTED = "Queue exhausted"
    TARGET_REACHED = "Result target reached"
    BUDGET_EXHAUSTED = "Request budget exhausted"
    MAX_DEPTH_REACHED = "Maximum depth reached"
    CANCELLED = "User cancellation"
    PROVIDER_ERROR = "Provider failure"
    MAX_QUEUE_SIZE_REACHED = "Maximum queue size reached"


def normalize_keyword_key(text: str) -> str:
    """Produce a canonical key for deduplication and comparison.

    Preserves Bangla Unicode (via NFC normalization), strips extra whitespace,
    and applies case-folding without destructive stemming.
    """
    if not text:
        return ""
    # Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text)
    # Collapse multiple whitespaces
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    return collapsed.lower()


@dataclass
class DiscoveredKeyword:
    """Represents a unique keyword discovered through recursive expansion."""

    keyword: str
    normalized_key: str
    depth: int
    parent_queries: List[str] = field(default_factory=list)
    discovery_paths: int = 1
    source_type: str = "autocomplete"
    source_name: str = "youtube_autocomplete"
    language: str = "en"
    country: str = "US"
    first_discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    is_generated: bool = False
    pattern_category: Optional[str] = None
    pattern_template: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    tail_length: Optional[str] = None
    intent_labels: List[str] = field(default_factory=list)
    word_count: Optional[int] = None
    discovery_query: str = ""
    is_cached: bool = False
    relevance_score: float = 0.0
    cluster_name: str = "Core Seed Variations"
    intent_explanation: str = ""

    def __post_init__(self) -> None:
        if not self.sources:
            self.sources = [self.source_type]
        if not self.discovery_query and self.parent_queries:
            self.discovery_query = self.parent_queries[0]

    @property
    def strict_source_label(self) -> str:
        """Strict provenance label: LIVE_AUTOCOMPLETE, CACHED_AUTOCOMPLETE, or GENERATED_PATTERN."""
        if (
            self.is_generated
            or self.source_type in ("generated", "GENERATED_PATTERN")
            or "generated" in self.sources
            or "GENERATED_PATTERN" in self.sources
        ):
            return "GENERATED_PATTERN"
        if (
            self.is_cached
            or self.source_type in ("cached", "CACHED_AUTOCOMPLETE")
            or "cached" in self.sources
            or "CACHED_AUTOCOMPLETE" in self.sources
        ):
            return "CACHED_AUTOCOMPLETE"
        return "LIVE_AUTOCOMPLETE"

    def add_discovery_path(self, parent_query: Optional[str], found_depth: int) -> None:
        """Merge a rediscovery path into this keyword record."""
        self.discovery_paths += 1
        self.last_discovered_at = datetime.now(timezone.utc).isoformat()
        if found_depth < self.depth:
            self.depth = found_depth
        if parent_query and parent_query not in self.parent_queries:
            self.parent_queries.append(parent_query)
        if not self.discovery_query and parent_query:
            self.discovery_query = parent_query

    def to_dict(self) -> Dict[str, Any]:
        """Convert keyword to dictionary representation for UI tables."""
        data = asdict(self)
        data["strict_source_type"] = self.strict_source_label
        data["relevance_score"] = round(self.relevance_score, 1)
        data["cluster_name"] = self.cluster_name
        data["intent_explanation"] = self.intent_explanation
        data["discovery_query"] = self.discovery_query or (
            self.parent_queries[0] if self.parent_queries else self.keyword
        )
        data["parent_queries_str"] = (
            ", ".join(self.parent_queries) if self.parent_queries else "(seed)"
        )
        data["sources_str"] = ", ".join(self.sources) if self.sources else self.source_type
        data["intent_labels_str"] = ", ".join(self.intent_labels) if self.intent_labels else "Informational"
        return data


    def to_keyword_item(self, seed_keyword: Optional[str] = None) -> KeywordItem:
        """Convert to KeywordItem for database persistence."""
        seed = seed_keyword or (self.parent_queries[0] if self.parent_queries else self.keyword)
        parent = self.parent_queries[0] if self.parent_queries else None
        src = (
            SourceType.GENERATED
            if self.source_type == "generated"
            else SourceType.AUTOCOMPLETE
        )
        return KeywordItem(
            keyword=self.keyword,
            seed_keyword=seed,
            source=src,
            depth=self.depth,
            parent_keyword=parent,
            language=self.language,
            country=self.country,
            normalized_key=self.normalized_key,
            tail_length=self.tail_length,
            intent_labels=self.intent_labels,
            sources=self.sources,
            relevance_score=self.relevance_score,
            cluster_name=self.cluster_name,
            intent_explanation=self.intent_explanation,
        )


@dataclass
class CrawlConfig:
    """Runtime parameters for the recursive crawler."""

    seeds: List[str]
    language: str = "en"
    country: str = "US"
    max_depth: int = 2
    max_unique_keywords: int = 50
    request_budget: int = 25
    min_delay_seconds: float = 0.1
    use_cache: bool = True
    max_queue_size: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate configuration bounds."""
        if not self.seeds:
            raise ValueError("At least one seed keyword is required.")
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative.")
        if self.max_unique_keywords <= 0:
            raise ValueError("max_unique_keywords must be positive.")
        if self.request_budget <= 0:
            raise ValueError("request_budget must be positive.")
        if self.min_delay_seconds < 0:
            raise ValueError("min_delay_seconds cannot be negative.")
        if self.max_queue_size is not None and self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive if specified.")


@dataclass
class CrawlProgress:
    """Real-time progress telemetry emitted during crawling."""

    queries_processed: int = 0
    keywords_discovered: int = 0
    current_depth: int = 0
    requests_remaining: int = 0
    current_query: str = ""


@dataclass
class CrawlResult:
    """Final output of a recursive crawl session."""

    keywords: List[DiscoveredKeyword]
    stop_reason: StopReason
    queries_processed: int
    total_requests_made: int
    is_partial: bool
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

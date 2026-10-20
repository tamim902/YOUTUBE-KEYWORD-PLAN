"""Domain models and configuration for keyword classification and search intent analysis."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TailLength(str, Enum):
    """Classification of keyword length based on token count."""

    SHORT_TAIL = "Short-tail"
    MEDIUM_TAIL = "Medium-tail"
    LONG_TAIL = "Long-tail"


class SearchIntent(str, Enum):
    """Predicted user search intent categories.

    Note: Intent predictions are rule-based heuristics and do not imply
    observed search volume or verified user analytics.
    """

    INFORMATIONAL = "Informational"
    TUTORIAL = "Tutorial"
    COMPARISON = "Comparison"
    REVIEW = "Review"
    COMMERCIAL_INVESTIGATION = "Commercial Investigation"
    BUYING_INTENT = "Buying Intent"
    QUESTION = "Question"
    LISTICLE = "Listicle"
    # Phase 9 Canonical Categories
    HOW_TO_TUTORIAL = "How-to / Tutorial"
    COMPARISON_VS = "Comparison / VS"
    BEST_TOP_LIST = "Best / Top list"
    BUYING_COMMERCIAL = "Buying / Commercial intent"
    PROBLEM_SOLVING = "Problem-solving"
    AUDIENCE_SPECIFIC = "Audience-specific"
    LOCATION_SPECIFIC = "Location-specific"
    GENERAL = "General / Unclassified"


@dataclass
class TailThresholds:
    """Configurable token count thresholds for tail length classification."""

    short_max: int = 2
    medium_max: int = 4

    def __post_init__(self) -> None:
        if self.short_max < 1:
            raise ValueError("short_max must be at least 1.")
        if self.medium_max <= self.short_max:
            raise ValueError("medium_max must be strictly greater than short_max.")

    def classify(self, word_count: int) -> TailLength:
        """Classify tail length based on configured word count thresholds."""
        if word_count <= self.short_max:
            return TailLength.SHORT_TAIL
        elif word_count <= self.medium_max:
            return TailLength.MEDIUM_TAIL
        else:
            return TailLength.LONG_TAIL


@dataclass
class KeywordClassification:
    """Structured classification result for a single keyword.

    Strictly separates:
    - Tail length (structural token count)
    - Search intent (semantic purpose)
    - Provenance/Source (which remains in the keyword's source field)
    """

    keyword: str
    normalized_key: str
    word_count: int
    tail_length: TailLength
    intent_labels: List[SearchIntent] = field(default_factory=list)
    primary_intent: SearchIntent = SearchIntent.INFORMATIONAL
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    matched_reasons: Dict[str, str] = field(default_factory=dict)
    primary_explanation: str = ""
    is_question: bool = False
    is_listicle: bool = False
    is_review: bool = False
    is_tutorial: bool = False
    is_comparison: bool = False
    is_buying_intent: bool = False
    is_commercial_investigation: bool = False
    is_informational: bool = True
    is_problem_solving: bool = False
    is_audience_specific: bool = False
    is_location_specific: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert classification result to a dictionary representation."""
        data = asdict(self)
        data["tail_length"] = self.tail_length.value
        data["primary_intent"] = self.primary_intent.value
        data["intent_labels"] = [i.value for i in self.intent_labels]
        data["matched_reasons"] = self.matched_reasons
        data["primary_explanation"] = self.primary_explanation
        return data

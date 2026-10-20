"""Domain models for Product Opportunity Ranking & Affiliate Content Planner (Phase 14)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ShortlistStatus(str, Enum):
    """Workflow lifecycle statuses for shortlisted product opportunities."""

    DISCOVERED = "Discovered"
    NEEDS_RESEARCH = "Needs Research"
    VERIFIED = "Verified"
    SHORTLISTED = "Shortlisted"
    BRIEF_CREATED = "Brief Created"
    IN_PRODUCTION = "In Production"
    PUBLISHED = "Published"
    REJECTED = "Rejected"


class ContentFormatRecommendation(str, Enum):
    """Strategic content formats recommended based on product attributes and search evidence."""

    PRODUCT_REVIEW = "Product Review"
    UNBOXING = "Unboxing"
    PRODUCT_COMPARISON = "Product Comparison"
    ALTERNATIVES = "Alternatives"
    BUYING_GUIDE = "Buying Guide"
    BEGINNER_TUTORIAL = "Beginner Tutorial"
    COMMON_MISTAKES = "Common Mistakes"
    LONG_TERM_REVIEW = "Long-Term Review"
    PROBLEM_SOLVING = "Problem-Solving Video"


@dataclass
class AffiliateProductData:
    """Represents real or user-supplied affiliate and merchant metadata."""

    product_name: str
    brand: str = ""
    model: str = ""
    product_page_url: str = ""
    merchant: str = ""  # e.g., "Amazon", "Best Buy", "B&H", "Manufacturer Direct"
    price: Optional[float] = None
    currency: str = "USD"
    affiliate_program: str = ""  # e.g., "Amazon Associates", "Brand Affiliate"
    commission_info: str = "Needs verification"
    availability: str = "Unknown"  # "In Stock", "Pre-Order", "Backordered", "Unknown"
    affiliate_link: str = ""
    is_verified_merchant: bool = False
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AffiliateProductData":
        valid_keys = {
            "product_name", "brand", "model", "product_page_url", "merchant",
            "price", "currency", "affiliate_program", "commission_info",
            "availability", "affiliate_link", "is_verified_merchant",
            "retrieved_at", "notes",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ProductOpportunityShortlist:
    """Represents a product prioritized for YouTube content planning."""

    product_name: str
    id: Optional[int] = None
    product_id: Optional[int] = None
    session_id: Optional[int] = None
    brand: str = ""
    model: str = ""
    niche: str = ""
    category: str = ""
    country: str = "US"
    language: str = "en"
    status: str = ShortlistStatus.SHORTLISTED.value
    priority: str = "Medium"  # "High", "Medium", "Low"
    intended_format: str = ContentFormatRecommendation.PRODUCT_REVIEW.value
    notes: str = ""
    opportunity_score: float = 50.0  # 0 to 100 heuristic
    confidence_level: str = "Moderate Evidence"  # "High Evidence", "Moderate Evidence", "Low Evidence"
    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    formula_version: str = "v14.0"
    matching_videos_count: int = 0
    queries_executed_count: int = 0
    supporting_keywords: List[str] = field(default_factory=list)
    affiliate_data: Dict[str, Any] = field(default_factory=dict)
    verification_checklist: Dict[str, bool] = field(
        default_factory=lambda: {
            "identity_verified": False,
            "specs_checked": False,
            "merchant_available": False,
            "competitor_evidence_reviewed": False,
            "affiliate_compliance_ready": False,
        }
    )
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductOpportunityShortlist":
        valid_keys = {
            "id", "product_id", "session_id", "product_name", "brand", "model",
            "niche", "category", "country", "language", "status", "priority",
            "intended_format", "notes", "opportunity_score", "confidence_level",
            "score_breakdown", "formula_version", "matching_videos_count",
            "queries_executed_count", "supporting_keywords", "affiliate_data",
            "verification_checklist", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class AffiliateContentBrief:
    """Editable, evidence-grounded content brief for an affiliate video production."""

    product_name: str
    primary_keyword: str
    id: Optional[int] = None
    shortlist_id: Optional[int] = None
    product_id: Optional[int] = None
    brand: str = ""
    model: str = ""
    category: str = ""
    supporting_keywords: List[str] = field(default_factory=list)
    target_audience: str = "General Consumers"
    search_intent: str = "Commercial Investigation"
    content_format: str = ContentFormatRecommendation.PRODUCT_REVIEW.value
    title_ideas: List[str] = field(default_factory=list)
    video_structure: List[Dict[str, str]] = field(default_factory=list)
    questions_to_investigate: List[str] = field(default_factory=list)
    features_to_verify: List[str] = field(default_factory=list)
    pros_and_cons: Dict[str, List[str]] = field(
        default_factory=lambda: {"pros": [], "cons": []}
    )
    competitor_references: List[Dict[str, Any]] = field(default_factory=list)
    call_to_action: str = ""
    affiliate_disclosure: str = (
        "FTC Compliance Disclosure: State clearly at the start of the video and in the first lines of the description: "
        "'Disclosure: Some links in this description are affiliate links. If you purchase through them, I may earn a small commission at no additional cost to you.'"
    )
    fact_checking_checklist: List[Dict[str, Any]] = field(default_factory=list)
    brief_notes: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AffiliateContentBrief":
        valid_keys = {
            "id", "shortlist_id", "product_id", "product_name", "primary_keyword",
            "brand", "model", "category", "supporting_keywords", "target_audience",
            "search_intent", "content_format", "title_ideas", "video_structure",
            "questions_to_investigate", "features_to_verify", "pros_and_cons",
            "competitor_references", "call_to_action", "affiliate_disclosure",
            "fact_checking_checklist", "brief_notes", "created_at", "updated_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

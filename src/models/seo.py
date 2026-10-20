"""Domain models for Advanced YouTube SEO Intelligence, Title Generation, and Description Studio (Phase 22 Parts 2, 3, 4, 5)."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class KeywordIntentType(str, Enum):
    """Categorized search intent types for empirical YouTube keyword queries."""

    INFORMATIONAL = "Informational"
    REVIEW_BUYER = "Review & Buyer Intent"
    COMPARISON = "Comparison / VS"
    HOW_TO = "How-To & Tutorial"
    PROBLEM_SOLVING = "Problem Solving"
    QUESTION = "Question / Investigation"
    LISTICLE = "Listicle & Best-Of"
    PRODUCT_SPECIFIC = "Product / Model Specific"
    SEMANTIC_SUPPORT = "Semantic Supporting Term"


class SeoRelevanceTier(str, Enum):
    HIGH = "High Channel Relevance"
    MODERATE = "Moderate Channel Relevance"
    PERIPHERAL = "Peripheral / Broad"
    LOW = "Low / Peripheral Relevance"


class SeoOpportunityTier(str, Enum):
    EXCEPTIONAL = "Exceptional Opportunity"
    STRONG = "Strong Opportunity"
    HIGH = "High Opportunity"
    MODERATE = "Moderate Opportunity"
    SATURATED = "Saturated / Low Margin"
    LOW = "Low / Saturated Opportunity"


class AffiliatePotentialTier(str, Enum):
    HIGH = "High Affiliate Potential"
    MODERATE = "Moderate Commercial Intent"
    LOW = "Low Commercial Intent"
    INFORMATIONAL = "Non-Commercial / Pure Info"
    NONE = "Affiliate Disabled / Non-Commercial"
    DISABLED = "Affiliate Disabled"


class ResearchConfidenceTier(str, Enum):
    HIGH = "High Confidence (Empirical Evidence)"
    MODERATE = "Moderate Confidence (Sample Coverage)"
    PRELIMINARY = "Preliminary (Low Query Coverage)"
    LOW = "Preliminary / Low Coverage"


@dataclass
class SeoOpportunityScore:
    """Transparent, multi-dimensional SEO opportunity scoring model without fabricated rankings."""

    overall_score: float = 50.0  # 0 to 100
    seo_relevance_label: str = SeoRelevanceTier.MODERATE.value
    opportunity_label: str = SeoOpportunityTier.MODERATE.value
    affiliate_potential_label: str = AffiliatePotentialTier.MODERATE.value
    confidence_level: str = ResearchConfidenceTier.MODERATE.value
    is_search_volume_available: bool = False
    volume_display_text: str = "Search volume unavailable"
    signals_breakdown: Dict[str, Any] = field(default_factory=dict)
    contributing_factors: List[str] = field(default_factory=list)
    explanation: str = ""
    guaranteed_ranking_disclaimer: str = "Heuristic opportunity estimate based on competition gap, channel alignment, and search intent. Does not guarantee search rankings or views."
    data_freshness: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeoKeywordItem:
    """Keyword enriched with multi-dimensional SEO attributes, channel relevance, and empirical evidence."""

    keyword: str
    seed_keyword: str
    category: str = "Primary Keyword"
    intent: str = KeywordIntentType.INFORMATIONAL.value
    relevance_score: float = 75.0
    channel_fit: str = "Matched Channel Niche"
    word_count: int = 2
    is_long_tail: bool = False
    source_type: str = "LIVE_AUTOCOMPLETE"
    retrieval_time: str = field(default_factory=_now_iso)
    language: str = "en"
    country: str = "US"
    has_video_evidence: bool = False
    median_competitor_views: float = 0.0
    opportunity_score: Optional[SeoOpportunityScore] = None
    missing_data_warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.word_count = len(self.keyword.strip().split())
        self.is_long_tail = self.word_count >= 3
        if not self.missing_data_warnings:
            self.missing_data_warnings = [
                "Search volume unavailable (Zero-fabricated-metrics policy enforced)",
                "Impression & CTR estimates are private YouTube creator analytics",
            ]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeoTitleCandidate:
    """Structured, editable YouTube video title option with SEO quality metrics."""

    title: str
    angle_category: str  # "Search-Focused", "Question-Based", "Problem-Solving", "Comparison (VS)", "Review & Buyer-Intent", "Curiosity & Value"
    character_count: int = 0
    truncation_risk: str = "Optimal (Mobile & Desktop)"
    primary_keyword_front_loaded: bool = False
    quality_score: float = 85.0
    is_clickbait_flagged: bool = False
    is_duplicated_in_channel: bool = False
    checklist: Dict[str, bool] = field(default_factory=dict)
    explanation: str = ""

    def __post_init__(self):
        self.character_count = len(self.title)
        if self.character_count <= 60:
            self.truncation_risk = "Optimal (Mobile & Desktop <60 chars)"
        elif self.character_count <= 75:
            self.truncation_risk = "Desktop Safe (<75 chars, may truncate on some mobile)"
        else:
            self.truncation_risk = "High Truncation Risk (>75 chars, title will truncate on mobile)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoDescriptionSection:
    """Section of a structured YouTube video description."""

    section_id: str
    title: str
    content: str
    is_required: bool = False
    help_text: str = ""


@dataclass
class VideoDescription:
    """Fully articulated YouTube Video Description for Description Studio (Phase 22 Part 5)."""

    channel_id: int
    channel_name: str
    topic: str
    primary_keyword: str
    supporting_keywords: List[str] = field(default_factory=list)
    target_audience: str = "General Audience"
    opening_hook: str = ""
    viewer_value: str = ""
    chapters: List[Dict[str, str]] = field(default_factory=list)  # [{"timestamp": "00:00", "label": "Introduction"}]
    resources_and_links: List[Dict[str, str]] = field(default_factory=list)  # [{"title": "Official Specs", "url": "..."}]
    affiliate_links: List[Dict[str, str]] = field(default_factory=list)  # [{"label": "Product A", "url": "...", "merchant": "..."}]
    affiliate_disclosure: str = ""
    calls_to_action: str = ""
    references_and_specs: str = ""
    channel_footer: str = ""
    full_text: str = ""
    character_count: int = 0
    max_characters: int = 5000
    has_affiliate_links: bool = False
    has_affiliate_disclosure: bool = False
    is_ftc_compliant: bool = True
    keyword_repetition_warnings: List[str] = field(default_factory=list)
    broken_url_warnings: List[str] = field(default_factory=list)
    quality_checklist: Dict[str, bool] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def assemble_full_text(self) -> str:
        """Assemble all sections into final YouTube description text."""
        parts = []

        # A. Opening
        if self.opening_hook.strip():
            parts.append(self.opening_hook.strip())

        # B. Viewer Value
        if self.viewer_value.strip():
            parts.append(self.viewer_value.strip())

        # C. Chapters
        if self.chapters:
            chap_lines = ["⏱️ CHAPTERS & TIMESTAMPS:"]
            for ch in self.chapters:
                ts = ch.get("timestamp", "").strip()
                lbl = ch.get("label", "").strip()
                if ts and lbl:
                    chap_lines.append(f"{ts} - {lbl}")
            if len(chap_lines) > 1:
                parts.append("\n".join(chap_lines))

        # D. Verified Resources
        if self.resources_and_links:
            res_lines = ["🔗 VERIFIED RESOURCES & LINKS:"]
            for r in self.resources_and_links:
                lbl = r.get("title", "").strip()
                url = r.get("url", "").strip()
                if lbl and url:
                    res_lines.append(f"• {lbl}: {url}")
            if len(res_lines) > 1:
                parts.append("\n".join(res_lines))

        # E. Affiliate Links & Disclosure
        if self.affiliate_links:
            aff_lines = ["🛒 PRODUCT & AFFILIATE LINKS:"]
            for a in self.affiliate_links:
                lbl = a.get("label", "").strip()
                url = a.get("url", "").strip()
                merch = a.get("merchant", "").strip()
                extra = f" ({merch})" if merch else ""
                if lbl and url:
                    aff_lines.append(f"• {lbl}{extra}: {url}")
            if self.affiliate_disclosure.strip():
                aff_lines.append(f"\n📢 AFFILIATE DISCLOSURE:\n{self.affiliate_disclosure.strip()}")
            parts.append("\n".join(aff_lines))

        # F. Calls to Action
        if self.calls_to_action.strip():
            parts.append(self.calls_to_action.strip())

        # G. References / Specs
        if self.references_and_specs.strip():
            parts.append(f"📋 TECHNICAL SPECIFICATIONS & NOTES:\n{self.references_and_specs.strip()}")

        # H. Channel Footer
        if self.channel_footer.strip():
            parts.append(f"---\n{self.channel_footer.strip()}")

        assembled = "\n\n".join(parts)
        self.full_text = assembled
        self.character_count = len(assembled)
        self.has_affiliate_links = bool(self.affiliate_links)
        self.has_affiliate_disclosure = bool(self.affiliate_disclosure.strip())
        self.is_ftc_compliant = (not self.has_affiliate_links) or self.has_affiliate_disclosure
        return assembled

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

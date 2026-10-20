"""Domain models for Phase 23: YouTube SEO Audit & Affiliate Content Quality Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditFindingSeverity(str, Enum):
    """Severity levels for audit findings."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    IMPROVEMENT = "IMPROVEMENT"
    POSITIVE = "POSITIVE"


class AuditStatus(str, Enum):
    """Status of specific audit sub-checks."""
    CHECKED = "CHECKED"
    NOT_CHECKED = "NOT CHECKED"
    NOT_APPLICABLE = "NOT APPLICABLE"


@dataclass
class AuditFinding:
    """An individual actionable finding from an audit category."""
    category: str
    severity: AuditFindingSeverity
    title: str
    message: str
    evidence_source: str = ""
    suggestion: str = ""
    is_objective: bool = True  # True if rule-based / deterministic, False if heuristic


@dataclass
class TitleQualityResult:
    """Evaluation results for proposed video title."""
    score: float
    findings: List[AuditFinding]
    character_count: int
    word_count: int
    truncation_risk: str  # "Safe (<60 chars)", "Moderate (60-75 chars)", "High Risk (>75 chars)"
    has_primary_keyword: bool
    keyword_position: str  # "Front (First 4 words)", "Middle/End", "Missing"
    intent_match: str
    alternatives: List[Dict[str, str]] = field(default_factory=list)
    similarity_flags: List[str] = field(default_factory=list)


@dataclass
class DescriptionQualityResult:
    """Evaluation results for draft video description."""
    score: float
    findings: List[AuditFinding]
    character_count: int
    has_hook: bool
    has_primary_keyword_hook: bool
    has_timestamps: bool
    timestamp_count: int
    has_ftc_disclosure: bool
    has_placeholders: bool
    link_count: int
    secondary_keywords_covered: List[str] = field(default_factory=list)
    secondary_keywords_missing: List[str] = field(default_factory=list)


@dataclass
class ScriptAlignmentResult:
    """Evaluation results for script, outline, or transcript."""
    status: AuditStatus
    score: Optional[float]
    findings: List[AuditFinding]
    promises_addressed: List[str] = field(default_factory=list)
    missing_promises: List[str] = field(default_factory=list)
    fluff_phrases_found: List[str] = field(default_factory=list)
    criteria_covered: List[str] = field(default_factory=list)
    unsupported_claims: List[str] = field(default_factory=list)


@dataclass
class AffiliateQualityResult:
    """Evaluation results for affiliate marketing content quality."""
    status: AuditStatus
    score: Optional[float]
    findings: List[AuditFinding]
    has_variant_specificity: bool
    has_balanced_pros_cons: bool
    has_price_freshness_notice: bool
    has_ftc_disclosure: bool
    unsupported_superlatives: List[str] = field(default_factory=list)
    unverified_facts: List[str] = field(default_factory=list)


@dataclass
class ThumbnailQualityResult:
    """Evaluation results for thumbnail concept."""
    concept_status: AuditStatus
    visual_inspection_status: AuditStatus
    score: float
    findings: List[AuditFinding]
    word_count: int
    character_count: int
    readability_assessment: str
    complements_title: bool
    potential_clickbait_flags: List[str] = field(default_factory=list)


@dataclass
class AuditScoreBreakdown:
    """Transparent SEO Readiness Score breakdown."""
    overall_readiness_score: float
    title_score: float
    description_score: float
    script_alignment_score: Optional[float]
    affiliate_quality_score: Optional[float]
    thumbnail_score: float
    deductions: List[Dict[str, Any]] = field(default_factory=list)
    checked_categories: List[str] = field(default_factory=list)
    not_checked_categories: List[str] = field(default_factory=list)
    not_applicable_categories: List[str] = field(default_factory=list)
    prioritized_actions: List[Dict[str, Any]] = field(default_factory=list)
    disclaimer: str = (
        "Readiness scores indicate adherence to YouTube SEO best practices, viewer-centric clarity, "
        "and FTC guidelines. Rankings and click-through rates cannot be guaranteed."
    )


@dataclass
class PublishingChecklistItem:
    """An item in the pre-publishing checklist requiring manual confirmation."""
    item_id: str
    label: str
    category: str
    is_completed: bool = False
    is_manual_required: bool = True
    help_text: str = ""


@dataclass
class VideoSeoAudit:
    """Full SEO Audit record for a video concept or published URL."""
    id: Optional[int]
    channel_id: int
    channel_name: str
    idea_id: Optional[int]
    primary_keyword: str
    secondary_keywords: List[str]
    proposed_title: str
    draft_description: str
    script_text: str
    thumbnail_concept: str
    video_url: str
    is_published_url: bool
    scores: AuditScoreBreakdown
    findings: List[AuditFinding]
    title_result: TitleQualityResult
    description_result: DescriptionQualityResult
    script_result: ScriptAlignmentResult
    affiliate_result: AffiliateQualityResult
    thumbnail_result: ThumbnailQualityResult
    checklist: List[PublishingChecklistItem]
    revision_number: int = 1
    created_at: str = ""
    updated_at: str = ""


@dataclass
class AuditRevision:
    """Snapshot of an audit revision for version comparison."""
    id: Optional[int]
    audit_id: int
    revision_number: int
    proposed_title: str
    draft_description: str
    script_text: str
    thumbnail_concept: str
    scores: Dict[str, Any]
    findings: List[Dict[str, Any]]
    notes: str = ""
    created_at: str = ""

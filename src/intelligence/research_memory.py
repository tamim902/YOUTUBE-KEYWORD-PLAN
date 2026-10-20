"""
Phase 34: Personal SEO Research Memory & Smart Recommendations Engine.

Provides:
1. Lightweight, evidence-based research memory per channel.
2. Duplicate research detection (exact & semantic similarity, staleness detection).
3. Personalized smart recommendations based on actual saved records.
4. User feedback collection (Useful, Not relevant, Already completed, Try again later).
5. Performance insights comparing selected vs published topics and self-reported ratings.
6. 4-channel isolation and strict epistemic modesty (no synthetic view/CTR claims).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import difflib
from enum import Enum
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager, db_manager

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Categorization of stored research memory items."""
    SEED_SEARCH = "seed_search"
    SAVED_TOPIC = "saved_topic"
    CONTENT_PACKAGE = "content_package"
    PUBLISHED_VIDEO = "published_video"
    REJECTED_IDEA = "rejected_idea"


class MemoryStatus(str, Enum):
    """Lifecycle status of a research memory item."""
    ACTIVE = "active"
    PUBLISHED = "published"
    REJECTED = "rejected"
    STALE = "stale"
    ARCHIVED = "archived"


class SimilarityType(str, Enum):
    """Type of duplicate or similarity match detected."""
    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILAR = "semantic_similar"
    SUBSTRING_MATCH = "substring_match"
    NO_MATCH = "no_match"


class FeedbackStatus(str, Enum):
    """User feedback classification for smart recommendations."""
    USEFUL = "useful"
    NOT_RELEVANT = "not_relevant"
    ALREADY_COMPLETED = "already_completed"
    TRY_AGAIN_LATER = "try_again_later"


class UserPerformanceRating(str, Enum):
    """Creator self-reported evaluation of published video performance."""
    EXCEEDED_EXPECTATIONS = "exceeded_expectations"
    MET_EXPECTATIONS = "met_expectations"
    UNDERPERFORMED = "underperformed"
    UNRATED = "unrated"


@dataclass
class MemoryRecord:
    """A persistent research memory entry for a specific channel."""
    channel_id: int
    topic_or_keyword: str
    memory_type: MemoryType = MemoryType.SEED_SEARCH
    source_provenance: str = "live_autocomplete"
    status: MemoryStatus = MemoryStatus.ACTIVE
    intent: str = "Informational"
    relevance_score: float = 0.0
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: str = ""
    user_performance_rating: str = ""
    published_video_url: str = ""
    published_date: str = ""
    research_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_reviewed_date: str = ""
    is_stale: bool = False
    id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to database-ready dictionary."""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "topic_or_keyword": self.topic_or_keyword,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, MemoryType) else str(self.memory_type),
            "source_provenance": self.source_provenance,
            "status": self.status.value if isinstance(self.status, MemoryStatus) else str(self.status),
            "intent": self.intent,
            "relevance_score": self.relevance_score,
            "evidence_summary": self.evidence_summary,
            "rejection_reason": self.rejection_reason,
            "user_performance_rating": self.user_performance_rating,
            "published_video_url": self.published_video_url,
            "published_date": self.published_date,
            "research_date": self.research_date,
            "last_reviewed_date": self.last_reviewed_date,
            "is_stale": self.is_stale,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        """Reconstruct record from dictionary safely."""
        m_type = data.get("memory_type", "seed_search")
        try:
            m_type_enum = MemoryType(m_type)
        except Exception:
            m_type_enum = MemoryType.SEED_SEARCH

        st = data.get("status", "active")
        try:
            st_enum = MemoryStatus(st)
        except Exception:
            st_enum = MemoryStatus.ACTIVE

        return cls(
            id=data.get("id"),
            channel_id=data.get("channel_id", 1),
            topic_or_keyword=data.get("topic_or_keyword", ""),
            memory_type=m_type_enum,
            source_provenance=data.get("source_provenance", "live_autocomplete"),
            status=st_enum,
            intent=data.get("intent", "Informational"),
            relevance_score=float(data.get("relevance_score", 0.0)),
            evidence_summary=data.get("evidence_summary") or {},
            rejection_reason=data.get("rejection_reason", ""),
            user_performance_rating=data.get("user_performance_rating", ""),
            published_video_url=data.get("published_video_url", ""),
            published_date=data.get("published_date", ""),
            research_date=data.get("research_date", ""),
            last_reviewed_date=data.get("last_reviewed_date", ""),
            is_stale=bool(data.get("is_stale", False)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class DuplicateMatch:
    """Duplicate research comparison result."""
    is_duplicate: bool
    similarity_type: SimilarityType
    similarity_score: float  # 0.0 to 1.0
    matched_topic: str
    matched_record_id: Optional[int] = None
    research_date: str = ""
    days_ago: int = 0
    is_stale: bool = False
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    suggested_action: str = ""  # "open_previous_research", "refresh_research", "none"

    def to_dict(self) -> Dict[str, Any]:
        """Convert match to dictionary."""
        return {
            "is_duplicate": self.is_duplicate,
            "similarity_type": self.similarity_type.value,
            "similarity_score": round(self.similarity_score, 2),
            "matched_topic": self.matched_topic,
            "matched_record_id": self.matched_record_id,
            "research_date": self.research_date,
            "days_ago": self.days_ago,
            "is_stale": self.is_stale,
            "evidence_summary": self.evidence_summary,
            "explanation": self.explanation,
            "suggested_action": self.suggested_action,
        }


@dataclass
class MemoryRecommendation:
    """Actionable recommendation derived from authentic channel research memory."""
    recommendation_key: str
    channel_id: int
    recommendation_type: str  # "unreviewed_topic", "missing_brief", "add_to_calendar", "stale_research_refresh", "seo_review_needed", "first_step"
    title: str
    topic: str
    why_suggested: str
    supporting_evidence: str
    next_action_label: str
    target_page: str
    target_params: Dict[str, Any] = field(default_factory=dict)
    priority_score: int = 50
    feedback_status: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary."""
        return {
            "recommendation_key": self.recommendation_key,
            "channel_id": self.channel_id,
            "recommendation_type": self.recommendation_type,
            "title": self.title,
            "topic": self.topic,
            "why_suggested": self.why_suggested,
            "supporting_evidence": self.supporting_evidence,
            "next_action_label": self.next_action_label,
            "target_page": self.target_page,
            "target_params": self.target_params,
            "priority_score": self.priority_score,
            "feedback_status": self.feedback_status,
            "created_at": self.created_at,
        }


@dataclass
class PerformanceInsightsSummary:
    """Channel performance metrics and research velocity summary."""
    channel_id: int
    channel_name: str
    total_topics_selected: int
    total_topics_published: int
    total_packages_created: int
    total_searches_run: int
    topics_over_time: Dict[str, int]
    user_ratings_breakdown: Dict[str, int]
    analytics_connected: bool
    analytics_explanation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "total_topics_selected": self.total_topics_selected,
            "total_topics_published": self.total_topics_published,
            "total_packages_created": self.total_packages_created,
            "total_searches_run": self.total_searches_run,
            "topics_over_time": self.topics_over_time,
            "user_ratings_breakdown": self.user_ratings_breakdown,
            "analytics_connected": self.analytics_connected,
            "analytics_explanation": self.analytics_explanation,
        }


# ==============================================================================
# Helper Functions for Text Normalization & Similarity
# ==============================================================================

def _normalize_tokens(text: str) -> Set[str]:
    """Tokenize and normalize text preserving Unicode/Bengali characters."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = {t.strip() for t in cleaned.split() if len(t.strip()) > 1}
    return tokens


def _compute_similarity(query_a: str, query_b: str) -> Tuple[SimilarityType, float]:
    """Compute deterministic similarity between two topic phrases."""
    clean_a = " ".join(query_a.lower().strip().split())
    clean_b = " ".join(query_b.lower().strip().split())

    if not clean_a or not clean_b:
        return SimilarityType.NO_MATCH, 0.0

    # 1. Exact Match
    if clean_a == clean_b:
        return SimilarityType.EXACT_MATCH, 1.0

    tokens_a = _normalize_tokens(clean_a)
    tokens_b = _normalize_tokens(clean_b)

    # 2. Token Jaccard Similarity
    jaccard = 0.0
    if tokens_a and tokens_b:
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        jaccard = len(intersection) / len(union) if union else 0.0

    # 3. SequenceMatcher Ratio
    seq_ratio = difflib.SequenceMatcher(None, clean_a, clean_b).ratio()

    # 4. Substring Containment
    is_substring = (clean_a in clean_b) or (clean_b in clean_a)

    if jaccard >= 0.70 or seq_ratio >= 0.80:
        return SimilarityType.SEMANTIC_SIMILAR, max(jaccard, seq_ratio)

    if is_substring and (len(clean_a) >= 6 and len(clean_b) >= 6):
        score = max(0.65, seq_ratio)
        return SimilarityType.SUBSTRING_MATCH, score

    if jaccard >= 0.45 or seq_ratio >= 0.65:
        score = max(jaccard, seq_ratio)
        return SimilarityType.SEMANTIC_SIMILAR, score

    return SimilarityType.NO_MATCH, max(jaccard, seq_ratio)


def _calculate_days_ago(date_str: str) -> int:
    """Calculate age in days from an ISO date string or YYYY-MM-DD date."""
    if not date_str:
        return 0
    now = datetime.now(timezone.utc)
    try:
        # Strip trailing Z and offset if needed
        clean_date = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        return max(0, delta.days)
    except Exception:
        try:
            # Fallback to YYYY-MM-DD format
            parts = date_str.split("T")[0].split("-")
            if len(parts) == 3:
                dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=timezone.utc)
                return max(0, (now - dt).days)
        except Exception:
            pass
    return 0


# ==============================================================================
# Research Memory Engine
# ==============================================================================

class ResearchMemoryEngine:
    """Coordinates channel-specific research memory, duplicate detection, and recommendations."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        chan_mgr: Optional[ChannelManager] = None,
        stale_threshold_days: int = 30,
    ) -> None:
        self.db = database or db_manager
        self.chan_mgr = chan_mgr or channel_manager
        self.stale_threshold_days = stale_threshold_days

    def check_duplicate_research(
        self, channel_id: int, query: str
    ) -> DuplicateMatch:
        """Search channel's saved research and return duplicate / similarity match details."""
        clean_q = query.strip()
        if not clean_q or len(clean_q) < 2:
            return DuplicateMatch(
                is_duplicate=False,
                similarity_type=SimilarityType.NO_MATCH,
                similarity_score=0.0,
                matched_topic="",
                explanation="Query is too short to check against research memory.",
            )

        # Retrieve existing memory records for this channel
        records = self.db.get_research_memory_records(channel_id=channel_id, limit=200)

        # If empty, run an initial sync from existing searches and packages
        if not records:
            self.db.sync_channel_research_memory(channel_id)
            records = self.db.get_research_memory_records(channel_id=channel_id, limit=200)

        best_match: Optional[Dict[str, Any]] = None
        best_type = SimilarityType.NO_MATCH
        best_score = 0.0

        for r in records:
            target_topic = r.get("topic_or_keyword", "")
            sim_type, score = _compute_similarity(clean_q, target_topic)

            if score > best_score:
                best_score = score
                best_type = sim_type
                best_match = r

        if best_match and best_score >= 0.55:
            matched_topic = best_match.get("topic_or_keyword", "")
            res_date = best_match.get("research_date", "")
            days_ago = _calculate_days_ago(res_date)
            is_stale = days_ago > self.stale_threshold_days
            rec_id = best_match.get("id")
            evidence = best_match.get("evidence_summary", {})

            # Plain-English explanation
            if best_type == SimilarityType.EXACT_MATCH:
                if is_stale:
                    explanation = (
                        f"Exact previous research found for '{matched_topic}' from {days_ago} days ago. "
                        f"Because this research is over {self.stale_threshold_days} days old, YouTube search demand may have evolved. "
                        f"You can review previous findings or run a fresh research query below."
                    )
                    suggested_action = "refresh_research"
                else:
                    explanation = (
                        f"You previously researched this exact topic '{matched_topic}' {days_ago} days ago. "
                        f"Saved autocomplete results and packages are readily available."
                    )
                    suggested_action = "open_previous_research"
            else:
                if is_stale:
                    explanation = (
                        f"Similar previous topic '{matched_topic}' was researched {days_ago} days ago ({round(best_score * 100)}% match). "
                        f"Existing evidence is older than {self.stale_threshold_days} days. Running fresh research will capture new trends."
                    )
                    suggested_action = "refresh_research"
                else:
                    explanation = (
                        f"Found semantically similar previous topic '{matched_topic}' researched {days_ago} days ago ({round(best_score * 100)}% match). "
                        f"You can build on that research or continue with this new specific angle."
                    )
                    suggested_action = "open_previous_research"

            return DuplicateMatch(
                is_duplicate=True,
                similarity_type=best_type,
                similarity_score=best_score,
                matched_topic=matched_topic,
                matched_record_id=rec_id,
                research_date=res_date,
                days_ago=days_ago,
                is_stale=is_stale,
                evidence_summary=evidence,
                explanation=explanation,
                suggested_action=suggested_action,
            )

        # No duplicate detected
        return DuplicateMatch(
            is_duplicate=False,
            similarity_type=SimilarityType.NO_MATCH,
            similarity_score=best_score,
            matched_topic="",
            explanation="No duplicate research found in this channel's memory. This is a fresh topic exploration.",
            suggested_action="none",
        )

    def generate_smart_recommendations(
        self, channel_id: int, max_recommendations: int = 5
    ) -> List[MemoryRecommendation]:
        """Generate evidence-grounded next action recommendations using real channel history."""
        channel = self.chan_mgr.get_channel(channel_id)
        c_name = channel.channel_name if channel else f"Channel {channel_id}"

        # Sync memory if not populated
        self.db.sync_channel_research_memory(channel_id)

        # Retrieve user feedback to suppress or prioritize items
        feedback_map = self.db.get_recommendation_feedback(channel_id)

        recommendations: List[MemoryRecommendation] = []

        # ----------------------------------------------------------------------
        # 1. Check for Unreviewed Morning Gap Ideas (Rule 1)
        # ----------------------------------------------------------------------
        ideas = self.db.get_daily_ideas_by_channel(channel_id, limit=30)
        unreviewed_ideas = [
            i for i in ideas
            if getattr(i, "is_saved", False) and not getattr(i, "is_rejected", False)
        ]
        # Check if already has a package
        packages = self.db.get_video_content_packages(channel_id=channel_id, limit=50)
        packaged_topics = {p.get("topic", "").lower().strip() for p in packages}

        for item in unreviewed_ideas:
            t = getattr(item, "proposed_topic", "")
            if t.lower().strip() not in packaged_topics:
                r_key = f"gap_idea_{item.id}_{t[:20].lower().replace(' ', '_')}"
                if self._is_suppressed(r_key, feedback_map):
                    continue

                recommendations.append(
                    MemoryRecommendation(
                        recommendation_key=r_key,
                        channel_id=channel_id,
                        recommendation_type="unreviewed_topic",
                        title=f"Prepare Video Package: {t}",
                        topic=t,
                        why_suggested=(
                            f"You saved this opportunity from morning competitor gap analysis. "
                            f"It matches your '{getattr(item, 'pillar_name', 'Core')}' content pillar."
                        ),
                        supporting_evidence=(
                            f"Discovered in Morning Report #{item.report_id}. "
                            f"Primary Keyword: `{getattr(item, 'primary_keyword', t)}`"
                        ),
                        next_action_label="Draft One-Click Video Package",
                        target_page="Description & Metadata Studio",
                        target_params={"topic": t, "keyword": getattr(item, "primary_keyword", t)},
                        priority_score=90,
                        feedback_status=self._get_feedback_status(r_key, feedback_map),
                    )
                )

        # ----------------------------------------------------------------------
        # 2. Check for Completed Packages Missing Calendar Date (Rule 2)
        # ----------------------------------------------------------------------
        for pkg in packages:
            if not pkg.get("calendar_item_id"):
                t = pkg.get("topic", "")
                pkg_id = pkg.get("id")
                r_key = f"schedule_pkg_{pkg_id}"
                if self._is_suppressed(r_key, feedback_map):
                    continue

                recommendations.append(
                    MemoryRecommendation(
                        recommendation_key=r_key,
                        channel_id=channel_id,
                        recommendation_type="add_to_calendar",
                        title=f"Schedule Recording Date: {t}",
                        topic=t,
                        why_suggested=(
                            f"A full 6-part video package is ready for '{t}', but it is not yet on your production calendar."
                        ),
                        supporting_evidence=(
                            f"Video Content Package #{pkg_id} ({pkg.get('format_type', 'long-form')}) created on "
                            f"{pkg.get('created_at', '')[:10]}."
                        ),
                        next_action_label="Add to Content Calendar",
                        target_page="Strategy & Calendar",
                        target_params={"package_id": pkg_id, "topic": t},
                        priority_score=85,
                        feedback_status=self._get_feedback_status(r_key, feedback_map),
                    )
                )

        # ----------------------------------------------------------------------
        # 3. Check for Content Packages Needing SEO Review (Rule 3)
        # ----------------------------------------------------------------------
        for pkg in packages:
            seo_checks = pkg.get("seo_readiness", [])
            needs_review = [
                c.get("item_name") for c in seo_checks
                if c.get("status") in ("NEEDS_REVIEW", "Needs Review")
            ]
            if needs_review:
                t = pkg.get("topic", "")
                pkg_id = pkg.get("id")
                r_key = f"seo_review_pkg_{pkg_id}"
                if self._is_suppressed(r_key, feedback_map):
                    continue

                recommendations.append(
                    MemoryRecommendation(
                        recommendation_key=r_key,
                        channel_id=channel_id,
                        recommendation_type="seo_review_needed",
                        title=f"Resolve SEO Readiness Checklist: {t}",
                        topic=t,
                        why_suggested=(
                            f"Package #{pkg_id} has {len(needs_review)} item(s) flagged for review: {', '.join(needs_review[:2])}."
                        ),
                        supporting_evidence="SEO Readiness Audit evaluated pre-publish title length or keyword placement.",
                        next_action_label="Review & Polish Package",
                        target_page="Description & Metadata Studio",
                        target_params={"package_id": pkg_id, "topic": t},
                        priority_score=75,
                        feedback_status=self._get_feedback_status(r_key, feedback_map),
                    )
                )

        # ----------------------------------------------------------------------
        # 4. Check for Stale Research Requiring Re-Check (Rule 4)
        # ----------------------------------------------------------------------
        memory_records = self.db.get_research_memory_records(channel_id=channel_id, limit=50)
        for rec in memory_records:
            res_date = rec.get("research_date", "")
            days_ago = _calculate_days_ago(res_date)
            t = rec.get("topic_or_keyword", "")
            rec_id = rec.get("id")

            if days_ago > self.stale_threshold_days and rec.get("status") == "active":
                r_key = f"stale_refresh_{rec_id}"
                if self._is_suppressed(r_key, feedback_map):
                    continue

                recommendations.append(
                    MemoryRecommendation(
                        recommendation_key=r_key,
                        channel_id=channel_id,
                        recommendation_type="stale_research_refresh",
                        title=f"Refresh Search Demand: {t}",
                        topic=t,
                        why_suggested=(
                            f"Researched {days_ago} days ago. Autocomplete predictions change as seasonal and search trends shift."
                        ),
                        supporting_evidence=f"Researched on {res_date[:10]} ({days_ago} days ago).",
                        next_action_label="Run Fresh Autocomplete Search",
                        target_page="New Keyword Research",
                        target_params={"keyword": t},
                        priority_score=60,
                        feedback_status=self._get_feedback_status(r_key, feedback_map),
                    )
                )

        # ----------------------------------------------------------------------
        # 5. Beginner First Step Fallback (When History is Empty or All Completed)
        # ----------------------------------------------------------------------
        if not recommendations:
            first_step_key = f"first_step_ch_{channel_id}"
            niche = channel.channel_niche if channel else "YouTube Content"
            recommendations.append(
                MemoryRecommendation(
                    recommendation_key=first_step_key,
                    channel_id=channel_id,
                    recommendation_type="first_step",
                    title=f"Launch First Keyword Discovery for {c_name}",
                    topic=f"{niche} trending questions",
                    why_suggested=(
                        f"Your research memory for {c_name} is fresh. "
                        f"Discover what real viewers are searching for in {niche} to populate your idea library."
                    ),
                    supporting_evidence=f"Channel Profile: {niche} (Audience: {getattr(channel, 'target_audience', 'Creators')}).",
                    next_action_label="Start Keyword Research",
                    target_page="New Keyword Research",
                    target_params={"seed": niche.split("&")[0].strip()},
                    priority_score=100,
                    feedback_status=self._get_feedback_status(first_step_key, feedback_map),
                )
            )

        # Sort recommendations by priority score (descending)
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        return recommendations[:max_recommendations]

    def _is_suppressed(self, r_key: str, feedback_map: Dict[str, Dict[str, Any]]) -> bool:
        """Check whether user feedback marked this item as not relevant or completed."""
        fb = feedback_map.get(r_key)
        if not fb:
            return False
        st = fb.get("feedback_status")
        return st in (FeedbackStatus.NOT_RELEVANT.value, FeedbackStatus.ALREADY_COMPLETED.value)

    def _get_feedback_status(self, r_key: str, feedback_map: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Get the active feedback status string if present."""
        fb = feedback_map.get(r_key)
        return fb.get("feedback_status") if fb else None

    def record_recommendation_feedback(
        self,
        channel_id: int,
        recommendation_key: str,
        recommendation_type: str,
        status: FeedbackStatus,
        reason: str = "",
    ) -> bool:
        """Record explicit user feedback for a recommendation."""
        return self.db.save_recommendation_feedback(
            channel_id=channel_id,
            recommendation_key=recommendation_key,
            recommendation_type=recommendation_type,
            feedback_status=status.value if isinstance(status, FeedbackStatus) else str(status),
            reason=reason,
        )

    def record_topic_published(
        self,
        channel_id: int,
        topic: str,
        video_url: str = "",
        user_rating: str = "",
    ) -> bool:
        """Explicitly record a topic as published with optional creator performance rating."""
        now = datetime.now(timezone.utc).isoformat()
        rec = MemoryRecord(
            channel_id=channel_id,
            topic_or_keyword=topic,
            memory_type=MemoryType.PUBLISHED_VIDEO,
            source_provenance="user_input",
            status=MemoryStatus.PUBLISHED,
            user_performance_rating=user_rating or UserPerformanceRating.UNRATED.value,
            published_video_url=video_url,
            published_date=now[:10],
            research_date=now,
        )
        self.db.save_research_memory_record(rec)
        return True

    def get_performance_insights(self, channel_id: int) -> PerformanceInsightsSummary:
        """Compile evidence-grounded performance insights comparing selected vs published topics."""
        channel = self.chan_mgr.get_channel(channel_id)
        c_name = channel.channel_name if channel else f"Channel {channel_id}"

        # Sync existing data into memory
        self.db.sync_channel_research_memory(channel_id)
        records = self.db.get_research_memory_records(channel_id=channel_id, limit=300)

        total_selected = sum(
            1 for r in records if r.get("memory_type") in ("saved_topic", "content_package", "published_video")
        )
        total_published = sum(
            1 for r in records if r.get("status") == "published" or r.get("memory_type") == "published_video"
        )
        total_packages = sum(
            1 for r in records if r.get("memory_type") == "content_package"
        )
        total_searches = sum(
            1 for r in records if r.get("memory_type") == "seed_search"
        )

        # Time distributions
        now = datetime.now(timezone.utc)
        last_7_days = sum(1 for r in records if _calculate_days_ago(r.get("research_date", "")) <= 7)
        last_30_days = sum(1 for r in records if _calculate_days_ago(r.get("research_date", "")) <= 30)

        # User ratings breakdown
        ratings_breakdown = {
            "exceeded_expectations": 0,
            "met_expectations": 0,
            "underperformed": 0,
            "unrated": 0,
        }
        for r in records:
            rating = r.get("user_performance_rating", "")
            if rating in ratings_breakdown:
                ratings_breakdown[rating] += 1
            elif r.get("status") == "published":
                ratings_breakdown["unrated"] += 1

        # Transparent analytics status
        analytics_connected = False
        try:
            creds = self.db.get_channel_credentials(channel_id)
            analytics_connected = bool(creds and getattr(creds, "is_authorized", False))
        except Exception:
            analytics_connected = False

        if analytics_connected:
            explanation = "Connected to verified YouTube Analytics API data."
        else:
            explanation = (
                "YouTube Analytics OAuth is not configured. "
                "Performance tracking uses verified creator logs, calendar records, "
                "and self-reported performance ratings without synthetic view estimates."
            )

        return PerformanceInsightsSummary(
            channel_id=channel_id,
            channel_name=c_name,
            total_topics_selected=total_selected,
            total_topics_published=total_published,
            total_packages_created=total_packages,
            total_searches_run=total_searches,
            topics_over_time={
                "past_7_days": last_7_days,
                "past_30_days": last_30_days,
                "all_time": len(records),
            },
            user_ratings_breakdown=ratings_breakdown,
            analytics_connected=analytics_connected,
            analytics_explanation=explanation,
        )

    def clear_memory_record(self, record_id: int, channel_id: int) -> bool:
        """Delete an individual research record for a specific channel."""
        return self.db.delete_research_memory_record(record_id=record_id, channel_id=channel_id)


# Default singleton instance
research_memory_engine = ResearchMemoryEngine()

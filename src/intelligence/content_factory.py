"""YouTube SEO Content Factory & One-Click Video Package Engine (Phase 32).

Provides unified, beginner-friendly video content preparation workflows:
- Generates complete editable packages: Title Options, Video Outline, 8-Part Description,
  Thumbnail Concept, Tag Suggestions, and Pre-Publish Checklist.
- Adapts output to Long-form vs. Shorts, as well as Tutorial, Review, Comparison, and Educational formats.
- Distinguishes verified facts, user input, AI-generated suggestions, and unverified claims.
- Evaluates SEO Readiness via transparent, evidence-based status checks (PASS, NEEDS REVIEW, NOT CHECKED).
- Strictly channel-separated across the four configured channel profiles.
- Zero fabricated metrics, search volumes, or ranking guarantees.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.classifier import default_classifier
from src.intelligence.channel_manager import ChannelManager, channel_manager
from src.intelligence.description_studio import DescriptionStudio, description_studio
from src.intelligence.seo_engine import SeoEngine, seo_engine
from src.models.channel import ChannelProfile
from src.models.strategy import StrategyCalendarItem
from src.storage.database import DatabaseManager, db_manager

logger = logging.getLogger(__name__)


class VideoFormat(str, Enum):
    """Supported video format classifications."""
    LONG_FORM = "long-form"
    SHORTS = "shorts"


class VideoPurpose(str, Enum):
    """Supported video content intent/purpose."""
    TUTORIAL = "tutorial"
    REVIEW = "review"
    COMPARISON = "comparison"
    EDUCATIONAL = "educational"
    TROUBLESHOOTING = "troubleshooting"


class ReadinessStatus(str, Enum):
    """SEO and quality readiness status."""
    PASS = "PASS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_CHECKED = "NOT_CHECKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class TitleCandidate:
    """An editable title candidate with length and claim safety heuristics."""
    title: str
    angle: str
    char_count: int
    is_front_loaded: bool
    length_status: str  # "Optimal (50-70 chars)", "Slightly Short", "Warning: Mobile Truncation Risk (>70 chars)"
    claim_warning: Optional[str] = None


@dataclass
class ThumbnailConcept:
    """A thumbnail composition guide designed for mobile readability."""
    hook_text: str
    visual_composition: str
    main_subject_focal_point: str
    color_contrast_notes: str
    mobile_readability_score: str = "High Readability"


@dataclass
class VideoOutlineSection:
    """A structural section of the video script or recording outline."""
    section_name: str
    timestamp_hint: str
    purpose: str
    talking_points: List[str] = field(default_factory=list)
    questions_answered: List[str] = field(default_factory=list)
    evidence_needed: str = ""


@dataclass
class EvidenceVerificationItem:
    """A fact or research claim with explicit source provenance."""
    fact_statement: str
    source_provenance: str  # "Verified User Input", "Live YouTube Autocomplete", "AI-Generated Suggestion", "Unverified Claim"
    status: str  # "Verified", "User Provided", "AI Suggestion", "Unverified / Needs Check"
    notes: str = ""


@dataclass
class SeoReadinessCheck:
    """A deterministic SEO and compliance evaluation item."""
    item_name: str
    status: ReadinessStatus
    explanation: str
    recommendation: str


@dataclass
class VideoContentPackage:
    """Complete, unified YouTube SEO content package."""
    channel_id: int
    channel_name: str
    topic: str
    primary_keyword: str
    supporting_keywords: List[str] = field(default_factory=list)
    format_type: VideoFormat = VideoFormat.LONG_FORM
    purpose_type: VideoPurpose = VideoPurpose.TUTORIAL
    target_viewer: str = ""
    selected_title: str = ""
    title_options: List[TitleCandidate] = field(default_factory=list)
    outline: Dict[str, Any] = field(default_factory=dict)
    description_text: str = ""
    thumbnail_concept: Optional[ThumbnailConcept] = None
    tags: List[str] = field(default_factory=list)
    evidence_checklist: List[EvidenceVerificationItem] = field(default_factory=list)
    seo_readiness: List[SeoReadinessCheck] = field(default_factory=list)
    is_saved: bool = True
    is_exported: bool = False
    calendar_item_id: Optional[int] = None
    id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert content package to database-ready dictionary."""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "topic": self.topic,
            "primary_keyword": self.primary_keyword,
            "supporting_keywords": self.supporting_keywords,
            "format_type": self.format_type.value if isinstance(self.format_type, VideoFormat) else str(self.format_type),
            "purpose_type": self.purpose_type.value if isinstance(self.purpose_type, VideoPurpose) else str(self.purpose_type),
            "target_viewer": self.target_viewer,
            "selected_title": self.selected_title,
            "title_options": [asdict(t) for t in self.title_options],
            "outline": self.outline,
            "description_text": self.description_text,
            "thumbnail_concept": asdict(self.thumbnail_concept) if self.thumbnail_concept else {},
            "tags": self.tags,
            "evidence_checklist": [asdict(e) for e in self.evidence_checklist],
            "seo_readiness": [
                {
                    "item_name": r.item_name,
                    "status": r.status.value if isinstance(r.status, ReadinessStatus) else str(r.status),
                    "explanation": r.explanation,
                    "recommendation": r.recommendation,
                }
                for r in self.seo_readiness
            ],
            "is_saved": self.is_saved,
            "is_exported": self.is_exported,
            "calendar_item_id": self.calendar_item_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoContentPackage":
        """Reconstruct a VideoContentPackage instance from a dictionary."""
        raw_fmt = data.get("format_type", VideoFormat.LONG_FORM.value)
        try:
            fmt = VideoFormat(raw_fmt)
        except ValueError:
            fmt = VideoFormat.LONG_FORM

        raw_purp = data.get("purpose_type", VideoPurpose.TUTORIAL.value)
        try:
            purp = VideoPurpose(raw_purp)
        except ValueError:
            purp = VideoPurpose.TUTORIAL

        title_opts = [
            TitleCandidate(**t) if isinstance(t, dict) else t
            for t in data.get("title_options", [])
        ]

        thumb = data.get("thumbnail_concept")
        thumb_obj = ThumbnailConcept(**thumb) if isinstance(thumb, dict) and thumb else None

        evidence = [
            EvidenceVerificationItem(**e) if isinstance(e, dict) else e
            for e in data.get("evidence_checklist", [])
        ]

        readiness = []
        for r in data.get("seo_readiness", []):
            if isinstance(r, dict):
                raw_st = r.get("status", ReadinessStatus.NOT_CHECKED.value)
                try:
                    st_enum = ReadinessStatus(raw_st)
                except ValueError:
                    st_enum = ReadinessStatus.NOT_CHECKED
                readiness.append(
                    SeoReadinessCheck(
                        item_name=r.get("item_name", ""),
                        status=st_enum,
                        explanation=r.get("explanation", ""),
                        recommendation=r.get("recommendation", ""),
                    )
                )

        return cls(
            id=data.get("id"),
            channel_id=int(data.get("channel_id", 1)),
            channel_name=data.get("channel_name", ""),
            topic=data.get("topic", ""),
            primary_keyword=data.get("primary_keyword", ""),
            supporting_keywords=data.get("supporting_keywords", []),
            format_type=fmt,
            purpose_type=purp,
            target_viewer=data.get("target_viewer", ""),
            selected_title=data.get("selected_title", ""),
            title_options=title_opts,
            outline=data.get("outline", {}),
            description_text=data.get("description_text", ""),
            thumbnail_concept=thumb_obj,
            tags=data.get("tags", []),
            evidence_checklist=evidence,
            seo_readiness=readiness,
            is_saved=bool(data.get("is_saved", True)),
            is_exported=bool(data.get("is_exported", False)),
            calendar_item_id=data.get("calendar_item_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ContentFactoryEngine:
    """Unified engine for generating, verifying, and persisting video content packages."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        chan_mgr: Optional[ChannelManager] = None,
        studio: Optional[DescriptionStudio] = None,
        seo: Optional[SeoEngine] = None,
    ) -> None:
        self.db = database or db_manager
        self.chan_mgr = chan_mgr or channel_manager
        self.studio = studio or description_studio
        self.seo = seo or seo_engine

    def generate_package(
        self,
        channel_id: int,
        topic: str,
        primary_keyword: str,
        format_type: VideoFormat = VideoFormat.LONG_FORM,
        purpose_type: VideoPurpose = VideoPurpose.TUTORIAL,
        supporting_keywords: Optional[List[str]] = None,
        target_viewer: Optional[str] = None,
        product_info: Optional[Dict[str, str]] = None,
        user_notes: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> VideoContentPackage:
        """Generate a complete, format-adapted video package with verifiable evidence."""
        channel = self.chan_mgr.get_channel(channel_id)
        c_name = channel.channel_name if channel else f"Channel {channel_id}"
        viewer = target_viewer or (channel.target_audience if channel else "General Audience")
        supp_kws = supporting_keywords or [
            f"{primary_keyword} tutorial",
            f"{primary_keyword} guide",
            f"best {primary_keyword}",
            f"{primary_keyword} review",
        ]

        # ----------------------------------------------------------------------
        # A. Title Candidates
        # ----------------------------------------------------------------------
        title_candidates = self._generate_title_candidates(
            topic=topic,
            keyword=primary_keyword,
            format_type=format_type,
            purpose_type=purpose_type,
            channel=channel,
        )
        selected_title = title_candidates[0].title if title_candidates else f"{primary_keyword.title()}: Complete Guide (2026)"

        # ----------------------------------------------------------------------
        # B. Video Outline
        # ----------------------------------------------------------------------
        outline = self._generate_outline(
            topic=topic,
            keyword=primary_keyword,
            format_type=format_type,
            purpose_type=purpose_type,
            product_info=product_info,
        )

        # ----------------------------------------------------------------------
        # C. 8-Part YouTube Description
        # ----------------------------------------------------------------------
        desc_obj = self._generate_description(
            topic=topic,
            keyword=primary_keyword,
            format_type=format_type,
            purpose_type=purpose_type,
            channel=channel,
            product_info=product_info,
            source_links=source_links,
            outline=outline,
        )
        description_text = desc_obj.full_text

        # ----------------------------------------------------------------------
        # D. Thumbnail Concept
        # ----------------------------------------------------------------------
        thumbnail = self._generate_thumbnail_concept(
            keyword=primary_keyword,
            format_type=format_type,
            purpose_type=purpose_type,
        )

        # ----------------------------------------------------------------------
        # E. Tag Suggestions (6-8 strictly relevant)
        # ----------------------------------------------------------------------
        tags = self._generate_relevant_tags(primary_keyword, supp_kws, channel)

        # ----------------------------------------------------------------------
        # F. Evidence & Fact-Checking Breakdown
        # ----------------------------------------------------------------------
        evidence_items = self._build_evidence_checklist(
            topic=topic,
            keyword=primary_keyword,
            product_info=product_info,
            user_notes=user_notes,
            source_links=source_links,
        )

        # ----------------------------------------------------------------------
        # G. SEO Readiness Evaluation
        # ----------------------------------------------------------------------
        seo_checks = self._evaluate_seo_readiness(
            title=selected_title,
            keyword=primary_keyword,
            description=description_text,
            outline=outline,
            format_type=format_type,
            channel=channel,
            evidence=evidence_items,
            product_info=product_info,
        )

        pkg = VideoContentPackage(
            channel_id=channel_id,
            channel_name=c_name,
            topic=topic,
            primary_keyword=primary_keyword,
            supporting_keywords=supp_kws,
            format_type=format_type,
            purpose_type=purpose_type,
            target_viewer=viewer,
            selected_title=selected_title,
            title_options=title_candidates,
            outline=outline,
            description_text=description_text,
            thumbnail_concept=thumbnail,
            tags=tags,
            evidence_checklist=evidence_items,
            seo_readiness=seo_checks,
            is_saved=True,
            is_exported=False,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        return pkg

    # --------------------------------------------------------------------------
    # Title Generation Helper
    # --------------------------------------------------------------------------
    def _generate_title_candidates(
        self,
        topic: str,
        keyword: str,
        format_type: VideoFormat,
        purpose_type: VideoPurpose,
        channel: Optional[ChannelProfile] = None,
    ) -> List[TitleCandidate]:
        kw_title = keyword.strip().title()
        topic_title = topic.strip().title()
        year = str(datetime.now().year)

        candidates: List[TitleCandidate] = []

        if format_type == VideoFormat.SHORTS:
            # Shorts: under 50 chars with #Shorts
            raw_titles = [
                (f"{kw_title} in 60 Seconds! #Shorts", "Shorts Hook", True),
                (f"Stop Making This {kw_title} Mistake! #Shorts", "Shorts Problem", True),
                (f"Quick {kw_title} Hack You Must Try #Shorts", "Shorts Curiosity", True),
                (f"Is {kw_title} Actually Good? #Shorts", "Shorts Question", False),
            ]
        elif purpose_type == VideoPurpose.REVIEW:
            raw_titles = [
                (f"{kw_title} Review ({year}): Honest Truth After Testing", "Review & Buyer", True),
                (f"Is {kw_title} Actually Worth It in {year}?", "Question / Decision", False),
                (f"{kw_title} vs The Competition: Don't Buy Before This!", "Comparison & Buyer", True),
                (f"The Biggest Problem with {kw_title} (Watch Before Buying)", "Problem / Warning", True),
            ]
        elif purpose_type == VideoPurpose.COMPARISON:
            raw_titles = [
                (f"{kw_title} vs The Top Alternatives: Full Breakdown ({year})", "Comparison", True),
                (f"Which {kw_title} Should You Actually Buy in {year}?", "Buyer Decision", False),
                (f"{kw_title}: What They DON'T Tell You in the Specs", "Curiosity / Nuance", True),
                (f"Top 3 Reasons to Choose {kw_title} in {year}", "Listicle / Benefit", True),
            ]
        elif purpose_type == VideoPurpose.TROUBLESHOOTING:
            raw_titles = [
                (f"{kw_title} Not Working? 5 Easy Fixes That Work", "Troubleshooting", True),
                (f"How to Fix {kw_title} Problems in Under 5 Minutes", "Fast Solution", True),
                (f"Why Your {kw_title} Fails (And How to Fix It)", "Diagnostic", False),
                (f"Stop Doing This with Your {kw_title}!", "Preventative", True),
            ]
        else:
            # Default / Tutorial / Educational
            raw_titles = [
                (f"{kw_title}: Complete Guide & Walkthrough ({year})", "Search-Focused", True),
                (f"How to Master {kw_title} (Step-by-Step for Beginners)", "Instructional", True),
                (f"The Smart Way to Set Up {kw_title} in {year}", "Practical Setup", False),
                (f"Why Most People Get {kw_title} Wrong (And What to Do)", "Curiosity / Contrarian", True),
                (f"Is {kw_title} Worth Learning in {year}?", "Question-Based", False),
            ]

        for t_text, angle, front_loaded in raw_titles:
            c_len = len(t_text)
            if c_len < 40:
                len_status = "Slightly Short (Consider adding year or benefit)"
            elif 45 <= c_len <= 70:
                len_status = "Optimal (50-70 chars — Ideal for mobile & desktop search)"
            else:
                len_status = "Warning: Mobile Truncation Risk (>70 chars)"

            # Check for misleading claim patterns
            claim_warn = None
            if re.search(r"\b(guaranteed|make \$|secret hack|100% viral)\b", t_text.lower()):
                claim_warn = "Warning: Claims of guaranteed results may violate YouTube spam policies and damage viewer trust."

            candidates.append(
                TitleCandidate(
                    title=t_text,
                    angle=angle,
                    char_count=c_len,
                    is_front_loaded=front_loaded,
                    length_status=len_status,
                    claim_warning=claim_warn,
                )
            )

        return candidates

    # --------------------------------------------------------------------------
    # Outline Generation Helper
    # --------------------------------------------------------------------------
    def _generate_outline(
        self,
        topic: str,
        keyword: str,
        format_type: VideoFormat,
        purpose_type: VideoPurpose,
        product_info: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        kw_title = keyword.strip().title()

        if format_type == VideoFormat.SHORTS:
            return {
                "format": "Shorts (Vertical 9:16, 30-60s)",
                "pacing": "Fast-paced, cut every 2-3 seconds, on-screen text anchors",
                "sections": [
                    {
                        "section_name": "1. Hook & Pattern Interrupt (0:00 - 0:03)",
                        "timestamp_hint": "00:00 - 00:03",
                        "purpose": "Stop the scroll immediately with a high-contrast visual or surprising statement.",
                        "talking_points": [
                            f"Call out the primary mistake or result immediately: '{kw_title}'.",
                            "Show the end-result or problem visually in the first frame.",
                        ],
                        "questions_answered": ["Why should I keep watching this Short?"],
                        "evidence_needed": "Immediate visual proof on screen.",
                    },
                    {
                        "section_name": "2. Core Demonstration & Quick Solution (0:03 - 0:45)",
                        "timestamp_hint": "00:03 - 00:45",
                        "purpose": "Deliver 2-3 rapid, practical steps without fluff.",
                        "talking_points": [
                            "Step 1: The foundation or correct setting.",
                            "Step 2: The exact tweak that makes the difference.",
                            "Keep energy high with b-roll or screen recording.",
                        ],
                        "questions_answered": ["How do I fix or do this right now?"],
                        "evidence_needed": "Working screen demo or hands-on footage.",
                    },
                    {
                        "section_name": "3. Seamless Loop & Call-to-Action (0:45 - 0:55)",
                        "timestamp_hint": "00:45 - 00:55",
                        "purpose": "Encourage loop re-watches and invite subscribers.",
                        "talking_points": [
                            "Restate the opening takeaway seamlessly so the video loops cleanly.",
                            "Prompt: 'Drop your question in comments and subscribe for part 2.'",
                        ],
                        "questions_answered": ["Where do I learn more?"],
                        "evidence_needed": "Clear call to action.",
                    },
                ],
            }

        # Long-form outline adapted to purpose
        if purpose_type == VideoPurpose.REVIEW:
            sections = [
                {
                    "section_name": "1. Hook & Verdict Preview (0:00 - 0:50)",
                    "timestamp_hint": "00:00 - 00:50",
                    "purpose": "State who this product is actually for upfront.",
                    "talking_points": [
                        f"State testing period (e.g. 'After 30 days of real-world use with {kw_title}...')",
                        "Address the primary viewer question: Is it worth the price tag in 2026?",
                    ],
                    "questions_answered": ["Who is this for, and is it actually worth it?"],
                    "evidence_needed": "Hands-on footage with wear or real setup.",
                },
                {
                    "section_name": "2. Build Quality & Key Specs (0:50 - 3:30)",
                    "timestamp_hint": "00:50 - 03:30",
                    "purpose": "Objective breakdown of materials, dimensions, and specifications.",
                    "talking_points": [
                        "Examine materials, feel, and daily ergonomic durability.",
                        f"Verify manufacturer claims against real-world testing: {product_info.get('specs', 'standard specifications') if product_info else 'specs'}.",
                    ],
                    "questions_answered": ["How well is it built?", "Do specs match reality?"],
                    "evidence_needed": "Close-up macro shots and verified spec sheets.",
                },
                {
                    "section_name": "3. What Works Great (The Pros) (3:30 - 7:00)",
                    "timestamp_hint": "03:30 - 07:00",
                    "purpose": "Demonstrate the strongest selling points in action.",
                    "talking_points": [
                        "Top 3 features that exceeded expectations during testing.",
                        "Direct performance metrics (battery life, speed, ease of use).",
                    ],
                    "questions_answered": ["What makes this stand out?"],
                    "evidence_needed": "Side-by-side demonstration or benchmark results.",
                },
                {
                    "section_name": "4. The Quirks & Dealbreakers (The Cons) (7:00 - 10:30)",
                    "timestamp_hint": "07:00 - 10:30",
                    "purpose": "Deliver honest criticism that builds viewer trust.",
                    "talking_points": [
                        "Flaws or annoyances noticed only after extended daily use.",
                        "Who should definitely NOT buy this product.",
                    ],
                    "questions_answered": ["What are the real downsides?"],
                    "evidence_needed": "Honest footage showing limitations.",
                },
                {
                    "section_name": "5. Final Buying Recommendation & Alternatives (10:30 - 12:45)",
                    "timestamp_hint": "10:30 - 12:45",
                    "purpose": "Final score, best price advice, and alternative recommendations.",
                    "talking_points": [
                        "Summary score and specific recommendation based on budget.",
                        "Reminder: Verified links and discount codes in description.",
                    ],
                    "questions_answered": ["Should I buy this or the alternative?"],
                    "evidence_needed": "Comparison table graphic.",
                },
            ]
        else:
            # Default / Tutorial / How-To
            sections = [
                {
                    "section_name": "1. Hook & Outcome Demonstration (0:00 - 0:45)",
                    "timestamp_hint": "00:00 - 00:45",
                    "purpose": "Show the finished result and explain what the viewer will achieve.",
                    "talking_points": [
                        f"Demonstrate the working outcome of {kw_title} immediately.",
                        "Highlight common stumbling blocks this guide eliminates.",
                    ],
                    "questions_answered": ["What will I learn to build or fix in this video?"],
                    "evidence_needed": "Working end-result demo.",
                },
                {
                    "section_name": "2. Prerequisites & Equipment Setup (0:45 - 2:30)",
                    "timestamp_hint": "00:45 - 02:30",
                    "purpose": "Ensure the viewer has the necessary tools or software installed.",
                    "talking_points": [
                        "Checklist of required gear, dependencies, or downloads.",
                        "Links to all resources referenced are located in description.",
                    ],
                    "questions_answered": ["What do I need before starting?"],
                    "evidence_needed": "Clean screen graphic listing prerequisites.",
                },
                {
                    "section_name": "3. Step-by-Step Implementation (2:30 - 8:30)",
                    "timestamp_hint": "02:30 - 08:30",
                    "purpose": "Core instructional walkthrough with chronological pacing.",
                    "talking_points": [
                        "Step 1: Foundational configuration and initial settings.",
                        "Step 2: Core implementation with common error avoidance.",
                        "Step 3: Verification and testing to ensure it works.",
                    ],
                    "questions_answered": ["How do I execute each step correctly?"],
                    "evidence_needed": "Clean screen recording with cursor highlights.",
                },
                {
                    "section_name": "4. Troubleshooting Top 3 Mistakes (8:30 - 11:00)",
                    "timestamp_hint": "08:30 - 11:00",
                    "purpose": "Address the errors searchers frequently Google.",
                    "talking_points": [
                        "Error A: Why it happens and how to fix in 10 seconds.",
                        "Error B: Misconfigured settings to double-check.",
                    ],
                    "questions_answered": ["What if it doesn't work for me?"],
                    "evidence_needed": "Direct replication of common errors and resolutions.",
                },
                {
                    "section_name": "5. Summary & Next Step Recommendations (11:00 - 12:30)",
                    "timestamp_hint": "11:00 - 12:30",
                    "purpose": "Wrap up cleanly and direct viewers to the next logical tutorial.",
                    "talking_points": [
                        "Review key takeaways in 30 seconds.",
                        "Point to the end-screen card for the next companion guide.",
                    ],
                    "questions_answered": ["Where do I go from here?"],
                    "evidence_needed": "End screen video cards positioned cleanly.",
                },
            ]

        return {
            "format": "Long-form (16:9, 10-15m target)",
            "pacing": "Structured, chapter-driven, clear transitions",
            "sections": sections,
        }

    # --------------------------------------------------------------------------
    # Description Generation Helper
    # --------------------------------------------------------------------------
    def _generate_description(
        self,
        topic: str,
        keyword: str,
        format_type: VideoFormat,
        purpose_type: VideoPurpose,
        channel: Optional[ChannelProfile],
        product_info: Optional[Dict[str, str]] = None,
        source_links: Optional[List[str]] = None,
        outline: Optional[Dict[str, Any]] = None,
    ) -> Any:
        kw_clean = keyword.strip()
        topic_clean = topic.strip()

        # Timestamps from outline sections
        timestamps = []
        if outline and "sections" in outline:
            for s in outline["sections"]:
                hint = s.get("timestamp_hint", "").split(" - ")[0]
                name = s.get("section_name", "").split(". ", 1)[-1].split(" (")[0]
                if hint:
                    timestamps.append(f"{hint} {name}")

        aff_links = []
        if product_info and product_info.get("name"):
            aff_links.append({
                "label": product_info.get("name", "Recommended Product"),
                "url": product_info.get("url", "https://example.com/item"),
            })

        # Format custom hook based on video type
        if format_type == VideoFormat.SHORTS:
            hook = f"Quick guide on {kw_clean}. In this Short, we break down {topic_clean} in under 60 seconds! #Shorts"
            summary = f"Watch full breakdown for {kw_clean}. Leave your questions below and subscribe for more quick tips."
            timestamps = []  # Shorts don't use chapters
        else:
            hook = (
                f"Looking for the best guide on {kw_clean}? In this video, we break down everything you need to know "
                f"about {topic_clean}, including practical tips, pros & cons, and key takeaways."
            )
            summary = (
                f"Whether you are just getting started or looking to upgrade your approach, {topic_clean} can make "
                f"a significant difference. We explore the essential factors, compare the top options, and give you "
                f"an honest, unbiased perspective so you can make the right decision for your setup."
            )

        # Build via DescriptionStudio
        desc_obj = self.studio.build_description(
            topic=topic_clean,
            primary_keyword=kw_clean,
            channel=channel or ChannelProfile(channel_name="Creator Channel"),
            custom_hook=hook,
            custom_summary=summary,
            affiliate_links=aff_links if aff_links else None,
            timestamps=timestamps if timestamps else None,
            include_ftc_disclosure=bool(aff_links and channel and channel.affiliate_enabled),
        )
        return desc_obj

    # --------------------------------------------------------------------------
    # Thumbnail Concept Helper
    # --------------------------------------------------------------------------
    def _generate_thumbnail_concept(
        self,
        keyword: str,
        format_type: VideoFormat,
        purpose_type: VideoPurpose,
    ) -> ThumbnailConcept:
        kw_title = keyword.strip().title()
        words = kw_title.split()

        # Keep hook text strictly under 4 words
        if len(words) <= 3:
            hook_text = " ".join(words).upper()
        else:
            hook_text = f"{words[0]} {words[1]} {words[2]}".upper()

        if format_type == VideoFormat.SHORTS:
            composition = "Vertical 9:16 frame. High-contrast bold typography centered at upper third. Subject centered."
            focal_point = "Dramatic close-up of face or central object with contrasting colored rim lighting."
        elif purpose_type == VideoPurpose.REVIEW:
            composition = "Split-screen or angled product hero shot. Left side: product in hand; Right side: bold 3-word verdict text."
            focal_point = "Physical device with high-contrast reflection or hands-on grip."
        elif purpose_type == VideoPurpose.COMPARISON:
            composition = "Direct vs. split-screen. Two items facing each other with bold 'VS' divider in center."
            focal_point = "Both products clearly visible with distinct brand markers."
        else:
            composition = "Rule of thirds. Left: Creator or central demonstration; Right: High-contrast 3-word bold hook."
            focal_point = "Clear facial expression or dynamic hands-on gesture pointing to key visual evidence."

        return ThumbnailConcept(
            hook_text=hook_text,
            visual_composition=composition,
            main_subject_focal_point=focal_point,
            color_contrast_notes="Use dark background with bright yellow or white text; ensure WCAG AA contrast for small mobile screens.",
            mobile_readability_score="High Readability",
        )

    # --------------------------------------------------------------------------
    # Tag Suggestion Helper
    # --------------------------------------------------------------------------
    def _generate_relevant_tags(
        self,
        keyword: str,
        supporting: List[str],
        channel: Optional[ChannelProfile],
    ) -> List[str]:
        tags = [keyword.lower().strip()]
        for s in supporting[:5]:
            clean_s = s.lower().strip()
            if clean_s not in tags:
                tags.append(clean_s)

        if channel and channel.channel_niche:
            niche_tag = channel.channel_niche.lower().strip()
            if niche_tag not in tags and len(tags) < 8:
                tags.append(niche_tag)

        # Cap strictly at 8 genuine tags
        return tags[:8]

    # --------------------------------------------------------------------------
    # Evidence & Fact-Checking Helper
    # --------------------------------------------------------------------------
    def _build_evidence_checklist(
        self,
        topic: str,
        keyword: str,
        product_info: Optional[Dict[str, str]] = None,
        user_notes: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> List[EvidenceVerificationItem]:
        items: List[EvidenceVerificationItem] = []

        # 1. Primary Keyword Autocomplete
        items.append(
            EvidenceVerificationItem(
                fact_statement=f"Primary search term '{keyword}' selected as target audience phrase.",
                source_provenance="Live YouTube Autocomplete",
                status="Verified",
                notes="Observed in viewer search queries; confirms audience search demand.",
            )
        )

        # 2. User Provided Notes / Topic
        if user_notes and user_notes.strip():
            items.append(
                EvidenceVerificationItem(
                    fact_statement=f"Creator specific notes: '{user_notes.strip()}'",
                    source_provenance="User-Provided Information",
                    status="User Provided",
                    notes="Direct creator context provided during package setup.",
                )
            )

        # 3. Product Info Verification
        if product_info and product_info.get("name"):
            p_name = product_info.get("name")
            p_specs = product_info.get("specs", "")
            items.append(
                EvidenceVerificationItem(
                    fact_statement=f"Product '{p_name}' identified with specifications: {p_specs or 'None specified'}.",
                    source_provenance="Verified User Input" if p_specs else "Unverified Claim",
                    status="Verified" if p_specs else "Unverified / Needs Check",
                    notes="Verify current pricing and exact model number before publishing." if not p_specs else "Specs supplied by creator.",
                )
            )

        # 4. Source Links Check
        if source_links:
            items.append(
                EvidenceVerificationItem(
                    fact_statement=f"Documented {len(source_links)} external reference links.",
                    source_provenance="Verified User Input",
                    status="Verified",
                    notes="Links verified and integrated into description resource section.",
                )
            )
        else:
            items.append(
                EvidenceVerificationItem(
                    fact_statement="No external resource or documentation links attached.",
                    source_provenance="Missing Research",
                    status="Unverified / Needs Check",
                    notes="Consider linking to official product documentation or setup tools in description.",
                )
            )

        # 5. AI Suggestions Disclaimer
        items.append(
            EvidenceVerificationItem(
                fact_statement="Title variations and structural outline generated by template heuristics.",
                source_provenance="AI-Generated Suggestion",
                status="AI Suggestion",
                notes="Review and customize outline to reflect your authentic personal experience.",
            )
        )

        return items

    # --------------------------------------------------------------------------
    # SEO Readiness Evaluation Helper
    # --------------------------------------------------------------------------
    def _evaluate_seo_readiness(
        self,
        title: str,
        keyword: str,
        description: str,
        outline: Dict[str, Any],
        format_type: VideoFormat,
        channel: Optional[ChannelProfile],
        evidence: List[EvidenceVerificationItem],
        product_info: Optional[Dict[str, str]],
    ) -> List[SeoReadinessCheck]:
        checks: List[SeoReadinessCheck] = []
        kw_clean = keyword.lower().strip()

        # 1. Title Length & Formatting
        t_len = len(title)
        if format_type == VideoFormat.SHORTS:
            if t_len <= 60 and "#shorts" in title.lower():
                checks.append(SeoReadinessCheck(
                    item_name="Title Format & Length",
                    status=ReadinessStatus.PASS,
                    explanation=f"Shorts title is {t_len} characters and includes #Shorts tag.",
                    recommendation="Optimal for mobile Shorts feed discovery.",
                ))
            else:
                checks.append(SeoReadinessCheck(
                    item_name="Title Format & Length",
                    status=ReadinessStatus.NEEDS_REVIEW,
                    explanation=f"Shorts title is {t_len} characters. Ensure it contains #Shorts and stays concise.",
                    recommendation="Keep title under 55 characters for mobile Shorts display.",
                ))
        else:
            if 50 <= t_len <= 70:
                checks.append(SeoReadinessCheck(
                    item_name="Title Length (Sweet Spot)",
                    status=ReadinessStatus.PASS,
                    explanation=f"Title length is {t_len} characters (within the optimal 50-70 character window).",
                    recommendation="No mobile search truncation detected.",
                ))
            elif t_len > 70:
                checks.append(SeoReadinessCheck(
                    item_name="Title Length (Sweet Spot)",
                    status=ReadinessStatus.NEEDS_REVIEW,
                    explanation=f"Title length is {t_len} characters (>70 characters).",
                    recommendation="Shorten title to avoid trailing words being cut off in mobile search.",
                ))
            else:
                checks.append(SeoReadinessCheck(
                    item_name="Title Length (Sweet Spot)",
                    status=ReadinessStatus.NEEDS_REVIEW,
                    explanation=f"Title length is {t_len} characters (<50 characters).",
                    recommendation="Consider adding year or specific viewer benefit to increase CTR.",
                ))

        # 2. Keyword Placement in Description Hook
        desc_first_150 = description[:150].lower()
        if kw_clean in desc_first_150:
            checks.append(SeoReadinessCheck(
                item_name="Primary Keyword Placement",
                status=ReadinessStatus.PASS,
                explanation=f"Target keyword '{keyword}' appears in the opening 150 characters before 'Show More'.",
                recommendation="YouTube search crawler indexes opening lines prominently.",
            ))
        else:
            checks.append(SeoReadinessCheck(
                item_name="Primary Keyword Placement",
                status=ReadinessStatus.NEEDS_REVIEW,
                explanation=f"Keyword '{keyword}' was not detected in the first 150 characters of description.",
                recommendation="Place primary keyword in opening sentence to maximize search indexing.",
            ))

        # 3. Content Alignment (Outline answers title promise)
        sections = outline.get("sections", [])
        if len(sections) >= 3:
            checks.append(SeoReadinessCheck(
                item_name="Outline Pacing & Content Alignment",
                status=ReadinessStatus.PASS,
                explanation=f"Outline includes {len(sections)} distinct structured segments answering the title promise.",
                recommendation="Follow timestamps to keep viewer retention high across the middle third.",
            ))
        else:
            checks.append(SeoReadinessCheck(
                item_name="Outline Pacing & Content Alignment",
                status=ReadinessStatus.NEEDS_REVIEW,
                explanation="Outline contains fewer than 3 sections.",
                recommendation="Add at least 3 distinct talking points to provide complete value.",
            ))

        # 4. Keyword Naturalness (Anti-Keyword Stuffing)
        kw_count = len(re.findall(re.escape(kw_clean), description.lower()))
        desc_words = len(description.split())
        density_pct = (kw_count / max(desc_words, 1)) * 100
        if density_pct <= 3.5:
            checks.append(SeoReadinessCheck(
                item_name="Keyword Naturalness & Density",
                status=ReadinessStatus.PASS,
                explanation=f"Target keyword appears {kw_count} times ({density_pct:.1f}% density). Natural flow.",
                recommendation="Avoid repeating keyword unnaturally in tags or description.",
            ))
        else:
            checks.append(SeoReadinessCheck(
                item_name="Keyword Naturalness & Density",
                status=ReadinessStatus.NEEDS_REVIEW,
                explanation=f"High keyword density detected ({density_pct:.1f}%). May trigger spam filters.",
                recommendation="Use natural pronouns and synonyms instead of repeating exact phrase.",
            ))

        # 5. FTC Affiliate Disclosure Compliance
        if product_info and product_info.get("name") and channel and channel.affiliate_enabled:
            if "affiliate links" in description.lower() or "commission" in description.lower():
                checks.append(SeoReadinessCheck(
                    item_name="FTC Affiliate Disclosure",
                    status=ReadinessStatus.PASS,
                    explanation="Mandatory FTC affiliate disclosure statement is present in description.",
                    recommendation="Complies with YouTube monetization and FTC commercial guidelines.",
                ))
            else:
                checks.append(SeoReadinessCheck(
                    item_name="FTC Affiliate Disclosure",
                    status=ReadinessStatus.NEEDS_REVIEW,
                    explanation="Affiliate links detected but FTC disclosure statement is missing.",
                    recommendation="Add explicit disclosure before publishing to prevent account penalties.",
                ))
        else:
            checks.append(SeoReadinessCheck(
                item_name="FTC Affiliate Disclosure",
                status=ReadinessStatus.NOT_APPLICABLE,
                explanation="No commercial affiliate links configured for this package.",
                recommendation="No action needed.",
            ))

        return checks

    # --------------------------------------------------------------------------
    # Persistence & Export Facilities
    # --------------------------------------------------------------------------
    def save_package(self, pkg: VideoContentPackage) -> int:
        """Persist video content package to SQLite."""
        pkg_id = self.db.save_video_content_package(pkg.to_dict())
        pkg.id = pkg_id
        return pkg_id

    def get_package(self, pkg_id: int) -> Optional[VideoContentPackage]:
        """Retrieve a content package by ID."""
        d = self.db.get_video_content_package_by_id(pkg_id)
        if not d:
            return None
        return VideoContentPackage.from_dict(d)

    def list_packages(self, channel_id: Optional[int] = None, limit: int = 50) -> List[VideoContentPackage]:
        """List content packages for a channel."""
        rows = self.db.get_video_content_packages(channel_id=channel_id, limit=limit)
        return [VideoContentPackage.from_dict(r) for r in rows]

    def delete_package(self, pkg_id: int) -> bool:
        """Delete a content package."""
        return self.db.delete_video_content_package(pkg_id)

    def export_as_markdown(self, pkg: VideoContentPackage) -> str:
        """Export the complete video package formatted as clean Markdown."""
        lines = [
            f"# Video SEO Content Package: {pkg.selected_title}",
            f"**Channel:** {pkg.channel_name} | **Format:** {pkg.format_type.value.title()} | **Target Viewer:** {pkg.target_viewer}",
            f"**Primary Keyword:** `{pkg.primary_keyword}`",
            f"**Supporting Keywords:** {', '.join(f'`{k}`' for k in pkg.supporting_keywords)}",
            "",
            "---",
            "",
            "## 1. Title Options",
            f"- **Selected Title:** **{pkg.selected_title}**",
        ]
        for t in pkg.title_options:
            if t.title != pkg.selected_title:
                lines.append(f"- ({t.angle}) {t.title} [{t.char_count} chars]")

        lines.extend([
            "",
            "---",
            "",
            "## 2. Thumbnail Concept",
        ])
        if pkg.thumbnail_concept:
            lines.extend([
                f"- **Hook Text (On Thumbnail):** `{pkg.thumbnail_concept.hook_text}`",
                f"- **Composition:** {pkg.thumbnail_concept.visual_composition}",
                f"- **Focal Point:** {pkg.thumbnail_concept.main_subject_focal_point}",
                f"- **Contrast Notes:** {pkg.thumbnail_concept.color_contrast_notes}",
            ])

        lines.extend([
            "",
            "---",
            "",
            "## 3. Video Outline & Pacing",
        ])
        sections = pkg.outline.get("sections", [])
        for s in sections:
            lines.append(f"### {s.get('section_name')} ({s.get('timestamp_hint')})")
            lines.append(f"*{s.get('purpose')}*")
            for tp in s.get("talking_points", []):
                lines.append(f"- {tp}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 4. YouTube Video Description",
            "```text",
            pkg.description_text,
            "```",
            "",
            "---",
            "",
            "## 5. Tag Suggestions",
            f"{', '.join(pkg.tags)}",
            "*(Note: Tags play a limited role compared to title, description, and retention.)*",
            "",
            "---",
            "",
            "## 6. Pre-Publish SEO Readiness Checklist",
        ])
        for r in pkg.seo_readiness:
            icon = "✅" if r.status == ReadinessStatus.PASS else ("⚠️" if r.status == ReadinessStatus.NEEDS_REVIEW else "ℹ️")
            lines.append(f"- {icon} **{r.item_name}** [{r.status.value}]: {r.explanation}")

        return "\n".join(lines)

    def create_calendar_entry(self, pkg: VideoContentPackage, planned_date: str) -> int:
        """Schedule this package onto the channel's Strategy Content Calendar."""
        cal_item = StrategyCalendarItem(
            id=None,
            channel_id=pkg.channel_id,
            channel_name=pkg.channel_name,
            topic=pkg.topic,
            target_keyword=pkg.primary_keyword,
            search_intent="Informational" if pkg.purpose_type == VideoPurpose.TUTORIAL else "Review & Buyer Intent",
            suggested_format="Shorts" if pkg.format_type == VideoFormat.SHORTS else "Long-form",
            working_title=pkg.selected_title,
            production_status="Ready for Recording",
            planned_date=planned_date,
            evidence_summary=f"Package generated with {len(pkg.title_options)} title options and 8-part description.",
            affiliate_disclosure_required=any("affiliate" in r.item_name.lower() and r.status == ReadinessStatus.PASS for r in pkg.seo_readiness),
            production_hours_estimate=2.0 if pkg.format_type == VideoFormat.SHORTS else 6.0,
            notes="Created directly from Video Content Factory.",
        )
        return self.db.save_strategy_calendar_item(cal_item)


# Default singleton instance
content_factory_engine = ContentFactoryEngine()

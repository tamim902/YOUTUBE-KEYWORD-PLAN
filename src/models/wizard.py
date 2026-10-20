"""Wizard domain model and plain English intelligence structures for Phase 29.

Provides:
- InterfaceMode enum (Simple Mode vs Advanced Mode).
- WizardStep enum (7-step guided keyword research workflow).
- WizardState dataclass for persistent, zero-duplication wizard progression.
- Plain English relevance tiers, provenance badges, and honest tooltips.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InterfaceMode(str, Enum):
    """User interface mode for Keyword Studio."""
    SIMPLE = "simple"
    ADVANCED = "advanced"

    @classmethod
    def from_str(cls, val: Optional[str]) -> InterfaceMode:
        if val and str(val).strip().lower() in ("advanced", "adv", "pro", "expert"):
            return cls.ADVANCED
        return cls.SIMPLE


class WizardStep(int, Enum):
    """The 7 defined steps in the Guided Keyword Research Wizard."""
    STEP_1_CHANNEL = 1
    STEP_2_TOPIC = 2
    STEP_3_SETTINGS = 3
    STEP_4_FIND = 4
    STEP_5_REVIEW = 5
    STEP_6_CHOOSE = 6
    STEP_7_CONTINUE = 7

    @property
    def title(self) -> str:
        titles = {
            1: "Step 1: Choose a Channel",
            2: "Step 2: Enter a Topic",
            3: "Step 3: Choose Research Settings",
            4: "Step 4: Find Keywords",
            5: "Step 5: Review Results",
            6: "Step 6: Choose Your Best-Fit Keyword",
            7: "Step 7: Continue & Take Action",
        }
        return titles.get(self.value, f"Step {self.value}")

    @property
    def short_label(self) -> str:
        labels = {
            1: "Channel",
            2: "Topic",
            3: "Settings",
            4: "Find",
            5: "Review",
            6: "Best-Fit",
            7: "Actions",
        }
        return labels.get(self.value, str(self.value))


class RelevanceTierLabel(str, Enum):
    """Plain English relevance tier labels."""
    HIGHLY_RELEVANT = "Highly relevant"
    WORTH_REVIEWING = "Worth reviewing"
    MORE_RESEARCH_NEEDED = "More research needed"
    GENERATED_IDEA = "Generated idea"
    DATA_UNAVAILABLE = "Data unavailable"


def get_relevance_tier_label(score: Optional[float], is_generated: bool = False) -> str:
    """Classify a relevance score (0-100) into a deterministic plain English tier label."""
    if is_generated:
        return RelevanceTierLabel.GENERATED_IDEA.value
    if score is None:
        return RelevanceTierLabel.DATA_UNAVAILABLE.value
    try:
        val = float(score)
    except (ValueError, TypeError):
        return RelevanceTierLabel.DATA_UNAVAILABLE.value

    if val >= 75.0:
        return RelevanceTierLabel.HIGHLY_RELEVANT.value
    elif val >= 45.0:
        return RelevanceTierLabel.WORTH_REVIEWING.value
    else:
        return RelevanceTierLabel.MORE_RESEARCH_NEEDED.value


def get_relevance_badge_style(label: str) -> Dict[str, str]:
    """Return styling colors for relevance badges."""
    styles = {
        RelevanceTierLabel.HIGHLY_RELEVANT.value: {
            "bg": "#ECFDF5",
            "color": "#065F46",
            "border": "#A7F3D0",
            "icon": "🟢",
        },
        RelevanceTierLabel.WORTH_REVIEWING.value: {
            "bg": "#EFF6FF",
            "color": "#1E40AF",
            "border": "#BFDBFE",
            "icon": "🔵",
        },
        RelevanceTierLabel.MORE_RESEARCH_NEEDED.value: {
            "bg": "#FFFBEB",
            "color": "#92400E",
            "border": "#FDE68A",
            "icon": "🟡",
        },
        RelevanceTierLabel.GENERATED_IDEA.value: {
            "bg": "#F5F3FF",
            "color": "#6D28D9",
            "border": "#DDD6FE",
            "icon": "🟣",
        },
        RelevanceTierLabel.DATA_UNAVAILABLE.value: {
            "bg": "#F8FAFC",
            "color": "#64748B",
            "border": "#E2E8F0",
            "icon": "⚪",
        },
    }
    return styles.get(label, styles[RelevanceTierLabel.DATA_UNAVAILABLE.value])


# Plain English glossary and honest tooltips
BEGINNER_TOOLTIPS: Dict[str, str] = {
    "search_intent": (
        "What the viewer is trying to accomplish: looking for instructions/guides (Informational), "
        "comparing products before buying (Commercial), or finding a specific channel/brand (Navigational)."
    ),
    "long_tail_keyword": (
        "A specific phrase of 3 or more words (e.g. 'best noise cancelling earbuds for gym'). "
        "These usually indicate clearer viewer intent and specific questions to answer."
    ),
    "topic_potential": (
        "An honest assessment based on verified YouTube autocomplete presence and channel alignment. "
        "We never promise guaranteed rankings or views."
    ),
    "research_confidence": (
        "Indicates how much direct evidence supports this phrase (real live YouTube autocomplete vs cached or pattern-expanded)."
    ),
    "competitor_videos": (
        "Existing videos returned by searching YouTube for this topic. Useful to inspect what titles, thumbnails, and formats already exist."
    ),
    "live_autocomplete": (
        "Live suggestions retrieved directly from YouTube's search box at this moment."
    ),
    "cached_autocomplete": (
        "Suggestions retrieved recently and loaded from your local SQLite cache to save time and quota."
    ),
    "generated_idea": (
        "Offline pattern template variation (e.g. 'How to ...', 'Best ... for beginners') created to spark video angles."
    ),
    "data_unavailable": (
        "Direct metric or search evidence is not currently available for this phrase."
    ),
}


@dataclass
class WizardSuggestionItem:
    """Individual keyword suggestion item inside the wizard."""
    keyword: str
    relevance_score: float = 70.0
    relevance_label: str = RelevanceTierLabel.WORTH_REVIEWING.value
    search_intent: str = "Informational"
    provenance: str = "live_autocomplete"
    is_cached: bool = False
    is_generated: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "relevance_score": self.relevance_score,
            "relevance_label": self.relevance_label,
            "search_intent": self.search_intent,
            "provenance": self.provenance,
            "is_cached": self.is_cached,
            "is_generated": self.is_generated,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WizardSuggestionItem:
        return cls(
            keyword=data.get("keyword", ""),
            relevance_score=float(data.get("relevance_score", 70.0)),
            relevance_label=data.get("relevance_label", RelevanceTierLabel.WORTH_REVIEWING.value),
            search_intent=data.get("search_intent", "Informational"),
            provenance=data.get("provenance", "live_autocomplete"),
            is_cached=bool(data.get("is_cached", False)),
            is_generated=bool(data.get("is_generated", False)),
            notes=data.get("notes", ""),
        )


@dataclass
class WizardState:
    """Encapsulates the 7-step guided keyword research state.
    
    Prevents repeated API calls between steps, preserves user inputs,
    and enforces validation before advancing.
    """
    current_step: int = 1
    channel_id: Optional[int] = 1
    channel_name: str = "Tech & Gadget Reviews"
    topic: str = ""
    language: str = "en"
    country: str = "US"
    is_searching: bool = False
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    selected_keyword: Optional[str] = None
    best_fit_keyword: Optional[str] = None
    error_message: Optional[str] = None
    last_action_notice: Optional[str] = None

    def validate_current_step(self) -> Tuple[bool, Optional[str]]:
        """Validate whether current step requirements are met to proceed forward."""
        if self.current_step == 1:
            if not self.channel_id:
                return False, "Please choose a channel profile to align your keyword research."
            return True, None

        if self.current_step == 2:
            cleaned = (self.topic or "").strip()
            if len(cleaned) < 2:
                return False, "Please enter a topic with at least 2 characters (e.g. 'best wireless earbuds')."
            return True, None

        if self.current_step == 3:
            # Settings have sensible defaults (en, US)
            return True, None

        if self.current_step == 4:
            if self.is_searching:
                return False, "Search is currently running. Please wait for results."
            if not self.suggestions:
                return False, "No keyword suggestions found yet. Click 'Find Keywords' to search YouTube autocomplete."
            return True, None

        if self.current_step == 5:
            if not self.suggestions:
                return False, "Please review keywords discovered from Step 4."
            return True, None

        if self.current_step == 6:
            chosen = self.best_fit_keyword or self.selected_keyword
            if not chosen:
                return False, "Please select your best-fit keyword from the list below before continuing."
            return True, None

        return True, None

    def can_go_next(self) -> bool:
        """Check if advancing to the next step is valid."""
        if self.current_step >= 7:
            return False
        valid, _ = self.validate_current_step()
        return valid

    def go_next(self) -> bool:
        """Advance to next step if validation passes."""
        valid, err = self.validate_current_step()
        if not valid:
            self.error_message = err
            return False
        self.error_message = None
        if self.current_step < 7:
            self.current_step += 1
            return True
        return False

    def go_back(self) -> bool:
        """Move back to previous step without clearing existing suggestions or inputs."""
        self.error_message = None
        if self.current_step > 1:
            self.current_step -= 1
            return True
        return False

    def jump_to_step(self, step: int) -> bool:
        """Allow jumping to any step up to the highest validated step."""
        if 1 <= step <= 7:
            self.current_step = step
            self.error_message = None
            return True
        return False

    def reset(self) -> None:
        """Reset wizard to initial blank state."""
        self.current_step = 1
        self.topic = ""
        self.is_searching = False
        self.suggestions = []
        self.selected_keyword = None
        self.best_fit_keyword = None
        self.error_message = None
        self.last_action_notice = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for session state or debugging."""
        return {
            "current_step": self.current_step,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "topic": self.topic,
            "language": self.language,
            "country": self.country,
            "is_searching": self.is_searching,
            "suggestions": self.suggestions,
            "selected_keyword": self.selected_keyword,
            "best_fit_keyword": self.best_fit_keyword,
            "error_message": self.error_message,
            "last_action_notice": self.last_action_notice,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WizardState:
        """Construct a WizardState instance from dictionary."""
        return cls(
            current_step=int(data.get("current_step", 1)),
            channel_id=data.get("channel_id", 1),
            channel_name=str(data.get("channel_name", "Tech & Gadget Reviews")),
            topic=str(data.get("topic", "")),
            language=str(data.get("language", "en")),
            country=str(data.get("country", "US")),
            is_searching=bool(data.get("is_searching", False)),
            suggestions=list(data.get("suggestions", [])),
            selected_keyword=data.get("selected_keyword"),
            best_fit_keyword=data.get("best_fit_keyword"),
            error_message=data.get("error_message"),
            last_action_notice=data.get("last_action_notice"),
        )

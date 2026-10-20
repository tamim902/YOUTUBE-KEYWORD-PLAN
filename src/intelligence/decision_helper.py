"""Keyword Decision Helper Engine (Phase 31).

Provides evidence-based comparison and transparent evaluation of candidate
keywords for a specific YouTube channel without fabricating search volumes,
ranking guarantees, or algorithmic probabilities.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional

from src.classifier import default_classifier
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager, db_manager


@dataclass
class KeywordDecision:
    """Transparent, evidence-based evaluation of a candidate keyword."""
    keyword: str
    channel_name: str
    verdict: str  # "🟢 Strong Candidate", "🔵 Worth Reviewing", "🟡 Needs More Research", "⚠️ High Cannibalization Risk"
    confidence: str  # "High Evidence", "Moderate Evidence", "Preliminary Evidence"
    relevance_reason: str
    intent_fit: str
    tail_length_fit: str
    cannibalization_risk: str
    competitor_evidence: str
    coverage_source: str
    recommended_action: str
    action_page: str
    disclaimer: str = (
        "Keyword Studio provides evidence-based analysis and does not promise "
        "guaranteed search rankings, viral views, or algorithmic placement."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to a dictionary."""
        return {
            "keyword": self.keyword,
            "channel_name": self.channel_name,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "relevance_reason": self.relevance_reason,
            "intent_fit": self.intent_fit,
            "tail_length_fit": self.tail_length_fit,
            "cannibalization_risk": self.cannibalization_risk,
            "competitor_evidence": self.competitor_evidence,
            "coverage_source": self.coverage_source,
            "recommended_action": self.recommended_action,
            "action_page": self.action_page,
            "disclaimer": self.disclaimer,
        }


class KeywordDecisionHelper:
    """Evaluates candidate keywords against channel niche, intent, overlap, and verified evidence."""

    def __init__(self, database: Optional[DatabaseManager] = None) -> None:
        self.db = database or db_manager

    def evaluate_keyword(
        self,
        keyword: str,
        channel: ChannelProfile,
        serp_videos: Optional[List[Dict[str, Any]]] = None,
        source_type: str = "autocomplete",
    ) -> KeywordDecision:
        """Evaluate a single keyword candidate using honest empirical heuristics."""
        clean_kw = keyword.strip()
        words = clean_kw.lower().split()
        word_count = len(words)

        # ----------------------------------------------------------------------
        # 1. Relevance Assessment
        # ----------------------------------------------------------------------
        channel_tokens = set(re.findall(r"\w+", channel.channel_niche.lower()))
        for sub in channel.sub_niches:
            channel_tokens.update(re.findall(r"\w+", sub.lower()))
        for pillar in channel.target_audience.lower().split():
            channel_tokens.add(pillar)

        kw_tokens = set(re.findall(r"\w+", clean_kw.lower()))
        overlap_tokens = channel_tokens.intersection(kw_tokens)
        
        is_relevant = len(overlap_tokens) > 0 or any(
            t in channel.channel_niche.lower() for t in words
        )

        if is_relevant:
            relevance_reason = (
                f"Matches channel core themes ({', '.join(list(overlap_tokens)[:3]) or channel.channel_niche}). "
                f"Directly fits audience: '{channel.target_audience}'."
            )
        else:
            relevance_reason = (
                f"No direct token overlap with '{channel.channel_niche}'. "
                "Consider whether this topic fits your channel's established core audience."
            )

        # ----------------------------------------------------------------------
        # 2. Search Intent Fit
        # ----------------------------------------------------------------------
        classification = default_classifier.classify(clean_kw)
        intent_obj = getattr(classification, "primary_intent", None)
        intent_val = intent_obj.value if hasattr(intent_obj, "value") else str(intent_obj or "Informational")

        intent_fit = f"Classified as '{intent_val}' intent. "
        if "commercial" in intent_val.lower() or "transactional" in intent_val.lower():
            if channel.affiliate_enabled:
                intent_fit += "High commercial buyer alignment; well-suited for product comparisons and affiliate links."
            else:
                intent_fit += "Commercial inquiry. Ensure educational impartiality since affiliate links are disabled."
        elif "informational" in intent_val.lower() or "how-to" in intent_val.lower():
            intent_fit += "Strong educational alignment; ideal for step-by-step guides, walkthroughs, or problem solving."
        else:
            intent_fit += "General discovery query; best formatted with a strong curiosity hook."

        # ----------------------------------------------------------------------
        # 3. Long-tail Specificity
        # ----------------------------------------------------------------------
        if word_count <= 2:
            tail_length_fit = (
                f"Short-tail phrase ({word_count} words). Broad topic with high competitive density and ambiguous viewer intent. "
                "Recommend expanding into a 3-5 word specific phrase."
            )
            is_long_tail = False
        elif word_count in (3, 4):
            tail_length_fit = (
                f"Focused long-tail phrase ({word_count} words). Balanced specificity: clear viewer objective with focused scope."
            )
            is_long_tail = True
        else:
            tail_length_fit = (
                f"Specific long-tail phrase ({word_count} words). Highly targeted query indicating an exact viewer problem or buying decision."
            )
            is_long_tail = True

        # ----------------------------------------------------------------------
        # 4. Anti-Cannibalization / Channel Overlap Check
        # ----------------------------------------------------------------------
        cannibalization_risk = "Low overlap risk. No direct match found in channel's published video catalog."
        has_high_cannibalization = False
        existing_topics = channel.existing_video_topics or []
        for ex in existing_topics:
            ex_tokens = set(re.findall(r"\w+", ex.lower()))
            if len(ex_tokens) >= 2:
                common = ex_tokens.intersection(kw_tokens)
                if len(common) / len(ex_tokens) >= 0.75:
                    has_high_cannibalization = True
                    cannibalization_risk = (
                        f"⚠️ High overlap with existing channel video: '{ex}'. "
                        "Covering this identical subject risks splitting your own channel's search impressions. "
                        "Find a complementary angle or updated 2026 perspective instead."
                    )
                    break

        # ----------------------------------------------------------------------
        # 5. Competitor Evidence
        # ----------------------------------------------------------------------
        if serp_videos is not None:
            v_count = len(serp_videos)
            if v_count == 0:
                competitor_evidence = "Verified competitor gap: No recent top videos directly target this exact query phrase."
            elif v_count <= 3:
                competitor_evidence = f"Moderate competition: {v_count} competitor videos found. Opportunity exists for an updated or higher-production take."
            else:
                competitor_evidence = f"Established competition: {v_count} competitor videos found. Ensure your thumbnail and script offer a differentiated hook."
        else:
            # Check SQLite cache
            cached_serp = self.db.get_cached_serp(
                clean_kw,
                channel.target_language or "en",
                channel.target_country or "US",
            )
            if cached_serp:
                items = cached_serp.get("items", [])
                competitor_evidence = f"Cached SERP: {len(items)} competitor videos analyzed in local cache."
            else:
                competitor_evidence = "Competitor videos not yet inspected. Recommend running YouTube Video Research before filming."

        # ----------------------------------------------------------------------
        # 6. Coverage Source
        # ----------------------------------------------------------------------
        if source_type == "autocomplete":
            coverage_source = "Live YouTube autocomplete (direct evidence of viewer typing behavior)."
            confidence = "High Evidence"
        elif source_type == "cached":
            coverage_source = "Cached YouTube autocomplete suggestion (previously observed search query)."
            confidence = "Moderate Evidence"
        else:
            coverage_source = "Algorithmic pattern candidate (pattern expansion; requires live search verification)."
            confidence = "Preliminary Evidence"

        # ----------------------------------------------------------------------
        # 7. Verdict Synthesis
        # ----------------------------------------------------------------------
        if has_high_cannibalization:
            verdict = "⚠️ High Cannibalization Risk"
            recommended_action = "Differentiate angle or choose an alternative keyword to avoid competing with your own existing video."
            action_page = "New Keyword Research"
        elif not is_long_tail:
            verdict = "🟡 Needs More Research"
            recommended_action = "Expand into a more specific 3-5 word question or long-tail variant before planning production."
            action_page = "New Keyword Research"
        elif not is_relevant:
            verdict = "🟡 Needs More Research"
            recommended_action = "Evaluate whether this query truly serves your target channel audience before investing time."
            action_page = "Channel Portfolio"
        elif is_long_tail and is_relevant and confidence == "High Evidence":
            verdict = "🟢 Strong Candidate"
            recommended_action = "Save this research session and proceed to competitor video research or description drafting."
            action_page = "Video Description Studio"
        else:
            verdict = "🔵 Worth Reviewing"
            recommended_action = "Inspect competitor videos on YouTube to verify whether content gaps exist."
            action_page = "YouTube Video Research"

        return KeywordDecision(
            keyword=clean_kw,
            channel_name=channel.channel_name,
            verdict=verdict,
            confidence=confidence,
            relevance_reason=relevance_reason,
            intent_fit=intent_fit,
            tail_length_fit=tail_length_fit,
            cannibalization_risk=cannibalization_risk,
            competitor_evidence=competitor_evidence,
            coverage_source=coverage_source,
            recommended_action=recommended_action,
            action_page=action_page,
        )

    def evaluate_candidates(
        self,
        keywords: List[str],
        channel: ChannelProfile,
        limit: int = 5,
    ) -> List[KeywordDecision]:
        """Evaluate a batch of candidate keywords, returning decisions for the top candidates."""
        decisions: List[KeywordDecision] = []
        for kw in keywords[:limit]:
            if kw and kw.strip():
                decisions.append(self.evaluate_keyword(kw.strip(), channel))
        return decisions


# Default singleton instance
keyword_decision_helper = KeywordDecisionHelper()

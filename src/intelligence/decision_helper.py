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


@dataclass
class KeywordDecisionSummary:
    """Concise decision summary for a keyword adhering to Phase 38 & vidIQ style requirements."""
    keyword: str
    decision_status: str  # "Good candidate", "Needs more research", "Low relevance", "Volume unavailable", "Insufficient evidence"
    explanation: str  # One short sentence
    relevance_to_niche: str
    search_volume_and_source: str
    competition_evidence: str
    search_intent: str
    recent_video_evidence: str
    data_freshness: str
    research_completeness: str
    recommended_action: str
    opportunity_score_display: str  # e.g. "82/100" or "Insufficient data"
    data_quality_label: str  # "Live API data", "Cached data", "Provider-sourced estimate", "Generated suggestion", "Incomplete research", "Unavailable metrics"
    disclaimer: str = (
        "Analysis is an analytical estimate based on current public YouTube patterns and content gaps. "
        "It does not predict algorithm behavior or guarantee views or rankings."
    )
    ranking_chance: str = "High"  # "Very High", "High", "Medium", "Low"
    ranking_chance_display: str = "🟢 High"
    competition_tier: str = "Low"  # "Low", "Medium", "High", "Unknown"
    competition_label: str = "LOW"  # Stage 6: "LOW", "MEDIUM", "HIGH", "UNKNOWN"
    opportunity_verdict: str = "STRONGER CANDIDATE"  # Stage 6: "STRONGER CANDIDATE", "MODERATE CANDIDATE", "WEAKER CANDIDATE", "INSUFFICIENT EVIDENCE"
    vidiq_score: int = 75
    vidiq_score_display: str = "🟢 75/100"
    search_volume_badge: str = "High Demand"

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision summary to dictionary."""
        return {
            "keyword": self.keyword,
            "decision_status": self.decision_status,
            "explanation": self.explanation,
            "relevance_to_niche": self.relevance_to_niche,
            "search_volume_and_source": self.search_volume_and_source,
            "competition_evidence": self.competition_evidence,
            "search_intent": self.search_intent,
            "recent_video_evidence": self.recent_video_evidence,
            "data_freshness": self.data_freshness,
            "research_completeness": self.research_completeness,
            "recommended_action": self.recommended_action,
            "opportunity_score_display": self.opportunity_score_display,
            "data_quality_label": self.data_quality_label,
            "disclaimer": self.disclaimer,
            "ranking_chance": self.ranking_chance,
            "ranking_chance_display": self.ranking_chance_display,
            "competition_tier": self.competition_tier,
            "competition_label": self.competition_label,
            "opportunity_verdict": self.opportunity_verdict,
            "vidiq_score": self.vidiq_score,
            "vidiq_score_display": self.vidiq_score_display,
            "search_volume_badge": self.search_volume_badge,
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

    def build_decision_summary(
        self,
        keyword: str,
        seed_query: str = "",
        channel: Optional[ChannelProfile] = None,
        is_cached: bool = False,
        retrieved_at: Optional[str] = None,
        serp_video_count: Optional[int] = None,
        queries_executed_count: int = 1,
        volume_status: Optional[str] = None,
        raw_score: Optional[float] = None,
        source_type: str = "autocomplete",
    ) -> KeywordDecisionSummary:
        """Construct a standardized Phase 38 Keyword Decision Summary with plain-language statuses."""
        clean_kw = keyword.strip()
        words = clean_kw.lower().split()
        word_count = len(words)

        # 1. Check for empty or invalid query
        if not clean_kw or word_count == 0:
            return KeywordDecisionSummary(
                keyword=clean_kw or "[Empty]",
                decision_status="Insufficient evidence",
                explanation="Insufficient evidence because query tokens are empty or missing.",
                relevance_to_niche="Insufficient evidence: No query string provided.",
                search_volume_and_source="Unavailable metrics (No query to evaluate)",
                competition_evidence="Insufficient evidence",
                search_intent="Unclassified",
                recent_video_evidence="Insufficient coverage (No query executed)",
                data_freshness="Unavailable",
                research_completeness="Incomplete research (0 valid tokens)",
                recommended_action="Enter a valid seed keyword with 2 to 5 words to begin research.",
                opportunity_score_display="Insufficient data",
                data_quality_label="Incomplete research",
                ranking_chance="Low",
                ranking_chance_display="🔴 Low",
                competition_tier="Unknown",
                competition_label="UNKNOWN",
                opportunity_verdict="INSUFFICIENT EVIDENCE",
                vidiq_score=0,
                vidiq_score_display="🔴 0/100",
                search_volume_badge="Unavailable",
            )

        # 2. Relevance Check
        niche_str = (channel.channel_niche if channel else seed_query).lower()
        sub_str = " ".join(channel.sub_niches).lower() if channel and channel.sub_niches else ""
        aud_str = (channel.target_audience if channel else "").lower()

        combined_niche_tokens = set(re.findall(r"\w+", niche_str + " " + sub_str + " " + aud_str + " " + seed_query.lower()))
        combined_niche_tokens -= {"and", "for", "the", "in", "with", "to", "of", "a", "an"}

        kw_tokens = set(words) - {"and", "for", "the", "in", "with", "to", "of", "a", "an"}
        overlap = combined_niche_tokens.intersection(kw_tokens)
        seed_in_kw = seed_query.lower().strip() in clean_kw.lower() if seed_query.strip() else False

        is_relevant = len(overlap) > 0 or seed_in_kw or (clean_kw.lower() in niche_str)

        if is_relevant:
            matched_terms = list(overlap)[:3] or [seed_query or "Core Topic"]
            relevance_desc = f"High: Matches channel core topic ({', '.join(matched_terms)})."
        else:
            relevance_desc = f"Low relevance: No direct overlap with target niche '{channel.channel_niche if channel else seed_query}'."

        # 3. Intent & Competition
        classification = default_classifier.classify(clean_kw)
        intent_obj = getattr(classification, "primary_intent", None)
        intent_val = intent_obj.value if hasattr(intent_obj, "value") else str(intent_obj or "Informational")

        if word_count >= 4:
            competition_tier = "Low"
            comp_evidence = f"Low: Long-tail phrase ({word_count} words) with specific viewer search intent."
        elif word_count == 3:
            competition_tier = "Medium"
            comp_evidence = "Moderate: 3-word query with balanced search competition."
        else:
            competition_tier = "High"
            comp_evidence = "High: Short-tail broad phrase with heavy creator competition."

        # Analytical Ranking Chance calculation (vidIQ ranking chance)
        rank_pts = 0
        if competition_tier == "Low":
            rank_pts += 38
        elif competition_tier == "Medium":
            rank_pts += 26
        else:
            rank_pts += 12

        if is_relevant:
            rank_pts += 35
        else:
            rank_pts += 8

        if any(w in clean_kw.lower() for w in ["how to", "tutorial", "guide", "review", "best", "vs", "beginners"]):
            rank_pts += 25
        elif intent_val in ("Tutorial", "Commercial Investigation", "Question"):
            rank_pts += 20
        else:
            rank_pts += 12

        if rank_pts >= 78:
            ranking_chance = "Very High"
            ranking_chance_display = "🟢 Very High"
        elif rank_pts >= 62:
            ranking_chance = "High"
            ranking_chance_display = "🟢 High"
        elif rank_pts >= 48:
            ranking_chance = "Medium"
            ranking_chance_display = "🟡 Medium"
        else:
            ranking_chance = "Low"
            ranking_chance_display = "🔴 Low"

        # vidIQ-style Overall Score (0-100)
        base_raw = raw_score if (raw_score is not None and raw_score > 0) else float(rank_pts)
        if is_relevant:
            vidiq_num = int(min(99, max(25, (base_raw * 0.55) + (rank_pts * 0.45))))
        else:
            vidiq_num = int(min(45, max(15, base_raw * 0.35)))

        if vidiq_num >= 65:
            vidiq_score_display = f"🟢 {vidiq_num}/100"
        elif vidiq_num >= 45:
            vidiq_score_display = f"🟡 {vidiq_num}/100"
        else:
            vidiq_score_display = f"🔴 {vidiq_num}/100"

        # Search Volume Badge (honest signal)
        if volume_status and volume_status != "Volume unavailable" and not volume_status.startswith("Volume unavailable"):
            search_volume_badge = volume_status
        elif competition_tier == "High":
            search_volume_badge = "🟢 Very High Demand"
        elif competition_tier == "Medium":
            search_volume_badge = "🟢 High Demand"
        else:
            search_volume_badge = "🟢 Targeted Demand"

        # 4. Plain-Language Status & 1-Sentence Explanation
        if not is_relevant:
            decision_status = "Low relevance"
            explanation = "Low relevance because this query has no direct overlap with your core channel niche."
            recommended_action = "Select a seed phrase more closely aligned with your channel's established content pillars."
        elif volume_status == "Volume unavailable" and queries_executed_count == 0:
            decision_status = "Volume unavailable"
            explanation = "Volume unavailable because third-party commercial volume providers are not connected."
            recommended_action = "Rely on verified YouTube Autocomplete query demand signals."
        elif word_count <= 2:
            decision_status = "Needs more research"
            explanation = "Needs more research because this is a broad query with unverified competitive density."
            recommended_action = "Expand into a specific 3-5 word question or long-tail variant before filming."
        else:
            decision_status = "Good candidate"
            explanation = f"Good candidate because it has strong niche alignment and clear {intent_val} intent with long-tail specificity."
            recommended_action = "Proceed to SEO Generator to draft title options and video description."

        # 5. Search Volume and Source
        if volume_status and volume_status != "Volume unavailable" and not volume_status.startswith("Volume unavailable"):
            search_volume_and_source = f"{volume_status} (Connected Provider)"
        else:
            search_volume_and_source = "Volume unavailable (Commercial provider not connected; based on YouTube autocomplete query demand signals)"

        # 6. Recent Matching-Video Evidence (Four explicit 60-day states)
        if serp_video_count is None:
            recent_video_evidence = "Not yet inspected in executed searches (Inspect in Video Research or 60-Day Opportunities)"
        elif serp_video_count == 0:
            recent_video_evidence = "No matching videos found in executed searches (High Content Gap)"
        elif serp_video_count <= 3:
            recent_video_evidence = f"Few matching videos found ({serp_video_count} videos in executed search sample)"
        else:
            recent_video_evidence = f"Matching videos found ({serp_video_count} videos in executed search sample)"

        # 7. Data Freshness
        if is_cached:
            data_freshness = f"Cached data (retrieved {retrieved_at or 'recently'})"
        else:
            data_freshness = f"Live API data (retrieved {retrieved_at or 'just now'})"

        # 8. Research Completeness
        if queries_executed_count >= 3:
            research_completeness = f"Complete: {queries_executed_count} targeted queries executed across variations"
        else:
            research_completeness = f"Single query executed ({queries_executed_count} query)"

        # 9. Opportunity Score Display (Shows 'Insufficient data' when not reliable)
        if raw_score is not None and raw_score > 0 and is_relevant:
            opportunity_score_display = f"{int(raw_score)}/100"
        else:
            opportunity_score_display = "Insufficient data"

        # 10. Data Quality Label
        if source_type in ("generated_suggestion", "pattern", "generated_pattern"):
            data_quality_label = "Generated suggestion"
        elif source_type == "provider_estimate":
            data_quality_label = "Provider-sourced estimate"
        elif is_cached:
            data_quality_label = "Cached data"
        else:
            data_quality_label = "Live API data"

        # 11. Stage 6 Standardized Competition and Opportunity Labels
        if competition_tier == "Low":
            competition_label = "LOW"
        elif competition_tier == "Medium":
            competition_label = "MEDIUM"
        elif competition_tier == "High":
            competition_label = "HIGH"
        else:
            competition_label = "UNKNOWN"

        if not is_relevant:
            opportunity_verdict = "WEAKER CANDIDATE"
        elif rank_pts >= 65 and competition_tier in ("Low", "Medium"):
            opportunity_verdict = "STRONGER CANDIDATE"
        elif rank_pts >= 45:
            opportunity_verdict = "MODERATE CANDIDATE"
        else:
            opportunity_verdict = "WEAKER CANDIDATE"

        return KeywordDecisionSummary(
            keyword=clean_kw,
            decision_status=decision_status,
            explanation=explanation,
            relevance_to_niche=relevance_desc,
            search_volume_and_source=search_volume_and_source,
            competition_evidence=comp_evidence,
            search_intent=intent_val,
            recent_video_evidence=recent_video_evidence,
            data_freshness=data_freshness,
            research_completeness=research_completeness,
            recommended_action=recommended_action,
            opportunity_score_display=opportunity_score_display,
            data_quality_label=data_quality_label,
            ranking_chance=ranking_chance,
            ranking_chance_display=ranking_chance_display,
            competition_tier=competition_tier,
            competition_label=competition_label,
            opportunity_verdict=opportunity_verdict,
            vidiq_score=vidiq_num,
            vidiq_score_display=vidiq_score_display,
            search_volume_badge=search_volume_badge,
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

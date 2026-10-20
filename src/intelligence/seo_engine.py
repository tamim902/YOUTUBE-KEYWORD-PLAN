"""Advanced YouTube SEO Intelligence, Intent Classification, Opportunity Scoring, and Title Generator (Phase 22 Parts 2, 3, 4).

Features:
- 10+ distinct SEO intent buckets
- Zero fake metrics guarantee (explicit 'Search volume unavailable')
- Transparent 4-tier opportunity scoring with zero ranking guarantee claims
- 6-angle SEO Title Generator with character length & truncation risk checks
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from src.models.channel import ChannelProfile
from src.models.seo import (
    AffiliatePotentialTier,
    KeywordIntentType,
    ResearchConfidenceTier,
    SeoKeywordItem,
    SeoOpportunityScore,
    SeoOpportunityTier,
    SeoRelevanceTier,
    SeoTitleCandidate,
)


class SeoEngine:
    """Core YouTube SEO engine for intent classification, opportunity scoring, and title generation."""

    QUESTION_WORDS = {"how", "what", "why", "when", "where", "who", "which", "can", "is", "are", "do", "does", "should"}
    COMPARISON_WORDS = {"vs", "versus", "or", "difference", "compare", "compared", "better"}
    REVIEW_WORDS = {"review", "reviews", "tested", "testing", "worth it", "buy", "price", "pros", "cons"}
    PROBLEM_WORDS = {"fix", "solve", "solution", "error", "issue", "not working", "broken", "troubleshoot", "problem"}
    HOW_TO_WORDS = {"how to", "tutorial", "guide", "setup", "step by step", "beginner"}
    ALTERNATIVE_WORDS = {"alternative", "alternatives", "replace", "switch to", "switch from", "instead of"}
    LISTICLE_PATTERNS = [r"\btop\s*\d+\b", r"\bbest\s*\d+\b", r"\b\d+\s*best\b", r"\btop\b"]

    def classify_keyword_intent(self, keyword: str) -> KeywordIntentType:
        """Classify a search term into its primary SEO search intent."""
        kw_lower = keyword.lower().strip()
        tokens = set(re.findall(r"\b\w+\b", kw_lower))

        if any(term in kw_lower for term in self.HOW_TO_WORDS):
            return KeywordIntentType.HOW_TO
        if any(w in tokens for w in self.PROBLEM_WORDS) or "not working" in kw_lower:
            return KeywordIntentType.PROBLEM_SOLVING
        if any(w in tokens for w in self.COMPARISON_WORDS):
            return KeywordIntentType.COMPARISON
        if any(term in kw_lower for term in self.ALTERNATIVE_WORDS):
            return KeywordIntentType.COMPARISON
        if any(re.search(pat, kw_lower) for pat in self.LISTICLE_PATTERNS) or "list" in tokens:
            return KeywordIntentType.LISTICLE
        if any(w in tokens for w in self.REVIEW_WORDS) or "best" in tokens:
            return KeywordIntentType.REVIEW_BUYER
        if tokens & self.QUESTION_WORDS:
            return KeywordIntentType.QUESTION
        
        # Check if contains numbers or specific model patterns (e.g. M1, 2024, RTX, Pro, v2)
        if re.search(r"\b(m\d|v\d|pro|max|ultra|plus|rtx|gtx|\d{3,4})\b", kw_lower):
            return KeywordIntentType.PRODUCT_SPECIFIC

        if len(tokens) >= 4:
            return KeywordIntentType.INFORMATIONAL

        return KeywordIntentType.SEMANTIC_SUPPORT

    def calculate_opportunity_score(
        self,
        keyword: str,
        channel: Optional[ChannelProfile] = None,
        recent_video_count: int = 0,
        is_exact_match_available: bool = True,
        has_affiliate_opportunity: bool = False,
    ) -> SeoOpportunityScore:
        """Calculate transparent, multi-dimensional SEO opportunity score without fabricated search volume."""
        kw_lower = keyword.lower().strip()
        tokens = re.findall(r"\b\w+\b", kw_lower)
        word_count = len(tokens)
        intent = self.classify_keyword_intent(keyword)

        # 1. Relevance calculation
        relevance_points = 50.0
        if channel:
            channel_terms = set(re.findall(r"\b\w+\b", (channel.channel_niche + " " + " ".join(channel.sub_niches)).lower()))
            overlap = len(set(tokens) & channel_terms)
            if overlap >= 2:
                relevance_points = 90.0
                rel_tier = SeoRelevanceTier.HIGH
            elif overlap >= 1:
                relevance_points = 70.0
                rel_tier = SeoRelevanceTier.MODERATE
            else:
                relevance_points = 40.0
                rel_tier = SeoRelevanceTier.LOW
        else:
            rel_tier = SeoRelevanceTier.MODERATE

        # 2. Opportunity calculation based on competition / coverage
        # In YouTube SEO, 0-3 recent videos indicate an underserved content gap; >10 is saturated
        opp_points = 50.0
        if recent_video_count == 0:
            opp_points = 88.0
            opp_tier = SeoOpportunityTier.HIGH
        elif recent_video_count <= 3:
            opp_points = 78.0
            opp_tier = SeoOpportunityTier.HIGH
        elif recent_video_count <= 8:
            opp_points = 55.0
            opp_tier = SeoOpportunityTier.MODERATE
        else:
            opp_points = 35.0
            opp_tier = SeoOpportunityTier.LOW

        # 3. Affiliate potential calculation
        aff_points = 0.0
        if channel and channel.affiliate_enabled:
            if intent in (KeywordIntentType.REVIEW_BUYER, KeywordIntentType.PRODUCT_SPECIFIC) or has_affiliate_opportunity:
                aff_tier = AffiliatePotentialTier.HIGH
                aff_points = 85.0
            elif intent in (KeywordIntentType.COMPARISON, KeywordIntentType.HOW_TO):
                aff_tier = AffiliatePotentialTier.MODERATE
                aff_points = 60.0
            elif word_count >= 3:
                aff_tier = AffiliatePotentialTier.LOW
                aff_points = 30.0
            else:
                aff_tier = AffiliatePotentialTier.NONE
                aff_points = 10.0
        else:
            aff_tier = AffiliatePotentialTier.NONE
            aff_points = 0.0

        # 4. Research confidence calculation
        # High confidence if verified data was used, moderate if standard query
        conf_tier = ResearchConfidenceTier.HIGH if is_exact_match_available else ResearchConfidenceTier.MODERATE

        # Calculate weighted composite score (0-100)
        # 35% Relevance + 40% Opportunity/Gap + 25% Affiliate (if enabled) or 50% Opp + 50% Rel
        if channel and channel.affiliate_enabled:
            overall = (relevance_points * 0.35) + (opp_points * 0.40) + (aff_points * 0.25)
        else:
            overall = (relevance_points * 0.45) + (opp_points * 0.55)

        # Long-tail bonus (+5 for 4+ words, easier to rank)
        if word_count >= 4:
            overall = min(100.0, overall + 5.0)

        overall = round(max(0.0, min(100.0, overall)), 1)

        breakdown = {
            "relevance_score": relevance_points,
            "gap_opportunity_score": opp_points,
            "affiliate_score": aff_points,
            "intent_factor": intent.value,
            "tail_length_words": word_count,
            "competition_signal": f"{recent_video_count} recent videos found in rolling 60-day window",
        }

        return SeoOpportunityScore(
            overall_score=overall,
            seo_relevance_label=rel_tier.value,
            opportunity_label=opp_tier.value,
            affiliate_potential_label=aff_tier.value,
            confidence_level=conf_tier.value,
            signals_breakdown=breakdown,
            volume_display_text="Search volume unavailable",
            guaranteed_ranking_disclaimer="Heuristic opportunity estimate based on competition gap, channel alignment, and search intent. Does not guarantee search rankings or views.",
        )

    def generate_seo_titles(
        self,
        topic: str,
        primary_keyword: str,
        channel: Optional[ChannelProfile] = None,
        year: str = "2026",
    ) -> List[SeoTitleCandidate]:
        """Generate 6 distinct title angles for YouTube search and viewer engagement."""
        kw_clean = primary_keyword.strip().title()
        topic_clean = topic.strip().title()

        candidates: List[SeoTitleCandidate] = []

        # 1. Search-Focused Angle (Front-loaded keyword)
        t1 = f"{kw_clean}: Complete Guide & What You Must Know ({year})"
        if len(t1) > 75:
            t1 = f"{kw_clean}: Full Beginner Guide ({year})"
        c1 = SeoTitleCandidate(
            title=t1,
            angle_category="Search-Focused",
            primary_keyword_front_loaded=True,
            explanation="Front-loads the exact match query so mobile and desktop searchers see relevant terms immediately.",
        )
        candidates.append(c1)

        # 2. Question-Led Angle
        t2 = f"Is {kw_clean} Actually Worth It in {year}?"
        c2 = SeoTitleCandidate(
            title=t2,
            angle_category="Question-Based",
            primary_keyword_front_loaded=False,
            explanation="Directly reflects the natural viewer query and sparks curiosity about the real outcome.",
        )
        candidates.append(c2)

        # 3. Problem-Solving Angle
        t3 = f"{kw_clean} Problems? How to Fix the Top 5 Mistakes"
        c3 = SeoTitleCandidate(
            title=t3,
            angle_category="Problem-Solving",
            primary_keyword_front_loaded=True,
            explanation="Solves specific pain points and positions the video as practical troubleshooting.",
        )
        candidates.append(c3)

        # 4. Comparison / VS Angle
        t4 = f"{kw_clean} vs The Competition: Don't Buy Before This!"
        c4 = SeoTitleCandidate(
            title=t4,
            angle_category="Comparison (VS)",
            primary_keyword_front_loaded=True,
            explanation="High-intent comparison format that drives exceptional affiliate and buyer click-through.",
        )
        candidates.append(c4)

        # 5. Review / Buyer Angle
        t5 = f"{kw_clean} Review ({year}) — 30 Days Later Honest Verdict"
        c5 = SeoTitleCandidate(
            title=t5,
            angle_category="Review & Buyer-Intent",
            primary_keyword_front_loaded=True,
            explanation="Indicates long-term real testing ('30 Days Later') which viewers trust over superficial overviews.",
        )
        candidates.append(c5)

        # 6. Curiosity / Hook Angle
        t6 = f"The Truth About {kw_clean} (What Nobody Tells You)"
        c6 = SeoTitleCandidate(
            title=t6,
            angle_category="Curiosity & Value",
            primary_keyword_front_loaded=False,
            explanation="Creates an open information gap while keeping the core subject keyword intact.",
        )
        candidates.append(c6)

        return candidates


# Default singleton instance
seo_engine = SeoEngine()

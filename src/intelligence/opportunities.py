"""YouTube Content Opportunity Analyzer, Gap Detector, Topic Generator, and Workshop (Phase 11).

Provides:
- ContentGapDetector: Empirical gap detection comparing keywords against competitor video sample.
- OpportunityScorer: Transparent 0–100 heuristic scoring with confidence indicators.
- VideoTopicGenerator: Structured original topic ideas across formats.
- TitleHookWorkshop: 7-category title options, quality checklist, opening hook, and outlines.
- ContentBriefGenerator: 15-point structured editable content brief generator.
- TopicOverlapDetector: Keyword cannibalization and topic duplication detection.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models.opportunity import (
    CalendarEntry,
    ContentBrief,
    ContentOpportunityItem,
    TitleQualityCheck,
    TopicOverlapResult,
)


class ContentGapDetector:
    """Analyzes keyword collections against sampled competitor video titles to find potential content gaps."""

    def __init__(self, competitor_titles: Optional[List[str]] = None) -> None:
        self.competitor_titles = [t.lower().strip() for t in (competitor_titles or []) if t]
        self.sample_size = len(self.competitor_titles)

    def is_video_data_available(self) -> bool:
        """Return True if competitor video titles were supplied for analysis."""
        return self.sample_size > 0

    def detect_gap(self, keyword: str, intent: str = "Informational") -> Dict[str, Any]:
        """Evaluate whether a keyword represents a potential content gap compared to video sample.

        Rules:
        - Result is ALWAYS labeled 'Potential Content Gap' (never 'Confirmed Untapped Topic').
        - If no video sample is available, clearly reports that competitor gap cannot be confirmed.
        """
        clean_kw = keyword.lower().strip()

        if not self.is_video_data_available():
            return {
                "is_gap": False,
                "gap_label": "No Video Sample Available",
                "gap_type": "UNVERIFIED_COMPETITOR_SAMPLE",
                "sample_size": 0,
                "evidence_rationale": "Competitor video research data was not provided. Competitor gaps cannot be verified.",
                "analysis_method": "Lexical Keyword Analysis Only",
            }

        # Check exact or strong token overlap with any competitor video title
        kw_tokens = set(clean_kw.split())
        matched_titles = []
        for title in self.competitor_titles:
            title_tokens = set(title.split())
            if clean_kw in title or (len(kw_tokens) >= 2 and kw_tokens.issubset(title_tokens)):
                matched_titles.append(title)

        is_question = any(clean_kw.startswith(q) for q in ("how", "what", "which", "why", "when", "can", "is"))
        is_comparison = any(term in clean_kw for term in (" vs ", " versus ", " compared to ", " or "))
        is_audience = any(clean_kw.startswith(a) or f" {a}" in clean_kw for a in ("for beginners", "for pros", "for students", "for budget", "for black cars"))

        if not matched_titles:
            if is_question:
                gap_type = "QUESTION_GAP"
                rationale = f"Question query has 0 matching titles among {self.sample_size} competitor videos."
            elif is_audience:
                gap_type = "AUDIENCE_GAP"
                rationale = f"Audience-specific angle not found among {self.sample_size} competitor videos."
            elif is_comparison:
                gap_type = "COMPARISON_GAP"
                rationale = f"Direct comparison angle absent from {self.sample_size} competitor videos."
            else:
                gap_type = "UNCOVERED_KEYWORD"
                rationale = f"Keyword absent from all {self.sample_size} competitor video titles in the sample."

            return {
                "is_gap": True,
                "gap_label": "Potential Content Gap",
                "gap_type": gap_type,
                "sample_size": self.sample_size,
                "evidence_rationale": rationale,
                "analysis_method": "Empirical Title Matching vs Sample",
            }
        else:
            return {
                "is_gap": False,
                "gap_label": "Covered in Competitor Sample",
                "gap_type": "COVERED_IN_SAMPLE",
                "sample_size": self.sample_size,
                "matches_count": len(matched_titles),
                "evidence_rationale": f"Found {len(matched_titles)} competitor titles covering this topic.",
                "analysis_method": "Empirical Title Matching vs Sample",
            }


class OpportunityScorer:
    """Calculates an explainable 0–100 heuristic Opportunity Score with confidence rating."""

    def __init__(
        self,
        weight_relevance: float = 0.25,
        weight_audience: float = 0.20,
        weight_intent: float = 0.15,
        weight_supporting: float = 0.15,
        weight_gap: float = 0.15,
        weight_format: float = 0.10,
    ) -> None:
        self.w_relevance = weight_relevance
        self.w_audience = weight_audience
        self.w_intent = weight_intent
        self.w_supporting = weight_supporting
        self.w_gap = weight_gap
        self.w_format = weight_format

    def calculate_score(
        self,
        keyword: str,
        seed_keyword: str,
        target_audience: str,
        search_intent: str,
        content_format: str,
        supporting_keywords: List[str],
        gap_info: Dict[str, Any],
        has_video_sample: bool = True,
    ) -> Tuple[float, str, Dict[str, Any]]:
        """Calculate a transparent 0-100 score, confidence label, and breakdown."""
        clean_kw = keyword.lower().strip()
        clean_seed = seed_keyword.lower().strip()

        # 1. Relevance to seed (0-25 pts)
        if clean_kw == clean_seed:
            rel_score = 25.0
        elif clean_seed in clean_kw:
            rel_score = 22.0
        else:
            common_words = set(clean_kw.split()) & set(clean_seed.split())
            rel_score = min(20.0, len(common_words) * 7.0)

        # 2. Target audience match (0-20 pts)
        clean_aud = target_audience.lower().strip()
        if clean_aud == "general audience":
            aud_score = 15.0  # Neutral baseline
        elif clean_aud in clean_kw or ("beginner" in clean_aud and "beginner" in clean_kw):
            aud_score = 20.0
        else:
            aud_score = 10.0

        # 3. Intent clarity (0-15 pts)
        clear_intents = {"How-to / Tutorial", "Comparison / VS", "Review", "Problem-solving", "Best / Top list"}
        if search_intent in clear_intents:
            intent_score = 15.0
        elif search_intent in ("Informational", "Question"):
            intent_score = 12.0
        else:
            intent_score = 8.0

        # 4. Supporting keyword evidence count (0-15 pts)
        sup_count = len(supporting_keywords)
        if sup_count >= 5:
            sup_score = 15.0
        elif sup_count >= 3:
            sup_score = 11.0
        elif sup_count >= 1:
            sup_score = 7.0
        else:
            sup_score = 3.0

        # 5. Gap evidence in video sample (0-15 pts)
        if gap_info.get("is_gap"):
            gap_score = 15.0
        elif not has_video_sample:
            gap_score = 6.0  # Neutral when video data is unavailable
        else:
            gap_score = 4.0  # Already heavily covered in competitor sample

        # 6. Content format fit (0-10 pts)
        if content_format and content_format != "General":
            format_score = 10.0
        else:
            format_score = 6.0

        total = round(rel_score + aud_score + intent_score + sup_score + gap_score + format_score, 1)
        total = max(0.0, min(100.0, total))

        # Confidence level derived from evidence completeness
        if has_video_sample and sup_count >= 3:
            confidence = "High Evidence"
        elif has_video_sample or sup_count >= 2:
            confidence = "Moderate Evidence"
        else:
            confidence = "Low / Lexical Only"

        breakdown = {
            "relevance_score": rel_score,
            "audience_score": aud_score,
            "intent_score": intent_score,
            "supporting_score": sup_score,
            "gap_score": gap_score,
            "format_score": format_score,
            "total_score": total,
            "inputs_from_retrieved_data": [
                f"Seed match: '{clean_seed}'",
                f"Supporting keywords count: {sup_count}",
                f"Video sample gap verified: {'Yes' if has_video_sample else 'No (offline)'}",
            ],
            "inputs_from_user_preferences": [
                f"Selected Audience: '{target_audience}'",
                f"Selected Format: '{content_format}'",
            ],
            "formula_explanation": (
                "Score = Seed Relevance (0–25) + Audience Match (0–20) + Intent Clarity (0–15) + "
                "Supporting Evidence (0–15) + Gap Evidence (0–15) + Format Fit (0–10). "
                "Represents content planning potential, NOT ranking probability or search volume."
            ),
        }

        return total, confidence, breakdown


class VideoTopicGenerator:
    """Generates structured, original topic opportunities based on keyword and video research data."""

    def __init__(self, scorer: Optional[OpportunityScorer] = None) -> None:
        self.scorer = scorer or OpportunityScorer()

    def generate_topics_for_keywords(
        self,
        keywords: List[str],
        seed_keyword: str,
        target_audience: str = "General Audience",
        preferred_format: str = "All Formats",
        competitor_titles: Optional[List[str]] = None,
        max_topics: int = 15,
        project_id: Optional[int] = None,
    ) -> List[ContentOpportunityItem]:
        """Generate structured content opportunities from a collection of researched keywords."""
        if not keywords:
            return []

        gap_detector = ContentGapDetector(competitor_titles)
        has_video_sample = gap_detector.is_video_data_available()
        current_year = datetime.now(timezone.utc).year

        # Normalize and deduplicate keywords
        unique_kws: List[str] = []
        seen: Set[str] = set()
        for k in keywords:
            clean = k.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                unique_kws.append(clean)

        opportunities: List[ContentOpportunityItem] = []

        format_templates = [
            ("Step-by-step Guide", "How to {kw}: Complete Step-by-Step Guide", "How-to / Tutorial"),
            ("Beginner Tutorial", "Complete Beginner's Guide to {kw}", "How-to / Tutorial"),
            ("Top 5 / Top 10", f"Top 5 Best {{kw}} Options ({current_year})", "Best / Top list"),
            ("Common Mistakes", "5 Huge {kw} Mistakes to Avoid", "Problem-solving"),
            ("Product Review", "The Truth About {kw}: Full Hands-On Review", "Review"),
            ("Comparison", "{kw} vs Common Alternatives: Full Comparison", "Comparison / VS"),
            ("Buying Guide", "{kw} Buyer's Guide: What's Actually Worth Buying?", "Buying / Commercial intent"),
            ("Frequently Asked Questions", "Your Top Questions About {kw} Answered", "Question"),
        ]

        # Filter by preferred format if specified
        if preferred_format and preferred_format != "All Formats":
            format_templates = [
                fmt for fmt in format_templates if fmt[0].lower() == preferred_format.lower()
            ] or format_templates

        for idx, kw in enumerate(unique_kws):
            if len(opportunities) >= max_topics:
                break

            template_idx = idx % len(format_templates)
            fmt_name, title_pattern, intent = format_templates[template_idx]

            # Title topic
            topic_title = title_pattern.format(kw=kw.title())

            # Find closely related supporting keywords
            tokens = set(kw.lower().split())
            supporting = [
                other for other in unique_kws
                if other != kw and bool(set(other.lower().split()) & tokens)
            ][:5]

            # Gap detection
            gap_info = gap_detector.detect_gap(kw, intent=intent)

            # Scoring
            score, confidence, breakdown = self.scorer.calculate_score(
                keyword=kw,
                seed_keyword=seed_keyword,
                target_audience=target_audience,
                search_intent=intent,
                content_format=fmt_name,
                supporting_keywords=supporting,
                gap_info=gap_info,
                has_video_sample=has_video_sample,
            )

            priority = "High" if score >= 75.0 else ("Medium" if score >= 50.0 else "Low")

            evidence_dict = {
                "gap_analysis": gap_info,
                "competitor_sample_size": gap_detector.sample_size,
                "supporting_keywords_count": len(supporting),
            }

            opp = ContentOpportunityItem(
                project_id=project_id,
                topic=topic_title,
                primary_keyword=kw,
                supporting_keywords=supporting,
                target_audience=target_audience,
                search_intent=intent,
                content_format=fmt_name,
                opportunity_score=score,
                confidence_level=confidence,
                score_breakdown=breakdown,
                evidence=evidence_dict,
                status="Idea",
                priority=priority,
            )
            opportunities.append(opp)

        return opportunities


class TitleHookWorkshop:
    """Tool for generating diverse title options, running quality checks, and creating video hooks and outlines."""

    CLICKBAIT_TERMS = {
        "guaranteed", "100%", "insane", "miracle", "secret", "never seen before",
        "life changing", "destroyed", "shocking", "exposed", "overnight",
    }

    def generate_title_variations(
        self,
        keyword: str,
        target_audience: str = "General Audience",
        current_year: Optional[int] = None,
    ) -> Dict[str, str]:
        """Generate 7 categorized title options for a selected topic or keyword."""
        year = current_year or datetime.now(timezone.utc).year
        clean_k = keyword.strip().title()
        aud = target_audience.strip()

        return {
            "Informational": f"The Complete Guide to {clean_k} ({year})",
            "How-To / Practical": f"How to Master {clean_k} in 4 Easy Steps",
            "Comparison / VS": f"{clean_k} vs the Competition: Which Is Actually Worth It?",
            "Review / Hands-On": f"We Tested {clean_k}: Real Results & Review",
            "Question-Based": f"Is {clean_k} Still Worth It in {year}?",
            "List-Based": f"Top 5 {clean_k} Tips That Actually Work",
            "Audience-Specific": f"{clean_k} for {aud}: The Ultimate Playbook",
        }

    # Alias for flexibility
    generate_title_options = generate_title_variations

    def check_title_quality(self, title: str, primary_keyword: str) -> TitleQualityCheck:
        """Run a transparent 7-point quality checklist on a proposed title."""
        t_lower = title.lower()
        k_lower = primary_keyword.lower().strip()
        length = len(title)

        feedback: List[str] = []
        score = 100.0

        # 1. Primary Keyword Relevance
        k_tokens = set(k_lower.split())
        t_tokens = set(t_lower.split())
        passes_rel = k_lower in t_lower or (len(k_tokens) > 1 and len(k_tokens & t_tokens) >= len(k_tokens) - 1)
        if not passes_rel:
            score -= 25.0
            feedback.append("Title does not clearly feature the primary keyword.")

        # 2. Length & Clarity (Ideal 40 - 70 characters)
        passes_clarity = 30 <= length <= 80
        if length > 70:
            score -= 10.0
            feedback.append("Title exceeds 70 characters and may truncate on mobile displays.")
        elif length < 30:
            score -= 10.0
            feedback.append("Title is very short and may lack sufficient context.")

        # 3. Specificity
        has_numbers = bool(re.search(r"\d+", title))
        has_qualifiers = any(w in t_lower for w in ("guide", "review", "steps", "best", "tips", "tested"))
        passes_spec = has_numbers or has_qualifiers
        if not passes_spec:
            score -= 10.0
            feedback.append("Consider adding specific numbers, timeframes, or format indicators.")

        # 4. Audience Fit
        passes_aud = True

        # 5. Unsupported Claims / Clickbait Terms
        found_clickbait = [term for term in self.CLICKBAIT_TERMS if term in t_lower]
        has_unsupported = len(found_clickbait) > 0
        if has_unsupported:
            score -= 20.0
            feedback.append(f"Contains potentially misleading or unsupported words: {', '.join(found_clickbait)}.")

        # 6. Excessive Word Repetition
        words = [w for w in re.sub(r"[^\w\s]", "", t_lower).split() if len(w) > 2]
        repeated = [w for w in set(words) if words.count(w) > 2]
        has_repetition = len(repeated) > 0
        if has_repetition:
            score -= 15.0
            feedback.append(f"Contains excessive word repetition: {', '.join(repeated)}.")

        # 7. Misleading wording
        has_misleading = has_unsupported

        score = max(0.0, min(100.0, score))
        if not feedback:
            feedback.append("Great title! Well-balanced, specific, and adheres to YouTube best practices.")

        return TitleQualityCheck(
            title=title,
            score=score,
            passes_relevance=passes_rel,
            passes_clarity=passes_clarity,
            passes_specificity=passes_spec,
            passes_audience_fit=passes_aud,
            has_unsupported_claims=has_unsupported,
            has_excessive_repetition=has_repetition,
            has_misleading_wording=has_misleading,
            feedback=feedback,
        )

    def generate_hook_and_outline(
        self,
        title: str,
        keyword: str,
        target_audience: str = "General Audience",
    ) -> Dict[str, Any]:
        """Generate a concise script hook (first 15 seconds) and a 3-part video outline."""
        clean_k = keyword.strip()
        hook = (
            f"If you're looking to master {clean_k}, there is one major mistake that most {target_audience.lower()} "
            f"make right at the beginning. In this video, we're breaking down exactly how to do it right, "
            f"step-by-step, with real demonstrations."
        )

        outline = [
            f"0:00 - Introduction & The #{clean_k} Problem (The Hook)",
            f"1:15 - Core Concepts Every {target_audience} Needs to Know",
            f"3:30 - Step-by-Step Walkthrough & Hands-on Demonstration",
            f"7:00 - Common Pitfalls & How to Avoid Wasting Money",
            f"9:30 - Final Recommendations & Next Action Steps",
        ]

        return {
            "hook": hook,
            "outline": outline,
            "title": title,
            "primary_keyword": keyword,
        }


class ContentBriefGenerator:
    """Generates complete, 15-point editable content briefs for content opportunities (Step 7)."""

    def generate_brief(
        self,
        opportunity: ContentOpportunityItem,
        working_title: Optional[str] = None,
    ) -> ContentBrief:
        """Create a complete 15-point structured content brief from an opportunity item."""
        title = working_title or opportunity.topic
        pk = opportunity.primary_keyword
        aud = opportunity.target_audience
        intent = opportunity.search_intent

        problem = f"Viewers searching for '{pk}' struggle with confusing advice, lack of hands-on proof, and outdated methods."
        unique_angle = (
            f"A fresh, modern breakdown specifically tailored for {aud}, backed by transparent testing and zero marketing hype."
        )
        intro = (
            f"Hook the viewer by acknowledging their biggest frustration with {pk}, then state exactly what actionable result they will achieve by the end of the video."
        )

        main_sections = [
            f"1. Executive Summary & Why {pk.title()} Matters Today",
            f"2. Foundation & Prerequisites for {aud}",
            f"3. Practical Step-by-Step Implementation & Workflow",
            f"4. Comparative Evaluation of Common Alternatives",
            f"5. Key Mistakes to Avoid & Pro Troubleshooting Tips",
            f"6. Final Verdict & Action Checklist",
        ]

        examples_to_research = [
            f"Collect 2-3 real-world pricing examples or benchmarks for {pk}.",
            f"Verify current manufacturer guidelines or industry standards.",
            f"Find 1 practical before-and-after demonstration or case study.",
        ]

        visual_elements = [
            "Clear split-screen comparison cards highlighting key trade-offs.",
            "Text overlays and callout graphics for technical specifications.",
            "Close-up B-roll footage showing the practical steps in real-time.",
            "Numbered progress bar or chapter title cards on screen.",
        ]

        faqs = [
            f"Is {pk} suitable for beginners?",
            f"How much does {pk} typically cost or require in time investment?",
            f"What is the most common mistake people make with {pk}?",
        ]

        conclusion = (
            f"Summarize the top 3 actionable takeaways for {pk}. Tell viewers to check the description for resources, "
            f"and prompt them to watch the related video on your channel."
        )

        fact_checking = [
            "Verify all referenced statistics against official, primary sources.",
            "Double-check all product model names, pricing, and availability.",
            "Mark unverified personal opinions clearly so viewers know they are editorial experience.",
        ]

        source_refs = [
            f"Seed keyword discovery query: '{pk}'",
            f"Search intent classified as: {intent}",
        ]
        if opportunity.supporting_keywords:
            source_refs.append(f"Supporting keywords: {', '.join(opportunity.supporting_keywords)}")

        return ContentBrief(
            opportunity_id=opportunity.id,
            working_title=title,
            primary_keyword=pk,
            supporting_keywords=list(opportunity.supporting_keywords),
            target_audience=aud,
            search_intent=intent,
            viewer_problem=problem,
            unique_angle=unique_angle,
            proposed_intro=intro,
            main_sections=main_sections,
            examples_to_research=examples_to_research,
            visual_elements=visual_elements,
            faqs=faqs,
            conclusion_cta=conclusion,
            fact_checking_checklist=fact_checking,
            source_references=source_refs,
        )


class TopicOverlapDetector:
    """Checks for keyword cannibalization and topic duplication across planned video topics (Step 9)."""

    STOPWORDS = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "how", "what", "which", "why", "when", "is", "it", "top", "best", "guide", "2024", "2025", "2026",
    }

    def tokenize(self, text: str) -> Set[str]:
        """Normalize and tokenize text into informative word tokens."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        return {w for w in clean.split() if len(w) > 1 and w not in self.STOPWORDS}

    def calculate_similarity(self, title_a: str, title_b: str, kw_a: str, kw_b: str) -> Tuple[float, str, List[str]]:
        """Calculate Jaccard similarity between two topics and determine overlap type."""
        clean_kwa = kw_a.strip().lower()
        clean_kwb = kw_b.strip().lower()

        # Identical primary keyword
        if clean_kwa == clean_kwb:
            shared = [clean_kwa]
            return (1.0, "Shared Primary Keyword", shared)

        tokens_a = self.tokenize(f"{title_a} {kw_a}")
        tokens_b = self.tokenize(f"{title_b} {kw_b}")

        if not tokens_a or not tokens_b:
            return (0.0, "None", [])

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union)

        overlap_type = "None"
        if jaccard >= 0.6:
            overlap_type = "High Token Overlap"
        elif len(intersection) >= 2:
            overlap_type = "Shared Supporting Keywords"

        return (round(jaccard, 2), overlap_type, sorted(list(intersection)))

    def check_overlap(
        self,
        items: List[Dict[str, Any]],
        similarity_threshold: float = 0.40,
    ) -> List[TopicOverlapResult]:
        """Scan a list of planned topics or opportunities and flag potential cannibalization."""
        results: List[TopicOverlapResult] = []
        n = len(items)

        for i in range(n):
            for j in range(i + 1, n):
                item_a = items[i]
                item_b = items[j]

                title_a = item_a.get("title") or item_a.get("topic", "")
                title_b = item_b.get("title") or item_b.get("topic", "")
                kw_a = item_a.get("primary_keyword", "")
                kw_b = item_b.get("primary_keyword", "")

                sim, o_type, shared = self.calculate_similarity(title_a, title_b, kw_a, kw_b)

                if sim >= similarity_threshold or o_type == "Shared Primary Keyword":
                    warn = (
                        f"Potential keyword cannibalization detected: '{title_a}' and '{title_b}' "
                        f"share significant semantic focus (similarity {int(sim*100)}%). "
                        f"Publishing both may cause your videos to compete against each other in YouTube search."
                    )
                    results.append(
                        TopicOverlapResult(
                            topic_a=title_a,
                            topic_b=title_b,
                            similarity_score=sim,
                            overlap_type=o_type,
                            shared_keywords=shared,
                            warning_message=warn,
                            resolution="Unresolved",
                        )
                    )

        return results

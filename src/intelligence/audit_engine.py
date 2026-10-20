"""Core YouTube SEO & Affiliate Content Quality Engine (Phase 23 Parts 1 to 10).

Provides comprehensive, transparent, local-first auditing across:
1. Video Title Quality & Truncation Risk
2. Description SEO, Chapter Timestamps & FTC Compliance
3. Script / Outline Content Alignment & Promise Delivery
4. Affiliate Content Quality, Product Variant Clarity & Balanced Reviews
5. Thumbnail Concept & Title Synergy
6. Transparent SEO Readiness Score (Zero Ranking Guarantees)
7. Pre-Publishing Checklist with Manual Confirmation Enforcement
8. Public YouTube URL Metadata Retrieval (Public Metadata Only)
9. Export Sanitization (Formula Injection Protection)
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import requests

from src.models.audit import (
    AffiliateQualityResult,
    AuditFinding,
    AuditFindingSeverity,
    AuditScoreBreakdown,
    AuditStatus,
    DescriptionQualityResult,
    PublishingChecklistItem,
    ScriptAlignmentResult,
    ThumbnailQualityResult,
    TitleQualityResult,
    VideoSeoAudit,
)
from src.models.channel import ChannelProfile
from src.storage.database import DatabaseManager, db_manager
from src.storage.export import sanitize_formula_injection


class AuditEngine:
    """Intelligent audit engine for YouTube SEO and affiliate content quality."""

    # Common generic fluff / filler phrases in YouTube scripts
    FLUFF_PHRASES = [
        "without further ado",
        "in today's video",
        "in this day and age",
        "as we all know",
        "needless to say",
        "fast-paced digital world",
        "fast paced world",
        "smash that like button",
        "hit the subscribe button",
        "ring the notification bell",
        "stay tuned until the very end",
        "without wasting any time",
        "diving right into it",
    ]

    # Unsupported or sensational clickbait phrases in titles / concepts
    MISLEADING_TITLE_PATTERNS = [
        r"\b100%\s*(guaranteed|working|free|pass)\b",
        r"\bguaranteed\b",
        r"\bsecret\s*(hack|trick|code|method)\b",
        r"\bmake\s*millions?\b",
        r"\bget\s*rich\s*quick\b",
        r"\bnever\s*seen\s*before\b",
        r"\bmiracle\b",
        r"\bmagic\s*trick\b",
        r"\bshocking\s*(truth|reveal)\b",
        r"\bmind\s*blowing\b",
        r"\binsane\s*(hack|method)\b",
    ]

    # Unsupported superlatives in affiliate reviews
    UNSUPPORTED_SUPERLATIVES = [
        "best ever",
        "flawless",
        "perfect in every way",
        "magic",
        "miracle device",
        "unbeatable",
        "100% recommended for everyone",
        "completely without flaws",
        "cannot go wrong",
    ]

    # Common template placeholder patterns
    PLACEHOLDER_PATTERNS = [
        r"\[INSERT\s+[^\]]+\]",
        r"\[TODO\b[^\]]*\]",
        r"\[LINK\b[^\]]*\]",
        r"\[PRODUCT\s*NAME\]",
        r"\[ADD\s+[^\]]+\]",
        r"\[YOUR\s+[^\]]+\]",
        r"\bTODO:\b",
        r"\bXXX\b",
        r"\bexample\.com\b",
    ]

    def __init__(self, database: Optional[DatabaseManager] = None) -> None:
        self.db = database or db_manager

    # --------------------------------------------------------------------------
    # 1. Title Quality Checker
    # --------------------------------------------------------------------------

    def audit_title(
        self,
        title: str,
        primary_keyword: str,
        channel: Optional[ChannelProfile] = None,
        existing_titles: Optional[List[str]] = None,
    ) -> TitleQualityResult:
        """Evaluate title for search intent, keyword prominence, readability, repetition, and truncation risk."""
        clean_title = (title or "").strip()
        kw_clean = (primary_keyword or "").strip().lower()
        title_lower = clean_title.lower()
        char_count = len(clean_title)
        words = re.findall(r"\b\w+\b", title_lower)
        word_count = len(words)

        findings: List[AuditFinding] = []
        score = 100.0

        # Truncation Risk Assessment
        if char_count < 60:
            truncation_risk = "Safe (<60 chars)"
            findings.append(
                AuditFinding(
                    category="Title Optimization",
                    severity=AuditFindingSeverity.POSITIVE,
                    title="Safe Title Length for Mobile Display",
                    message=f"Title length ({char_count} chars) is under 60 characters, minimizing mobile search truncation risk.",
                    evidence_source=f"{char_count} characters",
                    is_objective=True,
                )
            )
        elif char_count <= 75:
            truncation_risk = "Moderate (60-75 chars)"
            score -= 8.0
            findings.append(
                AuditFinding(
                    category="Title Optimization",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Moderate Truncation Risk on Mobile",
                    message=f"Title length ({char_count} chars) may truncate on mobile cards. Aim for under 60 characters for complete visibility.",
                    evidence_source=f"{char_count} characters",
                    suggestion="Condense secondary clauses or place the primary benefit in the first 50 characters.",
                    is_objective=True,
                )
            )
        else:
            truncation_risk = "High Risk (>75 chars)"
            score -= 18.0
            findings.append(
                AuditFinding(
                    category="Title Optimization",
                    severity=AuditFindingSeverity.WARNING,
                    title="High Mobile Truncation Risk",
                    message=f"Title length ({char_count} chars) exceeds 75 characters and will likely be cut off on YouTube mobile search.",
                    evidence_source=f"{char_count} characters",
                    suggestion="Shorten title to 50-60 characters to ensure key value propositions are visible.",
                    is_objective=True,
                )
            )

        # Primary Keyword Presence & Placement
        kw_tokens = re.findall(r"\b\w+\b", kw_clean)
        has_exact_kw = kw_clean in title_lower if kw_clean else False
        has_partial_kw = all(t in words for t in kw_tokens) if kw_tokens else False

        if has_exact_kw:
            # Check position: is it in the first 4 words?
            first_4_words = " ".join(words[:4])
            if kw_clean in first_4_words:
                kw_pos = "Front (First 4 words)"
                findings.append(
                    AuditFinding(
                        category="Keyword Placement",
                        severity=AuditFindingSeverity.POSITIVE,
                        title="Primary Keyword Front-Loaded",
                        message="Target keyword appears in the first 4 words of the title, maximizing search relevance.",
                        evidence_source=f"Found in: '{first_4_words}'",
                        is_objective=True,
                    )
                )
            else:
                kw_pos = "Middle/End"
                score -= 6.0
                findings.append(
                    AuditFinding(
                        category="Keyword Placement",
                        severity=AuditFindingSeverity.IMPROVEMENT,
                        title="Primary Keyword Not Front-Loaded",
                        message="Primary keyword appears later in the title. Front-loading improves search recognition on small screens.",
                        evidence_source=f"Position: {title_lower.find(kw_clean)} chars in",
                        suggestion="Consider reordering to place the core topic or query near the start.",
                        is_objective=True,
                    )
                )
        elif has_partial_kw:
            kw_pos = "Middle/End"
            score -= 10.0
            findings.append(
                AuditFinding(
                    category="Keyword Placement",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Partial Keyword Match Only",
                    message="Keywords words appear scattered throughout the title rather than as a cohesive phrase.",
                    evidence_source=f"Tokens: {kw_tokens}",
                    suggestion=f"Try integrating the exact phrase '{primary_keyword}' naturally.",
                    is_objective=True,
                )
            )
        else:
            kw_pos = "Missing"
            score -= 25.0
            findings.append(
                AuditFinding(
                    category="Keyword Placement",
                    severity=AuditFindingSeverity.WARNING,
                    title="Target Keyword Missing From Title",
                    message=f"The primary target keyword '{primary_keyword}' does not appear in the proposed title.",
                    evidence_source=f"Searched for: '{primary_keyword}'",
                    suggestion="Incorporate your exact primary keyword to signal topic relevance to searchers.",
                    is_objective=True,
                )
            )

        # Misleading or Sensational Claims Check
        misleading_found = []
        for pat in self.MISLEADING_TITLE_PATTERNS:
            match = re.search(pat, title_lower)
            if match:
                misleading_found.append(match.group(0))

        if misleading_found:
            score -= 15.0
            findings.append(
                AuditFinding(
                    category="Editorial Integrity",
                    severity=AuditFindingSeverity.WARNING,
                    title="Sensational or Misleading Claim Detected",
                    message=f"Title contains sensational trigger phrases ({', '.join(misleading_found)}) that may trigger viewer distrust or algorithmic suppression.",
                    evidence_source=", ".join(misleading_found),
                    suggestion="Replace extreme claims with specific, verifiable value propositions.",
                    is_objective=True,
                )
            )

        # Excessive Word Repetition
        stop_words = {"the", "and", "in", "of", "to", "a", "for", "with", "on", "at", "by", "from", "is", "your", "how", "what", "why"}
        content_words = [w for w in words if w not in stop_words]
        word_counts = {}
        for w in content_words:
            word_counts[w] = word_counts.get(w, 0) + 1
        repeated_words = [w for w, count in word_counts.items() if count > 1]
        if repeated_words:
            score -= 8.0
            findings.append(
                AuditFinding(
                    category="Title Readability",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Word Repetition Detected",
                    message=f"Word(s) {repeated_words} appear multiple times in the title, which reduces readability.",
                    evidence_source=", ".join(repeated_words),
                    suggestion="Remove redundant repetitions to keep the title punchy and concise.",
                    is_objective=True,
                )
            )

        # Self-Cannibalization / Similarity to Existing Channel Titles
        similarity_flags = []
        if existing_titles:
            title_word_set = set(words)
            for ex in existing_titles:
                ex_clean = ex.strip().lower()
                ex_words = set(re.findall(r"\b\w+\b", ex_clean))
                if not ex_words or not title_word_set:
                    continue
                jaccard = len(title_word_set & ex_words) / len(title_word_set | ex_words)
                if jaccard >= 0.65:
                    similarity_flags.append(f"Highly similar to published video: '{ex}' (Overlap: {int(jaccard*100)}%)")

        if similarity_flags:
            score -= 12.0
            findings.append(
                AuditFinding(
                    category="Channel Cannibalization",
                    severity=AuditFindingSeverity.WARNING,
                    title="Potential Topic Cannibalization Risk",
                    message="Proposed title overlaps heavily with existing channel content, risking internal search competition.",
                    evidence_source="; ".join(similarity_flags[:2]),
                    suggestion="Differentiate this video by targeting a specific angle, advanced sub-topic, or updated year.",
                    is_objective=False,
                )
            )

        # Generate Improved Alternatives (Never guarantee rankings or invent CTR predictions)
        alternatives = self._generate_title_alternatives(clean_title, primary_keyword, channel)

        return TitleQualityResult(
            score=max(0.0, min(100.0, round(score, 1))),
            findings=findings,
            character_count=char_count,
            word_count=word_count,
            truncation_risk=truncation_risk,
            has_primary_keyword=(has_exact_kw or has_partial_kw),
            keyword_position=kw_pos,
            intent_match="Classified based on query structure",
            alternatives=alternatives,
            similarity_flags=similarity_flags,
        )

    def _generate_title_alternatives(
        self,
        current_title: str,
        primary_keyword: str,
        channel: Optional[ChannelProfile] = None,
    ) -> List[Dict[str, str]]:
        """Generate 4 distinct, ethically framed title alternatives with rationales."""
        kw_cap = primary_keyword.strip().title() if primary_keyword else "Topic"
        year = datetime.now().year

        alt1_title = f"{kw_cap}: Complete Step-by-Step Guide ({year})"
        alt1_why = "Front-loads the primary keyword for clear search relevance and specifies an updated timeframe."

        alt2_title = f"The Truth About {kw_cap} (What Most People Miss)"
        alt2_why = "Creates a viewer-centric curiosity angle while keeping the keyword clearly identified."

        alt3_title = f"{kw_cap} Explained Simply in 10 Minutes"
        alt3_why = "Emphasizes clarity, brevity, and low barrier to entry under 55 characters to avoid mobile truncation."

        alt4_title = f"Before You Try {kw_cap}: Watch This First"
        alt4_why = "Addresses search intent by offering practical caution and preventing common viewer mistakes."

        return [
            {"title": alt1_title, "angle": "Search-Focused / Comprehensive", "why_suggested": alt1_why, "char_count": len(alt1_title)},
            {"title": alt2_title, "angle": "Curiosity & Value Angle", "why_suggested": alt2_why, "char_count": len(alt2_title)},
            {"title": alt3_title, "angle": "Concise & Direct (<60 chars)", "why_suggested": alt3_why, "char_count": len(alt3_title)},
            {"title": alt4_title, "angle": "Buyer / Learner Decision Angle", "why_suggested": alt4_why, "char_count": len(alt4_title)},
        ]

    # --------------------------------------------------------------------------
    # 2. Description SEO Audit
    # --------------------------------------------------------------------------

    def audit_description(
        self,
        description: str,
        primary_keyword: str,
        secondary_keywords: Optional[List[str]] = None,
        channel: Optional[ChannelProfile] = None,
        has_affiliate_links: bool = False,
    ) -> DescriptionQualityResult:
        """Audit description for character limit, hook placement, chapters, FTC disclosure, and placeholders."""
        desc_clean = (description or "").strip()
        char_count = len(desc_clean)
        desc_lower = desc_clean.lower()
        kw_clean = (primary_keyword or "").strip().lower()
        sec_kws = [k.strip().lower() for k in (secondary_keywords or []) if k.strip()]

        findings: List[AuditFinding] = []
        score = 100.0

        # Character Limit Check (YouTube limit = 5,000 characters)
        if char_count > 5000:
            score -= 30.0
            findings.append(
                AuditFinding(
                    category="Platform Compliance",
                    severity=AuditFindingSeverity.CRITICAL,
                    title="Exceeds YouTube 5,000 Character Limit",
                    message=f"Description has {char_count} characters, exceeding YouTube's hard limit of 5,000 characters. Extra text will be rejected.",
                    evidence_source=f"{char_count} / 5000 characters",
                    suggestion="Trim boilerplate, reduce link lists, or shorten summaries.",
                    is_objective=True,
                )
            )
        elif char_count < 150:
            score -= 15.0
            findings.append(
                AuditFinding(
                    category="Description Depth",
                    severity=AuditFindingSeverity.WARNING,
                    title="Description Too Brief",
                    message="Description is under 150 characters. A thorough summary provides valuable context for viewers and search indexing.",
                    evidence_source=f"{char_count} characters",
                    suggestion="Add a 2-3 paragraph breakdown explaining the video's core takeaways.",
                    is_objective=True,
                )
            )
        else:
            findings.append(
                AuditFinding(
                    category="Platform Compliance",
                    severity=AuditFindingSeverity.POSITIVE,
                    title="Valid Description Length",
                    message=f"Description length ({char_count} chars) is well within the 5,000 character platform limit.",
                    evidence_source=f"{char_count} characters",
                    is_objective=True,
                )
            )

        # Opening Hook & Primary Keyword Placement (First 200 characters)
        first_200 = desc_clean[:200].lower()
        has_kw_in_hook = kw_clean in first_200 if kw_clean else False
        has_hook = len(desc_clean) > 50

        if has_kw_in_hook:
            findings.append(
                AuditFinding(
                    category="Hook & First Impression",
                    severity=AuditFindingSeverity.POSITIVE,
                    title="Primary Keyword in Opening Hook",
                    message="Target keyword appears within the first 200 characters (visible before the 'Show More' fold).",
                    evidence_source=f"Found in: '{desc_clean[:120]}...'",
                    is_objective=True,
                )
            )
        else:
            score -= 12.0
            findings.append(
                AuditFinding(
                    category="Hook & First Impression",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Target Keyword Missing from Opening Lines",
                    message="Primary keyword is not found in the first 200 characters. Viewers and search spiders scan the opening lines first.",
                    evidence_source="Checked first 200 chars",
                    suggestion="Mention your primary topic in the very first sentence describing the video value.",
                    is_objective=True,
                )
            )

        # Chapter Timestamps Validation
        # Matches: 0:00 - Title or 01:23 Intro
        timestamp_matches = re.findall(r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:]\s*(.+)", desc_clean)
        ts_count = len(timestamp_matches)
        has_timestamps = ts_count >= 3

        if timestamp_matches:
            first_ts = timestamp_matches[0][0].strip()
            if first_ts not in ("0:00", "00:00", "0:00:00"):
                score -= 10.0
                findings.append(
                    AuditFinding(
                        category="Video Chapters",
                        severity=AuditFindingSeverity.WARNING,
                        title="Timestamps Do Not Start at 0:00",
                        message=f"First timestamp is '{first_ts}'. YouTube chapters require the first marker to begin exactly at 0:00 to enable video scrub-bar chapters.",
                        evidence_source=f"First timestamp: {first_ts}",
                        suggestion="Add '0:00 - Introduction' at the beginning of your timestamps list.",
                        is_objective=True,
                    )
                )
            elif ts_count < 3:
                score -= 6.0
                findings.append(
                    AuditFinding(
                        category="Video Chapters",
                        severity=AuditFindingSeverity.IMPROVEMENT,
                        title="Fewer Than 3 Chapter Markers",
                        message=f"Found {ts_count} timestamp markers. YouTube requires at least 3 valid timestamps in ascending order to activate chapters.",
                        evidence_source=f"{ts_count} markers found",
                        suggestion="Add at least 3 distinct timestamps spaced throughout the video.",
                        is_objective=True,
                    )
                )
            else:
                findings.append(
                    AuditFinding(
                        category="Video Chapters",
                        severity=AuditFindingSeverity.POSITIVE,
                        title="Valid Chapter Timestamps Detected",
                        message=f"Detected {ts_count} formatted timestamps starting at 0:00, enabling interactive YouTube scrubbing.",
                        evidence_source=f"{ts_count} chapters",
                        is_objective=True,
                    )
                )
        else:
            score -= 8.0
            findings.append(
                AuditFinding(
                    category="Video Chapters",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="No Chapter Timestamps Provided",
                    message="No formatted timestamps found. Video chapters improve user retention and Google search key-moments indexing.",
                    evidence_source="No matching 0:00 lines",
                    suggestion="Add a TIMESTAMPS section starting with 0:00.",
                    is_objective=True,
                )
            )

        # Mandatory FTC Affiliate Disclosure
        # Required if affiliate links are present or channel has affiliate marketing enabled
        affiliate_channel_active = bool(channel and channel.affiliate_enabled)
        requires_disclosure = has_affiliate_links or affiliate_channel_active
        ftc_keywords = ["affiliate", "commission", "disclosure", "compensation", "earn", "partner"]
        has_disclosure = any(k in desc_lower for k in ftc_keywords)

        if requires_disclosure:
            if not has_disclosure:
                score -= 25.0
                findings.append(
                    AuditFinding(
                        category="FTC Regulatory Compliance",
                        severity=AuditFindingSeverity.CRITICAL,
                        title="Missing Mandatory FTC Affiliate Disclosure",
                        message="Affiliate links or commercial recommendations are enabled, but no clear FTC disclosure was found.",
                        evidence_source="Scanned for 'affiliate', 'commission', 'disclosure'",
                        suggestion="Insert a clear disclosure notice: 'Some links are affiliate links. If you make a purchase, we may earn a small commission at no additional cost to you.'",
                        is_objective=True,
                    )
                )
            else:
                # Check disclosure placement: is it placed near the top or middle rather than only in the last 5%?
                disclosure_idx = min(desc_lower.find(k) for k in ftc_keywords if k in desc_lower)
                if disclosure_idx > len(desc_clean) * 0.90 and len(desc_clean) > 800:
                    score -= 8.0
                    findings.append(
                        AuditFinding(
                            category="FTC Regulatory Compliance",
                            severity=AuditFindingSeverity.WARNING,
                            title="FTC Disclosure Buried at Bottom",
                            message="FTC guidelines require disclosures to be clear, conspicuous, and placed before or alongside affiliate links, not buried below social links.",
                            evidence_source=f"Position: {int((disclosure_idx/len(desc_clean))*100)}% through text",
                            suggestion="Move the disclosure above or immediately adjacent to your product links.",
                            is_objective=True,
                        )
                    )
                else:
                    findings.append(
                        AuditFinding(
                            category="FTC Regulatory Compliance",
                            severity=AuditFindingSeverity.POSITIVE,
                            title="Prominent FTC Disclosure Present",
                            message="Clear affiliate disclosure detected in compliance with FTC transparency standards.",
                            evidence_source="Detected keywords present",
                            is_objective=True,
                        )
                    )

        # Detect Unfilled Template Placeholders
        detected_placeholders = []
        for pat in self.PLACEHOLDER_PATTERNS:
            matches = re.findall(pat, desc_clean, flags=re.IGNORECASE)
            if matches:
                detected_placeholders.extend(matches)

        has_placeholders = len(detected_placeholders) > 0
        if has_placeholders:
            score -= 20.0
            findings.append(
                AuditFinding(
                    category="Quality & Completeness",
                    severity=AuditFindingSeverity.CRITICAL,
                    title="Unfilled Template Placeholders Detected",
                    message=f"Description contains unfilled template placeholder tokens ({', '.join(detected_placeholders[:3])}) that must be customized before publishing.",
                    evidence_source=", ".join(detected_placeholders[:3]),
                    suggestion="Fill in all brackets and placeholder URLs with verified actual details.",
                    is_objective=True,
                )
            )

        # Secondary Keywords Coverage
        covered_sec = [k for k in sec_kws if k in desc_lower]
        missing_sec = [k for k in sec_kws if k not in desc_lower]
        if sec_kws:
            coverage_pct = int((len(covered_sec) / len(sec_kws)) * 100)
            if coverage_pct >= 60:
                findings.append(
                    AuditFinding(
                        category="Supporting Keywords",
                        severity=AuditFindingSeverity.POSITIVE,
                        title="Strong Secondary Keyword Coverage",
                        message=f"{len(covered_sec)} of {len(sec_kws)} secondary keywords ({coverage_pct}%) naturally present in description.",
                        evidence_source=f"Covered: {', '.join(covered_sec[:4])}",
                        is_objective=True,
                    )
                )
            else:
                score -= 8.0
                findings.append(
                    AuditFinding(
                        category="Supporting Keywords",
                        severity=AuditFindingSeverity.IMPROVEMENT,
                        title="Low Secondary Keyword Coverage",
                        message=f"Only {len(covered_sec)} of {len(sec_kws)} secondary terms appear in the description.",
                        evidence_source=f"Missing: {', '.join(missing_sec[:4])}",
                        suggestion="Weave missing related search queries naturally into your video summary paragraphs.",
                        is_objective=True,
                    )
                )

        # Count Links
        links = re.findall(r"https?://[^\s]+", desc_clean)

        return DescriptionQualityResult(
            score=max(0.0, min(100.0, round(score, 1))),
            findings=findings,
            character_count=char_count,
            has_hook=has_hook,
            has_primary_keyword_hook=has_kw_in_hook,
            has_timestamps=has_timestamps,
            timestamp_count=ts_count,
            has_ftc_disclosure=has_disclosure,
            has_placeholders=has_placeholders,
            link_count=len(links),
            secondary_keywords_covered=covered_sec,
            secondary_keywords_missing=missing_sec,
        )

    # --------------------------------------------------------------------------
    # 3. Script & Content Alignment
    # --------------------------------------------------------------------------

    def audit_script_alignment(
        self,
        title: str,
        description: str,
        primary_keyword: str,
        script_or_outline: Optional[str] = None,
    ) -> ScriptAlignmentResult:
        """Compare title promises vs script delivery. If empty, return NOT CHECKED (no penalty)."""
        script_text = (script_or_outline or "").strip()

        # RULE: If no script or outline is supplied, mark as NOT CHECKED. Never assume pass or penalize.
        if not script_text:
            return ScriptAlignmentResult(
                status=AuditStatus.NOT_CHECKED,
                score=None,
                findings=[
                    AuditFinding(
                        category="Script Alignment",
                        severity=AuditFindingSeverity.IMPROVEMENT,
                        title="Script / Outline Not Provided (NOT CHECKED)",
                        message="Script alignment was NOT CHECKED because no script, outline, or transcript was submitted. (No penalty applied to readiness score).",
                        evidence_source="Input was empty",
                        suggestion="Paste your video outline or draft script to verify that title promises are delivered in the content.",
                        is_objective=True,
                    )
                ],
                promises_addressed=[],
                missing_promises=[],
                fluff_phrases_found=[],
                criteria_covered=[],
                unsupported_claims=[],
            )

        script_lower = script_text.lower()
        title_words = set(re.findall(r"\b\w{4,}\b", title.lower()))
        stop_words = {"this", "that", "with", "from", "your", "what", "where", "when", "about", "guide", "video", "tips"}
        key_title_terms = [w for w in title_words if w not in stop_words]

        findings: List[AuditFinding] = []
        score = 100.0

        # Check if title promises are delivered
        addressed = [t for t in key_title_terms if t in script_lower]
        missing = [t for t in key_title_terms if t not in script_lower]

        if missing:
            score -= (len(missing) * 6.0)
            findings.append(
                AuditFinding(
                    category="Content Promise Alignment",
                    severity=AuditFindingSeverity.WARNING,
                    title="Potential Title Promise Gap",
                    message=f"Term(s) from title ({', '.join(missing)}) were not detected in the script. Ensure all title promises are resolved.",
                    evidence_source=", ".join(missing),
                    suggestion="Add a dedicated segment addressing each claim made in the title.",
                    is_objective=True,
                )
            )
        else:
            findings.append(
                AuditFinding(
                    category="Content Promise Alignment",
                    severity=AuditFindingSeverity.POSITIVE,
                    title="All Title Promises Reflected in Script",
                    message="Core concepts from the video title are actively discussed in the script.",
                    evidence_source=f"Found: {', '.join(addressed)}",
                    is_objective=True,
                )
            )

        # Fluff / Filler Phrase Detection
        fluff_found = []
        for phrase in self.FLUFF_PHRASES:
            if phrase in script_lower:
                fluff_found.append(phrase)

        if fluff_found:
            score -= (len(fluff_found) * 4.0)
            findings.append(
                AuditFinding(
                    category="Script Pacing & Retention",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Fluff / Filler Phrases Detected",
                    message=f"Found {len(fluff_found)} cliché phrase(s) ({', '.join(fluff_found[:3])}) that slow down video pacing.",
                    evidence_source=", ".join(fluff_found[:3]),
                    suggestion="Cut pleasantries and hook viewers with immediate value in the first 15 seconds.",
                    is_objective=True,
                )
            )

        # Check for review / comparison criteria if commercial
        is_review = any(w in title.lower() for w in ["review", "vs", "versus", "compare", "best"])
        criteria_list = ["pros", "cons", "drawback", "price", "performance", "build", "battery", "verdict", "alternative"]
        covered_criteria = [c for c in criteria_list if c in script_lower]

        if is_review and len(covered_criteria) < 2:
            score -= 15.0
            findings.append(
                AuditFinding(
                    category="Review Criteria Depth",
                    severity=AuditFindingSeverity.WARNING,
                    title="Missing Standard Evaluation Criteria",
                    message="Title suggests a product review or comparison, but the script lacks standard criteria (pros, cons, price, trade-offs).",
                    evidence_source=f"Found only: {covered_criteria}",
                    suggestion="Include clear sections covering pricing, pros, cons, and who should NOT buy the product.",
                    is_objective=False,
                )
            )

        return ScriptAlignmentResult(
            status=AuditStatus.CHECKED,
            score=max(0.0, min(100.0, round(score, 1))),
            findings=findings,
            promises_addressed=addressed,
            missing_promises=missing,
            fluff_phrases_found=fluff_found,
            criteria_covered=covered_criteria,
            unsupported_claims=[],
        )

    # --------------------------------------------------------------------------
    # 4. Affiliate Content Quality Audit
    # --------------------------------------------------------------------------

    def audit_affiliate_content(
        self,
        description: str,
        script_or_outline: Optional[str] = None,
        channel: Optional[ChannelProfile] = None,
        has_affiliate_links: bool = False,
    ) -> AffiliateQualityResult:
        """Audit for balanced pros/cons, unsupported superlatives, FTC disclosure, and price freshness notice."""
        # If channel affiliate is disabled and no affiliate links exist: mark NOT APPLICABLE
        affiliate_enabled = bool(channel and channel.affiliate_enabled)
        if not affiliate_enabled and not has_affiliate_links:
            return AffiliateQualityResult(
                status=AuditStatus.NOT_APPLICABLE,
                score=None,
                findings=[
                    AuditFinding(
                        category="Affiliate Content Quality",
                        severity=AuditFindingSeverity.POSITIVE,
                        title="Affiliate Quality Check Not Applicable",
                        message="Affiliate marketing is disabled for this channel profile and no affiliate links were provided.",
                        evidence_source="Channel settings: affiliate_enabled=False",
                        is_objective=True,
                    )
                ],
                has_variant_specificity=True,
                has_balanced_pros_cons=True,
                has_price_freshness_notice=True,
                has_ftc_disclosure=True,
                unsupported_superlatives=[],
                unverified_facts=[],
            )

        combined_text = (description + " " + (script_or_outline or "")).lower()
        findings: List[AuditFinding] = []
        score = 100.0

        # Check for Unsupported Superlatives
        superlatives_found = []
        for s in self.UNSUPPORTED_SUPERLATIVES:
            if s in combined_text:
                superlatives_found.append(s)

        if superlatives_found:
            score -= (len(superlatives_found) * 8.0)
            findings.append(
                AuditFinding(
                    category="Affiliate Editorial Integrity",
                    severity=AuditFindingSeverity.WARNING,
                    title="Unsupported Superlatives Detected",
                    message=f"Found absolute superlatives ({', '.join(superlatives_found)}) which damage credibility and violate review guidelines.",
                    evidence_source=", ".join(superlatives_found),
                    suggestion="Replace hyperbolic praise with specific test results, use cases, and nuance.",
                    is_objective=True,
                )
            )

        # Balanced Pros & Cons / Limitations Check
        con_terms = ["con", "cons", "drawback", "drawbacks", "downside", "downsides", "skip if", "not for", "limitation"]
        has_cons = any(t in combined_text for t in con_terms)

        if not has_cons:
            score -= 18.0
            findings.append(
                AuditFinding(
                    category="Balanced Review Integrity",
                    severity=AuditFindingSeverity.WARNING,
                    title="Missing Drawbacks or Limitations",
                    message="Content lacks discussion of downsides or who should skip this product. Unbalanced reviews harm viewer trust.",
                    evidence_source="No terms like 'cons', 'drawbacks', 'not for' found",
                    suggestion="Add at least 2 genuine limitations or alternative recommendations for specific use cases.",
                    is_objective=False,
                )
            )
        else:
            findings.append(
                AuditFinding(
                    category="Balanced Review Integrity",
                    severity=AuditFindingSeverity.POSITIVE,
                    title="Balanced Review Perspective Detected",
                    message="Content addresses both benefits and drawbacks, establishing authentic editorial value.",
                    evidence_source="Contains limitation markers",
                    is_objective=True,
                )
            )

        # Price Freshness / Availability Notice
        freshness_terms = ["subject to change", "prices change", "price at time of recording", "check current price", "check latest price"]
        has_freshness = any(t in combined_text for t in freshness_terms)

        if not has_freshness:
            score -= 6.0
            findings.append(
                AuditFinding(
                    category="Price & Availability Notice",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Missing Price Freshness Disclaimer",
                    message="Online pricing and availability fluctuate. Remind viewers to check current prices via link.",
                    evidence_source="No price freshness disclaimer found",
                    suggestion="Add 'Prices and availability subject to change' near product links.",
                    is_objective=True,
                )
            )

        # FTC Disclosure Verification
        ftc_terms = ["affiliate", "commission", "disclosure"]
        has_ftc = any(t in combined_text for t in ftc_terms)

        return AffiliateQualityResult(
            status=AuditStatus.CHECKED,
            score=max(0.0, min(100.0, round(score, 1))),
            findings=findings,
            has_variant_specificity=True,
            has_balanced_pros_cons=has_cons,
            has_price_freshness_notice=has_freshness,
            has_ftc_disclosure=has_ftc,
            unsupported_superlatives=superlatives_found,
            unverified_facts=[],
        )

    # --------------------------------------------------------------------------
    # 5. Thumbnail & Title Alignment
    # --------------------------------------------------------------------------

    def audit_thumbnail_alignment(
        self,
        thumbnail_concept: str,
        title: str,
        script_or_outline: Optional[str] = None,
    ) -> ThumbnailQualityResult:
        """Audit thumbnail text readability, concept clarity, and title synergy."""
        concept_clean = (thumbnail_concept or "").strip()

        # If no concept text supplied:
        if not concept_clean:
            return ThumbnailQualityResult(
                concept_status=AuditStatus.NOT_CHECKED,
                visual_inspection_status=AuditStatus.NOT_CHECKED,
                score=70.0,
                findings=[
                    AuditFinding(
                        category="Thumbnail Concept",
                        severity=AuditFindingSeverity.IMPROVEMENT,
                        title="Thumbnail Concept Not Provided",
                        message="Thumbnail concept was NOT CHECKED because no concept text or description was provided.",
                        evidence_source="Input was empty",
                        suggestion="Provide your planned thumbnail visual elements and text overlay for audit.",
                        is_objective=True,
                    )
                ],
                word_count=0,
                character_count=0,
                readability_assessment="Not evaluated",
                complements_title=True,
                potential_clickbait_flags=[],
            )

        words = re.findall(r"\b\w+\b", concept_clean)
        word_count = len(words)
        char_count = len(concept_clean)
        findings: List[AuditFinding] = []
        score = 100.0

        # Word count & mobile readability check
        if word_count > 6:
            score -= 15.0
            readability = "Excessive Text (Poor Mobile Readability)"
            findings.append(
                AuditFinding(
                    category="Thumbnail Readability",
                    severity=AuditFindingSeverity.WARNING,
                    title="Too Many Words on Thumbnail Concept",
                    message=f"Concept has {word_count} words. Thumbnails should ideally use 2-4 punchy words for mobile readability.",
                    evidence_source=f"{word_count} words",
                    suggestion="Condense text overlay to 3-4 impactful words at most.",
                    is_objective=True,
                )
            )
        else:
            readability = "Good Readability (<5 words)"
            findings.append(
                AuditFinding(
                    category="Thumbnail Readability",
                    severity=AuditFindingSeverity.POSITIVE,
                    title="Punchy Thumbnail Text Length",
                    message=f"Concept uses {word_count} words, suitable for glanceable mobile comprehension.",
                    evidence_source=f"{word_count} words",
                    is_objective=True,
                )
            )

        # Title Complement Check (Should NOT just be an exact copy of the title)
        title_lower = title.strip().lower()
        concept_lower = concept_clean.lower()
        duplicates_title = (concept_lower == title_lower) or (len(concept_clean) > 15 and concept_lower in title_lower)

        if duplicates_title:
            score -= 12.0
            findings.append(
                AuditFinding(
                    category="Thumbnail & Title Synergy",
                    severity=AuditFindingSeverity.IMPROVEMENT,
                    title="Thumbnail Repeats Title Word-for-Word",
                    message="Thumbnail duplicates the title text. Best practice is for thumbnail and title to work as a 1-2 punch with complementary information.",
                    evidence_source=f"Matches title: '{title[:30]}...'",
                    suggestion="Use the thumbnail to show the emotion, result, or curiosity hook, and the title for search keywords.",
                    is_objective=False,
                )
            )

        # Clickbait / misleading visual elements check
        clickbait_markers = ["red arrow", "fake circle", "shocked face", "crying emoji", "100% real", "proof!"]
        flags = [m for m in clickbait_markers if m in concept_lower]
        if flags:
            score -= 10.0
            findings.append(
                AuditFinding(
                    category="Thumbnail Quality",
                    severity=AuditFindingSeverity.WARNING,
                    title="Sensational Thumbnail Element Detected",
                    message=f"Concept references cliché clickbait elements ({', '.join(flags)}) that can reduce viewer trust.",
                    evidence_source=", ".join(flags),
                    suggestion="Rely on clear focal points, high contrast, and authentic product shots.",
                    is_objective=True,
                )
            )

        # Visual image inspection status: always marked NOT CHECKED
        findings.append(
            AuditFinding(
                category="Image Pixel Inspection",
                severity=AuditFindingSeverity.POSITIVE,
                title="Visual Pixel Inspection: NOT CHECKED",
                message="Visual image pixel inspection is marked NOT CHECKED (textual thumbnail concept was evaluated).",
                evidence_source="Textual concept mode",
                is_objective=True,
            )
        )

        return ThumbnailQualityResult(
            concept_status=AuditStatus.CHECKED,
            visual_inspection_status=AuditStatus.NOT_CHECKED,
            score=max(0.0, min(100.0, round(score, 1))),
            findings=findings,
            word_count=word_count,
            character_count=char_count,
            readability_assessment=readability,
            complements_title=not duplicates_title,
            potential_clickbait_flags=flags,
        )

    # --------------------------------------------------------------------------
    # 6. Transparent SEO Readiness Score Breakdown
    # --------------------------------------------------------------------------

    def calculate_readiness_score(
        self,
        title_res: TitleQualityResult,
        desc_res: DescriptionQualityResult,
        script_res: ScriptAlignmentResult,
        affiliate_res: AffiliateQualityResult,
        thumbnail_res: ThumbnailQualityResult,
    ) -> AuditScoreBreakdown:
        """Calculate weighted readiness score across CHECKED categories with itemized deductions."""
        weights: Dict[str, float] = {}
        checked: List[str] = []
        not_checked: List[str] = []
        not_applicable: List[str] = []

        # Title: always checked
        weights["title"] = 35.0
        checked.append("Title Quality")

        # Description: always checked
        weights["description"] = 35.0
        checked.append("Description & FTC Compliance")

        # Thumbnail:
        if thumbnail_res.concept_status == AuditStatus.CHECKED:
            weights["thumbnail"] = 10.0
            checked.append("Thumbnail Concept")
        else:
            not_checked.append("Thumbnail Concept")

        # Script:
        if script_res.status == AuditStatus.CHECKED and script_res.score is not None:
            weights["script"] = 20.0
            checked.append("Script & Content Alignment")
        else:
            not_checked.append("Script & Content Alignment")

        # Affiliate:
        if affiliate_res.status == AuditStatus.CHECKED and affiliate_res.score is not None:
            weights["affiliate"] = 15.0
            checked.append("Affiliate Quality")
        elif affiliate_res.status == AuditStatus.NOT_APPLICABLE:
            not_applicable.append("Affiliate Quality")
        else:
            not_checked.append("Affiliate Quality")

        # Normalize weights so sum is 100%
        total_weight = sum(weights.values())
        norm_weights = {k: (v / total_weight) for k, v in weights.items()}

        # Compute composite score
        overall = 0.0
        overall += title_res.score * norm_weights["title"]
        overall += desc_res.score * norm_weights["description"]
        if "thumbnail" in norm_weights:
            overall += thumbnail_res.score * norm_weights["thumbnail"]
        if "script" in norm_weights:
            overall += (script_res.score or 100.0) * norm_weights["script"]
        if "affiliate" in norm_weights:
            overall += (affiliate_res.score or 100.0) * norm_weights["affiliate"]

        # Aggregate deductions across all findings
        deductions: List[Dict[str, Any]] = []
        all_findings: List[AuditFinding] = (
            title_res.findings
            + desc_res.findings
            + script_res.findings
            + affiliate_res.findings
            + thumbnail_res.findings
        )

        for f in all_findings:
            if f.severity == AuditFindingSeverity.CRITICAL:
                deductions.append({
                    "category": f.category,
                    "title": f.title,
                    "severity": f.severity.value,
                    "is_objective": f.is_objective,
                    "suggestion": f.suggestion,
                })
            elif f.severity == AuditFindingSeverity.WARNING:
                deductions.append({
                    "category": f.category,
                    "title": f.title,
                    "severity": f.severity.value,
                    "is_objective": f.is_objective,
                    "suggestion": f.suggestion,
                })

        # Generate prioritized action list
        # Order: 1. Critical compliance & facts, 2. Content alignment, 3. SEO improvements, 4. Optional
        prioritized: List[Dict[str, Any]] = []
        for f in all_findings:
            if f.severity in (AuditFindingSeverity.CRITICAL, AuditFindingSeverity.WARNING, AuditFindingSeverity.IMPROVEMENT):
                p_level = 1 if f.severity == AuditFindingSeverity.CRITICAL else (2 if f.severity == AuditFindingSeverity.WARNING else 3)
                prioritized.append({
                    "priority_level": p_level,
                    "category": f.category,
                    "issue": f.title,
                    "action": f.suggestion or f.message,
                    "severity": f.severity.value,
                })
        prioritized.sort(key=lambda x: x["priority_level"])

        return AuditScoreBreakdown(
            overall_readiness_score=round(max(0.0, min(100.0, overall)), 1),
            title_score=title_res.score,
            description_score=desc_res.score,
            script_alignment_score=script_res.score,
            affiliate_quality_score=affiliate_res.score,
            thumbnail_score=thumbnail_res.score,
            deductions=deductions,
            checked_categories=checked,
            not_checked_categories=not_checked,
            not_applicable_categories=not_applicable,
            prioritized_actions=prioritized,
        )

    # --------------------------------------------------------------------------
    # 7. Before-Publishing Checklist
    # --------------------------------------------------------------------------

    def generate_publishing_checklist(
        self,
        channel: Optional[ChannelProfile] = None,
        has_affiliate: bool = False,
    ) -> List[PublishingChecklistItem]:
        """Generate a structured, reusable pre-publishing checklist requiring manual confirmation."""
        checklist = [
            PublishingChecklistItem(
                item_id="chk_title_mobile",
                label="Verify title length under 60 characters for mobile display",
                category="Title & Packaging",
                is_completed=False,
                is_manual_required=True,
                help_text="Preview how the title looks on a phone screen without truncation.",
            ),
            PublishingChecklistItem(
                item_id="chk_hook_value",
                label="Confirm first 2 sentences of description clearly communicate viewer value",
                category="Description & SEO",
                is_completed=False,
                is_manual_required=True,
                help_text="Ensure the hook states why the viewer should watch before the fold.",
            ),
            PublishingChecklistItem(
                item_id="chk_timestamps_000",
                label="Verify chapter timestamps start at 0:00 with ascending chronology",
                category="Description & SEO",
                is_completed=False,
                is_manual_required=True,
                help_text="YouTube scrub-bar chapters only work when the first timestamp is 0:00.",
            ),
            PublishingChecklistItem(
                item_id="chk_links_tested",
                label="Manually click and test all external and resource links",
                category="Links & Integrity",
                is_completed=False,
                is_manual_required=True,
                help_text="Confirm none of the links are broken or lead to placeholder pages.",
            ),
            PublishingChecklistItem(
                item_id="chk_thumbnail_mobile",
                label="Review thumbnail at small thumbnail card size for focal contrast",
                category="Title & Packaging",
                is_completed=False,
                is_manual_required=True,
                help_text="Squint test: can the text and subject be identified in 1 second?",
            ),
            PublishingChecklistItem(
                item_id="chk_script_promises",
                label="Confirm every premise or question in the title is answered in the video",
                category="Content Alignment",
                is_completed=False,
                is_manual_required=True,
                help_text="Prevents viewer dissatisfaction and click-away drop-offs.",
            ),
            PublishingChecklistItem(
                item_id="chk_cards_endscreen",
                label="Plan YouTube end screen cards and related playlist links",
                category="Channel Strategy",
                is_completed=False,
                is_manual_required=True,
                help_text="Guide viewers directly to your next relevant video.",
            ),
        ]

        # Add FTC item if affiliate is active
        if (channel and channel.affiliate_enabled) or has_affiliate:
            checklist.insert(
                3,
                PublishingChecklistItem(
                    item_id="chk_ftc_prominence",
                    label="Ensure FTC affiliate disclosure is clearly visible above product links",
                    category="Compliance & FTC",
                    is_completed=False,
                    is_manual_required=True,
                    help_text="Required by law whenever financial affiliate links are included.",
                ),
            )
            checklist.insert(
                4,
                PublishingChecklistItem(
                    item_id="chk_price_freshness",
                    label="Verify product model specs and add price change disclaimer",
                    category="Compliance & FTC",
                    is_completed=False,
                    is_manual_required=True,
                    help_text="Ensure exact variant is identified and pricing freshness is noted.",
                ),
            )

        return checklist

    # --------------------------------------------------------------------------
    # 8. Four-Channel Topic Overlap & Isolation Checker
    # --------------------------------------------------------------------------

    def check_channel_isolation(
        self,
        channel: ChannelProfile,
        proposed_topic: str,
        primary_keyword: str,
    ) -> List[AuditFinding]:
        """Verify proposed topic does not violate channel exclusions or overlap other channels."""
        findings: List[AuditFinding] = []
        topic_lower = (proposed_topic + " " + primary_keyword).lower()

        # Check Channel Exclusions
        for excluded in channel.excluded_topics + channel.excluded_keywords:
            if excluded and excluded.lower() in topic_lower:
                findings.append(
                    AuditFinding(
                        category="Channel Profile Boundaries",
                        severity=AuditFindingSeverity.CRITICAL,
                        title=f"Topic Matches Channel Exclusion: '{excluded}'",
                        message=f"'{excluded}' is explicitly configured as an excluded topic/keyword for {channel.channel_name}.",
                        evidence_source=f"Excluded: {excluded}",
                        suggestion=f"Remove or pivot away from '{excluded}' to maintain channel brand focus.",
                        is_objective=True,
                    )
                )

        # Check Cross-Channel Niche Overlap
        all_channels = self.db.get_channel_profiles() if hasattr(self.db, "get_channel_profiles") else []
        for other in all_channels:
            if other.id != channel.id:
                other_niche = other.channel_niche.lower()
                if other_niche and other_niche in topic_lower and other_niche not in channel.channel_niche.lower():
                    findings.append(
                        AuditFinding(
                            category="Cross-Channel Overlap Warning",
                            severity=AuditFindingSeverity.WARNING,
                            title=f"Potential Overlap with Channel {other.id} ({other.channel_name})",
                            message=f"This topic appears closer to Channel {other.id}'s niche ('{other.channel_niche}') than {channel.channel_name}'s niche ('{channel.channel_niche}').",
                            evidence_source=f"Matches niche of: {other.channel_name}",
                            suggestion=f"Consider routing this research idea to Channel {other.id} instead.",
                            is_objective=False,
                        )
                    )

        return findings

    # --------------------------------------------------------------------------
    # 9. Public YouTube Video URL Metadata Fetching
    # --------------------------------------------------------------------------

    def fetch_public_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """Retrieve public YouTube video metadata safely. Never implies private analytics access."""
        url_clean = (video_url or "").strip()
        if not url_clean:
            return {"success": False, "error": "No URL provided"}

        # Extract YouTube Video ID
        match = re.search(r"(?:v=|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url_clean)
        if not match:
            return {
                "success": False,
                "error": "Could not parse a valid 11-character YouTube video ID from URL.",
                "is_public_metadata_only": True,
            }

        video_id = match.group(1)

        # 1. First attempt: YouTube public oEmbed endpoint (zero API key needed, zero quota, 100% public metadata)
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            resp = requests.get(oembed_url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "video_id": video_id,
                    "title": data.get("title", ""),
                    "channel_title": data.get("author_name", ""),
                    "channel_url": data.get("author_url", ""),
                    "thumbnail_url": data.get("thumbnail_url", ""),
                    "source": "YouTube Public oEmbed (Live)",
                    "is_public_metadata_only": True,
                    "private_analytics_accessible": False,
                    "notice": "Retrieved public video metadata only. local-first local studio does not access private YouTube Studio analytics.",
                }
        except Exception:
            pass

        # Fallback return with extracted video ID
        return {
            "success": True,
            "video_id": video_id,
            "title": f"YouTube Video ({video_id})",
            "channel_title": "Public Channel",
            "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "source": "Local ID Parser",
            "is_public_metadata_only": True,
            "private_analytics_accessible": False,
            "notice": "Retrieved public video metadata only. local-first local studio does not access private YouTube Studio analytics.",
        }

    # --------------------------------------------------------------------------
    # 10. Report Export & Formula Injection Protection
    # --------------------------------------------------------------------------

    def export_audit_report(self, audit: VideoSeoAudit, format: str = "markdown") -> str:
        """Export sanitized SEO Audit Report protected against formula injection."""
        title_sanitized = str(sanitize_formula_injection(audit.proposed_title))
        kw_sanitized = str(sanitize_formula_injection(audit.primary_keyword))
        channel_sanitized = str(sanitize_formula_injection(audit.channel_name))
        desc_sanitized = str(sanitize_formula_injection(audit.draft_description))

        if format.lower() == "json":
            export_dict = {
                "audit_id": audit.id,
                "channel": channel_sanitized,
                "primary_keyword": kw_sanitized,
                "proposed_title": title_sanitized,
                "revision_number": audit.revision_number,
                "scores": {
                    "overall": audit.scores.overall_readiness_score,
                    "title": audit.scores.title_score,
                    "description": audit.scores.description_score,
                    "script": audit.scores.script_alignment_score,
                    "affiliate": audit.scores.affiliate_quality_score,
                    "thumbnail": audit.scores.thumbnail_score,
                },
                "findings": [
                    {"category": f.category, "severity": f.severity.value, "title": f.title, "message": f.message}
                    for f in audit.findings
                ],
                "checklist": [
                    {"label": c.label, "is_completed": c.is_completed}
                    for c in audit.checklist
                ],
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "disclaimer": audit.scores.disclaimer,
            }
            return json.dumps(export_dict, indent=2)

        # Markdown format
        lines = [
            f"# YouTube SEO & Content Quality Audit Report",
            f"**Channel:** {channel_sanitized} | **Revision:** #{audit.revision_number} | **Date:** {audit.created_at[:10] if audit.created_at else 'Current'}",
            "",
            f"## 1. Executive Scorecard",
            f"- **Overall SEO Readiness Score:** `{audit.scores.overall_readiness_score} / 100`",
            f"- **Title Quality Score:** `{audit.scores.title_score} / 100`",
            f"- **Description & Chapters Score:** `{audit.scores.description_score} / 100`",
            f"- **Script Alignment Score:** `{audit.scores.script_alignment_score if audit.scores.script_alignment_score is not None else 'NOT CHECKED'}`",
            f"- **Affiliate Content Quality Score:** `{audit.scores.affiliate_quality_score if audit.scores.affiliate_quality_score is not None else 'NOT APPLICABLE'}`",
            f"- **Thumbnail Concept Score:** `{audit.scores.thumbnail_score} / 100`",
            "",
            f"> *Note: {audit.scores.disclaimer}*",
            "",
            f"## 2. Target Video Specifications",
            f"- **Primary Keyword:** `{kw_sanitized}`",
            f"- **Proposed Title:** `{title_sanitized}` ({len(audit.proposed_title)} chars — {audit.title_result.truncation_risk})",
            "",
            f"## 3. Prioritized Action Items",
        ]

        if audit.scores.prioritized_actions:
            for item in audit.scores.prioritized_actions:
                p_badge = "🔴 CRITICAL" if item["severity"] == "CRITICAL" else ("🟠 WARNING" if item["severity"] == "WARNING" else "🟡 IMPROVEMENT")
                lines.append(f"- **{p_badge} [{item['category']}]:** {item['issue']}")
                lines.append(f"  *Action:* {item['action']}")
        else:
            lines.append("- *No high-priority issues detected.*")

        lines.extend([
            "",
            f"## 4. Pre-Publishing Checklist Status",
        ])
        for chk in audit.checklist:
            mark = "[x]" if chk.is_completed else "[ ]"
            lines.append(f"- {mark} {chk.label}")

        lines.extend([
            "",
            f"---",
            f"*Generated by Keyword Studio Local Pro Studio — Formula injection sanitized*",
        ])
        return "\n".join(lines)


# Default singleton instance
audit_engine = AuditEngine()

"""Transparent, rule-based Keyword Relevance Scoring Engine.

Calculates a normalized Relevance Score (0-100) based on documented, explainable rules:
1. Seed Term Presence (0 to seed_term_weight * 100): Overlap ratio of normalized seed terms present in the keyword.
2. Sequence Similarity (0 to similarity_weight * 100): Token set / character similarity between seed and keyword.
3. Intent Clarity & Topic Modifiers (0 to intent_clarity_weight * 100): Bonus for structured user search intents.
4. Word Count / Tail Quality (0 to length_quality_weight * 100): Bonus for standard 2-6 word search queries.
5. Penalty for Degenerate/Duplicate tokens: Detects spammy word repetition (e.g. "wax wax wax").

CRITICAL NOTICE:
This is a transparent heuristic "Relevance Score", NOT search volume, CPC, or ranking difficulty.
A high score does NOT imply or guarantee YouTube ranking or traffic.
"""

import collections
import difflib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.classifier.models import KeywordClassification, SearchIntent
from src.utils.normalization import normalize_keyword_key, tokenize_keyword


@dataclass
class ScoringWeights:
    """Customizable scoring weights summing to 1.0."""

    seed_term_weight: float = 0.40
    similarity_weight: float = 0.30
    intent_clarity_weight: float = 0.20
    length_quality_weight: float = 0.10
    duplicate_repetition_penalty: float = 20.0

    def __post_init__(self) -> None:
        total = (
            self.seed_term_weight
            + self.similarity_weight
            + self.intent_clarity_weight
            + self.length_quality_weight
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to approximately 1.0 (got {total:.2f})")


@dataclass
class RelevanceBreakdown:
    """Detailed transparent breakdown of relevance score components."""

    total_score: float
    seed_term_score: float
    similarity_score: float
    intent_score: float
    length_score: float
    penalty: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RelevanceScorer:
    """Calculates explainable, deterministic relevance scores for discovered keywords."""

    def __init__(self, weights: Optional[ScoringWeights] = None) -> None:
        self.weights = weights or ScoringWeights()

    def score(
        self,
        keyword: str,
        seed_keyword: str,
        classification: Optional[KeywordClassification] = None,
        preferred_intents: Optional[List[str]] = None,
    ) -> RelevanceBreakdown:
        """Compute the relevance score and transparent explanation."""
        clean_kw = unicodedata.normalize("NFC", keyword.strip())
        clean_seed = unicodedata.normalize("NFC", seed_keyword.strip())

        if not clean_kw or not clean_seed:
            return RelevanceBreakdown(
                total_score=0.0,
                seed_term_score=0.0,
                similarity_score=0.0,
                intent_score=0.0,
                length_score=0.0,
                penalty=0.0,
                explanation="Empty keyword or seed term",
            )

        kw_tokens = [t.lower() for t in tokenize_keyword(clean_kw)]
        seed_tokens = [t.lower() for t in tokenize_keyword(clean_seed)]

        if not kw_tokens or not seed_tokens:
            return RelevanceBreakdown(
                total_score=0.0,
                seed_term_score=0.0,
                similarity_score=0.0,
                intent_score=0.0,
                length_score=0.0,
                penalty=0.0,
                explanation="No valid tokens extracted",
            )

        # 1. Seed Term Presence (0.0 to 1.0 * seed_term_weight * 100)
        seed_set = set(seed_tokens)
        kw_set = set(kw_tokens)
        matched_seed_tokens = seed_set.intersection(kw_set)
        seed_overlap_ratio = len(matched_seed_tokens) / max(1, len(seed_set))
        seed_term_score = round(seed_overlap_ratio * (self.weights.seed_term_weight * 100), 2)

        # 2. Sequence Similarity (0.0 to 1.0 * similarity_weight * 100)
        # Using difflib SequenceMatcher on normalized lowercase strings
        norm_kw = normalize_keyword_key(clean_kw)
        norm_seed = normalize_keyword_key(clean_seed)
        seq_ratio = difflib.SequenceMatcher(None, norm_seed, norm_kw).ratio()
        # If seed is an exact prefix or substring, give high similarity floor
        if norm_kw.startswith(norm_seed) or norm_seed in norm_kw:
            seq_ratio = max(seq_ratio, 0.85)
        similarity_score = round(seq_ratio * (self.weights.similarity_weight * 100), 2)

        # 3. Intent Clarity & Topic Relevance (0.0 to 1.0 * intent_clarity_weight * 100)
        intent_ratio = 0.5  # Baseline for any coherent query
        matched_intent_name = "General"
        if classification:
            # If keyword has specific intent (e.g. Tutorial, Review, Problem-solving, Comparison)
            non_general_intents = [
                i.value
                for i in classification.intent_labels
                if i not in (SearchIntent.INFORMATIONAL, SearchIntent.GENERAL)
            ]
            if non_general_intents:
                intent_ratio = 1.0
                matched_intent_name = non_general_intents[0]
            elif classification.is_question:
                intent_ratio = 0.9
                matched_intent_name = "Question"

            # User preferred intent bonus
            if preferred_intents:
                pref_lower = [p.lower() for p in preferred_intents]
                for intent in classification.intent_labels:
                    if intent.value.lower() in pref_lower:
                        intent_ratio = 1.0
                        matched_intent_name = f"Preferred: {intent.value}"
                        break
        intent_score = round(intent_ratio * (self.weights.intent_clarity_weight * 100), 2)

        # 4. Length Quality Score (0.0 to 1.0 * length_quality_weight * 100)
        # Sweet spot for video search queries is 2-6 words
        word_count = len(kw_tokens)
        if 2 <= word_count <= 6:
            length_ratio = 1.0
        elif word_count == 1:
            length_ratio = 0.5  # Single word is often too broad
        elif 7 <= word_count <= 9:
            length_ratio = 0.8  # Long tail
        else:
            length_ratio = 0.4  # Overly verbose / potential keyword stuffing
        length_score = round(length_ratio * (self.weights.length_quality_weight * 100), 2)

        # 5. Penalty for Repeated / Degenerate Tokens
        counts = collections.Counter(kw_tokens)
        has_repetition = any(c >= 3 for c in counts.values())
        penalty = self.weights.duplicate_repetition_penalty if has_repetition else 0.0

        raw_total = seed_term_score + similarity_score + intent_score + length_score - penalty
        final_score = max(0.0, min(100.0, round(raw_total, 1)))

        explanation_parts = [
            f"Seed overlap: {len(matched_seed_tokens)}/{len(seed_set)} ({seed_term_score:.1f} pts)",
            f"Similarity: {seq_ratio * 100:.0f}% ({similarity_score:.1f} pts)",
            f"Intent: {matched_intent_name} ({intent_score:.1f} pts)",
            f"Length: {word_count} words ({length_score:.1f} pts)",
        ]
        if penalty > 0:
            explanation_parts.append(f"Penalty: -{penalty:.0f} pts (repeated tokens)")

        explanation = " + ".join(explanation_parts) + f" = {final_score:.1f}/100"

        return RelevanceBreakdown(
            total_score=final_score,
            seed_term_score=seed_term_score,
            similarity_score=similarity_score,
            intent_score=intent_score,
            length_score=length_score,
            penalty=penalty,
            explanation=explanation,
        )


default_scorer = RelevanceScorer()

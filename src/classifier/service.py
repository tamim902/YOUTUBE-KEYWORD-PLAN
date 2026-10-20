"""Deterministic keyword classification service."""

from typing import Dict, List, Optional
from src.classifier.models import (
    KeywordClassification,
    SearchIntent,
    TailLength,
    TailThresholds,
)
from src.classifier.rules import INTENT_RULES
from src.utils.normalization import count_tokens, normalize_keyword_display, normalize_keyword_key


class KeywordClassifier:
    """Classifies search keywords into structural tail lengths and semantic search intents."""

    def __init__(self, thresholds: Optional[TailThresholds] = None) -> None:
        self.thresholds = thresholds or TailThresholds()

    def classify(self, keyword: str) -> KeywordClassification:
        """Classify a single keyword term."""
        display = normalize_keyword_display(keyword)
        key = normalize_keyword_key(display)
        word_count = count_tokens(display)
        tail = self.thresholds.classify(word_count)

        matched_intents: List[SearchIntent] = []
        confidence_scores: Dict[str, float] = {}
        matched_reasons: Dict[str, str] = {}

        # Evaluate rules
        for rule_tuple in INTENT_RULES:
            intent = rule_tuple[0]
            patterns = rule_tuple[1]
            base_score = rule_tuple[2]
            reason = rule_tuple[3] if len(rule_tuple) > 3 else "Matched intent pattern"

            matched = False
            for pattern in patterns:
                m = pattern.search(display) or pattern.search(key)
                if m:
                    matched = True
                    matched_term = m.group(0).strip()
                    specific_reason = f"{reason} (term: '{matched_term}')"
                    break
            if matched:
                if intent not in matched_intents:
                    matched_intents.append(intent)
                    confidence_scores[intent.value] = base_score
                    matched_reasons[intent.value] = specific_reason

                # Add Phase 9 canonical category aliases
                if intent == SearchIntent.TUTORIAL and SearchIntent.HOW_TO_TUTORIAL not in matched_intents:
                    matched_intents.append(SearchIntent.HOW_TO_TUTORIAL)
                    confidence_scores[SearchIntent.HOW_TO_TUTORIAL.value] = base_score
                    matched_reasons[SearchIntent.HOW_TO_TUTORIAL.value] = specific_reason
                elif intent == SearchIntent.COMPARISON and SearchIntent.COMPARISON_VS not in matched_intents:
                    matched_intents.append(SearchIntent.COMPARISON_VS)
                    confidence_scores[SearchIntent.COMPARISON_VS.value] = base_score
                    matched_reasons[SearchIntent.COMPARISON_VS.value] = specific_reason
                elif intent in (SearchIntent.LISTICLE, SearchIntent.COMMERCIAL_INVESTIGATION) and SearchIntent.BEST_TOP_LIST not in matched_intents:
                    matched_intents.append(SearchIntent.BEST_TOP_LIST)
                    confidence_scores[SearchIntent.BEST_TOP_LIST.value] = base_score
                    matched_reasons[SearchIntent.BEST_TOP_LIST.value] = specific_reason
                elif intent == SearchIntent.BUYING_INTENT and SearchIntent.BUYING_COMMERCIAL not in matched_intents:
                    matched_intents.append(SearchIntent.BUYING_COMMERCIAL)
                    confidence_scores[SearchIntent.BUYING_COMMERCIAL.value] = base_score
                    matched_reasons[SearchIntent.BUYING_COMMERCIAL.value] = specific_reason

        # Default fallback to Informational if no specific intent was detected
        if not matched_intents:
            matched_intents.append(SearchIntent.INFORMATIONAL)
            matched_intents.append(SearchIntent.GENERAL)
            confidence_scores[SearchIntent.INFORMATIONAL.value] = 0.60
            confidence_scores[SearchIntent.GENERAL.value] = 0.60
            matched_reasons[SearchIntent.INFORMATIONAL.value] = "General / Unclassified fallback informational intent"
            matched_reasons[SearchIntent.GENERAL.value] = "General / Unclassified search topic without specific modifier"

        # Determine primary intent: highest confidence score, prioritizing specific non-informational intents
        sorted_intents = sorted(
            matched_intents,
            key=lambda x: (
                confidence_scores.get(x.value, 0.0),
                0 if x in (SearchIntent.INFORMATIONAL, SearchIntent.GENERAL) else 1,
            ),
            reverse=True,
        )
        primary_intent = sorted_intents[0]
        primary_explanation = matched_reasons.get(
            primary_intent.value, "Default rule-based intent classification"
        )

        is_question = SearchIntent.QUESTION in matched_intents
        is_listicle = (
            SearchIntent.LISTICLE in matched_intents or SearchIntent.BEST_TOP_LIST in matched_intents
        )
        is_review = SearchIntent.REVIEW in matched_intents
        is_tutorial = (
            SearchIntent.TUTORIAL in matched_intents or SearchIntent.HOW_TO_TUTORIAL in matched_intents
        )
        is_comparison = (
            SearchIntent.COMPARISON in matched_intents or SearchIntent.COMPARISON_VS in matched_intents
        )
        is_buying_intent = (
            SearchIntent.BUYING_INTENT in matched_intents
            or SearchIntent.BUYING_COMMERCIAL in matched_intents
        )
        is_commercial = (
            SearchIntent.COMMERCIAL_INVESTIGATION in matched_intents
            or SearchIntent.BEST_TOP_LIST in matched_intents
        )
        is_informational = SearchIntent.INFORMATIONAL in matched_intents or is_question
        is_problem_solving = SearchIntent.PROBLEM_SOLVING in matched_intents
        is_audience_specific = SearchIntent.AUDIENCE_SPECIFIC in matched_intents
        is_location_specific = SearchIntent.LOCATION_SPECIFIC in matched_intents

        return KeywordClassification(
            keyword=display,
            normalized_key=key,
            word_count=word_count,
            tail_length=tail,
            intent_labels=matched_intents,
            primary_intent=primary_intent,
            confidence_scores=confidence_scores,
            matched_reasons=matched_reasons,
            primary_explanation=primary_explanation,
            is_question=is_question,
            is_listicle=is_listicle,
            is_review=is_review,
            is_tutorial=is_tutorial,
            is_comparison=is_comparison,
            is_buying_intent=is_buying_intent,
            is_commercial_investigation=is_commercial,
            is_informational=is_informational,
            is_problem_solving=is_problem_solving,
            is_audience_specific=is_audience_specific,
            is_location_specific=is_location_specific,
        )

    def batch_classify(self, keywords: List[str]) -> List[KeywordClassification]:
        """Classify a list of keywords."""
        return [self.classify(k) for k in keywords]


# Default singleton instance
default_classifier = KeywordClassifier()
BilingualClassifier = KeywordClassifier

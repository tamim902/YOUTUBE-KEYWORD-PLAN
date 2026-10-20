"""Deduplication and provenance merging engine."""

from typing import Dict, List, Optional, Tuple
from src.crawler.models import DiscoveredKeyword
from src.utils.normalization import (
    find_fuzzy_duplicates,
    fuzzy_similarity,
    normalize_keyword_display,
    normalize_keyword_key,
)


class DeduplicationEngine:
    """Manages canonical key deduplication, provenance merging, and non-destructive fuzzy suggestions."""

    @staticmethod
    def merge_two_records(
        existing: DiscoveredKeyword, incoming: DiscoveredKeyword
    ) -> DiscoveredKeyword:
        """Merge provenance and metadata from an incoming record into an existing record without data loss."""
        # Merge sources set
        existing_sources = set(existing.sources or [existing.source_type])
        incoming_sources = set(incoming.sources or [incoming.source_type])
        merged_sources = list(sorted(existing_sources | incoming_sources))
        existing.sources = merged_sources

        # Provenance precedence: autocomplete takes priority over generated for primary source_type
        if "autocomplete" in merged_sources:
            existing.source_type = "autocomplete"
            existing.source_name = "youtube_autocomplete"
        elif not existing.source_type:
            existing.source_type = incoming.source_type
            existing.source_name = incoming.source_name

        # Merge paths and parent queries
        existing.discovery_paths += incoming.discovery_paths
        for pq in incoming.parent_queries:
            if pq and pq not in existing.parent_queries:
                existing.parent_queries.append(pq)

        # Retain minimum discovery depth
        if incoming.depth < existing.depth:
            existing.depth = incoming.depth

        # Retain earliest first_discovered_at and latest last_discovered_at
        if incoming.first_discovered_at < existing.first_discovered_at:
            existing.first_discovered_at = incoming.first_discovered_at
        if incoming.last_discovered_at > existing.last_discovered_at:
            existing.last_discovered_at = incoming.last_discovered_at

        # Flag as generated if either was generated
        if incoming.is_generated or "generated" in merged_sources:
            existing.is_generated = True

        # Preserve pattern metadata
        if not existing.pattern_category and incoming.pattern_category:
            existing.pattern_category = incoming.pattern_category
        if not existing.pattern_template and incoming.pattern_template:
            existing.pattern_template = incoming.pattern_template

        # Preserve classification metadata if incoming has it
        if not existing.tail_length and getattr(incoming, "tail_length", None):
            existing.tail_length = incoming.tail_length
        if not existing.intent_labels and getattr(incoming, "intent_labels", None):
            existing.intent_labels = incoming.intent_labels
        if not existing.word_count and getattr(incoming, "word_count", None):
            existing.word_count = incoming.word_count

        return existing

    def deduplicate(
        self, keywords: List[DiscoveredKeyword]
    ) -> List[DiscoveredKeyword]:
        """Deduplicate a list of DiscoveredKeyword records by their canonical normalized key.

        Preserves original display keyword and merges provenance rather than discarding records.
        """
        canonical_map: Dict[str, DiscoveredKeyword] = {}

        for kw in keywords:
            key = kw.normalized_key or normalize_keyword_key(kw.keyword)
            kw.normalized_key = key
            if not kw.sources:
                kw.sources = [kw.source_type]

            if key not in canonical_map:
                canonical_map[key] = kw
            else:
                self.merge_two_records(canonical_map[key], kw)

        return list(canonical_map.values())

    @staticmethod
    def get_fuzzy_duplicate_suggestions(
        keywords: List[str], threshold: float = 0.85
    ) -> List[Tuple[str, str, float]]:
        """Identify potential near-duplicate or misspelled keywords without modifying or deleting data."""
        return find_fuzzy_duplicates(keywords, threshold=threshold)


# Singleton instance
default_deduplicator = DeduplicationEngine()

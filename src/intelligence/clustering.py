"""Deterministic, rule-based Topic Clustering Engine for YouTube Keywords.

Groups discovered keywords into semantic clusters while:
- Preserving original keyword text and full provenance.
- Avoiding merging unrelated topics solely because they share a seed word (e.g. 'car' or 'wax').
- Providing clear, human-readable explanations of why each cluster was formed.
- Supporting manual cluster renaming, keyword moving, and cluster exclusion.
"""

import collections
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Union

from src.utils.normalization import normalize_keyword_key, tokenize_keyword

# Semantic cluster rules with regex pattern and descriptive explanation
SEMANTIC_CLUSTER_PATTERNS = [
    (
        "Paint Colors & Finishes",
        re.compile(r"\b(black|white|red|dark|blue|silver|grey|gray|clear coat|paint|matte)\b", re.IGNORECASE),
        "Grouped by vehicle paint color, finish type, or exterior coat",
    ),
    (
        "Comparisons & Alternatives",
        re.compile(r"\b(vs|versus|difference between|compared to|comparison|alternatives?|or)\b", re.IGNORECASE),
        "Grouped by head-to-head comparison queries or product alternatives",
    ),
    (
        "Reviews & Evaluations",
        re.compile(r"\b(reviews?|honest review|tested|testing|ratings?|worth it|hands on|unboxing)\b", re.IGNORECASE),
        "Grouped by product testing, appraisal, ratings, or user reviews",
    ),
    (
        "How-To & Application Guides",
        re.compile(r"\b(how to apply|how to use|how to|application|apply|applying|steps|guide|tips|technique|method)\b", re.IGNORECASE),
        "Grouped by application techniques, instructional guides, and tutorials",
    ),
    (
        "Pricing & Buying Guides",
        re.compile(r"\b(price|cost|buy|cheap|affordable|budget|where to buy|deal|deals|discount)\b", re.IGNORECASE),
        "Grouped by pricing, purchasing, budget options, or commercial queries",
    ),
    (
        "Target Audience & Vehicle Types",
        re.compile(r"\b(for beginners?|for old cars?|for new cars?|for daily drivers?|professionals?|pros?|diy)\b", re.IGNORECASE),
        "Grouped by specific target user segment or vehicle condition",
    ),
    (
        "Troubleshooting & Defect Removal",
        re.compile(r"\b(fix|scratches?|haze|haziness|swirls?|streak|streaks|residue|remove|stains?|repair)\b", re.IGNORECASE),
        "Grouped by scratch removal, streak troubleshooting, and paint defect repair",
    ),
    (
        "Formulations & Product Types",
        re.compile(r"\b(spray|liquid|paste|ceramic|carnauba|synthetic|sealant|graphene|hybrid)\b", re.IGNORECASE),
        "Grouped by chemical formulation, delivery format, or technology type",
    ),
]


@dataclass
class TopicCluster:
    """Represents a coherent topic cluster of discovered keywords."""

    name: str
    explanation: str
    keywords: List[str] = field(default_factory=list)
    keyword_items: List[Dict[str, Any]] = field(default_factory=list)
    is_excluded: bool = False

    @property
    def count(self) -> int:
        return len(self.keywords)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "explanation": self.explanation,
            "keywords": self.keywords,
            "keyword_items": self.keyword_items,
            "is_excluded": self.is_excluded,
            "count": self.count,
        }


class TopicClusteringEngine:
    """Groups keywords into explainable topic clusters using transparent rules."""

    def __init__(self) -> None:
        pass

    def cluster_keywords(
        self,
        keywords: List[Any],
        seed_keyword: str = "",
    ) -> List[TopicCluster]:
        """Cluster keywords into semantic groups.

        Args:
            keywords: List of keyword strings, KeywordItem, or DiscoveredKeyword objects.
            seed_keyword: Original research seed keyword to prevent clustering on common seed words.

        Returns:
            List of TopicCluster objects.
        """
        if not keywords:
            return []

        clean_seed = unicodedata.normalize("NFC", seed_keyword.strip().lower())
        seed_tokens = set(tokenize_keyword(clean_seed))

        # Clusters dictionary: name -> TopicCluster
        clusters: Dict[str, TopicCluster] = {}

        def get_or_create_cluster(name: str, explanation: str) -> TopicCluster:
            if name not in clusters:
                clusters[name] = TopicCluster(name=name, explanation=explanation)
            return clusters[name]

        # Process each keyword
        for item in keywords:
            if hasattr(item, "keyword"):
                kw_text = item.keyword
                item_dict = item.to_dict() if hasattr(item, "to_dict") else vars(item)
            elif isinstance(item, dict) and "keyword" in item:
                kw_text = item["keyword"]
                item_dict = item
            else:
                kw_text = str(item)
                item_dict = {"keyword": kw_text}

            clean_kw = unicodedata.normalize("NFC", kw_text.strip())
            norm_kw = normalize_keyword_key(clean_kw)

            assigned = False

            # 1. Match semantic cluster patterns
            for cluster_name, pattern, explanation in SEMANTIC_CLUSTER_PATTERNS:
                if pattern.search(clean_kw):
                    c = get_or_create_cluster(cluster_name, explanation)
                    c.keywords.append(clean_kw)
                    c.keyword_items.append(item_dict)
                    assigned = True
                    break

            if assigned:
                continue

            # 2. Bigram / Modifier subtopic clustering for keywords not matching predefined patterns
            kw_tokens = [t for t in tokenize_keyword(norm_kw) if t not in seed_tokens and len(t) > 2]
            if len(kw_tokens) >= 2:
                # Group by prominent modifier pair
                subtopic = f"{kw_tokens[0].title()} {kw_tokens[1].title()} Ideas"
                c = get_or_create_cluster(
                    subtopic,
                    f"Grouped by shared modifier concept: '{kw_tokens[0]} {kw_tokens[1]}'",
                )
                c.keywords.append(clean_kw)
                c.keyword_items.append(item_dict)
                assigned = True
            elif len(kw_tokens) == 1:
                subtopic = f"{kw_tokens[0].title()} Focus"
                c = get_or_create_cluster(
                    subtopic,
                    f"Grouped by modifier term: '{kw_tokens[0]}'",
                )
                c.keywords.append(clean_kw)
                c.keyword_items.append(item_dict)
                assigned = True

            # 3. Fallback to Core / General Seed Variations
            if not assigned:
                c = get_or_create_cluster(
                    "Core Seed Variations",
                    "Direct expansions and baseline variations of the seed topic",
                )
                c.keywords.append(clean_kw)
                c.keyword_items.append(item_dict)

        # Sort clusters by size descending, but keep Core Seed Variations near top if non-empty
        sorted_clusters = sorted(
            clusters.values(),
            key=lambda c: (1 if c.name == "Core Seed Variations" else 0, len(c.keywords)),
            reverse=True,
        )
        return sorted_clusters

    @staticmethod
    def rename_cluster(
        clusters: List[TopicCluster], old_name: str, new_name: str
    ) -> bool:
        """Rename an existing cluster."""
        clean_new = new_name.strip()
        if not clean_new:
            return False
        for c in clusters:
            if c.name.lower() == old_name.lower():
                c.name = clean_new
                return True
        return False

    @staticmethod
    def move_keyword(
        clusters: List[TopicCluster],
        keyword: str,
        from_cluster_name: str,
        to_cluster_name: str,
    ) -> bool:
        """Move a keyword from one cluster to another."""
        clean_kw = keyword.strip()
        from_c = next((c for c in clusters if c.name.lower() == from_cluster_name.lower()), None)
        to_c = next((c for c in clusters if c.name.lower() == to_cluster_name.lower()), None)

        if not from_c or not to_c or clean_kw not in from_c.keywords:
            return False

        # Remove from source
        idx = from_c.keywords.index(clean_kw)
        from_c.keywords.pop(idx)
        moved_item = from_c.keyword_items.pop(idx) if idx < len(from_c.keyword_items) else {"keyword": clean_kw}

        # Add to destination
        to_c.keywords.append(clean_kw)
        to_c.keyword_items.append(moved_item)
        return True

    @staticmethod
    def exclude_cluster(clusters: List[TopicCluster], cluster_name: str, exclude: bool = True) -> bool:
        """Toggle exclusion of a cluster from results."""
        for c in clusters:
            if c.name.lower() == cluster_name.lower():
                c.is_excluded = exclude
                return True
        return False

    @staticmethod
    def get_active_clusters(clusters: List[TopicCluster]) -> List[TopicCluster]:
        """Return only non-excluded clusters."""
        return [c for c in clusters if not c.is_excluded]


default_clusterer = TopicClusteringEngine()

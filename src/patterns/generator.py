"""Smart Keyword Pattern Generator.

Produces high-intent search query variations across 8 categories in English and Bangla
without requiring external APIs or paid AI services.
"""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from src.crawler.models import DiscoveredKeyword, normalize_keyword_key
from src.patterns.models import (
    GeneratedKeyword,
    PatternCategory,
    PatternConfig,
    PatternLanguage,
)
from src.patterns.templates import (
    BN_TEMPLATES,
    COMPARISON_GENERAL_BN,
    COMPARISON_GENERAL_EN,
    COMPARISON_SPECIFIC_BN,
    COMPARISON_SPECIFIC_EN,
    EN_TEMPLATES,
)


class SmartKeywordPatternGenerator:
    """Offline, deterministic keyword pattern generator with de-stuttering and strict provenance."""

    @staticmethod
    def destutter(text: str) -> str:
        """Collapse consecutive duplicate words and 2-word phrases.

        Prevents awkward repetitive patterns like:
        - "python tutorial tutorial" -> "python tutorial"
        - "best best camera" -> "best camera"
        - "how to how to code" -> "how to code"
        - "সেরা সেরা ক্যামেরা" -> "সেরা ক্যামেরা"
        """
        if not text:
            return ""
        normalized = unicodedata.normalize("NFC", text)
        cleaned = re.sub(r"\s+", " ", normalized).strip()
        words = cleaned.split(" ")

        # Step 1: Detect and collapse repeated 2-word phrases: words[i:i+2] == words[i+2:i+4]
        i = 0
        while i < len(words) - 3:
            if (
                words[i].lower() == words[i + 2].lower()
                and words[i + 1].lower() == words[i + 3].lower()
            ):
                del words[i + 2 : i + 4]
            else:
                i += 1

        # Step 2: Detect and collapse repeated single adjacent words
        i = 0
        while i < len(words) - 1:
            if words[i].lower() == words[i + 1].lower():
                del words[i + 1]
            else:
                i += 1

        return " ".join(words)

    @staticmethod
    def sanitize_alternatives(
        alternatives: Optional[List[str]], seed: str
    ) -> List[str]:
        """Validate, clean, and filter comparison alternative candidates.

        Strictly rejects empty values, single characters, or tokens identical to the seed.
        """
        if not alternatives:
            return []
        cleaned: List[str] = []
        seed_key = normalize_keyword_key(seed)
        seen = set()

        for alt in alternatives:
            if not alt or not isinstance(alt, str):
                continue
            normalized = unicodedata.normalize("NFC", alt.strip())
            alt_key = normalize_keyword_key(normalized)
            if len(normalized) < 2:
                continue
            if alt_key == seed_key:
                continue
            if alt_key in seen:
                continue
            seen.add(alt_key)
            cleaned.append(normalized)

        return cleaned

    def generate(self, config: PatternConfig) -> List[GeneratedKeyword]:
        """Generate deduplicated keyword variations based on config."""
        results: List[GeneratedKeyword] = []
        seen_keys: Set[str] = set()

        current_year = config.current_year or datetime.now(timezone.utc).year

        # Determine languages to generate
        languages: List[Tuple[str, Dict[PatternCategory, List[str]]]] = []
        if config.language_mode in (PatternLanguage.EN, PatternLanguage.BOTH):
            languages.append(("en", EN_TEMPLATES))
        if config.language_mode in (PatternLanguage.BN, PatternLanguage.BOTH):
            languages.append(("bn", BN_TEMPLATES))

        for seed in config.seeds:
            seed_norm = unicodedata.normalize("NFC", seed.strip())
            seed_key = normalize_keyword_key(seed_norm)
            valid_alternatives = self.sanitize_alternatives(config.alternatives, seed_norm)

            for lang_code, template_dict in languages:
                for category in config.categories:
                    # Category-specific template extraction
                    templates_to_apply: List[str] = []

                    if category == PatternCategory.COMPARISON:
                        # General comparison templates always apply
                        general_templates = (
                            COMPARISON_GENERAL_EN
                            if lang_code == "en"
                            else COMPARISON_GENERAL_BN
                        )
                        templates_to_apply.extend(general_templates)

                        # Specific comparison templates only apply if valid alternatives exist
                        if valid_alternatives:
                            specific_templates = (
                                COMPARISON_SPECIFIC_EN
                                if lang_code == "en"
                                else COMPARISON_SPECIFIC_BN
                            )
                            for alt in valid_alternatives:
                                for stpl in specific_templates:
                                    filled_stpl = stpl.replace("[alternative]", alt)
                                    templates_to_apply.append(filled_stpl)

                    elif category == PatternCategory.TIME_MODIFIERS:
                        if config.include_current_year:
                            raw_time_templates = template_dict.get(category, [])
                            for tpl in raw_time_templates:
                                filled_tpl = tpl.replace("[current_year]", str(current_year))
                                templates_to_apply.append(filled_tpl)
                        # If include_current_year is False, skip time modifiers

                    else:
                        templates_to_apply = template_dict.get(category, [])

                    # Apply each template with substitution, de-stuttering, and deduplication
                    for tpl in templates_to_apply:
                        raw_substituted = tpl.replace("[keyword]", seed_norm)
                        destuttered = self.destutter(raw_substituted)
                        cleaned_keyword = unicodedata.normalize("NFC", destuttered.strip())
                        cand_key = normalize_keyword_key(cleaned_keyword)

                        # Skip empty, self-referential seed equivalents, or already-seen keys
                        if not cand_key or cand_key == seed_key or cand_key in seen_keys:
                            continue

                        seen_keys.add(cand_key)
                        kw_item = GeneratedKeyword(
                            keyword=cleaned_keyword,
                            normalized_key=cand_key,
                            pattern_category=category,
                            pattern_template=tpl,
                            seed_keyword=seed_norm,
                            language=lang_code,
                        )
                        results.append(kw_item)

                        if (
                            config.max_generated is not None
                            and len(results) >= config.max_generated
                        ):
                            return results

        return results

    @staticmethod
    def merge_provenance(
        existing_keywords: List[DiscoveredKeyword],
        generated_keywords: List[GeneratedKeyword],
    ) -> List[DiscoveredKeyword]:
        """Merge generated keywords into discovered keywords with strict provenance preservation.

        Rules:
        - If an autocomplete keyword matches a generated keyword, preserve source_type="autocomplete"
          and mark is_generated=True.
        - If a generated keyword does not match an existing autocomplete keyword, add it with
          source_type="generated" and is_generated=True.
        """
        merged_map: Dict[str, DiscoveredKeyword] = {}

        # 1. Populate with existing discovered keywords
        for k in existing_keywords:
            merged_map[k.normalized_key] = k

        # 2. Merge generated keywords
        for gen in generated_keywords:
            if gen.normalized_key in merged_map:
                existing = merged_map[gen.normalized_key]
                # Keep existing source_type ("autocomplete" is never overwritten by "generated")
                existing.is_generated = True
                if not existing.sources:
                    existing.sources = [existing.source_type]
                if "generated" not in existing.sources:
                    existing.sources.append("generated")
                if not existing.pattern_category:
                    existing.pattern_category = gen.pattern_category.value
                if not existing.pattern_template:
                    existing.pattern_template = gen.pattern_template
            else:
                from src.classifier import default_classifier

                cls = default_classifier.classify(gen.keyword)
                # Add as generated keyword
                new_item = DiscoveredKeyword(
                    keyword=gen.keyword,
                    normalized_key=gen.normalized_key,
                    depth=0,
                    parent_queries=[gen.seed_keyword],
                    discovery_paths=1,
                    source_type="generated",
                    source_name="pattern_generator",
                    language=gen.language,
                    first_discovered_at=gen.generation_timestamp,
                    last_discovered_at=gen.generation_timestamp,
                    is_generated=True,
                    pattern_category=gen.pattern_category.value,
                    pattern_template=gen.pattern_template,
                    sources=["generated"],
                    tail_length=cls.tail_length.value,
                    intent_labels=[i.value for i in cls.intent_labels],
                    word_count=cls.word_count,
                )
                merged_map[gen.normalized_key] = new_item

        return list(merged_map.values())

"""Unit and regression tests for Phase 4 Smart Keyword Pattern Generator.

All tests operate 100% offline with zero external network requests or API keys.
"""

import unicodedata
from datetime import datetime, timezone
import pytest

from src.crawler.models import DiscoveredKeyword, normalize_keyword_key
from src.models.keyword import ClassificationType, SourceType
from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import (
    GeneratedKeyword,
    PatternCategory,
    PatternConfig,
    PatternLanguage,
)


@pytest.fixture
def generator() -> SmartKeywordPatternGenerator:
    """Fixture providing a fresh pattern generator instance."""
    return SmartKeywordPatternGenerator()


def test_listicles_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 1: Listicle pattern generation (Top 5, Top 10, Best 5, Best 10, etc.)."""
    cfg = PatternConfig(
        seeds=["python frameworks"],
        categories=[PatternCategory.LISTICLES],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert any("top 5 python frameworks" in kw for kw in keywords)
    assert any("top 10 python frameworks" in kw for kw in keywords)
    assert any("best 5 python frameworks" in kw for kw in keywords)
    assert any("best 10 python frameworks" in kw for kw in keywords)
    assert all(r.pattern_category == PatternCategory.LISTICLES for r in results)
    assert all(r.source_type == "generated" for r in results)


def test_best_and_buying_intent_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 2: Best and buying intent pattern generation."""
    cfg = PatternConfig(
        seeds=["wireless earbuds"],
        categories=[PatternCategory.BEST_BUYING],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert any("best wireless earbuds" in kw for kw in keywords)
    assert any("best budget wireless earbuds" in kw for kw in keywords)
    assert any("affordable wireless earbuds" in kw for kw in keywords)
    assert any("wireless earbuds buying guide" in kw for kw in keywords)
    assert any("is wireless earbuds worth it" in kw for kw in keywords)
    assert all(r.pattern_category == PatternCategory.BEST_BUYING for r in results)


def test_reviews_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 3: Review pattern generation."""
    cfg = PatternConfig(
        seeds=["mechanical keyboard"],
        categories=[PatternCategory.REVIEWS],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert any("mechanical keyboard review" in kw for kw in keywords)
    assert any("mechanical keyboard honest review" in kw for kw in keywords)
    assert any("mechanical keyboard detailed review" in kw for kw in keywords)
    assert all(r.pattern_category == PatternCategory.REVIEWS for r in results)


def test_how_to_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 4: How-to and tutorial pattern generation."""
    cfg = PatternConfig(
        seeds=["build a website"],
        categories=[PatternCategory.HOW_TO],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert any("how to build a website" in kw for kw in keywords)
    assert any("build a website tutorial" in kw for kw in keywords)
    assert any("build a website step by step" in kw for kw in keywords)
    assert all(r.pattern_category == PatternCategory.HOW_TO for r in results)


def test_comparison_patterns_without_alternatives(
    generator: SmartKeywordPatternGenerator,
) -> None:
    """Test 5: Comparison patterns without alternatives produce general comparisons only and never invent alternatives."""
    cfg = PatternConfig(
        seeds=["fastapi"],
        categories=[PatternCategory.COMPARISON],
        language_mode=PatternLanguage.EN,
        alternatives=None,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert "fastapi vs alternatives" in keywords
    assert "fastapi comparison" in keywords
    # Never invent a specific alternative
    for kw in keywords:
        assert "[alternative]" not in kw
        assert "django" not in kw
        assert "flask" not in kw


def test_comparison_patterns_with_valid_alternatives(
    generator: SmartKeywordPatternGenerator,
) -> None:
    """Test 6: Comparison patterns with verified user-supplied alternatives generate specific head-to-head pairs."""
    cfg = PatternConfig(
        seeds=["fastapi"],
        categories=[PatternCategory.COMPARISON],
        language_mode=PatternLanguage.EN,
        alternatives=["django", "flask"],
    )
    results = generator.generate(cfg)
    keywords = [r.keyword.lower() for r in results]

    # Specific pairs
    assert "fastapi vs django" in keywords
    assert "fastapi vs flask" in keywords
    assert "difference between fastapi and django" in keywords
    assert "difference between fastapi and flask" in keywords
    # General comparisons still present
    assert "fastapi vs alternatives" in keywords
    assert "fastapi comparison" in keywords


def test_comparison_patterns_reject_empty_or_invalid_alternatives(
    generator: SmartKeywordPatternGenerator,
) -> None:
    """Test 7: Comparison patterns strictly reject empty, whitespace, short, or self-matching alternatives."""
    cfg = PatternConfig(
        seeds=["fastapi"],
        categories=[PatternCategory.COMPARISON],
        language_mode=PatternLanguage.EN,
        alternatives=["", "   ", "a", "fastapi"],  # all invalid
    )
    results = generator.generate(cfg)
    keywords = [r.keyword.lower() for r in results]

    assert "fastapi vs alternatives" in keywords
    assert "fastapi comparison" in keywords
    # Invalid alternatives must NOT produce specific patterns
    assert "fastapi vs a" not in keywords
    assert "fastapi vs fastapi" not in keywords
    assert "fastapi vs " not in keywords


def test_questions_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 8: Questions pattern generation."""
    cfg = PatternConfig(
        seeds=["docker"],
        categories=[PatternCategory.QUESTIONS],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert any("what is docker" in kw for kw in keywords)
    assert any("how does docker work" in kw for kw in keywords)
    assert any("why is docker important" in kw for kw in keywords)
    assert any("when to use docker" in kw for kw in keywords)
    assert any("which docker is best" in kw for kw in keywords)
    assert any("can beginners use docker" in kw for kw in keywords)


def test_audience_use_case_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 9: Audience and use-case pattern generation."""
    cfg = PatternConfig(
        seeds=["accounting software"],
        categories=[PatternCategory.AUDIENCE],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert any("accounting software for beginners" in kw for kw in keywords)
    assert any("accounting software for students" in kw for kw in keywords)
    assert any("accounting software for small business" in kw for kw in keywords)
    assert any("accounting software for daily use" in kw for kw in keywords)
    assert any("accounting software on a budget" in kw for kw in keywords)


def test_time_modifiers_dynamic_year(generator: SmartKeywordPatternGenerator) -> None:
    """Test 10: Dynamic time modifiers with current year and toggle."""
    expected_year = datetime.now(timezone.utc).year
    cfg = PatternConfig(
        seeds=["seo tools"],
        categories=[PatternCategory.TIME_MODIFIERS],
        language_mode=PatternLanguage.EN,
        include_current_year=True,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    keywords = [r.keyword.lower() for r in results]
    assert f"best seo tools {expected_year}" in keywords
    assert f"seo tools guide {expected_year}" in keywords
    assert f"new seo tools {expected_year}" in keywords
    assert f"seo tools updates {expected_year}" in keywords

    # Test custom specified year
    cfg_custom = PatternConfig(
        seeds=["seo tools"],
        categories=[PatternCategory.TIME_MODIFIERS],
        language_mode=PatternLanguage.EN,
        include_current_year=True,
        current_year=2030,
    )
    results_custom = generator.generate(cfg_custom)
    keywords_custom = [r.keyword.lower() for r in results_custom]
    assert f"best seo tools 2030" in keywords_custom

    # Test disabled current year
    cfg_disabled = PatternConfig(
        seeds=["seo tools"],
        categories=[PatternCategory.TIME_MODIFIERS],
        language_mode=PatternLanguage.EN,
        include_current_year=False,
    )
    results_disabled = generator.generate(cfg_disabled)
    assert len(results_disabled) == 0


def test_bangla_unicode_nfc_normalized_generation(
    generator: SmartKeywordPatternGenerator,
) -> None:
    """Test 11: Bangla Unicode NFC normalized generation across categories."""
    seed_bn = "পাইথন প্রোগ্রামিং"
    cfg = PatternConfig(
        seeds=[seed_bn],
        categories=[
            PatternCategory.LISTICLES,
            PatternCategory.BEST_BUYING,
            PatternCategory.REVIEWS,
            PatternCategory.HOW_TO,
            PatternCategory.QUESTIONS,
        ],
        language_mode=PatternLanguage.BN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    for r in results:
        # Verify strict Unicode NFC normalization
        assert unicodedata.is_normalized("NFC", r.keyword)
        assert r.language == "bn"
        assert r.source_type == "generated"

    keywords = [r.keyword for r in results]
    assert any("সেরা ৫ পাইথন প্রোগ্রামিং" in kw for kw in keywords)
    assert any("পাইথন প্রোগ্রামিং রিভিউ" in kw for kw in keywords)
    assert any("কিভাবে পাইথন প্রোগ্রামিং করবেন" in kw for kw in keywords)
    assert any("পাইথন প্রোগ্রামিং কি" in kw for kw in keywords)


def test_bilingual_mode_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 12: Bilingual generation mode ('both' produces both English and Bangla)."""
    cfg = PatternConfig(
        seeds=["python"],
        categories=[PatternCategory.HOW_TO],
        language_mode=PatternLanguage.BOTH,
    )
    results = generator.generate(cfg)
    languages = {r.language for r in results}

    assert "en" in languages
    assert "bn" in languages
    assert any("how to python" in r.keyword.lower() for r in results if r.language == "en")
    assert any("কিভাবে python করবেন" in r.keyword for r in results if r.language == "bn")


def test_english_only_mode_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 13: English-only mode produces only English."""
    cfg = PatternConfig(
        seeds=["camera"],
        categories=[PatternCategory.REVIEWS],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0
    assert all(r.language == "en" for r in results)
    # Ensure no Bengali characters exist in output
    for r in results:
        assert not any("\u0980" <= ch <= "\u09ff" for ch in r.keyword)


def test_bangla_only_mode_generation(generator: SmartKeywordPatternGenerator) -> None:
    """Test 14: Bangla-only mode produces only Bangla."""
    cfg = PatternConfig(
        seeds=["ক্যামেরা"],
        categories=[PatternCategory.REVIEWS],
        language_mode=PatternLanguage.BN,
    )
    results = generator.generate(cfg)
    assert len(results) > 0
    assert all(r.language == "bn" for r in results)
    for r in results:
        assert any("\u0980" <= ch <= "\u09ff" for ch in r.keyword)


def test_destuttering_tutorial(generator: SmartKeywordPatternGenerator) -> None:
    """Test 15: De-stuttering: seed already containing 'tutorial' does not produce 'tutorial tutorial'."""
    # Direct method test
    assert generator.destutter("python tutorial tutorial") == "python tutorial"

    # Generator run
    cfg = PatternConfig(
        seeds=["python tutorial"],
        categories=[PatternCategory.HOW_TO],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    for r in results:
        assert "tutorial tutorial" not in r.keyword.lower()


def test_destuttering_best(generator: SmartKeywordPatternGenerator) -> None:
    """Test 16: De-stuttering: seed already containing 'best' does not produce 'best best'."""
    assert generator.destutter("best best camera") == "best camera"

    cfg = PatternConfig(
        seeds=["best camera"],
        categories=[PatternCategory.BEST_BUYING, PatternCategory.LISTICLES],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    for r in results:
        assert "best best" not in r.keyword.lower()


def test_destuttering_how_to(generator: SmartKeywordPatternGenerator) -> None:
    """Test 17: De-stuttering: seed already containing 'how to' does not produce 'how to how to'."""
    assert generator.destutter("how to how to code") == "how to code"

    cfg = PatternConfig(
        seeds=["how to code"],
        categories=[PatternCategory.HOW_TO],
        language_mode=PatternLanguage.EN,
    )
    results = generator.generate(cfg)
    for r in results:
        assert "how to how to" not in r.keyword.lower()


def test_deduplication_within_session(generator: SmartKeywordPatternGenerator) -> None:
    """Test 18: Deduplication of generated keywords within a session."""
    cfg = PatternConfig(
        seeds=["python"],
        categories=list(PatternCategory),
        language_mode=PatternLanguage.BOTH,
    )
    results = generator.generate(cfg)
    assert len(results) > 0

    seen_keys = set()
    for r in results:
        key = normalize_keyword_key(r.keyword)
        assert key not in seen_keys, f"Duplicate keyword found: '{r.keyword}'"
        seen_keys.add(key)


def test_max_generated_limit_enforcement(generator: SmartKeywordPatternGenerator) -> None:
    """Test 19: Generation limit / max keywords enforcement."""
    cfg = PatternConfig(
        seeds=["javascript"],
        categories=list(PatternCategory),
        language_mode=PatternLanguage.BOTH,
        max_generated=15,
    )
    results = generator.generate(cfg)
    assert len(results) == 15


def test_provenance_merging_preserves_autocomplete(
    generator: SmartKeywordPatternGenerator,
) -> None:
    """Test 20: Provenance merging: autocomplete keyword matched with generated keyword preserves autocomplete source_type."""
    # Autocomplete keyword from recursive crawl or live search
    existing_autocomplete = DiscoveredKeyword(
        keyword="python tutorial",
        normalized_key=normalize_keyword_key("python tutorial"),
        depth=1,
        parent_queries=["python"],
        discovery_paths=2,
        source_type="autocomplete",
        source_name="youtube_autocomplete",
    )

    # Generated keyword with the exact same normalized query
    gen_match = GeneratedKeyword(
        keyword="python tutorial",
        normalized_key=normalize_keyword_key("python tutorial"),
        pattern_category=PatternCategory.HOW_TO,
        pattern_template="[keyword] tutorial",
        seed_keyword="python",
        language="en",
    )

    # Generated keyword with a distinct query
    gen_distinct = GeneratedKeyword(
        keyword="best python tutorial",
        normalized_key=normalize_keyword_key("best python tutorial"),
        pattern_category=PatternCategory.BEST_BUYING,
        pattern_template="best [keyword]",
        seed_keyword="python tutorial",
        language="en",
    )

    merged = generator.merge_provenance(
        existing_keywords=[existing_autocomplete],
        generated_keywords=[gen_match, gen_distinct],
    )

    assert len(merged) == 2
    merged_by_key = {k.normalized_key: k for k in merged}

    matched_item = merged_by_key["python tutorial"]
    # Critical rule: autocomplete source_type is strictly preserved
    assert matched_item.source_type == "autocomplete"
    assert matched_item.source_name == "youtube_autocomplete"
    assert matched_item.depth == 1
    assert matched_item.is_generated is True
    assert matched_item.pattern_category == "how_to"

    distinct_item = merged_by_key["best python tutorial"]
    # Distinct generated keyword retains generated attribution
    assert distinct_item.source_type == "generated"
    assert distinct_item.source_name == "pattern_generator"
    assert distinct_item.is_generated is True
    assert distinct_item.depth == 0


def test_invalid_pattern_config_validation(generator: SmartKeywordPatternGenerator) -> None:
    """Test invalid pattern configurations raise appropriate ValueError."""
    with pytest.raises(ValueError, match="At least one seed keyword is required"):
        PatternConfig(seeds=[])

    with pytest.raises(ValueError, match="At least one pattern category must be enabled"):
        PatternConfig(seeds=["python"], categories=[])

    with pytest.raises(ValueError, match="max_generated must be positive"):
        PatternConfig(seeds=["python"], max_generated=0)

    with pytest.raises(ValueError, match="current_year must be valid"):
        PatternConfig(seeds=["python"], current_year=1999)


def test_generated_keyword_model_conversion() -> None:
    """Test GeneratedKeyword to_dict and to_keyword_item conversions."""
    gen = GeneratedKeyword(
        keyword="best laptop for students",
        normalized_key=normalize_keyword_key("best laptop for students"),
        pattern_category=PatternCategory.AUDIENCE,
        pattern_template="[keyword] for students",
        seed_keyword="best laptop",
        language="en",
    )
    d = gen.to_dict()
    assert d["keyword"] == "best laptop for students"
    assert d["category"] == "audience"
    assert d["source_type"] == "generated"

    item = gen.to_keyword_item()
    assert item.keyword == "best laptop for students"
    assert item.source == SourceType.GENERATED
    assert item.seed_keyword == "best laptop"

"""Tests for domain models and classifications."""

import pytest
from src.models.keyword import (
    ClassificationType,
    KeywordItem,
    SourceType,
    calculate_word_count,
    infer_tail_length,
)


def test_keyword_item_creation() -> None:
    """Test standard KeywordItem creation and properties."""
    item = KeywordItem(
        keyword="python programming tutorial",
        seed_keyword="python",
        source=SourceType.LIVE,
        classification=ClassificationType.HOW_TO,
        depth=1,
    )
    assert item.keyword == "python programming tutorial"
    assert item.word_count == 3
    assert item.source == SourceType.LIVE
    assert item.classification == ClassificationType.HOW_TO
    assert item.depth == 1


def test_bangla_unicode_support() -> None:
    """Test word count and KeywordItem with Bangla Unicode text."""
    bangla_text = "পাইথন প্রোগ্রামিং শিখুন সহজে"
    item = KeywordItem(
        keyword=bangla_text,
        seed_keyword="পাইথন",
        source=SourceType.ALGORITHMIC,
        classification=ClassificationType.TUTORIAL if hasattr(ClassificationType, 'TUTORIAL') else ClassificationType.GENERAL,
        language="bn",
        country="BD",
    )
    assert item.keyword == bangla_text
    assert item.word_count == 4
    assert item.language == "bn"
    assert item.source == SourceType.ALGORITHMIC


def test_keyword_item_validation() -> None:
    """Test validation errors for empty keywords or negative depth."""
    with pytest.raises(ValueError, match="Keyword string cannot be empty"):
        KeywordItem(
            keyword="   ",
            seed_keyword="python",
            source=SourceType.LIVE,
        )

    with pytest.raises(ValueError, match="Seed keyword cannot be empty"):
        KeywordItem(
            keyword="python tutorial",
            seed_keyword="",
            source=SourceType.LIVE,
        )

    with pytest.raises(ValueError, match="Depth must be non-negative"):
        KeywordItem(
            keyword="python tutorial",
            seed_keyword="python",
            source=SourceType.LIVE,
            depth=-1,
        )


def test_to_dict_serialization() -> None:
    """Test serialization of KeywordItem to dict for DataFrames."""
    item = KeywordItem(
        keyword="best camera 2026",
        seed_keyword="camera",
        source=SourceType.CACHED,
        classification=ClassificationType.LISTICLE,
    )
    d = item.to_dict()
    assert d["keyword"] == "best camera 2026"
    assert d["source"] == "cached"
    assert d["classification"] == "Listicle"
    assert d["word_count"] == 3
    assert "created_at" in d


def test_tail_length_inference() -> None:
    """Test infer_tail_length categorization."""
    assert infer_tail_length(1) == ClassificationType.SHORT_TAIL
    assert infer_tail_length(2) == ClassificationType.SHORT_TAIL
    assert infer_tail_length(3) == ClassificationType.MEDIUM_TAIL
    assert infer_tail_length(4) == ClassificationType.MEDIUM_TAIL
    assert infer_tail_length(5) == ClassificationType.LONG_TAIL
    assert infer_tail_length(8) == ClassificationType.LONG_TAIL

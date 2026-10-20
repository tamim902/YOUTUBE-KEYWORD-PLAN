"""Tests for Unicode input sanitization and crawl parameter limits."""

import unicodedata
from src.utils.validators import sanitize_seed_keyword, validate_crawl_parameters


def test_sanitize_seed_keyword_valid() -> None:
    """Test standard valid English seed keywords."""
    is_valid, text, err = sanitize_seed_keyword("  python tutorial  ")
    assert is_valid
    assert text == "python tutorial"
    assert err == ""


def test_sanitize_seed_keyword_bangla() -> None:
    """Test Bangla Unicode seed keywords."""
    raw = "পাইথন প্রোগ্রামিং টিউটোরিয়াল"
    is_valid, text, err = sanitize_seed_keyword(raw)
    assert is_valid
    assert text == unicodedata.normalize("NFC", raw)
    assert err == ""


def test_sanitize_seed_keyword_empty_or_whitespace() -> None:
    """Test validation rejection for empty or whitespace-only inputs."""
    is_valid, text, err = sanitize_seed_keyword("")
    assert not is_valid
    assert "empty" in err

    is_valid, text, err = sanitize_seed_keyword("    ")
    assert not is_valid
    assert "whitespace" in err


def test_sanitize_seed_keyword_length_bounds() -> None:
    """Test min and max length bounds."""
    is_valid, text, err = sanitize_seed_keyword("a")
    assert not is_valid
    assert "at least 2 characters" in err

    oversized = "a" * 200
    is_valid, text, err = sanitize_seed_keyword(oversized)
    assert not is_valid
    assert "cannot exceed 150 characters" in err


def test_validate_crawl_parameters() -> None:
    """Test bounds checking on max depth and request budget."""
    valid, err = validate_crawl_parameters(max_depth=2, request_budget=50)
    assert valid
    assert err == ""

    # Invalid max depth
    valid, err = validate_crawl_parameters(max_depth=-1, request_budget=50)
    assert not valid
    assert "Max depth" in err

    valid, err = validate_crawl_parameters(max_depth=10, request_budget=50)
    assert not valid
    assert "Max depth" in err

    # Invalid request budget
    valid, err = validate_crawl_parameters(max_depth=2, request_budget=0)
    assert not valid
    assert "Request budget" in err

    valid, err = validate_crawl_parameters(max_depth=2, request_budget=500)
    assert not valid
    assert "Request budget" in err

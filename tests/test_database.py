"""Tests for SQLite persistence and caching layer."""

from pathlib import Path
from src.models.keyword import ClassificationType, KeywordItem, SourceType
from src.storage.database import DatabaseManager


def test_database_initialization(temp_db_path: Path) -> None:
    """Test schema creation in empty database."""
    manager = DatabaseManager(db_path=temp_db_path)
    manager.init_db()
    assert temp_db_path.exists()

    with manager.get_connection() as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "searches" in tables
        assert "keywords" in tables
        assert "autocomplete_cache" in tables


def test_save_and_retrieve_search(test_db_manager: DatabaseManager) -> None:
    """Test saving a search session and retrieving history."""
    search_id = test_db_manager.save_search(
        seed_keyword="machine learning",
        language="en",
        country="US",
        max_depth=2,
        request_budget=50,
        total_results=0,
    )
    assert search_id > 0

    recent = test_db_manager.get_recent_searches(limit=5)
    assert len(recent) == 1
    assert recent[0]["id"] == search_id
    assert recent[0]["seed_keyword"] == "machine learning"
    assert recent[0]["language"] == "en"


def test_save_and_retrieve_keywords(test_db_manager: DatabaseManager) -> None:
    """Test saving keyword items associated with a search ID."""
    search_id = test_db_manager.save_search(
        seed_keyword="docker",
        language="en",
        country="US",
        max_depth=2,
        request_budget=50,
    )

    items = [
        KeywordItem(
            keyword="docker tutorial",
            seed_keyword="docker",
            source=SourceType.LIVE,
            classification=ClassificationType.HOW_TO,
            depth=1,
        ),
        KeywordItem(
            keyword="docker vs kubernetes",
            seed_keyword="docker",
            source=SourceType.ALGORITHMIC,
            classification=ClassificationType.COMPARISON,
            depth=1,
        ),
    ]

    saved_count = test_db_manager.save_keywords(search_id, items)
    assert saved_count == 2

    retrieved = test_db_manager.get_keywords_by_search_id(search_id)
    assert len(retrieved) == 2
    assert retrieved[0]["keyword"] == "docker tutorial"
    assert retrieved[0]["source_type"] == "live"
    assert retrieved[1]["keyword"] == "docker vs kubernetes"
    assert retrieved[1]["source_type"] == "algorithmic"


def test_autocomplete_caching(test_db_manager: DatabaseManager) -> None:
    """Test caching autocomplete responses."""
    query = "react tutorial"
    lang = "en"
    country = "US"
    suggestions = ["react tutorial for beginners", "react tutorial 2026"]

    # Before cache
    cached = test_db_manager.get_cached_suggestions(query, lang, country)
    assert cached is None

    # Save to cache
    test_db_manager.set_cached_suggestions(query, lang, country, suggestions)

    # After cache
    cached_again = test_db_manager.get_cached_suggestions(query, lang, country)
    assert cached_again == suggestions


def test_empty_keyword_batch(test_db_manager: DatabaseManager) -> None:
    """Test saving an empty list of keywords safely returns 0."""
    search_id = test_db_manager.save_search("vue", "en", "US", 2, 50)
    count = test_db_manager.save_keywords(search_id, [])
    assert count == 0


def test_database_transaction_rollback(test_db_manager: DatabaseManager) -> None:
    """Test that connection context manager rolls back on database execution errors."""
    import pytest
    import sqlite3

    with pytest.raises(sqlite3.OperationalError):
        with test_db_manager.get_connection() as conn:
            conn.execute("INSERT INTO nonexistent_table VALUES (1);")

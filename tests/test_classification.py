"""Automated unit, integration, and regression tests for Phase 5:
Classification, Normalization, Deduplication, Provenance Merging, and Database Migration.

All tests operate 100% offline with zero live network calls.
"""

import io
import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pytest

from src.classifier import (
    KeywordClassification,
    KeywordClassifier,
    SearchIntent,
    TailLength,
    TailThresholds,
    default_classifier,
)
from src.crawler.models import DiscoveredKeyword
from src.deduplication import DeduplicationEngine, default_deduplicator
from src.models.keyword import ClassificationType, KeywordItem, SourceType
from src.storage.database import DatabaseManager
from src.utils.normalization import (
    count_tokens,
    find_fuzzy_duplicates,
    fuzzy_similarity,
    normalize_keyword_display,
    normalize_keyword_key,
    normalize_unicode_nfc,
    normalize_whitespace,
    tokenize_keyword,
)


# 1. English token counting
def test_english_token_counting() -> None:
    """Test 1: Unicode-aware English token counting across short and long phrases."""
    assert count_tokens("python") == 1
    assert count_tokens("python tutorial") == 2
    assert count_tokens("how to learn python programming") == 5
    assert count_tokens("   best   wireless    earbuds   ") == 3


# 2. Bangla Unicode token counting
def test_bangla_unicode_token_counting() -> None:
    """Test 2: Bangla Unicode token counting preserving Bengali characters and diacritics."""
    assert count_tokens("পাইথন") == 1
    assert count_tokens("পাইথন প্রোগ্রামিং") == 2
    assert count_tokens("সহজে পাইথন শেখার উপায়") == 4
    assert count_tokens("নতুনদের জন্য সেরা পাইথন টিউটোরিয়াল") == 5


# 3. Mixed-language keywords
def test_mixed_language_keywords() -> None:
    """Test 3: Token counting and normalization for mixed English and Bangla queries."""
    text = "python বাংলা tutorial"
    tokens = tokenize_keyword(text)
    assert len(tokens) == 3
    assert tokens == ["python", "বাংলা", "tutorial"]
    assert count_tokens("React JS দিয়ে ওয়েবসাইট তৈরি") == 5


# 4. Unicode normalization (NFC)
def test_unicode_nfc_normalization() -> None:
    """Test 4: Strict Unicode NFC normalization for Bengali decomposed vs composed forms."""
    # Decomposed Bengali 'য' + nukta vs composed 'য়'
    decomposed = "\u09af\u09bc"
    composed = "\u09df"
    assert decomposed != composed
    norm_decomposed = normalize_unicode_nfc(decomposed)
    norm_composed = normalize_unicode_nfc(composed)
    assert norm_decomposed == norm_composed
    assert unicodedata.is_normalized("NFC", norm_decomposed)


# 5. Whitespace normalization
def test_whitespace_normalization() -> None:
    """Test 5: Trimming and collapsing of whitespace (tabs, newlines, multi-spaces)."""
    raw = " \t  machine   \n learning   basics   \t"
    cleaned = normalize_whitespace(raw)
    assert cleaned == "machine learning basics"
    display = normalize_keyword_display(raw)
    assert display == "machine learning basics"


# 6. Case-insensitive duplicates
def test_case_insensitive_duplicates() -> None:
    """Test 6: Case-insensitivity in normalized keys for comparison and deduplication."""
    k1 = "Python Tutorial"
    k2 = "python tutorial"
    k3 = "PYTHON TUTORIAL"
    key1 = normalize_keyword_key(k1)
    key2 = normalize_keyword_key(k2)
    key3 = normalize_keyword_key(k3)
    assert key1 == key2 == key3 == "python tutorial"


# 7. Meaningful punctuation preservation
def test_meaningful_punctuation_preservation() -> None:
    """Test 7: Preservation of technical symbols and syntax (+, #, ., -, ?)."""
    tokens = tokenize_keyword("c++ tutorial for beginners")
    assert "c++" in tokens

    tokens_csharp = tokenize_keyword("c# vs .net core")
    assert "c#" in tokens_csharp
    assert ".net" in tokens_csharp or ".net core" in " ".join(tokens_csharp)

    tokens_node = tokenize_keyword("node.js backend development")
    assert "node.js" in tokens_node

    tokens_hyphen = tokenize_keyword("step-by-step how-to guide")
    assert "step-by-step" in tokens_hyphen
    assert "how-to" in tokens_hyphen


# 8. Numbers and symbols
def test_numbers_and_symbols_preservation() -> None:
    """Test 8: Preservation of version numbers, Bangla numerals, and symbols."""
    text_ver = "python 3.12 features and updates"
    assert "3.12" in tokenize_keyword(text_ver)
    assert count_tokens(text_ver) == 5

    text_bn_num = "সেরা ১০ টি পাইথন টিপস"
    tokens_bn = tokenize_keyword(text_bn_num)
    assert "১০" in tokens_bn
    assert count_tokens(text_bn_num) == 5


# 9. Multiple provenance sources
def test_multiple_provenance_sources() -> None:
    """Test 9: Merging records from multiple sources preserves all source attributions."""
    rec1 = DiscoveredKeyword(
        keyword="fastapi tutorial",
        normalized_key="fastapi tutorial",
        depth=1,
        source_type="autocomplete",
        source_name="youtube_autocomplete",
        sources=["autocomplete"],
    )
    rec2 = DiscoveredKeyword(
        keyword="fastapi tutorial",
        normalized_key="fastapi tutorial",
        depth=0,
        source_type="generated",
        source_name="pattern_generator",
        sources=["generated"],
        is_generated=True,
    )

    merged = default_deduplicator.merge_two_records(rec1, rec2)
    assert "autocomplete" in merged.sources
    assert "generated" in merged.sources
    # Autocomplete remains the primary source_type
    assert merged.source_type == "autocomplete"
    assert merged.is_generated is True
    assert merged.depth == 0  # retained minimum depth


# 10. Distinct keyword preservation
def test_distinct_keyword_preservation() -> None:
    """Test 10: Distinct keywords with different semantics are never conflated or merged."""
    kws = [
        DiscoveredKeyword(keyword="python tutorial", normalized_key="python tutorial", depth=1),
        DiscoveredKeyword(keyword="python interview", normalized_key="python interview", depth=1),
        DiscoveredKeyword(keyword="python project", normalized_key="python project", depth=1),
    ]
    deduped = default_deduplicator.deduplicate(kws)
    assert len(deduped) == 3
    keys = {k.normalized_key for k in deduped}
    assert keys == {"python tutorial", "python interview", "python project"}


# 11. Fuzzy duplicate suggestions
def test_fuzzy_duplicate_suggestions() -> None:
    """Test 11: Non-destructive fuzzy duplicate detection identifies near-duplicates."""
    candidates = [
        "python tutorial",
        "pythn tutorial",       # 1 char typo
        "fastapi tutorial",
        "fastapi tutorial 2026",
    ]
    suggestions = find_fuzzy_duplicates(candidates, threshold=0.85)
    assert len(suggestions) > 0
    # Should flag ("python tutorial", "pythn tutorial")
    matched_pairs = [(s[0], s[1]) for s in suggestions]
    assert any(
        ("python tutorial" in pair and "pythn tutorial" in pair)
        for pair in matched_pairs
    )
    # Original list remains untouched (non-destructive)
    assert len(candidates) == 4


# 12. Each tail category
def test_tail_categories() -> None:
    """Test 12: Short-tail, Medium-tail, and Long-tail classifications with custom thresholds."""
    classifier = KeywordClassifier(TailThresholds(short_max=2, medium_max=4))

    c1 = classifier.classify("python")
    assert c1.tail_length == TailLength.SHORT_TAIL
    assert c1.word_count == 1

    c2 = classifier.classify("python web development")
    assert c2.tail_length == TailLength.MEDIUM_TAIL
    assert c2.word_count == 3

    c3 = classifier.classify("how to build a website with python and flask")
    assert c3.tail_length == TailLength.LONG_TAIL
    assert c3.word_count == 9

    # Test custom thresholds: short <= 1, medium 2-3, long >= 4
    custom_classifier = KeywordClassifier(TailThresholds(short_max=1, medium_max=3))
    assert custom_classifier.classify("python tutorial").tail_length == TailLength.MEDIUM_TAIL
    assert custom_classifier.classify("best python tutorial online").tail_length == TailLength.LONG_TAIL


# 13. Multiple intent labels
def test_multiple_intent_labels() -> None:
    """Test 13: A keyword can have multiple concurrent intent labels."""
    cls = default_classifier.classify("how to buy best camera review")
    # "how to" -> Tutorial
    # "buy" -> Buying Intent
    # "best" -> Commercial Investigation
    # "review" -> Review
    intents = cls.intent_labels
    assert SearchIntent.TUTORIAL in intents
    assert SearchIntent.BUYING_INTENT in intents
    assert SearchIntent.REVIEW in intents
    assert SearchIntent.COMMERCIAL_INVESTIGATION in intents
    assert cls.is_tutorial is True
    assert cls.is_buying_intent is True
    assert cls.is_review is True


# 14. Source type versus search intent separation
def test_source_type_vs_search_intent_separation() -> None:
    """Test 14: Source type provenance and search intent classification remain strictly decoupled."""
    kw_item = KeywordItem(
        keyword="how to install docker",
        seed_keyword="docker",
        source=SourceType.AUTOCOMPLETE,
    )
    cls = default_classifier.classify(kw_item.keyword)

    # Source is provenance; Intent is semantic category
    assert kw_item.source == SourceType.AUTOCOMPLETE
    assert cls.primary_intent in (SearchIntent.TUTORIAL, SearchIntent.QUESTION)
    # The source must not overwrite intent, and intent must not overwrite source
    assert kw_item.source.value != cls.primary_intent.value


# 15. Database uniqueness
def test_database_uniqueness(tmp_path: Path) -> None:
    """Test 15: Database prevents duplicate records for the same search session."""
    db_file = tmp_path / "test_unique.db"
    mgr = DatabaseManager(db_file)
    mgr.init_db()

    search_id = mgr.save_search(
        seed_keyword="python",
        language="en",
        country="US",
        max_depth=1,
        request_budget=5,
    )

    items = [
        KeywordItem(keyword="python tutorial", seed_keyword="python", source=SourceType.AUTOCOMPLETE),
        KeywordItem(keyword="python tutorial", seed_keyword="python", source=SourceType.GENERATED),
        KeywordItem(keyword="python guide", seed_keyword="python", source=SourceType.AUTOCOMPLETE),
    ]

    saved_count = mgr.save_keywords(search_id, items)
    assert saved_count == 3

    # Query back: should have only 2 unique rows in keywords table
    rows = mgr.get_keywords_by_search_id(search_id)
    assert len(rows) == 2
    keys = {r["normalized_key"] for r in rows}
    assert keys == {"python tutorial", "python guide"}

    # Verified merged sources on the duplicated keyword
    py_tut = [r for r in rows if r["normalized_key"] == "python tutorial"][0]
    assert "autocomplete" in py_tut["sources"]
    assert "generated" in py_tut["sources"]


# 16. Fresh database creation
def test_fresh_database_creation(tmp_path: Path) -> None:
    """Test 16: Initializing a fresh database creates all required Phase 5 columns and indexes."""
    db_file = tmp_path / "fresh.db"
    mgr = DatabaseManager(db_file)
    mgr.init_db()

    with mgr.get_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(keywords);")
        cols = {row["name"] for row in cursor.fetchall()}
        required_cols = {
            "id", "search_id", "keyword", "seed_keyword", "source_type",
            "classification", "depth", "parent_keyword", "language", "country",
            "created_at", "normalized_key", "tail_length", "intent_labels",
            "sources_json", "word_count"
        }
        assert required_cols.issubset(cols)

        # Check indexes
        cursor = conn.execute("PRAGMA index_list(keywords);")
        indexes = {row["name"] for row in cursor.fetchall()}
        assert "idx_keywords_norm_key" in indexes
        assert "idx_keywords_tail" in indexes


# 17. Existing database migration
def test_existing_database_migration(tmp_path: Path) -> None:
    """Test 17: Safely migrating a legacy Phase 1–4 database adds columns and backfills data without data loss."""
    legacy_db = tmp_path / "legacy.db"
    # Create legacy schema without Phase 5 columns
    conn = sqlite3.connect(legacy_db)
    conn.execute(
        """
        CREATE TABLE searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seed_keyword TEXT NOT NULL,
            language TEXT NOT NULL,
            country TEXT NOT NULL,
            max_depth INTEGER NOT NULL,
            request_budget INTEGER NOT NULL,
            total_results INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER,
            keyword TEXT NOT NULL,
            seed_keyword TEXT NOT NULL,
            source_type TEXT NOT NULL,
            classification TEXT NOT NULL,
            depth INTEGER NOT NULL,
            parent_keyword TEXT,
            language TEXT NOT NULL,
            country TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        INSERT INTO keywords (
            search_id, keyword, seed_keyword, source_type, classification, depth, language, country, created_at
        ) VALUES (1, 'Legacy Python Tutorial', 'python', 'autocomplete', 'General', 1, 'en', 'US', '2026-10-01T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()

    # Now use DatabaseManager to initialize/migrate
    mgr = DatabaseManager(legacy_db)
    mgr.init_db()

    # Verify that existing row was preserved and backfilled
    rows = mgr.get_keywords_by_search_id(1)
    assert len(rows) == 1
    legacy_row = rows[0]
    assert legacy_row["keyword"] == "Legacy Python Tutorial"
    assert legacy_row["normalized_key"] == "legacy python tutorial"
    assert legacy_row["word_count"] == 3
    assert legacy_row["tail_length"] == "Medium-tail"
    assert legacy_row["sources"] == ["autocomplete"]


# 18. Provenance merging after repeated research
def test_provenance_merging_after_repeated_research(tmp_path: Path) -> None:
    """Test 18: Repeatedly running research merges provenance sources rather than duplicating records."""
    db_file = tmp_path / "repeat.db"
    mgr = DatabaseManager(db_file)
    mgr.init_db()

    search_id = mgr.save_search("fastapi", "en", "US", 1, 5)

    # First run: direct autocomplete
    mgr.save_keywords(
        search_id,
        [KeywordItem(keyword="fastapi vs flask", seed_keyword="fastapi", source=SourceType.AUTOCOMPLETE)],
    )

    # Second run: pattern generator adds same keyword
    mgr.save_keywords(
        search_id,
        [KeywordItem(keyword="fastapi vs flask", seed_keyword="fastapi", source=SourceType.GENERATED)],
    )

    rows = mgr.get_keywords_by_search_id(search_id)
    assert len(rows) == 1
    rec = rows[0]
    assert rec["keyword"] == "fastapi vs flask"
    assert "autocomplete" in rec["sources"]
    assert "generated" in rec["sources"]


# 19. CSV/XLSX compatibility
def test_csv_xlsx_compatibility() -> None:
    """Test 19: CSV and XLSX exports preserve text (English and Bangla NFC) and provenance."""
    classifier = default_classifier
    kws = [
        "python tutorial for beginners",
        "fastapi vs django comparison",
        "পাইথন প্রোগ্রামিং বাংলা টিউটোরিয়াল",
    ]
    data = []
    for idx, kw in enumerate(kws):
        cls = classifier.classify(kw)
        data.append({
            "#": idx + 1,
            "Keyword": cls.keyword,
            "Normalized Key": cls.normalized_key,
            "Tail Type": cls.tail_length.value,
            "Word Count": cls.word_count,
            "Primary Intent": cls.primary_intent.value,
            "All Intents": ", ".join(i.value for i in cls.intent_labels),
            "Source": "Autocomplete" if idx == 0 else "Autocomplete (+Pattern)",
            "All Sources": "autocomplete" if idx == 0 else "autocomplete, generated",
            "Depth": idx,
            "Discovery Paths": idx + 1,
            "Parent Queries": "python, coding" if idx > 0 else "(seed)",
            "Language": "bn" if idx == 2 else "en",
            "Country": "BD" if idx == 2 else "US",
        })

    df = pd.DataFrame(data)
    # Check DataFrame attributes
    assert len(df) == 3
    assert "Tail Type" in df.columns
    assert "Primary Intent" in df.columns
    assert "All Sources" in df.columns

    # 1. Check CSV export and read-back preserving Unicode and provenance
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    df_from_csv = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8")
    assert len(df_from_csv) == 3
    assert df_from_csv.iloc[2]["Keyword"] == data[2]["Keyword"]
    assert df_from_csv.iloc[2]["All Sources"] == "autocomplete, generated"
    assert df_from_csv.iloc[2]["Tail Type"] == "Medium-tail"
    assert df_from_csv.iloc[1]["Parent Queries"] == "python, coding"

    # 2. Check Excel (.xlsx via openpyxl) export and read-back preserving Unicode and provenance
    excel_buf = io.BytesIO()
    df.to_excel(excel_buf, index=False, engine="openpyxl")
    excel_buf.seek(0)
    df_from_xlsx = pd.read_excel(excel_buf, engine="openpyxl")
    assert len(df_from_xlsx) == 3
    assert df_from_xlsx.iloc[2]["Keyword"] == data[2]["Keyword"]
    assert df_from_xlsx.iloc[2]["All Sources"] == "autocomplete, generated"
    assert df_from_xlsx.iloc[2]["Tail Type"] == "Medium-tail"
    assert df_from_xlsx.iloc[1]["Parent Queries"] == "python, coding"



# 20. Phase 1–4 regression tests
def test_phase1_to_4_regressions() -> None:
    """Test 20: Regression check verifying foundation models and previous phase guarantees."""
    # Phase 1: Models and tail inference
    from src.models.keyword import calculate_word_count, infer_tail_length
    assert calculate_word_count("hello world") == 2
    assert infer_tail_length(2) == ClassificationType.SHORT_TAIL

    # Phase 2: AutocompleteResult
    from src.models.keyword import AutocompleteResult
    res = AutocompleteResult(keyword="test autocomplete")
    assert res.source_type == "autocomplete"

    # Phase 3: Recursive crawler DiscoveredKeyword
    kw = DiscoveredKeyword(keyword="crawl test", normalized_key="crawl test", depth=1)
    assert kw.depth == 1
    assert kw.discovery_paths == 1

    # Phase 4: Pattern generator
    from src.patterns import SmartKeywordPatternGenerator, PatternConfig, PatternCategory
    gen = SmartKeywordPatternGenerator()
    patterns = gen.generate(PatternConfig(seeds=["testing"], categories=[PatternCategory.LISTICLES]))
    assert len(patterns) > 0
    assert any("top 5 testing" in p.keyword.lower() for p in patterns)


# 21. Dashboard filtering logic
def test_dashboard_filtering_logic() -> None:
    """Test 21: Verify multi-dimensional dashboard filtering logic across all dimensions."""
    keywords = [
        DiscoveredKeyword(keyword="python", normalized_key="python", depth=0, source_type="autocomplete", language="en", country="US"),
        DiscoveredKeyword(keyword="python tutorial for beginners", normalized_key="python tutorial for beginners", depth=1, source_type="autocomplete", language="en", country="US"),
        DiscoveredKeyword(keyword="how to install docker on windows step by step", normalized_key="how to install docker on windows step by step", depth=2, source_type="autocomplete", language="en", country="US"),
        DiscoveredKeyword(keyword="top 10 python tools", normalized_key="top 10 python tools", depth=0, source_type="generated", is_generated=True, language="en", country="US"),
        DiscoveredKeyword(keyword="পাইথন প্রোগ্রামিং বাংলা টিউটোরিয়াল", normalized_key="পাইথন প্রোগ্রামিং বাংলা টিউটোরিয়াল", depth=1, source_type="autocomplete", language="bn", country="BD"),
    ]

    classified_items = []
    for k in keywords:
        c = default_classifier.classify(k.keyword)
        tail = c.tail_length.value
        intents = [i.value for i in c.intent_labels]
        classified_items.append((k, tail, intents))

    # 1. Tail filtering
    short_items = [k for k, tail, _ in classified_items if tail == "Short-tail"]
    assert len(short_items) == 1
    assert short_items[0].keyword == "python"

    medium_items = [k for k, tail, _ in classified_items if tail == "Medium-tail"]
    assert len(medium_items) == 3

    long_items = [k for k, tail, _ in classified_items if tail == "Long-tail"]
    assert len(long_items) == 1
    assert "docker" in long_items[0].keyword

    # 2. Source filtering
    autocomplete_only = [k for k, _, _ in classified_items if k.source_type == "autocomplete"]
    assert len(autocomplete_only) == 4

    generated_only = [k for k, _, _ in classified_items if k.source_type == "generated" or k.is_generated]
    assert len(generated_only) == 1
    assert generated_only[0].keyword == "top 10 python tools"

    # 3. Language filtering
    bn_only = [k for k, _, _ in classified_items if k.language == "bn"]
    assert len(bn_only) == 1
    assert bn_only[0].keyword == "পাইথন প্রোগ্রামিং বাংলা টিউটোরিয়াল"

    # 4. Search intent filtering
    tutorials = [k for k, _, intents in classified_items if SearchIntent.TUTORIAL.value in intents]
    assert len(tutorials) >= 2

    # 5. Substring text filter
    docker_items = [k for k, _, _ in classified_items if "docker" in k.keyword.lower()]
    assert len(docker_items) == 1
    assert "docker" in docker_items[0].keyword


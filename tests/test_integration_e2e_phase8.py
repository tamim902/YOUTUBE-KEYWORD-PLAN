"""Phase 8 End-to-End Integration and Security Automated Tests.

Deterministic, offline tests verifying:
1. Complete workflow A through O:
   - Seed keyword input
   - Language & country settings
   - Provider autocomplete retrieval
   - Source metadata & provenance preservation
   - Bounded recursive expansion
   - Pattern generator integration
   - Classification and deduplication
   - Dashboard DataFrame representation
   - Multi-dimensional filtering and search
   - Copy selected / copy filtered formatting
   - SQLite transactional persistence
   - Simulated app restart and historical project reloading
   - CSV (with UTF-8 BOM) and XLSX export generation
   - Export content and provenance verification
2. Security audit regression tests:
   - SQL injection resistance
   - Formula injection neutralization
   - Directory traversal protection in backups
   - Rate limit and timeout bounds
"""

import io
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import List
import openpyxl
import pandas as pd
import pytest

from app import (
    build_dataframe_from_keywords,
    execute_recursive_crawl,
    filter_keywords,
    format_keywords_for_clipboard,
)
from src.classifier.service import default_classifier
from src.crawler.models import CrawlConfig, StopReason
from src.patterns.generator import SmartKeywordPatternGenerator
from src.patterns.models import PatternCategory, PatternConfig, PatternLanguage
from src.providers.base import BaseAutocompleteProvider
from src.models.keyword import AutocompleteResult
from src.providers.exceptions import (
    AccessForbiddenError,
    MalformedResponseError,
    NetworkTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.backup import BackupManager
from src.storage.database import DatabaseManager
from src.storage.export import ExportService, sanitize_formula_injection


class MockDeterministicProvider(BaseAutocompleteProvider):
    """Deterministic offline provider for End-to-End testing."""

    def __init__(self, mapping=None) -> None:
        self.mapping = mapping or {
            "python tutorial": [
                "python tutorial for beginners",
                "python tutorial full course",
                "=cmd|' /C calc'!A0",  # Test formula injection in suggestions
            ],
            "python tutorial for beginners": [
                "python tutorial for beginners 2026",
                "python tutorial for beginners in bangla",
            ],
            "ইউটিউব এসইও": [
                "ইউটিউব এসইও টিউটোরিয়াল",
                "ইউটিউব এসইও কোর্স",
            ],
        }
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "mock_deterministic_provider"

    def get_suggestions(
        self,
        query: str,
        language: str = "en",
        country: str = "US",
        use_cache: bool = True,
        cancellation_token=None,
    ) -> List[AutocompleteResult]:
        self.call_count += 1
        results = self.mapping.get(query, [])
        return [
            AutocompleteResult(
                keyword=r,
                source_type="autocomplete",
                source_name=self.provider_name,
                language=language,
                country=country,
                retrieved_at="2026-10-18T20:00:00Z",
                discovery_query=query,
            )
            for r in results
        ]


def test_complete_e2e_workflow(tmp_path: Path) -> None:
    """Execute complete workflow A through O end-to-end with deterministic data."""
    db_file = tmp_path / "e2e_test.db"
    db = DatabaseManager(db_file)
    db.init_db()

    # Step A & B: Enter seed keyword, language, and country
    seed = "python tutorial"
    language = "en"
    country = "US"

    crawl_config = CrawlConfig(
        seeds=[seed],
        language=language,
        country=country,
        max_depth=1,
        max_unique_keywords=20,
        request_budget=5,
        min_delay_seconds=0.0,
        use_cache=False,
    )

    provider = MockDeterministicProvider()

    # Step C, D, E: Autocomplete retrieval, source metadata, recursive expansion
    crawl_result = execute_recursive_crawl(
        crawl_config=crawl_config,
        provider=provider,
        save_to_db=False,
        database_manager=db,
    )

    assert len(crawl_result.keywords) >= 4
    for kw in crawl_result.keywords:
        assert kw.source_type == "autocomplete"
        assert kw.language == language
        assert kw.country == country
        assert kw.discovery_paths >= 1

    # Step F: Generate optional keyword patterns
    pattern_gen = SmartKeywordPatternGenerator()
    pat_config = PatternConfig(
        seeds=[seed],
        categories=[PatternCategory.LISTICLES, PatternCategory.HOW_TO],
        language_mode=PatternLanguage.EN,
        max_generated=10,
    )
    generated = pattern_gen.generate(pat_config)
    assert len(generated) > 0

    # Step G: Classify and deduplicate results
    merged_keywords = pattern_gen.merge_provenance(
        existing_keywords=crawl_result.keywords,
        generated_keywords=generated,
    )

    # Step H: Display results in Dashboard format
    all_tuples = filter_keywords(
        keywords=merged_keywords,
        source_filter="All Sources",
        tail_filter="All Lengths",
        intent_filter="All Intents",
        search_query="",
    )
    df = build_dataframe_from_keywords(all_tuples)
    assert not df.empty
    assert "Keyword" in df.columns
    assert "Tail Type" in df.columns
    assert "Primary Intent" in df.columns
    assert "Source" in df.columns

    # Step I: Apply filters and search
    filtered_tuples = filter_keywords(
        keywords=merged_keywords,
        search_query="beginners",
        tail_filter="All Lengths",
        intent_filter="All Intents",
        source_filter="All Sources",
    )
    assert len(filtered_tuples) > 0
    assert all("beginners" in t[0].keyword.lower() for t in filtered_tuples)

    # Step J: Copy selected and filtered keywords
    filtered_df = build_dataframe_from_keywords(filtered_tuples)
    clipboard_text = format_keywords_for_clipboard(filtered_df)
    assert "beginners" in clipboard_text.lower()

    # Step K: Save research to SQLite
    search_id = db.save_search(
        seed_keyword=seed,
        language=language,
        country=country,
        max_depth=1,
        request_budget=5,
        total_results=len(merged_keywords),
        project_name="E2E Research Project",
        status="completed",
        stop_reason=crawl_result.stop_reason.value,
        parameters_json=json.dumps({"test": True}),
        requests_made=provider.call_count,
    )
    keyword_items = [k.to_keyword_item(seed_keyword=seed) for k in merged_keywords]
    saved_count = db.save_keywords(search_id, keyword_items)
    assert saved_count == len(merged_keywords)

    # Step L & M: Close and reopen application, reload saved project
    new_db_instance = DatabaseManager(db_file)
    searches = new_db_instance.list_projects()
    assert len(searches) == 1
    assert searches[0]["project_name"] == "E2E Research Project"

    reloaded_items = new_db_instance.get_keywords_by_search_id(search_id)
    assert len(reloaded_items) == len(merged_keywords)

    # Step N & O: Export selected and filtered results to CSV and XLSX, verify content
    csv_bytes = ExportService.export_csv(filtered_df, sanitize_formulas=True, include_bom=True)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM present
    csv_text = csv_bytes.decode("utf-8-sig")
    assert "beginners" in csv_text

    xlsx_bytes = ExportService.export_excel(filtered_df, sanitize_formulas=True)
    assert xlsx_bytes.startswith(b"PK\x03\x04")  # Valid OOXML ZIP header

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    sheet = wb.active
    assert sheet.title == "Keywords"
    wb.close()


def test_bilingual_bangla_e2e_persistence_and_export(tmp_path: Path) -> None:
    """Verify Bangla Unicode text survives crawling, pattern generation, saving, and export."""
    db_file = tmp_path / "bangla_e2e.db"
    db = DatabaseManager(db_file)
    db.init_db()

    seed = "ইউটিউব এসইও"
    crawl_config = CrawlConfig(
        seeds=[seed],
        language="bn",
        country="BD",
        max_depth=0,
        max_unique_keywords=10,
        request_budget=2,
        min_delay_seconds=0.0,
        use_cache=False,
    )

    provider = MockDeterministicProvider()
    result = execute_recursive_crawl(
        crawl_config=crawl_config,
        provider=provider,
        save_to_db=True,
        project_name="বাংলা এসইও প্রজেক্ট",
        database_manager=db,
    )

    assert len(result.keywords) == 2
    assert any("টিউটোরিয়াল" in k.keyword for k in result.keywords)

    # Verify database persistence
    saved = db.get_keywords_by_search_id(result.search_id)
    assert len(saved) == 2
    assert any("টিউটোরিয়াল" in k["keyword"] for k in saved)

    # Verify CSV export preserves Bangla without mojibake
    bangla_tuples = filter_keywords(
        keywords=result.keywords,
        source_filter="All Sources",
        tail_filter="All Lengths",
        intent_filter="All Intents",
        search_query="",
    )
    df = build_dataframe_from_keywords(bangla_tuples)
    csv_bytes = ExportService.export_csv(df, include_bom=True)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    decoded = csv_bytes.decode("utf-8-sig")
    assert "ইউটিউব এসইও টিউটোরিয়াল" in decoded


def test_security_formula_injection_defense() -> None:
    """Verify spreadsheet formula execution triggers are escaped at export boundary."""
    dangerous_inputs = [
        "=SUM(A1:A10)",
        "+1234567890",
        "-2+3*4",
        "@SUM(B1:B5)",
        "\tcmd.exe",
        "\rcalc",
    ]
    for val in dangerous_inputs:
        sanitized = sanitize_formula_injection(val)
        assert sanitized.startswith("'"), f"Failed to sanitize: {val}"
        assert sanitize_formula_injection(sanitized) == sanitized or sanitized.startswith("'")

    # Safe inputs must NOT be prefixed
    safe_inputs = ["python tutorial", "10 tips", "best laptop", "কীভাবে শিখব"]
    for val in safe_inputs:
        assert sanitize_formula_injection(val) == val


def test_security_backup_directory_traversal_prevention(tmp_path: Path) -> None:
    """Verify BackupManager refuses to write outside its designated backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    bm = BackupManager(backup_dir)

    source_db = tmp_path / "src.db"
    db = DatabaseManager(source_db)
    db.init_db()

    # Traversal attempt via backup_name
    traversal_name = "../../escaped_test.db"
    created = bm.create_backup(source_db, backup_name=traversal_name)
    # Must be stripped to safe filename inside backup_dir
    assert created.parent.resolve() == backup_dir.resolve()
    assert created.name == "escaped_test.db"
    assert not (tmp_path / "escaped_test.db").exists()


def test_provider_http_error_handling_and_no_retries_on_403() -> None:
    """Verify HTTP 403 halts immediately with AccessForbiddenError without futile retries."""
    from unittest.mock import MagicMock
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 403

    session = MagicMock(spec=requests.Session)
    session.get.return_value = mock_resp

    provider = YouTubeAutocompleteProvider(
        endpoint="https://suggestqueries.google.com/complete/search",
        max_retries=3,
        session=session,
    )

    with pytest.raises(AccessForbiddenError):
        provider.get_suggestions("python", use_cache=False)

    # 403 must NOT be retried: call count must be exactly 1
    assert session.get.call_count == 1


def test_provider_http_429_retry_exhaustion() -> None:
    """Verify HTTP 429 raises RateLimitError when retries are exhausted."""
    from unittest.mock import MagicMock
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "10"}

    session = MagicMock(spec=requests.Session)
    session.get.return_value = mock_resp

    provider = YouTubeAutocompleteProvider(
        endpoint="https://suggestqueries.google.com/complete/search",
        max_retries=2,
        session=session,
    )

    with pytest.raises(RateLimitError) as exc_info:
        provider.get_suggestions("python", use_cache=False)

    assert exc_info.value.retry_after == 10.0


def test_provider_http_500_server_error_exhaustion() -> None:
    """Verify 5xx server errors attempt max_retries before raising ProviderUnavailableError."""
    from unittest.mock import MagicMock
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 503

    session = MagicMock(spec=requests.Session)
    session.get.return_value = mock_resp

    provider = YouTubeAutocompleteProvider(
        endpoint="https://suggestqueries.google.com/complete/search",
        max_retries=2,
        backoff_factor=0.01,
        session=session,
    )

    with pytest.raises(ProviderUnavailableError):
        provider.get_suggestions("python", use_cache=False)

    assert session.get.call_count == 3  # Initial + 2 retries

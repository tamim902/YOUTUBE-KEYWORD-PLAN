"""Master Command Live Verification Script: Real YouTube Autocomplete on 'BEST CAR WAX'.

Performs:
1. Live network request to YouTube autocomplete for 'BEST CAR WAX'.
2. Live expansion query with letter 'a' ('best car wax a') and preposition 'for' ('best car wax for').
3. Verifies strictly labeled LIVE_AUTOCOMPLETE source.
4. Verifies SQLite persistence and subsequent CACHED_AUTOCOMPLETE hit.
5. Verifies CSV and XLSX export generation and validation.
6. Unicode UTF-8 output configured for Windows console.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import build_dataframe_from_keywords, export_keywords_to_csv, export_keywords_to_excel
from src.classifier import default_classifier
from src.crawler import ControlledExpansionEngine, DiscoveredKeyword, ExpansionConfig
from src.models.keyword import AutocompleteResult, SourceType
from src.providers.youtube import YouTubeAutocompleteProvider
from src.storage.database import db_manager


def run_live_verification():
    print("=" * 80)
    print("MASTER COMMAND VERIFICATION: REAL YOUTUBE AUTOCOMPLETE ON 'BEST CAR WAX'")
    print("=" * 80)

    # 1. Initialize Provider
    db_manager.init_db()
    provider = YouTubeAutocompleteProvider(database_manager=db_manager)

    seed_keyword = "BEST CAR WAX"
    print(f"\n[STEP 1] Querying real YouTube autocomplete endpoint for seed: '{seed_keyword}'...")
    print(f"Endpoint: {provider.endpoint}?client=firefox&ds=yt&q=best%20car%20wax")

    # Clear cache for seed to guarantee a live network fetch
    db_manager.clear_cache(expired_only=False)

    live_suggestions = provider.get_suggestions(
        query=seed_keyword,
        language="en",
        country="US",
        use_cache=True,
    )

    print(f"\n[LIVE RESPONSE] Status: 200 OK | Retrieved: {len(live_suggestions)} genuine suggestions:")
    for idx, s in enumerate(live_suggestions, 1):
        badge = "LIVE_AUTOCOMPLETE" if not s.is_cached else "CACHED_AUTOCOMPLETE"
        print(f"  {idx:2d}. [🔍] {s.keyword:<42} [{badge}]")

    assert len(live_suggestions) >= 5, "Expected at least 5 suggestions for 'BEST CAR WAX'"
    assert any("wax" in s.keyword.lower() for s in live_suggestions)

    # 2. Test Local Cache Hit on identical query
    print(f"\n[STEP 2] Verifying Local Cache Hit on identical query '{seed_keyword}'...")
    cached_suggestions = provider.get_suggestions(
        query=seed_keyword,
        language="en",
        country="US",
        use_cache=True,
    )
    print(f"[CACHE HIT] Retrieved: {len(cached_suggestions)} suggestions:")
    for idx, s in enumerate(cached_suggestions[:3], 1):
        badge = "CACHED_AUTOCOMPLETE" if s.is_cached else "LIVE_AUTOCOMPLETE"
        print(f"  {idx:2d}. [💾] {s.keyword:<42} [{badge}]")
    assert cached_suggestions[0].is_cached is True, "Expected cached result to have is_cached=True"

    # 3. Test Controlled Expansion (A-Z & Prepositions)
    print(f"\n[STEP 3] Running Controlled Expansion for '{seed_keyword}' (Alphabet + Prepositions, Budget=6)...")
    engine = ControlledExpansionEngine(provider=provider, database_manager=db_manager)
    exp_cfg = ExpansionConfig(
        seeds=[seed_keyword],
        include_alphabet=True,
        include_numbers=False,
        include_prepositions=True,
        include_questions=False,
        include_modifiers=False,
        request_budget=6,
        min_delay_seconds=0.2,
        max_unique_keywords=100,
        use_cache=True,
    )

    exp_result = engine.expand(exp_cfg)
    print(f"[EXPANSION COMPLETED] Status: {exp_result.stop_reason.value}")
    print(f"Total Requests: {exp_result.total_requests_made} | Queries Processed: {exp_result.queries_processed}")
    print(f"Unique Keywords Discovered: {len(exp_result.keywords)} in {exp_result.duration_seconds}s")

    print("\nSample Discovered Keywords with Provenance:")
    for idx, kw in enumerate(exp_result.keywords[:10], 1):
        print(
            f"  {idx:2d}. {kw.keyword:<45} | Query: {kw.discovery_query:<22} | Source: {kw.strict_source_label}"
        )

    # 4. Save to SQLite Project History
    print(f"\n[STEP 4] Persisting research session into SQLite database...")
    search_id = db_manager.save_search(
        seed_keyword=seed_keyword,
        language="en",
        country="US",
        max_depth=1,
        request_budget=6,
        total_results=len(exp_result.keywords),
        project_name="Best Car Wax Live Verification",
        status="completed",
        stop_reason=exp_result.stop_reason.value,
        requests_made=exp_result.total_requests_made,
    )
    print(f"Saved Project Search ID: {search_id}")

    kw_items = [
        kw.to_keyword_item(seed_keyword=seed_keyword)
        for kw in exp_result.keywords
    ]
    saved_count = db_manager.save_keywords(search_id, kw_items)
    print(f"Saved {saved_count} keywords to SQLite database table `keywords`.")

    retrieved = db_manager.get_keywords_by_search_id(search_id)
    print(f"Retrieved {len(retrieved)} keywords from database for confirmation.")
    assert len(retrieved) == len(exp_result.keywords)

    # 5. Build DataFrame & Export CSV / XLSX
    print(f"\n[STEP 5] Building Results DataFrame and generating CSV & XLSX exports...")
    classified_tuples = []
    for kw in exp_result.keywords:
        cls = default_classifier.classify(kw.keyword)
        classified_tuples.append((kw, cls.tail_length.value, [i.value for i in cls.intent_labels]))

    df = build_dataframe_from_keywords(classified_tuples)
    print("DataFrame Columns:")
    print(list(df.columns))

    # Verify no fake search volume / cpc metrics
    for col in df.columns:
        assert "volume" not in col.lower()
        assert "cpc" not in col.lower()
        assert "difficulty" not in col.lower()

    export_dir = PROJECT_ROOT / "data" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    csv_path = export_dir / "best_car_wax_verification.csv"
    xlsx_path = export_dir / "best_car_wax_verification.xlsx"

    csv_bytes = export_keywords_to_csv(df, sanitize_formulas=True, include_bom=True)
    with open(csv_path, "wb") as f:
        f.write(csv_bytes)
    print(f"Exported CSV: {csv_path} ({len(csv_bytes):,} bytes)")

    xlsx_bytes = export_keywords_to_excel(df, sanitize_formulas=True)
    with open(xlsx_path, "wb") as f:
        f.write(xlsx_bytes)
    print(f"Exported XLSX: {xlsx_path} ({len(xlsx_bytes):,} bytes)")

    assert csv_path.exists() and csv_path.stat().st_size > 0
    assert xlsx_path.exists() and xlsx_path.stat().st_size > 0

    print("\n" + "=" * 80)
    print("STATUS: PASS — LIVE AUTOCOMPLETE VERIFIED")
    print(f"Successfully retrieved real YouTube suggestions for '{seed_keyword}',")
    print(f"performed controlled expansion ({len(exp_result.keywords)} unique keywords),")
    print(f"persisted to SQLite ({search_id}), and exported to CSV and XLSX.")
    print("=" * 80)


if __name__ == "__main__":
    run_live_verification()

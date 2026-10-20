"""Phase 12.1 Conservative Live API Verification Script.

Executes a live date-bounded YouTube search for candidate products in 'Wireless Earbuds'
over the last 60 days using the configured YouTube Data API v3 key.
Records actual returned videos, publish dates, query coverage, and classification.
Never exposes API credentials.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import sys

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.product_finder import (
    NicheProductPipeline,
    ProductExtractor,
    ProductMatcher,
    ProductOpportunityScorer,
)
from src.models.product import CandidateProduct, ProductResearchSession, SearchMode
from src.providers.serp import YouTubeDataApiSerpProvider
from src.storage.database import db_manager


def run_live_verification() -> None:
    print("==================================================================")
    print("PHASE 12.1 — LIVE YOUTUBE API VERIFICATION: NICHE PRODUCT DISCOVERY")
    print("==================================================================")

    # 1. Check Connectivity & Credentials
    provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
    api_key = provider.get_api_key()
    if not api_key:
        print("STATUS: NOT VERIFIED — No API key configured in database or environment.")
        return

    print("Checking connection to YouTube Data API v3...")
    is_ok, verify_msg = provider.verify_api_key(api_key)
    if not is_ok:
        print(f"STATUS: NOT VERIFIED — Key verification failed: {verify_msg}")
        return

    quota_before = db_manager.get_daily_quota_used()
    print(f"API Connection: Verified (Active)")
    print(f"Daily Quota Used Before Test: {quota_before} / 10,000 units")

    # 2. Date Range: Last 60 Days
    pipeline = NicheProductPipeline()
    start_iso, end_iso = pipeline.get_default_date_range(60)
    print(f"Date Range (RFC 3339, 60 days): {start_iso} to {end_iso}")

    # 3. Target Candidate: Sony WF-1000XM5 in Wireless Earbuds
    product = CandidateProduct(
        product_name="Sony WF-1000XM5",
        brand="Sony",
        model="WF-1000XM5",
        niche="Wireless Earbuds",
        source="Curated Market Catalog",
        verification_status="Verified Market Product",
        extraction_confidence="High",
        aliases=["Sony XM5 Earbuds", "Sony WF 1000XM5"],
    )

    extractor = ProductExtractor()
    matcher = ProductMatcher()
    scorer = ProductOpportunityScorer()

    queries = extractor.generate_search_queries(
        product,
        search_modes=[SearchMode.REVIEWS.value, SearchMode.UNBOXING.value],
        year=datetime.now(timezone.utc).year,
    )[:2]

    print(f"\nTarget Product: {product.product_name}")
    print(f"Search Queries to Execute ({len(queries)}):")
    for q_text, mode in queries:
        print(f"  - [{mode}] '{q_text}'")

    matched_videos = []
    executed_queries = []
    queries_succeeded = 0

    # 4. Execute Live Queries
    for q_text, mode in queries:
        print(f"\nExecuting Live SERP Query: '{q_text}' (publishedAfter={start_iso[:10]}, publishedBefore={end_iso[:10]})...")
        serp = provider.analyze_keyword(
            keyword=q_text,
            language="en",
            country="US",
            max_results=5,
            published_after=start_iso,
            published_before=end_iso,
            use_cache=False,  # Force live retrieval for verification
        )
        executed_queries.append(f"{q_text} ({mode})")
        if serp.status_message and "API Error" in serp.status_message:
            print(f"  Error: {serp.status_message}")
        else:
            queries_succeeded += 1
            print(f"  Retrieved {len(serp.videos)} videos within date range.")
            for v in serp.videos:
                is_m, m_type, m_field, m_terms = matcher.is_match(product, v.title, v.description)
                if is_m:
                    print(f"    [MATCH] '{v.title}' ({v.channel_title}) | Views: {v.view_count:,} | Published: {v.publish_date[:10]} | Match: {m_type}")
                    matched_videos.append({
                        "video_id": v.video_id,
                        "title": v.title,
                        "channel_title": v.channel_title,
                        "publish_date": v.publish_date,
                        "url": f"https://www.youtube.com/watch?v={v.video_id}",
                        "views": v.view_count,
                        "match_type": m_type,
                    })
                else:
                    print(f"    [NO MATCH] '{v.title}' (Isolated/Non-matching model)")

    # 5. Deduplicate Video Matches by Video ID
    deduped_vids = {v["video_id"]: v for v in matched_videos}
    unique_matches = list(deduped_vids.values())

    product.matching_videos_count = len(unique_matches)
    product.unique_channels_count = len(set(v["channel_title"] for v in unique_matches))
    product.queries_executed = executed_queries
    product.queries_succeeded = queries_succeeded
    product.data_source = "Live YouTube Data API v3"
    if unique_matches:
        dates = sorted([v["publish_date"] for v in unique_matches if v.get("publish_date")], reverse=True)
        product.latest_video_date = dates[0] if dates else None

    # 6. Score & Classify
    score, classification, conf, breakdown = scorer.calculate_score(
        product,
        few_videos_threshold=3,
        min_queries_for_zero_match=2,
    )
    product.opportunity_score = score
    product.classification = classification
    product.confidence_level = conf
    product.opportunity_score_breakdown = breakdown

    quota_after = db_manager.get_daily_quota_used()

    print("\n------------------------------------------------------------------")
    print("LIVE VERIFICATION RESULTS:")
    print("------------------------------------------------------------------")
    print(f"Product Investigated:       {product.product_name}")
    print(f"Queries Executed:           {len(executed_queries)} (Succeeded: {queries_succeeded})")
    print(f"Matching Videos Found:      {len(unique_matches)}")
    print(f"Unique Channels:            {product.unique_channels_count}")
    print(f"Latest Matching Video Date: {product.latest_video_date or 'None'}")
    print(f"Classification:             {classification}")
    print(f"Classification Reason:      {breakdown.get('classification_reason', '')}")
    print(f"Opportunity Score:          {score} / 100")
    print(f"Confidence Level:           {conf}")
    print(f"Data Source:                {product.data_source}")
    print(f"Quota Used During Run:      {quota_after - quota_before} units")
    print(f"Total Quota Today:          {quota_after} / 10,000 units")
    print(f"Empirical Limitation:       {breakdown.get('empirical_limitation_notice', '')}")
    print("==================================================================")


if __name__ == "__main__":
    run_live_verification()

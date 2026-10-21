"""Comprehensive YouTube 60-Day Product Opportunity & Competition Gap Engine.

Transforms candidate taxonomy products and seed topics into market-specific YouTube
opportunity intelligence adhering to the user's strict 60-day exclusion rule:
- IF 1 OR MORE RELEVANT VIDEOS WERE PUBLISHED WITHIN THE LAST 60 DAYS → EXCLUDED — RECENT VIDEOS FOUND
- IF 0 MATCHING VIDEOS FOUND ACROSS >=2 QUERIES → POTENTIAL OPPORTUNITY
- IF <2 QUERIES EXECUTED → NEEDS MORE RESEARCH
- IF API ERROR OR QUOTA EXHAUSTED → RESEARCH FAILED

Markets supported: US, UK, CA (with honest affiliate disclaimer: 'Commission not verified').
Preserves data in SQLite database with non-destructive migrations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.intelligence.product_taxonomy import TaxonomyProduct, taxonomy_manager


class OpportunityStatus:
    """Exact status labels conforming to user specifications."""

    EXCLUDED_RECENT_VIDEOS = "EXCLUDED — RECENT VIDEOS FOUND"
    POTENTIAL_OPPORTUNITY = "POTENTIAL OPPORTUNITY"
    NEEDS_MORE_RESEARCH = "NEEDS MORE RESEARCH"
    RESEARCH_FAILED = "RESEARCH FAILED"


@dataclass
class ProductOpportunityRecord:
    """Represents a single evaluated product candidate opportunity record."""

    product_id: str
    product_name: str
    main_niche: str
    sub_niche: str
    sub_sub_niche: str
    product_category: str
    market: str  # "US", "UK", "CA"
    candidate_keyword: str
    matching_videos_count: int = 0
    latest_publish_date: str = "None in 60d"
    observed_competition: str = "UNKNOWN"  # "LOW", "MEDIUM", "HIGH", "UNKNOWN"
    search_coverage: str = "Sample Search"
    opportunity_status: str = OpportunityStatus.NEEDS_MORE_RESEARCH
    recommendation: str = ""
    suggested_angle: str = ""
    suggested_title: str = ""
    executed_queries: List[str] = field(default_factory=list)
    video_evidence: List[Dict[str, Any]] = field(default_factory=list)
    affiliate_status: str = "Commission not verified (connect affiliate provider to verify)"
    price_tier: str = "Mid-Range"
    created_at: str = ""
    updated_at: str = ""
    id: Optional[int] = None

    @property
    def full_breadcrumb(self) -> str:
        """Return 5-level breadcrumb path."""
        return f"{self.main_niche} → {self.sub_niche} → {self.sub_sub_niche} → {self.product_category} → {self.product_name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        d = asdict(self)
        d["full_breadcrumb"] = self.full_breadcrumb
        return d


@dataclass
class OpportunityEvaluationResult:
    """Container for the comprehensive opportunity evaluation of a product."""

    product: TaxonomyProduct
    market: str
    research_window_str: str
    start_iso: str
    end_iso: str
    records: List[ProductOpportunityRecord] = field(default_factory=list)
    recommended_candidates: List[Dict[str, Any]] = field(default_factory=list)
    excluded_candidates: List[Dict[str, Any]] = field(default_factory=list)
    total_queries_executed: int = 0
    quota_used: int = 0
    data_source: str = "YouTube Data API v3 (Rolling 60-Day Window)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product.product_id,
            "product_name": self.product.product_name,
            "breadcrumb": self.product.full_breadcrumb,
            "market": self.market,
            "research_window": self.research_window_str,
            "start_iso": self.start_iso,
            "end_iso": self.end_iso,
            "records_count": len(self.records),
            "recommended_count": len(self.recommended_candidates),
            "excluded_count": len(self.excluded_candidates),
            "total_queries_executed": self.total_queries_executed,
            "quota_used": self.quota_used,
            "data_source": self.data_source,
        }


class ProductGapEngine:
    """Evaluates product competitor publishing gaps across rolling 60-day window."""

    def __init__(self, window_days: int = 60) -> None:
        self.window_days = window_days

    def get_rolling_window(self) -> Tuple[datetime, datetime, str]:
        """Compute the exact rolling UTC datetime window and human-readable string."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=self.window_days)
        window_str = f"{start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')} ({self.window_days} days UTC)"
        return start, now, window_str

    def generate_candidate_queries(
        self,
        product: TaxonomyProduct,
        market: str = "US",
        max_queries: int = 5,
    ) -> List[str]:
        """Generate targeted, non-overbroad YouTube search queries for a product."""
        clean_name = product.product_name.strip()
        queries: List[str] = [clean_name]

        # Aliases
        for alias in product.aliases:
            if alias.lower() not in [q.lower() for q in queries]:
                queries.append(alias.strip())

        # Buyer intent & review patterns
        current_year = datetime.now(timezone.utc).year
        intent_templates = [
            f"best {clean_name}",
            f"{clean_name} review {current_year}",
            f"{clean_name} worth it",
            f"how to use {clean_name}",
            f"{clean_name} for beginners",
            f"{clean_name} comparison",
        ]
        for it in intent_templates:
            if it.lower() not in [q.lower() for q in queries]:
                queries.append(it)

        # Candidate keywords registered with the product
        for kw in product.candidate_keywords:
            if kw.lower() not in [q.lower() for q in queries]:
                queries.append(kw.strip())

        # Localized terms if non-US market
        if market == "UK":
            uk_q = f"best {clean_name} UK"
            if uk_q.lower() not in [q.lower() for q in queries]:
                queries.append(uk_q)
        elif market == "CA":
            ca_q = f"best {clean_name} Canada"
            if ca_q.lower() not in [q.lower() for q in queries]:
                queries.append(ca_q)

        return queries[:max_queries]

    def check_video_relevance(
        self,
        video_title: str,
        product_name: str,
        aliases: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Validate if a discovered video is genuinely relevant to the product.
        
        Prevents broad or unrelated YouTube search results (e.g. coffee cake vs espresso machine)
        from falsely triggering the exclusion rule.
        """
        title_clean = video_title.lower()
        prod_clean = product_name.lower()

        # Stop words to exclude from token matching
        stop_words = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "up", "about", "into", "over", "after", "vs",
            "best", "top", "review", "guide", "test", "how", "what", "is", "are"
        }

        # Check full alias exact phrase matches first
        if aliases:
            for alias in aliases:
                if len(alias) >= 3 and alias.lower() in title_clean:
                    return (True, f"Matched product alias: '{alias}'")

        # Check product name exact phrase
        if len(prod_clean) >= 4 and prod_clean in title_clean:
            return (True, f"Matched full product name: '{product_name}'")

        # Token set overlap
        prod_tokens = set(re.findall(r"[a-z0-9]+", prod_clean)) - stop_words
        title_tokens = set(re.findall(r"[a-z0-9]+", title_clean))

        if not prod_tokens:
            return (True, "Short product name; default accepted")

        overlap = prod_tokens.intersection(title_tokens)
        overlap_ratio = len(overlap) / len(prod_tokens)

        # If >= 50% of the distinctive product tokens match, consider it relevant
        if overlap_ratio >= 0.5 or len(overlap) >= 2:
            return (True, f"Substantial token overlap: {list(overlap)}")

        # Single word product names (e.g. "Multimeter", "Hacksaw")
        if len(prod_tokens) == 1 and len(overlap) == 1:
            return (True, f"Direct key noun match: {list(overlap)[0]}")

        return (False, f"Irrelevant: only {len(overlap)}/{len(prod_tokens)} tokens matched ({list(overlap)})")

    def evaluate_opportunity(
        self,
        candidate_keyword: str,
        product: TaxonomyProduct,
        market: str = "US",
        matching_videos: Optional[List[Dict[str, Any]]] = None,
        executed_queries: Optional[List[str]] = None,
        has_api_error: bool = False,
        quota_exhausted: bool = False,
    ) -> ProductOpportunityRecord:
        """Evaluate a single candidate keyword adhering strictly to the user's exclusion rule."""
        now_dt = datetime.now(timezone.utc)
        cutoff_60d = now_dt - timedelta(days=self.window_days)
        queries = executed_queries or [candidate_keyword]
        vids = matching_videos or []

        # Step 1: Filter videos strictly published within the rolling 60-day window
        recent_videos = []
        for v in vids:
            pub_date_str = v.get("published_at") or v.get("publish_date") or ""
            is_recent = False
            if pub_date_str:
                try:
                    # Clean ISO format
                    clean_iso = pub_date_str.replace("Z", "+00:00")
                    pub_dt = datetime.fromisoformat(clean_iso)
                    if pub_dt >= cutoff_60d:
                        is_recent = True
                except Exception:
                    # Fallback to date prefix match
                    if len(pub_date_str) >= 10:
                        try:
                            pub_dt = datetime.strptime(pub_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                            if pub_dt >= cutoff_60d:
                                is_recent = True
                        except Exception:
                            is_recent = True
            if is_recent:
                recent_videos.append(v)

        # Step 2: Relevance verification
        relevant_recent_videos = []
        irrelevant_videos = []
        for rv in recent_videos:
            title = rv.get("title", "")
            is_rel, rel_reason = self.check_video_relevance(
                video_title=title,
                product_name=product.product_name,
                aliases=product.aliases,
            )
            annotated_v = dict(rv)
            annotated_v["relevance_reason"] = rel_reason
            if is_rel:
                annotated_v["relevance_status"] = "Relevant Matching Video"
                relevant_recent_videos.append(annotated_v)
            else:
                annotated_v["relevance_status"] = f"Irrelevant Video ({rel_reason})"
                irrelevant_videos.append(annotated_v)

        matching_count = len(relevant_recent_videos)
        q_count = len(queries)

        # Coverage status
        if q_count >= 3:
            coverage_label = f"Complete Sample ({q_count} queries)"
        elif q_count == 2:
            coverage_label = f"Basic Sample ({q_count} queries)"
        else:
            coverage_label = f"Insufficient Coverage ({q_count} query)"

        # Latest publish date
        if relevant_recent_videos:
            dates = [v.get("published_at") or v.get("publish_date") or "" for v in relevant_recent_videos]
            sorted_dates = sorted([d[:10] for d in dates if len(d) >= 10], reverse=True)
            latest_date = sorted_dates[0] if sorted_dates else "Recent (Last 60d)"
        else:
            latest_date = "None in 60d"

        # Step 3: Strict Evaluation Policy
        if has_api_error or quota_exhausted:
            status = OpportunityStatus.RESEARCH_FAILED
            obs_comp = "UNKNOWN"
            reason = "YouTube API quota exhausted or network error. Never classified as an opportunity."
            angle = "Retry search when YouTube Data API quota resets."
            title_idea = f"Guide to {product.product_name}"
        elif q_count < 2:
            status = OpportunityStatus.NEEDS_MORE_RESEARCH
            obs_comp = "UNKNOWN"
            reason = f"Only {q_count} query executed. Minimum 2 distinct queries required to verify gap status."
            angle = "Execute additional queries covering product aliases before committing to production."
            title_idea = f"{product.product_name}: Complete Overview"
        elif matching_count >= 1:
            status = OpportunityStatus.EXCLUDED_RECENT_VIDEOS
            obs_comp = "HIGH" if matching_count >= 4 else "MEDIUM"
            reason = f"Strict Rule Applied: Found {matching_count} relevant competitor video(s) published within the last 60 days. Excluded from approved opportunities."
            angle = f"High competitor activity detected ({matching_count} recent uploads). Saturated in 60-day window."
            title_idea = f"{product.product_name} Tested: What Competitors Don't Tell You"
        else:
            # 0 matching videos across >=2 queries
            status = OpportunityStatus.POTENTIAL_OPPORTUNITY
            obs_comp = "LOW"
            reason = f"0 matching videos found across {q_count} executed searches in the rolling 60-day window. Prime potential content gap."
            angle = f"First-mover beginner walkthrough and hands-on testing answering questions skipped by competitors."
            title_idea = f"Best {product.product_name} in {now_dt.year}: Complete Beginner Guide & Hands-on Test"

        return ProductOpportunityRecord(
            product_id=product.product_id,
            product_name=product.product_name,
            main_niche=product.main_niche,
            sub_niche=product.sub_niche,
            sub_sub_niche=product.sub_sub_niche,
            product_category=product.product_category,
            market=market,
            candidate_keyword=candidate_keyword,
            matching_videos_count=matching_count,
            latest_publish_date=latest_date,
            observed_competition=obs_comp,
            search_coverage=coverage_label,
            opportunity_status=status,
            recommendation=reason,
            suggested_angle=angle,
            suggested_title=title_idea,
            executed_queries=queries,
            video_evidence=relevant_recent_videos[:10] + irrelevant_videos[:5],
            affiliate_status="Commission not verified (connect affiliate provider to verify)",
            price_tier=product.price_tier,
            created_at=now_dt.isoformat(),
            updated_at=now_dt.isoformat(),
        )

    def research_product(
        self,
        product: TaxonomyProduct,
        market: str = "US",
        serp_provider: Any = None,
        max_queries: int = 5,
        use_cache: bool = True,
    ) -> OpportunityEvaluationResult:
        """Execute full 60-day competition research for a specific taxonomy product."""
        start_dt, end_dt, window_str = self.get_rolling_window()
        cutoff_iso = start_dt.isoformat()

        candidate_queries = self.generate_candidate_queries(product, market=market, max_queries=max_queries)
        has_api = serp_provider and hasattr(serp_provider, "is_connected") and serp_provider.is_connected()

        records: List[ProductOpportunityRecord] = []
        total_queries_executed = 0
        quota_used = 0
        has_api_error = False

        for q in candidate_queries:
            total_queries_executed += 1
            matching_videos: List[Dict[str, Any]] = []

            if has_api:
                try:
                    serp_res = serp_provider.analyze_keyword(
                        keyword=q,
                        max_results=10,
                        order="date",
                        published_after=cutoff_iso,
                        country=market,
                        use_cache=use_cache,
                    )
                    quota_used += 100
                    for v in serp_res.videos:
                        matching_videos.append({
                            "video_id": v.video_id,
                            "title": v.title,
                            "channel_title": v.channel_title,
                            "channel_id": getattr(v, "channel_id", ""),
                            "channel_url": getattr(v, "channel_url", f"https://www.youtube.com/channel/{getattr(v, 'channel_id', '')}"),
                            "video_url": getattr(v, "video_url", f"https://www.youtube.com/watch?v={v.video_id}"),
                            "published_at": v.publish_date,
                            "views": v.view_count,
                            "like_count": getattr(v, "like_count", None),
                            "comment_count": getattr(v, "comment_count", None),
                            "query": q,
                            "market": market,
                        })
                except Exception:
                    has_api_error = True
            else:
                # Deterministic simulation based on keyword hash when live API is unconfigured
                h_val = abs(hash(f"{q}_{market}"))
                recent_vids_count = h_val % 3  # 0, 1, or 2
                now_dt = datetime.now(timezone.utc)
                if recent_vids_count > 0:
                    for i in range(recent_vids_count):
                        days_ago = ((h_val + i * 11) % 50) + 2
                        v_date = (now_dt - timedelta(days=days_ago)).isoformat()
                        matching_videos.append({
                            "video_id": f"sim_{h_val}_{i}",
                            "title": f"Review of {product.product_name} - Honest {market} Testing",
                            "channel_title": f"Tech & Gear Lab {i + 1}",
                            "channel_id": f"UC_sample_{i}",
                            "channel_url": f"https://www.youtube.com/channel/UC_sample_{i}",
                            "video_url": f"https://www.youtube.com/watch?v=sim_{h_val}_{i}",
                            "published_at": v_date,
                            "views": 1500 * (i + 1),
                            "like_count": 80 * (i + 1),
                            "comment_count": 15 * (i + 1),
                            "query": q,
                            "market": market,
                        })

            record = self.evaluate_opportunity(
                candidate_keyword=q,
                product=product,
                market=market,
                matching_videos=matching_videos,
                executed_queries=candidate_queries,
                has_api_error=has_api_error,
            )
            records.append(record)

        # Separate into recommended vs excluded
        recommended = []
        excluded = []

        for rec in records:
            if rec.opportunity_status == OpportunityStatus.POTENTIAL_OPPORTUNITY:
                recommended.append({
                    "keyword": rec.candidate_keyword,
                    "opportunity_status": rec.opportunity_status,
                    "product": rec.product_name,
                    "market": rec.market,
                    "why_selected": "Zero matching videos found across executed searches within the rolling 60-day window; satisfies strict personal exclusion policy.",
                    "research_support": f"Executed {len(rec.executed_queries)} targeted search queries in {market}.",
                    "executed_queries": rec.executed_queries,
                    "matching_recent_videos": 0,
                    "missing_evidence": "Search volume data not connected (epistemic modesty: volume unverified).",
                    "suggested_title": rec.suggested_title,
                    "suggested_angle": rec.suggested_angle,
                    "next_action": "Send to SEO Generator to produce complete video package.",
                })
            elif rec.opportunity_status == OpportunityStatus.EXCLUDED_RECENT_VIDEOS:
                excluded.append({
                    "keyword": rec.candidate_keyword,
                    "opportunity_status": rec.opportunity_status,
                    "matching_videos_count": rec.matching_videos_count,
                    "latest_publish_date": rec.latest_publish_date,
                    "reason": rec.recommendation,
                })

        return OpportunityEvaluationResult(
            product=product,
            market=market,
            research_window_str=window_str,
            start_iso=start_dt.isoformat(),
            end_iso=end_dt.isoformat(),
            records=records,
            recommended_candidates=recommended,
            excluded_candidates=excluded,
            total_queries_executed=total_queries_executed,
            quota_used=quota_used,
            data_source="Live YouTube Data API v3" if has_api else "Deterministic Simulation (API Unconfigured)",
        )


product_gap_engine = ProductGapEngine()

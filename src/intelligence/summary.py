"""Research Session Summary Generator.

Computes precise, audit-grade session telemetry from actual session data:
- Queries attempted, succeeded, failed.
- Live autocomplete vs cached autocomplete vs generated results.
- Unique keyword count and topic cluster count.
- Collection start, end, and elapsed times.
- Clear status determination (Completed, Cancelled, Partially Failed).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from src.crawler.models import DiscoveredKeyword, StopReason


@dataclass
class ResearchSummary:
    """Audit-grade summary of a keyword research session."""

    seed_keyword: str
    queries_attempted: int
    queries_successful: int
    queries_failed: int
    live_autocomplete_count: int
    cached_autocomplete_count: int
    generated_keyword_count: int
    total_unique_keywords: int
    clusters_created: int
    start_time: str
    end_time: str
    status: str  # "Completed", "Cancelled", "Partially Failed", "Target Reached"
    stop_reason: Optional[str] = None
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_session_data(
        cls,
        seed_keyword: str,
        keywords: List[Any],
        query_logs: Optional[List[Any]] = None,
        stop_reason: Optional[Union[StopReason, str]] = None,
        start_time_iso: Optional[str] = None,
        end_time_iso: Optional[str] = None,
        elapsed_seconds: float = 0.0,
        cluster_count: int = 0,
    ) -> "ResearchSummary":
        """Compute summary strictly from actual discovered keywords and query logs."""
        now_iso = datetime.now(timezone.utc).isoformat()
        start = start_time_iso or now_iso
        end = end_time_iso or now_iso

        queries_attempted = 0
        queries_successful = 0
        queries_failed = 0

        if query_logs:
            queries_attempted = len(query_logs)
            for log in query_logs:
                st = getattr(log, "status", None) or (log.get("status") if isinstance(log, dict) else "")
                if st in ("success", "cached"):
                    queries_successful += 1
                elif st in ("failed", "cancelled"):
                    queries_failed += 1
        else:
            # Infer from unique parent queries if logs not available
            all_parents = set()
            for k in keywords:
                parents = getattr(k, "parent_queries", None) or (k.get("parent_queries") if isinstance(k, dict) else [])
                for p in parents:
                    all_parents.add(p)
            queries_attempted = len(all_parents) or 1
            queries_successful = queries_attempted

        live_count = 0
        cached_count = 0
        generated_count = 0

        for k in keywords:
            # Inspect provenance
            strict_source = getattr(k, "strict_source_label", None) or (
                getattr(k, "strict_source_type", None) or (
                    k.get("strict_source_type") if isinstance(k, dict) else None
                )
            )
            is_gen = getattr(k, "is_generated", False) or (k.get("is_generated", False) if isinstance(k, dict) else False)
            is_cac = getattr(k, "is_cached", False) or (k.get("is_cached", False) if isinstance(k, dict) else False)
            src_val = getattr(k, "source", None)
            if hasattr(src_val, "value"):
                src_val = src_val.value
            src_type = str(getattr(k, "source_type", None) or src_val or (k.get("source_type", "") if isinstance(k, dict) else ""))

            if (
                strict_source == "GENERATED_PATTERN"
                or is_gen
                or "generated" in src_type.lower()
                or "pattern" in src_type.lower()
            ):
                generated_count += 1
            elif (
                strict_source == "CACHED_AUTOCOMPLETE"
                or is_cac
                or "cached" in src_type.lower()
            ):
                cached_count += 1
            else:
                live_count += 1

        total_unique = len(keywords)

        # Status determination
        stop_str = str(stop_reason.value if hasattr(stop_reason, "value") else (stop_reason or "Completed"))
        if "cancel" in stop_str.lower():
            status = "Cancelled"
        elif "provider failure" in stop_str.lower() or "error" in stop_str.lower():
            status = "Partially Failed"
        elif "target" in stop_str.lower():
            status = "Target Reached"
        else:
            status = "Completed"

        return cls(
            seed_keyword=seed_keyword,
            queries_attempted=queries_attempted,
            queries_successful=queries_successful,
            queries_failed=queries_failed,
            live_autocomplete_count=live_count,
            cached_autocomplete_count=cached_count,
            generated_keyword_count=generated_count,
            total_unique_keywords=total_unique,
            clusters_created=cluster_count,
            start_time=start,
            end_time=end,
            status=status,
            stop_reason=stop_str,
            elapsed_seconds=round(elapsed_seconds, 2),
        )

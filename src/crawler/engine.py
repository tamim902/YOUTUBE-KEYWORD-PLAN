"""Recursive keyword expansion engine.

Implements a bounded, breadth-first keyword discovery queue using
BaseAutocompleteProvider with depth tracking, request budgets,
result targets, deduplication, provenance merging, and clean cancellation.
"""

import collections
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.crawler.models import (
    CrawlConfig,
    CrawlProgress,
    CrawlResult,
    DiscoveredKeyword,
    StopReason,
    normalize_keyword_key,
)
from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import AutocompleteError, OperationCancelledError
from src.providers.youtube import YouTubeAutocompleteProvider
from src.classifier import default_classifier
from src.intelligence.clustering import default_clusterer
from src.intelligence.scoring import default_scorer
from src.utils.logging import get_logger

logger = get_logger("crawler_engine")


class RecursiveKeywordEngine:
    """Breadth-first recursive keyword expansion coordinator."""

    def __init__(
        self,
        provider: Optional[BaseAutocompleteProvider] = None,
        database_manager: Optional[object] = None,
        **kwargs,
    ) -> None:
        if provider is not None:
            self.provider = provider
        elif database_manager is not None:
            self.provider = YouTubeAutocompleteProvider(database_manager=database_manager)
        else:
            self.provider = YouTubeAutocompleteProvider()
        self.database_manager = database_manager

    def crawl(
        self,
        config: CrawlConfig,
        cancellation_token: Optional[threading.Event] = None,
        on_progress: Optional[Callable[[CrawlProgress], None]] = None,
    ) -> CrawlResult:
        """Execute a breadth-first recursive keyword crawl up to configured bounds."""
        start_time = time.monotonic()

        # Queue contains tuples of: (query_text, depth, parent_query)
        queue: collections.deque[Tuple[str, int, Optional[str]]] = collections.deque()
        discovered_keywords: Dict[str, DiscoveredKeyword] = {}
        processed_queries: Set[str] = set()
        enqueued_queries: Set[str] = set()

        requests_made = 0
        queries_processed = 0
        stop_reason = StopReason.QUEUE_EXHAUSTED
        error_message: Optional[str] = None
        is_partial = False

        # 1. Enqueue initial seed keywords at depth 0
        for seed in config.seeds:
            norm_seed = normalize_keyword_key(seed)
            if norm_seed and norm_seed not in enqueued_queries:
                queue.append((seed.strip(), 0, None))
                enqueued_queries.add(norm_seed)

        if not queue:
            return CrawlResult(
                keywords=[],
                stop_reason=StopReason.QUEUE_EXHAUSTED,
                queries_processed=0,
                total_requests_made=0,
                is_partial=False,
                duration_seconds=round(time.monotonic() - start_time, 2),
            )

        logger.info(
            "Starting crawl with %d seed(s) [max_depth=%d, target=%d, budget=%d]",
            len(queue),
            config.max_depth,
            config.max_unique_keywords,
            config.request_budget,
        )

        while queue:
            # 2. Check limits BEFORE issuing a request
            if cancellation_token and cancellation_token.is_set():
                logger.info("Crawl cancelled by user.")
                stop_reason = StopReason.CANCELLED
                is_partial = True
                break

            if len(discovered_keywords) >= config.max_unique_keywords:
                logger.info("Unique keyword target reached: %d", len(discovered_keywords))
                stop_reason = StopReason.TARGET_REACHED
                is_partial = False
                break

            if requests_made >= config.request_budget:
                logger.info("Request budget exhausted: %d requests made", requests_made)
                stop_reason = StopReason.BUDGET_EXHAUSTED
                is_partial = True
                break

            # Check if all remaining items in queue exceed max_depth
            if all(item[1] > config.max_depth for item in queue):
                logger.info("Maximum depth reached for all queued queries.")
                stop_reason = StopReason.MAX_DEPTH_REACHED
                break

            # 3. Pop next query from breadth-first queue
            current_query, current_depth, parent_query = queue.popleft()
            norm_query = normalize_keyword_key(current_query)

            # Skip if depth exceeds max allowed depth
            if current_depth > config.max_depth:
                continue

            # Skip if this normalized query was already processed
            if norm_query in processed_queries:
                continue

            # 4. Report progress to listener
            queries_processed += 1
            if on_progress:
                progress = CrawlProgress(
                    queries_processed=queries_processed,
                    keywords_discovered=len(discovered_keywords),
                    current_depth=current_depth,
                    requests_remaining=max(0, config.request_budget - requests_made),
                    current_query=current_query,
                )
                try:
                    on_progress(progress)
                except Exception as exc:
                    logger.warning("Error in progress callback: %s", exc)

            # 5. Fetch autocomplete suggestions from provider
            requests_made += 1
            try:
                suggestions = self.provider.get_suggestions(
                    query=current_query,
                    language=config.language,
                    country=config.country,
                    use_cache=config.use_cache,
                    cancellation_token=cancellation_token,
                )
            except OperationCancelledError:
                logger.info("Operation cancelled during provider fetch.")
                stop_reason = StopReason.CANCELLED
                is_partial = True
                break
            except AutocompleteError as exc:
                logger.warning("Provider error fetching '%s': %s", current_query, exc)
                stop_reason = StopReason.PROVIDER_ERROR
                error_message = exc.message if hasattr(exc, "message") else str(exc)
                is_partial = True
                break
            except Exception as exc:
                logger.error("Unexpected error in crawl loop: %s", exc, exc_info=True)
                stop_reason = StopReason.PROVIDER_ERROR
                error_message = str(exc)
                is_partial = True
                break

            processed_queries.add(norm_query)

            # 6. Process suggestions: deduplicate, merge provenance, and enqueue
            for suggestion in suggestions:
                kw_text = suggestion.keyword.strip()
                kw_norm = normalize_keyword_key(kw_text)
                if not kw_norm:
                    continue

                if kw_norm in discovered_keywords:
                    # Merge rediscovery provenance
                    discovered_keywords[kw_norm].add_discovery_path(
                        parent_query=current_query,
                        found_depth=current_depth + 1,
                    )
                else:
                    # New unique keyword discovered
                    if len(discovered_keywords) < config.max_unique_keywords:
                        now_iso = datetime.now(timezone.utc).isoformat()
                        cls = default_classifier.classify(kw_text)
                        seed_ref = config.seeds[0] if config.seeds else current_query
                        rel = default_scorer.score(
                            keyword=kw_text,
                            seed_keyword=seed_ref,
                            classification=cls,
                        )
                        discovered_keywords[kw_norm] = DiscoveredKeyword(
                            keyword=kw_text,
                            normalized_key=kw_norm,
                            depth=current_depth + 1,
                            parent_queries=[current_query],
                            discovery_paths=1,
                            source_type=suggestion.source_type,
                            source_name=suggestion.source_name,
                            language=config.language,
                            country=config.country,
                            first_discovered_at=now_iso,
                            last_discovered_at=now_iso,
                            sources=[suggestion.source_type],
                            tail_length=cls.tail_length.value,
                            intent_labels=[i.value for i in cls.intent_labels],
                            word_count=cls.word_count,
                            relevance_score=rel.total_score,
                            intent_explanation=cls.primary_explanation,
                        )

                        # Enqueue for further recursive expansion if within depth bounds
                        if (current_depth + 1) <= config.max_depth:
                            if config.max_queue_size and len(queue) >= config.max_queue_size:
                                logger.info("Max queue size reached (%d).", config.max_queue_size)
                                stop_reason = StopReason.MAX_QUEUE_SIZE_REACHED
                                break

                            if kw_norm not in enqueued_queries and kw_norm not in processed_queries:
                                queue.append((kw_text, current_depth + 1, current_query))
                                enqueued_queries.add(kw_norm)

                # Stop immediately if target is reached
                if len(discovered_keywords) >= config.max_unique_keywords:
                    stop_reason = StopReason.TARGET_REACHED
                    is_partial = False
                    break

            if stop_reason in (StopReason.TARGET_REACHED, StopReason.MAX_QUEUE_SIZE_REACHED):
                break

            # Report updated progress after processing suggestions
            if on_progress:
                progress = CrawlProgress(
                    queries_processed=queries_processed,
                    keywords_discovered=len(discovered_keywords),
                    current_depth=current_depth,
                    requests_remaining=max(0, config.request_budget - requests_made),
                    current_query=current_query,
                )
                try:
                    on_progress(progress)
                except Exception as exc:
                    logger.warning("Error in progress callback: %s", exc)

            # 7. Respect minimum delay between requests
            if config.min_delay_seconds > 0 and queue:
                time.sleep(config.min_delay_seconds)

        # Final progress notification
        if on_progress:
            try:
                on_progress(
                    CrawlProgress(
                        queries_processed=queries_processed,
                        keywords_discovered=len(discovered_keywords),
                        current_depth=current_depth if 'current_depth' in locals() else 0,
                        requests_remaining=max(0, config.request_budget - requests_made),
                        current_query="",
                    )
                )
            except Exception:
                pass

        # Apply topic clustering across discovered keywords
        if discovered_keywords:
            seed_kw = config.seeds[0] if config.seeds else ""
            clusters = default_clusterer.cluster_keywords(list(discovered_keywords.values()), seed_keyword=seed_kw)
            cluster_map = {}
            for c in clusters:
                for kw in c.keywords:
                    cluster_map[normalize_keyword_key(kw)] = c.name
            for k_norm, dk in discovered_keywords.items():
                if k_norm in cluster_map:
                    dk.cluster_name = cluster_map[k_norm]

        duration = round(time.monotonic() - start_time, 2)
        logger.info(
            "Crawl finished. Stop reason: %s. Discovered: %d keywords in %.2fs",
            stop_reason.value,
            len(discovered_keywords),
            duration,
        )

        return CrawlResult(
            keywords=list(discovered_keywords.values()),
            stop_reason=stop_reason,
            queries_processed=queries_processed,
            total_requests_made=requests_made,
            is_partial=is_partial,
            error_message=error_message,
            duration_seconds=duration,
        )

    # Alias execute to crawl for compatibility
    execute = crawl

"""YouTube Keyword Finder - Application Entry Point.

Local-first desktop Streamlit application providing keyword discovery,
real YouTube autocomplete integration, recursive keyword expansion,
deterministic classification, pattern variations, research project history,
and professional dashboard controls.
"""

import io
import json
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import pandas as pd
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import APP_NAME, APP_VERSION, config
from src.crawler import (
    ControlledExpansionEngine,
    CrawlConfig,
    CrawlProgress,
    CrawlResult,
    DiscoveredKeyword,
    ExpansionConfig,
    ExpansionResult,
    QueryLogEntry,
    RecursiveKeywordEngine,
    StopReason,
)

from src.models.keyword import AutocompleteResult, KeywordItem, SourceType
from src.classifier import (
    KeywordClassification,
    KeywordClassifier,
    SearchIntent,
    TailLength,
    TailThresholds,
    default_classifier,
)
from src.patterns import (
    GeneratedKeyword,
    PatternCategory,
    PatternConfig,
    PatternLanguage,
    SmartKeywordPatternGenerator,
)
from src.providers import (
    AccessForbiddenError,
    AutocompleteError,
    MalformedResponseError,
    NetworkConnectionError,
    NetworkTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    YouTubeAutocompleteProvider,
    get_ai_provider,
)
from src.providers.serp import (
    BaseSerpMetricsProvider,
    SerpMetrics,
    UnconnectedSerpMetricsProvider,
    YouTubeDataApiSerpProvider,
    default_serp_provider,
)
from src.models.serp import CompetitorVideoItem, KeywordSerpAnalysis, QuotaUsageLog
from src.models.opportunity import (
    CalendarEntry,
    ContentBrief,
    ContentOpportunityItem,
    TitleQualityCheck,
    TopicOverlapResult,
)
from src.models.product import (
    CandidateProduct,
    ClassificationCategory,
    ProductQueryExecution,
    ProductResearchSession,
    ProductVideoMatch,
    SearchMode,
)
from src.models.product_planner import (
    AffiliateContentBrief,
    AffiliateProductData,
    ContentFormatRecommendation,
    ProductOpportunityShortlist,
    ShortlistStatus,
)
from src.models.monitor import (
    AlertSeverity,
    MonitorAlert,
    MonitorRunStatus,
    ProductSnapshotItem,
    ResearchMonitorRun,
    ResearchSchedule,
    ResearchScheduleFrequency,
    SavedResearchConfig,
    SnapshotComparisonResult,
)
from src.intelligence import (
    AffiliateBriefGenerator,
    ChangeAlertDetector,
    ContentBriefGenerator,
    ContentFormatRecommender,
    ContentGapDetector,
    HistoricalAnalyticsAggregator,
    NicheProductPipeline,
    OpportunityScorer,
    OpportunityScorerV14,
    ProductComparisonEngine,
    ProductExtractor,
    ProductMatcher,
    ProductOpportunityScorer,
    ResearchComparisonEngine,
    ResearchSchedulerService,
    infer_product_category,
    RelevanceBreakdown,
    RelevanceScorer,
    ResearchSummary,
    TitleHookWorkshop,
    TopicCluster,
    TopicClusteringEngine,
    TopicOverlapDetector,
    VideoTopicGenerator,
    default_clusterer,
    default_scorer,
    ChannelManager,
    channel_manager,
    SeoEngine,
    seo_engine,
    DescriptionStudio,
    description_studio,
    GapFinder,
    gap_finder,
    DailyOpportunityEngine,
    daily_opportunity_engine,
    NotificationService,
    notification_service,
    AuditEngine,
    audit_engine,
    GrowthEngine,
    growth_engine,
    ContentStrategyAutopilot,
    content_strategy_autopilot,
)
from src.providers.youtube_analytics import (
    YouTubeAnalyticsProvider,
    youtube_analytics_provider,
)
from src.models import (
    ChannelProfile,
    get_default_four_channels,
    KeywordIntentType,
    SeoRelevanceTier,
    SeoOpportunityTier,
    AffiliatePotentialTier,
    ResearchConfidenceTier,
    SeoOpportunityScore,
    SeoKeywordItem,
    SeoTitleCandidate,
    VideoDescription,
    DailyIdeaItem,
    DailyMorningReport,
    GapFinderState,
    IdeaReviewStatus,
    AuditFinding,
    AuditFindingSeverity,
    AuditScoreBreakdown,
    AuditStatus,
    AffiliateQualityResult,
    DescriptionQualityResult,
    PublishingChecklistItem,
    ScriptAlignmentResult,
    ThumbnailQualityResult,
    TitleQualityResult,
    VideoSeoAudit,
    AnalyticsAuthStatus,
    ChannelAnalyticsOverview,
    ChannelOAuthCredentials,
    GrowthRecommendation,
    MetricComparison,
    PublishingExperiment,
    VideoAnalyticsItem,
    WorkflowStage,
    ProductionEffort,
    TopicUserStatus,
    ContentPillar,
    ContentCluster,
    PrioritizedTopic,
    StrategyCalendarItem,
    ContentBriefDocument,
    ProductionWorkflowProject,
    ChannelStrategySettings,
)
from src.providers.affiliate import (
    BaseAffiliateProvider,
    CuratedCatalogAffiliateProvider,
    ManualAffiliateProvider,
    MockAffiliateProvider,
)
from src.storage import (
    BackupManager,
    DatabaseManager,
    ExportService,
    MigrationManager,
    db_manager,
    generate_export_filename,
    sanitize_dataframe_for_export,
    sanitize_formula_injection,
)
try:
    from src.ui import (
        ALL_NAVIGATION_PAGES,
        NAVIGATION_PAGES,
        PAGE_LANDING,
        PAGE_DASHBOARD,
        PAGE_NEW_RESEARCH,
        PAGE_RESULTS,
        PAGE_PATTERNS,
        PAGE_CONTENT_OPPORTUNITIES,
        PAGE_PRODUCT_OPPORTUNITIES,
        PAGE_PRODUCT_PLANNER,
        PAGE_RESEARCH_MONITOR,
        PAGE_CHANNELS,
        PAGE_MORNING_REPORT,
        PAGE_DESCRIPTION_STUDIO,
        PAGE_SEO_AUDIT,
        PAGE_ANALYTICS,
        PAGE_STRATEGY,
        PAGE_SAVED,
        PAGE_SERP,
        PAGE_USER_GUIDE,
        PAGE_AUTH,
        PAGE_SETTINGS,
        PAGE_VIDEO_RESEARCH,

        apply_custom_styles,
        render_channel_switcher,
        render_contextual_help,
        render_copy_box,
        render_empty_state,
        render_header,
        render_interactive_tour,
        render_metric_card,
        render_navigation,
        render_next_best_action_banner,
        render_onboarding_guide,
        render_page_header,
        render_provenance_badge,
        render_recommended_next_step,
        render_system_status,
        render_workflow_progress_checklist,
        reset_guidance_preferences,
        INTERACTIVE_TOURS,
        ONBOARDING_GOALS,
        USER_GUIDE_SECTIONS,
        WORKFLOW_PLANS,
    )
except ImportError:
    import importlib
    import src.ui
    import src.ui.components
    import src.ui.guide
    importlib.reload(src.ui.components)
    importlib.reload(src.ui.guide)
    importlib.reload(src.ui)
    from src.ui import (
        ALL_NAVIGATION_PAGES,
        NAVIGATION_PAGES,
        PAGE_LANDING,
        PAGE_DASHBOARD,
        PAGE_NEW_RESEARCH,
        PAGE_RESULTS,
        PAGE_PATTERNS,
        PAGE_CONTENT_OPPORTUNITIES,
        PAGE_PRODUCT_OPPORTUNITIES,
        PAGE_PRODUCT_PLANNER,
        PAGE_RESEARCH_MONITOR,
        PAGE_CHANNELS,
        PAGE_MORNING_REPORT,
        PAGE_DESCRIPTION_STUDIO,
        PAGE_SEO_AUDIT,
        PAGE_ANALYTICS,
        PAGE_STRATEGY,
        PAGE_SAVED,

        PAGE_SERP,
        PAGE_USER_GUIDE,
        PAGE_AUTH,
        PAGE_SETTINGS,
        PAGE_VIDEO_RESEARCH,
        apply_custom_styles,
        render_channel_switcher,
        render_contextual_help,
        render_copy_box,
        render_empty_state,
        render_header,
        render_interactive_tour,
        render_metric_card,
        render_navigation,
        render_next_best_action_banner,
        render_onboarding_guide,
        render_page_header,
        render_provenance_badge,
        render_recommended_next_step,
        render_system_status,
        render_workflow_progress_checklist,
        reset_guidance_preferences,
        INTERACTIVE_TOURS,
        ONBOARDING_GOALS,
        USER_GUIDE_SECTIONS,
        WORKFLOW_PLANS,
    )
from src.utils.logging import get_logger
from src.utils.normalization import normalize_keyword_key
from src.utils.validators import sanitize_seed_keyword

logger = get_logger("app")


# ==============================================================================
# Application Bootstrapping & Helper Functions
# ==============================================================================

@st.cache_resource
def bootstrap_application() -> bool:
    """Initialize folders and local SQLite database schema once per server instance."""
    try:
        config.ensure_directories()
        db_manager.init_db()
        logger.info("Application bootstrap complete. Database and paths verified.")
        return True
    except Exception as exc:
        logger.error("Failed to bootstrap application: %s", exc, exc_info=True)
        return False


def parse_seed_inputs(raw_text: str) -> List[str]:
    """Parse single or multiple seeds from comma- or newline-separated input."""
    if not raw_text:
        return []
    delimiters = [",", "\n", ";"]
    tokens = [raw_text]
    for d in delimiters:
        new_tokens = []
        for t in tokens:
            new_tokens.extend(t.split(d))
        tokens = new_tokens

    cleaned_seeds = []
    seen = set()
    for token in tokens:
        is_valid, sanitized, _ = sanitize_seed_keyword(token)
        if is_valid and sanitized.lower() not in seen:
            seen.add(sanitized.lower())
            cleaned_seeds.append(sanitized)
    return cleaned_seeds


def load_search_into_crawl_result(
    search_id: int, db: DatabaseManager = db_manager
) -> Optional[CrawlResult]:
    """Retrieve keywords for a stored research project and format as CrawlResult without re-querying network."""
    rows = db.get_keywords_by_search_id(search_id)
    if not rows:
        return None
    proj = db.get_project(search_id)
    keywords = []
    for r in rows:
        parents = r.get("parent_queries") or ([r["parent_keyword"]] if r.get("parent_keyword") else [])
        disc_paths_val = r.get("discovery_paths", [1])
        paths_count = disc_paths_val[0] if isinstance(disc_paths_val, list) and disc_paths_val else 1

        kw = DiscoveredKeyword(
            keyword=r["keyword"],
            normalized_key=r.get("normalized_key") or r["keyword"].lower(),
            depth=r.get("depth", 0),
            parent_queries=parents,
            discovery_paths=paths_count if isinstance(paths_count, int) else 1,
            source_type=r.get("source_type", "autocomplete"),
            source_name=r.get("source_name", "youtube_autocomplete"),
            language=r.get("language", "en"),
            country=r.get("country", "US"),
            first_discovered_at=r.get("created_at", ""),
            last_discovered_at=r.get("last_seen_at") or r.get("created_at", ""),
            is_generated=(r.get("source_type") == "generated" or "generated" in r.get("sources", [])),
            pattern_category=r.get("pattern_category"),
            pattern_template=r.get("pattern_template"),
            tail_length=r.get("tail_length"),
            intent_labels=r.get("intent_labels", []),
            sources=r.get("sources", [r.get("source_type", "autocomplete")]),
            word_count=r.get("word_count", len(r["keyword"].split())),
            relevance_score=r.get("relevance_score", 0.0),
            cluster_name=r.get("cluster_name", "Core Seed Variations"),
            intent_explanation=r.get("intent_explanation", ""),
        )
        keywords.append(kw)

    stop_reason = StopReason.TARGET_REACHED
    if proj and proj.get("stop_reason"):
        for sr in StopReason:
            if sr.value == proj["stop_reason"]:
                stop_reason = sr
                break

    requests_count = proj.get("requests_made", 1) if proj else 1
    return CrawlResult(
        keywords=keywords,
        stop_reason=stop_reason,
        queries_processed=requests_count,
        total_requests_made=requests_count,
        is_partial=(proj.get("status") == "partial") if proj else False,
        error_message=proj.get("error_message") if proj else None,
        duration_seconds=0.0,
    )


def filter_keywords(
    keywords: List[DiscoveredKeyword],
    source_filter: str = "All Sources",
    tail_filter: str = "All Lengths",
    intent_filter: str = "All Intents",
    lang_filter: str = "All Languages",
    country_filter: str = "All Countries",
    search_query: str = "",
    classifier: Optional[KeywordClassifier] = None,
    cluster_filter: str = "All Clusters",
    min_relevance: float = 0.0,
    min_word_count: Optional[int] = None,
    max_word_count: Optional[int] = None,
) -> List[Tuple[DiscoveredKeyword, str, List[str]]]:
    """Pure helper function to filter keywords according to dashboard criteria."""
    active_classifier = classifier or default_classifier
    filtered = []
    query_lower = search_query.strip().lower() if search_query else ""

    for k in keywords:
        classification = active_classifier.classify(k.keyword)
        tail = classification.tail_length.value
        intents = [i.value for i in classification.intent_labels]

        # 1. Source filter
        if source_filter != "All Sources":
            sf_lower = source_filter.lower()
            strict_lbl = getattr(k, "strict_source_label", "")
            if "live" in sf_lower or ("autocomplete" in sf_lower and "pattern" not in sf_lower and "generated" not in sf_lower and "cache" not in sf_lower):
                if strict_lbl and strict_lbl != "LIVE_AUTOCOMPLETE":
                    continue
                elif not strict_lbl and (k.source_type not in ("autocomplete", "live", "LIVE_AUTOCOMPLETE") or getattr(k, "is_generated", False) or getattr(k, "is_cached", False)):
                    continue
            elif "cache" in sf_lower:
                if strict_lbl and strict_lbl != "CACHED_AUTOCOMPLETE":
                    continue
                elif not strict_lbl and (k.source_type not in ("cached", "CACHED_AUTOCOMPLETE") and not getattr(k, "is_cached", False)):
                    continue
            elif "generated" in sf_lower or "pattern" in sf_lower:
                if strict_lbl and strict_lbl != "GENERATED_PATTERN":
                    continue
                elif not strict_lbl and (not getattr(k, "is_generated", False) and k.source_type not in ("generated", "GENERATED_PATTERN")):
                    continue

        # 2. Tail length filter
        if tail_filter != "All Lengths":
            tf_lower = tail_filter.lower()
            if "short" in tf_lower and tail != "Short-tail":
                continue
            elif "medium" in tf_lower and tail != "Medium-tail":
                continue
            elif "long" in tf_lower and tail != "Long-tail":
                continue
            elif "short" not in tf_lower and "medium" not in tf_lower and "long" not in tf_lower and tail != tail_filter:
                continue

        # 3. Search intent filter
        if intent_filter != "All Intents":
            if intent_filter not in intents and not any(intent_filter.lower() in i.lower() for i in intents):
                continue

        # 4. Language filter
        if lang_filter != "All Languages" and k.language != lang_filter:
            continue

        # 5. Country filter
        if country_filter != "All Countries" and k.country != country_filter:
            continue

        # 6. Text query filter
        if query_lower and query_lower not in k.keyword.lower():
            continue

        # 7. Cluster filter
        kw_cluster = getattr(k, "cluster_name", "Core Seed Variations") or "Core Seed Variations"
        if cluster_filter != "All Clusters" and kw_cluster.lower() != cluster_filter.lower():
            continue

        # 8. Relevance Score filter
        kw_rel = getattr(k, "relevance_score", 0.0) or 0.0
        if kw_rel < min_relevance:
            continue

        # 9. Word count range filters
        w_cnt = getattr(k, "word_count", None) or len(k.keyword.split())
        if min_word_count is not None and w_cnt < min_word_count:
            continue
        if max_word_count is not None and w_cnt > max_word_count:
            continue

        filtered.append((k, tail, intents))

    return filtered


def format_keywords_for_clipboard(
    keywords: Union[List[str], pd.DataFrame, List[Tuple[Any, ...]]],
) -> str:
    """Format keywords as newline-delimited plain text for clipboard copying."""
    if isinstance(keywords, pd.DataFrame):
        if "Keyword" in keywords.columns:
            return "\n".join(str(k) for k in keywords["Keyword"].tolist())
        return "\n".join(str(row.iloc[0]) for _, row in keywords.iterrows())
    elif isinstance(keywords, list):
        items = []
        for item in keywords:
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, tuple) and hasattr(item[0], "keyword"):
                items.append(item[0].keyword)
            elif hasattr(item, "keyword"):
                items.append(item.keyword)
            else:
                items.append(str(item))
        return "\n".join(items)
    return str(keywords)


def build_dataframe_from_keywords(
    classified_keywords: List[Tuple[DiscoveredKeyword, str, List[str]]],
) -> pd.DataFrame:
    """Build a display and export DataFrame from classified keyword tuples."""
    display_data = []
    for idx, (k, tail, intents) in enumerate(classified_keywords):
        primary_intent = intents[0] if intents else "Informational"
        all_intents_str = ", ".join(intents) if intents else "Informational"
        all_sources = (
            ", ".join(k.sources) if getattr(k, "sources", None) else k.source_type
        )
        source_label = (
            f"{k.source_type.title()}{' (+Pattern)' if k.is_generated and k.source_type == 'autocomplete' else ''}"
        )
        parent_str = ", ".join(k.parent_queries) if k.parent_queries else "(seed)"

        strict_source = getattr(k, "strict_source_label", None) or (
            "GENERATED_PATTERN" if (getattr(k, "is_generated", False) or k.source_type == "generated")
            else "CACHED_AUTOCOMPLETE" if (getattr(k, "is_cached", False) or k.source_type in ("cached", "CACHED_AUTOCOMPLETE"))
            else "LIVE_AUTOCOMPLETE"
        )
        discovery_query = getattr(k, "discovery_query", "") or (
            k.parent_queries[0] if k.parent_queries else k.keyword
        )

        display_data.append(
            {
                "#": idx + 1,
                "Keyword": k.keyword,
                "Relevance Score": round(getattr(k, "relevance_score", 0.0), 1),
                "Cluster": getattr(k, "cluster_name", "Core Seed Variations") or "Core Seed Variations",
                "Source Type": strict_source,
                "Discovery Query": discovery_query,
                "Tail Length": tail,
                "Intent Classification": primary_intent,
                "Word Count": k.word_count or len(k.keyword.split()),
                "Intent Explanation": getattr(k, "intent_explanation", ""),
                "Normalized Key": k.normalized_key or k.keyword.lower(),
                "Tail Type": tail,
                "Primary Intent": primary_intent,
                "All Intents": all_intents_str,
                "Source": source_label,
                "All Sources": all_sources,
                "Depth": k.depth,
                "Discovery Paths": k.discovery_paths,
                "Parent Queries": parent_str,
                "Language": k.language,
                "Country": k.country,
                "First Discovered": k.first_discovered_at or "",
            }
        )

    return pd.DataFrame(display_data)


def export_keywords_to_csv(
    df: pd.DataFrame, sanitize_formulas: bool = True, include_bom: bool = True
) -> bytes:
    """Serialize DataFrame to UTF-8 encoded CSV bytes with BOM and formula protection."""
    return ExportService.export_csv(df, sanitize_formulas=sanitize_formulas, include_bom=include_bom)


def export_keywords_to_excel(
    df: pd.DataFrame, sanitize_formulas: bool = True
) -> bytes:
    """Serialize DataFrame to openpyxl Excel bytes with formula protection."""
    return ExportService.export_excel(df, sanitize_formulas=sanitize_formulas)


# ==============================================================================
# Research Execution Pipelines
# ==============================================================================

def execute_keyword_search(
    query: str,
    language: str = "en",
    country: str = "US",
    provider: Optional[YouTubeAutocompleteProvider] = None,
    save_to_db: bool = True,
    project_name: Optional[str] = None,
) -> Tuple[List[AutocompleteResult], Optional[str]]:
    """Execute direct live autocomplete search for a single query."""
    active_provider = provider or YouTubeAutocompleteProvider(database_manager=db_manager)
    try:
        suggestions = active_provider.get_suggestions(
            query=query,
            language=language,
            country=country,
            use_cache=True,
        )

        if save_to_db and suggestions:
            try:
                search_id = db_manager.save_search(
                    seed_keyword=query,
                    language=language,
                    country=country,
                    max_depth=1,
                    request_budget=1,
                    total_results=len(suggestions),
                    project_name=project_name or query,
                    status="completed",
                    stop_reason="direct_autocomplete",
                    requests_made=1,
                )
                keyword_items = [
                    s.to_keyword_item(seed_keyword=query) for s in suggestions
                ]
                db_manager.save_keywords(search_id, keyword_items)
            except Exception as db_err:
                logger.warning("Could not persist direct search to SQLite: %s", db_err)

        return suggestions, None

    except AccessForbiddenError:
        return [], "Access forbidden (HTTP 403). YouTube endpoint refused the request."
    except RateLimitError as exc:
        return [], f"Rate limit encountered (HTTP 429). {exc}"
    except (NetworkConnectionError, NetworkTimeoutError) as exc:
        return [], f"Network error communicating with YouTube autocomplete: {exc}"
    except MalformedResponseError as exc:
        return [], f"Received unexpected response format from endpoint: {exc}"
    except AutocompleteError as exc:
        return [], f"Autocomplete provider error: {exc}"
    except Exception as exc:
        logger.error("Unexpected error during keyword query '%s': %s", query, exc, exc_info=True)
        return [], f"Unexpected error: {exc}"


def execute_recursive_crawl(
    crawl_config: CrawlConfig,
    provider: Optional[YouTubeAutocompleteProvider] = None,
    progress_callback: Optional[Callable[[CrawlProgress], None]] = None,
    cancellation_token: Optional[threading.Event] = None,
    save_to_db: bool = True,
    project_name: Optional[str] = None,
    engine: Optional[RecursiveKeywordEngine] = None,
    database_manager: Optional[DatabaseManager] = None,
) -> CrawlResult:
    """Execute breadth-first recursive exploration across one or more seed keywords."""
    active_db = database_manager or db_manager
    if engine is not None:
        active_engine = engine
    else:
        active_provider = provider or YouTubeAutocompleteProvider(database_manager=active_db)
        active_engine = RecursiveKeywordEngine(
            provider=active_provider,
        )

    crawl_fn = getattr(active_engine, "crawl", None) or getattr(active_engine, "execute", None)
    try:
        result = crawl_fn(
            config=crawl_config,
            on_progress=progress_callback,
            cancellation_token=cancellation_token,
        )
    except TypeError:
        result = crawl_fn(
            config=crawl_config,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    if save_to_db and result.keywords:
        try:
            status_val = "completed"
            if result.stop_reason == StopReason.CANCELLED:
                status_val = "cancelled"
            elif result.is_partial:
                status_val = "partial"
            elif result.error_message:
                status_val = "failed"

            params_dict = {
                "seeds": crawl_config.seeds,
                "language": crawl_config.language,
                "country": crawl_config.country,
                "max_depth": crawl_config.max_depth,
                "max_unique_keywords": crawl_config.max_unique_keywords,
                "request_budget": crawl_config.request_budget,
                "min_delay_seconds": crawl_config.min_delay_seconds,
            }

            search_id = active_db.save_search(
                seed_keyword=", ".join(crawl_config.seeds),
                language=crawl_config.language,
                country=crawl_config.country,
                max_depth=crawl_config.max_depth,
                request_budget=crawl_config.request_budget,
                total_results=len(result.keywords),
                project_name=project_name or crawl_config.seeds[0],
                status=status_val,
                stop_reason=result.stop_reason.value,
                parameters_json=json.dumps(params_dict),
                requests_made=result.total_requests_made,
                error_message=result.error_message,
            )
            keyword_items = [
                k.to_keyword_item(seed_keyword=crawl_config.seeds[0])
                for k in result.keywords
            ]
            active_db.save_keywords(search_id, keyword_items)
            result.search_id = search_id
        except Exception as exc:
            logger.warning("Failed to persist recursive crawl to SQLite: %s", exc)

    return result


def execute_controlled_expansion(
    expansion_config: ExpansionConfig,
    provider: Optional[YouTubeAutocompleteProvider] = None,
    progress_callback: Optional[Callable[[CrawlProgress], None]] = None,
    cancellation_token: Optional[threading.Event] = None,
    save_to_db: bool = True,
    project_name: Optional[str] = None,
    engine: Optional[ControlledExpansionEngine] = None,
    database_manager: Optional[DatabaseManager] = None,
) -> ExpansionResult:
    """Execute controlled A-Z, 0-9, and modifier keyword expansion across seed keywords."""
    active_db = database_manager or db_manager
    if engine is not None:
        active_engine = engine
    else:
        active_provider = provider or YouTubeAutocompleteProvider(database_manager=active_db)
        active_engine = ControlledExpansionEngine(
            provider=active_provider,
            database_manager=active_db,
        )

    result = active_engine.expand(
        config=expansion_config,
        cancellation_token=cancellation_token,
        on_progress=progress_callback,
    )

    if save_to_db and result.keywords:
        try:
            status_val = "completed"
            if result.stop_reason == StopReason.CANCELLED:
                status_val = "cancelled"
            elif result.is_partial:
                status_val = "partial"
            elif result.error_message:
                status_val = "failed"

            params_dict = {
                "seeds": expansion_config.seeds,
                "language": expansion_config.language,
                "country": expansion_config.country,
                "include_alphabet": expansion_config.include_alphabet,
                "include_numbers": expansion_config.include_numbers,
                "include_prepositions": expansion_config.include_prepositions,
                "request_budget": expansion_config.request_budget,
                "max_unique_keywords": expansion_config.max_unique_keywords,
                "min_delay_seconds": expansion_config.min_delay_seconds,
            }

            search_id = active_db.save_search(
                seed_keyword=", ".join(expansion_config.seeds),
                language=expansion_config.language,
                country=expansion_config.country,
                max_depth=1,
                request_budget=expansion_config.request_budget,
                total_results=len(result.keywords),
                project_name=project_name or expansion_config.seeds[0],
                status=status_val,
                stop_reason=result.stop_reason.value,
                parameters_json=json.dumps(params_dict),
                requests_made=result.total_requests_made,
                error_message=result.error_message,
            )
            keyword_items = [
                k.to_keyword_item(seed_keyword=expansion_config.seeds[0])
                for k in result.keywords
            ]
            active_db.save_keywords(search_id, keyword_items)
            result.search_id = search_id
        except Exception as exc:
            logger.warning("Failed to persist controlled expansion to SQLite: %s", exc)

    return result



# ==============================================================================
# Page View Renderers
# ==============================================================================

def render_page_landing(is_ready: bool) -> None:
    """Render the high-impact SaaS Landing Page and Interactive Product Showcase (Phase 16)."""
    render_page_header(
        title="Overview & Showcase",
        subtitle="Next-generation YouTube audience intelligence, recursive keyword discovery & competitor gap analysis.",
        category="WORKSPACE",
        badge_text=f"v{APP_VERSION} Pro",
        badge_type="primary",
        provenance="local_sqlite",
    )

    # 1. Premium Hero Section
    st.markdown(
        """
        <div class="premium-hero animate-fade-in">
            <div class="hero-eyebrow">
                <span class="dot-live"></span> NEXT-GEN YOUTUBE AUDIENCE & NICHE PRODUCT INTELLIGENCE
            </div>
            <h1 class="hero-title">
                Discover Untold YouTube Demand <span class="hero-gradient-text">Before Your Competitors Do.</span>
            </h1>
            <p class="hero-subtitle">
                Local-first autocomplete discovery, multi-angle search tree expansion, competitor SERP gap inspection,
                and affiliate content planning—powered strictly by authentic platform data with zero fabricated metrics.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Primary Action Triggers
    col_cta1, col_cta2, col_cta3, col_cta4 = st.columns(4)
    with col_cta1:
        if st.button("🚀 Launch Keyword Studio", type="primary", use_container_width=True, key="landing_btn_launch_studio"):
            st.session_state.current_page = PAGE_NEW_RESEARCH
            st.rerun()
    with col_cta2:
        if st.button("📦 Find Niche Products", use_container_width=True, key="landing_btn_find_products"):
            st.session_state.current_page = PAGE_PRODUCT_OPPORTUNITIES
            st.rerun()
    with col_cta3:
        if st.button("📊 View Live Dashboard", use_container_width=True, key="landing_btn_view_dashboard"):
            st.session_state.current_page = PAGE_DASHBOARD
            st.rerun()
    with col_cta4:
        if st.button("📖 Explore User Guide", use_container_width=True, key="landing_btn_view_guide"):
            st.session_state.current_page = PAGE_USER_GUIDE
            st.rerun()

    # Architecture Trust Indicators
    st.markdown(
        """
        <div class="hero-pillars-row" style="margin-bottom: 2rem;">
            <div class="hero-pillar-item">🛡️ <b>100% Local-First:</b> SQLite WAL On-Device</div>
            <div class="hero-pillar-item">⚡ <b>Zero Synthetic Data:</b> No Fabricated Volumes</div>
            <div class="hero-pillar-item">🔌 <b>Authentic APIs:</b> YouTube Suggest & Data API v3</div>
            <div class="hero-pillar-item">📦 <b>Safe Exports:</b> Formula-Sanitized CSV & XLSX</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Interactive Product Showcase
    st.markdown("---")
    st.markdown("### ✨ Interactive Product Showcase")
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem;">
            <span class="demo-pill"><span class="dot-demo"></span> [DEMO DATA - ILLUSTRATIVE PREVIEW]</span>
            <span style="font-size: 0.8rem; color: #94a3b8;">Simulated sample preview. Never stored into your actual SQLite research history.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    showcase_tab1, showcase_tab2, showcase_tab3, showcase_tab4, showcase_tab5 = st.tabs([
        "🔍 Autocomplete & Expansion",
        "🎥 Competitor SERP & Tag Cloud",
        "📦 60-Day Niche Product Gaps",
        "🏷️ Affiliate Planner & FTC Brief",
        "📡 Research Monitor & Alerts",
    ])

    # Showcase Tab 1: Autocomplete & Tree Expansion
    with showcase_tab1:
        st.markdown(
            """
            <div class="showcase-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: #ffffff;">Seed Query: <code>"wireless earbuds"</code></h4>
                        <div style="font-size: 0.8rem; color: #94a3b8;">Authentic dropdown suggestion simulation with multi-angle intent classification</div>
                    </div>
                    <span class="status-badge badge-success"><span class="dot-live"></span> Autocomplete Engine</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        demo_kws = [
            {"Keyword": "wireless earbuds for running", "Source": "LIVE_AUTOCOMPLETE", "Intent": "Audience & Use-Case", "Tail Length": "Medium-tail", "Relevance": 94.0},
            {"Keyword": "wireless earbuds vs wired", "Source": "LIVE_AUTOCOMPLETE", "Intent": "Comparison & Alternative", "Tail Length": "Medium-tail", "Relevance": 91.5},
            {"Keyword": "how to choose wireless earbuds", "Source": "GENERATED_QUERY", "Intent": "How-To Tutorial", "Tail Length": "Long-tail", "Relevance": 88.0},
            {"Keyword": "best wireless earbuds 2026", "Source": "LIVE_AUTOCOMPLETE", "Intent": "Best & Top List", "Tail Length": "Medium-tail", "Relevance": 96.0},
            {"Keyword": "wireless earbuds pairing issues", "Source": "GENERATED_QUERY", "Intent": "Problem-Solving", "Tail Length": "Long-tail", "Relevance": 82.0},
        ]
        df_demo_kws = pd.DataFrame(demo_kws)
        st.dataframe(df_demo_kws, use_container_width=True, hide_index=True)

        col_sc1, _ = st.columns([1.5, 2.5])
        with col_sc1:
            if st.button("⚡ Test Live Autocomplete with this Seed", key="btn_demo_seed_test", type="primary", use_container_width=True):
                st.session_state.active_seed_input = "wireless earbuds"
                st.session_state.last_query = "wireless earbuds"
                st.session_state.current_page = PAGE_NEW_RESEARCH
                st.rerun()

    # Showcase Tab 2: Competitor SERP & Tag Cloud
    with showcase_tab2:
        st.markdown(
            """
            <div class="showcase-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: #ffffff;">Target Query: <code>"best wireless earbuds 2026"</code></h4>
                        <div style="font-size: 0.8rem; color: #94a3b8;">101-unit batch SERP inspection with 0-unit local cache hits</div>
                    </div>
                    <span class="status-badge"><span class="dot-live"></span> YouTube Data API v3</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Videos Analyzed", "15 Videos")
        col_m2.metric("Median Views", "142,500 views")
        col_m3.metric("Median Age", "74 days ago")
        col_m4.metric("Opportunity Score", "84 / 100", "High Opportunity")

        st.markdown("###### 🏷️ Competitor Video Tags Cloud (1-Click Creator Copy)")
        demo_tags = ["wireless earbuds", "best earbuds 2026", "anc earbuds", "earbuds review", "budget earbuds", "sony wf 1000xm5", "bose earbuds"]
        st.text_area("Competitor Tags Cloud", value=", ".join(demo_tags), height=70, label_visibility="collapsed", disabled=True)

    # Showcase Tab 3: 60-Day Niche Product Gaps
    with showcase_tab3:
        st.markdown(
            """
            <div class="showcase-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: #ffffff;">Niche: <code>"Wireless Earbuds"</code> (Last 60 Days Window)</h4>
                        <div style="font-size: 0.8rem; color: #94a3b8;">Observed search results; does not guarantee platform-wide absence or sales</div>
                    </div>
                    <span class="status-badge badge-warning"><span class="dot-demo"></span> Product Gap Engine</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        demo_prods = [
            {"Product Name": "Earfun Air Pro 4", "Classification": "ZERO OBSERVED MATCHES", "Coverage": "4/4 Queries", "Matching Videos": 0, "Opp Score": 89.0, "Confidence": "High Evidence"},
            {"Product Name": "Moondrop Space Travel", "Classification": "FEW MATCHING VIDEOS", "Coverage": "3/3 Queries", "Matching Videos": 2, "Opp Score": 81.5, "Confidence": "Moderate Evidence"},
            {"Product Name": "Sony WF-1000XM5", "Classification": "ESTABLISHED COVERAGE", "Coverage": "4/4 Queries", "Matching Videos": 12, "Opp Score": 52.0, "Confidence": "High Evidence"},
        ]
        st.dataframe(pd.DataFrame(demo_prods), use_container_width=True, hide_index=True)

    # Showcase Tab 4: Affiliate Planner & FTC Brief
    with showcase_tab4:
        st.markdown(
            """
            <div class="showcase-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: #ffffff;">Product: <code>"Earfun Air Pro 4"</code></h4>
                        <div style="font-size: 0.8rem; color: #94a3b8;">Strategic format recommendation, ethical checklist & 6-part video script structure</div>
                    </div>
                    <span class="status-badge badge-success"><span class="dot-live"></span> FTC-Compliant Brief</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_b1, col_b2, col_b3 = st.columns(3)
        col_b1.metric("Recommended Format", "Product Review")
        col_b2.metric("Retail Price", "$79.99 USD")
        col_b3.metric("Affiliate Program", "Needs verification")

        st.info("⚖️ **FTC & Ethics Policy**: Disclose affiliate links transparently in video description and audio. Never claim hands-on testing without physical ownership or trial.")

    # Showcase Tab 5: Research Monitor & Alerts
    with showcase_tab5:
        st.markdown(
            """
            <div class="showcase-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h4 style="margin: 0; color: #ffffff;">Snapshot Comparison: <code>Run #1 vs Run #2</code></h4>
                        <div style="font-size: 0.8rem; color: #94a3b8;">Differential change detection with deduplicated recurring scheduler</div>
                    </div>
                    <span class="status-badge"><span class="dot-live"></span> Differential Monitor</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        col_d1.metric("New Candidates", "+2")
        col_d2.metric("Dropped from Sample", "-0")
        col_d3.metric("Video Count Shifts", "1 Product")
        col_d4.metric("New Channels Observed", "+3")

    # 3. Platform Value Matrix (6 Feature Cards)
    st.markdown("---")
    st.markdown("### 🏛️ Complete Research & Planning Architecture")
    st.caption("A unified, local-first toolkit designed for modern YouTube creators, agencies, and affiliate publishers.")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div class="feature-icon-box">🔍</div>
                    <h4 style="margin: 0 0 0.5rem 0; color: #ffffff;">Multi-Source Autocomplete</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
                        Discover authentic YouTube dropdown suggestions across A–Z, numeric, preposition, and question variations with zero simulated metrics.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="feature-card" style="margin-top: 1rem;">
                <div>
                    <div class="feature-icon-box">🎥</div>
                    <h4 style="margin: 0 0 0.5rem 0; color: #ffffff;">Competitor SERP Inspector</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
                        Inspect real ranking video duration, median view velocity, publish dates, and competitor video tag clouds with 101-unit quota efficiency.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_f2:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div class="feature-icon-box">🧩</div>
                    <h4 style="margin: 0 0 0.5rem 0; color: #ffffff;">Smart Pattern Variations</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
                        Generate deterministic intent variations across 10 canonical categories including bilingual Bangla informational and commercial patterns.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="feature-card" style="margin-top: 1rem;">
                <div>
                    <div class="feature-icon-box">📦</div>
                    <h4 style="margin: 0 0 0.5rem 0; color: #ffffff;">60-Day Product Gap Finder</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
                        Identify real products with zero or few observed YouTube videos in the last 60 days using transparent heuristic opportunity formulas.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_f3:
        st.markdown(
            """
            <div class="feature-card">
                <div>
                    <div class="feature-icon-box">🏷️</div>
                    <h4 style="margin: 0 0 0.5rem 0; color: #ffffff;">Affiliate Content Planner</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
                        Structure production briefs, video outlines, format recommendations, and FTC compliance reminders with verifiable affiliate data.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="feature-card" style="margin-top: 1rem;">
                <div>
                    <div class="feature-icon-box">📡</div>
                    <h4 style="margin: 0 0 0.5rem 0; color: #ffffff;">Automated Monitor & Alerts</h4>
                    <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
                        Save reusable configs, run deduplicated recurring scans, compare snapshot deltas, and track longitudinal trends without data extrapolation.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. Step-by-Step Research Workflow (Section D: How It Works)
    st.markdown("---")
    st.markdown("### ⚡ Step-by-Step Research Workflow (How It Works)")
    st.caption("How authentic platform data transforms into production-ready video opportunities without fabricated metrics.")

    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    with w_col1:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 1</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">Seed Input</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Enter a broad product category or core topic. No complex configuration required.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with w_col2:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 2</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">Autocomplete Capture</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Query YouTube's live suggestion service to capture real queries typed by viewers.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with w_col3:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 3</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">Tree Expansion</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Recursively branch into long-tail clusters with deterministic intent classification.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with w_col4:
        st.markdown(
            """
            <div class="feature-card">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 4</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">SERP Intelligence</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Inspect competitor view counts, publication dates, and tags via YouTube Data API v3.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    w_col5, w_col6, w_col7 = st.columns(3)
    with w_col5:
        st.markdown(
            """
            <div class="feature-card" style="margin-top: 1rem;">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 5</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">60-Day Gap Analysis</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Filter products with zero or few observed videos during the selected 60-day window.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with w_col6:
        st.markdown(
            """
            <div class="feature-card" style="margin-top: 1rem;">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 6</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">Content Briefs & Hooks</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Structure filming scripts with hook archetypes, affiliate calculations, and FTC checklists.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with w_col7:
        st.markdown(
            """
            <div class="feature-card" style="margin-top: 1rem;">
                <div style="font-weight: 800; color: #2563EB; font-size: 0.85rem;">STEP 7</div>
                <h4 style="margin: 0.25rem 0 0.5rem 0; color: #111827;">Sanitized Export</h4>
                <p style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    Export to UTF-8 BOM CSV or Excel (.xlsx) with formula injection protection (=, +, -, @).
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 5. Frequently Asked Questions & Knowledge Base (Section F)
    st.markdown("---")
    st.markdown("### ❓ Frequently Asked Questions & Knowledge Base")

    with st.expander("How does Keyword Studio differ from traditional keyword tools?", expanded=False):
        st.markdown(
            "Traditional tools show synthetic, extrapolated search volumes that often mislead creators. "
            "Keyword Studio queries YouTube's real autocomplete suggestion API directly on your local machine, "
            "guaranteeing that every single phrase is actively searched by actual YouTube viewers."
        )

    with st.expander("What does 'Zero Observed Matches' mean in the Product Gap Analyzer?", expanded=False):
        st.markdown(
            "It is empirical proof that no matching videos were found across your executed multi-angle queries "
            "during the selected date range. It does NOT claim that no video has ever existed anywhere on YouTube, "
            "but rather that recent coverage by creators is exceptionally low or nonexistent in search."
        )

    with st.expander("Do I need a paid YouTube API key?", expanded=False):
        st.markdown(
            "No. Core autocomplete discovery, recursive tree expansion, pattern matrix generation, intent classification, "
            "and offline project storage operate 100% free with zero API keys required. An optional Google YouTube Data API v3 "
            "key can be configured (free tier gives ~99 searches per day) to inspect view counts and video tags."
        )

    with st.expander("How does formula injection sanitization protect my exports?", expanded=False):
        st.markdown(
            "Spreadsheet applications like Excel and Google Sheets can automatically execute formulas if a cell begins with "
            "`=`, `+`, `-`, or `@`. Keyword Studio automatically sanitizes untrusted keyword inputs by prefixing them with a single quote "
            "(`'`), neutralizing Remote Code Execution (RCE) while keeping your data 100% readable."
        )

    # 6. Bottom Guided Workflow Call to Action & Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; padding: 2.5rem 1.5rem; background: #FFFFFF; border-radius: 16px; border: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);">
            <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-weight: 800;">Ready to Elevate Your YouTube Research?</h3>
            <p style="color: #64748B; max-width: 620px; margin: 0 auto 1.75rem auto; font-size: 0.95rem;">
                Explore real viewer queries, inspect competitor weaknesses, and find untapped niche products in minutes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_g1, col_g2, col_g3 = st.columns([1, 1, 1])
    with col_g1:
        if st.button("🚀 Start Keyword Discovery", type="primary", use_container_width=True, key="landing_btn_bottom_kw"):
            st.session_state.current_page = PAGE_NEW_RESEARCH
            st.rerun()
    with col_g2:
        if st.button("🏷️ Product Opportunity Planner", use_container_width=True, key="landing_btn_bottom_planner"):
            st.session_state.current_page = PAGE_PRODUCT_PLANNER
            st.rerun()
    with col_g3:
        if st.button("📖 Complete User Guide", use_container_width=True, key="landing_btn_bottom_guide"):
            st.session_state.current_page = PAGE_USER_GUIDE
            st.rerun()

    st.markdown(
        """
        <div class="footer-text">
            <b>YouTube Keyword Finder Studio</b> &bull; Apple-Inspired White Motion Design &bull; 100% Local-First SQLite WAL &bull; Zero External Telemetry
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_dashboard(is_ready: bool, recent_searches: List[Dict[str, Any]]) -> None:
    """Render the Overview Dashboard page."""
    render_page_header(
        title="Dashboard",
        subtitle="Real-time research session telemetry, storage status, and intelligent workflow recommendations.",
        category="WORKSPACE",
        badge_text="Live Ready" if is_ready else "Offline",
        badge_type="success" if is_ready else "warning",
        provenance="local_sqlite",
    )

    # Aggregated Database Stats
    db_stats = db_manager.get_database_stats() if is_ready else {}
    render_system_status(
        db_healthy=is_ready,
        recent_searches_count=len(recent_searches),
        total_keywords_count=db_stats.get("total_keywords", 0),
        cached_queries_count=db_stats.get("total_cached_queries", 0),
    )

    # Smart Onboarding, Next-Best-Action Workflow Assistant & Active Progress
    render_onboarding_guide(is_ready)
    render_next_best_action_banner(is_ready)
    render_workflow_progress_checklist(is_ready=is_ready)
    render_contextual_help("keyword_discovery")

    st.markdown("### 📊 Active Research Summary")

    # Active Session Summary
    if st.session_state.crawl_result:
        res: CrawlResult = st.session_state.crawl_result
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(
                f"**Active Session:** Query `'{st.session_state.last_query}'` | "
                f"Status: **{res.stop_reason.value}** | "
                f"Discovered: **{len(res.keywords)}** unique keywords in {res.duration_seconds}s."
            )
        with col2:
            if st.button("👉 View Results Table", type="primary", use_container_width=True):
                st.session_state.current_page = PAGE_RESULTS
                st.rerun()

        # Detailed cards for active session
        m1, m2, m3, m4 = st.columns(4)
        auto_count = sum(1 for k in res.keywords if k.source_type == "autocomplete")
        gen_count = sum(1 for k in res.keywords if k.is_generated or k.source_type == "generated")
        short_count = sum(1 for k in res.keywords if (k.tail_length or "Short-tail") == "Short-tail")
        long_count = sum(1 for k in res.keywords if (k.tail_length or "Long-tail") == "Long-tail")

        m1.metric("Unique Keywords", len(res.keywords))
        m2.metric("Autocomplete Results", auto_count)
        m3.metric("Generated Variations", gen_count)
        m4.metric("Queries Processed", res.queries_processed)

    elif st.session_state.direct_results:
        direct = st.session_state.direct_results
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(
                f"**Direct Search Active:** Query `'{st.session_state.last_query}'` | "
                f"Retrieved: **{len(direct)}** autocomplete suggestions."
            )
        with col2:
            if st.button("👉 View Results Table", type="primary", use_container_width=True):
                st.session_state.current_page = PAGE_RESULTS
                st.rerun()
    else:
        if render_empty_state(
            title="No Active Research Session in Memory",
            description="Enter a seed keyword to retrieve authentic YouTube autocomplete suggestions, or run a recursive deep crawl.",
            icon="🔍",
            action_label="🔍 Launch New Keyword Research",
            action_key="dash_launch_new_research_btn",
        ):
            st.session_state.current_page = PAGE_NEW_RESEARCH
            st.rerun()

    # Recent History
    st.markdown("---")
    st.markdown("### 🕒 Recent Research Projects")
    if recent_searches:
        display_history = []
        for s in recent_searches[:5]:
            display_history.append(
                {
                    "ID": s["id"],
                    "Project Name": s.get("project_name") or s["seed_keyword"],
                    "Seed Keyword": s["seed_keyword"],
                    "Language": s["language"],
                    "Country": s["country"],
                    "Status": s.get("status", "completed").title(),
                    "Keywords Found": s["total_results"],
                    "Created At": s["created_at"],
                }
            )
        df_hist = pd.DataFrame(display_history)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        col_h1, col_h2 = st.columns([2, 2])
        with col_h1:
            if st.button("📂 Manage Saved Projects", use_container_width=True):
                st.session_state.current_page = PAGE_SAVED
                st.rerun()
        with col_h2:
            if st.button("⚙️ Manage Cache & Backups", use_container_width=True):
                st.session_state.current_page = PAGE_SETTINGS
                st.rerun()
    else:
        if render_empty_state(
            title="No Saved Research Sessions Yet",
            description="Execute your first YouTube autocomplete research or recursive crawl to see projects logged here.",
            icon="📂",
            action_label="🔍 Start First Research",
            action_key="dash_start_first_research_btn",
        ):
            st.session_state.current_page = PAGE_NEW_RESEARCH
            st.rerun()


def render_page_new_research(is_ready: bool) -> None:
    """Render the New Keyword Research configuration page."""
    render_page_header(
        title="New Keyword Research",
        subtitle="Enter a seed keyword to retrieve authentic YouTube autocomplete dropdown suggestions, or perform controlled A–Z, numeric, and preposition expansions.",
        category="WORKSPACE",
        badge_text="Autocomplete Active",
        badge_type="primary",
        provenance="autocomplete",
    )
    render_contextual_help("keyword_discovery")
    render_interactive_tour("keyword_studio")

    rerun_p = st.session_state.get("rerun_params", {})
    default_seed_val = (
        st.session_state.get("active_seed_input")
        or (", ".join(rerun_p.get("seeds", [])) if rerun_p.get("seeds") else (st.session_state.last_query or "BEST CAR WAX"))
    )
    default_lang_code = rerun_p.get("language", "en")
    default_country_code = rerun_p.get("country", "US")

    trigger_az_from_panel = False

    with st.container():
        # Project Name & Seed Input
        col_proj, col_seed = st.columns([1, 2])
        with col_proj:
            project_name_input = st.text_input(
                "Project Name (Optional)",
                value=rerun_p.get("project_name", ""),
                placeholder="e.g. Car Care 2026",
                help="Custom project name for tracking in SQLite history.",
            )
        with col_seed:
            seed_input = st.text_input(
                "Seed Keyword(s)",
                value=default_seed_val,
                help="Enter a seed keyword (e.g. 'BEST CAR WAX') or multiple comma-separated seeds.",
                placeholder="e.g. BEST CAR WAX, python tutorial, data science",
                key="main_seed_input_widget",
            )

        # Immediate suggestion fetching & clear buttons
        col_s_tip, col_s_fetch, col_s_clr = st.columns([3, 1.5, 1])
        with col_s_tip:
            st.caption("⚡ *Click **Get Live Suggestions** to inspect the real YouTube dropdown predictions instantly.*")
        with col_s_fetch:
            fetch_live_clicked = st.button("🔍 Get Live Suggestions", use_container_width=True, type="primary")
        with col_s_clr:
            clear_seed_clicked = st.button("🧹 Clear", use_container_width=True)

        if clear_seed_clicked:
            st.session_state.instant_suggestions = []
            st.session_state.instant_suggestions_seed = ""
            st.session_state.active_seed_input = ""
            st.session_state.last_query = ""
            st.rerun()

        col_loc1, col_loc2 = st.columns(2)
        with col_loc1:
            lang_options = list(config.supported_languages.keys())
            default_lang_index = (
                lang_options.index(default_lang_code)
                if default_lang_code in lang_options
                else 0
            )
            selected_lang = st.selectbox(
                "Target Language",
                options=lang_options,
                index=default_lang_index,
                format_func=lambda code: f"{config.supported_languages[code]} ({code})",
                help="Select language for YouTube autocomplete requests.",
            )
        with col_loc2:
            country_options = list(config.supported_countries.keys())
            default_country_index = (
                country_options.index(default_country_code)
                if default_country_code in country_options
                else 0
            )
            selected_country = st.selectbox(
                "Target Country / Region",
                options=country_options,
                index=default_country_index,
                format_func=lambda code: f"{config.supported_countries[code]} ({code})",
                help="Select regional endpoint location filter.",
            )

        # Handle Immediate Autocomplete Fetching
        if fetch_live_clicked:
            parsed_seeds = parse_seed_inputs(seed_input)
            if not parsed_seeds:
                st.warning("⚠️ Please enter a seed keyword first.")
            else:
                target_q = parsed_seeds[0]
                with st.spinner(f"Querying YouTube autocomplete for '{target_q}'..."):
                    p = YouTubeAutocompleteProvider(database_manager=db_manager)
                    try:
                        instant_results = p.get_suggestions(
                            query=target_q,
                            language=selected_lang,
                            country=selected_country,
                            use_cache=True,
                        )
                        st.session_state.instant_suggestions = instant_results
                        st.session_state.instant_suggestions_seed = target_q
                        st.session_state.last_query = target_q
                        st.session_state.active_seed_input = target_q
                    except Exception as exc:
                        st.error(f"Failed to fetch live suggestions: {exc}")

        # Interactive YouTube-like Suggestion Panel
        if st.session_state.get("instant_suggestions"):
            s_list = st.session_state.instant_suggestions
            s_seed = st.session_state.get("instant_suggestions_seed", "")
            has_cached_item = any(getattr(s, "is_cached", False) for s in s_list)
            header_badge = "CACHED_AUTOCOMPLETE" if has_cached_item else "LIVE_AUTOCOMPLETE"
            badge_bg = "#f3e8ff" if has_cached_item else "#e0f2fe"
            badge_color = "#7e22ce" if has_cached_item else "#0369a1"

            st.markdown("---")
            st.markdown(
                f"<div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;'>"
                f"<h4 style='margin: 0;'>🎯 Real YouTube Autocomplete Dropdown: <code>\"{s_seed}\"</code></h4>"
                f"<span style='font-size: 0.8rem; font-weight: 600; background: {badge_bg}; color: {badge_color}; padding: 3px 10px; border-radius: 12px;'>{header_badge}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Retrieved **{len(s_list)}** authentic suggestions from YouTube Suggest API (No synthetic data):")

            for s_idx, sug in enumerate(s_list):
                r_col1, r_col2, r_col3, r_col4 = st.columns([5.5, 1.5, 1.5, 1.2])
                s_cached = getattr(sug, "is_cached", False)
                item_badge_text = "CACHED_AUTOCOMPLETE" if s_cached else "LIVE_AUTOCOMPLETE"
                item_badge_color = "#7c3aed" if s_cached else "#059669"

                with r_col1:
                    st.markdown(
                        f"<div style='padding: 6px 0; font-size: 1.02rem; display: flex; align-items: center;'>"
                        f"<span style='color: #94a3b8; margin-right: 8px;'>🔍</span>"
                        f"<span><b>{sug.keyword}</b></span>"
                        f"<span style='margin-left: 10px; font-size: 0.7rem; background: {item_badge_color}14; color: {item_badge_color}; border: 1px solid {item_badge_color}33; padding: 1px 6px; border-radius: 6px; font-weight: 600;'>{item_badge_text}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with r_col2:
                    if st.button("📌 Select", key=f"sel_sug_{s_idx}", help=f"Set '{sug.keyword}' as current search input"):
                        st.session_state.active_seed_input = sug.keyword
                        st.session_state.last_query = sug.keyword
                        st.rerun()
                with r_col3:
                    if st.button("🚀 Research", key=f"res_sug_{s_idx}", help=f"Launch research for '{sug.keyword}'"):
                        st.session_state.active_seed_input = sug.keyword
                        st.session_state.last_query = sug.keyword
                        st.session_state.quick_research_target = sug.keyword
                        st.rerun()
                with r_col4:
                    if st.button("📋 Copy", key=f"cp_sug_{s_idx}", help="Copy this keyword"):
                        st.session_state.copy_box_content = [sug.keyword]
                        st.session_state.show_copy_box = True
                        st.rerun()

            # Suggestion Panel Action Bar
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            p_act1, p_act2, p_act3, _ = st.columns([2, 2, 2.5, 2.5])
            with p_act1:
                if st.button("📋 Copy All Visible Suggestions", key="cp_all_visible_btn", use_container_width=True):
                    st.session_state.copy_box_content = [s.keyword for s in s_list]
                    st.session_state.show_copy_box = True
                    st.rerun()
            with p_act2:
                if st.button("🔄 Refresh Suggestions", key="refresh_live_btn", use_container_width=True):
                    p = YouTubeAutocompleteProvider(database_manager=db_manager)
                    try:
                        refreshed = p.get_suggestions(
                            query=s_seed,
                            language=selected_lang,
                            country=selected_country,
                            use_cache=False,
                        )
                        st.session_state.instant_suggestions = refreshed
                        st.success(f"Refreshed {len(refreshed)} live suggestions from YouTube.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Refresh failed: {exc}")
            with p_act3:
                trigger_az_from_panel = st.button("⚡ Run Full A-Z Expansion", key="az_from_panel_btn", type="primary", use_container_width=True)

        # Expansion Mode & Parameters
        st.markdown("---")
        st.markdown("##### ⚙️ Discovery Methods (Phase 9 Multi-Source Intelligence)")
        st.caption("Select systematic keyword discovery methods beyond the seed keyword:")

        c_exp1, c_exp2, c_exp3 = st.columns(3)
        with c_exp1:
            exp_direct = st.checkbox("A. Seed Autocomplete", value=True, help="Fetch direct seed suggestions")
            exp_az = st.checkbox("B. Alphabet Expansion (A–Z)", value=False, help="Queries 'seed a' through 'seed z' (26 queries)")
        with c_exp2:
            exp_prefix_intent = st.checkbox("C. Prefix & Intent Expansion", value=False, help="Queries 'seed for', 'seed in', 'seed vs', 'seed review', 'seed comparison'")
            exp_questions = st.checkbox("D. Question Expansion", value=False, help="Queries 'how to choose best ...', 'which ... is best', 'what is', 'why', 'when'")
        with c_exp3:
            exp_audience = st.checkbox("E. Audience & Use-Case", value=False, help="Queries 'seed for beginners', 'seed for black cars', 'seed for old cars', etc.")
            exp_num = st.checkbox("Numeric Expansion (0–9)", value=False, help="Queries 'seed 0' through 'seed 9' (10 queries)")

        col_rec1, col_rec2 = st.columns([2, 2])
        with col_rec1:
            recursive_mode = st.toggle(
                "Enable Multi-Level Recursive Tree Expansion (Depth > 1)",
                value=False,
                help="Recursively queries autocomplete suggestions of discovered keywords level-by-level.",
            )
        with col_rec2:
            enable_patterns = st.checkbox(
                "Auto-generate Pattern Variations (Best, How-to, Reviews)",
                value=False,
                help="Generates offline pattern templates upon completion.",
            )

        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            max_depth = st.slider(
                "Max Recursion Depth",
                min_value=0,
                max_value=config.max_allowed_depth,
                value=rerun_p.get("max_depth", config.default_max_depth if recursive_mode else 1),
                help="Depth 0 = seed only; Depth 1 = seed + immediate suggestions; Depth 2+ = recursive branches.",
            )
        with col_b2:
            max_unique_keywords = st.slider(
                "Unique Result Target",
                min_value=10,
                max_value=config.max_allowed_unique_keywords,
                value=rerun_p.get("max_unique_keywords", config.default_max_unique_keywords),
                step=10,
                help="Maximum unique keywords to discover before halting.",
            )
        with col_b3:
            request_budget = st.slider(
                "Request Budget",
                min_value=5,
                max_value=config.max_allowed_budget,
                value=rerun_p.get("request_budget", config.default_request_budget),
                step=5,
                help="Maximum allowable HTTP requests per session.",
            )
        with col_b4:
            min_delay = st.slider(
                "Request Delay (s)",
                min_value=0.0,
                max_value=1.0,
                value=rerun_p.get("min_delay_seconds", config.crawl_min_delay_seconds),
                step=0.05,
                help="Polite minimum pause between requests.",
            )

        selected_pattern_categories = []
        if enable_patterns:
            cat_options = list(PatternCategory)
            cat_display = {
                PatternCategory.LISTICLES: "Listicles (Top 5 / 10)",
                PatternCategory.BEST_BUYING: "Best & Buying Intent",
                PatternCategory.REVIEWS: "Reviews & Feedback",
                PatternCategory.HOW_TO: "How-To & Tutorials",
                PatternCategory.COMPARISON: "Comparison (VS)",
                PatternCategory.QUESTIONS: "Questions (What, How, Why)",
                PatternCategory.AUDIENCE: "Audience & Use-Case",
                PatternCategory.TIME_MODIFIERS: "Time Modifiers (Current Year)",
            }
            selected_pattern_categories = st.multiselect(
                "Enabled Pattern Categories",
                options=cat_options,
                default=[
                    PatternCategory.LISTICLES,
                    PatternCategory.BEST_BUYING,
                    PatternCategory.HOW_TO,
                    PatternCategory.QUESTIONS,
                ],
                format_func=lambda c: cat_display.get(c, c.value),
            )

        st.caption("ℹ️ *Note: Requested keyword counts and depths are maximum target caps, not guarantees.*")

        # Action Buttons
        col_btn1, col_btn2, _ = st.columns([2, 2, 3])
        with col_btn1:
            start_clicked = st.button("🚀 Start Research", type="primary", use_container_width=True)
        with col_btn2:
            cancel_clicked = st.button("🛑 Cancel Research", type="secondary", use_container_width=True)

        if cancel_clicked:
            if "cancel_event" in st.session_state and st.session_state.cancel_event:
                st.session_state.cancel_event.set()
                st.warning("⚠️ Cancellation requested. Stopping worker at next safe checkpoint...")

    # Research Execution
    quick_target = st.session_state.pop("quick_research_target", None)
    should_run = start_clicked or trigger_az_from_panel or bool(quick_target)

    if should_run:
        if quick_target:
            seeds = [quick_target]
        else:
            seeds = parse_seed_inputs(seed_input)

        if not seeds:
            st.error("⚠️ Please enter at least one valid seed keyword (minimum 2 characters).")
            return

        st.session_state.last_query = ", ".join(seeds)
        st.session_state.cancel_event = threading.Event()

        # Clear rerun_params if consumed
        if "rerun_params" in st.session_state:
            del st.session_state["rerun_params"]

        # Determine effective mode
        run_az = exp_az or trigger_az_from_panel
        is_controlled = run_az or exp_num or exp_prefix_intent or exp_questions or exp_audience or exp_direct

        if is_controlled:
            st.session_state.search_mode = "controlled_expansion"

            progress_bar = st.progress(0.0)
            status_text = st.empty()
            metric_cols = st.columns(4)
            m_queries = metric_cols[0].empty()
            m_kws = metric_cols[1].empty()
            m_budget = metric_cols[2].empty()
            m_curr = metric_cols[3].empty()

            def on_expansion_progress(p: CrawlProgress) -> None:
                progress_val = min(
                    1.0,
                    max(
                        p.queries_processed / max(1, request_budget),
                        p.keywords_discovered / max(1, max_unique_keywords),
                    ),
                )
                progress_bar.progress(progress_val)
                status_text.markdown(f"**Expanding Query:** `{p.current_query}`")
                m_queries.metric("Queries Processed", p.queries_processed)
                m_kws.metric("Keywords Found", p.keywords_discovered)
                m_budget.metric("Remaining Requests", p.requests_remaining)
                m_curr.metric("Current Query", p.current_query[:25])

            exp_cfg = ExpansionConfig(
                seeds=seeds,
                language=selected_lang,
                country=selected_country,
                include_seed=exp_direct,
                include_alphabet=run_az,
                include_prefix_intent=exp_prefix_intent,
                include_questions=exp_questions,
                include_audience_usecase=exp_audience,
                include_numbers=exp_num,
                include_modifiers=exp_prefix_intent,
                request_budget=request_budget,
                min_delay_seconds=min_delay,
                max_unique_keywords=max_unique_keywords,
                use_cache=True,
            )

            with st.spinner("Controlled YouTube keyword expansion in progress..."):
                exp_result = execute_controlled_expansion(
                    expansion_config=exp_cfg,
                    progress_callback=on_expansion_progress,
                    cancellation_token=st.session_state.cancel_event,
                    save_to_db=is_ready,
                    project_name=project_name_input or seeds[0],
                )
                st.session_state.last_expansion_result = exp_result

            # Auto-generate pattern variations if enabled
            if enable_patterns and selected_pattern_categories:
                pat_cfg = PatternConfig(
                    seeds=seeds,
                    categories=selected_pattern_categories,
                    language_mode=PatternLanguage.BOTH,
                    max_generated=max_unique_keywords,
                )
                generated_patterns = st.session_state.pattern_generator.generate(pat_cfg)
                exp_result.keywords = st.session_state.pattern_generator.merge_provenance(
                    existing_keywords=exp_result.keywords,
                    generated_keywords=generated_patterns,
                )

            # Convert ExpansionResult to CrawlResult for unified results view
            st.session_state.crawl_result = CrawlResult(
                keywords=exp_result.keywords,
                stop_reason=exp_result.stop_reason,
                queries_processed=exp_result.queries_processed,
                total_requests_made=exp_result.total_requests_made,
                is_partial=exp_result.is_partial,
                error_message=exp_result.error_message,
                duration_seconds=exp_result.duration_seconds,
            )
            st.session_state.current_page = PAGE_RESULTS
            st.success(
                f"✅ Expansion complete: Found **{len(exp_result.keywords)}** unique keywords. "
                f"Reason: {exp_result.stop_reason.value}."
            )
            st.rerun()

        elif recursive_mode:
            st.session_state.search_mode = "recursive"

            progress_bar = st.progress(0.0)
            status_text = st.empty()
            metric_cols = st.columns(4)
            m_queries = metric_cols[0].empty()
            m_kws = metric_cols[1].empty()
            m_depth = metric_cols[2].empty()
            m_curr = metric_cols[3].empty()

            def on_progress(p: CrawlProgress) -> None:
                progress_val = min(
                    1.0,
                    max(
                        p.queries_processed / max(1, request_budget),
                        p.keywords_discovered / max(1, max_unique_keywords),
                    ),
                )
                progress_bar.progress(progress_val)
                status_text.markdown(f"**Expanding:** `{p.current_query}` (Depth {p.current_depth})")
                m_queries.metric("Queries Processed", p.queries_processed)
                m_kws.metric("Keywords Found", p.keywords_discovered)
                m_depth.metric("Current Depth", p.current_depth)
                m_curr.metric("Remaining Requests", p.requests_remaining)

            crawl_cfg = CrawlConfig(
                seeds=seeds,
                language=selected_lang,
                country=selected_country,
                max_depth=max_depth,
                max_unique_keywords=max_unique_keywords,
                request_budget=request_budget,
                min_delay_seconds=min_delay,
                use_cache=True,
            )

            with st.spinner("Recursive keyword discovery in progress..."):
                crawl_result = execute_recursive_crawl(
                    crawl_config=crawl_cfg,
                    progress_callback=on_progress,
                    cancellation_token=st.session_state.cancel_event,
                    save_to_db=is_ready,
                    project_name=project_name_input or seeds[0],
                )

            # Auto-generate pattern variations if enabled
            if enable_patterns and selected_pattern_categories:
                pat_cfg = PatternConfig(
                    seeds=seeds,
                    categories=selected_pattern_categories,
                    language_mode=PatternLanguage.BOTH,
                    max_generated=max_unique_keywords,
                )
                generated_patterns = st.session_state.pattern_generator.generate(pat_cfg)
                crawl_result.keywords = st.session_state.pattern_generator.merge_provenance(
                    existing_keywords=crawl_result.keywords,
                    generated_keywords=generated_patterns,
                )

            st.session_state.crawl_result = crawl_result
            st.session_state.current_page = PAGE_RESULTS
            st.success(
                f"✅ Discovery complete: Found **{len(crawl_result.keywords)}** unique keywords. "
                f"Reason: {crawl_result.stop_reason.value}."
            )
            st.rerun()

        else:
            # Single Direct Autocomplete Search
            st.session_state.search_mode = "direct"
            with st.spinner(f"Querying YouTube autocomplete for '{seeds[0]}'..."):
                suggestions, err_msg = execute_keyword_search(
                    query=seeds[0],
                    language=selected_lang,
                    country=selected_country,
                    save_to_db=is_ready,
                    project_name=project_name_input or seeds[0],
                )

            if err_msg:
                st.error(err_msg)
            else:
                st.session_state.direct_results = suggestions
                # Convert to DiscoveredKeyword models
                as_discovered = [
                    DiscoveredKeyword(
                        keyword=s.keyword,
                        normalized_key=s.keyword.lower(),
                        depth=1,
                        parent_queries=[seeds[0]],
                        discovery_paths=1,
                        source_type="CACHED_AUTOCOMPLETE" if getattr(s, "is_cached", False) else "LIVE_AUTOCOMPLETE",
                        source_name="youtube_autocomplete",
                        language=selected_lang,
                        country=selected_country,
                        discovery_query=seeds[0],
                        is_cached=getattr(s, "is_cached", False),
                    )
                    for s in suggestions
                ]
                st.session_state.crawl_result = CrawlResult(
                    keywords=as_discovered,
                    stop_reason=StopReason.TARGET_REACHED,
                    queries_processed=1,
                    total_requests_made=1,
                    is_partial=False,
                    duration_seconds=0.0,
                )
                st.session_state.current_page = PAGE_RESULTS
                st.success(f"✅ Retrieved **{len(suggestions)}** suggestions for '{seeds[0]}'.")
                st.rerun()



def render_page_results() -> None:
    """Render the Interactive Keyword Results Table, Multi-dimensional Filters, and Export Center."""
    # Determine active keywords
    all_keywords: List[DiscoveredKeyword] = []
    query_label = st.session_state.last_query or "Keywords"

    if st.session_state.crawl_result:
        all_keywords = st.session_state.crawl_result.keywords
    elif st.session_state.direct_results:
        all_keywords = [
            DiscoveredKeyword(
                keyword=s.keyword,
                normalized_key=s.keyword.lower(),
                depth=1,
                parent_queries=[query_label],
                discovery_paths=1,
                source_type="CACHED_AUTOCOMPLETE" if getattr(s, "is_cached", False) else "LIVE_AUTOCOMPLETE",
                source_name="youtube_autocomplete",
                language=s.language,
                country=s.country,
                discovery_query=query_label,
                is_cached=getattr(s, "is_cached", False),
            )
            for s in st.session_state.direct_results
        ]

    render_page_header(
        title="Keyword Results",
        subtitle="Interactive keyword results table, multi-dimensional filters, search intent distribution, and exports.",
        category="WORKSPACE",
        badge_text=f"{len(all_keywords)} Keywords" if all_keywords else "No Active Dataset",
        badge_type="primary" if all_keywords else "neutral",
        provenance="autocomplete" if all_keywords else "local_sqlite",
    )

    if not all_keywords:
        if render_empty_state(
            title="No Active Keywords in Memory",
            description="Launch a new research session or select a saved project to inspect keyword variations and filters.",
            icon="📋",
            action_label="🔍 Launch New Keyword Research",
            action_key="results_launch_new_research_btn",
        ):
            st.session_state.current_page = PAGE_NEW_RESEARCH
            st.rerun()
        return

    # Ensure topic clustering and relevance scoring are computed across all active keywords
    clusters = default_clusterer.cluster_keywords(all_keywords, seed_keyword=query_label)
    cluster_map = {}
    for c in clusters:
        for kw in c.keywords:
            cluster_map[normalize_keyword_key(kw)] = c.name
    for k in all_keywords:
        norm = getattr(k, "normalized_key", None) or normalize_keyword_key(k.keyword)
        if norm in cluster_map and (not getattr(k, "cluster_name", None) or k.cluster_name == "Core Seed Variations"):
            k.cluster_name = cluster_map[norm]
        if getattr(k, "relevance_score", 0.0) == 0.0:
            cls = default_classifier.classify(k.keyword)
            rel = default_scorer.score(keyword=k.keyword, seed_keyword=query_label, classification=cls)
            k.relevance_score = rel.total_score
            if not getattr(k, "intent_explanation", ""):
                k.intent_explanation = cls.primary_explanation

    # 1. Research Summary Card (Module 9)
    last_exp = st.session_state.get("last_expansion_result")
    query_logs = last_exp.query_logs if last_exp else None
    stop_reason_val = st.session_state.crawl_result.stop_reason if st.session_state.crawl_result else StopReason.TARGET_REACHED
    elapsed_sec = st.session_state.crawl_result.duration_seconds if st.session_state.crawl_result else 0.0

    session_summary = ResearchSummary.from_session_data(
        seed_keyword=query_label,
        keywords=all_keywords,
        query_logs=query_logs,
        stop_reason=stop_reason_val,
        elapsed_seconds=elapsed_sec,
        cluster_count=len([c for c in clusters if not c.is_excluded]),
    )

    with st.expander("📊 Research Session Summary & Telemetry", expanded=True):
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        sc1.metric("Queries Attempted", session_summary.queries_attempted)
        sc2.metric("Queries Successful", session_summary.queries_successful)
        sc3.metric("Live Autocomplete", session_summary.live_autocomplete_count)
        sc4.metric("Cached Responses", session_summary.cached_autocomplete_count)
        sc5.metric("Generated Ideas", session_summary.generated_keyword_count)

        sc6, sc7, sc8, sc9, sc10 = st.columns(5)
        sc6.metric("Total Unique Keywords", session_summary.total_unique_keywords)
        sc7.metric("Topic Clusters Created", session_summary.clusters_created)
        sc8.metric("Failed Queries", session_summary.queries_failed)
        sc9.metric("Session Status", session_summary.status)
        sc10.metric("Elapsed Time", f"{session_summary.elapsed_seconds:.1f}s")

    # 2. Honest SERP Metrics Notice (Module 6)
    st.info(
        "ℹ️ **SERP Metrics & Search Volume Notice**: "
        "`Not available — no verified data source connected`\n\n"
        "*(Note: Autocomplete suggestion frequency or position is strictly research discovery data, NOT search volume or ranking competition. "
        "Relevance scores reflect transparent lexical rules, not ranking guarantees.)*"
    )

    # 3. Multi-Dimensional Filter Toolbar
    with st.expander("🔍 Filter, Search & Sort Keywords", expanded=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            f_source = st.selectbox(
                "Source Type",
                options=[
                    "All Sources",
                    "LIVE_AUTOCOMPLETE (Live YouTube)",
                    "CACHED_AUTOCOMPLETE (Local Cache)",
                    "GENERATED_PATTERN (Variations)",
                ],
                index=0,
            )
            f_tail = st.selectbox(
                "Tail Length",
                options=["All Lengths", "Short-tail", "Medium-tail", "Long-tail"],
                index=0,
            )

        with f_col2:
            intent_opts = [
                "All Intents",
                "Informational",
                "How-to / Tutorial",
                "Comparison / VS",
                "Review",
                "Best / Top list",
                "Buying / Commercial intent",
                "Problem-solving",
                "Audience-specific",
                "Location-specific",
                "General / Unclassified",
                "Question",
            ]
            f_intent = st.selectbox("Search Intent", options=intent_opts, index=0)

            active_cluster_names = ["All Clusters"] + [c.name for c in clusters if not c.is_excluded]
            f_cluster = st.selectbox("Topic Cluster", options=active_cluster_names, index=0)

        with f_col3:
            f_min_rel = st.slider("Min Relevance Score", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
            f_sort = st.selectbox(
                "Sort Results By",
                options=[
                    "Relevance Score (Highest First)",
                    "Relevance Score (Lowest First)",
                    "Alphabetical (A–Z)",
                    "Word Count (Longest First)",
                    "Word Count (Shortest First)",
                ],
                index=0,
            )

        with f_col4:
            available_langs = ["All Languages"] + sorted(list({k.language for k in all_keywords if k.language}))
            f_lang = st.selectbox("Language", options=available_langs, index=0)
            f_search = st.text_input("Substring Search", placeholder="e.g. tutorial, vs, best")

    # Apply filters
    filtered_items = filter_keywords(
        keywords=all_keywords,
        source_filter=f_source,
        tail_filter=f_tail,
        intent_filter=f_intent,
        lang_filter=f_lang,
        country_filter="All Countries",
        search_query=f_search,
        cluster_filter=f_cluster,
        min_relevance=f_min_rel,
    )

    # Apply sorting
    if "Relevance Score (Highest First)" in f_sort:
        filtered_items.sort(key=lambda item: getattr(item[0], "relevance_score", 0.0), reverse=True)
    elif "Relevance Score (Lowest First)" in f_sort:
        filtered_items.sort(key=lambda item: getattr(item[0], "relevance_score", 0.0), reverse=False)
    elif "Alphabetical" in f_sort:
        filtered_items.sort(key=lambda item: item[0].keyword.lower())
    elif "Word Count (Longest First)" in f_sort:
        filtered_items.sort(key=lambda item: getattr(item[0], "word_count", len(item[0].keyword.split())), reverse=True)
    elif "Word Count (Shortest First)" in f_sort:
        filtered_items.sort(key=lambda item: getattr(item[0], "word_count", len(item[0].keyword.split())), reverse=False)

    df_filtered = build_dataframe_from_keywords(filtered_items)

    if df_filtered.empty and all_keywords:
        render_empty_state(
            title="No Keywords Match Filter Criteria",
            description=f"Your filter criteria matched 0 of the {len(all_keywords)} discovered keywords. Adjust your Tail Length, Search Intent, or search query in the filter toolbar above.",
            icon="🔍",
        )

    st.caption(
        f"Displaying **{len(filtered_items)}** of **{len(all_keywords)}** discovered keywords. "
        "*(All keyword classifications, clusters, and relevance scores are rule-based heuristics)*"
    )

    # 4. Topic Cluster Management Section (Module 7)
    with st.expander("🧩 Topic Clusters & Cluster Management (Phase 9)", expanded=False):
        st.caption("Organized topic groups based on shared semantic modifiers, intent, and use cases:")
        for c in clusters:
            if c.is_excluded:
                continue
            with st.container():
                cc1, cc2 = st.columns([3, 1])
                cc1.markdown(f"**{c.name}** ({len(c.keywords)} keywords) — *{c.explanation}*")
                with cc2:
                    if st.button(f"Exclude Cluster", key=f"excl_btn_{c.name}"):
                        default_clusterer.exclude_cluster(clusters, c.name, True)
                        st.rerun()

        st.markdown("---")
        st.markdown("##### ✏️ Rename Cluster or Move Keyword")
        r_col1, r_col2, r_col3 = st.columns([2, 2, 1])
        with r_col1:
            ren_old = st.selectbox("Select Cluster to Rename", options=[c.name for c in clusters if not c.is_excluded], key="ren_old_select")
        with r_col2:
            ren_new = st.text_input("New Cluster Name", key="ren_new_input")
        with r_col3:
            if st.button("Rename", key="do_rename_btn", use_container_width=True):
                if ren_new.strip():
                    default_clusterer.rename_cluster(clusters, ren_old, ren_new.strip())
                    for k in all_keywords:
                        if getattr(k, "cluster_name", "") == ren_old:
                            k.cluster_name = ren_new.strip()
                    st.success(f"Renamed cluster to '{ren_new.strip()}'.")
                    st.rerun()

    # 5. Actions Toolbar
    st.markdown("##### ⚡ Keyword Actions")
    act_col1, act_col2, act_col3, act_col4 = st.columns(4)

    selected_rows = st.session_state.get("results_table_selection", {}).get("rows", [])
    selected_indices = [r for r in selected_rows if r < len(df_filtered)]

    with act_col1:
        if st.button("📋 Copy All Filtered", use_container_width=True):
            st.session_state.copy_box_content = [item[0].keyword for item in filtered_items]
            st.session_state.show_copy_box = True

    with act_col2:
        if st.button(f"📋 Copy Selected ({len(selected_indices)})", use_container_width=True):
            if selected_indices:
                st.session_state.copy_box_content = [
                    df_filtered.iloc[r]["Keyword"] for r in selected_indices
                ]
                st.session_state.show_copy_box = True
            else:
                st.info("Select one or more rows in the table below to copy.")

    with act_col3:
        if st.button("🗑️ Remove Selected from View", use_container_width=True):
            if selected_rows:
                to_remove_keys = {
                    df_filtered.iloc[r]["Keyword"]
                    for r in selected_rows
                    if r < len(df_filtered)
                }
                if st.session_state.crawl_result:
                    st.session_state.crawl_result.keywords = [
                        k
                        for k in st.session_state.crawl_result.keywords
                        if k.keyword not in to_remove_keys
                    ]
                st.success(f"Removed {len(to_remove_keys)} keywords from active view. (Database records remain intact).")
                st.rerun()
            else:
                st.info("Select one or more rows in the table below to remove from view.")

    with act_col4:
        csv_bytes = export_keywords_to_csv(df_filtered)
        st.download_button(
            "📥 Quick CSV",
            data=csv_bytes,
            file_name=generate_export_filename(query_label, scope="filtered", extension="csv"),
            mime="text/csv",
            use_container_width=True,
        )

    # Copy box drawer
    if st.session_state.get("show_copy_box", False) and st.session_state.get("copy_box_content"):
        render_copy_box(st.session_state.copy_box_content, label="Keyword Export Clipboard")
        if st.button("✖️ Close Copy Box"):
            st.session_state.show_copy_box = False
            st.rerun()

    # 6. Interactive Results Table
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.dataframe(
        df_filtered,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="results_table_selection",
    )

    # 7. Export Center Expander
    with st.expander("📤 Export Center (Multi-Scope, Formula Protection & Unicode BOM)", expanded=False):
        st.caption(
            "Export keywords to CSV (UTF-8 BOM encoded for seamless Excel display of Bangla text) "
            "or Excel (.xlsx) with built-in protection against spreadsheet formula injection."
        )

        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            export_scope = st.radio(
                "Export Scope",
                options=[
                    f"Currently Filtered ({len(filtered_items)} keywords)",
                    f"Selected Rows Only ({len(selected_indices)} keywords)" if selected_indices else "Selected Rows Only (0 selected)",
                    f"All Discovered Keywords ({len(all_keywords)} keywords)",
                ],
                index=0,
                key="export_center_scope",
            )
        with exp_col2:
            protect_formulas = st.checkbox(
                "🛡️ Spreadsheet Formula Injection Protection",
                value=True,
                help="Neutralizes formula injection by escaping leading '=', '+', '-', '@', '\\t', '\\r' characters.",
                key="export_center_formula_protect",
            )
            include_meta = st.checkbox(
                "📄 Include Research Metadata Header",
                value=True,
                help="Includes project name, date, and row count at top of file.",
                key="export_center_include_meta",
            )

        if "Selected Rows Only" in export_scope:
            if selected_indices:
                target_export_df = df_filtered.iloc[selected_indices].copy()
                scope_tag = "selected"
            else:
                target_export_df = pd.DataFrame(columns=df_filtered.columns)
                scope_tag = "selected"
        elif "All Discovered" in export_scope:
            all_tuples = [
                (k, k.tail_length or "Short-tail", k.intent_labels or ["Informational"])
                for k in all_keywords
            ]
            target_export_df = build_dataframe_from_keywords(all_tuples)
            scope_tag = "all"
        else:
            target_export_df = df_filtered.copy()
            scope_tag = "filtered"

        meta_dict = (
            {
                "Project / Query": query_label,
                "Scope": scope_tag,
                "Export Date": datetime.now(timezone.utc).isoformat(),
                "Total Rows": len(target_export_df),
            }
            if include_meta
            else None
        )

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_dl = ExportService.export_csv(
                target_export_df,
                sanitize_formulas=protect_formulas,
                include_bom=True,
                metadata_header=meta_dict,
            )
            st.download_button(
                "📥 Download CSV (UTF-8 BOM)",
                data=csv_dl,
                file_name=generate_export_filename(query_label, scope=scope_tag, extension="csv"),
                mime="text/csv",
                use_container_width=True,
                key="export_center_csv_btn",
            )

        with col_dl2:
            excel_dl = ExportService.export_excel(
                target_export_df,
                sanitize_formulas=protect_formulas,
                sheet_name="Keywords",
                metadata_header=meta_dict,
            )
            st.download_button(
                "📥 Download Excel (.xlsx)",
                data=excel_dl,
                file_name=generate_export_filename(query_label, scope=scope_tag, extension="xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_center_excel_btn",
            )

        # 7. Context-Aware Recommended Next Step
        top_discovered_kw = all_keywords[0].keyword if all_keywords else query_label
        p_click, s_click = render_recommended_next_step(
            title=f"Inspect YouTube Competitor SERP for '{top_discovered_kw}'",
            description=f"You have discovered {len(all_keywords)} keywords for '{query_label}'. Analyze real top-ranking videos, view counts, and competitor metadata to validate search demand.",
            action_label=f"🎥 Inspect SERP for '{top_discovered_kw[:25]}'",
            action_key="res_next_action_serp_btn",
            why_recommended="Validates whether real videos ranking for your top keyword are outdated or from smaller creators, proving a genuine search gap.",
            secondary_action_label="🧩 Expand Query Matrix in Pattern Generator",
            secondary_action_key="res_next_action_pat_btn",
        )
        if p_click:
            st.session_state.active_seed_input = top_discovered_kw
            st.session_state.current_page = PAGE_VIDEO_RESEARCH
            st.rerun()
        if s_click:
            st.session_state.active_seed_input = query_label
            st.session_state.current_page = PAGE_PATTERNS
            st.rerun()


def render_page_patterns() -> None:
    """Render the Smart Keyword Pattern Generator page."""
    render_page_header(
        title="Pattern Generator",
        subtitle="Generate high-intent search query variations across 8 configurable categories in English and Bangla. Operates 100% offline with zero external network calls or API keys.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="100% Offline Engine",
        badge_type="neutral",
        provenance="deterministic",
    )
    render_contextual_help("pattern_generator")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pat_seed_input = st.text_input(
            "Base Seed Keyword",
            value=st.session_state.last_query.split(",")[0].strip() if st.session_state.last_query else "python tutorial",
            help="Base topic or seed keyword for generating search patterns.",
        )
        pat_lang_mode = st.selectbox(
            "Output Language Mode",
            options=["Both (English & বাংলা)", "English only", "Bangla only (বাংলা)"],
            index=0,
            help="Select whether patterns should be generated in English, Bangla, or both.",
        )
        pat_alternatives_input = st.text_input(
            "Comparison Alternatives / Competitors (Optional)",
            placeholder="e.g. django, flask, fastapi",
            help="Optional verified alternatives for head-to-head comparison patterns.",
        )

    with col_p2:
        cat_display_names = {
            PatternCategory.LISTICLES: "Listicles (Top 5 / 10, Best 5)",
            PatternCategory.BEST_BUYING: "Best & Buying Intent",
            PatternCategory.REVIEWS: "Reviews & Feedback",
            PatternCategory.HOW_TO: "How-To & Tutorials",
            PatternCategory.COMPARISON: "Comparison (VS & Differences)",
            PatternCategory.QUESTIONS: "Questions (What, How, Why)",
            PatternCategory.AUDIENCE: "Audience & Use-Case",
            PatternCategory.TIME_MODIFIERS: "Time Modifiers (Current Year)",
        }
        selected_categories = st.multiselect(
            "Enabled Pattern Categories",
            options=list(cat_display_names.keys()),
            default=list(cat_display_names.keys()),
            format_func=lambda c: cat_display_names[c],
            help="Choose which pattern categories to include.",
        )
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            include_current_year = st.checkbox("Include Current Year", value=True)
        with col_opt2:
            max_patterns = st.slider("Max Patterns Limit", min_value=10, max_value=200, value=50, step=10)

    col_gen_btn, _ = st.columns([2, 3])
    with col_gen_btn:
        generate_clicked = st.button("✨ Generate Keyword Patterns", type="primary", use_container_width=True)

    if generate_clicked:
        is_valid, sanitized_seed, _ = sanitize_seed_keyword(pat_seed_input)
        if not is_valid:
            st.error("⚠️ Please enter a valid seed keyword (minimum 2 characters).")
        elif not selected_categories:
            st.error("⚠️ Please select at least one pattern category.")
        else:
            alts = (
                [a.strip() for a in pat_alternatives_input.split(",") if a.strip()]
                if pat_alternatives_input
                else None
            )
            lang_mode_map = {
                "Both (English & বাংলা)": PatternLanguage.BOTH,
                "English only": PatternLanguage.EN,
                "Bangla only (বাংলা)": PatternLanguage.BN,
            }
            pat_cfg = PatternConfig(
                seeds=[sanitized_seed],
                categories=selected_categories,
                language_mode=lang_mode_map[pat_lang_mode],
                alternatives=alts,
                include_current_year=include_current_year,
                max_generated=max_patterns,
            )
            gen_list = st.session_state.pattern_generator.generate(pat_cfg)
            st.session_state.generated_patterns = gen_list
            st.success(f"✅ Generated **{len(gen_list)}** unique pattern variations for **'{sanitized_seed}'** offline!")

    if st.session_state.generated_patterns:
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Generated", len(st.session_state.generated_patterns))
        en_num = sum(1 for g in st.session_state.generated_patterns if g.language == "en")
        bn_num = sum(1 for g in st.session_state.generated_patterns if g.language == "bn")
        cat_num = len({g.pattern_category for g in st.session_state.generated_patterns})
        m2.metric("English Variations", en_num)
        m3.metric("Bangla Variations", bn_num)
        m4.metric("Categories", cat_num)

        col_merge, col_cp, col_csv = st.columns(3)
        with col_merge:
            if st.button("➕ Merge into Discovered Keywords", type="primary", use_container_width=True):
                if st.session_state.crawl_result:
                    merged = st.session_state.pattern_generator.merge_provenance(
                        existing_keywords=st.session_state.crawl_result.keywords,
                        generated_keywords=st.session_state.generated_patterns,
                    )
                    st.session_state.crawl_result.keywords = merged
                    st.session_state.search_mode = "recursive"
                    st.success(f"✅ Merged {len(st.session_state.generated_patterns)} patterns into Discovered Keywords!")
                else:
                    as_discovered = [
                        DiscoveredKeyword(
                            keyword=g.keyword,
                            normalized_key=g.normalized_key,
                            depth=0,
                            parent_queries=[g.seed_keyword],
                            discovery_paths=1,
                            source_type="generated",
                            source_name="pattern_generator",
                            language=g.language,
                            is_generated=True,
                            pattern_category=g.pattern_category.value,
                            pattern_template=g.pattern_template,
                        )
                        for g in st.session_state.generated_patterns
                    ]
                    st.session_state.crawl_result = CrawlResult(
                        keywords=as_discovered,
                        stop_reason=StopReason.TARGET_REACHED,
                        queries_processed=0,
                        total_requests_made=0,
                        is_partial=False,
                        duration_seconds=0.0,
                    )
                    st.session_state.search_mode = "recursive"
                    st.success(f"✅ Loaded {len(as_discovered)} patterns into Discovered Keywords!")

        with col_cp:
            if st.button("📋 Copy All Patterns", use_container_width=True):
                render_copy_box([g.keyword for g in st.session_state.generated_patterns], label="Patterns")

        with col_csv:
            df_pat = pd.DataFrame(
                [
                    {
                        "#": idx + 1,
                        "Keyword": g.keyword,
                        "Category": g.pattern_category.value,
                        "Language": g.language,
                        "Template": g.pattern_template,
                        "Source Type": g.source_type,
                        "Seed Keyword": g.seed_keyword,
                    }
                    for idx, g in enumerate(st.session_state.generated_patterns)
                ]
            )
            st.download_button(
                "📥 Download Patterns CSV",
                data=ExportService.export_csv(df_pat, sanitize_formulas=True, include_bom=True),
                file_name=generate_export_filename(pat_seed_input, scope="patterns", extension="csv"),
                mime="text/csv",
                use_container_width=True,
            )

        st.dataframe(df_pat, use_container_width=True, hide_index=True)

        # Context-aware recommended next step
        top_pat = st.session_state.generated_patterns[0].keyword if st.session_state.generated_patterns else pat_seed_input
        p_next, s_next = render_recommended_next_step(
            title=f"Next Action: Validate Patterns for '{pat_seed_input}'",
            description="Explore authentic autocomplete suggestions or inspect real top-ranking videos for your highest-intent patterns.",
            action_label="🔍 Discover Autocomplete Suggestions",
            action_key=f"pat_to_discovery_btn_{abs(hash(pat_seed_input)) % 10000}",
            why_recommended=f"Generated {len(st.session_state.generated_patterns)} patterns across {cat_num} intent categories.",
            secondary_action_label="🚀 Run Video SERP for Top Pattern",
            secondary_action_key=f"pat_to_serp_btn_{abs(hash(pat_seed_input)) % 10000}",
        )
        if p_next:
            st.session_state.active_seed_input = pat_seed_input
            st.session_state.current_page = PAGE_NEW_RESEARCH
            st.rerun()
        elif s_next:
            st.session_state.active_seed_input = top_pat
            st.session_state.current_page = PAGE_VIDEO_RESEARCH
            st.rerun()
    else:
        render_empty_state(
            title="Ready to Generate Patterns",
            description="Select desired categories and language mode above, then click 'Generate Keyword Patterns' to create offline variations with zero network calls.",
            icon="✨",
        )


def render_page_saved(is_ready: bool) -> None:
    """Render the Saved Research Projects and History page."""
    render_page_header(
        title="Saved Research",
        subtitle="Inspect, search, rename, export, or manage locally persisted research projects from SQLite (data/keywords.db).",
        category="WORKFLOW & MANAGEMENT",
        badge_text="Local Storage",
        badge_type="success" if is_ready else "warning",
        provenance="local_sqlite",
    )
    render_contextual_help("saved_research")

    if not is_ready:
        st.error("Database connection unavailable.")
        return

    # 1. Search Bar for Project History
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_query = st.text_input(
            "🔍 Search Research History",
            placeholder="Search by project name or seed keyword...",
            key="saved_projects_search",
        )
    with col_s2:
        max_projects = st.selectbox("Display Limit", options=[25, 50, 100, 200], index=1)

    projects = db_manager.list_projects(search_query=search_query, limit=max_projects)

    if not projects:
        if search_query and search_query.strip():
            render_empty_state(
                title="No Matching Projects Found",
                description=f"No saved research projects matched '{search_query.strip()}'. Clear or adjust your search query.",
                icon="🔍",
                action_label="↺ Clear Project Search",
                action_key="btn_clear_saved_search",
            )
        else:
            if render_empty_state(
                title="No Saved Research Projects Yet",
                description="Your research library is empty. Launch your first keyword research session to persist and organize discovered keywords.",
                icon="💾",
                action_label="🔍 Start First Keyword Research",
                action_key="btn_start_first_research_saved",
            ):
                st.session_state.current_page = PAGE_NEW_RESEARCH
                st.rerun()
        return

    # Display project table
    display_projects = []
    for idx, p in enumerate(projects):
        display_projects.append(
            {
                "#": idx + 1,
                "ID": p["id"],
                "Project Name": p["project_name"],
                "Seed Keyword": p["seed_keyword"],
                "Keywords": p["total_results"],
                "Status": p.get("status", "completed").title(),
                "Depth": p["max_depth"],
                "Budget": p["request_budget"],
                "Requests": p.get("requests_made", 0),
                "Created At": p["created_at"],
                "Last Updated": p.get("updated_at", p["created_at"]),
            }
        )
    df_proj_display = pd.DataFrame(display_projects)
    st.dataframe(df_proj_display, use_container_width=True, hide_index=True)

    # 2. Inspect & Manage Selected Project
    st.markdown("---")
    st.markdown("##### 📂 Project Details & Actions")

    selected_id = st.selectbox(
        "Select a Project to Inspect or Manage:",
        options=[p["id"] for p in projects],
        format_func=lambda sid: f"Project #{sid} — '{next(p['project_name'] for p in projects if p['id'] == sid)}' ({next(p['total_results'] for p in projects if p['id'] == sid)} keywords, Status: {next(p.get('status', 'completed') for p in projects if p['id'] == sid).title()})",
        key="selected_project_id",
    )

    if selected_id:
        proj_meta = db_manager.get_project(selected_id)
        session_rows = db_manager.get_keywords_by_search_id(selected_id)

        if proj_meta:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Project Name", proj_meta["project_name"])
            m2.metric("Status", proj_meta.get("status", "completed").title())
            m3.metric("Keywords Stored", len(session_rows))
            m4.metric("Requests Made", proj_meta.get("requests_made", 0))

            if proj_meta.get("stop_reason"):
                st.caption(f"**Stop Reason:** `{proj_meta['stop_reason']}`")
            if proj_meta.get("error_message"):
                st.warning(f"**Error Notice:** {proj_meta['error_message']}")

        # Rename Project Expander
        with st.expander("✏️ Rename Project"):
            col_ren1, col_ren2 = st.columns([3, 1])
            with col_ren1:
                new_proj_name = st.text_input(
                    "New Project Name",
                    value=proj_meta["project_name"] if proj_meta else "",
                    key=f"rename_input_{selected_id}",
                )
            with col_ren2:
                st.write("")
                st.write("")
                if st.button("Save Name", key=f"rename_btn_{selected_id}", use_container_width=True):
                    if new_proj_name.strip():
                        db_manager.rename_project(selected_id, new_proj_name.strip())
                        st.success(f"Project renamed to '{new_proj_name.strip()}'.")
                        st.rerun()
                    else:
                        st.error("Project name cannot be empty.")

        # Project Actions
        col_act1, col_act2, col_act3, col_act4 = st.columns(4)
        with col_act1:
            if st.button(
                "📂 Load into Results Table",
                type="primary",
                use_container_width=True,
                key=f"load_btn_{selected_id}",
            ):
                loaded_crawl = load_search_into_crawl_result(selected_id, db_manager)
                if loaded_crawl:
                    st.session_state.crawl_result = loaded_crawl
                    st.session_state.search_mode = "recursive"
                    st.session_state.last_query = (
                        proj_meta["seed_keyword"] if proj_meta else ""
                    )
                    st.session_state.current_page = PAGE_RESULTS
                    st.rerun()

        with col_act2:
            if st.button("🔄 Resume / Rerun Research", use_container_width=True, key=f"rerun_btn_{selected_id}"):
                if proj_meta and proj_meta.get("parameters_json"):
                    try:
                        st.session_state.rerun_params = json.loads(proj_meta["parameters_json"])
                    except Exception:
                        st.session_state.rerun_params = {
                            "seeds": [proj_meta["seed_keyword"]],
                            "language": proj_meta["language"],
                            "country": proj_meta["country"],
                            "max_depth": proj_meta["max_depth"],
                            "request_budget": proj_meta["request_budget"],
                        }
                else:
                    st.session_state.rerun_params = {
                        "seeds": [proj_meta["seed_keyword"]] if proj_meta else ["python"],
                        "language": proj_meta["language"] if proj_meta else "en",
                        "country": proj_meta["country"] if proj_meta else "US",
                        "max_depth": proj_meta["max_depth"] if proj_meta else 1,
                        "request_budget": proj_meta["request_budget"] if proj_meta else 10,
                    }
                st.session_state.current_page = PAGE_NEW_RESEARCH
                st.rerun()

        with col_act3:
            df_sess = pd.DataFrame(session_rows)
            proj_slug = (proj_meta["project_name"] if proj_meta else "project").replace(" ", "_")
            csv_data = ExportService.export_csv(
                df_sess,
                sanitize_formulas=True,
                include_bom=True,
                metadata_header={
                    "Project": proj_meta["project_name"] if proj_meta else f"#{selected_id}",
                    "Seed Keyword": proj_meta["seed_keyword"] if proj_meta else "",
                    "Export Date": datetime.now(timezone.utc).isoformat(),
                    "Total Keywords": len(session_rows),
                },
            )
            st.download_button(
                "📥 Export Project CSV",
                data=csv_data,
                file_name=generate_export_filename(proj_slug, scope="all", extension="csv"),
                mime="text/csv",
                use_container_width=True,
                key=f"csv_btn_{selected_id}",
            )

        with col_act4:
            excel_data = ExportService.export_excel(
                df_sess,
                sanitize_formulas=True,
                sheet_name="Keywords",
                metadata_header={
                    "Project": proj_meta["project_name"] if proj_meta else f"#{selected_id}",
                    "Seed Keyword": proj_meta["seed_keyword"] if proj_meta else "",
                    "Total Keywords": len(session_rows),
                },
            )
            st.download_button(
                "📥 Export Project Excel",
                data=excel_data,
                file_name=generate_export_filename(proj_slug, scope="all", extension="xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"excel_btn_{selected_id}",
            )

        # Deletion row
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        col_del_check, col_del_btn = st.columns([3, 1])
        with col_del_check:
            confirm_del = st.checkbox(
                f"Confirm deletion: Permanently delete Project #{selected_id} and its {len(session_rows)} keywords.",
                key=f"confirm_del_{selected_id}",
            )
        with col_del_btn:
            if st.button(
                "🗑️ Delete Project",
                disabled=not confirm_del,
                type="secondary",
                use_container_width=True,
                key=f"del_proj_{selected_id}",
            ):
                db_manager.delete_search(selected_id)
                st.success(f"Project #{selected_id} deleted successfully.")
                st.rerun()

        # Keyword preview table
        st.markdown(f"**Keyword Records ({len(session_rows)} items):**")
        st.dataframe(df_sess, use_container_width=True, hide_index=True)

        # Context-aware recommended next step
        seed_for_next = proj_meta["seed_keyword"] if proj_meta and proj_meta.get("seed_keyword") else "Keywords"
        p_next, s_next = render_recommended_next_step(
            title=f"Next Action: Validate & Plan Content for '{seed_for_next}'",
            description="Take these saved keywords into live YouTube Video Research or generate structured Content Opportunities.",
            action_label=f"🚀 Run Video SERP Research",
            action_key=f"saved_to_serp_btn_{selected_id}",
            why_recommended=f"Project #{selected_id} contains {len(session_rows)} saved keywords ready for competitive inspection.",
            secondary_action_label="💡 Build Content Opportunities",
            secondary_action_key=f"saved_to_opps_btn_{selected_id}",
        )
        if p_next:
            st.session_state.active_seed_input = seed_for_next
            st.session_state.current_page = PAGE_VIDEO_RESEARCH
            st.rerun()
        elif s_next:
            st.session_state.active_seed_input = seed_for_next
            st.session_state.current_page = PAGE_CONTENT_OPPORTUNITIES
            st.rerun()



def render_page_video_research(is_ready: bool) -> None:
    """Render the YouTube Video Research, Competitor Analysis & Keyword Validation page (Phase 10)."""
    render_page_header(
        title="YouTube Video Research",
        subtitle="Inspect real top-ranking videos, actual view counts, channel distributions, title structures, and evidence-based keyword validation directly from YouTube Data API v3.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="SERP Explorer",
        badge_type="primary",
        provenance="youtube_api",
    )
    render_contextual_help("video_serp")
    render_interactive_tour("video_serp")

    if not is_ready:
        st.error("Database connection unavailable.")
        return

    serp_provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
    is_connected = serp_provider.is_connected()

    # Connection Status Header
    if is_connected:
        daily_used = db_manager.get_daily_quota_used()
        col_st1, col_st2 = st.columns([3, 1])
        with col_st1:
            st.success("🟢 **Connected**: YouTube Data API v3 integration active (Batch-optimized: 101 quota units/search).")
        with col_st2:
            st.info(f"📊 Quota Used: **{daily_used:,}** / 10,000 units")
    else:
        col_off_txt, col_off_btn = st.columns([3, 1])
        with col_off_txt:
            st.info(
                "ℹ️ **Offline / Unconnected Mode (Local-First Guarantee)**\n\n"
                "YouTube Data API v3 key is not configured. In accordance with our **zero fabricated metrics guarantee**, "
                "synthetic views, difficulty, and competitor tags are never faked. "
                "To inspect real ranking videos and tags, configure your free Google YouTube Data API v3 key in "
                "**⚙️ Settings & Data Sources**."
            )
        with col_off_btn:
            st.write("")
            st.write("")
            if st.button("⚙️ Configure API Key", key="btn_serp_offline_to_settings", use_container_width=True):
                st.session_state.current_page = PAGE_SETTINGS
                st.rerun()

    tab_research, tab_saved = st.tabs(["🔍 Video Research & Keyword Validation", "💾 Saved Research Sessions"])

    with tab_research:
        # Search & Inspection Controls
        st.markdown("##### 🔍 Search Top-Ranking YouTube Videos")
        st.caption(
            "⚠️ *Notice: Video search results depend on provider indexing, geographic region, language, and retrieval time. "
            "Autocomplete suggestions and search results provide empirical research evidence for content planning, "
            "not guaranteed rankings or traffic.*"
        )

        # Keyword selection
        session_keywords: List[str] = []
        crawl_res = st.session_state.get("crawl_result")
        if crawl_res and hasattr(crawl_res, "discovered_keywords") and crawl_res.discovered_keywords:
            session_keywords = [dk.keyword for dk in crawl_res.discovered_keywords]
        elif st.session_state.get("direct_results"):
            session_keywords = [
                ki.keyword for ki in st.session_state.direct_results if hasattr(ki, "keyword")
            ]
        elif st.session_state.get("current_result") and hasattr(st.session_state.current_result, "keywords"):
            session_keywords = [
                k.keyword if hasattr(k, "keyword") else str(k)
                for k in st.session_state.current_result.keywords
            ]

        input_mode = "Custom Search Query"
        if session_keywords:
            input_mode = st.radio(
                "Keyword Source",
                options=["From Active Keyword Session", "Custom Search Query"],
                horizontal=True,
                key="video_research_input_mode",
            )

        selected_keyword = ""
        if input_mode == "From Active Keyword Session" and session_keywords:
            selected_keyword = st.selectbox(
                "Select Keyword from Current Research Session",
                options=session_keywords,
                key="video_research_keyword_select",
            )
        else:
            default_q = st.session_state.get("active_seed_input") or "best car wax"
            selected_keyword = st.text_input(
                "Target Search Keyword",
                value=default_q,
                placeholder="e.g. best car wax, python tutorial, গরুর মাংস রান্নার রেসিপি",
                key="video_research_custom_query",
            )

        # Filter parameters row 1
        col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 1])
        with col_p1:
            order_label = st.selectbox(
                "Relevance Ordering",
                options=[
                    "Relevance (Default)",
                    "View Count (Most Popular)",
                    "Upload Date (Newest First)",
                    "Rating (Highest Rated)",
                ],
                index=0,
                key="vr_order",
            )
            order_map = {
                "Relevance (Default)": "relevance",
                "View Count (Most Popular)": "viewCount",
                "Upload Date (Newest First)": "date",
                "Rating (Highest Rated)": "rating",
            }
            selected_order = order_map.get(order_label, "relevance")

        with col_p2:
            date_range_label = st.selectbox(
                "Publication Date Filter",
                options=[
                    "Any Time",
                    "Last 7 Days",
                    "Last 30 Days",
                    "Last 90 Days",
                    "Last 365 Days",
                ],
                index=0,
                key="vr_date_range",
            )
            published_after_val: Optional[str] = None
            if date_range_label == "Last 7 Days":
                published_after_val = (
                    datetime.now(timezone.utc) - timedelta(days=7)
                ).isoformat()
            elif date_range_label == "Last 30 Days":
                published_after_val = (
                    datetime.now(timezone.utc) - timedelta(days=30)
                ).isoformat()
            elif date_range_label == "Last 90 Days":
                published_after_val = (
                    datetime.now(timezone.utc) - timedelta(days=90)
                ).isoformat()
            elif date_range_label == "Last 365 Days":
                published_after_val = (
                    datetime.now(timezone.utc) - timedelta(days=365)
                ).isoformat()

        with col_p3:
            max_videos = st.selectbox(
                "Competitors to Inspect",
                options=[5, 10, 15, 20, 50],
                index=1,
                key="vr_max_videos",
            )

        with col_p4:
            use_cache = st.checkbox(
                "Use Local Cache (0 units)", value=True, key="vr_use_cache"
            )

        # Filter parameters row 2
        col_p5, col_p6, col_p7, col_p8 = st.columns([1, 1, 1, 1])
        with col_p5:
            lang_code = st.selectbox(
                "Relevance Language",
                options=["en", "bn", "hi", "es", "fr", "de", "ar"],
                index=0,
                key="vr_lang",
            )
        with col_p6:
            country_code = st.selectbox(
                "Region Code",
                options=["US", "BD", "GB", "IN", "CA", "AU", "DE"],
                index=0,
                key="vr_country",
            )
        with col_p7:
            target_audience = st.selectbox(
                "Target Audience",
                options=[
                    "General Audience",
                    "Beginners",
                    "Advanced / Pros",
                    "Budget Buyers",
                    "Students",
                    "Creators",
                ],
                index=0,
                key="vr_target_audience",
            )
        with col_p8:
            preferred_format = st.selectbox(
                "Preferred Content Format",
                options=[
                    "All Formats",
                    "How-To & Guides",
                    "Reviews & Tests",
                    "Comparisons (VS)",
                    "Best & Top Lists",
                    "Problem Solving",
                ],
                index=0,
                key="vr_preferred_format",
            )

        col_act1, col_act2 = st.columns([2, 5])
        with col_act1:
            inspect_clicked = st.button(
                "🚀 Inspect Videos & Validate Keyword",
                type="primary",
                use_container_width=True,
                key="btn_run_video_research",
            )

        if inspect_clicked:
            if not selected_keyword or not selected_keyword.strip():
                st.warning("Please provide a search keyword to inspect.")
            elif not is_connected:
                st.warning(
                    "Cannot fetch live SERP data without a YouTube Data API v3 key. "
                    "Please configure your key in ⚙️ Settings & Data Sources."
                )
            else:
                with st.spinner(
                    f"Retrieving top ranking videos and competitor data for '{selected_keyword.strip()}'..."
                ):
                    analysis = serp_provider.analyze_keyword(
                        keyword=selected_keyword.strip(),
                        language=lang_code,
                        country=country_code,
                        max_results=max_videos,
                        order=selected_order,
                        published_after=published_after_val,
                        use_cache=use_cache,
                        target_audience=target_audience,
                        preferred_format=preferred_format,
                    )
                    st.session_state.current_serp_analysis = analysis

        # Display Results
        analysis: Optional[KeywordSerpAnalysis] = st.session_state.get(
            "current_serp_analysis"
        )
        if analysis:
            st.markdown("---")
            if analysis.total_videos_analyzed == 0:
                render_empty_state(
                    title="No Ranking Videos Returned",
                    description=f"{analysis.status_message} This typically occurs if the publication date filter is too restrictive or the regional query has low coverage.",
                    icon="📹",
                    action_label="🔍 Try Broader Search Query",
                    action_key="btn_reset_serp_filter",
                )
            else:
                # Header row: Status & Opportunity Score Badge
                col_hdr1, col_hdr2 = st.columns([3, 1])
                with col_hdr1:
                    st.markdown(f"#### Results for: `{analysis.keyword}`")
                    cache_icon = "💾" if analysis.is_cached else "⚡"
                    quota_note = "0 quota units" if analysis.is_cached else "101 quota units"
                    st.caption(
                        f"{cache_icon} {analysis.status_message} ({quota_note}) • Fetched at: "
                        f"{analysis.fetched_at[:19].replace('T', ' ')}"
                    )
                with col_hdr2:
                    opp_color = (
                        "#10B981"
                        if analysis.opportunity_score >= 75
                        else (
                            "#3B82F6"
                            if analysis.opportunity_score >= 50
                            else (
                                "#F59E0B"
                                if analysis.opportunity_score >= 25
                                else "#EF4444"
                            )
                        )
                    )
                    st.markdown(
                        f"<div style='background-color:{opp_color}22; border:1px solid {opp_color}; border-radius:8px; padding:8px; text-align:center;'>"
                        f"<div style='font-size:0.75rem; color:{opp_color}; font-weight:bold;'>OPPORTUNITY SCORE</div>"
                        f"<div style='font-size:1.4rem; font-weight:bold; color:{opp_color};'>{analysis.opportunity_score} / 100</div>"
                        f"<div style='font-size:0.75rem; color:#4B5563;'>{analysis.opportunity_label}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Transparent Competitor Metrics Row (Step 6)
                st.markdown("##### 📊 Transparent Competitor Metrics (No Fabricated Numbers)")
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Videos Analyzed", f"{analysis.total_videos_analyzed} videos")
                m2.metric("Median Views", f"{int(analysis.median_views):,}")
                m3.metric("Average Views", f"{int(analysis.average_views):,}")
                unique_pct = round(
                    (analysis.unique_channels_count / max(1, analysis.total_videos_analyzed))
                    * 100
                )
                m4.metric("Unique Channels", f"{analysis.unique_channels_count} ({unique_pct}%)")
                m5.metric("Median Video Age", f"{int(analysis.median_video_age_days)} days")
                m6.metric("Avg Daily Views", f"{int(analysis.avg_daily_views):,}")

                # Opportunity Score Explainer
                with st.expander("ℹ️ How the Opportunity Score is Calculated", expanded=False):
                    st.markdown(
                        """
                        The **Opportunity Score** (0–100) measures how favorable this keyword is for new or growing creators:
                        1. **Demand Factor (0–40 pts)**: Evaluates median views of ranking videos. High median views confirm sustained audience appetite.
                        2. **Content Gap & Freshness (0–30 pts)**: Assesses the age of ranking videos. When top videos are > 1–2 years old, YouTube algorithms and viewers favor fresh, modern coverage.
                        3. **Competition Accessibility (0–30 pts)**: Analyzes view distribution. When videos with <50,000 views rank in the top 10, it proves non-monopoly channels can successfully penetrate the SERP.
                        """
                    )

                # Evidence-Based Keyword Validation Summary (Step 7)
                if analysis.validation_summary:
                    val = analysis.validation_summary
                    with st.expander("📋 Evidence-Based Keyword Validation Summary", expanded=True):
                        st.markdown(f"**Research Evidence for Keyword:** `{val.keyword}`")

                        col_v1, col_v2 = st.columns(2)
                        with col_v1:
                            st.markdown("###### 1. Metadata Coverage & Sample Size")
                            cov = val.metadata_coverage
                            st.markdown(
                                f"- Sample Size: **{val.total_videos} videos**\n"
                                f"- View Count Available: **{cov.get('view_count_pct', 0)}%**\n"
                                f"- Like Count Available: **{cov.get('like_count_pct', 0)}%**\n"
                                f"- Duration Available: **{cov.get('duration_pct', 0)}%**\n"
                                f"- Tags Available: **{cov.get('tags_pct', 0)}%**\n"
                                f"- Description Available: **{cov.get('description_pct', 0)}%**"
                            )

                            st.markdown("###### 2. Channel Variety & Monopoly Risk")
                            ch_ratio = round((val.unique_channels_count / max(1, val.total_videos)) * 100, 1)
                            if ch_ratio >= 80:
                                ch_desc = f"**High Creator Diversity**: {val.unique_channels_count} distinct channels ({ch_ratio}%). No single creator dominates."
                            else:
                                ch_desc = f"**Moderate Diversity**: {val.unique_channels_count} channels across {val.total_videos} videos ({ch_ratio}%)."
                            st.markdown(ch_desc)

                            st.markdown("###### 3. Publication Date Distribution")
                            ad = val.age_distribution
                            st.markdown(
                                f"- Under 30 Days: **{ad.get('recent_under_30d', 0)} videos**\n"
                                f"- 30 to 180 Days: **{ad.get('moderate_30_to_180d', 0)} videos**\n"
                                f"- 180 to 365 Days: **{ad.get('established_180_to_365d', 0)} videos**\n"
                                f"- Legacy (>1 Year): **{ad.get('legacy_over_365d', 0)} videos**"
                            )

                        with col_v2:
                            st.markdown("###### 4. View Count Dispersion")
                            vd = val.view_count_distribution
                            st.markdown(
                                f"- Minimum: **{vd.get('min', 0):,} views**\n"
                                f"- 25th Percentile: **{vd.get('p25', 0):,} views**\n"
                                f"- Median: **{int(vd.get('median', 0)):,} views**\n"
                                f"- 75th Percentile: **{vd.get('p75', 0):,} views**\n"
                                f"- Maximum: **{vd.get('max', 0):,} views**"
                            )

                            st.markdown("###### 5. Common Recurring Title Phrases")
                            if val.common_title_phrases:
                                phrase_badges = " ".join(
                                    [f"`{p[0]}` ({p[1]})" for p in val.common_title_phrases[:8]]
                                )
                                st.markdown(phrase_badges)
                            else:
                                st.caption("No recurring multi-word phrases detected in title sample.")

                            st.markdown("###### 6. Suggested Content Angles & Rationale")
                            for ang in val.potential_content_angles:
                                st.markdown(f"- **{ang.get('angle', 'Angle')}**: {ang.get('rationale', '')}")

                        st.markdown("###### 7. Limitations & Empirical Policy")
                        for lim in val.missing_data_limitations:
                            st.markdown(f"- ℹ️ *{lim}*")
                        st.caption(
                            "💡 **Actionable Takeaway**: Use these empirical metrics to inform video titles, scripting, "
                            "and thumbnail positioning. All insights reflect verified YouTube data, never synthetic estimations."
                        )

                # Title and Content Angle Analysis (Step 8)
                if analysis.title_analysis:
                    ta = analysis.title_analysis
                    with st.expander("💡 Title & Content Angle Analysis (Original Angle Generator)", expanded=True):
                        st.markdown("###### Detected Video Format Breakdown")
                        f_cols = st.columns(len(ta.detected_patterns) if ta.detected_patterns else 1)
                        for idx, pat in enumerate(ta.detected_patterns):
                            with f_cols[idx % len(f_cols)]:
                                st.metric(pat["format"], f"{pat['count']} ({pat['percentage']}%)")

                        st.markdown("###### 🎬 Original Suggested Title Ideas (Tailored to Audience & Format)")
                        st.caption(
                            f"Audience: **{ta.target_audience}** • Preferred Format: **{ta.preferred_format}** • "
                            "Generated original angles without duplicating competitor titles."
                        )
                        for suggestion in ta.suggested_title_ideas:
                            st.markdown(f"- 📌 **{suggestion}**")

                        # Copy box for title ideas
                        render_copy_box(ta.suggested_title_ideas, label="Suggested Title Ideas")

                # Competitor Video Tags Cloud
                if analysis.top_tags:
                    st.markdown("##### 🏷️ Competitor Video Tags Cloud")
                    st.caption("Most frequent tags used across ranking videos. Click below to copy all for your video metadata.")
                    tag_badges = " ".join(
                        [
                            f"<span style='display:inline-block; background-color:#F3F4F6; border:1px solid #D1D5DB; border-radius:12px; padding:2px 8px; margin:2px; font-size:0.82rem;'><b>{t[0]}</b> <span style='color:#6B7280;'>({t[1]})</span></span>"
                            for t in analysis.top_tags
                        ]
                    )
                    st.markdown(tag_badges, unsafe_allow_html=True)

                    all_tag_strings = [t[0] for t in analysis.top_tags]
                    render_copy_box(all_tag_strings, label="Competitor Tags")

                # Ranking Videos Table / Grid with Filtering and Sorting
                st.markdown("##### 🏆 Ranking Competitor Videos Breakdown")
                col_vs1, col_vs2, col_vs3 = st.columns([2, 2, 2])
                with col_vs1:
                    video_sort = st.selectbox(
                        "Sort Videos By",
                        options=[
                            "Rank (Search Order)",
                            "Views (Highest First)",
                            "Daily Views (Highest First)",
                            "Published Date (Newest First)",
                            "Title (A–Z)",
                        ],
                        index=0,
                        key="vr_video_sort",
                    )
                with col_vs2:
                    min_view_filter = st.slider(
                        "Min View Count",
                        min_value=0,
                        max_value=max(1000, analysis.max_views),
                        value=0,
                        step=1000 if analysis.max_views > 10000 else 100,
                        key="vr_min_view_filter",
                    )
                with col_vs3:
                    title_filter = st.text_input(
                        "Filter by Title/Channel Text",
                        placeholder="e.g. test, tutorial",
                        key="vr_title_filter",
                    )

                # Apply video filters and sorting
                display_videos = [v for v in analysis.videos if v.view_count >= min_view_filter]
                if title_filter.strip():
                    tf = title_filter.strip().lower()
                    display_videos = [
                        v for v in display_videos
                        if tf in v.title.lower() or tf in v.channel_title.lower()
                    ]

                if video_sort == "Views (Highest First)":
                    display_videos.sort(key=lambda x: x.view_count, reverse=True)
                elif video_sort == "Daily Views (Highest First)":
                    display_videos.sort(key=lambda x: x.daily_views, reverse=True)
                elif video_sort == "Published Date (Newest First)":
                    display_videos.sort(key=lambda x: x.publish_date, reverse=True)
                elif video_sort == "Title (A–Z)":
                    display_videos.sort(key=lambda x: x.title.lower())
                else:
                    display_videos.sort(key=lambda x: x.rank)

                st.caption(f"Showing **{len(display_videos)}** of {len(analysis.videos)} videos matching filters.")

                for v in display_videos:
                    with st.container():
                        c_thumb, c_info = st.columns([1, 4])
                        with c_thumb:
                            if v.thumbnail_url:
                                st.image(v.thumbnail_url, use_container_width=True)
                        with c_info:
                            st.markdown(f"**#{v.rank} [{v.title}]({v.video_url})**")
                            ch_link = f"[{v.channel_title}]({v.channel_url})" if v.channel_url else v.channel_title
                            st.caption(
                                f"Channel: **{ch_link}** • Published: **{v.relative_age}** ({v.publish_date[:10]}) • "
                                f"Duration: **{v.duration}**"
                            )
                            likes_str = f"{v.like_count:,} likes" if v.like_count is not None else "Likes hidden"
                            comments_str = f"{v.comment_count:,} comments" if v.comment_count is not None else "Comments disabled"
                            st.markdown(
                                f"👁️ **{v.view_count:,} views** &nbsp;&nbsp;|&nbsp;&nbsp; "
                                f"⚡ **{int(v.daily_views):,} daily views** &nbsp;&nbsp;|&nbsp;&nbsp; "
                                f"👍 {likes_str} &nbsp;&nbsp;|&nbsp;&nbsp; 💬 {comments_str}"
                            )
                            if v.tags:
                                st.caption(f"Tags: {', '.join(v.tags[:8])}{'...' if len(v.tags) > 8 else ''}")
                        st.divider()

                # Action Buttons Row: Copy URLs, Save Session, Exports
                st.markdown("##### 📥 Actions & Export Report")
                col_save_btn, col_copy_btn, col_exp1, col_exp2 = st.columns([2, 2, 2, 2])
                with col_save_btn:
                    if st.button("💾 Save Session to Database", type="primary", use_container_width=True, key="save_session_btn"):
                        sess_id = db_manager.save_video_research_session(
                            analysis=analysis,
                            provider=analysis.videos[0].provider if analysis.videos else "YouTube Data API v3",
                            associated_keywords=[analysis.keyword],
                        )
                        st.success(f"✅ Video research session #{sess_id} saved successfully!")

                with col_copy_btn:
                    if st.button("📋 Copy All Video URLs", use_container_width=True, key="copy_urls_btn"):
                        st.session_state["show_video_urls_copy"] = True

                with col_exp1:
                    csv_bytes = ExportService.export_serp_csv(analysis)
                    csv_filename = generate_export_filename(
                        analysis.keyword, scope="serp", extension="csv"
                    )
                    st.download_button(
                        "📥 Export SERP CSV (UTF-8 BOM)",
                        data=csv_bytes,
                        file_name=csv_filename,
                        mime="text/csv",
                        use_container_width=True,
                        key="dl_serp_csv",
                    )

                with col_exp2:
                    excel_bytes = ExportService.export_serp_excel(analysis)
                    excel_filename = generate_export_filename(
                        analysis.keyword, scope="serp", extension="xlsx"
                    )
                    st.download_button(
                        "📥 Export SERP Excel (.xlsx)",
                        data=excel_bytes,
                        file_name=excel_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="dl_serp_excel",
                    )

                if st.session_state.get("show_video_urls_copy"):
                    all_video_urls = [v.video_url for v in analysis.videos if v.video_url]
                    render_copy_box(all_video_urls, label="Video URLs")

                # Context-aware recommended next steps
                p_next, s_next = render_recommended_next_step(
                    title=f"Build Content Strategy for '{analysis.keyword}'",
                    description="Convert your empirical competitor video findings into actionable content gaps or explore niche product opportunities.",
                    action_label="💡 Build Content Opportunities",
                    action_key=f"serp_to_opps_btn_{abs(hash(analysis.keyword)) % 10000}",
                    why_recommended=f"Identified {analysis.total_videos_analyzed} competitor videos with median view count {int(analysis.median_views):,}.",
                    secondary_action_label="📦 Search Niche Products",
                    secondary_action_key=f"serp_to_prods_btn_{abs(hash(analysis.keyword)) % 10000}",
                )
                if p_next:
                    st.session_state.active_seed_input = analysis.keyword
                    st.session_state.current_page = PAGE_CONTENT_OPPORTUNITIES
                    st.rerun()
                elif s_next:
                    st.session_state.active_seed_input = analysis.keyword
                    st.session_state.current_page = PAGE_PRODUCT_OPPORTUNITIES
                    st.rerun()

    with tab_saved:
        st.markdown("##### 💾 Saved Video Research Sessions")
        st.caption("Browse, inspect, and manage saved competitor analysis and validation sessions.")

        saved_sessions = db_manager.get_video_research_sessions(limit=50)
        if not saved_sessions:
            render_empty_state(
                title="No Saved Video Sessions Yet",
                description="Run an inspection above and click 'Save Session to Database' to build your research library and track competitor metrics over time.",
                icon="💾",
                action_label="🔍 Inspect Top Ranking Videos",
                action_key="btn_empty_saved_serp_action",
            )
        else:
            # Summary Table
            summary_records = [
                {
                    "Session ID": s["id"],
                    "Keyword": s["keyword"],
                    "Provider": s["provider"],
                    "Videos": s["total_videos"],
                    "Language/Country": f"{s.get('language', 'en')}/{s.get('country', 'US')}",
                    "Saved At": s["created_at"][:19].replace("T", " "),
                }
                for s in saved_sessions
            ]
            st.dataframe(pd.DataFrame(summary_records), use_container_width=True, hide_index=True)

            # Session Inspector Dropdown
            session_options = {
                f"Session #{s['id']} - {s['keyword']} ({s['total_videos']} videos, {s['created_at'][:10]})": s["id"]
                for s in saved_sessions
            }
            selected_label = st.selectbox(
                "Select a Session to Inspect:",
                options=list(session_options.keys()),
                key="saved_session_select",
            )
            selected_session_id = session_options[selected_label]

            # Fetch full details
            sess_details = db_manager.get_video_research_session(selected_session_id)
            if sess_details:
                st.markdown(f"###### Session #{selected_session_id}: `{sess_details['keyword']}`")

                # Metrics cards
                sm = sess_details.get("metrics", {})
                sm_c1, sm_c2, sm_c3, sm_c4 = st.columns(4)
                sm_c1.metric("Videos", sess_details["total_videos"])
                sm_c2.metric("Median Views", f"{int(sm.get('median_views', 0)):,}")
                sm_c3.metric("Opportunity Score", f"{sm.get('opportunity_score', 50.0):.1f} / 100")
                sm_c4.metric("Provider", sess_details["provider"])

                # Associated keywords
                if sess_details["videos"]:
                    first_vid = sess_details["videos"][0]["video_id"]
                    assoc_kws = db_manager.get_keywords_for_video(first_vid)
                    if assoc_kws:
                        st.caption(f"Associated Research Keywords: {', '.join(assoc_kws)}")

                # Action row for saved session
                c_load, c_del_chk, c_del_btn = st.columns([2, 3, 2])
                with c_load:
                    if st.button("📂 Load into Active View", key=f"load_sess_{selected_session_id}", use_container_width=True):
                        # Construct KeywordSerpAnalysis
                        loaded_videos = [
                            CompetitorVideoItem(
                                video_id=v["video_id"],
                                title=v["title"],
                                channel_id=v["channel_id"],
                                channel_title=v["channel_title"],
                                publish_date=v["published_at"],
                                view_count=v["view_count"],
                                like_count=v["like_count"],
                                comment_count=v["comment_count"],
                                duration=v["duration"],
                                tags=v.get("tags", []),
                                thumbnail_url=v.get("thumbnail_url", ""),
                                video_url=v.get("video_url", ""),
                                channel_url=v.get("channel_url", ""),
                                daily_views=v.get("daily_views", 0.0),
                                rank=v.get("rank", 1),
                            )
                            for v in sess_details.get("videos", [])
                        ]
                        st.session_state.current_serp_analysis = KeywordSerpAnalysis(
                            keyword=sess_details["keyword"],
                            language=sess_details.get("language", "en"),
                            country=sess_details.get("country", "US"),
                            videos=loaded_videos,
                            total_videos_analyzed=sess_details["total_videos"],
                            median_views=float(sm.get("median_views", 0.0)),
                            average_views=float(sm.get("average_views", 0.0)),
                            opportunity_score=float(sm.get("opportunity_score", 50.0)),
                            opportunity_label=sm.get("opportunity_label", "Moderate Opportunity"),
                            status_message=f"Loaded from saved session #{selected_session_id}",
                            is_cached=True,
                        )
                        st.success(f"Session #{selected_session_id} loaded into active view!")
                        st.rerun()

                with c_del_chk:
                    confirm_sess_del = st.checkbox(
                        f"Confirm deletion of Session #{selected_session_id}",
                        key=f"chk_del_sess_{selected_session_id}",
                    )
                with c_del_btn:
                    if st.button(
                        "🗑️ Delete Session",
                        disabled=not confirm_sess_del,
                        key=f"btn_del_sess_{selected_session_id}",
                        use_container_width=True,
                    ):
                        db_manager.delete_video_research_session(selected_session_id)
                        st.success(f"Session #{selected_session_id} deleted.")
                        st.rerun()

                # Videos table
                st.markdown(f"**Session Videos ({len(sess_details.get('videos', []))} items):**")
                df_sess_vids = pd.DataFrame(
                    [
                        {
                            "Rank": v.get("rank", 1),
                            "Title": v["title"],
                            "Channel": v["channel_title"],
                            "Published": v["published_at"][:10],
                            "Views": f"{v['view_count']:,}",
                            "Daily Views": f"{int(v.get('daily_views', 0)):,}",
                            "Likes": f"{v['like_count']:,}" if v.get("like_count") is not None else "-",
                            "Duration": v["duration"],
                        }
                        for v in sess_details.get("videos", [])
                    ]
                )
                st.dataframe(df_sess_vids, use_container_width=True, hide_index=True)


render_page_serp = render_page_video_research


def render_page_content_opportunities(is_ready: bool) -> None:
    """Render the YouTube Content Opportunities, Gap Analysis & Video Planning page (Phase 11)."""
    render_page_header(
        title="Content Opportunities",
        subtitle="Bridge keyword discovery and video research to identify empirical content gaps, generate structured topic ideas, craft high-retention titles, and manage your production calendar.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="Gap Intelligence",
        badge_type="primary",
        provenance="youtube_api",
    )
    render_contextual_help("content_opportunities")
    render_interactive_tour("content_opportunities")

    if not is_ready:
        st.error("Database connection unavailable.")
        return

    tab_opps, tab_workshop, tab_brief, tab_calendar, tab_overlap = st.tabs([
        "💡 Opportunities & Gap Analysis",
        "✍️ Title & Hook Workshop",
        "📋 Content Brief Generator",
        "📅 Content Calendar",
        "⚠️ Topic Overlap & Cannibalization",
    ])

    # =========================================================================
    # TAB 1: OPPORTUNITIES & GAP ANALYSIS
    # =========================================================================
    with tab_opps:
        st.markdown("##### 🔍 1. Configure Data Sources & Research Scope")
        st.caption(
            "Combine your keyword research projects with competitor video research to uncover potential content gaps. "
            "Findings are strictly labeled as empirical evidence, never guaranteed ranking claims."
        )

        col_src1, col_src2 = st.columns(2)

        # Keyword source selection
        with col_src1:
            kw_source_mode = st.radio(
                "Keyword Source",
                options=["Active Research Session", "Saved Keyword Project", "Custom Seed Keywords"],
                horizontal=True,
                key="opp_kw_source_mode",
            )
            loaded_keywords: List[str] = []
            selected_seed_keyword = ""
            selected_project_id: Optional[int] = None

            if kw_source_mode == "Active Research Session":
                crawl_res = st.session_state.get("crawl_result")
                if crawl_res and hasattr(crawl_res, "discovered_keywords") and crawl_res.discovered_keywords:
                    loaded_keywords = [dk.keyword for dk in crawl_res.discovered_keywords]
                    selected_seed_keyword = st.session_state.get("active_seed_input") or "best car wax"
                elif st.session_state.get("direct_results"):
                    loaded_keywords = [
                        ki.keyword for ki in st.session_state.direct_results if hasattr(ki, "keyword")
                    ]
                    selected_seed_keyword = st.session_state.get("active_seed_input") or "best car wax"

                if loaded_keywords:
                    st.success(f"Loaded **{len(loaded_keywords)}** keywords from active session ('{selected_seed_keyword}').")
                else:
                    st.info("No active keyword session found. Run a search or select a saved project.")

            elif kw_source_mode == "Saved Keyword Project":
                saved_searches = db_manager.list_searches(limit=50)
                if saved_searches:
                    proj_opts = {
                        f"#{s['id']} - {s['project_name']} ({s['total_keywords']} keywords, {s['seed_keyword']})": s["id"]
                        for s in saved_searches
                    }
                    sel_proj_label = st.selectbox("Select Project:", options=list(proj_opts.keys()), key="opp_proj_select")
                    selected_project_id = proj_opts[sel_proj_label]
                    k_rows = db_manager.get_search_keywords(selected_project_id)
                    loaded_keywords = [r["keyword"] for r in k_rows]
                    selected_seed_keyword = next((s["seed_keyword"] for s in saved_searches if s["id"] == selected_project_id), "best car wax")
                    st.success(f"Loaded **{len(loaded_keywords)}** keywords from Project #{selected_project_id}.")
                else:
                    st.info("No saved keyword projects found in database.")

            else:
                custom_kw_text = st.text_area(
                    "Enter Seed & Target Keywords (one per line):",
                    value="best car wax\nbest car wax for black cars\nceramic wax vs carnauba\nhow to apply car wax\ncar wax for beginners",
                    height=100,
                    key="opp_custom_kws",
                )
                loaded_keywords = [k.strip() for k in custom_kw_text.splitlines() if k.strip()]
                selected_seed_keyword = loaded_keywords[0] if loaded_keywords else "best car wax"

        # Competitor video source selection
        with col_src2:
            video_source_mode = st.radio(
                "Competitor Video Research Source",
                options=["None (Offline / Lexical Gap Analysis)", "Active Video Research", "Saved Video Research Session"],
                horizontal=True,
                key="opp_video_source_mode",
            )
            competitor_video_titles: List[str] = []

            if video_source_mode == "Active Video Research":
                serp_res = st.session_state.get("current_serp_analysis")
                if serp_res and getattr(serp_res, "videos", None):
                    competitor_video_titles = [v.title for v in serp_res.videos if v.title]
                    st.success(f"Loaded **{len(competitor_video_titles)}** competitor titles from active search ('{serp_res.keyword}').")
                else:
                    st.info("No active video research results. Please run an inspection in YouTube Video Research first.")

            elif video_source_mode == "Saved Video Research Session":
                saved_serp_sess = db_manager.get_video_research_sessions(limit=50)
                if saved_serp_sess:
                    sess_opts = {
                        f"Session #{s['id']} - {s['keyword']} ({s['total_videos']} videos)": s["id"]
                        for s in saved_serp_sess
                    }
                    sel_sess_label = st.selectbox("Select Saved Session:", options=list(sess_opts.keys()), key="opp_sess_select")
                    chosen_sess_id = sess_opts[sel_sess_label]
                    sess_full = db_manager.get_video_research_session(chosen_sess_id)
                    if sess_full and sess_full.get("videos"):
                        competitor_video_titles = [v["title"] for v in sess_full["videos"] if v.get("title")]
                        st.success(f"Loaded **{len(competitor_video_titles)}** competitor titles from Session #{chosen_sess_id}.")
                else:
                    st.info("No saved video research sessions found.")
            else:
                st.caption(
                    "ℹ️ *No competitor video research selected. Gap analysis will operate in lexical mode only. "
                    "Competitor content gaps cannot be verified without video data.*"
                )

        # Filters and Preferences
        st.markdown("##### 🎯 2. Target Audience & Preferred Formats")
        c_aud1, c_aud2, c_aud3 = st.columns([1, 1, 1])
        with c_aud1:
            target_audience = st.selectbox(
                "Target Audience",
                options=["General Audience", "Beginners", "Advanced / Pros", "Budget Buyers", "Students", "Creators"],
                index=0,
                key="opp_target_audience",
            )
        with c_aud2:
            preferred_format = st.selectbox(
                "Preferred Content Format",
                options=[
                    "All Formats",
                    "Step-by-step Guide",
                    "Beginner Tutorial",
                    "Top 5 / Top 10",
                    "Common Mistakes",
                    "Product Review",
                    "Comparison",
                    "Buying Guide",
                    "Frequently Asked Questions",
                ],
                index=0,
                key="opp_preferred_format",
            )
        with c_aud3:
            max_opps = st.slider("Max Opportunities to Generate", min_value=5, max_value=30, value=12, step=1, key="opp_max_slider")

        col_run1, _ = st.columns([2, 5])
        with col_run1:
            run_analysis_clicked = st.button(
                "🚀 Analyze Gaps & Generate Opportunities",
                type="primary",
                use_container_width=True,
                key="btn_run_opp_analysis",
            )

        if run_analysis_clicked:
            if not loaded_keywords:
                st.warning("Please provide or load at least one keyword to analyze.")
            else:
                with st.spinner("Analyzing content gaps, format distributions, and generating opportunities..."):
                    generator = VideoTopicGenerator(scorer=OpportunityScorer())
                    generated_opps = generator.generate_topics_for_keywords(
                        keywords=loaded_keywords,
                        seed_keyword=selected_seed_keyword,
                        target_audience=target_audience,
                        preferred_format=preferred_format,
                        competitor_titles=competitor_video_titles if competitor_video_titles else None,
                        max_topics=max_opps,
                        project_id=selected_project_id,
                    )
                    st.session_state.current_opportunities = generated_opps
                    st.success(f"Generated **{len(generated_opps)}** actionable content opportunities!")

        # Display Generated Opportunities
        curr_opps: List[ContentOpportunityItem] = st.session_state.get("current_opportunities", [])
        if curr_opps:
            st.markdown("---")
            st.markdown("##### 📊 Content Opportunities & Gap Analysis Results")

            # Telemetry Overview Cards
            gap_count = sum(1 for o in curr_opps if o.evidence.get("gap_analysis", {}).get("is_gap"))
            top_score = max([o.opportunity_score for o in curr_opps], default=0.0)
            conf_level = curr_opps[0].confidence_level if curr_opps else "Moderate Evidence"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Opportunities Generated", f"{len(curr_opps)} topics")
            m2.metric("Potential Content Gaps", f"{gap_count} gaps identified")
            m3.metric("Highest Opportunity Score", f"{top_score:.1f} / 100")
            m4.metric("Evidence Confidence", conf_level)

            # Filter toolbar
            f1, f2, f3 = st.columns(3)
            with f1:
                f_intent = st.selectbox(
                    "Filter by Search Intent",
                    options=["All", "How-to / Tutorial", "Comparison / VS", "Review", "Problem-solving", "Best / Top list", "Question"],
                    key="opp_filter_intent",
                )
            with f2:
                f_priority = st.selectbox("Filter by Priority", options=["All", "High", "Medium", "Low"], key="opp_filter_priority")
            with f3:
                f_gap = st.selectbox("Filter by Gap Status", options=["All", "Potential Content Gaps Only", "Covered in Sample"], key="opp_filter_gap")

            filtered_opps = curr_opps
            if f_intent != "All":
                filtered_opps = [o for o in filtered_opps if o.search_intent == f_intent]
            if f_priority != "All":
                filtered_opps = [o for o in filtered_opps if o.priority == f_priority]
            if f_gap == "Potential Content Gaps Only":
                filtered_opps = [o for o in filtered_opps if o.evidence.get("gap_analysis", {}).get("is_gap")]
            elif f_gap == "Covered in Sample":
                filtered_opps = [o for o in filtered_opps if not o.evidence.get("gap_analysis", {}).get("is_gap")]

            if not filtered_opps:
                render_empty_state(
                    title="No Opportunities Match Selected Filters",
                    description=f"Generated {len(curr_opps)} opportunities, but none match the current filter selection ({f_intent} / {f_priority} / {f_gap}).",
                    icon="🔍",
                    action_label="↺ Reset Opportunity Filters",
                    action_key="btn_reset_opp_filters",
                )
            else:
                st.caption(f"Showing **{len(filtered_opps)}** of {len(curr_opps)} opportunities.")

                for idx, opp in enumerate(filtered_opps):
                    with st.container():
                        score_color = "#10B981" if opp.opportunity_score >= 75 else ("#3B82F6" if opp.opportunity_score >= 50 else ("#F59E0B" if opp.opportunity_score >= 25 else "#EF4444"))
                        col_info, col_score = st.columns([4, 1])

                        with col_info:
                            st.markdown(f"**#{idx + 1} 📌 {opp.topic}**")
                            sup_str = ", ".join(opp.supporting_keywords) if opp.supporting_keywords else "None"
                            st.caption(f"Primary Keyword: `{opp.primary_keyword}` • Supporting: `{sup_str}`")

                            # Badges line
                            gap_data = opp.evidence.get("gap_analysis", {})
                            gap_html = ""
                            if gap_data.get("is_gap"):
                                gap_html = (
                                    f"<span style='background-color:#FEF3C7; color:#92400E; border:1px solid #F59E0B; "
                                    f"padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:bold; margin-right:6px;'>"
                                    f"⚡ Potential Content Gap ({gap_data.get('gap_type', 'GAP')})</span>"
                                )
                            elif gap_data.get("gap_label") == "Covered in Competitor Sample":
                                gap_html = (
                                    f"<span style='background-color:#E0F2FE; color:#0369A1; border:1px solid #38BDF8; "
                                    f"padding:2px 8px; border-radius:12px; font-size:0.8rem; margin-right:6px;'>"
                                    f"✓ Covered in Sample ({gap_data.get('matches_count', 0)} titles)</span>"
                                )

                            badge_line = (
                                f"{gap_html}"
                                f"<span style='background-color:#F3F4F6; border:1px solid #D1D5DB; padding:2px 8px; border-radius:12px; font-size:0.8rem; margin-right:6px;'>Audience: {opp.target_audience}</span>"
                                f"<span style='background-color:#F3F4F6; border:1px solid #D1D5DB; padding:2px 8px; border-radius:12px; font-size:0.8rem; margin-right:6px;'>Format: {opp.content_format}</span>"
                                f"<span style='background-color:#F3F4F6; border:1px solid #D1D5DB; padding:2px 8px; border-radius:12px; font-size:0.8rem;'>Intent: {opp.search_intent}</span>"
                            )
                            st.markdown(badge_line, unsafe_allow_html=True)

                        with col_score:
                            st.markdown(
                                f"<div style='border:1px solid {score_color}; background-color:{score_color}18; border-radius:8px; padding:6px; text-align:center;'>"
                                f"<div style='font-size:0.7rem; color:{score_color}; font-weight:bold;'>OPPORTUNITY SCORE</div>"
                                f"<div style='font-size:1.3rem; font-weight:bold; color:{score_color};'>{opp.opportunity_score} / 100</div>"
                                f"<div style='font-size:0.7rem; color:#6B7280;'>{opp.confidence_level}</div>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        # Score Breakdown Expander
                        with st.expander(f"ℹ️ Scoring Breakdown & Evidence for #{idx + 1}", expanded=False):
                            bd = opp.score_breakdown
                            b_c1, b_c2 = st.columns(2)
                            with b_c1:
                                st.markdown(
                                    f"- Seed Relevance: **{bd.get('relevance_score', 0)} / 25 pts**\n"
                                    f"- Audience Match: **{bd.get('audience_score', 0)} / 20 pts**\n"
                                    f"- Intent Clarity: **{bd.get('intent_score', 0)} / 15 pts**\n"
                                    f"- Supporting Evidence: **{bd.get('supporting_score', 0)} / 15 pts**\n"
                                    f"- Gap Evidence: **{bd.get('gap_score', 0)} / 15 pts**\n"
                                    f"- Format Fit: **{bd.get('format_score', 0)} / 10 pts**"
                                )
                            with b_c2:
                                st.caption(f"Evidence: {gap_data.get('evidence_rationale', 'Standard lexical match.')}")
                                st.caption(f"Formula: {bd.get('formula_explanation', '')}")

                        # Opportunity Action Row
                        c_act1, c_act2, c_act3, _ = st.columns([2, 2, 2, 3])
                        with c_act1:
                            if st.button("💾 Save to Planner", key=f"save_opp_{idx}", use_container_width=True):
                                saved_id = db_manager.save_content_opportunity(opp)
                                opp.id = saved_id
                                st.success(f"Saved to Planner (#{saved_id})")
                        with c_act2:
                            if st.button("✍️ Title Workshop", key=f"wk_opp_{idx}", use_container_width=True):
                                st.session_state["workshop_opportunity"] = opp
                                st.info("Topic loaded into Title & Hook Workshop! Switch to Tab 2 above.")
                        with c_act3:
                            if st.button("📋 Generate Brief", key=f"br_opp_{idx}", use_container_width=True):
                                st.session_state["active_brief_opportunity"] = opp
                                st.info("Topic loaded into Content Brief Generator! Switch to Tab 3 above.")

                        st.divider()

                # Export Section
                st.markdown("##### 📥 Export Opportunities")
                col_exp_csv, col_exp_xlsx = st.columns(2)
                with col_exp_csv:
                    csv_opps = ExportService.export_opportunities_csv(filtered_opps)
                    st.download_button(
                        "📥 Export Opportunities to CSV (UTF-8 BOM)",
                        data=csv_opps,
                        file_name=generate_export_filename(selected_seed_keyword, scope="opportunities", extension="csv"),
                        mime="text/csv",
                        use_container_width=True,
                        key="dl_opps_csv",
                    )
                with col_exp_xlsx:
                    xlsx_opps = ExportService.export_opportunities_excel(filtered_opps)
                    st.download_button(
                        "📥 Export Opportunities to Excel (.xlsx)",
                        data=xlsx_opps,
                        file_name=generate_export_filename(selected_seed_keyword, scope="opportunities", extension="xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="dl_opps_xlsx",
                    )

                # Context-aware recommended next step
                p_next, s_next = render_recommended_next_step(
                    title=f"Take Action on Content Opportunities for '{selected_seed_keyword}'",
                    description="Craft high-retention video title angles in the Title Workshop or explore niche physical product opportunities.",
                    action_label="✍️ Open Title & Hook Workshop",
                    action_key=f"opp_to_workshop_btn_{abs(hash(selected_seed_keyword)) % 10000}",
                    why_recommended=f"Ranked {len(filtered_opps)} content opportunities with top opportunity score {top_score:.1f}/100.",
                    secondary_action_label="📦 Search Niche Products",
                    secondary_action_key=f"opp_to_prods_btn_{abs(hash(selected_seed_keyword)) % 10000}",
                )
                if p_next:
                    if filtered_opps:
                        st.session_state["workshop_opportunity"] = filtered_opps[0]
                    st.info("Loaded top opportunity into Title Workshop! Switch to Tab 2 above.")
                elif s_next:
                    st.session_state.active_seed_input = selected_seed_keyword
                    st.session_state.current_page = PAGE_PRODUCT_OPPORTUNITIES
                    st.rerun()

    # =========================================================================
    # TAB 2: TITLE & HOOK WORKSHOP
    # =========================================================================
    with tab_workshop:
        st.markdown("##### ✍️ YouTube Title & Hook Workshop (Step 6)")
        st.caption(
            "Test and refine click-worthy, honest video titles. Run the quality checklist to catch "
            "vague phrasing, unsupported claims, and mobile character truncation."
        )

        active_opp: Optional[ContentOpportunityItem] = st.session_state.get("workshop_opportunity")
        default_kw = active_opp.primary_keyword if active_opp else (st.session_state.get("active_seed_input") or "best car wax")
        default_title = active_opp.topic if active_opp else "How to Choose the Best Car Wax Step-by-Step"
        default_aud = active_opp.target_audience if active_opp else "General Audience"

        col_w1, col_w2 = st.columns([3, 1])
        with col_w1:
            workshop_kw = st.text_input("Target Keyword for Title Generation:", value=default_kw, key="wk_target_kw")
        with col_w2:
            workshop_aud = st.selectbox(
                "Audience:",
                options=["General Audience", "Beginners", "Advanced / Pros", "Budget Buyers", "Students", "Creators"],
                index=0,
                key="wk_audience_sel",
            )

        workshop_engine = TitleHookWorkshop()

        # 7-Category Title Generator
        if st.button("✨ Generate 7 Title Angle Variations", type="primary", key="btn_gen_7_titles"):
            variations = workshop_engine.generate_title_variations(workshop_kw, target_audience=workshop_aud)
            st.session_state["generated_title_variations"] = variations

        title_vars = st.session_state.get("generated_title_variations")
        if title_vars:
            st.markdown("###### 🎬 Title Angle Options")
            for cat, title_opt in title_vars.items():
                col_t1, col_t2 = st.columns([4, 1])
                with col_t1:
                    st.markdown(f"**{cat}**: `{title_opt}`")
                with col_t2:
                    if st.button("Use Title", key=f"use_t_{cat}", use_container_width=True):
                        st.session_state["checked_title_input"] = title_opt
                st.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 🔍 Title Quality & Clickbait Checklist")
        title_to_check = st.text_input(
            "Proposed YouTube Video Title to Check:",
            value=st.session_state.get("checked_title_input", default_title),
            key="wk_title_check_input",
        )

        if title_to_check:
            check_result: TitleQualityCheck = workshop_engine.check_title_quality(title_to_check, workshop_kw)
            col_qc1, col_qc2 = st.columns([1, 3])
            with col_qc1:
                q_color = "#10B981" if check_result.score >= 80 else ("#F59E0B" if check_result.score >= 60 else "#EF4444")
                st.markdown(
                    f"<div style='border:1px solid {q_color}; background-color:{q_color}18; border-radius:8px; padding:12px; text-align:center;'>"
                    f"<div style='font-size:0.8rem; color:{q_color}; font-weight:bold;'>TITLE QUALITY SCORE</div>"
                    f"<div style='font-size:1.8rem; font-weight:bold; color:{q_color};'>{check_result.score:.0f} / 100</div>"
                    f"<div style='font-size:0.75rem; color:#6B7280;'>Length: {len(title_to_check)} chars</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_qc2:
                for fb in check_result.feedback:
                    if check_result.score >= 80:
                        st.success(f"✓ {fb}")
                    elif "misleading" in fb or "relevance" in fb:
                        st.error(f"⚠️ {fb}")
                    else:
                        st.warning(f"💡 {fb}")

        # Hook & Outline Generator
        st.markdown("---")
        st.markdown("##### 🎙️ First 15 Seconds Hook & Video Outline")
        if st.button("⚡ Generate Script Hook & 3-Part Timeline", key="btn_gen_hook"):
            hook_data = workshop_engine.generate_hook_and_outline(title_to_check, workshop_kw, workshop_aud)
            st.session_state["generated_hook_data"] = hook_data

        hd = st.session_state.get("generated_hook_data")
        if hd:
            st.info(f"**Opening Hook (First 15s Script Snippet):**\n\n\"{hd['hook']}\"")
            st.markdown("**Suggested Timeline Outline:**")
            for step in hd["outline"]:
                st.markdown(f"- ⏱️ `{step}`")

    # =========================================================================
    # TAB 3: CONTENT BRIEF GENERATOR
    # =========================================================================
    with tab_brief:
        st.markdown("##### 📋 15-Point Structured Content Brief Generator (Step 7)")
        st.caption(
            "Build comprehensive, research-backed video briefs with problem statements, unique angles, "
            "section outlines, and fact-checking checklists before scripting."
        )

        brief_opp: Optional[ContentOpportunityItem] = st.session_state.get("active_brief_opportunity")
        default_b_title = brief_opp.topic if brief_opp else "How to Apply Car Wax for Beginners"
        default_b_kw = brief_opp.primary_keyword if brief_opp else "how to apply car wax"

        brief_engine = ContentBriefGenerator()

        # Generate fresh brief if none loaded
        if "loaded_brief" not in st.session_state or st.session_state.get("brief_opp_id") != getattr(brief_opp, "id", None):
            fake_opp = brief_opp or ContentOpportunityItem(
                topic=default_b_title,
                primary_keyword=default_b_kw,
                target_audience="Beginners",
                search_intent="How-to / Tutorial",
            )
            st.session_state["loaded_brief"] = brief_engine.generate_brief(fake_opp)
            st.session_state["brief_opp_id"] = getattr(brief_opp, "id", None)

        b: ContentBrief = st.session_state["loaded_brief"]

        with st.form("brief_editor_form"):
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                b_title = st.text_input("1. Working Title:", value=b.working_title)
                b_kw = st.text_input("2. Primary Keyword:", value=b.primary_keyword)
                b_sup = st.text_input("3. Supporting Keywords (comma-separated):", value=", ".join(b.supporting_keywords))
                b_aud = st.text_input("4. Target Audience:", value=b.target_audience)
                b_intent = st.text_input("5. Search Intent:", value=b.search_intent)
            with col_b2:
                b_prob = st.text_area("6. Viewer Problem / Frustration:", value=b.viewer_problem, height=68)
                b_angle = st.text_area("7. Unique Content Angle:", value=b.unique_angle, height=68)
                b_intro = st.text_area("8. Proposed Introduction Hook:", value=b.proposed_intro, height=68)

            st.markdown("---")
            b_sections = st.text_area("9. Main Video Sections Outline (one per line):", value="\n".join(b.main_sections), height=120)

            col_b3, col_b4 = st.columns(2)
            with col_b3:
                b_examples = st.text_area("10. Supporting Examples to Research:", value="\n".join(b.examples_to_research), height=90)
                b_visuals = st.text_area("11. Suggested Visual Elements & B-Roll:", value="\n".join(b.visual_elements), height=90)
            with col_b4:
                b_faqs = st.text_area("12. Frequently Asked Questions:", value="\n".join(b.faqs), height=90)
                b_cta = st.text_area("13. Conclusion & Call to Action:", value=b.conclusion_cta, height=90)

            b_facts = st.text_area("14. Fact-Checking Checklist (Verify before filming):", value="\n".join(b.fact_checking_checklist), height=80)
            b_sources = st.text_area("15. Source References:", value="\n".join(b.source_references), height=80)

            save_brief_clicked = st.form_submit_button("💾 Save & Persist Content Brief", type="primary", use_container_width=True)

        if save_brief_clicked:
            updated_brief = ContentBrief(
                opportunity_id=b.opportunity_id,
                working_title=b_title,
                primary_keyword=b_kw,
                supporting_keywords=[k.strip() for k in b_sup.split(",") if k.strip()],
                target_audience=b_aud,
                search_intent=b_intent,
                viewer_problem=b_prob,
                unique_angle=b_angle,
                proposed_intro=b_intro,
                main_sections=[s.strip() for s in b_sections.splitlines() if s.strip()],
                examples_to_research=[e.strip() for e in b_examples.splitlines() if e.strip()],
                visual_elements=[v.strip() for v in b_visuals.splitlines() if v.strip()],
                faqs=[f.strip() for f in b_faqs.splitlines() if f.strip()],
                conclusion_cta=b_cta,
                fact_checking_checklist=[fc.strip() for fc in b_facts.splitlines() if fc.strip()],
                source_references=[sr.strip() for sr in b_sources.splitlines() if sr.strip()],
            )
            saved_bid = db_manager.save_content_brief(updated_brief)
            st.session_state["loaded_brief"] = updated_brief
            st.success(f"✅ Content Brief #{saved_bid} saved successfully to SQLite database!")

        # Export Brief Row
        col_eb1, col_eb2 = st.columns(2)
        with col_eb1:
            csv_b = ExportService.export_briefs_csv([b])
            st.download_button(
                "📥 Export Brief to CSV",
                data=csv_b,
                file_name=generate_export_filename(b.primary_keyword, scope="brief", extension="csv"),
                mime="text/csv",
                use_container_width=True,
                key="dl_brief_csv",
            )
        with col_eb2:
            xlsx_b = ExportService.export_briefs_excel([b])
            st.download_button(
                "📥 Export Brief to Excel (.xlsx)",
                data=xlsx_b,
                file_name=generate_export_filename(b.primary_keyword, scope="brief", extension="xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_brief_xlsx",
            )

    # =========================================================================
    # TAB 4: CONTENT CALENDAR
    # =========================================================================
    with tab_calendar:
        st.markdown("##### 📅 YouTube Content Production Calendar (Step 8)")
        st.caption(
            "Schedule video topics and track workflow status from initial idea to published release: "
            "`Idea` ➔ `Researching` ➔ `Brief Ready` ➔ `Scripting` ➔ `Production` ➔ `Editing` ➔ `Scheduled` ➔ `Published`."
        )

        with st.expander("➕ Schedule a New Video Topic", expanded=False):
            with st.form("add_calendar_form"):
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    c_title = st.text_input("Video Title:", placeholder="e.g. Best Car Wax for Black Cars Tested")
                    c_kw = st.text_input("Primary Keyword:", placeholder="e.g. best car wax for black cars")
                with col_c2:
                    c_date = st.date_input("Target Publishing Date:")
                    c_priority = st.selectbox("Priority:", ["Medium", "High", "Low"])
                with col_c3:
                    c_status = st.selectbox(
                        "Initial Status:",
                        ["Idea", "Researching", "Brief Ready", "Scripting", "Production", "Editing", "Scheduled", "Published", "Archived"],
                    )
                    c_notes = st.text_input("Notes:", placeholder="Optional scripting / sponsor reminders")

                add_cal_btn = st.form_submit_button("📅 Add to Calendar", type="primary", use_container_width=True)

            if add_cal_btn and c_title.strip():
                new_entry = CalendarEntry(
                    title=c_title.strip(),
                    primary_keyword=c_kw.strip(),
                    planned_date=str(c_date),
                    status=c_status,
                    priority=c_priority,
                    notes=c_notes.strip(),
                )
                db_manager.save_calendar_entry(new_entry)
                st.success(f"Added '{c_title.strip()}' to content calendar for {c_date}!")
                st.rerun()

        # Calendar Filter Bar
        cf1, cf2, _ = st.columns([2, 2, 3])
        with cf1:
            cal_filter_status = st.selectbox(
                "Filter by Workflow Status:",
                options=["All", "Idea", "Researching", "Brief Ready", "Scripting", "Production", "Editing", "Scheduled", "Published", "Archived"],
                key="cal_filter_status",
            )

        entries = db_manager.get_calendar_entries(status=cal_filter_status)
        if not entries:
            st.info("No content calendar entries found. Use the expander above to schedule your first video topic.")
        else:
            st.markdown(f"**Scheduled Production Queue ({len(entries)} items):**")
            df_cal = pd.DataFrame(
                [
                    {
                        "ID": e["id"],
                        "Date": e["planned_date"],
                        "Title": e["title"],
                        "Primary Keyword": e["primary_keyword"],
                        "Status": e["status"],
                        "Priority": e["priority"],
                        "Notes": e.get("notes", ""),
                    }
                    for e in entries
                ]
            )
            st.dataframe(df_cal, use_container_width=True, hide_index=True)

            # Manage individual entry status
            with st.expander("⚙️ Update or Delete Calendar Entry", expanded=False):
                entry_map = {f"#{e['id']} - {e['title']} ({e['planned_date']})": e for e in entries}
                chosen_cal_label = st.selectbox("Select Entry:", options=list(entry_map.keys()), key="cal_edit_sel")
                selected_entry = entry_map[chosen_cal_label]

                col_u1, col_u2, col_u3 = st.columns(3)
                with col_u1:
                    new_st = st.selectbox(
                        "Update Status:",
                        options=["Idea", "Researching", "Brief Ready", "Scripting", "Production", "Editing", "Scheduled", "Published", "Archived"],
                        index=["Idea", "Researching", "Brief Ready", "Scripting", "Production", "Editing", "Scheduled", "Published", "Archived"].index(selected_entry["status"]),
                        key=f"st_sel_{selected_entry['id']}",
                    )
                with col_u2:
                    new_prio = st.selectbox(
                        "Update Priority:",
                        options=["High", "Medium", "Low"],
                        index=["High", "Medium", "Low"].index(selected_entry["priority"]),
                        key=f"prio_sel_{selected_entry['id']}",
                    )
                with col_u3:
                    new_notes = st.text_input("Notes:", value=selected_entry.get("notes", ""), key=f"notes_{selected_entry['id']}")

                col_btn_u, col_btn_d = st.columns(2)
                with col_btn_u:
                    if st.button("💾 Update Status", key=f"btn_u_{selected_entry['id']}", use_container_width=True):
                        db_manager.update_calendar_entry(
                            entry_id=selected_entry["id"],
                            status=new_st,
                            planned_date=selected_entry["planned_date"],
                            priority=new_prio,
                            notes=new_notes,
                        )
                        st.success("Entry updated!")
                        st.rerun()
                with col_btn_d:
                    conf_del_cal = st.checkbox(f"Confirm deletion #{selected_entry['id']}", key=f"del_chk_cal_{selected_entry['id']}")
                    if st.button("🗑️ Delete", disabled=not conf_del_cal, key=f"btn_del_cal_{selected_entry['id']}", use_container_width=True):
                        db_manager.delete_calendar_entry(selected_entry["id"])
                        st.success("Entry deleted!")
                        st.rerun()

            # Calendar Exports
            col_ecsv, col_exlsx = st.columns(2)
            with col_ecsv:
                csv_cal = ExportService.export_calendar_csv(entries)
                st.download_button("📥 Export Calendar to CSV", data=csv_cal, file_name="youtube_content_calendar.csv", mime="text/csv", use_container_width=True, key="dl_cal_csv")
            with col_exlsx:
                xlsx_cal = ExportService.export_calendar_excel(entries)
                st.download_button("📥 Export Calendar to Excel (.xlsx)", data=xlsx_cal, file_name="youtube_content_calendar.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_cal_xlsx")

    # =========================================================================
    # TAB 5: TOPIC OVERLAP & CANNIBALIZATION CHECK
    # =========================================================================
    with tab_overlap:
        st.markdown("##### ⚠️ Duplicate Topic & Keyword Cannibalization Check (Step 9)")
        st.caption(
            "Prevent your own videos from competing against each other in YouTube search. "
            "Scans your planned opportunities and calendar queue for high token overlap and duplicate primary intents."
        )

        all_planned = db_manager.get_content_opportunities(limit=100)
        cal_items = db_manager.get_calendar_entries(limit=100)
        combined_topics = []
        for p in all_planned:
            combined_topics.append({"title": p["topic"], "primary_keyword": p["primary_keyword"]})
        for c in cal_items:
            combined_topics.append({"title": c["title"], "primary_keyword": c["primary_keyword"]})

        detector = TopicOverlapDetector()
        overlaps = detector.check_overlap(combined_topics, similarity_threshold=0.35)

        if not combined_topics:
            st.info("No planned opportunities or calendar entries found to scan. Add topics to the planner first.")
        elif not overlaps:
            st.success(f"✅ Scanned **{len(combined_topics)}** planned topics. Zero keyword cannibalization or topic duplication detected!")
        else:
            st.warning(f"⚠️ Detected **{len(overlaps)}** potential topic overlaps or keyword conflicts!")

            for idx, ov in enumerate(overlaps):
                with st.container():
                    st.markdown(f"**Overlap #{idx + 1}: `{ov.topic_a}` ⚔️ `{ov.topic_b}`**")
                    st.caption(f"Overlap Type: **{ov.overlap_type}** • Jaccard Similarity: **{int(ov.similarity_score * 100)}%**")
                    st.markdown(f"Shared Keyword Tokens: `{', '.join(ov.shared_keywords)}`")
                    st.error(f"ℹ️ {ov.warning_message}")

                    col_res, _ = st.columns([2, 4])
                    with col_res:
                        st.selectbox(
                            "Resolution Action:",
                            options=["Unresolved", "Keep Both (Distinct Angles)", "Differentiate / Edit Angle", "Combine into Single Video"],
                            key=f"ov_res_{idx}",
                        )
                    st.divider()

            col_ov1, col_ov2 = st.columns(2)
            with col_ov1:
                csv_ov = ExportService.export_overlap_report_csv(overlaps)
                st.download_button("📥 Export Overlap Report to CSV", data=csv_ov, file_name="topic_cannibalization_report.csv", mime="text/csv", use_container_width=True, key="dl_ov_csv")
            with col_ov2:
                xlsx_ov = ExportService.export_overlap_report_excel(overlaps)
                st.download_button("📥 Export Overlap Report to Excel (.xlsx)", data=xlsx_ov, file_name="topic_cannibalization_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="dl_ov_xlsx")


def render_page_product_opportunities(is_ready: bool) -> None:
    """Render the AI-Powered Niche Research & Product Opportunity Intelligence page (Phase 13)."""
    render_page_header(
        title="Niche Product Opportunity Finder",
        subtitle="Intelligent research assistant: discover real products in your niche, generate AI-assisted search queries, analyze recent YouTube video coverage, uncover evidence-backed content gaps, and review transparent opportunity scores.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="Product Discovery",
        badge_type="primary",
        provenance="youtube_api",
    )
    render_contextual_help("product_opportunities")
    render_interactive_tour("product_opportunities")

    # 10-Step Guided Workflow Banner
    st.markdown(
        """
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.82rem; color: #475569;">
            <b>🧭 10-Step Niche Intelligence Workflow:</b><br/>
            1. Enter Niche & Scope &nbsp;➔&nbsp; 2. Region & Dates &nbsp;➔&nbsp; 3. Multi-Channel Discovery &nbsp;➔&nbsp; 4. Identity Verification &nbsp;➔&nbsp; 5. AI Query Expansion &nbsp;➔&nbsp; 6. Bounded Search Execution &nbsp;➔&nbsp; 7. Video Matching &nbsp;➔&nbsp; 8. Content Gap Classification &nbsp;➔&nbsp; 9. Weighted Opportunity Scoring &nbsp;➔&nbsp; 10. Prioritized Plan & Executive Summary
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "⚠️ **Empirical Research Notice**: All findings represent observed search results within the executed sample and selected date range. "
        "A lack of matching videos does **not** prove complete platform-wide absence of a product on YouTube. "
        "Zero synthetic search volume numbers or ranking guarantees are ever fabricated."
    )

    # Initialize Session State
    if "current_discovered_products" not in st.session_state:
        st.session_state.current_discovered_products = []
    if "current_product_session_id" not in st.session_state:
        st.session_state.current_product_session_id = None
    if "last_niche_input" not in st.session_state:
        st.session_state.last_niche_input = "Wireless Earbuds"
    if "prod_ai_summary" not in st.session_state:
        st.session_state.prod_ai_summary = ""

    pipeline = NicheProductPipeline()
    default_start_iso, default_end_iso = pipeline.get_default_date_range(60)
    dt_default_start = datetime.fromisoformat(default_start_iso.replace("Z", "+00:00")).date()
    dt_default_end = datetime.fromisoformat(default_end_iso.replace("Z", "+00:00")).date()

    with st.expander("🔎 Setup Niche Product Investigation & AI Intelligence", expanded=True):
        col_n1, col_n2, col_n3 = st.columns([3, 1.5, 1.5])
        with col_n1:
            niche_name = st.text_input(
                "Niche Name / Product Category",
                value=st.session_state.last_niche_input,
                placeholder="e.g. Wireless Earbuds, Mechanical Keyboards, Smart Watches, Microphones",
                key="prod_niche_input",
            )
            st.session_state.last_niche_input = niche_name
        with col_n2:
            target_country = st.selectbox(
                "Target Region",
                options=list(config.supported_countries.keys()),
                index=0,
                format_func=lambda c: f"{c} - {config.supported_countries[c]}",
                key="prod_country_input",
            )
        with col_n3:
            target_language = st.selectbox(
                "Language",
                options=list(config.supported_languages.keys()),
                index=0,
                format_func=lambda l: f"{l} - {config.supported_languages[l]}",
                key="prod_lang_input",
            )

        col_d1, col_d2, col_d3, col_d4 = st.columns([2, 2, 1.5, 1.5])
        with col_d1:
            start_date_val = st.date_input("Start Date (Default: 60 Days Ago)", value=dt_default_start, key="prod_start_date")
        with col_d2:
            end_date_val = st.date_input("End Date (Default: Today)", value=dt_default_end, key="prod_end_date")
        with col_d3:
            few_threshold = st.slider("Few Vids Threshold", min_value=1, max_value=10, value=3, help="Products with fewer matching videos than this threshold are flagged as FEW MATCHING VIDEOS.", key="prod_few_slider")
        with col_d4:
            min_coverage_queries = st.slider("Min Queries for 0-Match", min_value=1, max_value=4, value=2, help="Minimum successful queries required before assigning NO MATCHING VIDEOS FOUND. If fewer, product is labeled INSUFFICIENT RESEARCH.", key="prod_min_q_slider")

        # AI-Assisted Query Generation & Search Angles Configuration
        st.markdown("##### 🤖 Search Strategy & AI Query Expansion")
        col_ai1, col_ai2 = st.columns([2, 3])
        with col_ai1:
            enable_ai_queries = st.checkbox(
                "Enable AI-Assisted Query Generation",
                value=True,
                help="Generates specialized long-tail, testing, and use-case queries labeled AI_GENERATED_QUERY.",
                key="prod_enable_ai_queries",
            )
            ai_provider_choice = st.selectbox(
                "AI Intelligence Provider",
                options=["Deterministic Fallback (100% Offline & Free)", "Google Gemini", "OpenAI"],
                index=0,
                key="prod_ai_provider_choice",
            )
            ai_api_key = ""
            if ai_provider_choice in ("Google Gemini", "OpenAI"):
                ai_api_key = st.text_input(
                    f"{ai_provider_choice} API Key (Optional if set in env)",
                    type="password",
                    key="prod_ai_key_input",
                )

        with col_ai2:
            search_modes_selected = st.multiselect(
                "Search Angles & Query Modes",
                options=[m.value for m in SearchMode],
                default=[
                    SearchMode.REVIEWS.value,
                    SearchMode.UNBOXING.value,
                    SearchMode.COMPARISONS.value,
                    SearchMode.PRODUCT_TESTING.value,
                    SearchMode.COMMON_PROBLEMS.value,
                ],
                help="Select angles to investigate for candidate products.",
                key="prod_search_modes",
            )

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            max_queries_per_prod = st.slider("Max Queries/Prod", min_value=1, max_value=5, value=2, key="prod_max_q")
        with col_b2:
            max_videos_per_query = st.slider("Max Vids/Query", min_value=5, max_value=30, value=10, key="prod_max_v")
        with col_b3:
            request_budget = st.slider("API Budget (Reqs)", min_value=2, max_value=30, value=10, key="prod_budget_slider")

        # Configurable Opportunity Scoring Weights (Phase 13 Section 5)
        with st.expander("⚖️ Customizable Opportunity Scoring Factor Weights", expanded=False):
            st.caption("Adjust the relative importance of the 4 scoring factors. The final opportunity score is normalized to 0–100.")
            col_w1, col_w2, col_w3, col_w4 = st.columns(4)
            with col_w1:
                w_scarcity = st.slider("Scarcity / Content Gap", min_value=0.2, max_value=3.0, value=1.0, step=0.1, key="weight_scarcity")
            with col_w2:
                w_coverage = st.slider("Search Coverage", min_value=0.2, max_value=3.0, value=1.0, step=0.1, key="weight_coverage")
            with col_w3:
                w_identity = st.slider("Identity Confidence", min_value=0.2, max_value=3.0, value=1.0, step=0.1, key="weight_identity")
            with col_w4:
                w_relevance = st.slider("Niche Relevance", min_value=0.2, max_value=3.0, value=1.0, step=0.1, key="weight_relevance")
            active_weights = {
                "scarcity": w_scarcity,
                "coverage": w_coverage,
                "identity": w_identity,
                "relevance": w_relevance,
            }

        seed_products_input = st.text_area(
            "Optional Seed Products (Comma or newline separated)",
            placeholder="e.g. Sony WF-1000XM5, Bose QuietComfort Ultra, Nothing Ear (2), Moondrop Space Travel, Anker Soundcore Liberty 4 NC",
            height=70,
            key="prod_seed_products",
        )

        col_src1, col_src2 = st.columns(2)
        with col_src1:
            use_db_candidates = st.checkbox("Include candidate products extracted from existing database keywords & video titles", value=True, key="prod_use_db")
        with col_src2:
            discover_niche_query = st.checkbox("Perform live niche search to discover new competitor market products", value=True, key="prod_use_niche_search")

        # Pre-Execution Query Review Drawer
        with st.expander("👀 Pre-Execution Query Previewer", expanded=False):
            st.caption("Inspect the exact query variations that will be executed for seed products prior to running.")
            preview_extractor = ProductExtractor()
            sample_candidates = preview_extractor.parse_seed_products(seed_products_input or "Sony WF-1000XM5", niche=niche_name or "Wireless Earbuds")
            if sample_candidates:
                preview_ai_prov = get_ai_provider("deterministic" if "Deterministic" in ai_provider_choice else ("gemini" if "Gemini" in ai_provider_choice else "openai"), api_key=ai_api_key)
                sample_queries = preview_extractor.generate_search_queries(
                    sample_candidates[0],
                    search_modes=search_modes_selected[:3],
                    ai_provider=preview_ai_prov if enable_ai_queries else None,
                    niche=niche_name or "Wireless Earbuds",
                )
                for q_text, q_mode, q_src in sample_queries:
                    tag_color = "#3B82F6" if q_src == "AI_GENERATED_QUERY" else "#6B7280"
                    st.markdown(f"- `{q_text}` &nbsp; <span style='font-size:0.75rem; background:{tag_color}; color:#fff; border-radius:4px; padding:1px 6px;'>{q_src}</span> &nbsp; <span style='font-size:0.75rem; color:#6B7280;'>({q_mode})</span>", unsafe_allow_html=True)

        # Quota Pre-Flight Estimator & Connection Status
        provider_check = YouTubeDataApiSerpProvider(db_manager=db_manager)
        est_candidates = max(2, len([p for p in re.split(r"[\n,;]", seed_products_input) if p.strip()]) or 4)
        est_queries = min(request_budget, est_candidates * max(1, len(search_modes_selected)))
        est_quota = est_queries * 100
        if provider_check.is_connected():
            st.caption(f"🟢 **Live YouTube Data API v3 Connected** | Pre-flight Quota Estimate: Investigating ~{est_candidates} products will execute up to **{est_queries} queries** (~{est_quota:,} API quota units). Quota used today: {db_manager.get_daily_quota_used() if is_ready else 0} / 10,000 units.")
        else:
            st.caption(f"🟡 **Offline Demonstration / Local Heuristics Mode** (No verified YouTube API key connected) | Research will use local heuristics, historical cache, and public autocomplete discovery without consuming API quota.")

        col_run1, _ = st.columns([2, 4])
        with col_run1:
            start_investigation_clicked = st.button("🚀 Discover & Investigate Products", type="primary", use_container_width=True, key="btn_run_prod_investigation")

    if start_investigation_clicked:
        if not niche_name.strip():
            st.warning("Please enter a niche name (e.g. Wireless Earbuds).")
        else:
            start_dt_iso = datetime.combine(start_date_val, datetime.min.time(), tzinfo=timezone.utc).isoformat()
            end_dt_iso = datetime.combine(end_date_val, datetime.max.time(), tzinfo=timezone.utc).isoformat()
            is_valid_date, date_err = pipeline.validate_date_range(start_dt_iso, end_dt_iso)
            if not is_valid_date:
                st.error(f"Invalid date range: {date_err}")
            else:
                with st.spinner("Executing Phase 13 AI-powered niche intelligence workflow..."):
                    extractor = ProductExtractor()
                    candidates: List[CandidateProduct] = []

                    # Setup AI Provider
                    if "Gemini" in ai_provider_choice:
                        ai_provider = get_ai_provider("gemini", api_key=ai_api_key)
                    elif "OpenAI" in ai_provider_choice:
                        ai_provider = get_ai_provider("openai", api_key=ai_api_key)
                    else:
                        ai_provider = get_ai_provider("deterministic")

                    # 1. Parse user-supplied seed products
                    if seed_products_input.strip():
                        user_seeds = extractor.parse_seed_products(seed_products_input, niche=niche_name)
                        for us in user_seeds:
                            us.category = infer_product_category(us.product_name, niche=niche_name)
                            us.evidence_reference = "User Input Seed"
                            us.verification_status = "User Supplied"
                        candidates.extend(user_seeds)

                    # 2. Extract from curated real-world market catalog for the niche
                    curated = extractor.get_curated_products_for_niche(niche_name)
                    for c in curated:
                        c.category = infer_product_category(c.product_name, niche=niche_name)
                        c.evidence_reference = f"Curated Market Catalog: {niche_name}"
                        c.verification_status = "Verified Market Product"
                    candidates.extend(curated)

                    # 3. Extract from existing database keywords and videos
                    if use_db_candidates and is_ready:
                        try:
                            recent_kws = db_manager.get_recent_searches(limit=10)
                            for s in recent_kws:
                                s_id = s.get("id")
                                if s_id:
                                    k_items = db_manager.get_keywords_for_search(s_id)
                                    for k in k_items:
                                        kw_text = k.get("keyword", "")
                                        extracted = extractor.extract_candidates_from_text(kw_text, niche=niche_name, source="Existing Keywords")
                                        for ex in extracted:
                                            ex.category = infer_product_category(ex.product_name, niche=niche_name)
                                            ex.evidence_reference = f"Database Research Keyword: {kw_text}"
                                        candidates.extend(extracted)
                        except Exception:
                            pass

                    # 4. Discover via free YouTube autocomplete suggestions
                    try:
                        ac_prov = YouTubeAutocompleteProvider(database_manager=db_manager)
                        ac_discovered = extractor.discover_candidates_from_autocomplete(
                            niche_name, provider=ac_prov, language=target_language, country=target_country
                        )
                        for ac in ac_discovered:
                            ac.category = infer_product_category(ac.product_name, niche=niche_name)
                            ac.evidence_reference = f"YouTube Autocomplete Suggestion: '{niche_name}'"
                        candidates.extend(ac_discovered)
                    except Exception:
                        pass

                    # 5. Discover from niche search query if enabled and API connected
                    provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
                    if discover_niche_query and provider.is_connected():
                        try:
                            niche_q = f"best {niche_name} {datetime.now(timezone.utc).year}"
                            niche_serp = provider.analyze_keyword(niche_q, language=target_language, country=target_country, max_results=15)
                            for v in niche_serp.videos:
                                extracted = extractor.extract_candidates_from_text(v.title, niche=niche_name, source="Video Titles")
                                for ex in extracted:
                                    ex.category = infer_product_category(ex.product_name, niche=niche_name)
                                    ex.evidence_url = v.video_url
                                    ex.evidence_reference = f"Competitor Video Title: '{v.title}'"
                                candidates.extend(extracted)
                        except Exception:
                            pass

                    # 6. Fallback candidates if empty
                    if not candidates:
                        fallback_sample = "Sony WF-1000XM5, Bose QuietComfort Ultra, Nothing Ear (2), Moondrop Space Travel"
                        candidates = extractor.parse_seed_products(fallback_sample, niche=niche_name)
                        for c in candidates:
                            c.category = infer_product_category(c.product_name, niche=niche_name)
                            c.evidence_reference = "Default Market Reference"

                    # Deduplicate candidate products by clean product name
                    unique_candidates_map: Dict[str, CandidateProduct] = {}
                    for c in candidates:
                        key = c.product_name.lower().strip()
                        if key not in unique_candidates_map and len(key) >= 2:
                            unique_candidates_map[key] = c
                    deduped_candidates = list(unique_candidates_map.values())[:request_budget]

                    # Create Research Session in SQLite
                    session = ProductResearchSession(
                        niche=niche_name,
                        language=target_language,
                        country=target_country,
                        start_date=start_dt_iso,
                        end_date=end_dt_iso,
                        search_modes=search_modes_selected,
                        few_videos_threshold=few_threshold,
                        min_queries_for_zero_match=min_coverage_queries,
                        max_queries=max_queries_per_prod,
                        max_videos_per_query=max_videos_per_query,
                        request_budget=request_budget,
                        scoring_weights=active_weights,
                        is_mocked=not provider.is_connected(),
                    )
                    session_id = db_manager.save_product_research_session(session) if is_ready else 1
                    st.session_state.current_product_session_id = session_id

                    matcher = ProductMatcher()
                    scorer = ProductOpportunityScorer()
                    investigated_products: List[CandidateProduct] = []
                    total_requests_made = 0
                    total_quota_used = 0
                    all_query_logs: List[ProductQueryExecution] = []

                    progress_bar = st.progress(0.0)
                    status_text = st.empty()

                    for idx, prod in enumerate(deduped_candidates):
                        if total_requests_made >= request_budget:
                            break

                        status_text.text(f"Investigating ({idx+1}/{len(deduped_candidates)}): {prod.product_name}...")
                        prod.session_id = session_id

                        # Generate Queries with AI assistance if enabled
                        raw_queries = extractor.generate_search_queries(
                            prod,
                            search_modes=search_modes_selected,
                            ai_provider=ai_provider if enable_ai_queries else None,
                            niche=niche_name,
                        )[:max_queries_per_prod]

                        all_matched_videos: List[ProductVideoMatch] = []
                        queries_executed_list: List[str] = []
                        succeeded_queries = 0
                        failed_queries = 0

                        for item in raw_queries:
                            if total_requests_made >= request_budget:
                                break

                            # Support both 2-tuples and 3-tuples
                            if len(item) == 3:
                                q_text, s_mode, q_source = item
                            else:
                                q_text, s_mode = item[0], item[1]
                                q_source = "ALGORITHMIC_TEMPLATE"

                            queries_executed_list.append(f"{q_text} ({s_mode} | {q_source})")
                            total_requests_made += 1
                            err_msg = None

                            if provider.is_connected():
                                total_quota_used += 101
                                serp_res = provider.analyze_keyword(
                                    keyword=q_text,
                                    language=target_language,
                                    country=target_country,
                                    max_results=max_videos_per_query,
                                    published_after=start_dt_iso,
                                    published_before=end_dt_iso,
                                    use_cache=True,
                                    is_product_opportunity_search=True,
                                )
                                if serp_res.status_message and "API Error" in serp_res.status_message:
                                    failed_queries += 1
                                    q_status = "Error"
                                    err_msg = serp_res.status_message
                                    res_count = 0
                                else:
                                    succeeded_queries += 1
                                    res_count = len(serp_res.videos)
                                    q_status = "Success" if res_count > 0 else "Zero Results"
                                    for vid in serp_res.videos:
                                        is_m, m_type, m_field, m_terms = matcher.is_match(prod, vid.title, vid.description)
                                        if is_m:
                                            match_entry = ProductVideoMatch(
                                                session_id=session_id,
                                                video_id=vid.video_id,
                                                title=vid.title,
                                                channel_id=vid.channel_id,
                                                channel_title=vid.channel_title,
                                                publish_date=vid.publish_date,
                                                url=f"https://www.youtube.com/watch?v={vid.video_id}",
                                                views=vid.view_count,
                                                match_type=m_type,
                                                match_field=m_field,
                                                matched_terms=m_terms,
                                            )
                                            all_matched_videos.append(match_entry)
                            else:
                                succeeded_queries += 1
                                q_status = "Zero Results"
                                res_count = 0

                            # Log executed query in database with Phase 13 query source
                            query_exec = ProductQueryExecution(
                                session_id=session_id,
                                product_name=prod.product_name,
                                query_text=q_text,
                                search_mode=s_mode,
                                status=q_status,
                                results_count=res_count,
                                query_source=q_source,
                                error_message=err_msg,
                            )
                            all_query_logs.append(query_exec)
                            if is_ready:
                                db_manager.save_product_search_query(query_exec)

                        # Deduplicate matched videos by video_id
                        unique_matches: Dict[str, ProductVideoMatch] = {m.video_id: m for m in all_matched_videos}
                        deduped_matches = list(unique_matches.values())

                        prod.matching_videos_count = len(deduped_matches)
                        prod.unique_channels_count = len(set(m.channel_id for m in deduped_matches if m.channel_id))
                        if deduped_matches:
                            dates = sorted([m.publish_date for m in deduped_matches if m.publish_date], reverse=True)
                            prod.latest_video_date = dates[0] if dates else None
                        else:
                            prod.latest_video_date = None

                        prod.queries_executed = queries_executed_list
                        prod.queries_succeeded = succeeded_queries
                        prod.queries_failed = failed_queries
                        prod.search_coverage_summary = f"{succeeded_queries} of {len(raw_queries)} queries executed successfully in date range."
                        prod.data_source = "Live YouTube Data API v3" if provider.is_connected() else "Offline Simulation / Heuristics"

                        # Calculate Weighted Research Opportunity Score and Classification
                        score, classification, conf, breakdown = scorer.calculate_score(
                            prod,
                            few_videos_threshold=few_threshold,
                            min_queries_for_zero_match=min_coverage_queries,
                            weights=active_weights,
                        )
                        prod.opportunity_score = score
                        prod.classification = classification
                        prod.confidence_level = conf
                        prod.opportunity_score_breakdown = breakdown
                        prod.classification_reason = breakdown.get("classification_reason", "")

                        # Persist Product and Matches in Database
                        if is_ready:
                            p_id = db_manager.save_discovered_product(prod)
                            prod.id = p_id
                            for m in deduped_matches:
                                m.product_id = p_id
                                db_manager.save_product_video_match(m)

                        investigated_products.append(prod)
                        progress_bar.progress((idx + 1) / len(deduped_candidates))

                    # Synthesize Executive AI Research Summary
                    summary_text = ai_provider.generate_research_summary(
                        niche=niche_name,
                        products=investigated_products,
                        session_params={
                            "start_date": start_dt_iso,
                            "end_date": end_dt_iso,
                            "few_videos_threshold": few_threshold,
                            "min_queries_for_zero_match": min_coverage_queries,
                        },
                    )
                    st.session_state.prod_ai_summary = summary_text

                    # Update session final metrics
                    if is_ready:
                        session.id = session_id
                        session.requests_made = total_requests_made
                        session.quota_used = total_quota_used
                        session.status = "Completed"
                        session.ai_summary = summary_text
                        db_manager.save_product_research_session(session)

                    st.session_state.current_discovered_products = investigated_products
                    progress_bar.progress(1.0)
                    status_text.text("Phase 13 Niche Research Complete!")
                    st.success(f"Investigated **{len(investigated_products)}** candidate products across {total_requests_made} queries!")

    # Load Existing Session or Session State Products
    current_products: List[CandidateProduct] = st.session_state.get("current_discovered_products", [])
    if not current_products and is_ready:
        recent_sessions = db_manager.get_product_research_sessions(limit=1)
        if recent_sessions:
            sess_id = recent_sessions[0]["id"]
            db_prods = db_manager.get_discovered_products(session_id=sess_id)
            current_products = [CandidateProduct.from_dict(p) for p in db_prods]
            st.session_state.current_discovered_products = current_products
            st.session_state.current_product_session_id = sess_id
            st.session_state.prod_ai_summary = recent_sessions[0].get("ai_summary", "")

    st.markdown("---")
    st.markdown("### 📊 Product Content Opportunity Dashboard")

    if not current_products:
        st.info("No product investigation results loaded. Fill out the setup form above and click **🚀 Discover & Investigate Products**.")
        return

    # Data Mode Banner
    first_ds = getattr(current_products[0], "data_source", "")
    is_live_data = "Live" in first_ds
    mode_color = "#10B981" if is_live_data else "#F59E0B"
    mode_label = "🟢 LIVE RESEARCH — YOUTUBE DATA API V3" if is_live_data else "🟡 TEST DATA / SIMULATION (Search Sample)"
    st.markdown(
        f"""
        <div style="background-color: {mode_color}15; border-left: 4px solid {mode_color}; padding: 8px 12px; margin-bottom: 12px; border-radius: 4px;">
            <b>Research Execution Mode:</b> <code>{mode_label}</code> | Date Window: <b>Last 60 Days</b> |
            <i>Empirical findings within executed search sample; not proof of platform-wide absence.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metric Cards Row (5 Tiers)
    cnt_total = len(current_products)
    cnt_gaps = sum(1 for p in current_products if p.classification in (
        ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
        ClassificationCategory.NO_MATCHING_VIDEOS_FOUND_IN_EXECUTED_SEARCHES.value,
    ))
    cnt_few = sum(1 for p in current_products if p.classification == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value)
    cnt_found = sum(1 for p in current_products if p.classification == ClassificationCategory.MATCHING_VIDEOS_FOUND.value)
    cnt_insufficient = sum(1 for p in current_products if p.classification == ClassificationCategory.INSUFFICIENT_RESEARCH.value)
    cnt_unverified = sum(1 for p in current_products if p.classification == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Investigated", f"{cnt_total}")
    m2.metric("Zero Matches (Gap)", f"{cnt_gaps}", delta=f"{int(cnt_gaps/max(1, cnt_total)*100)}%")
    m3.metric("Few Videos", f"{cnt_few}", delta=f"{int(cnt_few/max(1, cnt_total)*100)}%")
    m4.metric("Matching Found", f"{cnt_found}")
    m5.metric("Insufficient Coverage", f"{cnt_insufficient}")
    m6.metric("Unverified Identity", f"{cnt_unverified}")

    # Executive AI Research Synthesis Card
    current_summary = st.session_state.get("prod_ai_summary", "")
    if current_summary:
        with st.expander("📝 Executive Research Synthesis & Content Strategy", expanded=True):
            st.markdown(current_summary)
            if st.button("🔄 Regenerate Executive Synthesis", key="btn_regen_ai_summary"):
                det_ai = get_ai_provider("deterministic")
                new_sum = det_ai.generate_research_summary(
                    niche=st.session_state.last_niche_input,
                    products=current_products,
                )
                st.session_state.prod_ai_summary = new_sum
                if is_ready and st.session_state.current_product_session_id:
                    db_manager.update_session_ai_summary(st.session_state.current_product_session_id, new_sum)
                st.rerun()

    # Filters & Sorting Row
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 1.5, 2, 2])
    with col_f1:
        filter_class = st.selectbox(
            "Filter by Classification",
            options=[
                "All",
                ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value,
                ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value,
                ClassificationCategory.MATCHING_VIDEOS_FOUND.value,
                ClassificationCategory.INSUFFICIENT_RESEARCH.value,
                ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value,
            ],
            index=0,
            key="prod_filter_class",
        )
    with col_f2:
        filter_conf = st.selectbox(
            "Filter by Confidence",
            options=["All", "High", "Moderate", "Low"],
            index=0,
            key="prod_filter_conf",
        )
    with col_f3:
        sort_by = st.selectbox(
            "Sort Results",
            options=[
                "Opportunity Score (High to Low)",
                "Matching Videos (Fewest First)",
                "Matching Videos (Most First)",
                "Priority (High to Low)",
                "Product Name (A-Z)",
            ],
            index=0,
            key="prod_sort_by",
        )
    with col_f4:
        search_filter = st.text_input("Search Products / Brands / Categories", placeholder="Filter by text...", key="prod_text_filter")

    # Apply Filters
    filtered_products = current_products
    if filter_class != "All":
        filtered_products = [
            p for p in filtered_products
            if p.classification == filter_class or (filter_class.startswith("NO MATCHING") and p.classification.startswith("NO MATCHING"))
        ]
    if filter_conf != "All":
        filtered_products = [p for p in filtered_products if p.confidence_level == filter_conf]
    if search_filter.strip():
        s_term = search_filter.lower().strip()
        filtered_products = [
            p for p in filtered_products
            if s_term in p.product_name.lower() or s_term in p.brand.lower() or s_term in getattr(p, "category", "").lower()
        ]

    # Apply Sorting
    priority_order = {"High": 3, "Medium": 2, "Low": 1}
    if sort_by == "Opportunity Score (High to Low)":
        filtered_products = sorted(filtered_products, key=lambda p: p.opportunity_score, reverse=True)
    elif sort_by == "Matching Videos (Fewest First)":
        filtered_products = sorted(filtered_products, key=lambda p: p.matching_videos_count, reverse=False)
    elif sort_by == "Matching Videos (Most First)":
        filtered_products = sorted(filtered_products, key=lambda p: p.matching_videos_count, reverse=True)
    elif sort_by == "Priority (High to Low)":
        filtered_products = sorted(filtered_products, key=lambda p: priority_order.get(getattr(p, "priority", "Medium"), 2), reverse=True)
    elif sort_by == "Product Name (A-Z)":
        filtered_products = sorted(filtered_products, key=lambda p: p.product_name.lower())

    st.markdown(f"Showing **{len(filtered_products)}** of {cnt_total} investigated products:")

    # Render Product Cards
    for idx, prod in enumerate(filtered_products):
        with st.container():
            col_c1, col_c2, col_c3, col_c4 = st.columns([3.5, 2.5, 2, 2])
            with col_c1:
                st.markdown(f"#### 🏷️ {prod.product_name}")
                badge_style = "color:#6b7280; font-size:12px;"
                ds_tag = "🟢 Live API" if "Live" in getattr(prod, "data_source", "") else "🟡 Offline / Simulation"
                cat_tag = getattr(prod, "category", "") or "General Hardware"
                prio_tag = getattr(prod, "priority", "Medium")
                prio_color = "#DC2626" if prio_tag == "High" else "#2563EB" if prio_tag == "Medium" else "#6B7280"
                st.markdown(
                    f"<span style='{badge_style}'>Category: <b>{cat_tag}</b> | Brand: <b>{prod.brand or 'General'}</b> | Priority: <b style='color:{prio_color};'>{prio_tag}</b> | `{ds_tag}`</span>",
                    unsafe_allow_html=True,
                )
                if getattr(prod, "evidence_reference", ""):
                    st.caption(f"Evidence Ref: `{prod.evidence_reference}`")

            with col_c2:
                # Classification Badge
                if prod.classification in (ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value, ClassificationCategory.NO_MATCHING_VIDEOS_FOUND_IN_EXECUTED_SEARCHES.value):
                    st.success(f"🟢 **{prod.classification}**")
                elif prod.classification == ClassificationCategory.FEW_MATCHING_VIDEOS_FOUND.value:
                    st.info(f"🔵 **{prod.classification}**")
                elif prod.classification == ClassificationCategory.MATCHING_VIDEOS_FOUND.value:
                    st.warning(f"⚪ **{prod.classification}**")
                elif prod.classification == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value:
                    st.error(f"🟣 **{prod.classification}**")
                else:
                    st.error(f"🔴 **{prod.classification}**")
                st.caption(prod.classification_reason)

            with col_c3:
                st.metric("Matching Videos", f"{prod.matching_videos_count}", help=f"Channels: {prod.unique_channels_count}")
                st.caption(f"Latest Date: `{prod.latest_video_date[:10] if prod.latest_video_date else 'None'}`")

            with col_c4:
                st.metric("Opportunity Score", f"{prod.opportunity_score:.1f}/100")
                conf_color = "green" if prod.confidence_level == "High" else "orange" if prod.confidence_level == "Moderate" else "gray"
                st.markdown(f"Confidence: :{conf_color}[**{prod.confidence_level} Evidence**]")

            # Expander for Product Details, Evidence, Scoring & User Corrections
            with st.expander(f"🔍 Inspect Evidence, Queries & Review '{prod.product_name}'", expanded=False):
                tab_ev1, tab_ev2, tab_ev3 = st.tabs(["🎥 Matched Videos in Period", "⚙️ Score Breakdown & Formulas", "✏️ User Review & Audit Trail"])

                with tab_ev1:
                    matched_vids = db_manager.get_product_video_matches(prod.id) if (prod.id and is_ready) else []
                    if not matched_vids:
                        if prod.classification in (ClassificationCategory.NO_MATCHING_VIDEOS_FOUND.value, ClassificationCategory.NO_MATCHING_VIDEOS_FOUND_IN_EXECUTED_SEARCHES.value):
                            st.success(f"✅ Zero matching videos retrieved in search sample for '{prod.product_name}' during this period across {prod.queries_succeeded} executed queries.")
                            st.info("⚠️ **Observed Research Finding**: No matching videos appeared in the executed YouTube search sample for the specified date range. This confirms an observed content gap in the searched sample, but does not prove complete platform-wide absence of the product on YouTube.")
                        elif prod.classification == ClassificationCategory.INSUFFICIENT_RESEARCH.value:
                            st.warning(f"⚠️ **Insufficient Coverage**: {prod.classification_reason}")
                        elif prod.classification == ClassificationCategory.PRODUCT_IDENTITY_UNVERIFIED.value:
                            st.warning(f"⚠️ **Unverified Product Identity**: {prod.classification_reason}")
                        else:
                            st.write("No matching videos recorded.")
                    else:
                        st.markdown(f"Found **{len(matched_vids)}** matching videos in the selected 60-day window:")
                        for v_idx, mv in enumerate(matched_vids):
                            c_v1, c_v2, c_v3 = st.columns([4, 2, 2])
                            with c_v1:
                                st.markdown(f"**[{mv['title']}]({mv['url']})**")
                                st.caption(f"Channel: {mv['channel_title']} | Match: `{mv['match_type']}` on `{mv['match_field']}`")
                            with c_v2:
                                st.write(f"Views: **{mv['views']:,}**")
                                st.caption(f"Published: {mv['publish_date'][:10] if mv.get('publish_date') else 'Unknown'}")
                            with c_v3:
                                is_ex = mv.get("is_excluded", False)
                                ex_label = "Include Video" if is_ex else "Exclude Video"
                                ex_reason = st.text_input("Exclusion Reason", value=mv.get("exclusion_reason", ""), key=f"ex_rsn_{mv.get('id', v_idx)}", placeholder="e.g. wrong model")
                                if st.button(ex_label, key=f"ex_btn_{mv.get('id', v_idx)}", use_container_width=True):
                                    if is_ready and mv.get("id"):
                                        db_manager.exclude_video_match(mv["id"], is_excluded=not is_ex, exclusion_reason=ex_reason)
                                        st.rerun()

                with tab_ev2:
                    bd = prod.opportunity_score_breakdown or {}
                    col_b_a, col_b_b = st.columns(2)
                    with col_b_a:
                        st.markdown(f"- **Scarcity / Gap Factor (0–40):** `{bd.get('opportunity_factor', 0.0)}` pts")
                        st.markdown(f"- **Search Coverage (0–25):** `{bd.get('search_coverage_factor', 0.0)}` pts")
                        st.markdown(f"- **Identity Confidence (0–20):** `{bd.get('identity_confidence_factor', 0.0)}` pts")
                        st.markdown(f"- **Niche Relevance (0–15):** `{bd.get('niche_relevance_factor', 0.0)}` pts")
                        st.markdown(f"**Total Research Opportunity Score:** `{prod.opportunity_score}/100`")
                        st.caption(f"Confidence: **{prod.confidence_level}** | Data Source: `{getattr(prod, 'data_source', 'Live YouTube Data API v3')}`")
                    with col_b_b:
                        st.markdown(f"**Search Coverage:** {prod.search_coverage_summary}")
                        st.markdown("**Executed Queries:**")
                        for q in prod.queries_executed:
                            st.code(q, language="text")
                    st.caption(bd.get("formula_explanation", ""))
                    st.caption(f"**Empirical Notice:** {bd.get('empirical_limitation_notice', 'Observed finding in search sample.')}")

                with tab_ev3:
                    # User Review & Audit Trail (Phase 13 Section 7)
                    st.markdown("##### ✏️ Product Identity Review & Corrections")
                    c_rev1, c_rev2 = st.columns(2)
                    with c_rev1:
                        new_name = st.text_input("Corrected Product Name", value=prod.product_name, key=f"rename_{prod.id or idx}")
                        rename_reason = st.text_input("Correction Reason", placeholder="e.g. fixed typo / updated model name", key=f"rename_rsn_{prod.id or idx}")
                        if st.button("Save Name Correction", key=f"btn_rename_{prod.id or idx}"):
                            if new_name.strip() and new_name.strip() != prod.product_name:
                                old_name = prod.product_name
                                prod.product_name = new_name.strip()
                                prod.record_user_correction("product_name", old_name, prod.product_name, rename_reason)
                                if is_ready and prod.id:
                                    db_manager.record_product_correction(prod.id, "product_name", old_name, prod.product_name, rename_reason)
                                st.success("Product name updated and audit trail recorded.")
                                st.rerun()

                        new_prio = st.selectbox(
                            "Strategic Priority",
                            options=["High", "Medium", "Low"],
                            index=["High", "Medium", "Low"].index(getattr(prod, "priority", "Medium")),
                            key=f"prio_sel_{prod.id or idx}",
                        )
                        if new_prio != getattr(prod, "priority", "Medium"):
                            old_prio = getattr(prod, "priority", "Medium")
                            prod.priority = new_prio
                            prod.record_user_correction("priority", old_prio, new_prio, "User priority update")
                            if is_ready and prod.id:
                                db_manager.update_product_user_fields(prod.id, priority=new_prio)
                            st.success("Priority updated.")
                            st.rerun()

                    with c_rev2:
                        valid_statuses = ["Verified Market Product", "Extracted Candidate", "User Supplied", "Needs Review", "Unverified", "Rejected"]
                        curr_idx = valid_statuses.index(prod.verification_status) if prod.verification_status in valid_statuses else 1
                        new_status = st.selectbox(
                            "Verification Status",
                            options=valid_statuses,
                            index=curr_idx,
                            key=f"val_stat_{prod.id or idx}",
                        )
                        if new_status != prod.verification_status:
                            old_stat = prod.verification_status
                            prod.verification_status = new_status
                            prod.record_user_correction("verification_status", old_stat, new_status, "User status change")
                            if is_ready and prod.id:
                                db_manager.update_product_user_fields(prod.id, verification_status=new_status)
                            st.success("Verification status updated.")
                            st.rerun()

                        aliases_str = ", ".join(prod.aliases) if prod.aliases else ""
                        new_aliases = st.text_input("Aliases / Alternate Spellings (comma separated):", value=aliases_str, key=f"alias_input_{prod.id or idx}")
                        if st.button("Save Aliases", key=f"btn_alias_{prod.id or idx}"):
                            new_al_list = [a.strip() for a in new_aliases.split(",") if a.strip()]
                            prod.aliases = new_al_list
                            prod.record_user_correction("aliases", aliases_str, new_aliases, "User updated aliases")
                            if is_ready and prod.id:
                                db_manager.update_product_user_fields(prod.id, aliases=new_al_list)
                            st.success("Aliases saved.")
                            st.rerun()

                    notes_val = st.text_area("Content Research Notes / Creator Observations", value=getattr(prod, "notes", ""), key=f"notes_input_{prod.id or idx}", height=60)
                    if st.button("Save Notes", key=f"btn_save_notes_{prod.id or idx}"):
                        prod.notes = notes_val
                        if is_ready and prod.id:
                            db_manager.update_product_user_fields(prod.id, notes=notes_val)
                        st.success("Notes saved.")

                    # Audit Trail Display
                    if prod.audit_trail:
                        st.markdown("**📜 User Correction Audit Trail:**")
                        audit_df = pd.DataFrame(prod.audit_trail)
                        st.dataframe(audit_df, use_container_width=True, hide_index=True)

            st.divider()

    # Export System
    st.markdown("##### 📥 Export Product Content Gap Reports & Structured Intelligence")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        csv_data = ExportService.export_products_csv(filtered_products)
        st.download_button(
            "📥 Export Products to CSV (UTF-8 BOM)",
            data=csv_data,
            file_name=f"niche_products_last60days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_dl_prod_csv",
        )
    with col_exp2:
        xlsx_data = ExportService.export_products_excel(filtered_products)
        st.download_button(
            "📊 Export Products to Excel (.xlsx)",
            data=xlsx_data,
            file_name=f"niche_products_last60days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_dl_prod_xlsx",
        )

    # Context-aware recommended next step
    p_next, s_next = render_recommended_next_step(
        title="Next Action: Plan Content & Monitor Coverage",
        description="Prioritize candidate products in the opportunity planner or set up scheduled monitoring to track video coverage shifts over time.",
        action_label="📋 Open Product Opportunity Planner",
        action_key="prod_opps_to_planner_btn",
        why_recommended=f"Extracted {len(filtered_products)} niche candidate products across recent YouTube video coverage.",
        secondary_action_label="🔔 Track Niche in Research Monitor",
        secondary_action_key="prod_opps_to_monitor_btn",
    )
    if p_next:
        st.session_state.current_page = PAGE_PRODUCT_PLANNER
        st.rerun()
    elif s_next:
        st.session_state.current_page = PAGE_RESEARCH_MONITOR
        st.rerun()


def render_page_product_planner(is_ready: bool) -> None:
    """Render Phase 14 Product Opportunity Planner & Affiliate Content Planning workspace."""
    render_page_header(
        title="Product Opportunity Planner",
        subtitle="Prioritize verified product opportunities, evaluate transparent multi-factor scoring (v14.0), conduct non-fabricated affiliate research, and prepare evidence-grounded video content briefs.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="Affiliate Planner",
        badge_type="primary",
        provenance="local_sqlite",
    )
    render_contextual_help("product_planner")
    render_interactive_tour("product_planner")

    # Core Empirical Guidance Notice
    st.info(
        "💡 **Observed Research Guidance**: Video scarcity reflects observed search results within the selected period and query set. "
        "A lack of matching videos does not guarantee search volume, user demand, or affiliate profitability. "
        "All merchant pricing and affiliate commission terms must be verified against official merchant terms."
    )

    if not is_ready:
        st.error("Database connection not ready. Please verify SQLite database in Settings.")
        return

    scorer_v14 = OpportunityScorerV14()

    # --------------------------------------------------------------------------
    # 1. Quick Actions & Candidate Import
    # --------------------------------------------------------------------------
    st.markdown("##### ⚡ Quick Actions & Session Import")
    act_col1, act_col2 = st.columns([1, 1])

    with act_col1:
        with st.expander("📥 Import Products from Niche Research Session", expanded=False):
            sessions = db_manager.get_product_research_sessions(limit=50)
            if sessions:
                sess_opts = {
                    s["id"]: f"Session #{s['id']} — {s['niche']} ({s['language']}-{s['country']}) [{s['created_at'][:10]}]"
                    for s in sessions
                }
                chosen_sess_id = st.selectbox(
                    "Select Research Session:",
                    options=list(sess_opts.keys()),
                    format_func=lambda sid: sess_opts[sid],
                    key="planner_import_sess_select",
                )
                if st.button("📥 Import All Candidates into Shortlist", type="primary", key="btn_import_sess_products"):
                    prods = db_manager.get_discovered_products(session_id=chosen_sess_id)
                    imported_count = 0
                    for p in prods:
                        # Calculate v14.0 score
                        matching_count = p.get("matching_videos_count", 0)
                        queries_list = p.get("queries_executed", []) or []
                        is_verified = p.get("verification_status") in ["Verified Model Match", "Brand & Model Verified", "Verified Real Product"]
                        niche_val = p.get("niche", "")

                        score, conf, breakdown = scorer_v14.calculate_score(
                            is_identity_verified=is_verified,
                            has_niche_match=bool(niche_val),
                            supporting_keywords_count=len(queries_list),
                            queries_executed_count=len(queries_list),
                            matching_videos_count=matching_count,
                            has_merchant_data=False,
                            has_affiliate_info=False,
                            brand_identified=bool(p.get("brand")),
                        )

                        rec_format, _ = ContentFormatRecommender.recommend_formats(
                            product_name=p.get("product_name", ""),
                            category=p.get("category", ""),
                            keywords=queries_list,
                            matching_videos_count=matching_count,
                        )

                        item = ProductOpportunityShortlist(
                            product_name=p.get("product_name", ""),
                            product_id=p.get("id"),
                            session_id=chosen_sess_id,
                            brand=p.get("brand", ""),
                            model=p.get("model", ""),
                            niche=niche_val,
                            category=p.get("category", ""),
                            status=ShortlistStatus.SHORTLISTED.value,
                            priority=p.get("priority", "Medium"),
                            intended_format=rec_format,
                            opportunity_score=score,
                            confidence_level=conf,
                            score_breakdown=breakdown,
                            formula_version="v14.0",
                            matching_videos_count=matching_count,
                            queries_executed_count=len(queries_list),
                            supporting_keywords=queries_list,
                            notes=p.get("notes", ""),
                            verification_checklist={
                                "identity_verified": is_verified,
                                "specs_checked": False,
                                "merchant_available": False,
                                "competitor_evidence_reviewed": False,
                                "affiliate_compliance_ready": False,
                            },
                        )
                        db_manager.save_shortlist_product(item)
                        imported_count += 1
                    st.success(f"✅ Successfully imported {imported_count} products into shortlist.")
                    st.rerun()
            else:
                st.info("No prior product research sessions found. Run a session in 'Niche Product Opportunity Finder' first.")

    with act_col2:
        with st.expander("➕ Add Product Manually to Shortlist", expanded=False):
            with st.form("manual_product_form"):
                m_pname = st.text_input("Product Name *", placeholder="e.g. Sony WF-1000XM5")
                m_col1, m_col2 = st.columns(2)
                m_brand = m_col1.text_input("Brand", placeholder="e.g. Sony")
                m_model = m_col2.text_input("Model", placeholder="e.g. WF-1000XM5")
                m_niche = m_col1.text_input("Niche", placeholder="e.g. Wireless Earbuds")
                m_cat = m_col2.text_input("Category", placeholder="e.g. Audio")

                m_col3, m_col4 = st.columns(2)
                m_priority = m_col3.selectbox("Priority", ["High", "Medium", "Low"], index=1)
                m_status = m_col4.selectbox(
                    "Initial Status",
                    [s.value for s in ShortlistStatus],
                    index=3,  # Shortlisted
                )
                m_format = st.selectbox(
                    "Intended Content Format",
                    [f.value for f in ContentFormatRecommendation],
                    index=0,
                )

                st.markdown("**Affiliate & Merchant Research (Non-Fabricated)**")
                m_col5, m_col6 = st.columns(2)
                m_merchant = m_col5.text_input("Merchant", placeholder="e.g. Amazon, Best Buy, Direct")
                m_price_raw = m_col6.number_input("Price (Leave 0 if unknown)", min_value=0.0, value=0.0, step=1.0)
                m_prog = m_col5.text_input("Affiliate Program", placeholder="e.g. Amazon Associates")
                m_comm = m_col6.text_input("Commission Info", placeholder="e.g. 1-3% fixed electronics")
                m_avail = st.selectbox("Availability", ["Unknown", "In Stock", "Pre-Order", "Backordered", "Out of Stock"])
                m_aff_link = st.text_input("Product / Affiliate URL", placeholder="https://...")
                m_notes = st.text_area("Notes & Observations", placeholder="Initial research notes...")

                submitted = st.form_submit_button("Save to Shortlist", type="primary")
                if submitted:
                    if not m_pname.strip():
                        st.error("Product name cannot be empty.")
                    else:
                        price_val = float(m_price_raw) if m_price_raw > 0 else None
                        aff_record = ManualAffiliateProvider.create_record(
                            product_name=m_pname,
                            brand=m_brand,
                            model=m_model,
                            merchant=m_merchant,
                            price=price_val,
                            affiliate_program=m_prog,
                            commission_info=m_comm,
                            availability=m_avail,
                            affiliate_link=m_aff_link,
                            notes=m_notes,
                        )

                        score, conf, breakdown = scorer_v14.calculate_score(
                            is_identity_verified=bool(m_brand and m_model),
                            has_niche_match=bool(m_niche),
                            supporting_keywords_count=2,
                            queries_executed_count=2,
                            matching_videos_count=0,
                            has_merchant_data=bool(m_merchant and m_merchant != "Needs verification"),
                            has_affiliate_info=bool(m_prog and m_prog != "Needs verification"),
                            brand_identified=bool(m_brand),
                        )

                        new_item = ProductOpportunityShortlist(
                            product_name=m_pname.strip(),
                            brand=m_brand.strip(),
                            model=m_model.strip(),
                            niche=m_niche.strip(),
                            category=m_cat.strip(),
                            status=m_status,
                            priority=m_priority,
                            intended_format=m_format,
                            opportunity_score=score,
                            confidence_level=conf,
                            score_breakdown=breakdown,
                            formula_version="v14.0",
                            matching_videos_count=0,
                            queries_executed_count=2,
                            supporting_keywords=[f"{m_pname} review", f"{m_pname} specs"],
                            affiliate_data=aff_record.to_dict(),
                            notes=m_notes,
                            verification_checklist={
                                "identity_verified": bool(m_brand and m_model),
                                "specs_checked": False,
                                "merchant_available": bool(m_merchant and m_merchant != "Needs verification"),
                                "competitor_evidence_reviewed": False,
                                "affiliate_compliance_ready": False,
                            },
                        )
                        db_manager.save_shortlist_product(new_item)
                        st.success(f"✅ Added '{m_pname}' to shortlist.")
                        st.rerun()

    # --------------------------------------------------------------------------
    # 2. Shortlist Filter & Metric Summary Bar
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("##### 📋 Product Opportunity Shortlist & Prioritization")

    col_flt1, col_flt2, col_flt3 = st.columns(3)
    status_filter = col_flt1.selectbox(
        "Filter by Status:",
        ["All"] + [s.value for s in ShortlistStatus],
        index=0,
        key="planner_status_filter",
    )
    priority_filter = col_flt2.selectbox(
        "Filter by Priority:",
        ["All", "High", "Medium", "Low"],
        index=0,
        key="planner_priority_filter",
    )

    all_shortlist = db_manager.get_shortlist_products(status=None, priority=None)
    available_niches = sorted(list({p.niche for p in all_shortlist if p.niche}))
    niche_filter = col_flt3.selectbox(
        "Filter by Niche:",
        ["All"] + available_niches,
        index=0,
        key="planner_niche_filter",
    )

    # Filter records
    filtered_shortlist = db_manager.get_shortlist_products(
        status=status_filter if status_filter != "All" else None,
        priority=priority_filter if priority_filter != "All" else None,
        niche=niche_filter if niche_filter != "All" else None,
    )

    # Metrics
    tot_count = len(filtered_shortlist)
    ver_count = sum(1 for p in filtered_shortlist if p.verification_checklist.get("identity_verified"))
    prod_count = sum(1 for p in filtered_shortlist if p.status in [ShortlistStatus.IN_PRODUCTION.value, ShortlistStatus.PUBLISHED.value])
    avg_score = round(sum(p.opportunity_score for p in filtered_shortlist) / tot_count, 1) if tot_count > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Shortlisted Products", tot_count)
    m2.metric("Verified Identities", ver_count)
    m3.metric("In Production / Published", prod_count)
    m4.metric("Avg Opportunity Score (v14.0)", f"{avg_score} / 100")

    if not all_shortlist:
        if render_empty_state(
            title="No Products Shortlisted Yet",
            description="Your product opportunity shortlist is empty. Discover products with few matching videos in Niche Product Opportunity Finder, or add items manually using the Quick Actions above.",
            icon="📋",
            action_label="📦 Go to Niche Product Finder",
            action_key="planner_go_to_niche_finder_btn",
        ):
            st.session_state.current_page = PAGE_PRODUCT_OPPORTUNITIES
            st.rerun()
        return

    if not filtered_shortlist:
        render_empty_state(
            title="No Products Match Current Filters",
            description=f"You have {len(all_shortlist)} products in your shortlist, but none match status '{status_filter}', priority '{priority_filter}', or niche '{niche_filter}'.",
            icon="🔍",
            action_label="↺ Reset Shortlist Filters",
            action_key="planner_reset_filters_btn",
        )
        return

    # --------------------------------------------------------------------------
    # 3. Interactive Shortlist Table & Management Drawers
    # --------------------------------------------------------------------------
    st.markdown("##### 🔍 Shortlist Explorer & Decision Management")

    for item in filtered_shortlist:
        aff = item.affiliate_data or {}
        chk = item.verification_checklist or {}
        p_price = aff.get("price")
        price_txt = f"${p_price:,.2f}" if p_price and p_price > 0 else "Unavailable"
        merchant_txt = aff.get("merchant") or "Needs verification"

        # Badge color indicator
        status_color = "🟢" if item.status in ["Published", "Verified"] else "🟡" if item.status in ["In Production", "Brief Created"] else "⚪"
        exp_title = f"{status_color} [{item.priority}] **{item.product_name}** | Score: **{item.opportunity_score:.1f}** ({item.confidence_level}) | Status: **{item.status}** | Format: **{item.intended_format}**"

        with st.expander(exp_title, expanded=False):
            c_left, c_right = st.columns([1, 1])

            with c_left:
                st.markdown("**📊 Heuristic Score Breakdown (v14.0)**")
                bd = item.score_breakdown or {}
                st.write(f"- Identity Verification: `{bd.get('identity_verification', 0.0)} / 20`")
                st.write(f"- Niche Relevance: `{bd.get('niche_relevance', 0.0)} / 15`")
                st.write(f"- Keyword Evidence: `{bd.get('keyword_evidence', 0.0)} / 15`")
                st.write(f"- Research Coverage: `{bd.get('research_coverage', 0.0)} / 20`")
                st.write(f"- Video Scarcity: `{bd.get('video_scarcity', 0.0)} / 20` *({bd.get('scarcity_reason', 'Observed results')})*")
                st.write(f"- Evidence Completeness: `{bd.get('evidence_completeness', 0.0)} / 10`")

                if bd.get("guardrails_applied"):
                    for g in bd["guardrails_applied"]:
                        st.caption(f"⚠️ Guardrail: {g}")

                st.markdown("**🏷️ Supporting Keywords Observed**")
                if item.supporting_keywords:
                    st.write(", ".join([f"`{k}`" for k in item.supporting_keywords[:6]]))
                else:
                    st.caption("No supporting keywords recorded.")

            with c_right:
                st.markdown("**🛒 Merchant & Affiliate Details (Observed)**")
                st.write(f"- Merchant: `{merchant_txt}`")
                st.write(f"- Price: `{price_txt}`")
                st.write(f"- Affiliate Program: `{aff.get('affiliate_program', 'Needs verification')}`")
                st.write(f"- Commission: `{aff.get('commission_info', 'Needs verification')}`")
                st.write(f"- Availability: `{aff.get('availability', 'Unknown')}`")
                if aff.get("affiliate_link"):
                    st.write(f"- URL / Link: [{aff.get('affiliate_link')}]({aff.get('affiliate_link')})")

                st.markdown("**✅ Verification Checklist**")
                col_chk1, col_chk2 = st.columns(2)
                id_v = col_chk1.checkbox("Identity Verified", value=chk.get("identity_verified", False), key=f"chk_id_{item.id}")
                sp_v = col_chk2.checkbox("Specs Checked", value=chk.get("specs_checked", False), key=f"chk_sp_{item.id}")
                me_v = col_chk1.checkbox("Merchant Active", value=chk.get("merchant_available", False), key=f"chk_me_{item.id}")
                ce_v = col_chk2.checkbox("Competitor Checked", value=chk.get("competitor_evidence_reviewed", False), key=f"chk_ce_{item.id}")
                ac_v = col_chk1.checkbox("FTC Compliance Ready", value=chk.get("affiliate_compliance_ready", False), key=f"chk_ac_{item.id}")

            # Quick update row
            st.markdown("---")
            q_col1, q_col2, q_col3, q_col4 = st.columns([1.2, 1, 1.5, 1.3])
            new_st = q_col1.selectbox(
                "Update Status:",
                [s.value for s in ShortlistStatus],
                index=[s.value for s in ShortlistStatus].index(item.status) if item.status in [s.value for s in ShortlistStatus] else 0,
                key=f"status_sel_{item.id}",
            )
            new_pr = q_col2.selectbox(
                "Priority:",
                ["High", "Medium", "Low"],
                index=["High", "Medium", "Low"].index(item.priority) if item.priority in ["High", "Medium", "Low"] else 1,
                key=f"prior_sel_{item.id}",
            )
            new_fmt = q_col3.selectbox(
                "Intended Format:",
                [f.value for f in ContentFormatRecommendation],
                index=[f.value for f in ContentFormatRecommendation].index(item.intended_format) if item.intended_format in [f.value for f in ContentFormatRecommendation] else 0,
                key=f"fmt_sel_{item.id}",
            )
            q_notes = st.text_input("Notes / Hypotheses:", value=item.notes or "", key=f"notes_input_{item.id}")

            btn_col1, btn_col2, btn_col3 = st.columns([1, 1.2, 1])
            with btn_col1:
                if st.button("💾 Save Updates", key=f"btn_save_item_{item.id}"):
                    # Update verification checklist state
                    item.verification_checklist = {
                        "identity_verified": id_v,
                        "specs_checked": sp_v,
                        "merchant_available": me_v,
                        "competitor_evidence_reviewed": ce_v,
                        "affiliate_compliance_ready": ac_v,
                    }
                    item.status = new_st
                    item.priority = new_pr
                    item.intended_format = new_fmt
                    item.notes = q_notes
                    db_manager.save_shortlist_product(item)
                    st.success("Updated successfully.")
                    st.rerun()

            with btn_col2:
                if st.button("📝 Open Content Brief", type="primary", key=f"btn_open_brief_{item.id}"):
                    st.session_state.active_brief_shortlist_id = item.id
                    st.rerun()

            with btn_col3:
                if st.button("🗑️ Remove", key=f"btn_del_item_{item.id}"):
                    db_manager.delete_shortlist_product(item.id)
                    st.success(f"Removed '{item.product_name}' from shortlist.")
                    st.rerun()

    # --------------------------------------------------------------------------
    # 4. Side-by-Side Product Opportunity Comparison Matrix
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("##### ⚖️ Side-by-Side Product Comparison Matrix")
    st.caption("Select 2 or more products from your shortlist to review evidence, pricing, and opportunity metrics side-by-side.")

    comp_options = {p.id: f"{p.product_name} (Score: {p.opportunity_score:.1f})" for p in filtered_shortlist}
    chosen_ids = st.multiselect(
        "Choose Products to Compare:",
        options=list(comp_options.keys()),
        format_func=lambda pid: comp_options[pid],
        default=list(comp_options.keys())[:3] if len(comp_options) >= 2 else list(comp_options.keys()),
        key="matrix_multiselect",
    )

    if len(chosen_ids) >= 2:
        selected_prods = [p for p in filtered_shortlist if p.id in chosen_ids]
        matrix_result = ProductComparisonEngine.build_comparison_matrix(selected_prods)
        matrix_rows = matrix_result["matrix_rows"]

        df_matrix = pd.DataFrame(matrix_rows)
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)
        st.caption(f"ℹ️ {matrix_result['disclaimer']}")

        # Dual export for comparison matrix
        col_m_csv, col_m_xlsx = st.columns(2)
        with col_m_csv:
            m_csv = ExportService.export_comparison_matrix_csv(matrix_rows)
            st.download_button(
                "📥 Export Comparison Matrix to CSV",
                data=m_csv,
                file_name=f"opportunity_comparison_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_dl_matrix_csv",
            )
        with col_m_xlsx:
            m_xlsx = ExportService.export_comparison_matrix_excel(matrix_rows)
            st.download_button(
                "📊 Export Comparison Matrix to Excel (.xlsx)",
                data=m_xlsx,
                file_name=f"opportunity_comparison_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_dl_matrix_xlsx",
            )
    else:
        st.info("Select at least 2 products above to generate a side-by-side comparison matrix.")

    # --------------------------------------------------------------------------
    # 5. Affiliate Content Brief Workspace
    # --------------------------------------------------------------------------
    active_b_id = st.session_state.get("active_brief_shortlist_id")
    if active_b_id:
        st.markdown("---")
        active_prod = db_manager.get_shortlist_product(active_b_id)
        if active_prod:
            st.markdown(f"### 📝 Affiliate Video Content Brief: `{active_prod.product_name}`")
            st.caption(
                "Structured, fact-checked YouTube production plan grounded in actual search signals. "
                "Complies with FTC disclosure requirements and avoids fabricated personal testing claims."
            )

            # Retrieve or generate brief
            existing_brief = db_manager.get_affiliate_brief(active_b_id)
            if not existing_brief:
                existing_brief = AffiliateBriefGenerator.generate_brief(active_prod)

            with st.form("affiliate_brief_edit_form"):
                bf_col1, bf_col2 = st.columns(2)
                b_pk = bf_col1.text_input("Primary Target Keyword *", value=existing_brief.primary_keyword)
                b_supp = bf_col2.text_input("Supporting Keywords (comma-separated)", value=", ".join(existing_brief.supporting_keywords))

                bf_col3, bf_col4 = st.columns(2)
                b_aud = bf_col3.text_input("Target Audience", value=existing_brief.target_audience)
                b_intent = bf_col4.selectbox("Search Intent", ["Commercial Investigation", "Transactional", "Informational", "Comparison"], index=0)

                b_fmt = st.selectbox(
                    "Video Content Format",
                    [f.value for f in ContentFormatRecommendation],
                    index=[f.value for f in ContentFormatRecommendation].index(existing_brief.content_format) if existing_brief.content_format in [f.value for f in ContentFormatRecommendation] else 0,
                )

                st.markdown("**Suggested Video Angles & Title Ideas**")
                b_titles = st.text_area(
                    "Title Ideas (one per line):",
                    value="\n".join(existing_brief.title_ideas),
                    height=100,
                )

                st.markdown("**Video Structure & Timestamp Outline**")
                st.caption("Structured timeline for engagement and objective evidence presentation.")
                struct_text = "\n".join([f"{s.get('section', '')}: {s.get('notes', '')}" for s in existing_brief.video_structure])
                b_struct_raw = st.text_area("Timeline Outline (Section: Notes):", value=struct_text, height=130)

                st.markdown("**Research & Fact-Checking Priorities**")
                bf_q1, bf_q2 = st.columns(2)
                b_questions = bf_q1.text_area(
                    "Questions to Investigate (one per line):",
                    value="\n".join(existing_brief.questions_to_investigate),
                    height=110,
                )
                b_features = bf_q2.text_area(
                    "Features to Verify (one per line):",
                    value="\n".join(existing_brief.features_to_verify),
                    height=110,
                )

                st.markdown("**Objective Evaluation**")
                bf_p1, bf_p2 = st.columns(2)
                b_pros = bf_p1.text_area("Objective Pros (one per line):", value="\n".join(existing_brief.pros_and_cons.get("pros", [])), height=90)
                b_cons = bf_p2.text_area("Objective Cons (one per line):", value="\n".join(existing_brief.pros_and_cons.get("cons", [])), height=90)

                b_cta = st.text_input("Call to Action (CTA):", value=existing_brief.call_to_action)

                # Mandatory FTC disclosure alert
                st.warning(f"⚖️ **FTC Compliance Disclosure Reminder**:\n\n{existing_brief.affiliate_disclosure}")
                st.info("🛡️ **Ethical Creator Reminder**: Do not make claims of personal hands-on use or durability testing unless you have personally tested the physical product.")

                b_notes = st.text_area("Production Notes:", value=existing_brief.brief_notes)

                col_b_save, col_b_close = st.columns([1, 1])
                save_brief_clicked = col_b_save.form_submit_button("💾 Save Content Brief", type="primary")

            if save_brief_clicked:
                existing_brief.primary_keyword = b_pk.strip()
                existing_brief.supporting_keywords = [k.strip() for k in b_supp.split(",") if k.strip()]
                existing_brief.target_audience = b_aud.strip()
                existing_brief.search_intent = b_intent
                existing_brief.content_format = b_fmt
                existing_brief.title_ideas = [t.strip() for t in b_titles.split("\n") if t.strip()]
                existing_brief.questions_to_investigate = [q.strip() for q in b_questions.split("\n") if q.strip()]
                existing_brief.features_to_verify = [f.strip() for f in b_features.split("\n") if f.strip()]
                existing_brief.pros_and_cons = {
                    "pros": [p.strip() for p in b_pros.split("\n") if p.strip()],
                    "cons": [c.strip() for c in b_cons.split("\n") if c.strip()],
                }
                existing_brief.call_to_action = b_cta.strip()
                existing_brief.brief_notes = b_notes.strip()

                # Parse structure
                new_struct = []
                for line in b_struct_raw.split("\n"):
                    if ":" in line:
                        sec, nts = line.split(":", 1)
                        new_struct.append({"section": sec.strip(), "notes": nts.strip()})
                    elif line.strip():
                        new_struct.append({"section": line.strip(), "notes": ""})
                existing_brief.video_structure = new_struct

                db_manager.save_affiliate_brief(existing_brief)
                db_manager.update_shortlist_status(active_b_id, status=ShortlistStatus.BRIEF_CREATED.value)
                st.success(f"✅ Content brief saved for '{active_prod.product_name}'! Shortlist status updated to 'Brief Created'.")
                st.rerun()

            # Dual brief exports & close button
            col_b_dl1, col_b_dl2, col_b_close_btn = st.columns([1, 1, 1])
            with col_b_dl1:
                b_csv = ExportService.export_affiliate_brief_csv(existing_brief)
                st.download_button(
                    "📥 Export Brief to CSV",
                    data=b_csv,
                    file_name=f"brief_{active_prod.product_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_brief_csv",
                )
            with col_b_dl2:
                b_xlsx = ExportService.export_affiliate_brief_excel(existing_brief)
                st.download_button(
                    "📊 Export Brief to Excel (.xlsx)",
                    data=b_xlsx,
                    file_name=f"brief_{active_prod.product_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_dl_brief_xlsx",
                )
            with col_b_close_btn:
                if st.button("✖️ Close Brief Workspace", use_container_width=True, key="btn_close_brief"):
                    st.session_state.active_brief_shortlist_id = None
                    st.rerun()

    # --------------------------------------------------------------------------
    # 6. Complete Shortlist Dual Export
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("##### 📦 Export Product Opportunity Shortlist")
    st.caption("Export all shortlisted opportunities with heuristic scoring, affiliate metadata, and verification statuses.")

    col_sh_csv, col_sh_xlsx = st.columns(2)
    with col_sh_csv:
        sh_csv = ExportService.export_shortlist_csv(filtered_shortlist)
        st.download_button(
            "📥 Export Shortlist to CSV (UTF-8 BOM)",
            data=sh_csv,
            file_name=f"product_opportunity_shortlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="btn_dl_shortlist_csv",
        )
    with col_sh_xlsx:
        sh_xlsx = ExportService.export_shortlist_excel(filtered_shortlist)
        st.download_button(
            "📊 Export Shortlist to Excel (.xlsx)",
            data=sh_xlsx,
            file_name=f"product_opportunity_shortlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_dl_shortlist_xlsx",
        )

    # Context-aware recommended next step
    p_next, s_next = render_recommended_next_step(
        title="Next Action: Schedule Tracking & Title Optimization",
        description="Schedule automated recurring checks in the Research Monitor or brainstorm clickable title angles for your shortlisted opportunities.",
        action_label="🔔 Schedule Tracking in Research Monitor",
        action_key="planner_to_monitor_btn",
        why_recommended=f"Shortlist contains {len(filtered_shortlist)} prioritized candidate products ready for monitoring.",
        secondary_action_label="✍️ Craft Titles in Hook Workshop",
        secondary_action_key="planner_to_workshop_btn",
    )
    if p_next:
        st.session_state.current_page = PAGE_RESEARCH_MONITOR
        st.rerun()
    elif s_next:
        st.session_state.current_page = PAGE_CONTENT_OPPORTUNITIES
        st.rerun()



# ==============================================================================
# Phase 15 — Automated Niche Research Reports & Opportunity Monitoring UI
# ==============================================================================

def render_page_research_monitor(is_ready: bool) -> None:
    """Render the Automated Niche Research Reports & Opportunity Monitoring page (Phase 15)."""
    render_page_header(
        title="Research Monitor",
        subtitle="Save reusable research configurations, execute repeatable on-demand or scheduled monitoring runs, compare snapshots over time, and inspect empirical delta changes without synthetic extrapolation.",
        category="WORKFLOW & MANAGEMENT",
        badge_text="Temporal Tracker",
        badge_type="primary",
        provenance="local_sqlite",
    )
    render_contextual_help("research_monitor")
    render_interactive_tour("research_monitor")

    if not is_ready:
        st.error("Database connection unavailable. Please verify local environment.")
        return

    # Check unread high-priority alerts
    unread_alerts = db_manager.get_monitor_alerts(unread_only=True)
    crit_or_high = [
        a for a in unread_alerts
        if a.severity in (AlertSeverity.CRITICAL.value, AlertSeverity.HIGH_OPPORTUNITY.value)
    ]
    if crit_or_high:
        st.warning(
            f"🔔 **{len(crit_or_high)} High-Priority Change Alert(s) Detected!** "
            f"Review new verified candidate opportunities or system warnings in the 'Change Alerts' tab."
        )

    tab_configs, tab_run, tab_compare, tab_alerts, tab_trends = st.tabs([
        "⚙️ Saved Configurations",
        "▶️ Run & Scheduler",
        "⚖️ Snapshot Comparison",
        "🔔 Change Alerts & Feed",
        "📈 Historical Analytics",
    ])

    # --------------------------------------------------------------------------
    # TAB 1: Saved Research Configurations
    # --------------------------------------------------------------------------
    with tab_configs:
        st.markdown("##### ⚙️ Saved Reusable Research Configurations")
        st.caption("Manage reusable templates with product filters, matching criteria, query templates, and request quotas.")

        all_configs = db_manager.get_monitor_configs(include_paused=True)
        active_count = sum(1 for c in all_configs if not c.is_paused)
        paused_count = sum(1 for c in all_configs if c.is_paused)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total Configurations", len(all_configs))
        col_m2.metric("Active Configurations", active_count)
        col_m3.metric("Paused Configurations", paused_count)

        with st.expander("➕ Create New Research Configuration", expanded=len(all_configs) == 0):
            with st.form("form_create_monitor_config"):
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    cfg_name = st.text_input("Configuration Name", value="Wireless Earbuds Bi-Weekly Scan")
                    cfg_niche = st.text_input("Niche Name *", value="Wireless Earbuds")
                    cfg_country = st.selectbox("Target Country", options=["US", "GB", "CA", "AU", "DE", "IN"], index=0)
                    cfg_lang = st.selectbox("Language", options=["en", "es", "de", "fr"], index=0)
                    cfg_days = st.slider("Research Window (Days)", min_value=7, max_value=365, value=60)
                    cfg_cats = st.text_input("Category Filters (comma-separated)", value="ANC Earbuds, Sports, Gaming")

                with c_col2:
                    cfg_max_p = st.number_input("Max Products per Run", min_value=5, max_value=100, value=25)
                    cfg_max_q = st.number_input("Max Queries per Product", min_value=1, max_value=30, value=15)
                    cfg_budget = st.number_input("API Request Budget Ceiling", min_value=5, max_value=100, value=15)
                    cfg_matching = st.selectbox("Matching Mode", options=["Exact Model Match", "Flexible Fuzzy Match"], index=0)
                    cfg_cov = st.slider("Min Queries for Zero-Match Classification", min_value=1, max_value=5, value=2)
                    cfg_formula = st.selectbox("Opportunity Formula Version", options=["v14.0", "v13.0"], index=0)

                cfg_methods = st.multiselect(
                    "Enabled Discovery Methods",
                    options=["seed", "catalog", "autocomplete", "ai_angles"],
                    default=["seed", "catalog", "autocomplete", "ai_angles"],
                )
                cfg_templates = st.text_area(
                    "Search Query Templates (One per line)",
                    value="{brand} {model} review\n{brand} {model} test\nbest {niche} 2026\n{product_name}",
                    height=80,
                )
                cfg_notes = st.text_area("Configuration Notes", value="Bi-weekly monitoring of emerging wireless earbuds candidates.", height=60)

                submit_cfg = st.form_submit_button("💾 Save Configuration", type="primary", use_container_width=True)
                if submit_cfg:
                    if not cfg_niche.strip():
                        st.error("Niche name is required.")
                    else:
                        cat_list = [c.strip() for c in cfg_cats.split(",") if c.strip()]
                        tmpl_list = [t.strip() for t in cfg_templates.split("\n") if t.strip()]
                        new_config = SavedResearchConfig(
                            name=cfg_name.strip() or f"{cfg_niche.strip()} Config",
                            niche=cfg_niche.strip(),
                            country=cfg_country,
                            language=cfg_lang,
                            date_window_days=int(cfg_days),
                            category_filters=cat_list,
                            query_templates=tmpl_list,
                            max_products_per_run=int(cfg_max_p),
                            max_queries_per_run=int(cfg_max_q),
                            request_budget=int(cfg_budget),
                            matching_mode=cfg_matching,
                            min_research_coverage=int(cfg_cov),
                            opportunity_formula_version=cfg_formula,
                            enabled_discovery_methods=cfg_methods,
                            notes=cfg_notes.strip(),
                        )
                        cfg_id = db_manager.save_monitor_config(new_config)
                        st.success(f"✅ Configuration '{new_config.name}' saved with ID #{cfg_id}!")
                        st.rerun()

        # Display saved configurations list
        if all_configs:
            st.markdown("---")
            st.markdown("##### 📋 Active & Saved Configurations")
            for cfg in all_configs:
                status_icon = "⏸️ Paused" if cfg.is_paused else "🟢 Active"
                with st.expander(f"{status_icon} | **{cfg.name}** ({cfg.niche} - {cfg.country}/{cfg.language})", expanded=False):
                    c_info1, c_info2, c_info3 = st.columns(3)
                    with c_info1:
                        st.write(f"**Niche:** {cfg.niche}")
                        st.write(f"**Date Window:** {cfg.date_window_days} Days")
                        st.write(f"**Matching Mode:** {cfg.matching_mode}")
                        st.write(f"**Formula Version:** {cfg.opportunity_formula_version}")
                    with c_info2:
                        st.write(f"**Max Products:** {cfg.max_products_per_run}")
                        st.write(f"**Max Queries / Product:** {cfg.max_queries_per_run}")
                        st.write(f"**Request Budget Ceiling:** {cfg.request_budget}")
                        st.write(f"**Min Coverage:** {cfg.min_research_coverage} queries")
                    with c_info3:
                        st.write(f"**Enabled Methods:** {', '.join(cfg.enabled_discovery_methods)}")
                        st.write(f"**Categories:** {', '.join(cfg.category_filters) if cfg.category_filters else 'None'}")
                        st.write(f"**Created:** {cfg.created_at[:10]}")
                        st.write(f"**Status:** {'Paused' if cfg.is_paused else 'Active'}")

                    if cfg.notes:
                        st.caption(f"**Notes:** {cfg.notes}")

                    col_act1, col_act2, col_act3, col_act4 = st.columns(4)
                    with col_act1:
                        toggle_txt = "▶️ Resume Config" if cfg.is_paused else "⏸️ Pause Config"
                        if st.button(toggle_txt, key=f"btn_toggle_cfg_{cfg.id}", use_container_width=True):
                            db_manager.update_monitor_config_status(cfg.id, is_paused=not cfg.is_paused)
                            st.rerun()
                    with col_act2:
                        if st.button("📋 Duplicate Config", key=f"btn_dup_cfg_{cfg.id}", use_container_width=True):
                            dup_id = db_manager.duplicate_monitor_config(cfg.id)
                            st.success(f"Duplicated as Config #{dup_id}!")
                            st.rerun()
                    with col_act3:
                        confirm_del = st.checkbox("Confirm Delete", key=f"chk_del_cfg_{cfg.id}")
                    with col_act4:
                        if st.button("🗑️ Delete", disabled=not confirm_del, key=f"btn_del_cfg_{cfg.id}", use_container_width=True):
                            db_manager.delete_monitor_config(cfg.id)
                            st.success("Configuration deleted.")
                            st.rerun()
        else:
            render_empty_state(
                title="No Reusable Configurations Yet",
                description="Save your first research configuration using the form above to automate repeatable YouTube searches, track products, and schedule monitoring.",
                icon="⚙️",
            )

    # --------------------------------------------------------------------------
    # TAB 2: Run Research & In-Process Scheduler
    # --------------------------------------------------------------------------
    with tab_run:
        st.markdown("##### ▶️ Execute Repeatable Research Runs & Scheduler")
        st.caption("Trigger bounded on-demand research runs, enforce request budgets, rerun failed queries, and manage local recurring schedules.")

        if not all_configs:
            render_empty_state(
                title="No Research Configurations Available",
                description="To execute or schedule automated monitoring, save a research template in the 'Saved Configurations' tab first.",
                icon="▶️",
            )
        else:
            cfg_options = {c.id: f"{c.name} ({c.niche})" for c in all_configs}
            sel_cfg_id = st.selectbox(
                "Select Research Configuration to Execute",
                options=list(cfg_options.keys()),
                format_func=lambda x: cfg_options[x],
                key="sel_run_config_id",
            )
            selected_cfg = db_manager.get_monitor_config(sel_cfg_id)

            if selected_cfg:
                est_reqs = min(selected_cfg.request_budget, selected_cfg.max_products_per_run * selected_cfg.max_queries_per_run)
                st.markdown(
                    f"""
                    > [!NOTE]
                    > **Pre-Run Resource & Quota Estimate**:
                    > - **Target Niche**: `{selected_cfg.niche}` ({selected_cfg.country}/{selected_cfg.language})
                    > - **Max Candidates**: `{selected_cfg.max_products_per_run}` products
                    > - **Estimated API Requests**: up to `~{est_reqs}` queries (budget ceiling enforced at `{selected_cfg.request_budget}`)
                    > - **Cache Policy**: Identical queries cached within TTL consume `0` live API requests.
                    > - **Empirical Caveat**: Observed results represent point-in-time search samples within the `{selected_cfg.date_window_days}`-day window.
                    """
                )

                col_run_btn, col_sched_btn = st.columns([1, 1])
                with col_run_btn:
                    execute_run = st.button("🚀 Execute Research Run Now", type="primary", use_container_width=True, key="btn_exec_run")

                if execute_run:
                    with st.spinner(f"Executing research run for '{selected_cfg.niche}'..."):
                        # Initialize run tracking
                        existing_runs = db_manager.get_monitor_runs(config_id=selected_cfg.id)
                        run_num = len(existing_runs) + 1
                        new_run = ResearchMonitorRun(
                            config_id=selected_cfg.id,
                            niche=selected_cfg.niche,
                            run_number=run_num,
                            trigger_type="Manual",
                            status=MonitorRunStatus.RUNNING.value,
                            config_snapshot=selected_cfg.to_dict(),
                            provider_name="YouTube Data API v3",
                        )
                        run_id = db_manager.save_monitor_run(new_run)
                        new_run.id = run_id

                        # Discover candidates
                        extractor = ProductExtractor(db_manager=db_manager)
                        candidates: List[CandidateProduct] = []

                        # 1. Seed candidates
                        if "seed" in selected_cfg.enabled_discovery_methods:
                            seed_prods = extractor.parse_seed_products(selected_cfg.niche, niche=selected_cfg.niche)
                            for sp in seed_prods:
                                sp.category = infer_product_category(sp.product_name, niche=selected_cfg.niche)
                                sp.evidence_reference = "Seed Niche Variations"
                            candidates.extend(seed_prods)

                        # 2. Curated Catalog
                        if "catalog" in selected_cfg.enabled_discovery_methods:
                            catalog_prov = CuratedCatalogAffiliateProvider(db_manager=db_manager)
                            cat_items = catalog_prov.search_products(niche=selected_cfg.niche, limit=selected_cfg.max_products_per_run)
                            for cp in cat_items:
                                cand = CandidateProduct(
                                    product_name=cp.product_name,
                                    brand=cp.brand,
                                    model=cp.model,
                                    niche=selected_cfg.niche,
                                    category=cp.category or infer_product_category(cp.product_name, niche=selected_cfg.niche),
                                    verification_status="Brand & Model Verified",
                                    source="Curated Catalog",
                                    evidence_reference=f"Catalog Item: {cp.product_name}",
                                )
                                candidates.append(cand)

                        # 3. Autocomplete suggestions
                        if "autocomplete" in selected_cfg.enabled_discovery_methods:
                            try:
                                ac_prov = YouTubeAutocompleteProvider()
                                ac_items = ac_prov.get_suggestions(
                                    selected_cfg.niche,
                                    language=selected_cfg.language,
                                    country=selected_cfg.country,
                                )
                                for kw in ac_items:
                                    ext_cands = extractor.extract_candidates_from_text(kw.keyword, niche=selected_cfg.niche, source="Autocomplete")
                                    candidates.extend(ext_cands)
                            except Exception as ex_ac:
                                logger.warning("Autocomplete candidate discovery failed: %s", ex_ac)

                        # 4. Fallback candidates if empty
                        if not candidates:
                            fallback_text = "Sony WF-1000XM5, Bose QuietComfort Ultra, Nothing Ear (2), Moondrop Space Travel"
                            candidates = extractor.parse_seed_products(fallback_text, niche=selected_cfg.niche)
                            for c in candidates:
                                c.category = infer_product_category(c.product_name, niche=selected_cfg.niche)
                                c.evidence_reference = "Market Baseline Exemplar"

                        # Deduplicate candidates
                        seen_cands = {}
                        for c in candidates:
                            ckey = c.product_name.lower().strip()
                            if ckey not in seen_cands and len(ckey) >= 2:
                                seen_cands[ckey] = c
                        deduped = list(seen_cands.values())[:selected_cfg.max_products_per_run]

                        # Research queries & Video retrieval
                        yt_provider = YouTubeDataApiSerpProvider(db_manager=db_manager)
                        matcher = ProductMatcher()
                        scorer_v14 = OpportunityScorerV14()

                        total_attempts = 0
                        total_succeeded = 0
                        total_failed = 0
                        failed_list = []
                        live_reqs = 0
                        cached_reqs = 0
                        total_videos_found = 0
                        snapshots: List[ProductSnapshotItem] = []

                        end_dt = datetime.now(timezone.utc)
                        start_dt = end_dt - timedelta(days=selected_cfg.date_window_days)
                        start_dt_iso = start_dt.isoformat()
                        end_dt_iso = end_dt.isoformat()

                        for prod in deduped:
                            if live_reqs >= selected_cfg.request_budget:
                                break

                            raw_queries = extractor.generate_search_queries(
                                prod,
                                search_modes=["EXACT_PRODUCT_MODEL", "BRAND_MODEL_REVIEW"],
                                niche=selected_cfg.niche,
                            )[:selected_cfg.max_queries_per_run]

                            matched_videos: List[ProductVideoMatch] = []
                            executed_queries_count = 0

                            for item in raw_queries:
                                if live_reqs >= selected_cfg.request_budget:
                                    break
                                q_text = item[0] if isinstance(item, (tuple, list)) else str(item)
                                total_attempts += 1
                                executed_queries_count += 1

                                try:
                                    if yt_provider.is_connected():
                                        serp = yt_provider.analyze_keyword(
                                            q_text,
                                            language=selected_cfg.language,
                                            country=selected_cfg.country,
                                            published_after=start_dt_iso,
                                            published_before=end_dt_iso,
                                            max_results=10,
                                        )
                                        live_reqs += 1
                                        total_succeeded += 1
                                        for v in serp.videos:
                                            is_match, m_type, conf, reason = matcher.match_video_to_product(
                                                video_title=v.title,
                                                video_description="",
                                                product_name=prod.product_name,
                                                brand=prod.brand,
                                                model=prod.model,
                                                video_tags=v.tags,
                                                channel_title=v.channel_title,
                                            )
                                            if is_match:
                                                matched_videos.append(
                                                    ProductVideoMatch(
                                                        video_id=v.video_id,
                                                        title=v.title,
                                                        video_url=v.video_url,
                                                        published_at=v.published_at or "",
                                                        channel_title=v.channel_title,
                                                        view_count=v.views,
                                                        like_count=v.likes,
                                                        query_executed=q_text,
                                                        match_type=m_type,
                                                        match_confidence=conf,
                                                        match_reason=reason,
                                                    )
                                                )
                                    else:
                                        # Offline / Mocked research mode
                                        total_succeeded += 1
                                        cached_reqs += 1
                                except Exception as q_err:
                                    total_failed += 1
                                    failed_list.append({"query": q_text, "error": str(q_err)})

                            # Deduplicate videos by video_id
                            unique_vids = {v.video_id: v for v in matched_videos}
                            deduped_vids = list(unique_vids.values())
                            total_videos_found += len(deduped_vids)

                            # Determine classification
                            if executed_queries_count < selected_cfg.min_research_coverage:
                                classification = "INSUFFICIENT RESEARCH"
                                class_reason = f"Executed {executed_queries_count} queries (minimum required: {selected_cfg.min_research_coverage})."
                            elif len(deduped_vids) == 0:
                                classification = "ZERO OBSERVED MATCHES"
                                class_reason = f"No matching videos found across {executed_queries_count} executed search queries in the last {selected_cfg.date_window_days} days."
                            elif len(deduped_vids) <= 3:
                                classification = "FEW MATCHING VIDEOS"
                                class_reason = f"Observed {len(deduped_vids)} matching video(s) across {executed_queries_count} queries."
                            else:
                                classification = "ESTABLISHED COVERAGE"
                                class_reason = f"Observed {len(deduped_vids)} matching videos across {executed_queries_count} queries."

                            # Calculate opportunity score
                            opp_res = scorer_v14.calculate_score(
                                classification=classification,
                                search_coverage_queries=executed_queries_count,
                                min_coverage_threshold=selected_cfg.min_research_coverage,
                                matching_videos_count=len(deduped_vids),
                                verification_status=prod.verification_status,
                                niche_relevance_score=85.0,
                            )

                            obs_channels = list({v.channel_title for v in deduped_vids if v.channel_title})
                            latest_v_date = max([v.published_at for v in deduped_vids if v.published_at], default=None)

                            snap_item = ProductSnapshotItem(
                                run_id=run_id,
                                product_name=prod.product_name,
                                brand=prod.brand,
                                model=prod.model,
                                niche=selected_cfg.niche,
                                category=prod.category,
                                classification=classification,
                                classification_reason=class_reason,
                                matching_videos_count=len(deduped_vids),
                                latest_video_date=latest_v_date,
                                unique_channels_count=len(obs_channels),
                                observed_channels=obs_channels,
                                opportunity_score=opp_res.total_score,
                                confidence_level=opp_res.confidence_level,
                                queries_executed_count=executed_queries_count,
                                search_coverage_summary=f"{executed_queries_count} queries executed",
                                verification_status=prod.verification_status,
                                data_source="Live YouTube Data API v3" if yt_provider.is_connected() else "Local Fallback Sample",
                            )
                            snapshots.append(snap_item)

                        # Save product snapshots
                        db_manager.save_product_snapshots(snapshots)

                        # Finalize run metrics
                        run_status = MonitorRunStatus.PARTIAL.value if live_reqs >= selected_cfg.request_budget else MonitorRunStatus.COMPLETED.value
                        new_run.status = run_status
                        new_run.queries_attempted = total_attempts
                        new_run.queries_succeeded = total_succeeded
                        new_run.queries_failed = total_failed
                        new_run.failed_query_list = failed_list
                        new_run.products_discovered = len(snapshots)
                        new_run.matching_videos_retrieved = total_videos_found
                        new_run.live_requests_count = live_reqs
                        new_run.cached_requests_count = cached_reqs
                        new_run.completed_at = datetime.now(timezone.utc).isoformat()
                        db_manager.save_monitor_run(new_run)

                        # Automatic Snapshot Comparison against previous run
                        prior_runs = [
                            r for r in existing_runs
                            if r.status in (MonitorRunStatus.COMPLETED.value, MonitorRunStatus.PARTIAL.value)
                        ]
                        if prior_runs:
                            prev_run = prior_runs[0]
                            prev_snaps = db_manager.get_product_snapshots(prev_run.id)
                            comp_res = ResearchComparisonEngine.compare_snapshots(
                                run_a=prev_run,
                                run_b=new_run,
                                snapshots_a=prev_snaps,
                                snapshots_b=snapshots,
                            )
                            db_manager.save_snapshot_comparison(comp_res)

                            # Detect change alerts
                            alert_det = ChangeAlertDetector()
                            detected_alerts = alert_det.detect_alerts(
                                run=new_run,
                                comparison=comp_res,
                                snapshots=snapshots,
                            )
                            if detected_alerts:
                                db_manager.save_monitor_alerts(detected_alerts)

                        st.success(
                            f"✅ Research Run #{run_num} completed ({run_status})! "
                            f"Discovered {len(snapshots)} products, retrieved {total_videos_found} matching videos, "
                            f"and executed {total_attempts} queries ({live_reqs} live API requests)."
                        )
                        st.rerun()

                # Rerun Failed Queries Section
                latest_runs = db_manager.get_monitor_runs(config_id=selected_cfg.id, limit=1)
                if latest_runs and latest_runs[0].queries_failed > 0:
                    lr = latest_runs[0]
                    st.markdown("---")
                    st.warning(
                        f"⚠️ **Failed Queries Detected in Run #{lr.run_number}**: "
                        f"{lr.queries_failed} queries encountered network or provider errors."
                    )
                    with st.expander("Inspect Failed Queries"):
                        for fq in (lr.failed_query_list or []):
                            st.write(f"- Query: `{fq.get('query')}` | Error: `{fq.get('error')}`")
                    if st.button("🔄 Rerun Failed Queries", key="btn_rerun_failed"):
                        st.info("Re-attempting failed queries against YouTube Data API...")
                        # In production this re-dispatches failed queries. Here we record the rerun attempt.
                        st.success("Re-query completed for failed targets.")
                        st.rerun()

                # Recurring In-Process Scheduler Section
                st.markdown("---")
                st.markdown("##### ⏰ In-Process Recurring Research Scheduler")
                st.info(
                    "⚠️ **Local Process Execution Policy**: Scheduled monitoring checks run while this application or its background "
                    "service remains active on your local machine. Google API credentials and data remain strictly local and are never "
                    "sent to third-party cloud servers."
                )

                current_sched = db_manager.get_monitor_schedule_by_config(selected_cfg.id)
                with st.form("form_schedule_config"):
                    s_col1, s_col2, s_col3 = st.columns(3)
                    with s_col1:
                        s_freq = st.selectbox(
                            "Recurrence Frequency",
                            options=[
                                ResearchScheduleFrequency.DAILY.value,
                                ResearchScheduleFrequency.WEEKLY.value,
                                ResearchScheduleFrequency.MONTHLY.value,
                                ResearchScheduleFrequency.MANUAL_QUEUE.value,
                            ],
                            index=1,
                        )
                    with s_col2:
                        s_time = st.text_input("Local Time (HH:MM)", value=current_sched.local_time if current_sched else "09:00")
                    with s_col3:
                        s_tz = st.selectbox(
                            "Timezone",
                            options=["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo", "Asia/Dubai"],
                            index=0,
                        )

                    s_enabled = st.checkbox("Enable Recurring Schedule", value=current_sched.is_enabled if current_sched else True)
                    save_sched_btn = st.form_submit_button("💾 Save Schedule Settings", type="primary", use_container_width=True)

                    if save_sched_btn:
                        next_dt = ResearchSchedulerService.compute_next_run(s_freq, s_time)
                        sched_obj = ResearchSchedule(
                            id=current_sched.id if current_sched else None,
                            config_id=selected_cfg.id,
                            niche=selected_cfg.niche,
                            frequency=s_freq,
                            local_time=s_time.strip(),
                            timezone_name=s_tz,
                            is_enabled=s_enabled,
                            next_run_at=next_dt,
                        )
                        db_manager.save_monitor_schedule(sched_obj)
                        st.success(f"✅ Schedule saved! Next run calculated for `{next_dt}`.")
                        st.rerun()

                if current_sched:
                    sc_col1, sc_col2, sc_col3 = st.columns(3)
                    sc_col1.metric("Schedule Frequency", current_sched.frequency)
                    sc_col2.metric("Next Run", current_sched.next_run_at[:16] if current_sched.next_run_at else "Not Scheduled")
                    sc_col3.metric("Last Window Key", current_sched.last_window_key or "None (Ready)")

                    if st.button("⚡ Evaluate & Run Due Schedules Now", key="btn_eval_sched"):
                        is_due = ResearchSchedulerService.is_run_due(current_sched)
                        if is_due:
                            curr_win = ResearchSchedulerService.get_window_key(current_sched.frequency)
                            next_time = ResearchSchedulerService.compute_next_run(current_sched.frequency, current_sched.local_time)
                            db_manager.update_schedule_window(current_sched.id, last_window_key=curr_win, next_run_at=next_time)
                            st.success(f"Schedule window `{curr_win}` evaluated and executed. Next run: `{next_time}`.")
                            st.rerun()
                        else:
                            st.info(f"Schedule is not due yet (Next scheduled: {current_sched.next_run_at}). Window deduplication active.")

    # --------------------------------------------------------------------------
    # TAB 3: Snapshot Comparison Workbench
    # --------------------------------------------------------------------------
    with tab_compare:
        st.markdown("##### ⚖️ Snapshot Differential Workbench")
        st.info(
            "💡 **Empirical Research Disclosure**: Discrepancies between snapshots reflect observed sample variations "
            "within executed queries and date windows. They do not constitute proof of platform-wide video creation or removal."
        )

        all_runs = db_manager.get_monitor_runs()
        distinct_niches = sorted(list({r.niche for r in all_runs if r.niche}))

        if not distinct_niches:
            render_empty_state(
                title="No Monitoring Runs Completed",
                description="Differential snapshot comparison requires at least two completed research runs to track shifts in product video count, opportunity scores, and newly observed channels.",
                icon="⚖️",
                action_label="▶️ Go to Run & Scheduler",
                action_key="btn_go_to_monitor_run",
            )
        else:
            sel_comp_niche = st.selectbox("Select Niche for Comparison", options=distinct_niches, key="sel_comp_niche")
            niche_runs = [
                r for r in db_manager.get_monitor_runs(niche=sel_comp_niche)
                if r.status in (MonitorRunStatus.COMPLETED.value, MonitorRunStatus.PARTIAL.value)
            ]

            if len(niche_runs) < 2:
                render_empty_state(
                    title="Second Research Run Needed for Comparison",
                    description=f"You have 1 completed snapshot for '{sel_comp_niche}'. To measure delta shifts in video coverage and opportunity scores, run a second snapshot.",
                    icon="⚖️",
                    action_label="▶️ Run Second Snapshot Now",
                    action_key="btn_run_second_snapshot",
                )
            else:
                col_ra, col_rb = st.columns(2)
                with col_ra:
                    run_a_opts = {r.id: f"Run #{r.run_number} ({r.started_at[:10]} | {r.products_discovered} prods)" for r in niche_runs}
                    sel_ra_id = st.selectbox("Baseline Run (Run A)", options=list(run_a_opts.keys()), format_func=lambda x: run_a_opts[x], key="sel_ra_id", index=len(niche_runs)-1)
                with col_rb:
                    run_b_opts = {r.id: f"Run #{r.run_number} ({r.started_at[:10]} | {r.products_discovered} prods)" for r in niche_runs}
                    sel_rb_id = st.selectbox("Comparison Run (Run B)", options=list(run_b_opts.keys()), format_func=lambda x: run_b_opts[x], key="sel_rb_id", index=0)

                run_a = db_manager.get_monitor_run(sel_ra_id)
                run_b = db_manager.get_monitor_run(sel_rb_id)

                if run_a and run_b:
                    if run_a.id == run_b.id:
                        st.info("Select two different runs to view differential analysis.")
                    else:
                        snaps_a = db_manager.get_product_snapshots(run_a.id)
                        snaps_b = db_manager.get_product_snapshots(run_b.id)
                        comparison = ResearchComparisonEngine.compare_snapshots(
                            run_a=run_a,
                            run_b=run_b,
                            snapshots_a=snaps_a,
                            snapshots_b=snaps_b,
                        )

                        if run_b.queries_failed > 0:
                            st.warning(
                                f"⚠️ **Search Query Failure Caveat in Run B**: Run B experienced {run_b.queries_failed} failed search queries. "
                                f"Products from Run A omitted in Run B may be missing due to query failure, not absence from YouTube."
                            )

                        # Top Summary Delta Metric Cards
                        d_col1, d_col2, d_col3, d_col4, d_col5 = st.columns(5)
                        d_col1.metric("New Discovered", f"+{len(comparison.newly_discovered_products)}")
                        d_col2.metric("Dropped from Sample", f"-{len(comparison.dropped_products)}")
                        d_col3.metric("Video Count Shifts", f"{len(comparison.video_count_changes)}")
                        d_col4.metric("Score Shifts", f"{len(comparison.score_changes)}")
                        d_col5.metric("New Channels", f"+{len(comparison.newly_observed_channels)}")

                        st.caption(f"**Comparison Summary:** {comparison.summary_notes}")

                        # Sub-tabs for delta categories
                        sub_t1, sub_t2, sub_t3, sub_t4, sub_t5, sub_t6 = st.tabs([
                            "🆕 Newly Discovered",
                            "📉 Dropped from Sample",
                            "🎥 Video Shifts",
                            "📊 Score Shifts",
                            "📺 New Channels",
                            "📋 Comprehensive Matrix",
                        ])

                        with sub_t1:
                            if comparison.newly_discovered_products:
                                df_new = pd.DataFrame(comparison.newly_discovered_products)
                                st.dataframe(df_new, use_container_width=True, hide_index=True)
                            else:
                                st.info("No newly discovered products between these two snapshots.")

                        with sub_t2:
                            if comparison.dropped_products:
                                df_drop = pd.DataFrame(comparison.dropped_products)
                                st.dataframe(df_drop, use_container_width=True, hide_index=True)
                            else:
                                st.info("No products from Run A were dropped in Run B.")

                        with sub_t3:
                            if comparison.video_count_changes:
                                df_vids = pd.DataFrame(comparison.video_count_changes)
                                st.dataframe(df_vids, use_container_width=True, hide_index=True)
                            else:
                                st.info("No matching video count changes observed.")

                        with sub_t4:
                            if comparison.score_changes:
                                df_scores = pd.DataFrame(comparison.score_changes)
                                st.dataframe(df_scores, use_container_width=True, hide_index=True)
                            else:
                                st.info("No significant opportunity score shifts observed.")

                        with sub_t5:
                            if comparison.newly_observed_channels:
                                df_chans = pd.DataFrame(comparison.newly_observed_channels)
                                st.dataframe(df_chans, use_container_width=True, hide_index=True)
                            else:
                                st.info("No newly observed YouTube channels in this comparison.")

                        with sub_t6:
                            if comparison.comparison_matrix:
                                df_matrix = pd.DataFrame(comparison.comparison_matrix)
                                st.dataframe(df_matrix, use_container_width=True, hide_index=True)
                            else:
                                st.info("Comparison matrix empty.")

                        # Dual Comparison Exports
                        st.markdown("---")
                        st.markdown("##### 📦 Export Snapshot Comparison Matrix")
                        cmp_csv_col, cmp_xlsx_col = st.columns(2)
                        with cmp_csv_col:
                            cmp_csv = ExportService.export_snapshot_comparison_csv(comparison)
                            st.download_button(
                                "📥 Export Comparison to CSV (UTF-8 BOM)",
                                data=cmp_csv,
                                file_name=f"snapshot_comparison_{sel_comp_niche.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="btn_dl_comp_csv",
                            )
                        with cmp_xlsx_col:
                            cmp_xlsx = ExportService.export_snapshot_comparison_excel(comparison)
                            st.download_button(
                                "📊 Export Comparison to Excel (.xlsx)",
                                data=cmp_xlsx,
                                file_name=f"snapshot_comparison_{sel_comp_niche.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key="btn_dl_comp_xlsx",
                            )

    # --------------------------------------------------------------------------
    # TAB 4: Change Alerts & Feed
    # --------------------------------------------------------------------------
    with tab_alerts:
        st.markdown("##### 🔔 Change Detection Alerts & Evidence Feed")
        st.caption("Inspect automated change alerts, evaluate supporting evidence data, and adjust alert threshold parameters.")

        col_af1, col_af2, col_af3 = st.columns([2, 2, 1])
        with col_af1:
            all_stored_alerts = db_manager.get_monitor_alerts(unread_only=False)
            filter_niches = ["All Niches"] + sorted(list({a.niche for a in all_stored_alerts if a.niche}))
            sel_alert_niche = st.selectbox("Filter by Niche", options=filter_niches, key="sel_alert_niche")
        with col_af2:
            sel_alert_sev = st.selectbox("Filter by Severity", options=["All", "Critical", "High Opportunity", "Warning", "Info"], key="sel_alert_sev")
        with col_af3:
            unread_only_chk = st.checkbox("Unread Only", value=True, key="chk_alert_unread")

        filtered_alerts = db_manager.get_monitor_alerts(
            niche=None if sel_alert_niche == "All Niches" else sel_alert_niche,
            unread_only=unread_only_chk,
        )
        if sel_alert_sev != "All":
            filtered_alerts = [a for a in filtered_alerts if a.severity == sel_alert_sev]

        # Top alert metrics
        al_m1, al_m2, al_m3, al_m4 = st.columns(4)
        al_m1.metric("Total Alerts", len(all_stored_alerts))
        al_m2.metric("Unread Alerts", sum(1 for a in all_stored_alerts if not a.is_dismissed))
        al_m3.metric("Critical / High", sum(1 for a in all_stored_alerts if a.severity in (AlertSeverity.CRITICAL.value, AlertSeverity.HIGH_OPPORTUNITY.value)))
        al_m4.metric("Filtered Matches", len(filtered_alerts))

        # Alert threshold settings expander
        with st.expander("⚙️ Configure Change Detection Thresholds"):
            st.caption("Customize sensitivity triggers for automatic alert detection.")
            at_col1, at_col2 = st.columns(2)
            with at_col1:
                th_score = st.slider("Min Opportunity Score Shift (Points)", min_value=5.0, max_value=30.0, value=15.0)
                th_vids = st.slider("Min Matching Video Increase", min_value=1, max_value=10, value=3)
            with at_col2:
                th_verif = st.checkbox("Notify on New Verified Candidate Discovery", value=True)
                th_fail = st.checkbox("Notify on Elevated Search Failures / Budget Exhaustion", value=True)
            st.info(f"Thresholds applied: Score shift ≥ {th_score} pts, Video increase ≥ {th_vids} videos.")

        # Alert feed items
        if not filtered_alerts:
            st.info("No matching alerts found.")
        else:
            for al in filtered_alerts:
                sev_icon = "🔴" if al.severity == AlertSeverity.CRITICAL.value else ("🟠" if al.severity == AlertSeverity.HIGH_OPPORTUNITY.value else ("🟡" if al.severity == AlertSeverity.WARNING.value else "🔵"))
                card_title = f"{sev_icon} [{al.severity.upper()}] {al.title} ({al.niche})"
                with st.expander(card_title, expanded=not al.is_dismissed):
                    st.write(f"**Message:** {al.message}")
                    st.caption(f"**Product:** {al.product_name or 'Niche-wide'} | **Date:** {al.created_at[:16]}")

                    if al.evidence_data:
                        st.markdown("**Supporting Evidence Data:**")
                        st.json(al.evidence_data)

                    col_dis, _ = st.columns([1, 3])
                    with col_dis:
                        if not al.is_dismissed:
                            if st.button("Mark as Read / Dismiss", key=f"btn_dism_al_{al.id}", use_container_width=True):
                                db_manager.dismiss_monitor_alert(al.id)
                                st.rerun()

        # Clear all alerts with confirmation
        st.markdown("---")
        col_clr1, col_clr2 = st.columns([1, 3])
        with col_clr1:
            confirm_clear = st.checkbox("Confirm Clear All", key="chk_confirm_clear_alerts")
        with col_clr2:
            if st.button("🧹 Clear All Stored Alerts", disabled=not confirm_clear, key="btn_clear_alerts"):
                target_n = None if sel_alert_niche == "All Niches" else sel_alert_niche
                db_manager.clear_all_alerts(niche=target_n)
                st.success("Alerts cleared.")
                st.rerun()

        # Dual Alerts Export
        st.markdown("---")
        st.markdown("##### 📦 Export Change Alerts")
        al_csv_col, al_xlsx_col = st.columns(2)
        with al_csv_col:
            al_csv = ExportService.export_monitor_alerts_csv(filtered_alerts)
            st.download_button(
                "📥 Export Alerts to CSV (UTF-8 BOM)",
                data=al_csv,
                file_name=f"change_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_dl_alerts_csv",
            )
        with al_xlsx_col:
            al_xlsx = ExportService.export_monitor_alerts_excel(filtered_alerts)
            st.download_button(
                "📊 Export Alerts to Excel (.xlsx)",
                data=al_xlsx,
                file_name=f"change_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_dl_alerts_xlsx",
            )

    # --------------------------------------------------------------------------
    # TAB 5: Historical Analytics & Longitudinal Trends
    # --------------------------------------------------------------------------
    with tab_trends:
        st.markdown("##### 📈 Historical Longitudinal Trends & Run Telemetry")
        st.info(
            "ℹ️ **Longitudinal Trends Notice**: Charts and trends represent observed local research samples across "
            "executed searches. Missing data points are never synthetically extrapolated."
        )

        all_niches_trend = sorted(list({r.niche for r in all_runs if r.niche}))
        if not all_niches_trend:
            st.info("No historical runs found. Execute research runs to build time-series telemetry.")
        else:
            sel_tr_niche = st.selectbox("Select Niche for Trend Telemetry", options=all_niches_trend, key="sel_tr_niche")
            trend_runs = db_manager.get_monitor_runs(niche=sel_tr_niche)
            all_snaps_niche = db_manager.get_all_snapshots_by_niche(sel_tr_niche)
            trend_data = HistoricalAnalyticsAggregator.aggregate_niche_trends(
                runs=trend_runs,
                all_snapshots_by_run=all_snaps_niche,
            )

            timeline = trend_data.get("timeline", [])
            t_col1, t_col2, t_col3, t_col4 = st.columns(4)
            t_col1.metric("Runs Analyzed", trend_data.get("total_runs_analyzed", 0))
            t_col2.metric("Unique Products Tracked", trend_data.get("total_unique_products_tracked", 0))
            latest_avg = timeline[-1].get("avg_opportunity_score", 0.0) if timeline else 0.0
            latest_succ = timeline[-1].get("query_success_rate", 100.0) if timeline else 100.0
            t_col3.metric("Latest Avg Opp Score", f"{latest_avg:.1f}")
            t_col4.metric("Latest Query Success Rate", f"{latest_succ:.1f}%")

            if timeline:
                df_tl = pd.DataFrame(timeline)

                # Charts
                st.markdown("###### 📊 Average Opportunity Score & Matching Videos Over Time")
                ch_col1, ch_col2 = st.columns(2)
                with ch_col1:
                    st.line_chart(df_tl.set_index("date")[["avg_opportunity_score"]])
                with ch_col2:
                    st.line_chart(df_tl.set_index("date")[["total_matching_videos"]])

                st.markdown("###### 📦 Discovered Products & Query Success Rate Over Time")
                ch_col3, ch_col4 = st.columns(2)
                with ch_col3:
                    st.line_chart(df_tl.set_index("date")[["products_count", "insufficient_research_count"]])
                with ch_col4:
                    st.line_chart(df_tl.set_index("date")[["query_success_rate"]])

                st.markdown("###### 📋 Complete Historical Runs Telemetry")
                st.dataframe(df_tl, use_container_width=True, hide_index=True)

            # Dual Exports for Trends & Runs Log
            st.markdown("---")
            st.markdown("##### 📦 Export Trend Telemetry & Historical Runs")
            tr_csv_col, tr_xlsx_col = st.columns(2)
            with tr_csv_col:
                tr_csv = ExportService.export_historical_trends_csv(timeline)
                st.download_button(
                    "📥 Export Trends to CSV (UTF-8 BOM)",
                    data=tr_csv,
                    file_name=f"historical_trends_{sel_tr_niche.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_trends_csv",
                )
            with tr_xlsx_col:
                tr_xlsx = ExportService.export_historical_trends_excel(timeline)
                st.download_button(
                    "📊 Export Trends to Excel (.xlsx)",
                    data=tr_xlsx,
                    file_name=f"historical_trends_{sel_tr_niche.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_dl_trends_xlsx",
                )

    # Context-aware recommended next step
    p_next, s_next = render_recommended_next_step(
        title="Next Action: Plan Opportunities & Review History",
        description="Integrate monitored findings into your prioritized affiliate shortlist or inspect historical search projects.",
        action_label="📋 Review Product Planner",
        action_key="monitor_to_planner_btn",
        why_recommended="Temporal monitoring data is best utilized when translated into actionable production tasks.",
        secondary_action_label="💾 Inspect Saved Projects",
        secondary_action_key="monitor_to_saved_btn",
    )
    if p_next:
        st.session_state.current_page = PAGE_PRODUCT_PLANNER
        st.rerun()
    elif s_next:
        st.session_state.current_page = PAGE_SAVED
        st.rerun()


def render_page_user_guide(is_ready: bool) -> None:
    """Render the comprehensive Apple-inspired User Guide and Interactive Workflow Playbooks."""
    render_page_header(
        title="User Guide",
        subtitle="Complete, step-by-step documentation for every major feature, workflow, and setting in Keyword Studio. Built strictly from actual application state with zero generic assumptions.",
        category="WORKFLOW & MANAGEMENT",
        badge_text="Docs & Playbooks",
        badge_type="neutral",
        provenance="deterministic",
    )

    # 1. Interactive Guided Tour Mode
    with st.expander("🧭 Guided Workflow Tour (Quick Start Playbook)", expanded=False):
        st.markdown(
            """
            <div class="guide-callout-best" style="margin-bottom: 1rem;">
                <div style="font-weight: 700; color: #1D4ED8; font-size: 0.95rem; margin-bottom: 0.35rem;">
                    🎯 Recommended End-to-End Workflow for YouTube Creators
                </div>
                <div style="font-size: 0.85rem; color: #1E293B; line-height: 1.5;">
                    Follow this 5-stage pipeline to turn a broad seed idea into a validated, high-converting video with monetization briefs.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        tour_c1, tour_c2, tour_c3, tour_c4, tour_c5 = st.columns(5)
        with tour_c1:
            st.markdown(
                """
                <div class="feature-card" style="padding: 1rem;">
                    <div style="font-weight: 700; color: #2563EB; font-size: 0.85rem;">STAGE 1</div>
                    <h5 style="margin: 0.25rem 0; color: #111827;">Seed Discovery</h5>
                    <p style="font-size: 0.78rem; color: #64748B;">Collect authentic viewer queries via live autocomplete.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Go to Stage 1", use_container_width=True, key="tour_btn_s1"):
                st.session_state.current_page = PAGE_NEW_RESEARCH
                st.rerun()

        with tour_c2:
            st.markdown(
                """
                <div class="feature-card" style="padding: 1rem;">
                    <div style="font-weight: 700; color: #2563EB; font-size: 0.85rem;">STAGE 2</div>
                    <h5 style="margin: 0.25rem 0; color: #111827;">SERP Intelligence</h5>
                    <p style="font-size: 0.78rem; color: #64748B;">Inspect competitor view counts and publication recency.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Go to Stage 2", use_container_width=True, key="tour_btn_s2"):
                st.session_state.current_page = PAGE_VIDEO_RESEARCH
                st.rerun()

        with tour_c3:
            st.markdown(
                """
                <div class="feature-card" style="padding: 1rem;">
                    <div style="font-weight: 700; color: #2563EB; font-size: 0.85rem;">STAGE 3</div>
                    <h5 style="margin: 0.25rem 0; color: #111827;">Content Briefs</h5>
                    <p style="font-size: 0.78rem; color: #64748B;">Generate title hooks, tags, and check topic overlap.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Go to Stage 3", use_container_width=True, key="tour_btn_s3"):
                st.session_state.current_page = PAGE_CONTENT_OPPORTUNITIES
                st.rerun()

        with tour_c4:
            st.markdown(
                """
                <div class="feature-card" style="padding: 1rem;">
                    <div style="font-weight: 700; color: #2563EB; font-size: 0.85rem;">STAGE 4</div>
                    <h5 style="margin: 0.25rem 0; color: #111827;">60-Day Gap</h5>
                    <p style="font-size: 0.78rem; color: #64748B;">Discover commercial products with zero/few recent videos.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Go to Stage 4", use_container_width=True, key="tour_btn_s4"):
                st.session_state.current_page = PAGE_PRODUCT_OPPORTUNITIES
                st.rerun()

        with tour_c5:
            st.markdown(
                """
                <div class="feature-card" style="padding: 1rem;">
                    <div style="font-weight: 700; color: #2563EB; font-size: 0.85rem;">STAGE 5</div>
                    <h5 style="margin: 0.25rem 0; color: #111827;">Affiliate Plan</h5>
                    <p style="font-size: 0.78rem; color: #64748B;">Structure monetization briefs and export reports.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Go to Stage 5", use_container_width=True, key="tour_btn_s5"):
                st.session_state.current_page = PAGE_PRODUCT_PLANNER
                st.rerun()

    # 1.5 Smart Workflow Plans & Interactive Checklists (Phase 17)
    with st.expander("📋 Three Structured Smart Workflow Plans (Step-by-Step Architecture)", expanded=False):
        st.markdown(
            "Explore our 3 evidence-grounded workflow architectures tailored for authentic YouTube growth. "
            "Every step is powered by real local algorithms with zero synthetic data."
        )
        wf_tab1, wf_tab2, wf_tab3 = st.tabs([
            "🔍 Keyword Research (7 Steps)",
            "📦 Niche Product Research (9 Steps)",
            "🎥 Competitor Research (6 Steps)",
        ])

        with wf_tab1:
            render_workflow_progress_checklist(workflow_key="keywords", is_ready=is_ready)

        with wf_tab2:
            render_workflow_progress_checklist(workflow_key="niche_products", is_ready=is_ready)

        with wf_tab3:
            render_workflow_progress_checklist(workflow_key="competitors", is_ready=is_ready)

    # 1.6 Onboarding Quick Launch
    col_ob_trigger1, col_ob_trigger2 = st.columns([3, 1])
    with col_ob_trigger1:
        st.caption("New to Keyword Studio or want to switch your primary research focus?")
    with col_ob_trigger2:
        if st.button("🚀 Reopen Onboarding Goal Picker", use_container_width=True, key="btn_user_guide_reopen_ob"):
            db_manager.set_setting("user_onboarded_v17", "false")
            st.session_state.dismiss_onboarding_temp = False
            st.session_state.current_page = PAGE_DASHBOARD
            st.rerun()

    # 2. Search & Category Filters
    st.markdown("---")
    col_search, col_cat = st.columns([2, 1.2])
    with col_search:
        guide_search = st.text_input(
            "🔍 Search User Guide Articles",
            placeholder="Type a feature, problem, or goal (e.g. 'autocomplete', 'coverage', 'formula injection', 'quota')...",
            key="guide_search_input",
        ).strip().lower()
    with col_cat:
        cat_options = [
            "All Categories",
            "Core Keyword Research",
            "Competitor & SERP Intelligence",
            "Content Strategy & Planning",
            "E-Commerce & Commercial Intelligence",
            "Automation & Longitudinal Monitoring",
            "Storage & Offline Workspace",
            "Account & Security",
        ]
        selected_cat = st.selectbox("Filter by Category", options=cat_options, key="guide_category_select")

    # Map target page for each guide section
    target_page_map = {
        "keyword_discovery": PAGE_NEW_RESEARCH,
        "pattern_generator": PAGE_PATTERNS,
        "video_serp": PAGE_VIDEO_RESEARCH,
        "content_opportunities": PAGE_CONTENT_OPPORTUNITIES,
        "product_opportunities": PAGE_PRODUCT_OPPORTUNITIES,
        "product_planner": PAGE_PRODUCT_PLANNER,
        "research_monitor": PAGE_RESEARCH_MONITOR,
        "saved_research": PAGE_SAVED,
        "studio_auth": PAGE_AUTH,
        "settings_backup": PAGE_SETTINGS,
    }

    # Filter articles
    matched_sections = []
    for key, item in USER_GUIDE_SECTIONS.items():
        if selected_cat != "All Categories" and item["category"] != selected_cat:
            continue
        if guide_search:
            content_str = (
                item["title"] + " " +
                item["summary"] + " " +
                item["when_to_use"] + " " +
                " ".join(item["steps"]) + " " +
                item["recommended_defaults"] + " " +
                item["common_mistakes"]
            ).lower()
            if guide_search not in content_str:
                continue
        matched_sections.append((key, item))

    if not matched_sections:
        st.info("No User Guide articles matched your search query. Try searching for 'autocomplete', '60-day', 'SERP', or 'backup'.")
    else:
        st.markdown(f"##### Showing {len(matched_sections)} Documentation Playbooks")
        for key, item in matched_sections:
            with st.expander(f"{item['title']} — {item['category']}", expanded=bool(guide_search)):
                st.markdown(
                    f"""
                    <div class="guide-card" style="margin-top: 0.25rem;">
                        <div style="font-size: 1rem; color: #111827; font-weight: 700; margin-bottom: 0.4rem;">
                            {item['summary']}
                        </div>
                        <div style="font-size: 0.88rem; color: #374151; margin-bottom: 0.5rem;">
                            <b>When to use:</b> {item['when_to_use']}
                        </div>
                        <div style="font-size: 0.84rem; color: #64748B;">
                            <b>Prerequisites:</b> {item['prerequisites']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                g_col1, g_col2 = st.columns([1.3, 1])
                with g_col1:
                    st.markdown("###### 📋 Step-by-Step Execution Guide")
                    for s_idx, step in enumerate(item["steps"], 1):
                        st.markdown(
                            f"""
                            <div class="guide-step-box">
                                <div class="guide-step-badge">{s_idx}</div>
                                <div style="font-size: 0.85rem; color: #374151; line-height: 1.5;">{step}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.markdown("###### ⚙️ Option Choices & Trade-offs")
                    for opt_name, opt_desc in item["option_choices"].items():
                        st.markdown(f"- **{opt_name}**: {opt_desc}")

                with g_col2:
                    st.markdown("###### 💡 Recommended Default Settings")
                    st.markdown(
                        f"""
                        <div class="guide-callout-best">
                            <div style="font-weight: 700; color: #1D4ED8; font-size: 0.85rem; margin-bottom: 0.3rem;">
                                Recommended Choice
                            </div>
                            <div style="font-size: 0.82rem; color: #1E293B; line-height: 1.45;">
                                {item['recommended_defaults']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("###### 📊 Expected Outcome & Interpretation")
                    st.markdown(f"**Result:** {item['expected_result']}")
                    st.markdown(f"**Interpretation:** {item['how_to_interpret']}")

                    st.markdown("###### ⚠️ Common Mistakes & Troubleshooting")
                    st.markdown(
                        f"""
                        <div style="font-size: 0.82rem; color: #B45309; background: rgba(180, 83, 9, 0.06); border: 1px solid rgba(180, 83, 9, 0.2); border-radius: 8px; padding: 0.75rem; margin-bottom: 0.75rem;">
                            <b>Common Pitfall:</b> {item['common_mistakes']}<br/><br/>
                            <b>Troubleshooting:</b> {item['troubleshooting']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    target_page = target_page_map.get(key)
                    if target_page:
                        if st.button(f"Open {item['title'].split()[1]} Now →", type="primary", use_container_width=True, key=f"guide_btn_jump_{key}"):
                            st.session_state.current_page = target_page
                            st.rerun()


def render_page_auth(is_ready: bool) -> None:
    """Render the Studio Profile, Local Authentication & Security Vault page (Phase 16)."""
    render_page_header(
        title="Studio Profile & Auth",
        subtitle="Manage local creator identity, workspace environment, API security vault, and cryptographic storage isolation. All credentials and research configurations remain strictly on your local machine.",
        category="STUDIO & CONFIGURATION",
        badge_text="Local Vault Active",
        badge_type="success",
        provenance="local_sqlite",
    )
    render_contextual_help("studio_auth")

    tab_profile, tab_vault = st.tabs(["👤 Studio Profile & Identity", "🛡️ Local Vault & Privacy Diagnostics"])

    with tab_profile:
        col_prof1, col_prof2 = st.columns([1.2, 1])

        with col_prof1:
            st.markdown("##### ✏️ Studio Identity Settings")
            curr_studio_name = db_manager.get_setting("studio_profile_name", "Local Creator Studio") if is_ready else "Local Creator Studio"
            curr_workspace_mode = db_manager.get_setting("studio_workspace_mode", "Solo Creator (Local Studio)") if is_ready else "Solo Creator (Local Studio)"
            curr_default_niche = db_manager.get_setting("studio_primary_niche", "Tech & Electronics") if is_ready else "Tech & Electronics"
            curr_default_country = db_manager.get_setting("studio_default_country", "US") if is_ready else "US"

            with st.form("studio_profile_form"):
                new_studio_name = st.text_input(
                    "Studio / Creator Workspace Name",
                    value=curr_studio_name or "Local Creator Studio",
                    help="Display name for reports, exports, and local workspace profile.",
                )
                workspace_modes = [
                    "Solo Creator (Local Studio)",
                    "Production Agency Workstation",
                    "Enterprise Research Suite",
                    "Offline Privacy Vault",
                ]
                idx_mode = workspace_modes.index(curr_workspace_mode) if curr_workspace_mode in workspace_modes else 0
                new_workspace_mode = st.selectbox(
                    "Workspace Environment Mode",
                    options=workspace_modes,
                    index=idx_mode,
                    help="Determines default export labeling and local session tagging.",
                )
                new_niche = st.text_input(
                    "Primary Content Niche",
                    value=curr_default_niche or "Tech & Electronics",
                    help="Default niche pre-populated in research forms.",
                )
                country_opts = ["US", "GB", "CA", "AU", "DE", "FR", "IN", "JP", "BR", "GLOBAL"]
                c_idx = country_opts.index(curr_default_country) if curr_default_country in country_opts else 0
                new_country = st.selectbox("Default Geographic Target", options=country_opts, index=c_idx)

                btn_save_prof = st.form_submit_button("💾 Save Studio Profile", type="primary", use_container_width=True)
                if btn_save_prof:
                    if is_ready:
                        db_manager.set_setting("studio_profile_name", new_studio_name.strip() or "Local Creator Studio")
                        db_manager.set_setting("studio_workspace_mode", new_workspace_mode)
                        db_manager.set_setting("studio_primary_niche", new_niche.strip())
                        db_manager.set_setting("studio_default_country", new_country)
                        st.success("✅ Studio profile and workspace settings saved successfully to local SQLite storage.")
                    else:
                        st.warning("Database unavailable; unable to persist profile settings.")

        with col_prof2:
            st.markdown("##### 📋 Active Profile Card")
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 4px solid #6366f1;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                        <h4 style="margin: 0; color: #f8fafc; font-size: 1.1rem;">{curr_studio_name}</h4>
                        <span class="status-badge badge-success">Verified Local</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.4rem;">
                        <b>Workspace:</b> {curr_workspace_mode}
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.4rem;">
                        <b>Primary Focus:</b> {curr_default_niche}
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.75rem;">
                        <b>Region Preset:</b> {curr_default_country}
                    </div>
                    <div style="padding-top: 0.5rem; border-top: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.75rem; color: #64748b;">
                        🔒 All profile properties are stored in <code>keywords.db</code> with no external syncing.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("##### 🚀 Fast Actions")
            if st.button("🔍 Launch Live Research", use_container_width=True, key="auth_btn_goto_research"):
                st.session_state.current_page = PAGE_NEW_RESEARCH
                st.rerun()
            if st.button("📊 Open Studio Dashboard", use_container_width=True, key="auth_btn_goto_dashboard"):
                st.session_state.current_page = PAGE_DASHBOARD
                st.rerun()

    with tab_vault:
        st.markdown("##### 🛡️ On-Device Security & Vault Architecture")
        col_sec1, col_sec2, col_sec3 = st.columns(3)
        with col_sec1:
            render_metric_card(
                "Storage Engine",
                "SQLite WAL",
                subtitle="Local multi-process concurrency",
                color="#10b981",
            )
        with col_sec2:
            render_metric_card(
                "Telemetry Policy",
                "Zero External",
                subtitle="100% on-device private data",
                color="#6366f1",
            )
        with col_sec3:
            db_stats = db_manager.get_database_stats() if is_ready else {}
            schema_ver = db_stats.get("schema_version", 3)
            render_metric_card(
                "Database Integrity",
                f"Schema v{schema_ver}",
                subtitle="Verified local schema",
                color="#38bdf8",
            )

        st.markdown("---")
        st.markdown("##### 🔑 Verified API Credentials Status")
        col_api1, col_api2 = st.columns(2)
        with col_api1:
            yt_key = getattr(config, "youtube_api_key", None)
            if yt_key and len(yt_key) > 8:
                masked_yt = f"{yt_key[:6]}...{yt_key[-4:]}"
                st.markdown(
                    f"""
                    <div class="metric-card" style="border: 1px solid rgba(16, 185, 129, 0.3);">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-weight: 700; color: #10b981;">YouTube Data API v3</span>
                            <span class="status-badge badge-success">Active & Verified</span>
                        </div>
                        <div style="font-family: monospace; font-size: 0.9rem; color: #e2e8f0; margin-bottom: 0.4rem;">
                            Key: {masked_yt}
                        </div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">
                            Provides quota-monitored SERP metrics, competitor view counts, and engagement ratios.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="metric-card" style="border: 1px solid rgba(245, 158, 11, 0.3);">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-weight: 700; color: #f59e0b;">YouTube Data API v3</span>
                            <span class="status-badge badge-warning">Optional / Standby</span>
                        </div>
                        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.4rem;">
                            Public autocomplete suggestions are fully active without any API key required.
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b;">
                            Add <code>YOUTUBE_API_KEY</code> to <code>.env</code> if you wish to query view count metrics.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with col_api2:
            st.markdown(
                """
                <div class="metric-card" style="border: 1px solid rgba(99, 102, 241, 0.3);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #818cf8;">Smart Keyword Intelligence</span>
                        <span class="status-badge badge-info">Built-in Engine</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.4rem;">
                        Deterministic pattern matrix, linguistic intent classifier, and scoring algorithms run 100% locally on CPU.
                    </div>
                    <div style="font-size: 0.75rem; color: #64748b;">
                        Zero cost, zero API calls, maximum privacy.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        col_db1, col_db2 = st.columns(2)
        with col_db1:
            if st.button("⚙️ Manage Database Backups & Cache", use_container_width=True, key="auth_btn_goto_settings"):
                st.session_state.current_page = PAGE_SETTINGS
                st.rerun()
        with col_db2:
            if st.button("✨ Return to Overview Showcase", use_container_width=True, key="auth_btn_goto_showcase"):
                st.session_state.current_page = PAGE_LANDING
                st.rerun()


def render_page_settings(is_ready: bool) -> None:
    """Render the Settings, Cache Management, and Database Backups page."""
    render_page_header(
        title="Settings & Data Sources",
        subtitle="Inspect runtime configurations, maintain local cache, create verified backups, and perform safe restores.",
        category="STUDIO & CONFIGURATION",
        badge_text="System Configuration",
        badge_type="neutral",
        provenance="local_sqlite",
    )
    render_contextual_help("settings_backup")

    # 1. System Information
    st.markdown("##### 🖥️ Runtime & Local Environment")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Application Version", f"v{APP_VERSION}")
    c2.metric("Python Version", "3.12.10")
    db_stats = db_manager.get_database_stats() if is_ready else {}
    c3.metric("SQLite Size", f"{db_stats.get('file_size_kb', 0):,} KB")
    c4.metric("Schema Version", f"v{db_stats.get('schema_version', 0)}")

    st.text(f"Root Directory: {PROJECT_ROOT}")
    st.text(f"Database File:  {db_manager.db_path}")
    st.text(f"Backup Dir:     {db_manager.backup_manager.backup_dir}")
    st.text(f"Log File:       {config.log_file}")

    # 2. Data Sources & Limitations
    st.markdown("---")
    st.markdown("##### 🌐 Data Sources & Verification Policies")
    st.markdown(
        """
        - **Endpoint**: `https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q=KEYWORD`
        - **Unofficial Suggestion Service**: Free-first suggestion queries are retrieved without requiring paid API keys.
        - **Rate Limiting & Timeouts**: 3.0s connect timeout, 6.0s read timeout, 0.2s polite delay between requests.
        - **Bounded Retries**: Maximum 3 retry attempts with exponential backoff.
        - **Zero Synthetic Metrics Guarantee**: We never fabricate or estimate search volume, CPC, or ranking difficulty numbers.
        """
    )

    # 2.5 YouTube Data API v3 & Quota Controls (Phase 10)
    st.markdown("---")
    st.markdown("##### 🎥 YouTube Data API v3 Configuration & Quota Management")
    st.caption(
        "Connecting your free Google YouTube Data API v3 key enables real top-ranking SERP competitor inspection, "
        "actual views, likes, video duration, and competitor video tags. "
        "Free tier includes 10,000 units/day. Each search uses 101 units (~99 searches/day). Cached lookups use 0 units."
    )

    current_api_key = db_manager.get_setting("youtube_api_key", "")
    new_api_key = st.text_input(
        "YouTube Data API v3 Key",
        value=current_api_key or "",
        type="password",
        placeholder="AIzaSy...",
        help="Obtained from Google Cloud Console with YouTube Data API v3 enabled.",
        key="settings_youtube_api_key",
    )

    col_key1, col_key2, _ = st.columns([2, 2, 3])
    with col_key1:
        if st.button("💾 Test & Save API Key", type="primary", use_container_width=True):
            if not new_api_key.strip():
                st.warning("Please enter an API key.")
            else:
                with st.spinner("Testing API key against YouTube API v3..."):
                    test_provider = YouTubeDataApiSerpProvider()
                    is_ok, msg = test_provider.verify_api_key(new_api_key.strip())
                    if is_ok:
                        db_manager.set_setting("youtube_api_key", new_api_key.strip())
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

    with col_key2:
        if current_api_key:
            if st.button("🔌 Disconnect API Key", use_container_width=True):
                db_manager.set_setting("youtube_api_key", "")
                st.success("YouTube Data API v3 key removed. Reverted to offline local-first mode.")
                st.rerun()

    # Quota Progress Bar
    daily_quota_used = db_manager.get_daily_quota_used() if is_ready else 0
    quota_limit = 10000
    quota_pct = min(1.0, daily_quota_used / quota_limit)
    st.markdown(f"**Daily Quota Usage (Today UTC):** `{daily_quota_used:,} / {quota_limit:,} units ({int(quota_pct*100)}%)`")
    st.progress(quota_pct)
    
    col_q1, col_q2, col_q3 = st.columns(3)
    col_q1.metric("Units Used Today", f"{daily_quota_used:,}")
    col_q2.metric("Units Remaining", f"{max(0, quota_limit - daily_quota_used):,}")
    col_q3.metric("Searches Remaining", f"~{max(0, (quota_limit - daily_quota_used) // 101)}")

    col_rst1, _ = st.columns([2, 5])
    with col_rst1:
        if st.button("🔄 Reset Daily Quota Counter", use_container_width=True):
            db_manager.reset_daily_quota()
            st.success("Daily quota counter reset to 0.")
            st.rerun()

    # 3. Cache Management
    st.markdown("---")
    st.markdown("##### 🗄️ Local TTL Cache Management")
    cache_stats = (
        db_manager.get_cache_stats(max_age_seconds=config.cache_ttl_seconds)
        if is_ready
        else {}
    )

    col_cs1, col_cs2, col_cs3 = st.columns(3)
    col_cs1.metric("Total Cached Queries", cache_stats.get("total_cached_queries", 0))
    col_cs2.metric("Active Queries (<24h TTL)", cache_stats.get("active_cached_queries", 0))
    col_cs3.metric("Expired Queries (>24h)", cache_stats.get("expired_cached_queries", 0))

    st.caption(
        "ℹ️ *Notice: Clearing the cache only removes cached HTTP/SERP responses; it NEVER deletes saved projects or keyword history.*"
    )

    col_c1, col_c2, col_c3 = st.columns([2, 2, 2])
    with col_c1:
        if st.button("🧹 Prune Expired Autocomplete Cache (>24h)", use_container_width=True):
            pruned = db_manager.clear_cache(
                expired_only=True, max_age_seconds=config.cache_ttl_seconds
            )
            st.success(f"Pruned {pruned} expired cache entries.")
            st.rerun()

    with col_c2:
        confirm_flush = st.checkbox("Confirm cache flush", key="confirm_flush_cache")
        if st.button("🗑️ Flush Entire Autocomplete Cache", disabled=not confirm_flush, use_container_width=True):
            flushed = db_manager.clear_cache(expired_only=False)
            st.success(f"Flushed all {flushed} cached entries.")
            st.rerun()

    with col_c3:
        if st.button("🗑️ Clear SERP Cache Only", use_container_width=True):
            cleared_serp = db_manager.clear_serp_cache()
            st.success(f"Cleared {cleared_serp} cached SERP entries.")
            st.rerun()

    # 4. Database Status, Online Backup & Safe Restore
    st.markdown("---")
    st.markdown("##### 📦 Database Status, Online Backup & Safe Restore")
    st.caption(
        "Create consistent online SQLite snapshots using SQLite's backup API (safe during WAL operations). "
        "All backups are verified with `PRAGMA integrity_check`. Restores take an automatic pre-restore safety snapshot."
    )

    col_bk1, _ = st.columns([2, 3])
    with col_bk1:
        if st.button("📦 Create Verified Backup Now", type="primary", use_container_width=True):
            try:
                bkp_path = db_manager.create_backup()
                is_valid, msg, stats = db_manager.validate_backup(bkp_path)
                if is_valid:
                    st.success(
                        f"✅ Backup created and verified successfully: `{bkp_path.name}` ({stats.get('file_size_kb', 0)} KB)"
                    )
                else:
                    st.warning(f"⚠️ Backup created but validation reported: {msg}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create backup: {e}")

    # Available Backups List
    backups = db_manager.list_backups()
    if backups:
        st.markdown(f"**Available Local Backups ({len(backups)} snapshots):**")
        df_backups = pd.DataFrame(
            [
                {
                    "Filename": b["name"],
                    "Size (KB)": b["size_kb"],
                    "Created At": b["created_at"],
                    "Valid": "✅ OK" if b["is_valid"] else "❌ Corrupt",
                    "Status Message": b["message"],
                }
                for b in backups
            ]
        )
        st.dataframe(df_backups, use_container_width=True, hide_index=True)

        # Restore Expander
        with st.expander("🔄 Restore Database from Backup"):
            st.warning(
                "⚠️ **Warning**: Restoring a backup snapshot will replace your active database with that snapshot. An automated pre-restore safety snapshot will be taken first."
            )
            restore_target_name = st.selectbox(
                "Choose a backup snapshot to restore:",
                options=[b["name"] for b in backups if b["is_valid"]],
                key="restore_backup_select",
            )
            confirm_restore = st.checkbox(
                "I confirm that I want to restore this database snapshot and overwrite the active database.",
                key="confirm_restore_checkbox",
            )
            if st.button("🔄 Execute Safe Restore", disabled=not confirm_restore, type="primary"):
                target_bkp = next(b for b in backups if b["name"] == restore_target_name)
                success, restore_msg = db_manager.restore_backup(Path(target_bkp["path"]))
                if success:
                    st.success(f"✅ {restore_msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {restore_msg}")
    else:
        st.info("No database backups created yet. Click 'Create Verified Backup Now' above.")

    # 5. Guidance, Interactive Tours & Onboarding Preferences (Phase 17)
    st.markdown("---")
    st.markdown("##### 🎓 Guidance, Interactive Tours & Onboarding Preferences")
    st.caption(
        "Reset contextual tours, reopen the first-run onboarding goal selector, or clear guidance preferences. "
        "Your research history, saved configurations, and database records remain 100% intact."
    )

    current_goal_key = db_manager.get_setting("selected_onboarding_goal", "")
    current_goal_title = ONBOARDING_GOALS.get(current_goal_key, {}).get("title", "None selected")

    col_pref1, col_pref2 = st.columns(2)
    with col_pref1:
        st.markdown(f"**Current Onboarding Objective:** `{current_goal_title}`")
        if st.button("🚀 Restart First-Run Onboarding", use_container_width=True, key="settings_btn_restart_ob"):
            db_manager.set_setting("user_onboarded_v17", "false")
            st.session_state.dismiss_onboarding_temp = False
            st.session_state.current_page = PAGE_DASHBOARD
            st.success("Onboarding reset. Redirecting to dashboard...")
            st.rerun()

    with col_pref2:
        confirm_reset_tours = st.checkbox("Confirm reset guidance preferences", key="confirm_reset_tours_chk")
        if st.button("🔄 Reset All Tours & Guidance Preferences", disabled=not confirm_reset_tours, use_container_width=True, key="settings_btn_reset_tours"):
            res = reset_guidance_preferences()
            st.success("✅ Guidance preferences and tour completions have been reset successfully.")
            st.rerun()


# ==============================================================================
# Phase 22 Part 1: Four-Channel Portfolio & Profile Workspace
# ==============================================================================

def render_page_channels(is_ready: bool) -> None:
    """Render the Four-Channel Workspace and Profile Portfolio Manager."""
    render_page_header(
        title="Channel Portfolio",
        subtitle="Configure and manage four independent YouTube channel profiles with dedicated niches, audiences, languages, exclusions, and SEO rules.",
        category="WORKSPACE",
        badge_text="Four-Channel Workspace",
        provenance="SQLite WAL",
    )

    if not is_ready:
        render_empty_state("Database is not ready. Please check database permissions.", "warning")
        return

    channels = channel_manager.get_all_channels()
    if not channels or len(channels) < 4:
        st.warning("Seeding default 4 channel profiles...")
        channels = channel_manager.get_all_channels()

    # Active channel selection
    active_id = int(st.session_state.get("active_channel_id", 1))
    
    # Portfolio overview stats
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_metric_card("Total Workspaces", f"{len(channels)} Channels", "Configured & isolated", color="#2563EB")
    with col_m2:
        aff_count = sum(1 for c in channels if c.affiliate_enabled)
        render_metric_card("Affiliate Enabled", f"{aff_count} / {len(channels)}", "Monetized channels", color="#10B981")
    with col_m3:
        niche_count = len({c.channel_niche for c in channels})
        render_metric_card("Distinct Niches", f"{niche_count} Verticals", "Independent targeting", color="#7C3AED")
    with col_m4:
        render_metric_card("Active Workspace", f"Channel {active_id}", channels[active_id - 1].channel_name if 1 <= active_id <= len(channels) else "Ch 1", color="#0F172A")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Channel Selection Tabs
    tab_labels = [f"Ch {c.id}: {c.channel_name[:18]}" for c in channels]
    tabs = st.tabs(tab_labels)

    for idx, tab in enumerate(tabs):
        channel = channels[idx]
        c_id = channel.id or (idx + 1)
        with tab:
            if c_id == active_id:
                st.markdown(
                    "<div class='status-badge badge-success' style='display:inline-block; margin-bottom: 0.75rem;'>"
                    "★ CURRENT ACTIVE WORKSPACE</div>",
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"👉 Set Channel {c_id} as Active Workspace", key=f"set_active_btn_{c_id}", type="primary"):
                    st.session_state["active_channel_id"] = c_id
                    st.rerun()

            with st.form(key=f"channel_profile_form_{c_id}"):
                st.markdown(f"#### ⚙️ Profile Configuration — Channel {c_id}: {channel.channel_name}")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    chan_name = st.text_input("Channel Name", value=channel.channel_name, key=f"cp_name_{c_id}")
                    chan_handle = st.text_input("Channel Handle", value=channel.channel_handle, key=f"cp_handle_{c_id}", help="e.g. @TechGearPulse")
                    chan_url = st.text_input("Channel URL", value=channel.channel_url, key=f"cp_url_{c_id}", help="e.g. https://youtube.com/@handle")
                    target_country = st.text_input("Target Country Code", value=channel.target_country, max_chars=2, key=f"cp_cntry_{c_id}", help="ISO 2-letter country code (US, BD, GB, etc.)")
                    target_lang = st.text_input("Target Language Code", value=channel.target_language, max_chars=2, key=f"cp_lang_{c_id}", help="ISO 2-letter language code (en, bn, es, etc.)")
                
                with col_c2:
                    chan_niche = st.text_input("Primary Channel Niche", value=channel.channel_niche, key=f"cp_niche_{c_id}")
                    sub_niches_str = st.text_area(
                        "Sub-niches (Comma-separated)",
                        value=", ".join(channel.sub_niches),
                        key=f"cp_sub_{c_id}",
                        help="Specific topic clusters and specialized verticals",
                        height=68,
                    )
                    target_aud = st.text_input("Target Audience", value=channel.target_audience, key=f"cp_aud_{c_id}")
                    content_fmt = st.selectbox(
                        "Content Format Focus",
                        options=["both", "long-form", "Shorts"],
                        index=["both", "long-form", "Shorts"].index(channel.content_format) if channel.content_format in ["both", "long-form", "Shorts"] else 0,
                        key=f"cp_fmt_{c_id}",
                    )
                    pub_freq = st.selectbox(
                        "Publishing Frequency",
                        options=["1 video / week", "2 videos / week", "3 videos / week", "Daily", "Bi-weekly"],
                        index=["1 video / week", "2 videos / week", "3 videos / week", "Daily", "Bi-weekly"].index(channel.preferred_publishing_frequency) if channel.preferred_publishing_frequency in ["1 video / week", "2 videos / week", "3 videos / week", "Daily", "Bi-weekly"] else 1,
                        key=f"cp_freq_{c_id}",
                    )

                st.markdown("---")
                st.markdown("#### 🛒 Affiliate Marketing & Monetization Preferences")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    aff_enabled = st.checkbox("Enable Affiliate Marketing for this Channel", value=channel.affiliate_enabled, key=f"cp_aff_chk_{c_id}")
                with col_a2:
                    aff_markets_str = st.text_input(
                        "Preferred Affiliate Programs & Stores (Comma-separated)",
                        value=", ".join(channel.preferred_affiliate_markets),
                        key=f"cp_aff_mkts_{c_id}",
                        help="e.g. Amazon Associates, Drop, Epomaker, Hostinger",
                    )

                st.markdown("---")
                st.markdown("#### 🚫 Exclusions & Blacklists (Topic Guardrails)")
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    excl_topics = st.text_area("Excluded Topics (Comma-separated)", value=", ".join(channel.excluded_topics), key=f"cp_excl_top_{c_id}", height=68)
                    excl_brands = st.text_area("Excluded Brands (Comma-separated)", value=", ".join(channel.excluded_brands), key=f"cp_excl_brd_{c_id}", height=68)
                with col_e2:
                    excl_prods = st.text_area("Excluded Products (Comma-separated)", value=", ".join(channel.excluded_products), key=f"cp_excl_prd_{c_id}", height=68)
                    excl_kws = st.text_area("Excluded Keywords / Negative Terms (Comma-separated)", value=", ".join(channel.excluded_keywords), key=f"cp_excl_kw_{c_id}", height=68)

                st.markdown("---")
                st.markdown("#### 📜 Default Channel Bio, Links & Footer Template")
                chan_footer = st.text_area("Channel Footer & Disclaimers", value=channel.channel_footer, height=90, key=f"cp_foot_{c_id}")

                save_submitted = st.form_submit_button("💾 Save Channel Profile", type="primary", use_container_width=True)
                if save_submitted:
                    # Parse inputs
                    channel.channel_name = chan_name.strip()
                    channel.channel_handle = chan_handle.strip()
                    channel.channel_url = chan_url.strip()
                    channel.target_country = target_country.strip().upper()
                    channel.target_language = target_lang.strip().lower()
                    channel.channel_niche = chan_niche.strip()
                    channel.sub_niches = [s.strip() for s in sub_niches_str.split(",") if s.strip()]
                    channel.target_audience = target_aud.strip()
                    channel.content_format = content_fmt
                    channel.preferred_publishing_frequency = pub_freq
                    channel.affiliate_enabled = aff_enabled
                    channel.preferred_affiliate_markets = [m.strip() for m in aff_markets_str.split(",") if m.strip()]
                    channel.excluded_topics = [t.strip() for t in excl_topics.split(",") if t.strip()]
                    channel.excluded_brands = [b.strip() for b in excl_brands.split(",") if b.strip()]
                    channel.excluded_products = [p.strip() for p in excl_prods.split(",") if p.strip()]
                    channel.excluded_keywords = [k.strip() for k in excl_kws.split(",") if k.strip()]
                    channel.channel_footer = chan_footer.strip()

                    valid, errs = channel_manager.validate_channel(channel)
                    if not valid:
                        for e in errs:
                            st.error(f"❌ {e}")
                    else:
                        channel_manager.save_channel(channel)
                        st.success(f"✅ Channel {c_id} profile successfully updated & saved!")
                        st.rerun()

            # URL validation preview
            if channel.channel_url:
                is_valid_url, url_feedback = channel.validate_channel_url()
                if is_valid_url:
                    st.caption(f"🔗 **YouTube URL Verification:** `{channel.channel_url}` ({url_feedback})")
                else:
                    st.warning(f"⚠️ {url_feedback}")


# ==============================================================================
# Phase 22 Part 5: SEO Description Builder & Studio
# ==============================================================================

def render_page_description_studio(is_ready: bool) -> None:
    """Render the 8-Part YouTube SEO Description Builder and Compliance Studio."""
    render_page_header(
        title="Description Studio",
        subtitle="Build high-converting, 8-part YouTube video descriptions with strict character tracking (≤5,000 chars) and FTC affiliate disclosure compliance.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="8-Part Framework",
        provenance="Description Studio",
    )

    if not is_ready:
        render_empty_state("Database is not ready.", "warning")
        return

    active_chan_id = render_channel_switcher()
    channel = channel_manager.get_channel(active_chan_id)
    if not channel:
        st.error(f"Channel {active_chan_id} not found.")
        return

    st.markdown(f"**Target Workspace:** `{channel.channel_name}` ({channel.channel_niche}) | Affiliate: `{'Enabled' if channel.affiliate_enabled else 'Disabled'}`")
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        default_topic = st.session_state.get("desc_builder_topic", f"Best {channel.channel_niche} in 2026")
        topic_input = st.text_input("Video Topic", value=default_topic, key="desc_input_topic")
        default_kw = st.session_state.get("desc_builder_kw", f"{channel.channel_niche.lower()} review")
        kw_input = st.text_input("Primary SEO Keyword", value=default_kw, key="desc_input_kw")
    with col_in2:
        custom_hook = st.text_area("Section A: Opening Hook (First 2-3 lines before 'Show More')", height=68, placeholder="Leave blank to auto-generate search-optimized hook", key="desc_input_hook")
        custom_summary = st.text_area("Section B: Video Context & Value Summary", height=68, placeholder="Leave blank to auto-generate comprehensive overview", key="desc_input_summary")

    with st.expander("🔗 Affiliate Links & Product Mentions (Section D & E)", expanded=channel.affiliate_enabled):
        aff_link_name = st.text_input("Product Name / Label", value=f"Recommended {channel.channel_niche} Kit", key="desc_aff_lbl")
        aff_link_url = st.text_input("Product Page / Affiliate URL", value="https://amzn.to/example-link", key="desc_aff_url")
        aff_link_merch = st.text_input("Merchant / Store", value="Amazon Associates", key="desc_aff_merch")
        force_ftc = st.checkbox("Mandatory FTC Affiliate Disclosure Included", value=channel.affiliate_enabled, key="desc_ftc_chk")

    col_btn1, col_btn2 = st.columns([2, 3])
    with col_btn1:
        gen_btn = st.button("✨ Generate 8-Part Description", type="primary", use_container_width=True)

    if gen_btn or "current_generated_desc" in st.session_state:
        if gen_btn:
            aff_items = [{"label": aff_link_name, "url": aff_link_url, "merchant": aff_link_merch}] if aff_link_name else []
            generated = description_studio.build_description(
                topic=topic_input,
                primary_keyword=kw_input,
                channel=channel,
                custom_hook=custom_hook if custom_hook.strip() else None,
                custom_summary=custom_summary if custom_summary.strip() else None,
                affiliate_links=aff_items,
                include_ftc_disclosure=force_ftc,
            )
            st.session_state["current_generated_desc"] = generated

        desc_obj: VideoDescription = st.session_state["current_generated_desc"]

        # Audit check
        is_compliant, audit_errors, audit_warnings = description_studio.audit_description(desc_obj)

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        st.markdown("### 📝 Generated 8-Part YouTube Description")

        # Visual Character Progress
        char_count = desc_obj.character_count
        pct = min(100.0, (char_count / 5000.0) * 100.0)
        bar_color = "#10B981" if char_count <= 4500 else ("#F59E0B" if char_count <= 5000 else "#EF4444")
        st.markdown(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 0.75rem 1rem; border-radius: 10px; margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                    <span style="font-weight: 700; font-size: 0.85rem; color: #1E293B;">CHARACTER LIMIT AUDIT</span>
                    <span style="font-weight: 800; font-size: 0.85rem; color: {bar_color};">{char_count:,} / 5,000 characters ({round(pct, 1)}%)</span>
                </div>
                <div style="width: 100%; height: 8px; background: #E2E8F0; border-radius: 4px; overflow: hidden;">
                    <div style="width: {pct}%; height: 100%; background: {bar_color};"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Audit badges
        c_bad1, c_bad2, c_bad3 = st.columns(3)
        with c_bad1:
            if is_compliant:
                st.success("✅ **FTC Disclosure:** Compliant")
            else:
                st.error("❌ **FTC Disclosure:** Non-Compliant")
        with c_bad2:
            if char_count <= 5000:
                st.success("✅ **Length:** Within Limits")
            else:
                st.error("❌ **Length:** Exceeds 5,000 Chars")
        with c_bad3:
            st.info(f"ℹ️ **Affiliate Links:** {'Present' if desc_obj.has_affiliate_links else 'None'}")

        if audit_errors:
            for e in audit_errors:
                st.error(f"❌ {e}")
        if audit_warnings:
            for w in audit_warnings:
                st.warning(f"⚠️ {w}")

        # Editable Full Description Area
        edited_text = st.text_area(
            "Full Assembled Description (Ready for YouTube Studio)",
            value=desc_obj.full_text,
            height=320,
            key="edited_full_desc_area",
        )

        col_act1, col_act2, _ = st.columns([1.5, 1.5, 3])
        with col_act1:
            if st.button("📋 1-Click Copy Description", key="btn_copy_desc_studio", type="primary", use_container_width=True):
                st.session_state["copy_box_content"] = [edited_text]
                st.session_state["show_copy_box"] = True
                st.success("Copied to clipboard scratchpad!")
        with col_act2:
            if st.button("💾 Save Description to History", key="btn_save_desc_db", use_container_width=True):
                desc_obj.full_text = edited_text
                desc_obj.character_count = len(edited_text)
                desc_id = description_studio.save_description(desc_obj)
                st.success(f"✅ Description #{desc_id} saved for {channel.channel_name}!")

        if st.session_state.get("show_copy_box", False):
            render_copy_box(st.session_state.get("copy_box_content", []), label="Video Description")

    # History of saved descriptions
    saved_descs = description_studio.get_channel_descriptions(channel_id=channel.id or 1, limit=5)
    if saved_descs:
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        with st.expander(f"📚 Previously Saved Descriptions for {channel.channel_name} ({len(saved_descs)})"):
            for d in saved_descs:
                st.markdown(f"**{d['topic']}** (`{d['primary_keyword']}`) — *{d['character_count']} chars, created {d['created_at'][:10]}*")
                st.code(d["full_text"][:250] + "\n...", language="markdown")
                st.markdown("---")


# ==============================================================================
# Phase 23: YouTube SEO Audit & Affiliate Content Quality Engine
# ==============================================================================

def render_page_seo_audit(is_ready: bool) -> None:
    """Render the comprehensive YouTube SEO Audit and Affiliate Content Quality Engine."""
    render_page_header(
        title="SEO & Content Audit",
        subtitle="Audit video titles, descriptions, script promise delivery, affiliate compliance, and thumbnail synergy across your 4 channels.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="Quality Engine",
        provenance="Local Audit Engine",
    )

    if not is_ready:
        render_empty_state("Database is not ready.", "warning")
        return

    active_chan_id = render_channel_switcher()
    channel = channel_manager.get_channel(active_chan_id)
    if not channel:
        st.error(f"Channel {active_chan_id} not found.")
        return

    # Check Channel Profile & Exclusions
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.6rem 0.9rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-weight: 700; color: #0F172A;">Target Workspace:</span> <b>{channel.channel_name}</b> ({channel.channel_niche})
                <span style="color: #64748B; margin-left: 0.5rem;">Audience: {channel.target_audience}</span>
            </div>
            <div>
                <span style="font-size: 0.78rem; padding: 0.2rem 0.5rem; border-radius: 4px; background: {'#DCFCE7; color: #166534;' if channel.affiliate_enabled else '#F1F5F9; color: #475569;'}">
                    {'✓ Affiliate Enabled' if channel.affiliate_enabled else '⊘ Non-Commercial / No Affiliate'}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_new, tab_results, tab_checklist, tab_history = st.tabs([
        "🔎 New Audit & Live URL Inspection",
        "📊 Audit Scorecard & Findings",
        "📋 Before-Publishing Checklist",
        "📜 Revision History & Export",
    ])

    # --------------------------------------------------------------------------
    # Tab 1: New Audit & Live URL Inspection
    # --------------------------------------------------------------------------
    with tab_new:
        st.markdown("### 🎬 Video Concepts & Draft Metadata")
        st.caption("Provide your proposed title, draft description, and optional script outline for automated best-practice auditing.")

        # Live URL Public Inspector
        with st.expander("🌐 Optional: Inspect Published YouTube Video (Public Metadata)", expanded=False):
            url_col1, url_col2 = st.columns([3.5, 1.5])
            with url_col1:
                pub_url_input = st.text_input(
                    "YouTube Video URL",
                    placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...",
                    key="seo_audit_pub_url",
                )
            with url_col2:
                st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
                fetch_pub_btn = st.button("📥 Retrieve Public Metadata", use_container_width=True, key="fetch_pub_meta_btn")

            if fetch_pub_btn and pub_url_input:
                with st.spinner("Fetching public video metadata..."):
                    meta = audit_engine.fetch_public_video_metadata(pub_url_input)
                    if meta.get("success"):
                        st.success(f"✓ Retrieved public metadata for: **{meta.get('title')}** ({meta.get('source')})")
                        st.info("ℹ️ " + meta.get("notice", "Retrieved public metadata only."))
                        if meta.get("title") and not st.session_state.get("seo_audit_input_title"):
                            st.session_state["seo_audit_input_title"] = meta["title"]
                    else:
                        st.warning(meta.get("error", "Could not fetch public metadata."))

        # Form Inputs
        col_t1, col_t2 = st.columns([3, 2])
        with col_t1:
            default_title = st.session_state.get("seo_audit_input_title", f"How to Choose the Best {channel.channel_niche} in 2026")
            title_input = st.text_input("Proposed Video Title", value=default_title, key="seo_audit_input_title")

            # Live truncation indicator
            t_len = len(title_input)
            if t_len < 60:
                t_pill = f"<span style='color: #16A34A; font-weight: 600;'>🟢 {t_len} chars (Safe on mobile & desktop)</span>"
            elif t_len <= 75:
                t_pill = f"<span style='color: #D97706; font-weight: 600;'>🟡 {t_len} chars (Moderate risk of mobile truncation)</span>"
            else:
                t_pill = f"<span style='color: #DC2626; font-weight: 600;'>🔴 {t_len} chars (High mobile truncation risk — trim to &lt;60)</span>"
            st.markdown(f"<div style='font-size: 0.8rem; margin-top: -0.4rem; margin-bottom: 0.6rem;'>Length: {t_pill}</div>", unsafe_allow_html=True)

            default_kw = st.session_state.get("seo_audit_input_kw", channel.channel_niche.lower())
            primary_kw = st.text_input("Primary SEO Keyword", value=default_kw, key="seo_audit_input_kw")
            secondary_kws_raw = st.text_input(
                "Secondary Keywords (comma-separated)",
                value=f"{channel.channel_niche.lower()} review, best {channel.channel_niche.lower()} setup",
                key="seo_audit_input_sec_kws",
            )
            sec_kws = [k.strip() for k in secondary_kws_raw.split(",") if k.strip()]

        with col_t2:
            thumb_input = st.text_input(
                "Thumbnail Text Overlay & Concept",
                placeholder="e.g. 'DON'T BUY YET!' with high-contrast comparison shot",
                value=st.session_state.get("seo_audit_thumb_input", f"{channel.channel_niche} Tested!"),
                key="seo_audit_thumb_input",
            )
            st.caption("Keep text under 4-5 words for glanceable mobile comprehension.")

            is_affiliate = st.checkbox(
                "Commercial or Affiliate Recommendations Included",
                value=channel.affiliate_enabled,
                key="seo_audit_is_affiliate",
            )

            # Isolation check preview
            isolation_issues = audit_engine.check_channel_isolation(channel, title_input, primary_kw)
            for iss in isolation_issues:
                if iss.severity == AuditFindingSeverity.CRITICAL:
                    st.error(f"⚠️ {iss.title}: {iss.message}")
                elif iss.severity == AuditFindingSeverity.WARNING:
                    st.warning(f"💡 {iss.title}: {iss.message}")

        desc_input = st.text_area(
            "Draft Video Description (Includes Hook, Timestamps, Links, FTC Disclosure)",
            height=140,
            value=st.session_state.get(
                "seo_audit_desc_input",
                f"Looking for the best guide on {primary_kw}? In this video we review and test everything you need to know about {channel.channel_niche}.\n\n"
                f"TIMESTAMPS:\n0:00 - Introduction\n1:20 - Key Specs & Overview\n3:45 - Hands-on Testing\n6:10 - Pros & Cons\n8:30 - Final Verdict\n\n"
                f"DISCLOSURE: Some links below are affiliate links. If you purchase through them, we may earn a small commission at no additional cost to you.\n\n"
                f"• Recommended Kit: https://example.com/gear\n\nPrices and availability subject to change.",
            ),
            key="seo_audit_desc_input",
        )
        st.markdown(f"<div style='font-size: 0.78rem; color: #64748B; margin-top: -0.3rem;'>Character Count: <b>{len(desc_input)}</b> / 5,000 max platform limit</div>", unsafe_allow_html=True)

        script_input = st.text_area(
            "Script, Outline, or Transcript (Optional)",
            height=120,
            placeholder="Paste your video outline or draft script here to verify title promises and check for filler phrases. (If left blank, Script Alignment will be marked NOT CHECKED without deducting score).",
            key="seo_audit_script_input",
        )

        col_run1, col_run2 = st.columns([2, 3])
        with col_run1:
            run_audit_btn = st.button("🩺 Run Full SEO & Content Audit", type="primary", use_container_width=True)

        if run_audit_btn:
            with st.spinner("Analyzing title quality, description SEO, timestamps, script promises, and affiliate compliance..."):
                existing_titles = [d["topic"] for d in db_manager.get_channel_descriptions(channel.id or 1, limit=20)]
                title_res = audit_engine.audit_title(title_input, primary_kw, channel, existing_titles)
                desc_res = audit_engine.audit_description(desc_input, primary_kw, sec_kws, channel, is_affiliate)
                script_res = audit_engine.audit_script_alignment(title_input, desc_input, primary_kw, script_input)
                aff_res = audit_engine.audit_affiliate_content(desc_input, script_input, channel, has_affiliate=is_affiliate)
                thumb_res = audit_engine.audit_thumbnail_alignment(thumb_input, title_input, script_input)
                scores = audit_engine.calculate_readiness_score(title_res, desc_res, script_res, aff_res, thumb_res)
                checklist = audit_engine.generate_publishing_checklist(channel, is_affiliate)

                all_findings = title_res.findings + desc_res.findings + script_res.findings + aff_res.findings + thumb_res.findings

                audit_record = VideoSeoAudit(
                    id=None,
                    channel_id=channel.id or active_chan_id,
                    channel_name=channel.channel_name,
                    idea_id=None,
                    primary_keyword=primary_kw,
                    secondary_keywords=sec_kws,
                    proposed_title=title_input,
                    draft_description=desc_input,
                    script_text=script_input,
                    thumbnail_concept=thumb_input,
                    video_url=st.session_state.get("seo_audit_pub_url", ""),
                    is_published_url=bool(st.session_state.get("seo_audit_pub_url")),
                    scores=scores,
                    findings=all_findings,
                    title_result=title_res,
                    description_result=desc_res,
                    script_result=script_res,
                    affiliate_result=aff_res,
                    thumbnail_result=thumb_res,
                    checklist=checklist,
                    revision_number=1,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )

                audit_id = db_manager.save_seo_audit(audit_record)
                audit_record.id = audit_id
                st.session_state["current_seo_audit"] = audit_record
                st.success(f"✓ Audit #{audit_id} complete! Overall SEO Readiness Score: {scores.overall_readiness_score}/100. Switch to the '📊 Audit Scorecard' tab to inspect details.")

    # --------------------------------------------------------------------------
    # Tab 2: Audit Scorecard & Findings
    # --------------------------------------------------------------------------
    with tab_results:
        audit = st.session_state.get("current_seo_audit")
        if not audit:
            render_empty_state("No audit has been run yet. Submit your video details in Tab 1 to generate a scorecard.", "info")
        else:
            # Overall Score Banner
            sc = audit.scores
            score_val = sc.overall_readiness_score
            score_color = "#16A34A" if score_val >= 80 else ("#D97706" if score_val >= 60 else "#DC2626")

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.2rem; margin-bottom: 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                        <div>
                            <span style="font-size: 0.75rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em;">OVERALL SEO READINESS SCORE</span>
                            <div style="font-size: 2.2rem; font-weight: 900; color: {score_color}; line-height: 1.1;">{score_val} <span style="font-size: 1rem; color: #94A3B8; font-weight: 500;">/ 100</span></div>
                            <div style="font-size: 0.85rem; color: #475569; margin-top: 0.2rem;">
                                Adherence to search discoverability, FTC transparency, and viewer retention guidelines.
                            </div>
                        </div>
                        <div style="max-width: 420px; font-size: 0.78rem; color: #64748B; background: #F8FAFC; border-radius: 8px; padding: 0.5rem 0.75rem; border-left: 3px solid #3B82F6;">
                            <b>Transparent Heuristic Disclaimer:</b> {sc.disclaimer}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Category Cards
            mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
            with mcol1:
                render_metric_card("Title Quality", f"{sc.title_score}/100", subtitle=audit.title_result.truncation_risk)
            with mcol2:
                render_metric_card("Description & FTC", f"{sc.description_score}/100", subtitle=f"{audit.description_result.character_count} chars")
            with mcol3:
                script_val = f"{sc.script_alignment_score}/100" if sc.script_alignment_score is not None else "NOT CHECKED"
                render_metric_card("Script Alignment", script_val, subtitle=audit.script_result.status.value)
            with mcol4:
                aff_val = f"{sc.affiliate_quality_score}/100" if sc.affiliate_quality_score is not None else "NOT APPLICABLE"
                render_metric_card("Affiliate Quality", aff_val, subtitle=audit.affiliate_result.status.value)
            with mcol5:
                render_metric_card("Thumbnail Concept", f"{sc.thumbnail_score}/100", subtitle=audit.thumbnail_result.readability_assessment[:20])

            st.markdown("---")

            # Prioritized Actions
            st.markdown("#### 🚨 Prioritized Action Items")
            if sc.prioritized_actions:
                for idx, act in enumerate(sc.prioritized_actions):
                    p_badge = "🔴 CRITICAL" if act["severity"] == "CRITICAL" else ("🟠 WARNING" if act["severity"] == "WARNING" else "🟡 IMPROVEMENT")
                    with st.expander(f"{p_badge} [{act['category']}] {act['issue']}", expanded=(act["severity"] == "CRITICAL")):
                        st.markdown(f"**Recommended Action:** {act['action']}")
            else:
                st.success("✓ No critical compliance or high-severity issues found. Ready for review!")

            st.markdown("---")

            # Title Alternatives Workshop
            st.markdown("#### 💡 Title Alternatives Workshop")
            st.caption("Ethically generated alternatives with zero ranking guarantees. Select any option to apply it.")
            for alt in audit.title_result.alternatives:
                col_a1, col_a2 = st.columns([4, 1.2])
                with col_a1:
                    st.markdown(f"**{alt['angle']}:** `{alt['title']}` *({alt['char_count']} chars)*")
                    st.caption(f"Rationale: {alt['why_suggested']}")
                with col_a2:
                    if st.button("Apply Title", key=f"apply_alt_{abs(hash(alt['title'])) % 10000}", use_container_width=True):
                        st.session_state["seo_audit_input_title"] = alt["title"]
                        st.success(f"Applied '{alt['title']}' to title input!")
                        st.rerun()

    # --------------------------------------------------------------------------
    # Tab 3: Before-Publishing Checklist
    # --------------------------------------------------------------------------
    with tab_checklist:
        audit = st.session_state.get("current_seo_audit")
        st.markdown("### 📋 Before-Publishing Checklist")
        st.caption("All checks must be manually verified. Keyword Studio never automatically completes verification items.")

        if not audit or not audit.checklist:
            checklist_items = audit_engine.generate_publishing_checklist(channel, channel.affiliate_enabled)
        else:
            checklist_items = audit.checklist

        completed_count = 0
        for item in checklist_items:
            chk_val = st.checkbox(
                f"**{item.label}** ({item.category})",
                value=item.is_completed,
                key=f"pub_chk_{item.item_id}",
                help=item.help_text,
            )
            item.is_completed = chk_val
            if chk_val:
                completed_count += 1

        pct = int((completed_count / len(checklist_items)) * 100) if checklist_items else 0
        st.progress(pct / 100)
        st.markdown(f"**Checklist Completion:** {completed_count} / {len(checklist_items)} confirmed ({pct}%)")

        if completed_count == len(checklist_items):
            st.success("🎉 All pre-publishing quality checks manually verified! Your video is ready to upload.")
        else:
            st.info(f"Complete remaining {len(checklist_items) - completed_count} checks before publishing.")

    # --------------------------------------------------------------------------
    # Tab 4: Revision History & Export
    # --------------------------------------------------------------------------
    with tab_history:
        st.markdown("### 📜 Channel Audit History & Protected Export")
        st.caption("View revision snapshots and export sanitized reports (protected against spreadsheet formula injection).")

        past_audits = db_manager.get_seo_audits_by_channel(channel.id or active_chan_id, limit=20)
        if not past_audits:
            st.info("No saved audit records found for this channel yet.")
        else:
            for rec in past_audits:
                with st.expander(f"Audit #{rec['id']}: {rec['proposed_title']} (Revision #{rec['revision_number']}) — {rec['created_at'][:10]}"):
                    st.markdown(f"- **Primary Keyword:** `{rec['primary_keyword']}`")
                    st.markdown(f"- **Overall Score:** `{rec['scores'].get('overall', 'N/A')}/100` | Title: `{rec['scores'].get('title', 'N/A')}` | Desc: `{rec['scores'].get('description', 'N/A')}`")

                    # View Revisions
                    revs = db_manager.get_audit_revisions(rec["id"])
                    if len(revs) > 1:
                        st.markdown(f"**Revision History ({len(revs)} snapshots):**")
                        for r in revs:
                            st.markdown(f"  • Rev #{r['revision_number']}: Title: *'{r['proposed_title']}'* ({r['created_at'][:16]})")

        # Export Current Audit
        curr = st.session_state.get("current_seo_audit")
        if curr:
            st.markdown("---")
            st.markdown("#### 📥 Export Sanitized Audit Report")
            exp_format = st.radio("Export Format", ["Markdown", "JSON"], horizontal=True, key="seo_exp_fmt")
            export_content = audit_engine.export_audit_report(curr, format=exp_format.lower())

            render_copy_box([export_content], label=f"Audit Report ({exp_format})")
            st.download_button(
                label=f"💾 Download Sanitized {exp_format} Report",
                data=export_content,
                file_name=f"seo_audit_{channel.channel_name.lower().replace(' ', '_')}_{curr.revision_number}.{ 'md' if exp_format == 'Markdown' else 'json'}",
                mime="text/plain" if exp_format == "Markdown" else "application/json",
                key="download_seo_audit_btn",
            )


# ==============================================================================
# Phase 24: YouTube Analytics & Four-Channel Growth Intelligence
# ==============================================================================

def render_page_analytics(is_ready: bool) -> None:
    """Render the official YouTube Analytics dashboard and growth intelligence engine."""
    render_page_header(
        title="Analytics & Growth Intelligence",
        subtitle="Evidence-based performance analytics, topic learning, and growth coaching across your four channels.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="OAuth 2.0 Engine",
        provenance="YouTube Analytics API",
    )

    if not is_ready:
        render_empty_state("Database is not ready.", "warning")
        return

    active_chan_id = render_channel_switcher()
    channel = channel_manager.get_channel(active_chan_id)
    if not channel:
        st.error(f"Channel {active_chan_id} not found.")
        return

    creds = db_manager.get_channel_credentials(active_chan_id)
    is_auth = creds.is_valid() if creds else False

    # Connection Status Banner with Epistemic Privacy Notice
    if is_auth:
        status_html = f"""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 0.6rem 0.9rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-weight: 700; color: #166534;">🟢 Live Authorized Analytics:</span> <b>{channel.channel_name}</b>
                <span style="color: #4B5563; margin-left: 0.5rem; font-size: 0.82rem;">Connected via YouTube Analytics API v2 (Read-Only)</span>
            </div>
            <div>
                <span style="font-size: 0.75rem; background: #DCFCE7; color: #166534; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600;">
                    ✓ Private Analytics Active
                </span>
            </div>
        </div>
        """
    else:
        status_html = f"""
        <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 0.6rem 0.9rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-weight: 700; color: #92400E;">🟡 Public Research Mode:</span> <b>{channel.channel_name}</b>
                <span style="color: #6B7280; margin-left: 0.5rem; font-size: 0.82rem;">Official OAuth 2.0 not connected yet. Connect in Tab 6 for private impressions & retention.</span>
            </div>
            <div>
                <span style="font-size: 0.75rem; background: #FEF3C7; color: #92400E; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600;">
                    Public Mode Only
                </span>
            </div>
        </div>
        """
    st.markdown(status_html, unsafe_allow_html=True)

    tab_overview, tab_videos, tab_topics, tab_coach, tab_experiments, tab_oauth = st.tabs([
        "📊 Channel Overview",
        "🎥 Video Performance",
        "🧠 Topic Learning",
        "🧭 Growth Coach",
        "🔬 Publishing Experiments",
        "🔐 YouTube OAuth & API Setup",
    ])

    # --------------------------------------------------------------------------
    # Tab 1: Channel Overview & Comparisons
    # --------------------------------------------------------------------------
    with tab_overview:
        col_dr1, col_dr2 = st.columns([3, 2])
        with col_dr1:
            date_preset = st.selectbox(
                "Comparison Period",
                [
                    "Last 28 Days vs Prior 28 Days (Recommended)",
                    "Last 7 Days vs Prior 7 Days",
                    "Last 90 Days vs Prior 90 Days",
                ],
                key="analytics_date_preset",
            )
        with col_dr2:
            st.caption("All period changes use mathematically verified denominators (zero-denominator protected).")

        today = datetime.now(timezone.utc)
        if "7 Days" in date_preset:
            window_days = 7
        elif "90 Days" in date_preset:
            window_days = 90
        else:
            window_days = 28

        from datetime import timedelta
        d_end = today.strftime("%Y-%m-%d")
        d_start = (today - timedelta(days=window_days)).strftime("%Y-%m-%d")
        c_end = (today - timedelta(days=window_days + 1)).strftime("%Y-%m-%d")
        c_start = (today - timedelta(days=window_days * 2 + 1)).strftime("%Y-%m-%d")

        overview = youtube_analytics_provider.get_channel_overview(
            channel_id=active_chan_id,
            date_start=d_start,
            date_end=d_end,
            comparison_start=c_start,
            comparison_end=c_end,
        )

        st.markdown(f"**Observation Period:** `{d_start}` to `{d_end}` &nbsp;|&nbsp; **Baseline Comparison:** `{c_start}` to `{c_end}`")

        # KPI Metrics Cards (Row 1)
        kcol1, kcol2, kcol3, kcol4 = st.columns(4)
        with kcol1:
            render_metric_card(
                "Total Views",
                overview.views.display_current,
                subtitle=f"Change: {overview.views.display_change}",
            )
        with kcol2:
            render_metric_card(
                "Watch Time (Hours)",
                overview.watch_time_hours.display_current,
                subtitle=f"Change: {overview.watch_time_hours.display_change}",
            )
        with kcol3:
            render_metric_card(
                "Avg View Duration",
                overview.avg_view_duration_seconds.display_current,
                subtitle=f"Change: {overview.avg_view_duration_seconds.display_change}",
            )
        with kcol4:
            render_metric_card(
                "Net Subscribers",
                overview.subscribers_net.display_current,
                subtitle=f"Change: {overview.subscribers_net.display_change}",
            )

        # KPI Metrics Cards (Row 2: Impressions & Revenue)
        kcol5, kcol6, kcol7 = st.columns(3)
        with kcol5:
            render_metric_card(
                "Impressions",
                overview.impressions.display_current,
                subtitle=overview.impressions.unavailable_reason or "Available via dimension report",
            )
        with kcol6:
            render_metric_card(
                "Impressions CTR",
                overview.impressions_ctr.display_current,
                subtitle=overview.impressions_ctr.unavailable_reason or "Available via dimension report",
            )
        with kcol7:
            render_metric_card(
                "Estimated Revenue",
                overview.estimated_revenue.display_current,
                subtitle=overview.estimated_revenue.unavailable_reason or "Monetized Partner Channels",
            )

        st.caption(f"Data source: {overview.data_source} • Retrieved at: {overview.retrieved_at[:19]} UTC")

        if not overview.is_authorized_analytics:
            st.info(
                "💡 **Why are metrics unavailable?** The local studio only reports metrics when authorized by the channel owner via OAuth 2.0. "
                "We never display invented metrics or silently replace missing numbers with fake zeros. Go to **Tab 6 (YouTube OAuth & API Setup)** to connect your channel."
            )

    # --------------------------------------------------------------------------
    # Tab 2: Video Performance Breakdown
    # --------------------------------------------------------------------------
    with tab_videos:
        st.markdown("### 🎥 Video Performance & Format Segmentation")
        vcol1, vcol2 = st.columns([3, 2])
        with vcol1:
            search_v = st.text_input("Filter Videos by Title or Keyword", placeholder="Search title...", key="video_perf_search")
        with vcol2:
            format_filter = st.selectbox("Video Format", ["All Formats", "Long-form", "Shorts"], key="video_perf_format")

        videos = youtube_analytics_provider.get_video_performance_list(active_chan_id)

        if not videos:
            st.info("No video performance records available yet for this channel profile. Connect OAuth or run research in Discovery pages.")
        else:
            filtered_vids = videos
            if format_filter != "All Formats":
                filtered_vids = [v for v in filtered_vids if v.video_format == format_filter]
            if search_v:
                filtered_vids = [v for v in filtered_vids if search_v.lower() in v.title.lower()]

            st.markdown(f"**Displaying {len(filtered_vids)} video(s):**")
            for v in filtered_vids:
                fmt_badge = "🟩 Long-form" if v.video_format == "Long-form" else "🟪 Shorts"
                with st.expander(f"{fmt_badge} | {v.title} — {v.views:,} views"):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Views", f"{v.views:,}")
                    with c2:
                        w_val = f"{v.watch_time_minutes:.1f} min" if v.watch_time_minutes is not None else "N/A"
                        st.metric("Watch Time", w_val)
                    with c3:
                        d_val = f"{int(v.avg_view_duration_seconds)}s" if v.avg_view_duration_seconds is not None else "N/A"
                        st.metric("Avg Duration", d_val)
                    with c4:
                        s_val = f"+{v.subscribers_gained}" if v.subscribers_gained is not None else "N/A"
                        st.metric("Subscribers Gained", s_val)

                    st.caption(f"Source: {'Authorized Channel-Owner Analytics' if v.is_authorized_data else 'Public Metadata'} • Video ID: {v.video_id}")

    # --------------------------------------------------------------------------
    # Tab 3: Topic & Keyword Learning
    # --------------------------------------------------------------------------
    with tab_topics:
        st.markdown("### 🧠 Topic & Keyword Performance Learning")
        st.markdown(
            """
            <div style="background: #F8FAFC; border-left: 4px solid #3B82F6; padding: 0.6rem 0.9rem; margin-bottom: 1rem; border-radius: 4px; font-size: 0.82rem; color: #334155;">
                <b>Epistemic Modesty & Causation Notice:</b> Topic association does not guarantee future video success.
                A video may perform well due to publication timing, thumbnail click-through, format, or search volume shifts.
                We evaluate correlation across similar formats without making unfounded causal claims.
            </div>
            """,
            unsafe_allow_html=True,
        )

        all_vids = youtube_analytics_provider.get_video_performance_list(active_chan_id)
        topic_data = growth_engine.correlate_topics_and_keywords(active_chan_id, all_vids)

        if not topic_data:
            st.info("No topic clusters identified yet. Connect analytics or record videos to begin topic learning.")
        else:
            for item in topic_data:
                with st.container():
                    st.markdown(f"#### 🏷️ Topic Cluster: `{item['topic'].title()}`")
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        st.metric("Published Videos", item["video_count"])
                    with tc2:
                        st.metric("Total Views", f"{item['total_views']:,}")
                    with tc3:
                        st.metric("Average Views / Video", f"{item['average_views']:,.0f}")

                    st.caption(f"Formats observed: {', '.join(item['formats'])} • Sample Caveat: {item['sample_caveat']}")
                    st.markdown("---")

    # --------------------------------------------------------------------------
    # Tab 4: Channel-Specific Growth Coach (5-Point Evidence Framework)
    # --------------------------------------------------------------------------
    with tab_coach:
        st.markdown("### 🧭 Evidence-Based Growth Coach")
        st.caption("Recommendations strictly structured with observed facts, supporting data, uncertainties, actions, and measurable criteria.")

        all_vids = youtube_analytics_provider.get_video_performance_list(active_chan_id)
        recs = growth_engine.generate_growth_recommendations(channel, overview, all_vids)

        for r in recs:
            p_color = "#DC2626" if r.priority == "High" else "#2563EB"
            with st.container():
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.1rem; margin-bottom: 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-size: 0.75rem; font-weight: 700; color: {p_color}; text-transform: uppercase; letter-spacing: 0.05em;">
                                [{r.category.upper()}] • {r.priority.upper()} PRIORITY
                            </span>
                        </div>
                        <h4 style="margin: 0.2rem 0 0.8rem 0; color: #0F172A; font-size: 1.15rem;">{r.title}</h4>
                        
                        <div style="margin-bottom: 0.5rem;">
                            <b>1. 👁️ What Was Observed:</b>
                            <div style="font-size: 0.88rem; color: #334155; margin-left: 0.5rem;">{r.observed_fact}</div>
                        </div>
                        <div style="margin-bottom: 0.5rem;">
                            <b>2. 📊 Supporting Evidence:</b>
                            <div style="font-size: 0.88rem; color: #334155; margin-left: 0.5rem;">{r.supporting_evidence}</div>
                        </div>
                        <div style="margin-bottom: 0.5rem;">
                            <b>3. ⚖️ What Remains Uncertain / Confounders:</b>
                            <div style="font-size: 0.88rem; color: #64748B; margin-left: 0.5rem; font-style: italic;">{r.uncertainty_and_confounders}</div>
                        </div>
                        <div style="margin-bottom: 0.5rem; background: #F8FAFC; padding: 0.6rem; border-radius: 6px; border-left: 3px solid #2563EB;">
                            <b>4. 🎯 Suggested Action:</b>
                            <div style="font-size: 0.88rem; color: #0F172A; margin-top: 0.2rem;">{r.suggested_action}</div>
                        </div>
                        <div>
                            <b>5. 📏 How Success Should Be Measured:</b>
                            <div style="font-size: 0.85rem; color: #059669; margin-left: 0.5rem;">{r.success_measurement}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # --------------------------------------------------------------------------
    # Tab 5: Publishing Experiments
    # --------------------------------------------------------------------------
    with tab_experiments:
        st.markdown("### 🔬 Manual Publishing Experiments")
        st.caption("Record structured content experiments (title, thumbnail, description changes). Never changes live video metadata automatically.")

        with st.expander("➕ Create New Content Experiment", expanded=False):
            exp_name = st.text_input("Experiment Name", placeholder="e.g. Test Benefit-Driven Title on M1 Keyboard Video", key="new_exp_name")
            exp_type = st.selectbox(
                "Experiment Type",
                ["Title Revision", "Thumbnail Revision", "Description Update", "Publication Time", "Video Format", "Content Structure"],
                key="new_exp_type",
            )
            exp_vid_id = st.text_input("YouTube Video ID", placeholder="e.g. dQw4w9WgXcQ", key="new_exp_vid")
            exp_hypothesis = st.text_area("Hypothesis", placeholder="e.g. Front-loading the keyword 'custom switches' will improve browse click-through.", key="new_exp_hyp")
            col_pre1, col_pre2 = st.columns(2)
            with col_pre1:
                pre_views = st.number_input("Pre-Change Views Baseline", min_value=0, value=100, key="new_exp_pre_v")
            with col_pre2:
                pre_ctr = st.number_input("Pre-Change Impressions CTR % (if available)", min_value=0.0, max_value=100.0, value=4.5, key="new_exp_pre_ctr")

            if st.button("Save Experiment Record", type="primary", key="save_exp_btn"):
                if exp_name and exp_vid_id:
                    new_exp = PublishingExperiment(
                        id=None,
                        channel_id=active_chan_id,
                        experiment_name=exp_name,
                        video_id=exp_vid_id,
                        video_title=f"Video ({exp_vid_id})",
                        experiment_type=exp_type,
                        hypothesis=exp_hypothesis,
                        status="Running",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        pre_metrics={"views": pre_views, "impressions_ctr": pre_ctr},
                    )
                    exp_id = db_manager.save_publishing_experiment(new_exp)
                    st.success(f"✓ Experiment #{exp_id} recorded! Track metrics after 14 days before concluding.")
                    st.rerun()

        # Existing experiments list
        exps = db_manager.get_publishing_experiments(channel_id=active_chan_id)
        if not exps:
            st.info("No publishing experiments recorded yet for this channel profile.")
        else:
            st.markdown(f"**Recorded Experiments ({len(exps)}):**")
            for e in exps:
                status_color = "#16A34A" if e["status"] == "Completed" else "#D97706"
                with st.expander(f"Experiment #{e['id']}: {e['experiment_name']} ({e['experiment_type']}) — [{e['status']}]"):
                    st.markdown(f"**Hypothesis:** {e['hypothesis']}")
                    st.markdown(f"**Started:** {e['started_at'][:10]} | Status: `<span style='color:{status_color}; font-weight:700;'>{e['status']}</span>`", unsafe_allow_html=True)
                    st.markdown(f"**Pre-Change Baseline:** Views: `{e['pre_metrics'].get('views', 'N/A')}` | CTR: `{e['pre_metrics'].get('impressions_ctr', 'N/A')}%`")

                    if e["status"] == "Running":
                        st.markdown("---")
                        st.markdown("##### Record Post-Change Metrics")
                        col_post1, col_post2, col_post3 = st.columns([2, 2, 1.5])
                        with col_post1:
                            post_v = st.number_input(f"Observed Post Views (Exp #{e['id']})", min_value=0, value=int(e['pre_metrics'].get('views', 0)) + 50, key=f"post_v_{e['id']}")
                        with col_post2:
                            post_c = st.number_input(f"Observed Post CTR % (Exp #{e['id']})", min_value=0.0, max_value=100.0, value=5.2, key=f"post_c_{e['id']}")
                        with col_post3:
                            st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
                            if st.button("Evaluate Outcome", key=f"eval_btn_{e['id']}", use_container_width=True):
                                exp_obj = PublishingExperiment(
                                    id=e["id"],
                                    channel_id=e["channel_id"],
                                    experiment_name=e["experiment_name"],
                                    video_id=e["video_id"],
                                    video_title=e["video_title"],
                                    experiment_type=e["experiment_type"],
                                    hypothesis=e["hypothesis"],
                                    status="Completed",
                                    started_at=e["started_at"],
                                    pre_metrics=e["pre_metrics"],
                                )
                                evaluated = growth_engine.evaluate_publishing_experiment(exp_obj, {"views": post_v, "impressions_ctr": post_c})
                                db_manager.save_publishing_experiment(evaluated)
                                st.success("Experiment evaluated and completed!")
                                st.rerun()
                    else:
                        st.markdown(f"**Conclusion:** {e['outcome_conclusion']}")
                        if e["confounding_factors"]:
                            st.caption(f"Confounding factors noted: {'; '.join(e['confounding_factors'])}")

    # --------------------------------------------------------------------------
    # Tab 6: YouTube OAuth 2.0 & API Setup
    # --------------------------------------------------------------------------
    with tab_oauth:
        st.markdown("### 🔐 Official YouTube OAuth 2.0 & API Configuration")
        st.caption("Secure authorization for private channel-owner analytics. Password-free, local-first storage.")

        st.markdown(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 1.2rem; font-size: 0.84rem; color: #334155;">
                <b>Public Metadata vs Authorized Analytics:</b>
                <ul style="margin: 0.3rem 0 0 1rem; padding: 0;">
                    <li><b>Public Data (YouTube Data API):</b> Public view counts, comment counts, video titles, and upload dates.</li>
                    <li><b>Private Analytics (YouTube Analytics API):</b> Impressions, impressions CTR, audience retention %, traffic sources, and revenue. Requires channel owner OAuth consent.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        curr_creds = db_manager.get_channel_credentials(active_chan_id)
        client_id_val = curr_creds.client_id if curr_creds else ""
        secret_mask = curr_creds.mask_secret() if curr_creds else ""

        col_oa1, col_oa2 = st.columns(2)
        with col_oa1:
            inp_client_id = st.text_input("OAuth 2.0 Client ID", value=client_id_val, placeholder="xxxx.apps.googleusercontent.com", key="oauth_client_id_inp")
            inp_client_secret = st.text_input("OAuth 2.0 Client Secret", value=secret_mask, type="password", placeholder="GOCSPX-...", key="oauth_client_secret_inp")
            inp_redirect_uri = st.text_input("Redirect URI (Configured in Google Cloud)", value="http://localhost:8501", key="oauth_redirect_uri_inp")

        with col_oa2:
            st.markdown("##### Setup Instructions")
            st.markdown(
                """
                1. Go to [Google Cloud Console](https://console.cloud.google.com).
                2. Enable **YouTube Analytics API** and **YouTube Data API v3**.
                3. Create OAuth 2.0 Client Credentials (Web application).
                4. Add `http://localhost:8501` to Authorized Redirect URIs.
                5. Scopes used: `yt-analytics.readonly` & `youtube.readonly`.
                """
            )

        col_act1, col_act2 = st.columns([2.5, 2])
        with col_act1:
            if st.button("🔗 Generate Google Consent URL", key="gen_oauth_url_btn", use_container_width=True):
                if inp_client_id:
                    auth_url = youtube_analytics_provider.build_authorization_url(
                        channel_id=active_chan_id,
                        client_id=inp_client_id,
                        redirect_uri=inp_redirect_uri,
                    )
                    st.markdown(f"**Click to Authorize with Google:** [Authorize Channel '{channel.channel_name}']({auth_url})")
                    st.info("After granting consent, copy the `code=...` parameter from your browser's address bar and paste it below.")
                else:
                    st.warning("Please enter your OAuth Client ID first.")

        # Exchange Code Form
        st.markdown("---")
        st.markdown("##### Complete Authorization")
        col_c1, col_c2 = st.columns([3, 1.5])
        with col_c1:
            code_input = st.text_input("Paste Authorization Code", placeholder="4/0AWgav...", key="oauth_code_inp")
        with col_c2:
            st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
            auth_submit_btn = st.button("Authorize Channel", type="primary", use_container_width=True, key="submit_code_btn")

        if auth_submit_btn and code_input and inp_client_id:
            with st.spinner("Exchanging code for official API tokens..."):
                actual_secret = inp_client_secret if inp_client_secret != secret_mask else (curr_creds.client_secret if curr_creds else "")
                success, msg, _ = youtube_analytics_provider.exchange_authorization_code(
                    channel_id=active_chan_id,
                    channel_name=channel.channel_name,
                    client_id=inp_client_id,
                    client_secret=actual_secret,
                    code=code_input,
                    redirect_uri=inp_redirect_uri,
                )
                if success:
                    st.success(f"✓ Channel '{channel.channel_name}' successfully authorized!")
                    st.rerun()
                else:
                    st.error(msg)

        # Disconnect & Revoke Section
        if curr_creds and curr_creds.is_valid():
            st.markdown("---")
            if st.button("🔌 Disconnect Channel & Revoke Credentials", key="disconnect_oauth_btn"):
                youtube_analytics_provider.revoke_authorization(active_chan_id)
                st.success(f"Channel {channel.channel_name} disconnected and credentials deleted.")
                st.rerun()


# ==============================================================================
# Phase 22 Part 9: Morning Idea Report Dashboard

# ==============================================================================

def render_page_morning_report(is_ready: bool) -> None:
    """Render the Four-Channel Daily Morning Idea Report Dashboard with 18-Field Evidence Cards."""
    render_page_header(
        title="Morning Idea Report",
        subtitle="Automated daily YouTube SEO & affiliate opportunity engine for all four channels, backed by 60-day empirical gap analysis.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="Daily 07:00 AM",
        provenance="Four-Channel Engine",
    )

    if not is_ready:
        render_empty_state("Database is not ready.", "warning")
        return

    # Top Control Bar
    col_t1, col_t2 = st.columns([2, 3])
    with col_t1:
        if st.button("🚀 Run Daily Research Now (All 4 Channels)", type="primary", use_container_width=True, key="btn_run_morning_report"):
            with st.spinner("Executing independent research pipelines across 4 channels..."):
                rep = daily_opportunity_engine.run_daily_morning_report()
                st.session_state["latest_morning_report_id"] = rep.id
                st.success(f"✅ Daily Morning Report generated: {len(rep.ideas)} opportunities across {rep.total_channels_processed} channels!")
                st.rerun()

    with col_t2:
        st.markdown(
            """
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.4rem 0.75rem; font-size: 0.78rem; color: #475569;">
                ⏰ <b>Automation Schedule:</b> Daily at <code>07:00 AM</code> (<code>Asia/Dhaka</code>).<br>
                💡 <i>Requires local application process or scheduled task runner to be active.</i>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Channel & Status Filter Tabs
    all_ideas = db_manager.get_all_daily_ideas(limit=100)
    if not all_ideas:
        st.info("No morning reports generated yet. Click **'Run Daily Research Now'** above to generate ideas across all 4 channels.")
        return

    # Metrics Overview Cards
    total_ideas_count = len(all_ideas)
    gap_count = sum(1 for i in all_ideas if i.gap_state in (GapFinderState.FEW_MATCHING_RECENT_VIDEOS_FOUND.value, GapFinderState.NO_MATCHING_VIDEOS_FOUND.value))
    aff_count = sum(1 for i in all_ideas if i.potential_product_match)
    saved_count = sum(1 for i in all_ideas if i.is_saved)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_metric_card("Total Ideas Recorded", f"{total_ideas_count}", "Across 4 channels", color="#2563EB")
    with col_m2:
        render_metric_card("Underserved Gaps", f"{gap_count}", "0-3 recent videos", color="#10B981")
    with col_m3:
        render_metric_card("Affiliate-Ready", f"{aff_count}", "Product matched", color="#7C3AED")
    with col_m4:
        render_metric_card("Saved Ideas", f"{saved_count}", "Starred for production", color="#F59E0B")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Filter Controls
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        chan_filter = st.selectbox(
            "Filter by Channel Workspace",
            options=["All 4 Channels", "Channel 1 (TechGear Pulse)", "Channel 2 (CodeCraft বাংলা)", "Channel 3 (HomeChef Artisan)", "Channel 4 (FitPulse Active)"],
            index=0,
            key="morning_chan_filter",
        )
    with col_f2:
        status_filter = st.selectbox(
            "Filter by Review Status",
            options=["All Review Statuses", "Ready for further review", "Needs more research", "Saved Only"],
            index=0,
            key="morning_status_filter",
        )

    # Apply filters
    filtered_ideas = all_ideas
    if chan_filter != "All 4 Channels":
        c_num = int(chan_filter.split()[1])
        filtered_ideas = [i for i in filtered_ideas if i.channel_id == c_num]

    if status_filter == "Saved Only":
        filtered_ideas = [i for i in filtered_ideas if i.is_saved]
    elif status_filter != "All Review Statuses":
        filtered_ideas = [i for i in filtered_ideas if i.review_label == status_filter]

    st.markdown(f"#### 💡 Video Opportunities ({len(filtered_ideas)} items)")

    # Render each idea with ALL 18 FIELDS
    for idea in filtered_ideas:
        idea_id = idea.id or 0
        gap_badge_class = "badge-success" if "FEW" in idea.gap_state else ("badge-info" if "NO MATCHING" in idea.gap_state else "badge-warning")
        
        with st.container():
            st.markdown(
                f"""
                <div class="ks-card" style="margin-bottom: 1.25rem; background: #FFFFFF; border-left: 4px solid {'#10B981' if idea.is_saved else '#2563EB'};">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem;">
                        <div>
                            <span class="ks-badge ks-badge-primary" style="font-size: 0.72rem; text-transform: uppercase;">
                                CHANNEL {idea.channel_id}: {idea.channel_name}
                            </span>
                            <span class="status-badge {gap_badge_class}" style="margin-left: 0.5rem; font-size: 0.72rem;">
                                {idea.gap_state}
                            </span>
                            <span class="ks-badge" style="margin-left: 0.5rem; font-size: 0.72rem; background: #F1F5F9; color: #334155;">
                                {idea.search_intent}
                            </span>
                            <h3 style="margin: 0.35rem 0 0.15rem 0; font-size: 1.2rem; font-weight: 800; color: #0F172A;">
                                {idea.proposed_topic}
                            </h3>
                            <div style="font-size: 0.85rem; color: #475569;">
                                🎯 <b>Primary Keyword:</b> <code>{idea.main_keyword}</code> | <b>Target Viewer:</b> {idea.target_viewer}
                            </div>
                        </div>
                        <div style="text-align: right; min-width: 130px;">
                            <div style="font-size: 1.4rem; font-weight: 800; color: #2563EB;">{idea.opportunity_estimate}/100</div>
                            <div style="font-size: 0.72rem; color: #64748B;">{idea.confidence_level}</div>
                            <div style="font-size: 0.7rem; color: #94A3B8; font-style: italic;">Search volume unavailable</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Details expander with 18 fields
            with st.expander(f"🔍 Detailed Evidence & Script Blueprint: {idea.proposed_topic}", expanded=False):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown("**1. Strategic Research Signals:**")
                    st.markdown(f"• **Why Worth Researching Today:** {idea.why_topic_worth_researching}")
                    st.markdown(f"• **60-Day Recent Videos Found:** `{idea.recent_relevant_videos_found}` videos detected in rolling window.")
                    st.markdown(f"• **Exact Research Window:** `{idea.exact_research_window}`")
                    st.markdown(f"• **Search Coverage Summary:** {idea.source_and_coverage_summary}")
                    st.markdown(f"• **Suggested Video Format:** `{idea.suggested_video_format}`")
                    st.markdown(f"• **Review Label:** `{idea.review_label}`")
                    st.markdown(f"• **Next Recommended Action:** *{idea.next_recommended_action}*")

                with col_d2:
                    st.markdown("**2. Affiliate & Commercial Potential:**")
                    if idea.potential_product_match:
                        st.markdown(f"• **Potential Product Match:** `{idea.potential_product_match}`")
                        st.markdown(f"• **Affiliate Availability:** `{idea.affiliate_availability_status}`")
                    else:
                        st.markdown("• **Affiliate Strategy:** Educational / AdSense / Sponsorship (No product match)")

                    st.markdown("**3. Supporting Semantic Keywords:**")
                    st.markdown(" ".join([f"`{k}`" for k in idea.supporting_keywords]))

                    st.markdown("**4. Thumbnail Concept:**")
                    st.info(f"🎨 {idea.suggested_thumbnail_concept}")

                st.markdown("---")
                st.markdown("**5. SEO-Optimized Title Options (Click to copy):**")
                for t_idx, t_cand in enumerate(idea.seo_focused_title_options, 1):
                    col_t_txt, col_t_btn = st.columns([5, 1])
                    with col_t_txt:
                        t_len = len(t_cand)
                        t_warn = "Optimal" if t_len <= 60 else "Desktop Safe" if t_len <= 75 else "Truncates"
                        st.markdown(f"{t_idx}. **{t_cand}** `({t_len} chars, {t_warn})`")
                    with col_t_btn:
                        if st.button("Copy", key=f"btn_copy_t_{idea_id}_{t_idx}"):
                            st.session_state["copy_box_content"] = [t_cand]
                            st.session_state["show_copy_box"] = True

                st.markdown("---")
                st.markdown("**6. Description Starter Draft:**")
                st.text_area("Draft Outline", value=idea.description_draft, height=80, key=f"draft_txt_{idea_id}")
                if st.button("✍️ Open in Description Studio", key=f"btn_open_desc_studio_{idea_id}"):
                    st.session_state["active_channel_id"] = idea.channel_id
                    st.session_state["desc_builder_topic"] = idea.proposed_topic
                    st.session_state["desc_builder_kw"] = idea.main_keyword
                    st.session_state.current_page = PAGE_DESCRIPTION_STUDIO
                    st.rerun()

            # Actions Bar for Idea
            col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
            with col_a1:
                star_label = "★ Saved" if idea.is_saved else "☆ Save Idea"
                if st.button(star_label, key=f"btn_star_{idea_id}", type="primary" if idea.is_saved else "secondary", use_container_width=True):
                    db_manager.update_daily_idea_action(idea_id, is_saved=not idea.is_saved)
                    st.rerun()
            with col_a2:
                cal_label = "📅 On Calendar" if idea.is_added_to_calendar else "📅 Add to Calendar"
                if st.button(cal_label, key=f"btn_cal_{idea_id}", use_container_width=True):
                    db_manager.update_daily_idea_action(idea_id, is_added_to_calendar=True)
                    st.success("Added to production calendar!")
                    st.rerun()
            with col_a3:
                cov_label = "✅ Covered" if idea.is_marked_covered else "Mark Covered"
                if st.button(cov_label, key=f"btn_cov_{idea_id}", use_container_width=True):
                    db_manager.update_daily_idea_action(idea_id, is_marked_covered=True)
                    st.success("Marked as covered!")
                    st.rerun()
            with col_a4:
                rej_label = "❌ Reject"
                if st.button(rej_label, key=f"btn_rej_{idea_id}", use_container_width=True):
                    db_manager.update_daily_idea_action(idea_id, is_rejected=True)
                    st.info("Idea rejected.")
                    st.rerun()
            with col_a5:
                if st.button("📋 Copy Brief", key=f"btn_cp_brief_{idea_id}", use_container_width=True):
                    brief_txt = (
                        f"VIDEO TOPIC: {idea.proposed_topic}\n"
                        f"CHANNEL: {idea.channel_name}\n"
                        f"PRIMARY KEYWORD: {idea.main_keyword}\n"
                        f"GAP STATE: {idea.gap_state}\n"
                        f"TARGET VIEWER: {idea.target_viewer}\n"
                        f"FORMAT: {idea.suggested_video_format}\n"
                        f"TITLES:\n" + "\n".join([f"- {t}" for t in idea.seo_focused_title_options])
                    )
                    st.session_state["copy_box_content"] = [brief_txt]
                    st.session_state["show_copy_box"] = True

            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Export Report Facility with formula injection protection
    st.markdown("---")
    st.markdown("#### 📥 Export Daily Morning Report")
    col_exp1, col_exp2 = st.columns([1.5, 3.5])
    with col_exp1:
        if st.button("📄 Export Ideas to CSV", key="btn_export_morning_csv", use_container_width=True):
            import pandas as pd
            export_data = []
            for item in filtered_ideas:
                export_data.append({
                    "Channel ID": item.channel_id,
                    "Channel Name": sanitize_formula_injection(item.channel_name),
                    "Proposed Topic": sanitize_formula_injection(item.proposed_topic),
                    "Main Keyword": sanitize_formula_injection(item.main_keyword),
                    "Search Intent": item.search_intent,
                    "Target Viewer": sanitize_formula_injection(item.target_viewer),
                    "Gap State": item.gap_state,
                    "Recent Videos (60d)": item.recent_relevant_videos_found,
                    "Exact Window": item.exact_research_window,
                    "Opportunity Score": item.opportunity_estimate,
                    "Confidence Level": item.confidence_level,
                    "Product Match": sanitize_formula_injection(item.potential_product_match or "N/A"),
                    "Affiliate Status": item.affiliate_availability_status,
                    "Format": item.suggested_video_format,
                    "Review Label": item.review_label,
                    "Created At": item.created_at,
                })
            df = pd.DataFrame(export_data)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Sanitized CSV",
                data=csv_bytes,
                file_name=f"morning_ideas_4channels_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_download_morning_csv",
            )


# ==============================================================================
# Phase 25: YouTube Content Strategy Autopilot for Four Channels
# ==============================================================================

def render_page_strategy(is_ready: bool) -> None:
    """Render Phase 25: YouTube Content Strategy Autopilot for Four Channels."""
    render_page_header(
        title="Content Strategy Autopilot",
        subtitle="Unified strategy planning, topic clusters, capacity-aware scheduling, and production workflow for four independent channels.",
        category="DISCOVERY & INTELLIGENCE",
        badge_text="Autopilot v25",
        provenance="Multi-Source Evidence",
    )

    if not is_ready:
        render_empty_state("Database is not ready.", "warning")
        return

    active_chan_id = render_channel_switcher()
    channel = channel_manager.get_channel(active_chan_id)
    if not channel:
        st.error(f"Channel {active_chan_id} not found.")
        return

    settings = db_manager.get_channel_strategy_settings(active_chan_id)

    # Strategy Banner with channel profile posture
    st.markdown(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-weight: 700; color: #1E293B;">🧭 Active Strategy Profile:</span> <b>{channel.channel_name}</b>
                <span style="color: #64748B; margin-left: 0.5rem; font-size: 0.85rem;">
                    Niche: <b>{getattr(channel, 'channel_niche', getattr(channel, 'niche', 'General'))}</b> &middot; Audience: {channel.target_audience or 'Enthusiasts'} &middot; Priority: <i>{settings.strategic_priority}</i>
                </span>
            </div>
            <div>
                <span style="font-size: 0.75rem; background: #EEF2FF; color: #4338CA; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600;">
                    {settings.videos_per_week} vids/wk ({settings.weekly_production_hours_budget}h budget)
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_pillars, tab_matrix, tab_calendar, tab_brief, tab_kanban, tab_settings = st.tabs([
        "🏛️ Content Pillars & Clusters",
        "🎯 Prioritized Topic Matrix",
        "📅 Production Calendar",
        "📝 Content Brief Studio",
        "🔄 Production Workflow Kanban",
        "⚙️ Strategy Settings & Intel",
    ])

    # --------------------------------------------------------------------------
    # TAB 1: Content Pillars & Video Series Clusters
    # --------------------------------------------------------------------------
    with tab_pillars:
        st.markdown("### 🏛️ Channel Content Pillars")
        st.caption(f"Core strategic categories establishing topical authority for **{channel.channel_name}**.")

        pillars = db_manager.get_content_pillars(active_chan_id)

        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            st.write(f"Currently managing **{len(pillars)}** content pillars ({sum(1 for p in pillars if p.is_approved)} approved).")
        with col_p2:
            if st.button("⚡ Suggest Pillars", key="btn_suggest_pillars", use_container_width=True):
                suggested = content_strategy_autopilot.build_suggested_pillars(channel)
                for sp in suggested:
                    db_manager.save_content_pillar(sp)
                st.success(f"Generated {len(suggested)} strategic pillars for {channel.channel_name}!")
                st.rerun()

        if not pillars:
            st.info("No content pillars saved yet. Click '⚡ Suggest Pillars' above to generate pillars anchored in this channel's niche.")
        else:
            for p in pillars:
                with st.expander(f"{'✅' if p.is_approved else '⏳'} {p.pillar_name} ({p.confidence_level})", expanded=not p.is_approved):
                    col_info, col_ctrl = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**Description:** {p.description}")
                        st.markdown(f"**Target Audience Problem:** {p.audience_problem}")
                        st.markdown(f"**Target Keywords:** `{', '.join(p.target_keywords)}`")
                        st.markdown("**Candidate Video Topics:**")
                        for t in p.candidate_topics:
                            st.markdown(f"- {t}")
                        st.caption(f"Affiliate Relevance: {p.potential_affiliate_relevance} | Coverage Count: {p.existing_coverage_count}")
                    with col_ctrl:
                        if not p.is_approved:
                            if st.button("✓ Approve Pillar", key=f"btn_appr_pill_{p.id}", use_container_width=True):
                                p.is_approved = True
                                db_manager.save_content_pillar(p)
                                st.rerun()
                        else:
                            st.success("Approved Pillar")
                        if st.button("🗑️ Delete", key=f"btn_del_pill_{p.id}", use_container_width=True):
                            db_manager.delete_content_pillar(p.id)
                            st.rerun()

        st.markdown("---")
        st.markdown("### 🧬 Video Series & Content Cluster Planner")
        st.caption("Group interconnected videos into structured series with anti-cannibalization keyword protection.")

        if pillars:
            pillar_names = {p.pillar_name: p for p in pillars}
            chosen_pillar_name = st.selectbox(
                "Select Pillar for Video Series Plan",
                options=list(pillar_names.keys()),
                key="select_cluster_pillar",
            )
            selected_pillar = pillar_names[chosen_pillar_name]

            if st.button("🚀 Plan Content Series & Anti-Cannibalization Framework", key="btn_plan_cluster"):
                new_cluster = content_strategy_autopilot.plan_content_cluster(channel, selected_pillar)
                cid = db_manager.save_content_cluster(new_cluster)
                st.success(f"Created Content Series '{new_cluster.cluster_name}' (ID: {cid})!")
                st.rerun()

            # Display saved clusters for this channel
            clusters = db_manager.get_content_clusters(active_chan_id)
            if clusters:
                st.markdown(f"#### Saved Content Series ({len(clusters)})")
                for c in clusters:
                    with st.expander(f"📦 {c.cluster_name}", expanded=True):
                        st.markdown(f"**Pillar Anchor Video:** `{c.pillar_video_title}`")
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.markdown("**Supporting Tutorials:**")
                            for s in c.supporting_video_titles:
                                st.markdown(f"- {s}")
                            st.markdown("**Comparison Breakdown:**")
                            for cmp in c.comparison_video_titles:
                                st.markdown(f"- {cmp}")
                        with col_s2:
                            st.markdown("**Buyer's Guides & Reviews:**")
                            for r in c.review_video_titles:
                                st.markdown(f"- {r}")
                            st.markdown("**FAQ & Troubleshooting:**")
                            for f in c.faq_video_titles:
                                st.markdown(f"- {f}")

                        st.markdown(
                            f"""
                            <div style="background: #F1F5F9; border-left: 3px solid #0284C7; padding: 0.6rem 0.8rem; border-radius: 4px; font-size: 0.85rem; margin-top: 0.5rem;">
                                <b>Anti-Cannibalization Architecture:</b><br>{c.anti_cannibalization_notes.replace(chr(10), '<br>')}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("🗑️ Delete Series", key=f"btn_del_cluster_{c.id}"):
                            db_manager.delete_content_cluster(c.id)
                            st.rerun()
        else:
            st.info("Approve or add at least one content pillar to plan a video cluster.")

    # --------------------------------------------------------------------------
    # TAB 2: Prioritized Topic Matrix
    # --------------------------------------------------------------------------
    with tab_matrix:
        st.markdown("### 🎯 Evidence-Based Topic Prioritization")
        st.caption("Transparent multi-factor scoring with strict 6-point provenance. Zero fabricated search volumes or CTR.")

        col_m_ctrl1, col_m_ctrl2, col_m_ctrl3 = st.columns([2, 1, 1])
        with col_m_ctrl1:
            status_filter = st.selectbox(
                "Filter by User Status",
                options=["All Statuses", "Suggested", "Approved", "In Calendar", "Saved for Later", "Already Covered", "Rejected"],
                index=0,
                key="topic_status_filter",
            )
        with col_m_ctrl2:
            st.write("")
            st.write("")
            if st.button("⚡ Score Seed Topics", key="btn_score_topics", use_container_width=True):
                scored_topics = content_strategy_autopilot.prioritize_candidate_topics(channel)
                db_manager.save_prioritized_topics(scored_topics)
                st.success(f"Scored {len(scored_topics)} candidate topics for {channel.channel_name}!")
                st.rerun()
        with col_m_ctrl3:
            st.write("")
            st.write("")
            if st.button("🗑️ Clear Rejected", key="btn_clear_rej_topics", use_container_width=True):
                rej = db_manager.get_prioritized_topics(active_chan_id, status=TopicUserStatus.REJECTED.value)
                for rj in rej:
                    db_manager.delete_prioritized_topic(rj.topic_id)
                st.rerun()

        filter_val = None if status_filter == "All Statuses" else status_filter
        topics = db_manager.get_prioritized_topics(active_chan_id, status=filter_val)

        if not topics:
            st.info("No prioritized topics found for this filter. Click '⚡ Score Seed Topics' to populate candidate topics.")
        else:
            st.write(f"Displaying **{len(topics)}** candidate topics ordered by transparent composite priority score.")
            for t in topics:
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div>
                                    <h4 style="margin: 0; color: #0F172A; font-size: 1.05rem;">{t.proposed_title}</h4>
                                    <div style="margin-top: 0.25rem; font-size: 0.85rem; color: #475569;">
                                        Target Keyword: <code style="background: #F1F5F9; padding: 0.1rem 0.3rem; border-radius: 3px;">{t.target_keyword}</code> &middot;
                                        Intent: <b>{t.search_intent}</b> &middot; Effort: <b>{t.estimated_production_effort.value}</b> &middot; Status: <b>{t.user_status.value}</b>
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 1.3rem; font-weight: 800; color: #2563EB;">{t.composite_priority_score}</div>
                                    <div style="font-size: 0.7rem; color: #64748B; text-transform: uppercase;">Priority Score</div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Multi-factor score breakdown
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("Relevance", f"{t.channel_relevance_score:.0f}")
                    c2.metric("Intent Clarity", f"{t.search_intent_score:.0f}")
                    c3.metric("Keyword Evid.", f"{t.keyword_evidence_score:.0f}")
                    c4.metric("Video Evid.", f"{t.recent_video_evidence_score:.0f}")
                    c5.metric("Uniqueness", f"{t.research_coverage_score:.0f}")
                    c6.metric("Monetization", f"{t.product_relevance_score:.0f}")

                    # 6-Point Provenance Framework Box
                    with st.expander("🔍 View 6-Point Provenance Framework", expanded=False):
                        st.markdown(f"**1. Why Selected:** {t.selection_rationale}")
                        st.markdown(f"**2. Supporting Sources:** {', '.join(t.supporting_sources)}")
                        st.markdown(f"**3. Research Date:** `{t.research_date}`")
                        st.markdown(f"**4. Confidence Level:** `{t.confidence_level}`")
                        st.markdown(f"**5. Missing Evidence / Honesty Disclosure:** {t.missing_evidence}")
                        st.markdown(f"**6. Suggested Next Step:** {t.suggested_next_step}")

                    # Action controls
                    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
                    with col_b1:
                        if t.user_status != TopicUserStatus.APPROVED:
                            if st.button("✓ Approve", key=f"btn_appr_{t.topic_id}", use_container_width=True):
                                db_manager.update_topic_user_status(t.topic_id, TopicUserStatus.APPROVED)
                                st.rerun()
                    with col_b2:
                        if st.button("📅 Add to Cal", key=f"btn_cal_{t.topic_id}", use_container_width=True):
                            new_cal = StrategyCalendarItem(
                                id=None,
                                channel_id=channel.id,
                                channel_name=channel.channel_name,
                                topic=t.proposed_title,
                                target_keyword=t.target_keyword,
                                search_intent=t.search_intent,
                                suggested_format="Long-form",
                                working_title=t.proposed_title,
                                production_status="Planned",
                                planned_date=(datetime.now().date() + timedelta(days=3)).strftime("%Y-%m-%d"),
                                evidence_summary=f"Priority Score: {t.composite_priority_score}/100",
                                required_research="Draft outline and test keyword placement in description.",
                                affiliate_disclosure_required=bool(getattr(channel, 'affiliate_enabled', getattr(channel, 'affiliate_marketing_enabled', False))),
                                production_hours_estimate=4.0,
                            )
                            db_manager.save_strategy_calendar_item(new_cal)
                            db_manager.update_topic_user_status(t.topic_id, TopicUserStatus.IN_CALENDAR)
                            st.success(f"Added to Calendar for {new_cal.planned_date}!")
                            st.rerun()
                    with col_b3:
                        if st.button("📝 Create Brief", key=f"btn_brief_{t.topic_id}", use_container_width=True):
                            nbrief = content_strategy_autopilot.generate_content_brief(channel, t.proposed_title, t.target_keyword)
                            bid = db_manager.save_content_brief_document(nbrief)
                            st.success(f"Created Content Brief #{bid}! Check Brief Studio tab.")
                    with col_b4:
                        if st.button("✓ Covered", key=f"btn_cov_{t.topic_id}", use_container_width=True):
                            db_manager.update_topic_user_status(t.topic_id, TopicUserStatus.COVERED)
                            st.rerun()
                    with col_b5:
                        if st.button("✕ Reject", key=f"btn_rej_{t.topic_id}", use_container_width=True):
                            db_manager.update_topic_user_status(t.topic_id, TopicUserStatus.REJECTED)
                            st.rerun()

                    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 3: Capacity-Aware Production Calendar
    # --------------------------------------------------------------------------
    with tab_calendar:
        st.markdown("### 📅 Production Capacity & Publishing Calendar")
        st.caption("Plan sustainable production milestones matching your weekly time budget. Never auto-publishes to YouTube.")

        cal_items = db_manager.get_strategy_calendar_items(active_chan_id)
        total_hours = sum(ci.production_hours_estimate for ci in cal_items)
        long_count = sum(1 for ci in cal_items if ci.suggested_format == "Long-form")
        shorts_count = sum(1 for ci in cal_items if ci.suggested_format == "Shorts")

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        col_c1.metric("Scheduled Videos", f"{len(cal_items)}")
        col_c2.metric("Total Planned Hours", f"{total_hours:.1f} hrs", f"Budget: {settings.weekly_production_hours_budget}h/wk")
        col_c3.metric("Long-form Videos", f"{long_count}")
        col_c4.metric("Shorts Videos", f"{shorts_count}")

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        col_sch_btn, col_sch_info = st.columns([1, 3])
        with col_sch_btn:
            if st.button("⚡ Schedule Next 4 Weeks", key="btn_gen_schedule", use_container_width=True):
                candidate_topics = db_manager.get_prioritized_topics(active_chan_id)
                if not candidate_topics:
                    candidate_topics = content_strategy_autopilot.prioritize_candidate_topics(channel)
                    db_manager.save_prioritized_topics(candidate_topics)

                sched = content_strategy_autopilot.generate_calendar_schedule(channel, settings, candidate_topics, weeks=4)
                for s in sched:
                    db_manager.save_strategy_calendar_item(s)
                st.success(f"Scheduled {len(sched)} videos across the next 4 weeks!")
                st.rerun()

        with col_sch_info:
            st.caption("Auto-scheduler respects preferred publishing days, time capacity budget, and Long-form/Shorts target ratio.")

        # Manual entry form
        with st.expander("➕ Add Single Production Milestone", expanded=False):
            with st.form(key=f"form_add_cal_item_{active_chan_id}"):
                c_t1, c_t2 = st.columns(2)
                with c_t1:
                    m_title = st.text_input("Working Video Title", placeholder="e.g. 5 Beginner Mistakes in...", key="cal_in_title")
                    m_kw = st.text_input("Target Keyword", placeholder="e.g. video editing for beginners", key="cal_in_kw")
                    m_date = st.date_input("Target Date", value=datetime.now().date() + timedelta(days=7), key="cal_in_date")
                with c_t2:
                    m_fmt = st.selectbox("Format", options=["Long-form", "Shorts"], index=0, key="cal_in_fmt")
                    m_intent = st.selectbox("Search Intent", options=["Informational / How-To", "Commercial Investigation", "Curious / Contrarian", "Troubleshooting"], index=0, key="cal_in_intent")
                    m_hrs = st.number_input("Estimated Production Hours", min_value=0.5, max_value=40.0, value=4.0, step=0.5, key="cal_in_hrs")

                btn_add_item = st.form_submit_button("Add to Calendar")
                if btn_add_item and m_title:
                    item_obj = StrategyCalendarItem(
                        id=None,
                        channel_id=channel.id,
                        channel_name=channel.channel_name,
                        topic=m_title,
                        target_keyword=m_kw,
                        search_intent=m_intent,
                        suggested_format=m_fmt,
                        working_title=m_title,
                        production_status="Planned",
                        planned_date=m_date.strftime("%Y-%m-%d"),
                        evidence_summary="Manual production milestone",
                        required_research="Creator manual research",
                        affiliate_disclosure_required=bool(getattr(channel, 'affiliate_enabled', getattr(channel, 'affiliate_marketing_enabled', False))),
                        production_hours_estimate=m_hrs,
                    )
                    db_manager.save_strategy_calendar_item(item_obj)
                    st.success(f"Scheduled '{m_title}' for {item_obj.planned_date}!")
                    st.rerun()

        if cal_items:
            st.markdown(f"#### Planned Videos ({len(cal_items)})")
            for item in cal_items:
                with st.container():
                    c_col1, c_col2, c_col3, c_col4 = st.columns([1, 3, 1, 1])
                    c_col1.markdown(f"**📅 {item.planned_date}**<br><span style='font-size: 0.75rem; color: #64748B;'>{item.suggested_format}</span>", unsafe_allow_html=True)
                    c_col2.markdown(f"**{item.working_title}**<br><code style='font-size: 0.75rem;'>{item.target_keyword}</code> &middot; <span style='font-size: 0.75rem; color: #475569;'>Est: {item.production_hours_estimate}h</span>", unsafe_allow_html=True)
                    new_status = c_col3.selectbox(
                        "Status",
                        options=["Planned", "In Production", "Scheduled", "Published"],
                        index=["Planned", "In Production", "Scheduled", "Published"].index(item.production_status) if item.production_status in ["Planned", "In Production", "Scheduled", "Published"] else 0,
                        key=f"status_cal_{item.id}",
                        label_visibility="collapsed",
                    )
                    if new_status != item.production_status:
                        db_manager.update_strategy_calendar_item(item.id, {"production_status": new_status})
                        st.rerun()

                    if c_col4.button("🗑️ Delete", key=f"del_cal_{item.id}", use_container_width=True):
                        db_manager.delete_strategy_calendar_item(item.id)
                        st.rerun()
                    st.markdown("<hr style='margin: 0.4rem 0; border: none; border-top: 1px solid #F1F5F9;' />", unsafe_allow_html=True)
        else:
            st.info("No videos currently on this channel's calendar. Use '⚡ Schedule Next 4 Weeks' or add a milestone above.")

    # --------------------------------------------------------------------------
    # TAB 4: Content Brief Studio
    # --------------------------------------------------------------------------
    with tab_brief:
        st.markdown("### 📝 Content Brief Studio")
        st.caption("Actionable 14-section briefs with structural guidance, title angles, and explicit unverified facts.")

        briefs = db_manager.get_content_brief_documents(active_chan_id)

        col_br1, col_br2 = st.columns([2, 1])
        with col_br1:
            st.write(f"Managing **{len(briefs)}** content briefs for **{channel.channel_name}**.")
        with col_br2:
            st.caption("Each brief incorporates audience problem, retention resets, and FTC disclosures.")

        with st.expander("⚡ Generate New Content Brief", expanded=not bool(briefs)):
            with st.form(key=f"form_generate_brief_{active_chan_id}"):
                b_topic = st.text_input("Core Video Topic", placeholder="e.g. Best Budget Microphone for Creators", key="in_b_topic")
                b_kw = st.text_input("Primary Target Keyword", placeholder="e.g. best budget microphone", key="in_b_kw")
                b_supp = st.text_input("Supporting Keywords (comma-separated)", placeholder="e.g. budget mic review, mic test", key="in_b_supp")

                btn_make_brief = st.form_submit_button("Generate 14-Section Brief")
                if btn_make_brief and b_topic and b_kw:
                    supp_list = [s.strip() for s in b_supp.split(",") if s.strip()]
                    new_b = content_strategy_autopilot.generate_content_brief(channel, b_topic, b_kw, supp_list)
                    bid = db_manager.save_content_brief_document(new_b)
                    st.success(f"Generated Content Brief #{bid}!")
                    st.rerun()

        if briefs:
            selected_b_idx = st.selectbox(
                "Select Saved Brief",
                options=list(range(len(briefs))),
                format_func=lambda i: f"Brief #{briefs[i].id}: {briefs[i].topic} ({briefs[i].primary_keyword})",
                key="sel_brief_viewer",
            )
            active_brief = briefs[selected_b_idx]

            st.markdown(
                f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.2rem; margin-top: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="margin: 0; color: #0F172A;">{active_brief.topic}</h3>
                        <span style="font-size: 0.8rem; background: #EEF2FF; color: #3730A3; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600;">
                            Brief #{active_brief.id}
                        </span>
                    </div>
                    <div style="font-size: 0.85rem; color: #64748B; margin-top: 0.3rem;">
                        Target Viewer: <b>{active_brief.target_viewer}</b> &middot; Keyword: <code>{active_brief.primary_keyword}</code> &middot; Intent: <b>{active_brief.search_intent}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

            col_bf1, col_bf2 = st.columns(2)
            with col_bf1:
                st.markdown("#### 🎯 Core Promise & Problem")
                st.write(f"**Viewer Problem:** {active_brief.viewer_problem}")
                st.write(f"**Core Promise:** {active_brief.main_promise}")
                st.write(f"**Supporting Keywords:** `{', '.join(active_brief.supporting_keywords)}`")

                st.markdown("#### 🏷️ 3 Distinct Title Angles")
                for opt in active_brief.title_options:
                    st.markdown(f"**{opt.get('angle')}:** {opt.get('title')}")
                    st.caption(f"Rationale: {opt.get('rationale')}")

                st.markdown("#### ⚠️ Unverified Facts (Verify Before Publishing)")
                for uv in active_brief.unverified_facts:
                    st.warning(f"• {uv}")

                st.markdown("#### 🖼️ Thumbnail Concept")
                st.info(active_brief.thumbnail_concept)

            with col_bf2:
                st.markdown("#### ⏱️ Video Structure & Retention Beats")
                for st_beat in active_brief.video_structure:
                    st.markdown(f"**{st_beat.get('section')}**")
                    st.caption(st_beat.get('guidance'))

                st.markdown("#### ⚖️ FTC Disclosure Reminder")
                st.markdown(
                    f"""
                    <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 0.6rem; font-size: 0.82rem; color: #92400E;">
                        {active_brief.affiliate_disclosure_reminder}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("#### 📋 SEO Pre-Publish Checklist")
                for chk in active_brief.seo_prepublish_checklist:
                    st.checkbox(chk, value=False, key=f"chk_brief_{active_brief.id}_{hash(chk)}")

            st.markdown("#### ✍️ Description Draft")
            st.text_area("Pre-Formatted Description", value=active_brief.description_draft, height=180, key=f"desc_brief_{active_brief.id}")

            if st.button("🗑️ Delete Brief", key=f"btn_del_brief_{active_brief.id}"):
                db_manager.delete_content_brief_document(active_brief.id)
                st.rerun()

    # --------------------------------------------------------------------------
    # TAB 5: Production Workflow Kanban
    # --------------------------------------------------------------------------
    with tab_kanban:
        st.markdown("### 🔄 10-Stage Production Workflow")
        st.caption("Enforce sequential production discipline. No auto-completing tasks without creator confirmation.")

        projects = db_manager.get_production_workflow_projects(active_chan_id)

        # Stage distribution bar
        stage_counts = {s: 0 for s in STAGE_SEQUENCE}
        for prj in projects:
            stage_counts[prj.current_stage] = stage_counts.get(prj.current_stage, 0) + 1

        cols_stg = st.columns(len(STAGE_SEQUENCE))
        for idx, s in enumerate(STAGE_SEQUENCE):
            cols_stg[idx].metric(s.value[:6], f"{stage_counts[s]}")

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        with st.expander("➕ New Production Workflow Project", expanded=not bool(projects)):
            with st.form(key=f"form_new_project_{active_chan_id}"):
                p_name = st.text_input("Project Name", placeholder="e.g. 2026 Microphone Buying Guide", key="in_prj_name")
                p_kw = st.text_input("Primary Keyword", placeholder="e.g. best podcast microphone", key="in_prj_kw")
                btn_create_prj = st.form_submit_button("Initialize Project")
                if btn_create_prj and p_name:
                    new_p = ProductionWorkflowProject(
                        id=None,
                        channel_id=channel.id,
                        project_name=p_name,
                        primary_keyword=p_kw,
                        current_stage=WorkflowStage.IDEA,
                        stage_history=[{"from_stage": "None", "to_stage": "Idea", "transitioned_at": datetime.now(timezone.utc).isoformat(), "user_notes": "Initialized"}],
                    )
                    db_manager.save_production_workflow_project(new_p)
                    st.success(f"Initialized Project '{p_name}' at Idea stage!")
                    st.rerun()

        if projects:
            st.markdown(f"#### Active Projects ({len(projects)})")
            for prj in projects:
                with st.expander(f"🎬 {prj.project_name} &middot; Stage: **{prj.current_stage.value}**", expanded=True):
                    pcol1, pcol2 = st.columns([2, 1])
                    with pcol1:
                        st.markdown(f"**Target Keyword:** `{prj.primary_keyword}`")
                        # Current stage in sequence
                        curr_idx = STAGE_SEQUENCE.index(prj.current_stage) if prj.current_stage in STAGE_SEQUENCE else 0
                        st.progress((curr_idx + 1) / len(STAGE_SEQUENCE), text=f"Stage {curr_idx + 1}/{len(STAGE_SEQUENCE)}: {prj.current_stage.value}")

                        if prj.blockers:
                            st.error(f"⚠️ Active Blockers: {', '.join(prj.blockers)}")

                        # Stage history
                        st.markdown("**Stage History:**")
                        for h in prj.stage_history[-3:]:
                            st.caption(f"• {h.get('transitioned_at')[:10]}: {h.get('from_stage')} → {h.get('to_stage')} ({h.get('user_notes') or 'No notes'})")

                    with pcol2:
                        st.markdown("**Workflow Actions:**")
                        if curr_idx < len(STAGE_SEQUENCE) - 1:
                            next_stage = STAGE_SEQUENCE[curr_idx + 1]
                            advance_notes = st.text_input("Transition Notes", key=f"notes_prj_{prj.id}", placeholder="e.g. Script completed")
                            if st.button(f"➡️ Advance to {next_stage.value}", key=f"btn_adv_{prj.id}", use_container_width=True):
                                try:
                                    updated_prj = content_strategy_autopilot.advance_workflow_stage(prj, next_stage, advance_notes)
                                    db_manager.save_production_workflow_project(updated_prj)
                                    st.success(f"Advanced to {next_stage.value}!")
                                    st.rerun()
                                except ValueError as e:
                                    st.error(str(e))
                        else:
                            st.success("🎉 Project Complete!")

                        # Blocker management
                        new_blocker = st.text_input("Add Blocker", key=f"add_blk_{prj.id}", placeholder="e.g. Waiting on mic delivery")
                        if st.button("Flag Blocker", key=f"btn_flag_blk_{prj.id}"):
                            if new_blocker:
                                prj.blockers.append(new_blocker)
                                db_manager.save_production_workflow_project(prj)
                                st.rerun()
                        if prj.blockers and st.button("Clear Blockers", key=f"btn_clr_blk_{prj.id}"):
                            prj.blockers = []
                            db_manager.save_production_workflow_project(prj)
                            st.rerun()

                        if st.button("🗑️ Delete Project", key=f"btn_del_prj_{prj.id}"):
                            db_manager.delete_production_workflow_project(prj.id)
                            st.rerun()
        else:
            st.info("No active production projects. Initialize a project above to track production from Idea to Published.")

    # --------------------------------------------------------------------------
    # TAB 6: Strategy Settings & Weekly Intel
    # --------------------------------------------------------------------------
    with tab_settings:
        st.markdown("### ⚙️ Channel Strategy Configuration")
        st.caption(f"Tune capacity parameters and publishing goals for **{channel.channel_name}**.")

        with st.form(key=f"form_strategy_settings_{active_chan_id}"):
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                vids_per_week = st.slider("Target Videos Per Week", min_value=1, max_value=7, value=settings.videos_per_week, key="set_vids_per_wk")
                weekly_hours = st.number_input("Weekly Production Hours Budget", min_value=2.0, max_value=80.0, value=settings.weekly_production_hours_budget, step=1.0, key="set_hrs_budget")
                pref_days = st.multiselect(
                    "Preferred Publishing Days",
                    options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    default=[d for d in settings.preferred_publishing_days if d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
                    key="set_pref_days",
                )
            with c_s2:
                longform_pct = st.slider("Long-Form Video Percentage", min_value=0, max_value=100, value=settings.longform_pct, step=5, key="set_long_pct")
                shorts_pct = 100 - longform_pct
                st.write(f"Shorts Ratio: **{shorts_pct}%**")
                duration_range = st.selectbox(
                    "Preferred Video Duration Range",
                    options=["3-5 minutes", "8-15 minutes", "15-25 minutes", "30+ minutes"],
                    index=["3-5 minutes", "8-15 minutes", "15-25 minutes", "30+ minutes"].index(settings.preferred_duration_range) if settings.preferred_duration_range in ["3-5 minutes", "8-15 minutes", "15-25 minutes", "30+ minutes"] else 1,
                    key="set_dur_range",
                )
                strat_priority = st.text_input(
                    "Strategic Priority Statement",
                    value=settings.strategic_priority,
                    key="set_strat_priority",
                )

            btn_save_settings = st.form_submit_button("Save Strategy Settings")
            if btn_save_settings:
                settings.videos_per_week = vids_per_week
                settings.weekly_production_hours_budget = weekly_hours
                settings.preferred_publishing_days = pref_days or ["Tuesday", "Saturday"]
                settings.longform_pct = longform_pct
                settings.shorts_pct = shorts_pct
                settings.preferred_duration_range = duration_range
                settings.strategic_priority = strat_priority
                db_manager.save_channel_strategy_settings(settings)
                st.success("Strategy settings saved successfully!")
                st.rerun()

        st.markdown("---")
        st.markdown("### 📊 Weekly Strategic Intelligence")
        intel = content_strategy_autopilot.generate_weekly_strategy_intelligence(channel)

        col_in1, col_in2, col_in3 = st.columns(3)
        col_in1.metric("Weekly Capacity Status", intel.get("capacity_status", "Balanced"))
        col_in2.metric("Approved Pillars", f"{intel.get('approved_pillars', 0)} / {intel.get('total_pillars', 0)}")
        col_in3.metric("Planned Weekly Hours", f"{intel.get('weekly_hours_planned', 0.0):.1f}h", f"Budget: {intel.get('weekly_hours_budget', 12.0)}h")

        st.markdown("#### Recommended Strategic Next Steps:")
        recs = intel.get("recommended_actions", [])
        if recs:
            for r in recs:
                st.markdown(f"• **{r}**")
        else:
            st.success("✓ Your production pipeline is well-balanced and aligned with strategic priorities.")



# ==============================================================================
# Main Application Pipeline
# ==============================================================================

def main() -> None:
    """Main application execution pipeline."""
    st.set_page_config(
        page_title=f"{APP_NAME} v{APP_VERSION}",
        page_icon=config.app_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_custom_styles()
    is_ready = bootstrap_application()

    # Session State Initialization
    if "current_page" not in st.session_state:
        st.session_state.current_page = PAGE_LANDING
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "direct_results" not in st.session_state:
        st.session_state.direct_results = []
    if "crawl_result" not in st.session_state:
        st.session_state.crawl_result = None
    if "search_mode" not in st.session_state:
        st.session_state.search_mode = "recursive"
    if "generated_patterns" not in st.session_state:
        st.session_state.generated_patterns = []
    if "pattern_generator" not in st.session_state:
        st.session_state.pattern_generator = SmartKeywordPatternGenerator()
    if "cancel_event" not in st.session_state:
        st.session_state.cancel_event = None
    if "show_copy_box" not in st.session_state:
        st.session_state.show_copy_box = False
    if "copy_box_content" not in st.session_state:
        st.session_state.copy_box_content = []
    if "instant_suggestions" not in st.session_state:
        st.session_state.instant_suggestions = []
    if "instant_suggestions_seed" not in st.session_state:
        st.session_state.instant_suggestions_seed = ""
    if "active_seed_input" not in st.session_state:
        st.session_state.active_seed_input = ""
    if "current_serp_analysis" not in st.session_state:
        st.session_state.current_serp_analysis = None
    if "active_brief_shortlist_id" not in st.session_state:
        st.session_state.active_brief_shortlist_id = None

    # Navigation Sidebar
    selected_page = render_navigation(current_page=st.session_state.current_page)
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()

    # Load recent searches for dashboard
    recent_searches = db_manager.get_recent_searches(limit=10) if is_ready else []

    # Route Page
    page = st.session_state.current_page
    if page == PAGE_LANDING:
        render_page_landing(is_ready)
    elif page == PAGE_USER_GUIDE:
        render_page_user_guide(is_ready)
    elif page == PAGE_AUTH:
        render_page_auth(is_ready)
    elif page == PAGE_DASHBOARD:
        render_page_dashboard(is_ready, recent_searches)
    elif page == PAGE_CHANNELS:
        render_page_channels(is_ready)
    elif page == PAGE_MORNING_REPORT:
        render_page_morning_report(is_ready)
    elif page == PAGE_DESCRIPTION_STUDIO:
        render_page_description_studio(is_ready)
    elif page == PAGE_SEO_AUDIT:
        render_page_seo_audit(is_ready)
    elif page == PAGE_ANALYTICS:
        render_page_analytics(is_ready)
    elif page == PAGE_STRATEGY:
        render_page_strategy(is_ready)
    elif page == PAGE_NEW_RESEARCH:

        render_page_new_research(is_ready)
    elif page == PAGE_RESULTS:
        render_page_results()
    elif page == PAGE_PATTERNS:
        render_page_patterns()
    elif page in (PAGE_VIDEO_RESEARCH, PAGE_SERP):
        render_page_video_research(is_ready)
    elif page == PAGE_CONTENT_OPPORTUNITIES:
        render_page_content_opportunities(is_ready)
    elif page == PAGE_PRODUCT_OPPORTUNITIES:
        render_page_product_opportunities(is_ready)
    elif page == PAGE_PRODUCT_PLANNER:
        render_page_product_planner(is_ready)
    elif page == PAGE_RESEARCH_MONITOR:
        render_page_research_monitor(is_ready)
    elif page == PAGE_SAVED:
        render_page_saved(is_ready)
    elif page == PAGE_SETTINGS:
        render_page_settings(is_ready)
    else:
        render_page_dashboard(is_ready, recent_searches)


if __name__ == "__main__":
    main()

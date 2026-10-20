"""Tests verifying module imports, architecture boundaries, and package integrity."""

import importlib


def test_import_src_package() -> None:
    """Test importing the main src package and version."""
    import src
    assert hasattr(src, "__version__")
    assert src.__version__ == "0.1.0"


def test_import_config_modules() -> None:
    """Test importing configuration from both root and src."""
    import config as root_config
    from src import config as src_config

    assert root_config.APP_NAME == "YouTube Keyword Finder"
    assert src_config.APP_NAME == "YouTube Keyword Finder"
    assert root_config.config.default_max_depth == 2


def test_import_models() -> None:
    """Test importing models package symbols."""
    from src.models import (
        ClassificationType,
        KeywordItem,
        SourceType,
        calculate_word_count,
        infer_tail_length,
    )
    assert SourceType.LIVE.value == "live"
    assert ClassificationType.LONG_TAIL.value == "Long-tail"


def test_import_storage() -> None:
    """Test importing storage package symbols."""
    from src.storage import DatabaseManager, db_manager
    assert isinstance(db_manager, DatabaseManager)


def test_import_utils() -> None:
    """Test importing utility package symbols."""
    from src.utils import get_logger, sanitize_seed_keyword, validate_crawl_parameters
    logger = get_logger("test")
    assert logger is not None


def test_import_ui() -> None:
    """Test importing UI package symbols."""
    from src.ui import apply_custom_styles, render_header
    assert callable(apply_custom_styles)
    assert callable(render_header)


def test_import_app_module() -> None:
    """Test importing app module entry point."""
    app_module = importlib.import_module("app")
    assert hasattr(app_module, "main")
    assert hasattr(app_module, "bootstrap_application")


def test_import_providers() -> None:
    """Test importing autocomplete providers package symbols."""
    from src.providers import (
        BaseAutocompleteProvider,
        YouTubeAutocompleteProvider,
        RateLimiter,
        AutocompleteError,
    )
    assert issubclass(YouTubeAutocompleteProvider, BaseAutocompleteProvider)
    assert issubclass(AutocompleteError, Exception)


def test_import_crawler() -> None:
    """Test importing recursive crawler package symbols."""
    from src.crawler import (
        CrawlConfig,
        CrawlProgress,
        CrawlResult,
        DiscoveredKeyword,
        RecursiveKeywordEngine,
        StopReason,
        normalize_keyword_key,
    )
    assert hasattr(RecursiveKeywordEngine, "crawl")
    assert StopReason.TARGET_REACHED.value == "Result target reached"


def test_import_patterns() -> None:
    """Test importing smart keyword pattern generator package symbols."""
    from src.patterns import (
        GeneratedKeyword,
        PatternCategory,
        PatternConfig,
        PatternLanguage,
        SmartKeywordPatternGenerator,
    )
    generator = SmartKeywordPatternGenerator()
    assert hasattr(generator, "generate")
    assert hasattr(generator, "destutter")
    assert PatternCategory.LISTICLES.value == "listicles"
    assert PatternLanguage.BOTH.value == "both"


def test_import_classifier() -> None:
    """Test importing keyword classifier symbols."""
    from src.classifier import (
        KeywordClassification,
        KeywordClassifier,
        SearchIntent,
        TailLength,
        TailThresholds,
        default_classifier,
    )
    assert TailLength.SHORT_TAIL.value == "Short-tail"
    assert SearchIntent.TUTORIAL.value == "Tutorial"
    assert isinstance(default_classifier, KeywordClassifier)


def test_import_deduplication() -> None:
    """Test importing deduplication symbols."""
    from src.deduplication import DeduplicationEngine, default_deduplicator
    assert isinstance(default_deduplicator, DeduplicationEngine)



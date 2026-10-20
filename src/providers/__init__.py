"""Providers package for autocomplete, SERP, and AI engines."""

from src.providers.base import BaseAutocompleteProvider
from src.providers.exceptions import (
    AccessForbiddenError,
    AutocompleteError,
    MalformedResponseError,
    NetworkConnectionError,
    NetworkError,
    NetworkTimeoutError,
    OperationCancelledError,
    ProviderUnavailableError,
    RateLimitError,
)
from src.providers.rate_limiter import RateLimiter
from src.providers.youtube import YouTubeAutocompleteProvider
from src.providers.serp import (
    BaseSerpMetricsProvider,
    SerpMetrics,
    UnconnectedSerpMetricsProvider,
    YouTubeDataApiSerpProvider,
    default_serp_provider,
)
from src.providers.ai import (
    BaseAiProvider,
    DeterministicFallbackAiProvider,
    GeminiAiProvider,
    OpenAiProvider,
    MockAiProvider,
    get_ai_provider,
)
from src.providers.youtube_analytics import (
    YouTubeAnalyticsProvider,
    youtube_analytics_provider,
)

__all__ = [
    "BaseAutocompleteProvider",
    "YouTubeAutocompleteProvider",
    "RateLimiter",
    "AutocompleteError",
    "NetworkError",
    "NetworkTimeoutError",
    "NetworkConnectionError",
    "AccessForbiddenError",
    "RateLimitError",
    "ProviderUnavailableError",
    "MalformedResponseError",
    "OperationCancelledError",
    "BaseSerpMetricsProvider",
    "SerpMetrics",
    "UnconnectedSerpMetricsProvider",
    "YouTubeDataApiSerpProvider",
    "default_serp_provider",
    "BaseAiProvider",
    "DeterministicFallbackAiProvider",
    "GeminiAiProvider",
    "OpenAiProvider",
    "MockAiProvider",
    "get_ai_provider",
    "YouTubeAnalyticsProvider",
    "youtube_analytics_provider",
]

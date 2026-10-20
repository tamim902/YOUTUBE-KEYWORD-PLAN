"""Configuration module for YouTube Keyword Finder.

Provides environment-aware settings, default limits, filesystem paths,
and supported language/country metadata for search requests.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


# Root filesystem paths
if getattr(sys, "frozen", False):
    # Running inside a PyInstaller frozen bundle:
    # Anchor persistent data and logs directory next to the user's executable
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATABASE_PATH = DATA_DIR / "keywords.db"
LOG_FILE = LOG_DIR / "app.log"


@dataclass(frozen=True)
class AppConfig:
    """Immutable application settings and runtime defaults."""

    app_name: str = "YouTube Keyword Finder"
    app_version: str = "0.1.0"
    app_icon: str = "🔍"
    debug: bool = False

    # Filesystem paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    log_dir: Path = LOG_DIR
    database_path: Path = DATABASE_PATH
    log_file: Path = LOG_FILE

    # Request & crawl constraints
    default_max_depth: int = 2
    max_allowed_depth: int = 5
    default_request_budget: int = 50
    max_allowed_budget: int = 200
    default_max_unique_keywords: int = 50
    max_allowed_unique_keywords: int = 500
    request_delay_seconds: float = 0.3
    request_timeout_seconds: float = 6.0
    crawl_min_delay_seconds: float = 0.1
    max_retries: int = 3

    # Autocomplete Provider Settings
    autocomplete_endpoint: str = "https://suggestqueries.google.com/complete/search"
    connect_timeout_seconds: float = 3.0
    read_timeout_seconds: float = 5.0

    rate_limit_min_interval_seconds: float = 0.2
    cache_ttl_seconds: int = 86400  # 24 hours
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    # Language support (English and Bangla Unicode prioritized)
    supported_languages: Dict[str, str] = field(
        default_factory=lambda: {
            "en": "English",
            "bn": "Bangla (বাংলা)",
            "hi": "Hindi (हिन्दी)",
            "es": "Spanish (Español)",
            "ar": "Arabic (العربية)",
            "fr": "French (Français)",
            "de": "German (Deutsch)",
        }
    )

    # Country / Region filters
    supported_countries: Dict[str, str] = field(
        default_factory=lambda: {
            "US": "United States",
            "BD": "Bangladesh",
            "GB": "United Kingdom",
            "IN": "India",
            "CA": "Canada",
            "AU": "Australia",
            "DE": "Germany",
        }
    )

    def __post_init__(self) -> None:
        """Validate configuration parameters upon initialization."""
        if self.default_max_depth <= 0 or self.default_max_depth > self.max_allowed_depth:
            raise ValueError(
                f"default_max_depth must be between 1 and {self.max_allowed_depth}."
            )
        if (
            self.default_request_budget <= 0
            or self.default_request_budget > self.max_allowed_budget
        ):
            raise ValueError(
                f"default_request_budget must be between 1 and {self.max_allowed_budget}."
            )
        if self.request_delay_seconds < 0:
            raise ValueError("request_delay_seconds cannot be negative.")
        if self.request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive.")
        if self.connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive.")
        if self.read_timeout_seconds <= 0:
            raise ValueError("read_timeout_seconds must be positive.")
        if self.rate_limit_min_interval_seconds < 0:
            raise ValueError("rate_limit_min_interval_seconds cannot be negative.")
        if self.cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds cannot be negative.")
        if (
            self.default_max_unique_keywords <= 0
            or self.default_max_unique_keywords > self.max_allowed_unique_keywords
        ):
            raise ValueError(
                f"default_max_unique_keywords must be between 1 and {self.max_allowed_unique_keywords}."
            )
        if self.crawl_min_delay_seconds < 0:
            raise ValueError("crawl_min_delay_seconds cannot be negative.")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

    def ensure_directories(self) -> None:
        """Create necessary data and log directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


# Default singleton instance
config = AppConfig()

APP_NAME = config.app_name
APP_VERSION = config.app_version

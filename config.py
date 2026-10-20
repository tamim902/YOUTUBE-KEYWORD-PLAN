"""Root configuration module proxy for YouTube Keyword Finder.

Exposes the central AppConfig singleton and top-level constants.
"""

from src.config import (
    APP_NAME,
    AppConfig,
    BASE_DIR,
    DATABASE_PATH,
    DATA_DIR,
    LOG_DIR,
    LOG_FILE,
    config,
)

__all__ = [
    "AppConfig",
    "config",
    "BASE_DIR",
    "DATA_DIR",
    "LOG_DIR",
    "DATABASE_PATH",
    "LOG_FILE",
    "APP_NAME",
]

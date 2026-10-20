"""Application-wide logging configuration.

Sets up console and rotating file logging safely without duplicate handlers,
ensuring Streamlit page reloads do not spawn redundant log listeners.
"""

import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.config import LOG_DIR, LOG_FILE, config


def get_logger(name: str = "youtube_keyword_finder") -> logging.Logger:
    """Obtain or configure a logger with console and file output."""
    logger = logging.getLogger(name)

    # Avoid duplicate handlers on Streamlit reload
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if config.debug else logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Rotating, max 5MB, keep 3 backups)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        # Fallback to console only if file logging fails (e.g. read-only environment)
        console_handler.setLevel(logging.DEBUG)
        logger.warning("Failed to initialize file logger: %s", exc)

    logger.propagate = False
    return logger

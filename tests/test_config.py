"""Tests for application configuration and defaults."""

import tempfile
from pathlib import Path
from src.config import AppConfig, config


def test_default_config_values() -> None:
    """Test default values of AppConfig."""
    assert config.app_name == "YouTube Keyword Finder"
    assert config.default_max_depth == 2
    assert config.max_allowed_depth >= 5
    assert config.default_request_budget == 50
    assert config.max_allowed_budget >= 100
    assert "en" in config.supported_languages
    assert "bn" in config.supported_languages
    assert "US" in config.supported_countries
    assert "BD" in config.supported_countries


def test_ensure_directories() -> None:
    """Test that ensure_directories creates data and log paths."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        data_dir = tmp_path / "sub_data"
        log_dir = tmp_path / "sub_logs"
        cfg = AppConfig(data_dir=data_dir, log_dir=log_dir)

        assert not data_dir.exists()
        assert not log_dir.exists()

        cfg.ensure_directories()

        assert data_dir.exists()
        assert log_dir.exists()


def test_invalid_configuration_handling() -> None:
    """Test that invalid configuration values raise ValueError."""
    import pytest

    # Depth out of bounds
    with pytest.raises(ValueError, match="default_max_depth"):
        AppConfig(default_max_depth=0)

    with pytest.raises(ValueError, match="default_max_depth"):
        AppConfig(default_max_depth=10, max_allowed_depth=5)

    # Budget out of bounds
    with pytest.raises(ValueError, match="default_request_budget"):
        AppConfig(default_request_budget=0)

    with pytest.raises(ValueError, match="default_request_budget"):
        AppConfig(default_request_budget=500, max_allowed_budget=200)

    # Negative timeout or delay
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        AppConfig(request_timeout_seconds=0)

    with pytest.raises(ValueError, match="request_delay_seconds"):
        AppConfig(request_delay_seconds=-0.5)

    with pytest.raises(ValueError, match="max_retries"):
        AppConfig(max_retries=-1)


def test_startup_prerequisites() -> None:
    """Test that application bootstrap fulfills startup prerequisites."""
    from app import bootstrap_application
    success = bootstrap_application()
    assert success is True
    assert config.data_dir.exists()
    assert config.log_dir.exists()
    assert config.database_path.exists()

"""Pytest fixtures for YouTube Keyword Finder tests."""

import sys
import tempfile
from pathlib import Path
from typing import Generator
import pytest

# Ensure root directory is on Python search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.database import DatabaseManager


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Provide a temporary SQLite database file for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_keywords.db"
        yield db_path


@pytest.fixture
def test_db_manager(temp_db_path: Path) -> DatabaseManager:
    """Provide an initialized DatabaseManager using a temporary database."""
    manager = DatabaseManager(db_path=temp_db_path)
    manager.init_db()
    return manager

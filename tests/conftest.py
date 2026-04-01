from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from planner import db


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Provide a fresh in-memory-like SQLite connection per test."""
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()

# -*- coding: utf-8 -*-
"""SQLite connection helpers shared by UI, services, and API code."""
from __future__ import annotations

import sqlite3


DEFAULT_SQLITE_TIMEOUT_SECONDS = 30.0
DEFAULT_SQLITE_BUSY_TIMEOUT_MS = 30_000


def connect_sqlite(db_path: str, *, row_factory: bool = False) -> sqlite3.Connection:
    """
    Open a SQLite connection that waits for short-lived UI/service locks.

    The desktop app frequently keeps one connection open while import/template
    helpers open another. A busy timeout avoids immediate "database is locked"
    failures when the first connection is finishing a write or schema guard.
    """
    conn = sqlite3.connect(db_path, timeout=DEFAULT_SQLITE_TIMEOUT_SECONDS)
    if row_factory:
        conn.row_factory = sqlite3.Row
    try:
        conn.execute(f"PRAGMA busy_timeout = {DEFAULT_SQLITE_BUSY_TIMEOUT_MS}")
    except sqlite3.DatabaseError:
        pass
    return conn


def is_database_locked_error(exc: BaseException) -> bool:
    return isinstance(exc, sqlite3.OperationalError) and "database is locked" in str(exc).lower()

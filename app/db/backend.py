# -*- coding: utf-8 -*-
"""Database backend detection helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from sqlalchemy.engine.url import make_url

SQLITE_BACKEND = "sqlite"
POSTGRESQL_BACKEND = "postgresql"


def database_backend(database_url: str | None) -> str:
    """Return a stable backend name from a SQLAlchemy database URL."""
    raw = str(database_url or "").strip()
    if not raw:
        return SQLITE_BACKEND
    try:
        backend = make_url(raw).get_backend_name()
    except Exception:
        return "unknown"
    if backend == "postgres":
        return POSTGRESQL_BACKEND
    return backend


def is_sqlite_url(database_url: str | None) -> bool:
    return database_backend(database_url) == SQLITE_BACKEND


def is_postgresql_url(database_url: str | None) -> bool:
    return database_backend(database_url) == POSTGRESQL_BACKEND


def is_sqlite_connection(conn: Any) -> bool:
    return isinstance(conn, sqlite3.Connection)


def require_sqlite_url(database_url: str | None, *, feature: str) -> None:
    """Fail fast when a legacy sqlite3-only path is used with another backend."""
    if is_sqlite_url(database_url):
        return
    backend = database_backend(database_url)
    raise RuntimeError(
        f"{feature} su anda sqlite3 tabanli eski veri erisim yolunu kullaniyor. "
        f"Aktif veritabani backend'i '{backend}'. PostgreSQL icin SQLAlchemy "
        "repository/migration yolunu kullanin; eski SQLite dosyasina sessizce "
        "yazmak veri tutarsizligi olusturabilir."
    )

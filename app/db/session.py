# -*- coding: utf-8 -*-
"""Tkinter ve FastAPI için merkezi DB session/connection yönetimi."""

from __future__ import annotations

import contextlib
import os
import sqlite3
from typing import Iterator

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except Exception:  # pragma: no cover - SQLAlchemy kurulu degilse sqlite yolu calisir
    create_engine = None
    sessionmaker = None

from app.core.config import AppConfig, load_app_config
from app.db.schema_compat import ensure_reporting_schema
from app.db.sqlite_connection import connect_sqlite


_engine_cache: dict[str, object] = {}
_session_factory_cache: dict[str, object] = {}


def get_engine(config: AppConfig | None = None):
    cfg = config or load_app_config()
    if create_engine is None:
        raise RuntimeError("SQLAlchemy mevcut değil.")
    url = cfg.database_url
    if url not in _engine_cache:
        _engine_cache[url] = create_engine(
            url,
            connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
            future=True,
        )
    return _engine_cache[url]


def get_session_factory(config: AppConfig | None = None):
    cfg = config or load_app_config()
    if sessionmaker is None:
        raise RuntimeError("SQLAlchemy mevcut değil.")
    url = cfg.database_url
    if url not in _session_factory_cache:
        _session_factory_cache[url] = sessionmaker(bind=get_engine(cfg), autoflush=False, autocommit=False, future=True)
    return _session_factory_cache[url]


def open_sqlite_connection(db_path: str | None = None, *, row_factory: bool = True) -> sqlite3.Connection:
    cfg = load_app_config()
    path = os.path.abspath(db_path or cfg.sqlite_db_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Veritabanı bulunamadı: {path}")
    conn = connect_sqlite(path, row_factory=row_factory)
    ensure_reporting_schema(conn)
    return conn


@contextlib.contextmanager
def db_session(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Kısa ömürlü sqlite transaction context manager."""
    conn = open_sqlite_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency uyumlu sqlite connection üretir."""
    with db_session() as conn:
        yield conn


def init_database(db_path: str | None = None) -> dict[str, object]:
    with db_session(db_path) as conn:
        result = ensure_reporting_schema(conn)
        return {"ok": True, "schema": result, "db_path": db_path or load_app_config().sqlite_db_path}


def close_database() -> None:
    _engine_cache.clear()
    _session_factory_cache.clear()

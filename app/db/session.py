# -*- coding: utf-8 -*-
"""Tkinter ve FastAPI için merkezi DB session/connection yönetimi.

PostgreSQL ve SQLite destekler. SQLAlchemy session tabanlı erişim sağlar.
"""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import AppConfig, load_app_config, resolve_sqlite_db_path
from app.db.backend import SQLITE_BACKEND, is_sqlite_url, require_sqlite_url
from app.db.database import Base, get_engine
from app.db.database import get_session as _get_session


def _resolve_sqlite_path(db_path: str | None = None, config: AppConfig | None = None) -> str:
    cfg = config or load_app_config()
    return str(resolve_sqlite_db_path(db_path or cfg.sqlite_db_path))


def _sqlite_url_for_path(db_path: str) -> str:
    return f"sqlite:///{Path(db_path).as_posix()}"


def open_sqlite_connection(db_path: str | None = None, *, row_factory: bool = True):
    """Legacy uyumluluk: Raw DBAPI connection döndürür.

    PostgreSQL aktifken ve açık bir SQLite yolu verilmemişken fail-fast davranır.
    Çağıran kod close() yapmakla yükümlüdür.
    """
    cfg = load_app_config()
    if db_path is None and not is_sqlite_url(cfg.database_url):
        require_sqlite_url(cfg.database_url, feature="open_sqlite_connection")
    conn = sqlite3.connect(_resolve_sqlite_path(db_path, cfg))
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


@contextlib.contextmanager
def db_session(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Kısa ömürlü legacy SQLite transaction context manager."""
    conn = open_sqlite_connection(db_path, row_factory=True)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency uyumlu SQLAlchemy session üretir."""
    session = _get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(db_path: str | None = None) -> dict[str, object]:
    """Veritabanı şemasını oluşturur/günceller."""
    cfg = load_app_config()
    schema_result = {}

    if db_path is not None or is_sqlite_url(cfg.database_url):
        resolved_path = _resolve_sqlite_path(db_path, cfg)
        Path(resolved_path).parent.mkdir(parents=True, exist_ok=True)
        database_url = _sqlite_url_for_path(resolved_path)
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        try:
            Base.metadata.create_all(bind=engine)
            from app.db.schema_compat import ensure_reporting_schema

            conn = sqlite3.connect(resolved_path)
            try:
                schema_result = ensure_reporting_schema(conn)
                conn.commit()
            finally:
                conn.close()
        finally:
            engine.dispose()

        return {
            "ok": True,
            "schema": schema_result,
            "db_path": resolved_path,
            "database_url": database_url,
            "database_backend": SQLITE_BACKEND,
        }

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    return {
        "ok": True,
        "schema": schema_result,
        "db_path": None,
        "database_url": cfg.database_url,
        "database_backend": cfg.db_backend,
    }


def close_database() -> None:
    """Engine'i temizler."""
    from app.db.database import dispose_session
    dispose_session()


def get_alembic_head(config_path: str = "alembic.ini") -> str | None:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(Config(config_path))
        return script.get_current_head()
    except Exception:
        return None


def stamp_database_head(engine_obj: object, config_path: str = "alembic.ini") -> str | None:
    head = get_alembic_head(config_path=config_path)
    if not head:
        return None
    with engine_obj.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"
        )
        conn.exec_driver_sql("DELETE FROM alembic_version")
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:version)"), {"version": head})
    return head

# -*- coding: utf-8 -*-
"""Tkinter ve FastAPI için merkezi DB session/connection yönetimi.

PostgreSQL ve SQLite destekler. SQLAlchemy session tabanlı erişim sağlar.
"""

from __future__ import annotations

import contextlib
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import AppConfig, load_app_config
from app.db.backend import is_sqlite_url
from app.db.database import get_engine, get_session as _get_session, Base


def open_sqlite_connection(db_path: str | None = None, *, row_factory: bool = True):
    """Legacy uyumluluk: Raw DBAPI connection döndürür.

    PostgreSQL backend'inde db_path yoksayılır.
    Çağıran kod close() yapmakla yükümlüdür.
    """
    engine = get_engine()
    return engine.raw_connection()


@contextlib.contextmanager
def db_session(db_path: str | None = None) -> Iterator[Session]:
    """Kısa ömürlü SQLAlchemy transaction context manager."""
    session = _get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency uyumlu session üretir."""
    with db_session() as session:
        yield session


def init_database(db_path: str | None = None) -> dict[str, object]:
    """Veritabanı şemasını oluşturur/günceller."""
    cfg = load_app_config()
    engine = get_engine()

    # ORM modellerinden tabloları oluştur
    Base.metadata.create_all(bind=engine)

    # Schema uyumluluğu — sadece SQLite için eski schema_compat çalıştır
    schema_result = {}
    if is_sqlite_url(cfg.database_url):
        try:
            from app.db.schema_compat import ensure_reporting_schema
            conn = engine.raw_connection()
            try:
                schema_result = ensure_reporting_schema(conn)
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            schema_result = {"error": str(exc)}

    return {
        "ok": True,
        "schema": schema_result,
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
        conn.exec_driver_sql(
            "INSERT INTO alembic_version (version_num) VALUES (%s)", (head,)
        )
    return head

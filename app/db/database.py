# -*- coding: utf-8 -*-
# =============================================================================
# app/db/database.py — SQLAlchemy Oturum Yonetimi
# =============================================================================
# ScopedSession ile thread-safe veritabani erisimi saglar.
# config.json'dan DB yolunu okur; yol degisirse engine otomatik yenilenir.
# ORM modelleri (models.py) icin Base tanimini icerir.
#
# Kullanim:
#   from app.db.database import get_session
#   session = get_session()
#   ...
#   session.close()
# =============================================================================
import os
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from app.core.settings import load_settings
from app.db.schema_compat import ensure_reporting_schema

_lock = threading.Lock()
_current_url: str = ""


def _load_db_url():
    settings = load_settings(config_path="config.json")
    return settings.db_url


DATABASE_URL = _load_db_url()
_current_url = DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
SessionLocal = scoped_session(SessionFactory)
Base = declarative_base()


def _refresh_engine_if_needed():
    """config.json degistiyse engine'i yeniden olusturur."""
    global engine, SessionFactory, SessionLocal, DATABASE_URL, _current_url

    new_url = _load_db_url()
    if new_url == _current_url:
        return

    with _lock:
        if new_url == _current_url:
            return
        try:
            SessionLocal.remove()
            engine.dispose()
        except Exception:
            pass

        DATABASE_URL = new_url
        _current_url = new_url
        engine = create_engine(
            new_url,
            connect_args={"check_same_thread": False} if new_url.startswith("sqlite") else {},
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
        SessionLocal = scoped_session(SessionFactory)


def get_session():
    _refresh_engine_if_needed()
    return SessionLocal()


def dispose_session():
    SessionLocal.remove()


def ensure_runtime_sqlite_schema(sqlite_path: str) -> dict:
    """
    Uygulama acilisinda kritik sqlite sema uyumlulugunu garanti eder.
    """
    if not sqlite_path or not os.path.exists(sqlite_path):
        return {"ok": False, "reason": "db_not_found"}
    try:
        import sqlite3

        conn = sqlite3.connect(sqlite_path)
        try:
            result = ensure_reporting_schema(conn)
            return {"ok": True, "result": result}
        finally:
            conn.close()
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}

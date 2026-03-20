# app/db/database.py
# ScopedSession ile bağlantı kopması önleme ve thread-safe kullanım
import json
import os
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

_lock = threading.Lock()
_current_url: str = ""


def _load_db_url():
    cfg = {"db_url": "sqlite:///./adil_secimli.db"}
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if "db_path" in data:
                cfg["db_url"] = f"sqlite:///{os.path.abspath(data['db_path'])}"
            elif "db_url" in data:
                cfg["db_url"] = data["db_url"]
        except Exception:
            pass
    return cfg["db_url"]


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

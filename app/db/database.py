# -*- coding: utf-8 -*-
# =============================================================================
# app/db/database.py — SQLAlchemy Oturum Yonetimi
# =============================================================================
# ScopedSession ile thread-safe veritabani erisimi saglar.
# PostgreSQL ve SQLite destekler.
# ORM modelleri (models.py) icin Base tanimini icerir.
#
# Kullanim:
#   from app.db.database import get_session
#   session = get_session()
#   ...
#   session.close()
# =============================================================================
import threading

<<<<<<< HEAD
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
=======
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
>>>>>>> f064caebbf2bfd6fac014f86504bd92f9d64e647

_lock = threading.Lock()
_current_url: str = ""

Base = declarative_base()

# Engine ve session nesneleri lazy olarak oluşturulur
engine = None
SessionFactory = None
SessionLocal = None


def _load_db_url():
    from app.core.config import load_app_config
    return load_app_config().database_url


def _build_engine(url: str):
    """Verilen URL'ye uygun SQLAlchemy engine oluşturur."""
    connect_args = {}
    kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # PostgreSQL pool ayarları
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    return create_engine(url, connect_args=connect_args, **kwargs)


def _fallback_sqlite_url() -> str:
    from app.core.config import load_app_config

    cfg = load_app_config()
    return f"sqlite:///{cfg.sqlite_db_path}"


def _ensure_engine():
    """Engine oluştur veya URL değiştiyse yenile."""
    global engine, SessionFactory, SessionLocal, _current_url

    url = _load_db_url()
    if engine is not None and url == _current_url:
        return

    with _lock:
        if engine is not None and url == _current_url:
            return
        # Eski engine varsa kapat
        if engine is not None:
            try:
                if SessionLocal is not None:
                    SessionLocal.remove()
                engine.dispose()
            except Exception:
                pass

        _current_url = url
        try:
            engine = _build_engine(url)
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            if not url.startswith("sqlite"):
                # PostgreSQL başarısız olursa SQLite fallback yap
                fallback_url = _fallback_sqlite_url()
                _current_url = fallback_url
                try:
                    engine = _build_engine(fallback_url)
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                except Exception as fallback_error:
                    raise RuntimeError(
                        f"Ana veritabanı '{url}' bağlanılamadı ve SQLite fallback "
                        f"'{fallback_url}' da başarısız: {fallback_error}"
                    )
            else:
                # SQLite URL'si önceden belirtildi ama bağlantı başarısız
                raise RuntimeError(
                    f"SQLite veritabanı bağlantısı başarısız. Dosya yolu: {url}\n"
                    f"Hata: {e}"
                )
        SessionFactory = sessionmaker(
            bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
        )
        SessionLocal = scoped_session(SessionFactory)


def get_engine():
    """Aktif engine'i döndürür."""
    _ensure_engine()
    return engine


def get_session():
    """Thread-safe session döndürür."""
    _ensure_engine()
    return SessionLocal()


def dispose_session():
    """Mevcut thread'in session'ını temizler."""
    if SessionLocal is not None:
        SessionLocal.remove()


def create_all_tables():
    """ORM modellerinden tüm tabloları oluşturur (PostgreSQL migration için)."""
    _ensure_engine()
    Base.metadata.create_all(bind=engine)

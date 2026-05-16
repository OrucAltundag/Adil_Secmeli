# -*- coding: utf-8 -*-
"""SQLite/PostgreSQL connection helpers shared by UI, services, and API code.

Bu modül geriye uyumluluk için korunmuştur. Yeni kod SQLAlchemy session
kullanmalıdır (app.db.database veya app.db.session modülleri aracılığıyla).
"""
from __future__ import annotations

from sqlalchemy import text
from app.db.database import get_engine


def connect_sqlite(db_path: str = "", *, row_factory: bool = False):
    """
    Legacy uyumluluk: Raw DBAPI connection döndürür.

    PostgreSQL backend'inde db_path yoksayılır ve engine'den
    raw connection alınır. Çağıran kod close() yapmakla yükümlüdür.
    """
    engine = get_engine()
    conn = engine.raw_connection()
    return conn


def is_database_locked_error(exc: BaseException) -> bool:
    """Veritabanı kilitli hatası mı kontrol eder."""
    err_msg = str(exc).lower()
    return "database is locked" in err_msg or "lock" in err_msg

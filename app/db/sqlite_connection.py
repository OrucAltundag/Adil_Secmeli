# -*- coding: utf-8 -*-
"""SQLite/PostgreSQL connection helpers shared by UI, services, and API code.

Bu modül geriye uyumluluk için korunmuştur. Yeni kod SQLAlchemy session
kullanmalıdır (app.db.database veya app.db.session modülleri aracılığıyla).
"""
from __future__ import annotations

from app.db.session import open_sqlite_connection


def connect_sqlite(db_path: str = "", *, row_factory: bool = False):
    """
    Legacy uyumluluk: Raw DBAPI connection döndürür.

    Açık bir db_path verilirse o SQLite dosyasına bağlanır; verilmezse aktif
    SQLite config yolunu kullanır. PostgreSQL aktifken db_path yoksa fail-fast
    davranır. Çağıran kod close() yapmakla yükümlüdür.
    """
    return open_sqlite_connection(db_path or None, row_factory=row_factory)


def is_database_locked_error(exc: BaseException) -> bool:
    """Veritabanı kilitli hatası mı kontrol eder."""
    err_msg = str(exc).lower()
    return "database is locked" in err_msg or "lock" in err_msg

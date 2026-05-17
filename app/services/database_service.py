# -*- coding: utf-8 -*-
"""Sağlık kontrolleri ve yeni kod için güvenli DB erişim servisi.

Amaç: UI/health katmanının doğrudan ``sqlite3`` kullanmaması. Bağlantılar
context manager ile açılıp her durumda kapatılır. Mevcut
``app.db.session`` altyapısını sarmalar (adapter); legacy kodu kırmaz.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator

from app.core.config import AppConfig, load_app_config, resolve_sqlite_db_path
from app.db.backend import is_sqlite_url
from app.db.session import open_sqlite_connection
from app.repositories.sqlite_repository import SqliteRepository


class DatabaseService:
    """Kısa ömürlü, güvenli kapatılan SQLite erişimi sağlar."""

    def __init__(self, db_path: str | None = None, config: AppConfig | None = None):
        self.config = config or load_app_config()
        self.db_path = str(resolve_sqlite_db_path(db_path or self.config.sqlite_db_path))

    def is_sqlite(self) -> bool:
        """Aktif backend SQLite mi?"""

        return is_sqlite_url(self.config.database_url) or bool(self.db_path)

    @contextmanager
    def connection(self, *, row_factory: bool = True) -> Iterator[sqlite3.Connection]:
        """Salt-okunur amaçlı kısa ömürlü bağlantı.

        İş bittiğinde bağlantı kesin kapatılır; hata olsa bile rollback yapılır.
        """

        conn = open_sqlite_connection(self.db_path or None, row_factory=row_factory)
        try:
            yield conn
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @contextmanager
    def repository(self) -> Iterator[SqliteRepository]:
        """:class:`SqliteRepository` örneği ile context manager."""

        with self.connection() as conn:
            yield SqliteRepository(conn)

    def measure_connection_ms(self) -> float:
        """Bağlantı kurma + basit ping süresini ms cinsinden ölçer."""

        start = time.perf_counter()
        with self.connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return (time.perf_counter() - start) * 1000.0


def get_database_service(
    db_path: str | None = None, config: AppConfig | None = None
) -> DatabaseService:
    return DatabaseService(db_path=db_path, config=config)

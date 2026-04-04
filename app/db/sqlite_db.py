# -*- coding: utf-8 -*-
# =============================================================================
# app/db/sqlite_db.py — UI Tarafli SQLite Veritabani Erisimi
# =============================================================================
# Tkinter UI katmani tarafindan kullanilan hafif sqlite3 wrapper.
# SQLAlchemy yerine dogrudan sqlite3 kullanir (basit sorgular icin).
# connect(), tables(), head(), read_df(), run_sql() metodlari sunar.
# =============================================================================
from __future__ import annotations

import os
import sqlite3
from typing import Any, Optional, Sequence

import pandas as pd
from app.db.schema_compat import ensure_reporting_schema


class Database:
    """
    UI tarafı için sqlite3 tabanlı küçük DB wrapper.
    - connect()
    - tables()
    - head()
    - read_df()
    - run_sql()

    Not: run_sql SELECT ise (cols, rows) döner, değilse commit yapar.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.conn: Optional[sqlite3.Connection] = None
        if db_path:
            self.connect(db_path)

    def connect(self, db_path: str) -> None:
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Veritabanı bulunamadı: {db_path}")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        ensure_reporting_schema(self.conn)
        self._migrate_ders_kriterleri_anket()

    def _migrate_ders_kriterleri_anket(self) -> None:
        """ders_kriterleri tablosuna anket ve import metadata sütunları ekler (yoksa)."""
        if not self.conn:
            return
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ders_kriterleri'")
            if not cur.fetchone():
                return
            cur.execute("PRAGMA table_info(ders_kriterleri)")
            cols = {row[1] for row in cur.fetchall()}
            columns = [
                ("anket_katilimci", "INTEGER DEFAULT 0"),
                ("anket_dersi_secen", "INTEGER DEFAULT 0"),
                ("anket_veri_kaynagi", "TEXT DEFAULT 'manual'"),
                ("anket_manual_locked", "INTEGER NOT NULL DEFAULT 0"),
                ("anket_import_id", "INTEGER"),
                ("anket_imported_at", "TEXT"),
            ]
            for col, ddl in columns:
                if col not in cols:
                    cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col} {ddl}")
            self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            print(f"[DB Migration] ders_kriterleri anket: {e}")

    def ensure(self) -> None:
        if not self.conn:
            raise RuntimeError("Veritabanı bağlantısı yok.")

    def tables(self) -> list[str]:
        self.ensure()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name;"
        )
        return [r[0] for r in cur.fetchall()]

    def head(self, table: str, limit: int = 1000) -> tuple[list[str], list[sqlite3.Row]]:
        self.ensure()
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {table} LIMIT {int(limit)};")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return cols, rows

    def read_df(self, query: str, params=None):
        self.ensure()
        if params is None:
            return pd.read_sql_query(query, self.conn)
        return pd.read_sql_query(query, self.conn, params=params)

    def run_sql(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None
    ) -> tuple[list[str], list[Any]]:
        """
        SELECT => (cols, rows)
        Diğer => commit ve ([], [])
        """
        self.ensure()
        cur = self.conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)

        if query.strip().lower().startswith("select"):
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return cols, rows

        self.conn.commit()
        return [], []


# -*- coding: utf-8 -*-
"""
Runtime schema compatibility helpers.

Bu modul, legacy SQLite dosyalariyla calisirken kritik kolon/index
eksiklerini uygulama acilisinda tamamlar. Alembic migration hattini
destekler, ancak migration calismamis ortamlarda da geriye uyumluluk
saglar.
"""

from __future__ import annotations

import sqlite3

DEFAULT_HAVUZ_DONEM = "Guz"
DEFAULT_SKOR_DONEM = "Guz"


def normalize_term(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if value.startswith("b"):
        return "Bahar"
    return DEFAULT_HAVUZ_DONEM


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return bool(cur.fetchone())


def _column_names(cur: sqlite3.Cursor, table_name: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(row[1]) for row in cur.fetchall()}


def _index_names(cur: sqlite3.Cursor, table_name: str) -> set[str]:
    cur.execute(f"PRAGMA index_list({table_name})")
    names = set()
    for row in cur.fetchall():
        # row tuple: seq, name, unique, origin, partial
        if row and len(row) > 1 and row[1]:
            names.add(str(row[1]))
    return names


def ensure_havuz_semester_schema(conn: sqlite3.Connection) -> dict[str, int]:
    """
    havuz tablosunu donem-aware hale getirir.

    Uygulananlar:
    - donem kolonu yoksa eklenir
    - bos/null donem degerleri normalize edilir
    - (ders_id, fakulte_id, yil, donem) tekilligi saglanir
    - fakulte+yil+donem icin sorgu indeksi eklenir
    """
    cur = conn.cursor()
    changed = {
        "column_added": 0,
        "rows_normalized": 0,
        "duplicates_removed": 0,
        "indexes_created": 0,
    }

    if not _table_exists(cur, "havuz"):
        return changed

    cols = _column_names(cur, "havuz")
    if "donem" not in cols:
        cur.execute("ALTER TABLE havuz ADD COLUMN donem TEXT NOT NULL DEFAULT 'Guz'")
        changed["column_added"] = 1
        cols.add("donem")

    cur.execute(
        """
        UPDATE havuz
        SET donem = CASE
            WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = 'b' THEN 'Bahar'
            ELSE 'Guz'
        END
        WHERE donem IS NULL
           OR TRIM(COALESCE(donem, '')) = ''
           OR LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) NOT IN ('g', 'b')
        """
    )
    changed["rows_normalized"] = int(cur.rowcount or 0)

    # Unique index olusturmadan once duplicate satirlari temizle.
    cur.execute(
        """
        DELETE FROM havuz
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM havuz
            GROUP BY ders_id, fakulte_id, yil, donem
        )
        """
    )
    changed["duplicates_removed"] = int(cur.rowcount or 0)

    idx_names = _index_names(cur, "havuz")
    if "uq_havuz_ders_fac_yil_donem" not in idx_names:
        cur.execute(
            """
            CREATE UNIQUE INDEX uq_havuz_ders_fac_yil_donem
            ON havuz (ders_id, fakulte_id, yil, donem)
            """
        )
        changed["indexes_created"] += 1

    if "ix_havuz_fakulte_yil_donem" not in idx_names:
        cur.execute(
            """
            CREATE INDEX ix_havuz_fakulte_yil_donem
            ON havuz (fakulte_id, yil, donem)
            """
        )
        changed["indexes_created"] += 1

    conn.commit()
    return changed


def ensure_skor_schema(conn: sqlite3.Connection) -> dict[str, int]:
    """
    skor tablosundaki kritik kolon/index uyumlulugunu saglar.

    Hedef:
    - skor tablosu yoksa olustur
    - eksik kolonlari migration-safe sekilde ekle (donem, hesap_tarih, skor_top)
    - donem normalize et
    - tekillik indexini olustur
    """
    cur = conn.cursor()
    changed = {
        "table_created": 0,
        "columns_added": 0,
        "rows_normalized": 0,
        "indexes_created": 0,
    }

    if not _table_exists(cur, "skor"):
        cur.execute(
            """
            CREATE TABLE skor (
                skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ders_id INTEGER NOT NULL,
                akademik_yil INTEGER NOT NULL,
                donem TEXT NOT NULL DEFAULT 'Guz',
                b_norm REAL,
                p_norm REAL,
                a_norm REAL,
                g_norm REAL,
                skor_top REAL,
                hesap_tarih TEXT
            )
            """
        )
        changed["table_created"] = 1

    cols = _column_names(cur, "skor")

    if "donem" not in cols:
        cur.execute("ALTER TABLE skor ADD COLUMN donem TEXT NOT NULL DEFAULT 'Guz'")
        cols.add("donem")
        changed["columns_added"] += 1

    if "hesap_tarih" not in cols:
        cur.execute("ALTER TABLE skor ADD COLUMN hesap_tarih TEXT")
        cols.add("hesap_tarih")
        changed["columns_added"] += 1

    if "skor_top" not in cols:
        cur.execute("ALTER TABLE skor ADD COLUMN skor_top REAL")
        cols.add("skor_top")
        changed["columns_added"] += 1

    cur.execute(
        """
        UPDATE skor
        SET donem = CASE
            WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = 'b' THEN 'Bahar'
            ELSE 'Guz'
        END
        """
    )
    changed["rows_normalized"] = int(cur.rowcount or 0)

    idx_names = _index_names(cur, "skor")
    if "uq_skor_ders_year_term" not in idx_names:
        cur.execute(
            """
            DELETE FROM skor
            WHERE skor_id NOT IN (
                SELECT MIN(skor_id)
                FROM skor
                GROUP BY ders_id, akademik_yil, donem
            )
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX uq_skor_ders_year_term
            ON skor (ders_id, akademik_yil, donem)
            """
        )
        changed["indexes_created"] += 1

    conn.commit()
    return changed


def ensure_reporting_schema(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """
    Raporlama icin gereken tum kritik tablolari synchronize eder.
    """
    return {
        "havuz": ensure_havuz_semester_schema(conn),
        "skor": ensure_skor_schema(conn),
    }

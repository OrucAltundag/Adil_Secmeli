# -*- coding: utf-8 -*-
"""
Runtime schema compatibility helpers.

Bu modul, legacy SQLite dosyalariyla calisirken kritik kolon/index
eksiklerini uygulama acilisinda tamamlar. Alembic migration hattini
destekler, ancak migration calismamis ortamlarda da geriye uyumluluk
saglar.
"""

from __future__ import annotations

import re
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


def _table_sql(cur: sqlite3.Cursor, table_name: str) -> str:
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    row = cur.fetchone()
    return str(row[0] or "") if row else ""


def _criteria_term_case_sql(column_name: str) -> str:
    return (
        f"CASE "
        f"WHEN LOWER(SUBSTR(TRIM(COALESCE({column_name}, '')), 1, 1)) = 'b' THEN 'Bahar' "
        f"ELSE 'Güz' END"
    )


def _create_ders_kriterleri_table(cur: sqlite3.Cursor, table_name: str = "ders_kriterleri") -> None:
    cur.execute(
        f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            donem TEXT NOT NULL DEFAULT 'Güz',
            toplam_ogrenci INTEGER DEFAULT 0,
            gecen_ogrenci INTEGER DEFAULT 0,
            basari_ortalamasi REAL DEFAULT 0.0,
            kontenjan INTEGER DEFAULT 0,
            kayitli_ogrenci INTEGER DEFAULT 0,
            anket_katilimci INTEGER DEFAULT 0,
            anket_dersi_secen INTEGER DEFAULT 0,
            anket_veri_kaynagi TEXT DEFAULT 'manual',
            anket_manual_locked INTEGER NOT NULL DEFAULT 0,
            anket_import_id INTEGER,
            anket_imported_at TEXT,
            criteria_import_id INTEGER,
            criteria_veri_kaynagi TEXT DEFAULT 'manual',
            criteria_manual_override INTEGER NOT NULL DEFAULT 0,
            criteria_updated_at TEXT,
            UNIQUE(ders_id, yil, donem)
        )
        """
    )


def _needs_ders_kriterleri_rebuild(cur: sqlite3.Cursor) -> bool:
    if not _table_exists(cur, "ders_kriterleri"):
        return False
    canonical_sql = re.sub(r"\s+", "", _table_sql(cur, "ders_kriterleri").lower())
    return "unique(ders_id,yil,donem)" not in canonical_sql


def _rebuild_ders_kriterleri_table(cur: sqlite3.Cursor) -> None:
    cols = _column_names(cur, "ders_kriterleri")
    _create_ders_kriterleri_table(cur, "ders_kriterleri__new")

    def select_expr(column_name: str, fallback_sql: str) -> str:
        return column_name if column_name in cols else fallback_sql

    cur.execute(
        f"""
        INSERT INTO ders_kriterleri__new (
            id,
            ders_id,
            yil,
            donem,
            toplam_ogrenci,
            gecen_ogrenci,
            basari_ortalamasi,
            kontenjan,
            kayitli_ogrenci,
            anket_katilimci,
            anket_dersi_secen,
            anket_veri_kaynagi,
            anket_manual_locked,
            anket_import_id,
            anket_imported_at,
            criteria_import_id,
            criteria_veri_kaynagi,
            criteria_manual_override,
            criteria_updated_at
        )
        SELECT
            old.id,
            old.ders_id,
            old.yil,
            {_criteria_term_case_sql("old.donem" if "donem" in cols else "''")} AS donem,
            {select_expr("toplam_ogrenci", "0")},
            {select_expr("gecen_ogrenci", "0")},
            {select_expr("basari_ortalamasi", "0.0")},
            {select_expr("kontenjan", "0")},
            {select_expr("kayitli_ogrenci", "0")},
            {select_expr("anket_katilimci", "0")},
            {select_expr("anket_dersi_secen", "0")},
            COALESCE({select_expr("anket_veri_kaynagi", "'manual'")}, 'manual'),
            COALESCE({select_expr("anket_manual_locked", "0")}, 0),
            {select_expr("anket_import_id", "NULL")},
            {select_expr("anket_imported_at", "NULL")},
            {select_expr("criteria_import_id", "NULL")},
            COALESCE({select_expr("criteria_veri_kaynagi", "'manual'")}, 'manual'),
            COALESCE({select_expr("criteria_manual_override", "0")}, 0),
            {select_expr("criteria_updated_at", "NULL")}
        FROM ders_kriterleri AS old
        JOIN (
            SELECT
                MAX(id) AS keep_id
            FROM ders_kriterleri
            GROUP BY
                ders_id,
                yil,
                {_criteria_term_case_sql("donem" if "donem" in cols else "''")}
        ) AS keep
            ON keep.keep_id = old.id
        """
    )
    cur.execute("DROP TABLE ders_kriterleri")
    cur.execute("ALTER TABLE ders_kriterleri__new RENAME TO ders_kriterleri")


def ensure_criteria_import_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """
    Kriter belge import semasini hazirlar.

    Hedef:
    - ders_kriterleri tablosunu donem-aware ve import izli hale getirmek
    - criteria_import / criteria_import_rows tablolarini olusturmak
    - raporlama ve aktif belge sorgulari icin indeksleri eklemek
    """
    cur = conn.cursor()
    changed = {
        "tables_created": 0,
        "columns_added": 0,
        "tables_rebuilt": 0,
        "indexes_created": 0,
    }

    if not _table_exists(cur, "ders_kriterleri"):
        _create_ders_kriterleri_table(cur)
        changed["tables_created"] += 1
    elif _needs_ders_kriterleri_rebuild(cur):
        _rebuild_ders_kriterleri_table(cur)
        changed["tables_rebuilt"] += 1

    if _table_exists(cur, "ders_kriterleri"):
        cols = _column_names(cur, "ders_kriterleri")
        criteria_columns = [
            ("criteria_import_id", "INTEGER"),
            ("criteria_veri_kaynagi", "TEXT DEFAULT 'manual'"),
            ("criteria_manual_override", "INTEGER NOT NULL DEFAULT 0"),
            ("criteria_updated_at", "TEXT"),
        ]
        for col_name, ddl in criteria_columns:
            if col_name not in cols:
                cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col_name} {ddl}")
                cols.add(col_name)
                changed["columns_added"] += 1

        cur.execute(
            f"""
            UPDATE ders_kriterleri
            SET donem = {_criteria_term_case_sql('donem')},
                criteria_veri_kaynagi = CASE
                    WHEN COALESCE(TRIM(criteria_veri_kaynagi), '') = '' THEN 'manual'
                    ELSE criteria_veri_kaynagi
                END,
                criteria_manual_override = CASE
                    WHEN criteria_manual_override IS NULL THEN 0
                    ELSE criteria_manual_override
                END
            """
        )

    if not _table_exists(cur, "criteria_import"):
        cur.execute(
            """
            CREATE TABLE criteria_import (
                import_id INTEGER PRIMARY KEY AUTOINCREMENT,
                fakulte_id INTEGER NOT NULL,
                bolum_id INTEGER,
                yil INTEGER NOT NULL,
                donem TEXT NOT NULL DEFAULT 'Güz',
                source_filename TEXT,
                template_version TEXT,
                notes TEXT,
                imported_at TEXT,
                status TEXT NOT NULL DEFAULT 'applied',
                version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_import_rows"):
        cur.execute(
            """
            CREATE TABLE criteria_import_rows (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER NOT NULL,
                row_no INTEGER NOT NULL,
                ders_kodu TEXT,
                ders_adi TEXT,
                toplam_ogrenci INTEGER NOT NULL DEFAULT 0,
                gecen_ogrenci INTEGER NOT NULL DEFAULT 0,
                basari_ortalamasi REAL NOT NULL DEFAULT 0.0,
                kontenjan INTEGER NOT NULL DEFAULT 0,
                kayitli_ogrenci INTEGER NOT NULL DEFAULT 0,
                matched_ders_id INTEGER,
                match_method TEXT,
                row_status TEXT NOT NULL DEFAULT 'matched',
                error_message TEXT,
                raw_fakulte TEXT,
                raw_bolum TEXT,
                raw_yil INTEGER,
                raw_donem TEXT
            )
            """
        )
        changed["tables_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ders_kriterleri_scope_term
        ON ders_kriterleri (yil, donem, ders_id)
        """
    )
    changed["indexes_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ders_kriterleri_criteria_import
        ON ders_kriterleri (criteria_import_id, yil, donem)
        """
    )
    changed["indexes_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_import_scope
        ON criteria_import (fakulte_id, bolum_id, yil, donem, status, version)
        """
    )
    changed["indexes_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_import_rows_import
        ON criteria_import_rows (import_id, row_status)
        """
    )
    changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_ders_code_schema(conn: sqlite3.Connection) -> dict[str, int]:
    """
    Legacy ders tablolarinda eksik ders kodu kolonunu tamamlar.

    Eski SQLite dosyalarinda `ders.kod` kolonu olmayabiliyor. Uygulamanin
    farkli yerlerinde bu kolon okundugu icin en azindan NULL/blank olacak
    sekilde kolonun varligini garanti ederiz.
    """
    cur = conn.cursor()
    changed = {
        "columns_added": 0,
    }

    if not _table_exists(cur, "ders"):
        return changed

    cols = _column_names(cur, "ders")
    if "kod" not in cols:
        cur.execute("ALTER TABLE ders ADD COLUMN kod TEXT")
        changed["columns_added"] += 1

    conn.commit()
    return changed


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


def ensure_survey_import_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """
    Fakulte+yil bazli anket import semasini hazirlar.

    Hedef:
    - ders_kriterleri uzerinde anket metadata kolonlarini eklemek
    - survey_import / survey_import_rows tablolarini olusturmak
    - replace ve raporlama icin gerekli indexleri eklemek
    """
    cur = conn.cursor()
    changed = {
        "tables_created": 0,
        "columns_added": 0,
        "indexes_created": 0,
    }

    if _table_exists(cur, "ders_kriterleri"):
        cols = _column_names(cur, "ders_kriterleri")
        survey_columns = [
            ("anket_veri_kaynagi", "TEXT DEFAULT 'manual'"),
            ("anket_manual_locked", "INTEGER NOT NULL DEFAULT 0"),
            ("anket_import_id", "INTEGER"),
            ("anket_imported_at", "TEXT"),
        ]
        for col_name, ddl in survey_columns:
            if col_name not in cols:
                cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col_name} {ddl}")
                cols.add(col_name)
                changed["columns_added"] += 1

        cur.execute(
            """
            UPDATE ders_kriterleri
            SET anket_veri_kaynagi = CASE
                    WHEN COALESCE(TRIM(anket_veri_kaynagi), '') = '' THEN 'manual'
                    ELSE anket_veri_kaynagi
                END,
                anket_manual_locked = CASE
                    WHEN anket_manual_locked IS NULL THEN 0
                    ELSE anket_manual_locked
                END
            """
        )

    if not _table_exists(cur, "survey_import"):
        cur.execute(
            """
            CREATE TABLE survey_import (
                import_id INTEGER PRIMARY KEY AUTOINCREMENT,
                fakulte_id INTEGER NOT NULL,
                yil INTEGER NOT NULL,
                total_participants INTEGER NOT NULL DEFAULT 0,
                matched_course_count INTEGER NOT NULL DEFAULT 0,
                unmatched_row_count INTEGER NOT NULL DEFAULT 0,
                source_filename TEXT,
                template_version TEXT,
                notes TEXT,
                imported_at TEXT,
                status TEXT NOT NULL DEFAULT 'applied',
                UNIQUE(fakulte_id, yil)
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "survey_import_rows"):
        cur.execute(
            """
            CREATE TABLE survey_import_rows (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER NOT NULL,
                row_no INTEGER NOT NULL,
                ders_kodu TEXT,
                ders_adi TEXT,
                tercih_sayisi INTEGER NOT NULL DEFAULT 0,
                aciklama TEXT,
                matched_ders_id INTEGER,
                match_method TEXT,
                row_status TEXT NOT NULL DEFAULT 'matched',
                error_message TEXT,
                raw_faculte TEXT,
                raw_yil INTEGER
            )
            """
        )
        changed["tables_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_survey_import_scope
        ON survey_import (fakulte_id, yil)
        """
    )
    changed["indexes_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_survey_import_rows_import
        ON survey_import_rows (import_id, row_status)
        """
    )
    changed["indexes_created"] += 1

    if _table_exists(cur, "ders_kriterleri"):
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_ders_kriterleri_survey_import
            ON ders_kriterleri (yil, anket_import_id, anket_manual_locked)
            """
        )
        changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_reporting_schema(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """
    Raporlama icin gereken tum kritik tablolari synchronize eder.
    """
    result = {
        "ders": ensure_ders_code_schema(conn),
        "havuz": ensure_havuz_semester_schema(conn),
        "skor": ensure_skor_schema(conn),
        "criteria": ensure_criteria_import_schema(conn),
        "survey": ensure_survey_import_schema(conn),
    }
    try:
        from app.services.yearly_workflow import ensure_yearly_workflow_schema

        result["workflow"] = ensure_yearly_workflow_schema(conn)  # type: ignore[assignment]
    except Exception:
        # Workflow semasi kritik raporlama akisini bloklamasin.
        result["workflow"] = {
            "tables_created": 0,
            "indexes_created": 0,
        }
    return result

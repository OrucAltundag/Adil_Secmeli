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
from datetime import datetime, timezone
from typing import Any

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


def _ensure_columns(cur: sqlite3.Cursor, table_name: str, columns: list[tuple[str, str]]) -> int:
    if not _table_exists(cur, table_name):
        return 0
    existing = _column_names(cur, table_name)
    added = 0
    for column_name, column_type in columns:
        if column_name not in existing:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            existing.add(column_name)
            added += 1
    return added


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _schema_mutation_allowed() -> bool:
    try:
        from app.core.config import load_app_config
        from app.core.database_policy import runtime_schema_mutation_allowed

        return runtime_schema_mutation_allowed(load_app_config())
    except Exception:
        return True


def _log_schema_compat(
    conn: sqlite3.Connection,
    *,
    action_type: str,
    table_name: str,
    column_name: str | None = None,
    index_name: str | None = None,
    sql_text: str | None = None,
    success: bool = True,
    message: str | None = None,
) -> None:
    try:
        cur = conn.cursor()
        if not _table_exists(cur, "schema_compat_logs"):
            return
        cur.execute(
            """
            INSERT INTO schema_compat_logs (
                action_type, table_name, column_name, index_name, sql_text,
                success, message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_type,
                table_name,
                column_name,
                index_name,
                sql_text,
                1 if success else 0,
                message,
                _utc_now(),
            ),
        )
    except Exception:
        # Schema compatibility logging ana şema düzeltmesini bloklamamalı.
        return


def _log_schema_compat_result(conn: sqlite3.Connection, name: str, result: dict[str, Any]) -> None:
    tables_created = int(result.get("tables_created") or 0)
    columns_added = int(result.get("columns_added") or result.get("column_added") or 0)
    tables_rebuilt = int(result.get("tables_rebuilt") or 0)
    indexes_created = int(result.get("indexes_created") or 0)
    if tables_created:
        action_type = "create_table"
    elif columns_added:
        action_type = "add_column"
    elif tables_rebuilt:
        action_type = "rebuild_table"
    elif indexes_created:
        # Most schema helpers use CREATE INDEX IF NOT EXISTS and report the
        # attempted index count, not actual changes. Avoid write-heavy log spam
        # on every GUI/API connection after the schema is already healthy.
        return
    else:
        return
    message = (
        f"{name}: tables_created={tables_created}, "
        f"columns_added={columns_added}, tables_rebuilt={tables_rebuilt}, "
        f"indexes_created={indexes_created}"
    )
    _log_schema_compat(conn, action_type=action_type, table_name=name, success=True, message=message)


def ensure_architecture_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    changed = {"tables_created": 0, "indexes_created": 0, "columns_added": 0}
    cur = conn.cursor()
    tables = {
        "schema_compat_logs": """
            CREATE TABLE schema_compat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                table_name TEXT NOT NULL,
                column_name TEXT,
                index_name TEXT,
                sql_text TEXT,
                success INTEGER NOT NULL DEFAULT 1,
                message TEXT,
                created_at TEXT NOT NULL
            )
        """,
        "sql_console_audit_logs": """
            CREATE TABLE sql_console_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                client_id TEXT,
                role TEXT,
                sql_text TEXT NOT NULL,
                statement_type TEXT,
                read_only INTEGER NOT NULL DEFAULT 1,
                dangerous INTEGER NOT NULL DEFAULT 0,
                allowed INTEGER NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                row_count INTEGER,
                executed_at TEXT NOT NULL,
                environment TEXT,
                request_id TEXT
            )
        """,
        "api_clients": """
            CREATE TABLE api_clients (
                id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                api_key_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'api_client',
                faculty_id INTEGER,
                department_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                last_used_at TEXT,
                notes TEXT
            )
        """,
        "secure_import_jobs": """
            CREATE TABLE secure_import_jobs (
                id TEXT PRIMARY KEY,
                import_type TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT,
                file_hash TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                mime_type TEXT,
                uploaded_by TEXT,
                uploaded_at TEXT,
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                semester TEXT,
                status TEXT NOT NULL DEFAULT 'uploaded',
                validation_summary_json TEXT,
                preview_summary_json TEXT,
                row_count INTEGER,
                warning_count INTEGER,
                error_count INTEGER,
                critical_count INTEGER,
                approval_required INTEGER NOT NULL DEFAULT 1,
                approved_by TEXT,
                approved_at TEXT,
                rejected_by TEXT,
                rejected_at TEXT,
                rejection_reason TEXT,
                applied_by TEXT,
                applied_at TEXT,
                rollback_available INTEGER NOT NULL DEFAULT 0,
                rollback_snapshot_id TEXT,
                notes TEXT
            )
        """,
        "secure_import_job_rows": """
            CREATE TABLE secure_import_job_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_job_id TEXT NOT NULL,
                row_number INTEGER NOT NULL,
                raw_data_json TEXT NOT NULL,
                normalized_data_json TEXT,
                matched_course_id INTEGER,
                row_status TEXT NOT NULL DEFAULT 'valid',
                issues_json TEXT,
                created_at TEXT
            )
        """,
        "security_audit_logs": """
            CREATE TABLE security_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                actor_id TEXT,
                role TEXT,
                faculty_id INTEGER,
                department_id INTEGER,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                severity TEXT NOT NULL DEFAULT 'info',
                message TEXT NOT NULL,
                before_json TEXT,
                after_json TEXT,
                metadata_json TEXT,
                request_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT,
                previous_hash TEXT,
                event_hash TEXT
            )
        """,
        "data_snapshots": """
            CREATE TABLE data_snapshots (
                id TEXT PRIMARY KEY,
                snapshot_type TEXT NOT NULL,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                related_import_job_id TEXT,
                related_decision_run_id INTEGER,
                snapshot_path TEXT,
                snapshot_hash TEXT,
                created_by TEXT,
                created_at TEXT,
                notes TEXT
            )
        """,
    }
    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1
            _log_schema_compat(
                conn,
                action_type="create_table",
                table_name=table_name,
                sql_text=ddl.strip(),
                success=True,
                message="Mimari denetim/audit tablosu oluşturuldu.",
            )
    for table_name, columns in {
        "schema_compat_logs": [
            ("action_type", "TEXT"),
            ("table_name", "TEXT"),
            ("column_name", "TEXT"),
            ("index_name", "TEXT"),
            ("sql_text", "TEXT"),
            ("success", "INTEGER NOT NULL DEFAULT 1"),
            ("message", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "sql_console_audit_logs": [
            ("user_id", "TEXT"),
            ("client_id", "TEXT"),
            ("role", "TEXT"),
            ("sql_text", "TEXT"),
            ("statement_type", "TEXT"),
            ("read_only", "INTEGER NOT NULL DEFAULT 1"),
            ("dangerous", "INTEGER NOT NULL DEFAULT 0"),
            ("allowed", "INTEGER NOT NULL DEFAULT 0"),
            ("success", "INTEGER NOT NULL DEFAULT 0"),
            ("error_message", "TEXT"),
            ("row_count", "INTEGER"),
            ("executed_at", "TEXT"),
            ("environment", "TEXT"),
            ("request_id", "TEXT"),
        ],
        "api_clients": [
            ("client_name", "TEXT"),
            ("api_key_hash", "TEXT"),
            ("role", "TEXT NOT NULL DEFAULT 'api_client'"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("is_active", "INTEGER NOT NULL DEFAULT 1"),
            ("created_at", "TEXT"),
            ("last_used_at", "TEXT"),
            ("notes", "TEXT"),
        ],
        "secure_import_jobs": [
            ("import_type", "TEXT"),
            ("original_filename", "TEXT"),
            ("stored_filename", "TEXT"),
            ("file_hash", "TEXT"),
            ("file_size_bytes", "INTEGER"),
            ("mime_type", "TEXT"),
            ("uploaded_by", "TEXT"),
            ("uploaded_at", "TEXT"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("semester", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'uploaded'"),
            ("validation_summary_json", "TEXT"),
            ("preview_summary_json", "TEXT"),
            ("row_count", "INTEGER"),
            ("warning_count", "INTEGER"),
            ("error_count", "INTEGER"),
            ("critical_count", "INTEGER"),
            ("approval_required", "INTEGER NOT NULL DEFAULT 1"),
            ("approved_by", "TEXT"),
            ("approved_at", "TEXT"),
            ("rejected_by", "TEXT"),
            ("rejected_at", "TEXT"),
            ("rejection_reason", "TEXT"),
            ("applied_by", "TEXT"),
            ("applied_at", "TEXT"),
            ("rollback_available", "INTEGER NOT NULL DEFAULT 0"),
            ("rollback_snapshot_id", "TEXT"),
            ("notes", "TEXT"),
        ],
        "secure_import_job_rows": [
            ("import_job_id", "TEXT"),
            ("row_number", "INTEGER"),
            ("raw_data_json", "TEXT"),
            ("normalized_data_json", "TEXT"),
            ("matched_course_id", "INTEGER"),
            ("row_status", "TEXT NOT NULL DEFAULT 'valid'"),
            ("issues_json", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "security_audit_logs": [
            ("event_type", "TEXT"),
            ("actor_type", "TEXT"),
            ("actor_id", "TEXT"),
            ("role", "TEXT"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("resource_type", "TEXT"),
            ("resource_id", "TEXT"),
            ("action", "TEXT"),
            ("success", "INTEGER NOT NULL DEFAULT 1"),
            ("severity", "TEXT NOT NULL DEFAULT 'info'"),
            ("message", "TEXT"),
            ("before_json", "TEXT"),
            ("after_json", "TEXT"),
            ("metadata_json", "TEXT"),
            ("request_id", "TEXT"),
            ("ip_address", "TEXT"),
            ("user_agent", "TEXT"),
            ("created_at", "TEXT"),
            ("previous_hash", "TEXT"),
            ("event_hash", "TEXT"),
        ],
        "data_snapshots": [
            ("snapshot_type", "TEXT"),
            ("scope_type", "TEXT NOT NULL DEFAULT 'global'"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("related_import_job_id", "TEXT"),
            ("related_decision_run_id", "INTEGER"),
            ("snapshot_path", "TEXT"),
            ("snapshot_hash", "TEXT"),
            ("created_by", "TEXT"),
            ("created_at", "TEXT"),
            ("notes", "TEXT"),
        ],
    }.items():
        changed["columns_added"] += _ensure_columns(cur, table_name, columns)
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_schema_compat_logs_created ON schema_compat_logs (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_sql_console_audit_executed ON sql_console_audit_logs (executed_at)",
        "CREATE INDEX IF NOT EXISTS ix_api_clients_active ON api_clients (is_active, role)",
        "CREATE INDEX IF NOT EXISTS ix_secure_import_jobs_status ON secure_import_jobs (status, uploaded_at)",
        "CREATE INDEX IF NOT EXISTS ix_security_audit_logs_created ON security_audit_logs (created_at, event_type)",
    ]
    for ddl in indexes:
        cur.execute(ddl)
        changed["indexes_created"] += 1
    if commit:
        conn.commit()
    return changed


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
        "columns_added": 0,
        "rows_normalized": 0,
        "duplicates_removed": 0,
        "indexes_created": 0,
    }

    if not _table_exists(cur, "havuz"):
        return changed

    cols = _column_names(cur, "havuz")
    if "donem" not in cols:
        cur.execute("ALTER TABLE havuz ADD COLUMN donem TEXT NOT NULL DEFAULT 'Guz'")
        changed["column_added"] += 1
        changed["columns_added"] += 1
        cols.add("donem")
    if "fakulte_id" not in cols:
        cur.execute("ALTER TABLE havuz ADD COLUMN fakulte_id INTEGER")
        changed["column_added"] += 1
        changed["columns_added"] += 1
        cols.add("fakulte_id")

    cur.execute(
        """
        SELECT COUNT(*)
        FROM havuz
        WHERE donem IS NULL
           OR TRIM(COALESCE(donem, '')) = ''
           OR LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) NOT IN ('g', 'b')
        """
    )
    needs_normalization = int((cur.fetchone() or [0])[0] or 0)
    if needs_normalization:
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
        SELECT COUNT(*)
        FROM (
            SELECT 1
            FROM havuz
            GROUP BY ders_id, fakulte_id, yil, donem
            HAVING COUNT(*) > 1
        )
        """
    )
    duplicate_groups = int((cur.fetchone() or [0])[0] or 0)
    if duplicate_groups:
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

    # Legacy donemsiz UNIQUE index temizligi:
    # Eski semalarda (ders_id, fakulte_id, yil) uzerinde donem ICERMEYEN bir UNIQUE
    # index bulunabiliyor (orn. ux_havuz_ders_fak_yil). Bu index, bir dersin ayni yil
    # icinde hem Guz hem Bahar satirina sahip olmasini engeller VE uretim hattindaki
    # term-scoping mantigini (donem ayrimini) devre disi birakir. Donem-scoped unique
    # index kanonik kabul edilir; donemsiz olanlari dusuruyoruz.
    for idx in cur.execute("PRAGMA index_list(havuz)").fetchall():
        if not idx or not int(idx[2] or 0):  # idx[2] = unique bayragi
            continue
        idx_name = str(idx[1])
        idx_cols = {str(r[2]) for r in cur.execute(f"PRAGMA index_info({idx_name})").fetchall()}
        if {"ders_id", "fakulte_id", "yil"}.issubset(idx_cols) and "donem" not in idx_cols:
            cur.execute(f'DROP INDEX IF EXISTS "{idx_name}"')
            changed["indexes_dropped"] = changed.get("indexes_dropped", 0) + 1

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
        SELECT COUNT(*)
        FROM skor
        WHERE donem IS NULL
           OR TRIM(COALESCE(donem, '')) = ''
           OR LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) NOT IN ('g', 'b')
        """
    )
    needs_normalization = int((cur.fetchone() or [0])[0] or 0)
    if needs_normalization:
        cur.execute(
            """
            UPDATE skor
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

    idx_names = _index_names(cur, "skor")
    if "uq_skor_ders_year_term" not in idx_names:
        pk_col = "skor_id" if "skor_id" in cols else ("id" if "id" in cols else "rowid")
        cur.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT 1
                FROM skor
                GROUP BY ders_id, akademik_yil, donem
                HAVING COUNT(*) > 1
            )
            """
        )
        duplicate_groups = int((cur.fetchone() or [0])[0] or 0)
        if duplicate_groups:
            cur.execute(
                f"""
                DELETE FROM skor
                WHERE {pk_col} NOT IN (
                    SELECT MIN({pk_col})
                    FROM skor
                    GROUP BY ders_id, akademik_yil, donem
                )
                """
            )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_skor_ders_year_term
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


def ensure_decision_governance_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """
    Karar yonetisimi ve aciklanabilirlik tablolarini hazirlar.

    Bu sema Alembic migration hattini tamamlar; migration calismamis legacy
    SQLite dosyalarinda da uygulama acilirken idempotent olarak tablo, kolon
    ve indeksleri olusturur.
    """
    cur = conn.cursor()
    changed = {"tables_created": 0, "indexes_created": 0, "columns_added": 0}

    table_ddls = {
        "ahp_weight_profiles": """
            CREATE TABLE ahp_weight_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                criteria_keys_json TEXT NOT NULL,
                pairwise_matrix_json TEXT NOT NULL,
                weights_json TEXT NOT NULL,
                consistency_index REAL,
                consistency_ratio REAL,
                is_consistent INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'default',
                created_by TEXT,
                notes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "decision_policies": """
            CREATE TABLE decision_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                mode TEXT NOT NULL DEFAULT 'static_threshold',
                curriculum_keep_threshold REAL NOT NULL DEFAULT 70,
                pool_threshold REAL NOT NULL DEFAULT 50,
                rest_threshold REAL NOT NULL DEFAULT 40,
                cancel_candidate_threshold REAL DEFAULT 30,
                min_success_rate REAL,
                min_survey_count INTEGER,
                min_enrollment_rate REAL,
                new_course_grace_period_years INTEGER NOT NULL DEFAULT 2,
                low_data_confidence_threshold REAL NOT NULL DEFAULT 0.50,
                sensitivity_margin REAL NOT NULL DEFAULT 3.0,
                top_percent_curriculum REAL,
                middle_percent_pool REAL,
                bottom_percent_rest REAL,
                require_manual_approval_for_cancel INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                CHECK (scope_type IN ('global', 'faculty', 'department')),
                CHECK (mode IN ('static_threshold')),
                CHECK (curriculum_keep_threshold BETWEEN 0 AND 100),
                CHECK (pool_threshold BETWEEN 0 AND 100),
                CHECK (rest_threshold BETWEEN 0 AND 100),
                CHECK (cancel_candidate_threshold IS NULL OR cancel_candidate_threshold BETWEEN 0 AND 100),
                CHECK (cancel_candidate_threshold IS NULL OR cancel_candidate_threshold <= rest_threshold),
                CHECK (rest_threshold < pool_threshold),
                CHECK (pool_threshold < curriculum_keep_threshold),
                CHECK (
                    (scope_type = 'global' AND faculty_id IS NULL AND department_id IS NULL)
                    OR (scope_type = 'faculty' AND faculty_id IS NOT NULL AND department_id IS NULL)
                    OR (scope_type = 'department' AND faculty_id IS NOT NULL AND department_id IS NOT NULL)
                )
            )
        """,
        "decision_runs": """
            CREATE TABLE decision_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                semester TEXT,
                algorithm_version TEXT NOT NULL,
                ahp_profile_id INTEGER,
                decision_policy_id INTEGER,
                decision_policy_snapshot_json TEXT,
                decision_policy_version INTEGER,
                decision_policy_mode TEXT,
                input_data_hash TEXT,
                status TEXT NOT NULL DEFAULT 'started',
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                created_by TEXT,
                summary_json TEXT,
                error_message TEXT,
                CHECK (status IN ('started', 'completed', 'failed', 'cancelled'))
            )
        """,
        "course_decisions": """
            CREATE TABLE course_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                semester TEXT,
                old_status INTEGER,
                recommended_status INTEGER,
                final_status INTEGER,
                topsis_score REAL,
                trend_score REAL,
                trend_label TEXT,
                data_confidence_score REAL,
                acilabilirlik_score REAL,
                decision_stability TEXT,
                approval_required INTEGER NOT NULL DEFAULT 0,
                approval_status TEXT,
                approval_by TEXT,
                approval_at TEXT,
                approval_reason TEXT,
                override_applied INTEGER NOT NULL DEFAULT 0,
                override_reason TEXT,
                main_reason TEXT,
                rule_triggered TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (
                    approval_status IS NULL
                    OR approval_status IN ('pending', 'approved', 'rejected', 'returned')
                )
            )
        """,
        "course_score_breakdowns": """
            CREATE TABLE course_score_breakdowns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                raw_values_json TEXT,
                normalized_values_json TEXT,
                weighted_values_json TEXT,
                weights_json TEXT,
                positive_distance REAL,
                negative_distance REAL,
                closeness_coefficient REAL,
                final_score REAL,
                contribution_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "course_trend_analysis": """
            CREATE TABLE course_trend_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                values_by_year_json TEXT,
                trend_score REAL,
                trend_label TEXT,
                volatility_score REAL,
                data_points_count INTEGER NOT NULL DEFAULT 0,
                explanation TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "course_data_confidence": """
            CREATE TABLE course_data_confidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                score REAL NOT NULL DEFAULT 0,
                level TEXT NOT NULL DEFAULT 'low',
                has_success_data INTEGER NOT NULL DEFAULT 0,
                has_popularity_data INTEGER NOT NULL DEFAULT 0,
                has_survey_data INTEGER NOT NULL DEFAULT 0,
                has_trend_data INTEGER NOT NULL DEFAULT 0,
                has_recent_data INTEGER NOT NULL DEFAULT 0,
                survey_count INTEGER,
                data_points_count INTEGER NOT NULL DEFAULT 0,
                missing_fields_json TEXT,
                explanation TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "course_decision_explanations": """
            CREATE TABLE course_decision_explanations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_decision_id INTEGER NOT NULL,
                main_reason TEXT,
                secondary_reasons_json TEXT,
                positive_factors_json TEXT,
                negative_factors_json TEXT,
                rule_triggered TEXT,
                confidence_level TEXT,
                human_readable_text TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "decision_sensitivity_results": """
            CREATE TABLE decision_sensitivity_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                base_score REAL,
                min_score REAL,
                max_score REAL,
                score_range REAL,
                decision_changed INTEGER NOT NULL DEFAULT 0,
                stability_level TEXT NOT NULL DEFAULT 'medium',
                tested_variations_json TEXT,
                explanation TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "decision_fairness_reports": """
            CREATE TABLE decision_fairness_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER NOT NULL,
                report_json TEXT,
                summary_text TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "course_governance_flags": """
            CREATE TABLE course_governance_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                strategic_flag INTEGER NOT NULL DEFAULT 0,
                accreditation_flag INTEGER NOT NULL DEFAULT 0,
                instructor_changed INTEGER NOT NULL DEFAULT 0,
                content_updated INTEGER NOT NULL DEFAULT 0,
                protected_until_year INTEGER,
                notes TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id)
            )
        """,
    }

    for table_name, ddl in table_ddls.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1

    columns_to_ensure = {
        "decision_policies": [
            ("name", "TEXT"),
            ("scope_type", "TEXT NOT NULL DEFAULT 'global'"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("mode", "TEXT NOT NULL DEFAULT 'static_threshold'"),
            ("curriculum_keep_threshold", "REAL NOT NULL DEFAULT 70"),
            ("pool_threshold", "REAL NOT NULL DEFAULT 50"),
            ("rest_threshold", "REAL NOT NULL DEFAULT 40"),
            ("cancel_candidate_threshold", "REAL DEFAULT 30"),
            ("min_success_rate", "REAL"),
            ("min_survey_count", "INTEGER"),
            ("min_enrollment_rate", "REAL"),
            ("new_course_grace_period_years", "INTEGER NOT NULL DEFAULT 2"),
            ("low_data_confidence_threshold", "REAL NOT NULL DEFAULT 0.50"),
            ("sensitivity_margin", "REAL NOT NULL DEFAULT 3.0"),
            ("top_percent_curriculum", "REAL"),
            ("middle_percent_pool", "REAL"),
            ("bottom_percent_rest", "REAL"),
            ("require_manual_approval_for_cancel", "INTEGER NOT NULL DEFAULT 1"),
            ("is_active", "INTEGER NOT NULL DEFAULT 1"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
            ("notes", "TEXT"),
        ],
        "decision_runs": [
            ("run_name", "TEXT"),
            ("year", "INTEGER"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("semester", "TEXT"),
            ("algorithm_version", "TEXT"),
            ("ahp_profile_id", "INTEGER"),
            ("decision_policy_id", "INTEGER"),
            ("decision_policy_snapshot_json", "TEXT"),
            ("decision_policy_version", "INTEGER"),
            ("decision_policy_mode", "TEXT"),
            ("input_data_hash", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'started'"),
            ("started_at", "TEXT"),
            ("completed_at", "TEXT"),
            ("created_by", "TEXT"),
            ("summary_json", "TEXT"),
            ("error_message", "TEXT"),
        ],
        "course_decisions": [
            ("decision_run_id", "INTEGER"),
            ("course_id", "INTEGER"),
            ("year", "INTEGER"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("semester", "TEXT"),
            ("old_status", "INTEGER"),
            ("recommended_status", "INTEGER"),
            ("final_status", "INTEGER"),
            ("topsis_score", "REAL"),
            ("trend_score", "REAL"),
            ("trend_label", "TEXT"),
            ("data_confidence_score", "REAL"),
            ("acilabilirlik_score", "REAL"),
            ("decision_stability", "TEXT"),
            ("approval_required", "INTEGER NOT NULL DEFAULT 0"),
            ("approval_status", "TEXT"),
            ("approval_by", "TEXT"),
            ("approval_at", "TEXT"),
            ("approval_reason", "TEXT"),
            ("override_applied", "INTEGER NOT NULL DEFAULT 0"),
            ("override_reason", "TEXT"),
            ("main_reason", "TEXT"),
            ("rule_triggered", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "course_score_breakdowns": [
            ("decision_run_id", "INTEGER"),
            ("course_id", "INTEGER"),
            ("year", "INTEGER"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("raw_values_json", "TEXT"),
            ("normalized_values_json", "TEXT"),
            ("weighted_values_json", "TEXT"),
            ("weights_json", "TEXT"),
            ("positive_distance", "REAL"),
            ("negative_distance", "REAL"),
            ("closeness_coefficient", "REAL"),
            ("final_score", "REAL"),
            ("contribution_json", "TEXT"),
            ("created_at", "TEXT"),
        ],
    }
    for table_name, columns in columns_to_ensure.items():
        changed["columns_added"] += _ensure_columns(cur, table_name, columns)

    # Legacy veride ayni kapsamta birden fazla aktif policy varsa son kaydi
    # koru; aksi halde partial unique index kurulumu mevcut DB'lerde kirilir.
    if _table_exists(cur, "decision_policies"):
        cur.execute(
            """
            UPDATE decision_policies
            SET is_active = 0
            WHERE is_active = 1
              AND id NOT IN (
                  SELECT MAX(id)
                  FROM decision_policies
                  WHERE is_active = 1
                  GROUP BY
                      scope_type,
                      COALESCE(faculty_id, -1),
                      COALESCE(department_id, -1),
                      COALESCE(year, -1)
              )
            """
        )

    index_ddls = [
        """
        CREATE INDEX IF NOT EXISTS ix_ahp_profiles_scope
        ON ahp_weight_profiles (scope_type, faculty_id, department_id, year, is_active)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_decision_policies_scope
        ON decision_policies (scope_type, faculty_id, department_id, year, is_active)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_decision_runs_scope
        ON decision_runs (year, faculty_id, department_id, semester, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_decisions_run
        ON course_decisions (decision_run_id, course_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_score_breakdowns_run
        ON course_score_breakdowns (decision_run_id, course_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_trend_run
        ON course_trend_analysis (decision_run_id, course_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_confidence_run
        ON course_data_confidence (decision_run_id, course_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_sensitivity_run
        ON decision_sensitivity_results (decision_run_id, course_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_fairness_run
        ON decision_fairness_reports (decision_run_id)
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_decision_policies_active_scope
        ON decision_policies (
            scope_type,
            COALESCE(faculty_id, -1),
            COALESCE(department_id, -1),
            COALESCE(year, -1)
        )
        WHERE is_active = 1
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_course_decisions_run_course
        ON course_decisions (decision_run_id, course_id)
        WHERE decision_run_id IS NOT NULL AND course_id IS NOT NULL
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_course_score_breakdowns_run_course
        ON course_score_breakdowns (decision_run_id, course_id)
        WHERE decision_run_id IS NOT NULL AND course_id IS NOT NULL
        """,
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_ahp_governance_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """AHP profil, kriter, policy, staleness ve sensitivity semasini hazirlar."""
    base = ensure_decision_governance_schema(conn, commit=False)
    cur = conn.cursor()
    changed = {
        "tables_created": int(base.get("tables_created", 0) or 0),
        "columns_added": 0,
        "indexes_created": int(base.get("indexes_created", 0) or 0),
    }

    def add_columns(table_name: str, columns: list[tuple[str, str]]) -> None:
        if not _table_exists(cur, table_name):
            return
        cols = _column_names(cur, table_name)
        for col_name, ddl in columns:
            if col_name not in cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {ddl}")
                cols.add(col_name)
                changed["columns_added"] += 1

    if not _table_exists(cur, "decision_criteria_definitions"):
        cur.execute(
            """
            CREATE TABLE decision_criteria_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criterion_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                criterion_type TEXT NOT NULL DEFAULT 'score',
                is_benefit INTEGER NOT NULL DEFAULT 1,
                default_enabled INTEGER NOT NULL DEFAULT 1,
                min_value REAL,
                max_value REAL,
                normalization_method TEXT,
                source_type TEXT,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        changed["tables_created"] += 1

    add_columns(
        "ahp_weight_profiles",
        [
            ("profile_name", "TEXT"),
            ("profile_code", "TEXT"),
            ("semester", "TEXT"),
            ("version", "INTEGER NOT NULL DEFAULT 1"),
            ("consistency_warning", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'active'"),
            ("approved_by", "TEXT"),
            ("approved_at", "TEXT"),
            ("rejected_by", "TEXT"),
            ("rejected_at", "TEXT"),
            ("rejection_reason", "TEXT"),
            ("parent_profile_id", "INTEGER"),
            ("superseded_by_profile_id", "INTEGER"),
        ],
    )
    add_columns(
        "decision_runs",
        [
            ("ahp_profile_version", "INTEGER"),
            ("ahp_weights_snapshot_json", "TEXT"),
            ("ahp_consistency_ratio", "REAL"),
            ("ahp_profile_status_at_run", "TEXT"),
            ("ahp_profile_source", "TEXT"),
            ("stale_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("recalculate_required", "INTEGER NOT NULL DEFAULT 0"),
        ],
    )
    add_columns(
        "course_score_breakdowns",
        [
            ("ahp_profile_id", "INTEGER"),
            ("weighted_contribution_json", "TEXT"),
        ],
    )
    add_columns(
        "skor",
        [
            ("ahp_profile_id", "INTEGER"),
            ("weights_snapshot_json", "TEXT"),
        ],
    )

    tables = {
        "ahp_profile_policies": """
            CREATE TABLE ahp_profile_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                semester TEXT,
                max_consistency_ratio REAL NOT NULL DEFAULT 0.10,
                require_approval_for_activation INTEGER NOT NULL DEFAULT 1,
                allow_inconsistent_profile_for_draft_runs INTEGER NOT NULL DEFAULT 0,
                allow_default_profile_if_missing INTEGER NOT NULL DEFAULT 1,
                mark_decisions_stale_on_profile_change INTEGER NOT NULL DEFAULT 1,
                require_notes_for_manual_profile INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "ahp_profile_approval_logs": """
            CREATE TABLE ahp_profile_approval_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                actor TEXT,
                message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "decision_staleness_flags": """
            CREATE TABLE decision_staleness_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                old_reference_id INTEGER,
                new_reference_id INTEGER,
                message TEXT,
                requires_recalculation INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                resolved_by TEXT
            )
        """,
        "ahp_sensitivity_results": """
            CREATE TABLE ahp_sensitivity_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER NOT NULL,
                ahp_profile_id INTEGER,
                variation_percent REAL NOT NULL DEFAULT 0.05,
                tested_variations_json TEXT,
                affected_courses_count INTEGER NOT NULL DEFAULT 0,
                sensitive_courses_json TEXT,
                stability_summary_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "ahp_course_sensitivity_items": """
            CREATE TABLE ahp_course_sensitivity_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensitivity_result_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                base_score REAL,
                min_score REAL,
                max_score REAL,
                score_range REAL,
                base_decision TEXT,
                changed_decision TEXT,
                stability_level TEXT NOT NULL DEFAULT 'medium',
                explanation TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }
    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1

    index_ddls = [
        "CREATE INDEX IF NOT EXISTS ix_decision_criteria_key ON decision_criteria_definitions (criterion_key, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_ahp_profiles_governance_scope ON ahp_weight_profiles (scope_type, faculty_id, department_id, year, semester, status, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_ahp_profile_policies_scope ON ahp_profile_policies (scope_type, faculty_id, department_id, year, semester, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_ahp_approval_logs_profile ON ahp_profile_approval_logs (profile_id, action, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_decision_staleness_run ON decision_staleness_flags (decision_run_id, reason, requires_recalculation)",
        "CREATE INDEX IF NOT EXISTS ix_ahp_sensitivity_run ON ahp_sensitivity_results (decision_run_id, ahp_profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_ahp_course_sensitivity_result ON ahp_course_sensitivity_items (sensitivity_result_id, course_id)",
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1

    # Legacy name kolonunu yeni profile_name ile senkron tut.
    if _table_exists(cur, "ahp_weight_profiles"):
        cols = _column_names(cur, "ahp_weight_profiles")
        if "profile_name" in cols:
            cur.execute(
                """
                UPDATE ahp_weight_profiles
                SET profile_name = CASE
                    WHEN name IS NOT NULL
                         AND TRIM(name) <> ''
                         AND LOWER(TRIM(name)) NOT IN ('(isimsiz)', 'isimsiz', 'none', 'null', '---')
                    THEN TRIM(name)
                    ELSE 'AHP Profili #' || id
                END
                WHERE profile_name IS NULL
                   OR TRIM(profile_name) = ''
                   OR LOWER(TRIM(profile_name)) IN ('(isimsiz)', 'isimsiz', 'none', 'null', '---')
                """
            )
            cur.execute(
                """
                UPDATE ahp_weight_profiles
                SET name = profile_name
                WHERE name IS NULL
                   OR TRIM(name) = ''
                   OR LOWER(TRIM(name)) IN ('(isimsiz)', 'isimsiz', 'none', 'null', '---')
                """
            )
        if "status" in cols:
            cur.execute("UPDATE ahp_weight_profiles SET status = COALESCE(status, CASE WHEN is_active=1 THEN 'active' ELSE 'archived' END)")

    if commit:
        conn.commit()
    return changed


def ensure_pool_state_governance_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """Havuz yasam dongusu state machine semasini idempotent hazirlar."""
    cur = conn.cursor()
    changed = {"tables_created": 0, "columns_added": 0, "indexes_created": 0}

    def add_missing_columns(table_name: str, columns: list[tuple[str, str]]) -> None:
        if not _table_exists(cur, table_name):
            return
        cols = _column_names(cur, table_name)
        for col_name, ddl in columns:
            if col_name not in cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {ddl}")
                cols.add(col_name)
                changed["columns_added"] += 1

    if not _table_exists(cur, "pool_state_policies"):
        cur.execute(
            """
            CREATE TABLE pool_state_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                semester TEXT,
                low_score_threshold REAL NOT NULL DEFAULT 50,
                medium_score_threshold REAL NOT NULL DEFAULT 70,
                high_score_threshold REAL NOT NULL DEFAULT 80,
                pool_entry_threshold REAL NOT NULL DEFAULT 60,
                rest_threshold REAL NOT NULL DEFAULT 45,
                cancel_candidate_threshold REAL NOT NULL DEFAULT 35,
                reactivation_threshold REAL NOT NULL DEFAULT 75,
                rest_after_years_in_pool INTEGER NOT NULL DEFAULT 2,
                cancel_after_years_in_rest INTEGER NOT NULL DEFAULT 2,
                max_years_in_pool INTEGER,
                new_course_grace_period_years INTEGER NOT NULL DEFAULT 2,
                revised_course_grace_period_years INTEGER NOT NULL DEFAULT 1,
                require_approval_for_cancel INTEGER NOT NULL DEFAULT 1,
                require_approval_for_reactivation INTEGER NOT NULL DEFAULT 1,
                protect_accreditation_courses INTEGER NOT NULL DEFAULT 1,
                protect_strategic_courses INTEGER NOT NULL DEFAULT 1,
                protect_required_courses INTEGER NOT NULL DEFAULT 1,
                low_confidence_blocks_cancel INTEGER NOT NULL DEFAULT 1,
                low_confidence_blocks_rest INTEGER NOT NULL DEFAULT 1,
                minimum_data_confidence_for_cancel REAL NOT NULL DEFAULT 0.75,
                minimum_data_confidence_for_rest REAL NOT NULL DEFAULT 0.60,
                allow_reactivation_from_rest INTEGER NOT NULL DEFAULT 1,
                allow_reactivation_from_cancelled INTEGER NOT NULL DEFAULT 0,
                reactivation_requires_manual_approval INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "course_governance_flags"):
        cur.execute(
            """
            CREATE TABLE course_governance_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                strategic_flag INTEGER NOT NULL DEFAULT 0,
                accreditation_flag INTEGER NOT NULL DEFAULT 0,
                protected_flag INTEGER NOT NULL DEFAULT 0,
                required_course_flag INTEGER NOT NULL DEFAULT 0,
                service_course_flag INTEGER NOT NULL DEFAULT 0,
                new_course_flag INTEGER NOT NULL DEFAULT 0,
                revised_course_flag INTEGER NOT NULL DEFAULT 0,
                revision_year INTEGER,
                first_offered_year INTEGER,
                protected_until_year INTEGER,
                protection_reason TEXT,
                instructor_changed INTEGER NOT NULL DEFAULT 0,
                content_updated INTEGER NOT NULL DEFAULT 0,
                updated_by TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                UNIQUE(course_id)
            )
            """
        )
        changed["tables_created"] += 1

    add_missing_columns(
        "course_governance_flags",
        [
            ("protected_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("required_course_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("service_course_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("new_course_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("revised_course_flag", "INTEGER NOT NULL DEFAULT 0"),
            ("revision_year", "INTEGER"),
            ("first_offered_year", "INTEGER"),
            ("protection_reason", "TEXT"),
            ("updated_by", "TEXT"),
        ],
    )

    if not _table_exists(cur, "course_state_transitions"):
        cur.execute(
            """
            CREATE TABLE course_state_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT,
                old_status INTEGER,
                recommended_status INTEGER,
                final_status INTEGER,
                lifecycle_label TEXT,
                trigger TEXT NOT NULL DEFAULT 'algorithm',
                rule_applied TEXT,
                topsis_score REAL,
                trend_score REAL,
                trend_label TEXT,
                data_confidence_score REAL,
                policy_id INTEGER,
                governance_flags_snapshot_json TEXT,
                counter_before INTEGER,
                counter_after INTEGER,
                approval_required INTEGER NOT NULL DEFAULT 0,
                approval_status TEXT,
                override_applied INTEGER NOT NULL DEFAULT 0,
                override_id INTEGER,
                explanation TEXT,
                warnings_json TEXT,
                metadata_json TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "course_state_approvals"):
        cur.execute(
            """
            CREATE TABLE course_state_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT,
                transition_id INTEGER,
                requested_status INTEGER NOT NULL,
                current_status INTEGER,
                approval_type TEXT NOT NULL,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                requested_by TEXT,
                requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approval_reason TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_note TEXT,
                expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "course_state_overrides"):
        cur.execute(
            """
            CREATE TABLE course_state_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT,
                transition_id INTEGER,
                recommended_status INTEGER,
                overridden_final_status INTEGER NOT NULL,
                reason TEXT NOT NULL,
                requested_by TEXT,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        changed["tables_created"] += 1

    add_missing_columns(
        "havuz",
        [
            ("recommended_status", "INTEGER"),
            ("final_status", "INTEGER"),
            ("lifecycle_label", "TEXT"),
            ("approval_required", "INTEGER NOT NULL DEFAULT 0"),
            ("approval_status", "TEXT"),
            ("transition_id", "INTEGER"),
            ("explanation", "TEXT"),
            ("policy_id", "INTEGER"),
        ],
    )

    index_ddls = [
        """
        CREATE INDEX IF NOT EXISTS ix_pool_state_policies_scope
        ON pool_state_policies (scope_type, faculty_id, department_id, year, semester, is_active)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_state_transitions_scope
        ON course_state_transitions (year, course_id, semester, approval_status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_state_approvals_scope
        ON course_state_approvals (year, course_id, semester, approval_status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_course_state_overrides_scope
        ON course_state_overrides (year, course_id, semester, is_active)
        """,
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_import_governance_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """
    Import audit trail ve veri kokeni tablolarini hazirlar.

    Mevcut criteria_import/survey_import yapilari korunur; yeni governance
    katmani ortak import_batches kaydi uzerinden geriye uyumlu iz birakir.
    """
    cur = conn.cursor()
    changed = {
        "tables_created": 0,
        "columns_added": 0,
        "indexes_created": 0,
    }

    def add_missing_columns(table_name: str, columns: list[tuple[str, str]]) -> None:
        if not _table_exists(cur, table_name):
            return
        cols = _column_names(cur, table_name)
        for col_name, ddl in columns:
            if col_name not in cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {ddl}")
                cols.add(col_name)
                changed["columns_added"] += 1

    tables = {
        "import_batches": """
            CREATE TABLE import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_type TEXT NOT NULL,
                source_table TEXT,
                source_import_id INTEGER,
                original_filename TEXT,
                stored_filename TEXT,
                file_hash_sha256 TEXT,
                file_size INTEGER,
                sheet_names_json TEXT,
                row_count INTEGER NOT NULL DEFAULT 0,
                column_count INTEGER NOT NULL DEFAULT 0,
                column_signature_hash TEXT,
                scope_type TEXT,
                school_id INTEGER,
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                semester TEXT,
                uploaded_by TEXT,
                uploaded_at TEXT,
                status TEXT NOT NULL DEFAULT 'uploaded',
                previous_import_batch_id INTEGER,
                superseded_by_import_batch_id INTEGER,
                duplicate_of_import_batch_id INTEGER,
                validation_summary_json TEXT,
                quality_score REAL,
                quality_level TEXT,
                error_message TEXT,
                notes TEXT,
                approved_by TEXT,
                approved_at TEXT,
                rejected_by TEXT,
                rejected_at TEXT,
                rejection_reason TEXT,
                rolled_back_by TEXT,
                rolled_back_at TEXT,
                rollback_reason TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "import_quality_checks": """
            CREATE TABLE import_quality_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id INTEGER NOT NULL,
                quality_score REAL NOT NULL DEFAULT 0.0,
                quality_level TEXT NOT NULL DEFAULT 'low',
                required_columns_ok INTEGER NOT NULL DEFAULT 1,
                successful_row_ratio REAL NOT NULL DEFAULT 0.0,
                matched_course_ratio REAL NOT NULL DEFAULT 0.0,
                valid_numeric_ratio REAL NOT NULL DEFAULT 0.0,
                duplicate_row_count INTEGER NOT NULL DEFAULT 0,
                unmatched_row_count INTEGER NOT NULL DEFAULT 0,
                invalid_numeric_count INTEGER NOT NULL DEFAULT 0,
                missing_required_count INTEGER NOT NULL DEFAULT 0,
                out_of_range_count INTEGER NOT NULL DEFAULT 0,
                warning_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                summary_json TEXT,
                created_at TEXT
            )
        """,
        "import_row_issues": """
            CREATE TABLE import_row_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id INTEGER NOT NULL,
                source_row_id INTEGER,
                row_number INTEGER NOT NULL DEFAULT 0,
                severity TEXT NOT NULL DEFAULT 'warning',
                issue_type TEXT NOT NULL DEFAULT 'unknown_error',
                field_name TEXT,
                raw_value TEXT,
                normalized_value TEXT,
                message TEXT NOT NULL,
                suggestion TEXT,
                created_at TEXT
            )
        """,
        "import_diffs": """
            CREATE TABLE import_diffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id INTEGER NOT NULL,
                compared_to_import_batch_id INTEGER,
                added_count INTEGER NOT NULL DEFAULT 0,
                removed_count INTEGER NOT NULL DEFAULT 0,
                changed_count INTEGER NOT NULL DEFAULT 0,
                unchanged_count INTEGER NOT NULL DEFAULT 0,
                summary_json TEXT,
                created_at TEXT
            )
        """,
        "import_diff_items": """
            CREATE TABLE import_diff_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_diff_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                entity_key TEXT,
                course_id INTEGER,
                field_name TEXT,
                before_value TEXT,
                after_value TEXT,
                before_row_json TEXT,
                after_row_json TEXT,
                message TEXT
            )
        """,
        "import_rollback_logs": """
            CREATE TABLE import_rollback_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                affected_table TEXT NOT NULL,
                affected_record_id INTEGER,
                before_json TEXT,
                after_json TEXT,
                message TEXT,
                created_at TEXT
            )
        """,
        "decision_run_import_sources": """
            CREATE TABLE decision_run_import_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER,
                import_batch_id INTEGER NOT NULL,
                import_type TEXT NOT NULL,
                created_at TEXT
            )
        """,
        "import_impact_reports": """
            CREATE TABLE import_impact_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id INTEGER NOT NULL,
                previous_decision_run_id INTEGER,
                new_decision_run_id INTEGER,
                changed_decision_count INTEGER NOT NULL DEFAULT 0,
                curriculum_to_pool_count INTEGER NOT NULL DEFAULT 0,
                pool_to_curriculum_count INTEGER NOT NULL DEFAULT 0,
                rest_candidate_count INTEGER NOT NULL DEFAULT 0,
                cancel_candidate_count INTEGER NOT NULL DEFAULT 0,
                significant_score_change_count INTEGER NOT NULL DEFAULT 0,
                data_confidence_improved_count INTEGER,
                data_confidence_decreased_count INTEGER,
                summary_json TEXT,
                summary_text TEXT,
                created_at TEXT
            )
        """,
        "criteria_value_sources": """
            CREATE TABLE criteria_value_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                field_name TEXT NOT NULL,
                value_text TEXT,
                value_numeric REAL,
                source_type TEXT NOT NULL,
                source_import_batch_id INTEGER,
                source_row_id INTEGER,
                is_locked INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                overridden_by_source_id INTEGER,
                override_reason TEXT,
                created_by TEXT,
                created_at TEXT
            )
        """,
    }

    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1

    source_import_columns = [
        ("import_batch_id", "INTEGER"),
        ("file_hash_sha256", "TEXT"),
        ("file_size", "INTEGER"),
        ("quality_score", "REAL"),
        ("quality_level", "TEXT"),
        ("previous_import_id", "INTEGER"),
        ("superseded_by_import_id", "INTEGER"),
        ("duplicate_of_import_id", "INTEGER"),
        ("rolled_back_at", "TEXT"),
        ("rollback_reason", "TEXT"),
    ]
    add_missing_columns("criteria_import", source_import_columns)
    add_missing_columns("survey_import", source_import_columns)

    source_row_columns = [
        ("import_batch_id", "INTEGER"),
        ("issue_count", "INTEGER NOT NULL DEFAULT 0"),
        ("normalized_row_json", "TEXT"),
        ("row_hash", "TEXT"),
    ]
    add_missing_columns("criteria_import_rows", source_row_columns)
    add_missing_columns("survey_import_rows", source_row_columns)

    if _table_exists(cur, "ders_kriterleri"):
        add_missing_columns(
            "ders_kriterleri",
            [
                ("source_import_batch_id", "INTEGER"),
                ("is_active", "INTEGER NOT NULL DEFAULT 1"),
                ("superseded_by_import_batch_id", "INTEGER"),
            ],
        )

    index_ddls = [
        """
        CREATE INDEX IF NOT EXISTS ix_import_batches_type_scope
        ON import_batches (import_type, faculty_id, department_id, year, semester, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_batches_hash
        ON import_batches (file_hash_sha256, import_type)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_batches_source
        ON import_batches (source_table, source_import_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_quality_checks_batch
        ON import_quality_checks (import_batch_id, created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_row_issues_batch
        ON import_row_issues (import_batch_id, severity, issue_type)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_diffs_batch
        ON import_diffs (import_batch_id, compared_to_import_batch_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_diff_items_diff
        ON import_diff_items (import_diff_id, change_type)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_rollback_logs_batch
        ON import_rollback_logs (import_batch_id, created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_decision_run_import_sources_batch
        ON decision_run_import_sources (import_batch_id, decision_run_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_import_impact_reports_batch
        ON import_impact_reports (import_batch_id, created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_value_sources_lookup
        ON criteria_value_sources (course_id, year, field_name, is_active)
        """,
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_criteria_completion_governance_schema(
    conn: sqlite3.Connection,
    commit: bool = True,
) -> dict[str, int]:
    """
    Gelismis kriter tamlik, validation, risk, gorev ve override semasini hazirlar.
    """
    cur = conn.cursor()
    changed = {
        "tables_created": 0,
        "columns_added": 0,
        "indexes_created": 0,
    }

    def add_missing_columns(table_name: str, columns: list[tuple[str, str]]) -> None:
        if not _table_exists(cur, table_name):
            return
        cols = _column_names(cur, table_name)
        for col_name, ddl in columns:
            if col_name not in cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {ddl}")
                cols.add(col_name)
                changed["columns_added"] += 1

    if not _table_exists(cur, "criteria_completion_matrix"):
        cur.execute(
            """
            CREATE TABLE criteria_completion_matrix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT,
                criterion_key TEXT NOT NULL,
                is_required INTEGER NOT NULL DEFAULT 1,
                is_present INTEGER NOT NULL DEFAULT 0,
                is_valid INTEGER NOT NULL DEFAULT 0,
                value_text TEXT,
                value_numeric REAL,
                missing_reason TEXT,
                invalid_reason TEXT,
                source_type TEXT,
                source_id INTEGER,
                checked_at TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_validation_issues"):
        cur.execute(
            """
            CREATE TABLE criteria_validation_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                course_id INTEGER,
                year INTEGER NOT NULL,
                semester TEXT,
                criterion_key TEXT,
                severity TEXT NOT NULL DEFAULT 'warning',
                issue_type TEXT NOT NULL DEFAULT 'unknown_error',
                raw_value TEXT,
                message TEXT NOT NULL,
                suggestion TEXT,
                created_at TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_completion_policies"):
        cur.execute(
            """
            CREATE TABLE criteria_completion_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                semester TEXT,
                required_completion_ratio REAL NOT NULL DEFAULT 1.0,
                required_fields_json TEXT NOT NULL,
                optional_fields_json TEXT,
                allow_new_course_missing_history INTEGER NOT NULL DEFAULT 1,
                new_course_grace_period_years INTEGER NOT NULL DEFAULT 2,
                min_survey_response_count INTEGER,
                block_on_invalid_numeric INTEGER NOT NULL DEFAULT 1,
                block_on_critical_issues INTEGER NOT NULL DEFAULT 1,
                allow_override INTEGER NOT NULL DEFAULT 1,
                override_requires_reason INTEGER NOT NULL DEFAULT 1,
                override_requires_approval INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_missing_data_risks"):
        cur.execute(
            """
            CREATE TABLE criteria_missing_data_risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                course_id INTEGER,
                year INTEGER NOT NULL,
                semester TEXT,
                risk_score REAL NOT NULL DEFAULT 0.0,
                risk_level TEXT NOT NULL DEFAULT 'low',
                missing_required_fields_json TEXT,
                missing_optional_fields_json TEXT,
                affected_weight_sum REAL,
                explanation TEXT,
                created_at TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_completion_tasks"):
        cur.execute(
            """
            CREATE TABLE criteria_completion_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                course_id INTEGER,
                year INTEGER NOT NULL,
                semester TEXT,
                assigned_to TEXT,
                assigned_role TEXT,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                missing_fields_json TEXT,
                validation_issues_json TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                created_by TEXT,
                created_at TEXT,
                updated_at TEXT,
                completed_at TEXT,
                approved_by TEXT,
                approved_at TEXT,
                notes TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_completion_overrides"):
        cur.execute(
            """
            CREATE TABLE criteria_completion_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                course_id INTEGER,
                year INTEGER NOT NULL,
                semester TEXT,
                missing_fields_json TEXT,
                validation_issues_json TEXT,
                reason TEXT NOT NULL,
                requested_by TEXT,
                requested_at TEXT,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                approved_by TEXT,
                approved_at TEXT,
                rejected_by TEXT,
                rejected_at TEXT,
                rejection_reason TEXT,
                expires_at TEXT,
                allowed_for_run_id INTEGER,
                used_at TEXT,
                created_at TEXT
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_completion_history"):
        cur.execute(
            """
            CREATE TABLE criteria_completion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER NOT NULL,
                semester TEXT,
                old_status TEXT,
                new_status TEXT NOT NULL,
                old_completion_ratio REAL,
                new_completion_ratio REAL NOT NULL DEFAULT 0.0,
                old_completion_level TEXT,
                new_completion_level TEXT,
                changed_by TEXT,
                change_reason TEXT,
                created_at TEXT,
                summary_json TEXT
            )
            """
        )
        changed["tables_created"] += 1

    status_columns = [
        ("semester", "TEXT"),
        ("completion_ratio", "REAL NOT NULL DEFAULT 0.0"),
        ("completion_level", "TEXT NOT NULL DEFAULT 'not_started'"),
        ("required_completion_ratio", "REAL NOT NULL DEFAULT 1.0"),
        ("total_courses", "INTEGER NOT NULL DEFAULT 0"),
        ("completed_courses", "INTEGER NOT NULL DEFAULT 0"),
        ("partial_courses", "INTEGER NOT NULL DEFAULT 0"),
        ("missing_courses", "INTEGER NOT NULL DEFAULT 0"),
        ("invalid_courses", "INTEGER NOT NULL DEFAULT 0"),
        ("total_required_fields", "INTEGER NOT NULL DEFAULT 0"),
        ("completed_required_fields", "INTEGER NOT NULL DEFAULT 0"),
        ("missing_required_fields", "INTEGER NOT NULL DEFAULT 0"),
        ("invalid_required_fields", "INTEGER NOT NULL DEFAULT 0"),
        ("last_checked_at", "TEXT"),
        ("blocking_reason", "TEXT"),
        ("can_run_algorithm", "INTEGER NOT NULL DEFAULT 0"),
        ("override_active", "INTEGER NOT NULL DEFAULT 0"),
    ]
    add_missing_columns("criteria_department_status", status_columns)
    add_missing_columns("criteria_faculty_status", status_columns)

    index_ddls = [
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_completion_matrix_scope
        ON criteria_completion_matrix (scope_type, faculty_id, department_id, year, semester, course_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_completion_matrix_field
        ON criteria_completion_matrix (criterion_key, is_required, is_present, is_valid)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_validation_issues_scope
        ON criteria_validation_issues (scope_type, faculty_id, department_id, year, semester, severity)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_completion_policies_scope
        ON criteria_completion_policies (scope_type, faculty_id, department_id, year, semester, is_active)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_missing_data_risks_scope
        ON criteria_missing_data_risks (scope_type, faculty_id, department_id, year, semester, risk_level)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_completion_tasks_scope
        ON criteria_completion_tasks (scope_type, faculty_id, department_id, year, semester, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_completion_overrides_scope
        ON criteria_completion_overrides (scope_type, faculty_id, department_id, course_id, year, semester, approval_status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_completion_history_scope
        ON criteria_completion_history (scope_type, faculty_id, department_id, year, semester, created_at)
        """,
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_ml_governance_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """ML algoritma konumlandırma, model run, tahmin ve readiness semasini hazirlar."""
    cur = conn.cursor()
    changed = {
        "tables_created": 0,
        "columns_added": 0,
        "indexes_created": 0,
    }

    tables = {
        "ml_algorithm_registry": """
            CREATE TABLE ml_algorithm_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algorithm_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                algorithm_type TEXT NOT NULL,
                usage_role TEXT NOT NULL DEFAULT 'advisory_ml',
                default_enabled INTEGER NOT NULL DEFAULT 1,
                min_training_samples INTEGER NOT NULL DEFAULT 50,
                min_samples_per_class INTEGER,
                requires_validation INTEGER NOT NULL DEFAULT 1,
                supports_confidence INTEGER NOT NULL DEFAULT 0,
                supports_explainability INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "ml_feature_snapshots": """
            CREATE TABLE ml_feature_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_schema_version TEXT NOT NULL,
                scope_json TEXT,
                year INTEGER,
                faculty_id INTEGER,
                department_id INTEGER,
                sample_count INTEGER NOT NULL DEFAULT 0,
                feature_names_json TEXT NOT NULL,
                missing_features_summary_json TEXT,
                imputation_strategy_json TEXT,
                normalization_summary_json TEXT,
                created_at TEXT
            )
        """,
        "ml_model_runs": """
            CREATE TABLE ml_model_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algorithm_key TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_type TEXT NOT NULL,
                usage_role TEXT NOT NULL,
                model_version TEXT NOT NULL,
                feature_schema_version TEXT NOT NULL,
                training_scope_json TEXT,
                training_sample_count INTEGER NOT NULL DEFAULT 0,
                target_column TEXT,
                class_distribution_json TEXT,
                parameters_json TEXT,
                train_metrics_json TEXT,
                validation_metrics_json TEXT,
                cross_validation_json TEXT,
                overfitting_report_json TEXT,
                readiness_level TEXT,
                readiness_warnings_json TEXT,
                status TEXT NOT NULL DEFAULT 'created',
                skip_reason TEXT,
                artifact_path TEXT,
                created_at TEXT,
                completed_at TEXT,
                created_by TEXT,
                notes TEXT
            )
        """,
        "ml_predictions": """
            CREATE TABLE ml_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_run_id INTEGER,
                algorithm_key TEXT NOT NULL,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                prediction_type TEXT NOT NULL,
                predicted_value_text TEXT,
                predicted_value_numeric REAL,
                confidence_score REAL,
                confidence_level TEXT,
                uncertainty_reasons_json TEXT,
                fallback_used INTEGER NOT NULL DEFAULT 0,
                fallback_method TEXT,
                fallback_reason TEXT,
                advisory_only INTEGER NOT NULL DEFAULT 1,
                should_influence_decision INTEGER NOT NULL DEFAULT 0,
                explanation TEXT,
                created_at TEXT
            )
        """,
        "ml_prediction_explanations": """
            CREATE TABLE ml_prediction_explanations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER NOT NULL,
                top_features_json TEXT,
                feature_importance_json TEXT,
                decision_path_json TEXT,
                limitations_json TEXT,
                human_readable_text TEXT NOT NULL,
                created_at TEXT
            )
        """,
        "ml_readiness_reports": """
            CREATE TABLE ml_readiness_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_json TEXT,
                year INTEGER,
                faculty_id INTEGER,
                department_id INTEGER,
                sample_count INTEGER NOT NULL DEFAULT 0,
                algorithm_readiness_json TEXT,
                feature_quality_json TEXT,
                recommendations_json TEXT,
                summary_text TEXT,
                created_at TEXT
            )
        """,
    }

    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1

    index_ddls = [
        """
        CREATE INDEX IF NOT EXISTS ix_ml_algorithm_registry_key
        ON ml_algorithm_registry (algorithm_key, usage_role)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ml_feature_snapshots_scope
        ON ml_feature_snapshots (year, faculty_id, department_id, created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ml_model_runs_algorithm
        ON ml_model_runs (algorithm_key, status, created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ml_predictions_course
        ON ml_predictions (course_id, year, algorithm_key, created_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ml_prediction_explanations_prediction
        ON ml_prediction_explanations (prediction_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ml_readiness_reports_scope
        ON ml_readiness_reports (year, faculty_id, department_id, created_at)
        """,
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1

    if commit:
        conn.commit()
    return changed


def ensure_algorithm_governance_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """Algoritma yönetişimi, benchmark metrikleri ve istatistiksel değerlendirme semasını hazırlar."""
    cur = conn.cursor()
    changed = {"tables_created": 0, "columns_added": 0, "indexes_created": 0}
    tables = {
        "algorithm_governance_registry": """
            CREATE TABLE algorithm_governance_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algorithm_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                algorithm_family TEXT NOT NULL,
                task_type TEXT NOT NULL,
                usage_role TEXT NOT NULL,
                can_affect_final_decision INTEGER NOT NULL DEFAULT 0,
                default_enabled INTEGER NOT NULL DEFAULT 1,
                minimum_sample_count INTEGER NOT NULL DEFAULT 10,
                minimum_samples_per_class INTEGER,
                requires_feature_scaling INTEGER NOT NULL DEFAULT 0,
                requires_target INTEGER NOT NULL DEFAULT 0,
                supports_probability INTEGER NOT NULL DEFAULT 0,
                supports_feature_importance INTEGER NOT NULL DEFAULT 0,
                supports_explainability INTEGER NOT NULL DEFAULT 0,
                supports_cross_validation INTEGER NOT NULL DEFAULT 0,
                recommended_validation_strategy TEXT,
                recommended_metrics_json TEXT,
                risk_notes TEXT,
                user_facing_warning TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "algorithm_task_mapping": """
            CREATE TABLE algorithm_task_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_key TEXT NOT NULL,
                algorithm_key TEXT NOT NULL,
                allowed_usage_role TEXT NOT NULL,
                is_recommended INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT
            )
        """,
        "algorithm_benchmark_runs": """
            CREATE TABLE algorithm_benchmark_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_name TEXT,
                task_type TEXT NOT NULL,
                dataset_name TEXT,
                dataset_scope_json TEXT,
                sample_count INTEGER NOT NULL DEFAULT 0,
                feature_count INTEGER NOT NULL DEFAULT 0,
                target_column TEXT,
                algorithms_json TEXT,
                validation_strategy TEXT,
                primary_metric_name TEXT,
                status TEXT NOT NULL DEFAULT 'created',
                started_at TEXT,
                completed_at TEXT,
                created_by TEXT,
                summary_json TEXT,
                warnings_json TEXT,
                error_message TEXT
            )
        """,
        "benchmark_metric_results": """
            CREATE TABLE benchmark_metric_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_run_id INTEGER,
                algorithm_key TEXT NOT NULL,
                task_type TEXT NOT NULL,
                metrics_json TEXT,
                primary_metric_name TEXT,
                primary_metric_value REAL,
                warnings_json TEXT,
                created_at TEXT
            )
        """,
        "benchmark_validation_results": """
            CREATE TABLE benchmark_validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_run_id INTEGER,
                algorithm_key TEXT NOT NULL,
                validation_strategy TEXT NOT NULL,
                fold_count INTEGER,
                split_summary_json TEXT,
                fold_metrics_json TEXT,
                mean_metrics_json TEXT,
                std_metrics_json TEXT,
                warnings_json TEXT,
                created_at TEXT
            )
        """,
        "benchmark_statistical_comparisons": """
            CREATE TABLE benchmark_statistical_comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_run_id INTEGER,
                task_type TEXT NOT NULL,
                primary_metric_name TEXT,
                compared_algorithms_json TEXT,
                confidence_intervals_json TEXT,
                pairwise_tests_json TEXT,
                global_test_json TEXT,
                effect_sizes_json TEXT,
                significance_groups_json TEXT,
                summary_text TEXT,
                created_at TEXT
            )
        """,
        "benchmark_data_leakage_reports": """
            CREATE TABLE benchmark_data_leakage_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_run_id INTEGER,
                algorithm_key TEXT,
                leakage_detected INTEGER NOT NULL DEFAULT 0,
                leakage_level TEXT NOT NULL DEFAULT 'none',
                warnings_json TEXT,
                blocked INTEGER NOT NULL DEFAULT 0,
                summary_text TEXT,
                created_at TEXT
            )
        """,
        "benchmark_model_diagnostics": """
            CREATE TABLE benchmark_model_diagnostics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_run_id INTEGER,
                algorithm_key TEXT NOT NULL,
                overfitting_warning INTEGER NOT NULL DEFAULT 0,
                overfitting_score REAL,
                train_validation_gap_json TEXT,
                class_imbalance_warning INTEGER NOT NULL DEFAULT 0,
                class_distribution_json TEXT,
                high_variance_warning INTEGER NOT NULL DEFAULT 0,
                diagnostics_json TEXT,
                summary_text TEXT,
                created_at TEXT
            )
        """,
        "clustering_evaluation_results": """
            CREATE TABLE clustering_evaluation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_run_id INTEGER,
                algorithm_key TEXT NOT NULL,
                cluster_count INTEGER NOT NULL DEFAULT 0,
                noise_ratio REAL,
                silhouette_score REAL,
                davies_bouldin_score REAL,
                calinski_harabasz_score REAL,
                cluster_size_distribution_json TEXT,
                stability_score REAL,
                dbscan_params_json TEXT,
                warnings_json TEXT,
                summary_text TEXT,
                created_at TEXT
            )
        """,
    }
    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1
    index_ddls = [
        "CREATE INDEX IF NOT EXISTS ix_algorithm_governance_registry_role ON algorithm_governance_registry (usage_role, algorithm_family, task_type)",
        "CREATE INDEX IF NOT EXISTS ix_algorithm_task_mapping_task ON algorithm_task_mapping (task_key, algorithm_key, allowed_usage_role)",
        "CREATE INDEX IF NOT EXISTS ix_algorithm_benchmark_runs_status ON algorithm_benchmark_runs (task_type, status, started_at)",
        "CREATE INDEX IF NOT EXISTS ix_benchmark_metric_results_run ON benchmark_metric_results (benchmark_run_id, algorithm_key, task_type)",
        "CREATE INDEX IF NOT EXISTS ix_benchmark_validation_results_run ON benchmark_validation_results (benchmark_run_id, algorithm_key)",
        "CREATE INDEX IF NOT EXISTS ix_benchmark_statistical_comparisons_run ON benchmark_statistical_comparisons (benchmark_run_id, task_type)",
        "CREATE INDEX IF NOT EXISTS ix_benchmark_data_leakage_reports_run ON benchmark_data_leakage_reports (benchmark_run_id, leakage_level)",
        "CREATE INDEX IF NOT EXISTS ix_benchmark_model_diagnostics_run ON benchmark_model_diagnostics (benchmark_run_id, algorithm_key)",
        "CREATE INDEX IF NOT EXISTS ix_clustering_evaluation_results_run ON clustering_evaluation_results (benchmark_run_id, algorithm_key)",
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1
    if commit:
        conn.commit()
    return changed


def ensure_semester_planning_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """Policy tabanli Guz/Bahar donem planlama semasini hazirlar."""
    cur = conn.cursor()
    changed = {"tables_created": 0, "columns_added": 0, "indexes_created": 0}
    tables = {
        "semester_planning_policies": """
            CREATE TABLE semester_planning_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                curriculum_year INTEGER,
                total_elective_target INTEGER NOT NULL DEFAULT 8,
                fall_min INTEGER NOT NULL DEFAULT 4,
                fall_max INTEGER NOT NULL DEFAULT 4,
                spring_min INTEGER NOT NULL DEFAULT 4,
                spring_max INTEGER NOT NULL DEFAULT 4,
                max_semester_imbalance INTEGER NOT NULL DEFAULT 0,
                allow_unbalanced_distribution INTEGER NOT NULL DEFAULT 0,
                same_course_repeat_policy TEXT NOT NULL DEFAULT 'disallow',
                same_course_repeat_requires_approval INTEGER NOT NULL DEFAULT 1,
                high_demand_repeat_threshold REAL,
                consider_course_availability INTEGER NOT NULL DEFAULT 1,
                consider_instructor_availability INTEGER NOT NULL DEFAULT 0,
                consider_resource_constraints INTEGER NOT NULL DEFAULT 0,
                consider_prerequisites INTEGER NOT NULL DEFAULT 1,
                consider_required_course_load INTEGER NOT NULL DEFAULT 0,
                consider_expected_demand INTEGER NOT NULL DEFAULT 1,
                consider_capacity_balance INTEGER NOT NULL DEFAULT 1,
                consider_time_conflicts INTEGER NOT NULL DEFAULT 0,
                minimum_plan_score REAL,
                hard_constraint_policy TEXT NOT NULL DEFAULT 'strict',
                soft_constraint_weight_json TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "course_semester_availability": """
            CREATE TABLE course_semester_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                year INTEGER,
                faculty_id INTEGER,
                department_id INTEGER,
                allowed_fall INTEGER NOT NULL DEFAULT 1,
                allowed_spring INTEGER NOT NULL DEFAULT 1,
                preferred_semester TEXT NOT NULL DEFAULT 'either',
                availability_type TEXT NOT NULL DEFAULT 'always',
                unavailable_reason TEXT,
                effective_from_year INTEGER,
                effective_to_year INTEGER,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "instructors": """
            CREATE TABLE instructors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                faculty_id INTEGER,
                department_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "course_instructor_assignments": """
            CREATE TABLE course_instructor_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                instructor_id INTEGER NOT NULL,
                priority INTEGER NOT NULL DEFAULT 1,
                can_teach INTEGER NOT NULL DEFAULT 1,
                preferred INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "instructor_semester_availability": """
            CREATE TABLE instructor_semester_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instructor_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT NOT NULL,
                available INTEGER NOT NULL DEFAULT 1,
                max_elective_courses INTEGER NOT NULL DEFAULT 2,
                current_assigned_elective_count INTEGER,
                unavailable_reason TEXT,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "teaching_resources": """
            CREATE TABLE teaching_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_name TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                capacity INTEGER,
                available_fall INTEGER NOT NULL DEFAULT 1,
                available_spring INTEGER NOT NULL DEFAULT 1,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "course_resource_requirements": """
            CREATE TABLE course_resource_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL,
                required_capacity INTEGER,
                required_hours REAL,
                hard_requirement INTEGER NOT NULL DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "semester_resource_capacity": """
            CREATE TABLE semester_resource_capacity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT NOT NULL,
                available_capacity INTEGER,
                available_hours REAL,
                reserved_hours REAL,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "course_prerequisites": """
            CREATE TABLE course_prerequisites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                prerequisite_course_id INTEGER NOT NULL,
                prerequisite_type TEXT NOT NULL DEFAULT 'hard',
                relation_note TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "semester_required_course_loads": """
            CREATE TABLE semester_required_course_loads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_id INTEGER,
                department_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT NOT NULL,
                required_course_count INTEGER NOT NULL DEFAULT 0,
                total_credits REAL,
                total_ects REAL,
                workload_score REAL,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """,
        "course_time_constraints": """
            CREATE TABLE course_time_constraints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                year INTEGER,
                semester TEXT,
                unavailable_slots_json TEXT,
                preferred_slots_json TEXT,
                conflict_group TEXT,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        """,
        "semester_plan_runs": """
            CREATE TABLE semester_plan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_name TEXT,
                year INTEGER NOT NULL,
                faculty_id INTEGER,
                department_id INTEGER,
                policy_id INTEGER,
                total_candidate_count INTEGER NOT NULL DEFAULT 0,
                selected_count INTEGER NOT NULL DEFAULT 0,
                fall_count INTEGER NOT NULL DEFAULT 0,
                spring_count INTEGER NOT NULL DEFAULT 0,
                plan_score REAL,
                status TEXT NOT NULL DEFAULT 'created',
                metrics_json TEXT,
                policy_snapshot_json TEXT,
                warnings_json TEXT,
                created_at TEXT,
                completed_at TEXT,
                created_by TEXT,
                error_message TEXT
            )
        """,
        "semester_plan_course_assignments": """
            CREATE TABLE semester_plan_course_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                assigned_semester TEXT NOT NULL,
                assignment_type TEXT NOT NULL DEFAULT 'selected',
                course_score REAL,
                expected_demand REAL,
                expected_capacity REAL,
                constraint_status TEXT NOT NULL DEFAULT 'ok',
                explanation TEXT,
                created_at TEXT
            )
        """,
        "semester_plan_constraint_violations": """
            CREATE TABLE semester_plan_constraint_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL,
                course_id INTEGER,
                constraint_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'warning',
                message TEXT NOT NULL,
                suggestion TEXT,
                created_at TEXT
            )
        """,
        "semester_plan_scenarios": """
            CREATE TABLE semester_plan_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_run_id INTEGER NOT NULL,
                scenario_name TEXT NOT NULL,
                scenario_type TEXT NOT NULL,
                fall_courses_json TEXT,
                spring_courses_json TEXT,
                metrics_json TEXT,
                constraint_violations_json TEXT,
                explanations_json TEXT,
                plan_score REAL,
                created_at TEXT
            )
        """,
    }
    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1

    for table_name, columns in {
        "mufredat": [
            ("semester_plan_run_id", "INTEGER"),
        ],
        "mufredat_ders": [
            ("semester_plan_run_id", "INTEGER"),
            ("assignment_explanation", "TEXT"),
            ("constraint_status", "TEXT"),
        ],
    }.items():
        if not _table_exists(cur, table_name):
            continue
        existing = _column_names(cur, table_name)
        for col_name, col_type in columns:
            if col_name not in existing:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                changed["columns_added"] += 1

    index_ddls = [
        "CREATE INDEX IF NOT EXISTS ix_semester_policy_scope ON semester_planning_policies (scope_type, faculty_id, department_id, year, curriculum_year, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_course_semester_availability_scope ON course_semester_availability (course_id, year, faculty_id, department_id)",
        "CREATE INDEX IF NOT EXISTS ix_course_instructor_assignments_course ON course_instructor_assignments (course_id, instructor_id)",
        "CREATE INDEX IF NOT EXISTS ix_instructor_semester_availability_scope ON instructor_semester_availability (instructor_id, year, semester)",
        "CREATE INDEX IF NOT EXISTS ix_teaching_resources_scope ON teaching_resources (resource_type, faculty_id, department_id, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_course_resource_requirements_course ON course_resource_requirements (course_id, resource_type)",
        "CREATE INDEX IF NOT EXISTS ix_semester_resource_capacity_scope ON semester_resource_capacity (resource_id, year, semester)",
        "CREATE INDEX IF NOT EXISTS ix_course_prerequisites_course ON course_prerequisites (course_id, prerequisite_course_id)",
        "CREATE INDEX IF NOT EXISTS ix_semester_required_loads_scope ON semester_required_course_loads (department_id, year, semester)",
        "CREATE INDEX IF NOT EXISTS ix_course_time_constraints_scope ON course_time_constraints (course_id, year, semester, conflict_group)",
        "CREATE INDEX IF NOT EXISTS ix_semester_plan_runs_scope ON semester_plan_runs (year, faculty_id, department_id, status, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_semester_plan_assignments_run ON semester_plan_course_assignments (plan_run_id, assigned_semester, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_semester_plan_violations_run ON semester_plan_constraint_violations (plan_run_id, severity, constraint_type)",
        "CREATE INDEX IF NOT EXISTS ix_semester_plan_scenarios_run ON semester_plan_scenarios (plan_run_id, scenario_type)",
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1
    if commit:
        conn.commit()
    return changed


def ensure_data_quality_schema(conn: sqlite3.Connection, commit: bool = True) -> dict[str, int]:
    """Data quality, readiness, confidence follow-up tablolarini hazirlar."""
    cur = conn.cursor()
    changed = {"tables_created": 0, "columns_added": 0, "indexes_created": 0}
    tables = {
        "data_coverage_reports": """
            CREATE TABLE data_coverage_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                semester TEXT,
                total_courses INTEGER NOT NULL DEFAULT 0,
                courses_with_criteria INTEGER NOT NULL DEFAULT 0,
                courses_with_performance INTEGER NOT NULL DEFAULT 0,
                courses_with_popularity INTEGER NOT NULL DEFAULT 0,
                courses_with_survey INTEGER NOT NULL DEFAULT 0,
                courses_with_score INTEGER NOT NULL DEFAULT 0,
                courses_with_trend_data INTEGER NOT NULL DEFAULT 0,
                criteria_coverage_ratio REAL NOT NULL DEFAULT 0.0,
                performance_coverage_ratio REAL NOT NULL DEFAULT 0.0,
                popularity_coverage_ratio REAL NOT NULL DEFAULT 0.0,
                survey_coverage_ratio REAL NOT NULL DEFAULT 0.0,
                score_coverage_ratio REAL NOT NULL DEFAULT 0.0,
                trend_coverage_ratio REAL NOT NULL DEFAULT 0.0,
                overall_coverage_score REAL NOT NULL DEFAULT 0.0,
                missing_data_summary_json TEXT,
                recommendations_json TEXT,
                created_at TEXT
            )
        """,
        "data_readiness_assessments": """
            CREATE TABLE data_readiness_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                readiness_score REAL NOT NULL DEFAULT 0.0,
                readiness_level TEXT NOT NULL DEFAULT 'not_ready',
                criteria_coverage_score REAL NOT NULL DEFAULT 0.0,
                performance_coverage_score REAL NOT NULL DEFAULT 0.0,
                popularity_coverage_score REAL NOT NULL DEFAULT 0.0,
                survey_coverage_score REAL NOT NULL DEFAULT 0.0,
                trend_readiness_score REAL NOT NULL DEFAULT 0.0,
                validation_quality_score REAL NOT NULL DEFAULT 0.0,
                data_confidence_average REAL NOT NULL DEFAULT 0.0,
                blocking_issues_count INTEGER NOT NULL DEFAULT 0,
                warning_issues_count INTEGER NOT NULL DEFAULT 0,
                recommendation_summary TEXT,
                created_at TEXT
            )
        """,
        "missing_data_items": """
            CREATE TABLE missing_data_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester TEXT,
                faculty_id INTEGER,
                department_id INTEGER,
                missing_field TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'warning',
                required_for_decision INTEGER NOT NULL DEFAULT 1,
                message TEXT,
                suggested_action TEXT,
                detected_at TEXT,
                resolved_at TEXT,
                resolved_by TEXT
            )
        """,
        "data_validation_issues": """
            CREATE TABLE data_validation_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_id INTEGER,
                source_row_id INTEGER,
                course_id INTEGER,
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                field_name TEXT,
                issue_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'warning',
                message TEXT,
                suggested_action TEXT,
                raw_value TEXT,
                normalized_value TEXT,
                is_resolved INTEGER NOT NULL DEFAULT 0,
                resolved_by TEXT,
                resolved_at TEXT,
                created_at TEXT
            )
        """,
        "low_confidence_decision_flags": """
            CREATE TABLE low_confidence_decision_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER NOT NULL,
                course_decision_id INTEGER,
                course_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                confidence_score REAL NOT NULL DEFAULT 0.0,
                confidence_level TEXT NOT NULL DEFAULT 'low',
                reason TEXT,
                recommended_action TEXT,
                created_at TEXT,
                resolved_at TEXT
            )
        """,
        "data_collection_priorities": """
            CREATE TABLE data_collection_priorities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_type TEXT NOT NULL DEFAULT 'global',
                faculty_id INTEGER,
                department_id INTEGER,
                year INTEGER,
                priority_rank INTEGER NOT NULL DEFAULT 100,
                target_entity_type TEXT NOT NULL,
                course_id INTEGER,
                missing_field TEXT,
                priority_reason TEXT,
                expected_impact TEXT NOT NULL DEFAULT 'medium',
                suggested_action TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT,
                completed_at TEXT
            )
        """,
        "post_decision_outcomes": """
            CREATE TABLE post_decision_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER,
                course_decision_id INTEGER,
                course_id INTEGER NOT NULL,
                decision_year INTEGER NOT NULL,
                outcome_year INTEGER NOT NULL,
                final_status_applied INTEGER,
                actual_enrollment INTEGER,
                actual_capacity INTEGER,
                actual_fill_rate REAL,
                actual_success_rate REAL,
                actual_average_grade REAL,
                actual_survey_demand INTEGER,
                outcome_label TEXT,
                decision_was_effective INTEGER,
                notes TEXT,
                created_at TEXT
            )
        """,
        "fairness_metric_items": """
            CREATE TABLE fairness_metric_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fairness_report_id INTEGER NOT NULL,
                metric_key TEXT NOT NULL,
                metric_value REAL,
                metric_level TEXT NOT NULL DEFAULT 'warning',
                explanation TEXT,
                created_at TEXT
            )
        """,
        "ml_dataset_snapshots": """
            CREATE TABLE ml_dataset_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_name TEXT,
                scope_json TEXT,
                year INTEGER,
                feature_schema_version TEXT NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                feature_count INTEGER NOT NULL DEFAULT 0,
                target_column TEXT,
                coverage_score REAL NOT NULL DEFAULT 0.0,
                average_confidence_score REAL NOT NULL DEFAULT 0.0,
                missing_data_summary_json TEXT,
                created_at TEXT
            )
        """,
    }
    for table_name, ddl in tables.items():
        if not _table_exists(cur, table_name):
            cur.execute(ddl)
            changed["tables_created"] += 1

    for table_name, columns in {
        "data_coverage_reports": [
            ("scope_type", "TEXT NOT NULL DEFAULT 'global'"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("semester", "TEXT"),
            ("total_courses", "INTEGER NOT NULL DEFAULT 0"),
            ("courses_with_criteria", "INTEGER NOT NULL DEFAULT 0"),
            ("courses_with_performance", "INTEGER NOT NULL DEFAULT 0"),
            ("courses_with_popularity", "INTEGER NOT NULL DEFAULT 0"),
            ("courses_with_survey", "INTEGER NOT NULL DEFAULT 0"),
            ("courses_with_score", "INTEGER NOT NULL DEFAULT 0"),
            ("courses_with_trend_data", "INTEGER NOT NULL DEFAULT 0"),
            ("criteria_coverage_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("performance_coverage_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("popularity_coverage_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("survey_coverage_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("score_coverage_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("trend_coverage_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("overall_coverage_score", "REAL NOT NULL DEFAULT 0.0"),
            ("missing_data_summary_json", "TEXT"),
            ("recommendations_json", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "data_readiness_assessments": [
            ("scope_type", "TEXT NOT NULL DEFAULT 'global'"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("readiness_score", "REAL NOT NULL DEFAULT 0.0"),
            ("readiness_level", "TEXT NOT NULL DEFAULT 'not_ready'"),
            ("criteria_coverage_score", "REAL NOT NULL DEFAULT 0.0"),
            ("performance_coverage_score", "REAL NOT NULL DEFAULT 0.0"),
            ("popularity_coverage_score", "REAL NOT NULL DEFAULT 0.0"),
            ("survey_coverage_score", "REAL NOT NULL DEFAULT 0.0"),
            ("trend_readiness_score", "REAL NOT NULL DEFAULT 0.0"),
            ("validation_quality_score", "REAL NOT NULL DEFAULT 0.0"),
            ("data_confidence_average", "REAL NOT NULL DEFAULT 0.0"),
            ("blocking_issues_count", "INTEGER NOT NULL DEFAULT 0"),
            ("warning_issues_count", "INTEGER NOT NULL DEFAULT 0"),
            ("recommendation_summary", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "missing_data_items": [
            ("course_id", "INTEGER"),
            ("year", "INTEGER"),
            ("semester", "TEXT"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("missing_field", "TEXT"),
            ("severity", "TEXT NOT NULL DEFAULT 'warning'"),
            ("required_for_decision", "INTEGER NOT NULL DEFAULT 1"),
            ("message", "TEXT"),
            ("suggested_action", "TEXT"),
            ("detected_at", "TEXT"),
            ("resolved_at", "TEXT"),
            ("resolved_by", "TEXT"),
        ],
        "data_validation_issues": [
            ("source_type", "TEXT NOT NULL DEFAULT 'manual_entry'"),
            ("source_id", "INTEGER"),
            ("source_row_id", "INTEGER"),
            ("course_id", "INTEGER"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("field_name", "TEXT"),
            ("issue_type", "TEXT"),
            ("severity", "TEXT NOT NULL DEFAULT 'warning'"),
            ("message", "TEXT"),
            ("suggested_action", "TEXT"),
            ("raw_value", "TEXT"),
            ("normalized_value", "TEXT"),
            ("is_resolved", "INTEGER NOT NULL DEFAULT 0"),
            ("resolved_by", "TEXT"),
            ("resolved_at", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "low_confidence_decision_flags": [
            ("decision_run_id", "INTEGER"),
            ("course_decision_id", "INTEGER"),
            ("course_id", "INTEGER"),
            ("year", "INTEGER"),
            ("confidence_score", "REAL NOT NULL DEFAULT 0.0"),
            ("confidence_level", "TEXT NOT NULL DEFAULT 'low'"),
            ("reason", "TEXT"),
            ("recommended_action", "TEXT"),
            ("created_at", "TEXT"),
            ("resolved_at", "TEXT"),
        ],
        "data_collection_priorities": [
            ("scope_type", "TEXT NOT NULL DEFAULT 'global'"),
            ("faculty_id", "INTEGER"),
            ("department_id", "INTEGER"),
            ("year", "INTEGER"),
            ("priority_rank", "INTEGER NOT NULL DEFAULT 100"),
            ("target_entity_type", "TEXT NOT NULL DEFAULT 'course'"),
            ("course_id", "INTEGER"),
            ("missing_field", "TEXT"),
            ("priority_reason", "TEXT"),
            ("expected_impact", "TEXT NOT NULL DEFAULT 'medium'"),
            ("suggested_action", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'open'"),
            ("created_at", "TEXT"),
            ("completed_at", "TEXT"),
        ],
        "post_decision_outcomes": [
            ("decision_run_id", "INTEGER"),
            ("course_decision_id", "INTEGER"),
            ("course_id", "INTEGER"),
            ("decision_year", "INTEGER"),
            ("outcome_year", "INTEGER"),
            ("final_status_applied", "INTEGER"),
            ("actual_enrollment", "INTEGER"),
            ("actual_capacity", "INTEGER"),
            ("actual_fill_rate", "REAL"),
            ("actual_success_rate", "REAL"),
            ("actual_average_grade", "REAL"),
            ("actual_survey_demand", "INTEGER"),
            ("outcome_label", "TEXT"),
            ("decision_was_effective", "INTEGER"),
            ("notes", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "fairness_metric_items": [
            ("fairness_report_id", "INTEGER"),
            ("metric_key", "TEXT"),
            ("metric_value", "REAL"),
            ("metric_level", "TEXT NOT NULL DEFAULT 'warning'"),
            ("explanation", "TEXT"),
            ("created_at", "TEXT"),
        ],
        "ml_dataset_snapshots": [
            ("snapshot_name", "TEXT"),
            ("scope_json", "TEXT"),
            ("year", "INTEGER"),
            ("feature_schema_version", "TEXT"),
            ("sample_count", "INTEGER NOT NULL DEFAULT 0"),
            ("feature_count", "INTEGER NOT NULL DEFAULT 0"),
            ("target_column", "TEXT"),
            ("coverage_score", "REAL NOT NULL DEFAULT 0.0"),
            ("average_confidence_score", "REAL NOT NULL DEFAULT 0.0"),
            ("missing_data_summary_json", "TEXT"),
            ("created_at", "TEXT"),
        ],
    }.items():
        changed["columns_added"] += _ensure_columns(cur, table_name, columns)

    index_ddls = [
        "CREATE INDEX IF NOT EXISTS ix_data_coverage_scope ON data_coverage_reports (scope_type, faculty_id, department_id, year, semester)",
        "CREATE INDEX IF NOT EXISTS ix_data_readiness_scope ON data_readiness_assessments (scope_type, faculty_id, department_id, year)",
        "CREATE INDEX IF NOT EXISTS ix_missing_data_scope ON missing_data_items (year, faculty_id, department_id, severity)",
        "CREATE INDEX IF NOT EXISTS ix_data_validation_scope ON data_validation_issues (year, severity, is_resolved)",
        "CREATE INDEX IF NOT EXISTS ix_low_confidence_flags_scope ON low_confidence_decision_flags (year, confidence_level, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_data_collection_scope ON data_collection_priorities (year, status, priority_rank)",
        "CREATE INDEX IF NOT EXISTS ix_post_decision_outcomes_scope ON post_decision_outcomes (decision_year, outcome_year, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_fairness_metric_items_report ON fairness_metric_items (fairness_report_id, metric_key)",
        "CREATE INDEX IF NOT EXISTS ix_ml_dataset_snapshots_year ON ml_dataset_snapshots (year, feature_schema_version)",
    ]
    for ddl in index_ddls:
        cur.execute(ddl)
        changed["indexes_created"] += 1
    if commit:
        conn.commit()
    return changed


def ensure_reporting_schema(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """
    Raporlama icin gereken tum kritik tablolari synchronize eder.
    """
    if not _schema_mutation_allowed():
        message = "Runtime schema compatibility mutation config ile kapalı."
        _log_schema_compat(conn, action_type="skip", table_name="schema_compat", success=True, message=message)
        return {
            "schema_compat": {
                "tables_created": 0,
                "columns_added": 0,
                "indexes_created": 0,
                "mutation_allowed": 0,
            }
        }

    result: dict[str, dict[str, int]] = {
        "architecture": ensure_architecture_schema(conn),
    }
    _log_schema_compat_result(conn, "architecture", result["architecture"])

    for name, ensure_func in [
        ("ders", ensure_ders_code_schema),
        ("havuz", ensure_havuz_semester_schema),
        ("skor", ensure_skor_schema),
        ("criteria", ensure_criteria_import_schema),
        ("survey", ensure_survey_import_schema),
        ("decision_governance", ensure_decision_governance_schema),
        ("pool_state_governance", ensure_pool_state_governance_schema),
        ("import_governance", ensure_import_governance_schema),
    ]:
        try:
            result[name] = ensure_func(conn)  # type: ignore[assignment]
            _log_schema_compat_result(conn, name, result[name])
        except Exception as exc:
            _log_schema_compat(
                conn,
                action_type="error",
                table_name=name,
                success=False,
                message=f"{type(exc).__name__}: {exc}",
            )
            raise
    try:
        from app.services.yearly_workflow import ensure_yearly_workflow_schema

        result["workflow"] = ensure_yearly_workflow_schema(conn)  # type: ignore[assignment]
        _log_schema_compat_result(conn, "workflow", result["workflow"])
    except Exception:
        # Workflow semasi kritik raporlama akisini bloklamasin.
        result["workflow"] = {
            "tables_created": 0,
            "indexes_created": 0,
        }
        _log_schema_compat(
            conn,
            action_type="error",
            table_name="workflow",
            success=False,
            message="Workflow şeması hazırlanamadı; ana raporlama akışı bloklanmadı.",
        )
    result["criteria_completion_governance"] = ensure_criteria_completion_governance_schema(conn)  # type: ignore[assignment]
    _log_schema_compat_result(conn, "criteria_completion_governance", result["criteria_completion_governance"])
    result["ml_governance"] = ensure_ml_governance_schema(conn)  # type: ignore[assignment]
    _log_schema_compat_result(conn, "ml_governance", result["ml_governance"])
    result["algorithm_governance"] = ensure_algorithm_governance_schema(conn)  # type: ignore[assignment]
    _log_schema_compat_result(conn, "algorithm_governance", result["algorithm_governance"])
    result["ahp_governance"] = ensure_ahp_governance_schema(conn)  # type: ignore[assignment]
    _log_schema_compat_result(conn, "ahp_governance", result["ahp_governance"])
    result["semester_planning"] = ensure_semester_planning_schema(conn)  # type: ignore[assignment]
    _log_schema_compat_result(conn, "semester_planning", result["semester_planning"])
    result["data_quality"] = ensure_data_quality_schema(conn)  # type: ignore[assignment]
    _log_schema_compat_result(conn, "data_quality", result["data_quality"])
    conn.commit()
    return result

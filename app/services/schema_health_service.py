# -*- coding: utf-8 -*-
"""Salt-okunur veritabanı şema sağlık kontrolleri."""

from __future__ import annotations

import os
import sqlite3
from app.services.db import get_raw_connection
from contextlib import contextmanager
from typing import Any, Iterator

import sqlalchemy as sa

from app.core.config import AppConfig, load_app_config
from app.core.database_policy import runtime_schema_mutation_allowed
from app.db.backend import is_sqlite_connection, is_sqlite_url


CORE_REQUIRED_TABLES = {
    "ders",
    "fakulte",
    "bolum",
    "ders_kriterleri",
    "havuz",
    "skor",
    "schema_compat_logs",
    "sql_console_audit_logs",
}

CORE_REQUIRED_COLUMNS = {
    "ders": {"ders_id", "ad"},
    "ders_kriterleri": {"ders_id", "yil", "donem"},
    "havuz": {"ders_id", "yil", "statu"},
    "schema_compat_logs": {"action_type", "table_name", "success", "created_at"},
    "sql_console_audit_logs": {"sql_text", "statement_type", "success", "executed_at"},
}


def _unwrap_sqlite_connection(conn: Any) -> Any:
    """SQLAlchemy raw connection proxy nesnelerinden gerçek sqlite bağlantısını al."""
    if is_sqlite_connection(conn):
        return conn
    for attr in ("driver_connection", "dbapi_connection", "connection"):
        try:
            candidate = getattr(conn, attr, None)
        except Exception:
            candidate = None
        if is_sqlite_connection(candidate):
            return candidate
    return conn


@contextmanager
def _managed_connection(
    conn: sqlite3.Connection | Any | None,
    db_path: str | None,
    config: AppConfig | None = None,
) -> Iterator[Any]:
    if conn is not None:
        yield _unwrap_sqlite_connection(conn)
        return
    cfg = config or load_app_config()
    if not is_sqlite_url(cfg.database_url):
        from app.db.database import get_engine

        with get_engine().connect() as connection:
            yield connection
        return
    path = db_path or cfg.sqlite_db_path
    sqlite_conn = sqlite3.connect(path)
    try:
        yield sqlite_conn
    finally:
        sqlite_conn.close()


def _table_names(conn: Any) -> set[str]:
    if not is_sqlite_connection(conn):
        return set(sa.inspect(conn).get_table_names())
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {str(row[0]) for row in cur.fetchall()}


def _column_names(conn: Any, table_name: str) -> set[str]:
    if not is_sqlite_connection(conn):
        if table_name not in _table_names(conn):
            return set()
        return {str(col["name"]) for col in sa.inspect(conn).get_columns(table_name)}
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(row[1]) for row in cur.fetchall()}


def check_required_tables(conn: sqlite3.Connection) -> dict[str, Any]:
    existing = _table_names(conn)
    missing = sorted(CORE_REQUIRED_TABLES - existing)
    return {"ok": not missing, "existing_count": len(existing), "missing_tables": missing}


def check_required_columns(conn: sqlite3.Connection) -> dict[str, Any]:
    existing_tables = _table_names(conn)
    missing: dict[str, list[str]] = {}
    for table_name, required_columns in CORE_REQUIRED_COLUMNS.items():
        if table_name not in existing_tables:
            missing[table_name] = sorted(required_columns)
            continue
        existing_columns = _column_names(conn, table_name)
        absent = sorted(required_columns - existing_columns)
        if absent:
            missing[table_name] = absent
    return {"ok": not missing, "missing_columns": missing}


def check_alembic_version(conn: Any) -> dict[str, Any]:
    tables = _table_names(conn)
    if "alembic_version" not in tables:
        return {"ok": False, "version": None, "message": "alembic_version tablosu bulunamadı."}
    if is_sqlite_connection(conn):
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
        row = cur.fetchone()
        version = str(row[0]) if row and row[0] else None
    else:
        row = conn.execute(sa.text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
        version = str(row[0]) if row and row[0] else None
    return {"ok": bool(version), "version": version}


def check_schema_compat_status(conn: sqlite3.Connection, config: AppConfig | None = None) -> dict[str, Any]:
    cfg = config or load_app_config()
    tables = _table_names(conn)
    logs_available = "schema_compat_logs" in tables
    latest_logs: list[dict[str, Any]] = []
    if logs_available:
        query = """
        SELECT action_type, table_name, column_name, index_name, success, message, created_at
        FROM schema_compat_logs
        ORDER BY id DESC
        LIMIT 10
        """
        if is_sqlite_connection(conn):
            rows = conn.cursor().execute(query).fetchall()
        else:
            rows = conn.execute(sa.text(query)).fetchall()
        latest_logs = [
            {
                "action_type": row[0],
                "table_name": row[1],
                "column_name": row[2],
                "index_name": row[3],
                "success": bool(row[4]),
                "message": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]
    return {
        "enabled": cfg.enable_schema_compat,
        "runtime_mutation_allowed": runtime_schema_mutation_allowed(cfg),
        "logs_available": logs_available,
        "latest_logs": latest_logs,
    }


def compare_models_to_database(conn: sqlite3.Connection) -> dict[str, Any]:
    try:
        from app.db.models import Base
    except Exception as exc:
        return {"ok": False, "missing_model_tables": [], "message": f"Model metadata okunamadı: {exc}"}
    model_tables = set(Base.metadata.tables.keys())
    existing = _table_names(conn)
    missing = sorted(model_tables - existing)
    return {"ok": not missing, "model_table_count": len(model_tables), "missing_model_tables": missing[:50]}


def check_schema_health(
    conn: sqlite3.Connection | None = None,
    db_path: str | None = None,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    cfg = config or load_app_config()
    path = db_path or cfg.sqlite_db_path
    with _managed_connection(conn, path, cfg) as active_conn:
        tables = check_required_tables(active_conn)
        columns = check_required_columns(active_conn)
        alembic = check_alembic_version(active_conn)
        compat = check_schema_compat_status(active_conn, cfg)
        models = compare_models_to_database(active_conn)
    warnings: list[str] = []
    if not tables["ok"]:
        warnings.append("Eksik kritik tablolar var.")
    if not columns["ok"]:
        warnings.append("Eksik kritik kolonlar var.")
    if cfg.environment == "production" and compat["runtime_mutation_allowed"]:
        warnings.append("Production ortamında runtime schema mutation açık görünüyor.")
    return {
        "db_path": os.path.abspath(path),
        "db_exists": os.path.exists(path) if is_sqlite_url(cfg.database_url) else True,
        "database_url": cfg.database_url,
        "database_backend": cfg.db_backend,
        "schema_ok": bool(tables["ok"] and columns["ok"]),
        "required_tables": tables,
        "required_columns": columns,
        "alembic": alembic,
        "schema_compat": compat,
        "model_comparison": models,
        "warnings": warnings,
    }


def generate_schema_health_report(
    conn: sqlite3.Connection | None = None,
    db_path: str | None = None,
    config: AppConfig | None = None,
) -> str:
    health = check_schema_health(conn=conn, db_path=db_path, config=config)
    lines = [
        f"DB yolu: {health['db_path']}",
        f"DB mevcut: {'Evet' if health['db_exists'] else 'Hayır'}",
        f"Şema sağlıklı: {'Evet' if health['schema_ok'] else 'Hayır'}",
        f"Alembic version: {health['alembic'].get('version') or 'Yok'}",
        f"Runtime schema mutation: {'Açık' if health['schema_compat'].get('runtime_mutation_allowed') else 'Kapalı'}",
    ]
    for warning in health.get("warnings") or []:
        lines.append(f"Uyarı: {warning}")
    return "\n".join(lines)

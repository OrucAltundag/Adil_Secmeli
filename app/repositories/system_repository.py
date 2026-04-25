# -*- coding: utf-8 -*-
"""Sistem sağlık kontrolleri için repository."""

from __future__ import annotations

import os
import sqlite3
from typing import Any


class SystemRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def ping(self) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1")
        row = cur.fetchone()
        return bool(row and int(row[0]) == 1)

    def table_count(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        row = cur.fetchone()
        return int(row[0] or 0) if row else 0

    def database_info(self, db_path: str | None = None) -> dict[str, Any]:
        path = os.path.abspath(db_path) if db_path else None
        return {
            "db_path": path,
            "exists": bool(path and os.path.exists(path)),
            "table_count": self.table_count(),
            "connection_ok": self.ping(),
        }

    def latest_schema_compat_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_compat_logs' LIMIT 1"
        )
        if not cur.fetchone():
            return []
        cur.execute(
            """
            SELECT id, action_type, table_name, column_name, index_name, success, message, created_at
            FROM schema_compat_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [
            {
                "id": row[0],
                "action_type": row[1],
                "table_name": row[2],
                "column_name": row[3],
                "index_name": row[4],
                "success": bool(row[5]),
                "message": row[6],
                "created_at": row[7],
            }
            for row in cur.fetchall()
        ]

    def latest_sql_console_audit_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sql_console_audit_logs' LIMIT 1"
        )
        if not cur.fetchone():
            return []
        cur.execute(
            """
            SELECT id, user_id, sql_text, statement_type, success, error_message, row_count, executed_at
            FROM sql_console_audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "sql_text": row[2],
                "statement_type": row[3],
                "success": bool(row[4]),
                "error_message": row[5],
                "row_count": row[6],
                "executed_at": row[7],
            }
            for row in cur.fetchall()
        ]

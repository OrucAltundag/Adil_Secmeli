# -*- coding: utf-8 -*-
"""UI tablo görüntüleme için servis katmanı."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.core.result import ServiceResult
from app.repositories.report_repository import ReportRepository


class ReportTableService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo = ReportRepository(conn)

    def list_tables(self) -> ServiceResult:
        return ServiceResult.ok(self.repo.list_tables())

    def table_head(self, table: str, limit: int = 1000) -> ServiceResult:
        cols, rows = self.repo.table_head(table, limit=limit)
        return ServiceResult.ok({"columns": cols, "rows": rows})

    @staticmethod
    def statement_type(query: str) -> str:
        stripped = (query or "").strip().split()
        return stripped[0].upper() if stripped else "UNKNOWN"

    @classmethod
    def is_dangerous_sql(cls, query: str) -> bool:
        return cls.statement_type(query) in {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE"}

    def _audit_sql_console(
        self,
        *,
        query: str,
        statement_type: str,
        success: bool,
        user_id: str | None = None,
        error_message: str | None = None,
        row_count: int | None = None,
    ) -> None:
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO sql_console_audit_logs (
                    user_id, sql_text, statement_type, success, error_message, row_count, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (user_id, query, statement_type, 1 if success else 0, error_message, row_count),
            )
            self.conn.commit()
        except Exception:
            return

    def run_admin_sql(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        *,
        user_id: str | None = None,
    ) -> ServiceResult:
        statement_type = self.statement_type(query)
        cur = self.conn.cursor()
        try:
            cur.execute(query, params)
            if statement_type == "SELECT":
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description] if cur.description else []
                self._audit_sql_console(
                    query=query,
                    statement_type=statement_type,
                    success=True,
                    user_id=user_id,
                    row_count=len(rows or []),
                )
                return ServiceResult.ok({"columns": cols, "rows": rows})
            row_count = cur.rowcount if cur.rowcount is not None else None
            self.conn.commit()
            self._audit_sql_console(
                query=query,
                statement_type=statement_type,
                success=True,
                user_id=user_id,
                row_count=row_count,
            )
            return ServiceResult.ok(message="Sorgu başarıyla çalıştı.")
        except Exception as exc:
            self._audit_sql_console(
                query=query,
                statement_type=statement_type,
                success=False,
                user_id=user_id,
                error_message=str(exc),
            )
            raise

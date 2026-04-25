# -*- coding: utf-8 -*-
"""Tablo görüntüleme ve raporlama için düşük seviyeli repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts, validate_identifier


class ReportRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_tables(self) -> list[str]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [str(row[0]) for row in cur.fetchall()]

    def table_head(self, table: str, limit: int = 1000) -> tuple[list[str], list[Any]]:
        safe_table = validate_identifier(table)
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {safe_table} LIMIT ?", (int(limit),))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, rows

    def table_count(self, table: str) -> int:
        safe_table = validate_identifier(table)
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) AS count FROM {safe_table}")
        row = cur.fetchone()
        return int(row[0] or 0) if row else 0

    def select_query(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(query, params)
        return fetch_all_dicts(cur)

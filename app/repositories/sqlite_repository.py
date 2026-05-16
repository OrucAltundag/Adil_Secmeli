# -*- coding: utf-8 -*-
"""Sağlık kontrolleri için güvenli SQLite repository adapterı."""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from app.db.session import open_sqlite_connection


def quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


class SQLiteRepository:
    def __init__(self, db_path: str):
        self.db_path = str(Path(db_path))

    @contextlib.contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = open_sqlite_connection(self.db_path, row_factory=True)
        try:
            yield conn
        finally:
            conn.close()

    def table_names(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            return [str(row[0]) for row in rows]

    def table_count(self) -> int:
        return len(self.table_names())

    def columns(self, table_name: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
            return [
                {
                    "cid": row[0],
                    "name": str(row[1]),
                    "type": str(row[2] or ""),
                    "notnull": bool(row[3]),
                    "default": row[4],
                    "pk": bool(row[5]),
                }
                for row in rows
            ]

    def row_count(self, table_name: str) -> int:
        with self.connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}").fetchone()
            return int(row[0] if row else 0)

    def execute_scalar(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else None

    def execute_rows(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute(sql, params).fetchall())

    def integrity_check(self) -> list[str]:
        rows = self.execute_rows("PRAGMA integrity_check")
        return [str(row[0]) for row in rows]

    def foreign_key_check(self) -> list[dict[str, Any]]:
        rows = self.execute_rows("PRAGMA foreign_key_check")
        return [dict(row) for row in rows]

    def write_permission_check(self) -> None:
        with self.connect() as conn:
            conn.execute("BEGIN")
            try:
                conn.execute("CREATE TEMP TABLE IF NOT EXISTS health_write_probe (id INTEGER)")
                conn.execute("INSERT INTO health_write_probe (id) VALUES (1)")
                conn.execute("DROP TABLE health_write_probe")
            finally:
                conn.rollback()

    def profile_tables(self, limit: int = 40) -> list[dict[str, Any]]:
        profile: list[dict[str, Any]] = []
        for table_name in self.table_names()[:limit]:
            columns = self.columns(table_name)
            profile.append(
                {
                    "table": table_name,
                    "row_count": self.row_count(table_name),
                    "column_count": len(columns),
                    "columns": [column["name"] for column in columns],
                }
            )
        return profile

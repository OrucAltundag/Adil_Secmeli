# -*- coding: utf-8 -*-
"""Sağlık kontrolleri için salt-okunur SQLite repository.

UI/health katmanı doğrudan ``sqlite3`` kullanmasın diye sorgular bu sınıf
arkasında toplanır. Tablo/kolon adları :func:`validate_identifier` ile
doğrulanır; böylece dinamik SQL'de injection riski azalır.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts, validate_identifier


class SqliteRepository:
    """sqlite3 bağlantısı üzerinde güvenli okuma yardımcıları."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -- Genel sorgu yardımcıları -------------------------------------------------
    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    def fetchall_dicts(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return fetch_all_dicts(cur)

    def scalar(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        row = self.fetchone(sql, params)
        return row[0] if row else None

    # -- Şema keşfi ---------------------------------------------------------------
    def table_names(self) -> list[str]:
        rows = self.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [str(r[0]) for r in rows]

    def table_exists(self, name: str) -> bool:
        row = self.fetchone(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (str(name),),
        )
        return row is not None

    def table_count(self) -> int:
        return int(
            self.scalar(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
            or 0
        )

    def column_names(self, table: str) -> list[str]:
        safe = validate_identifier(table)
        rows = self.fetchall(f"PRAGMA table_info({safe})")
        return [str(r[1]) for r in rows]

    def column_info(self, table: str) -> list[dict[str, Any]]:
        safe = validate_identifier(table)
        rows = self.fetchall(f"PRAGMA table_info({safe})")
        return [
            {"name": r[1], "type": r[2], "notnull": bool(r[3]), "pk": bool(r[5])}
            for r in rows
        ]

    def row_count(self, table: str) -> int:
        safe = validate_identifier(table)
        return int(self.scalar(f"SELECT COUNT(*) FROM {safe}") or 0)

    def null_count(self, table: str, column: str) -> int:
        safe_t = validate_identifier(table)
        safe_c = validate_identifier(column)
        return int(
            self.scalar(
                f"SELECT COUNT(*) FROM {safe_t} "
                f"WHERE {safe_c} IS NULL OR TRIM(CAST({safe_c} AS TEXT)) = ''"
            )
            or 0
        )

    def negative_count(self, table: str, column: str) -> int:
        safe_t = validate_identifier(table)
        safe_c = validate_identifier(column)
        return int(
            self.scalar(
                f"SELECT COUNT(*) FROM {safe_t} "
                f"WHERE {safe_c} IS NOT NULL AND CAST({safe_c} AS REAL) < 0"
            )
            or 0
        )

    def duplicate_groups(self, table: str, columns: tuple[str, ...]) -> int:
        safe_t = validate_identifier(table)
        safe_cols = ", ".join(validate_identifier(c) for c in columns)
        sql = (
            f"SELECT COUNT(*) FROM (SELECT {safe_cols}, COUNT(*) c "
            f"FROM {safe_t} GROUP BY {safe_cols} HAVING c > 1)"
        )
        return int(self.scalar(sql) or 0)

    def numeric_values(self, table: str, column: str, limit: int = 5000) -> list[float]:
        safe_t = validate_identifier(table)
        safe_c = validate_identifier(column)
        rows = self.fetchall(
            f"SELECT CAST({safe_c} AS REAL) FROM {safe_t} "
            f"WHERE {safe_c} IS NOT NULL LIMIT ?",
            (int(limit),),
        )
        out: list[float] = []
        for r in rows:
            try:
                out.append(float(r[0]))
            except (TypeError, ValueError):
                continue
        return out

    def preview(self, table: str, limit: int = 10) -> tuple[list[str], list[tuple[Any, ...]]]:
        safe_t = validate_identifier(table)
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {safe_t} LIMIT ?", (int(limit),))
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchall()

    # -- PRAGMA bütünlük kontrolleri ---------------------------------------------
    def integrity_check(self) -> list[str]:
        rows = self.fetchall("PRAGMA integrity_check")
        return [str(r[0]) for r in rows]

    def foreign_key_check(self) -> list[tuple[Any, ...]]:
        return self.fetchall("PRAGMA foreign_key_check")

    def pragma(self, name: str) -> Any:
        safe = validate_identifier(name)
        return self.scalar(f"PRAGMA {safe}")

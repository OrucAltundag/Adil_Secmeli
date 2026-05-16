# -*- coding: utf-8 -*-
"""Sağlık kontrolleri için özelleşmiş salt-okunur SQLite repository.

:class:`SqliteRepository` üzerine sağlık odaklı yardımcılar ekler
(bağlantı süresi, integrity/fk özetleri, kritik tablo varlığı). Yazma
yapmaz; gerçek veriyi değiştirmez.
"""

from __future__ import annotations

import sqlite3
import time
from typing import Any

from app.repositories.sqlite_repository import SqliteRepository


class SqliteHealthRepository(SqliteRepository):
    """Sağlık kontrollerinin kullandığı okuma yardımcıları."""

    def ping_ms(self) -> float:
        start = time.perf_counter()
        self.scalar("SELECT 1")
        return (time.perf_counter() - start) * 1000.0

    def integrity_summary(self) -> dict[str, Any]:
        rows = self.integrity_check()
        ok = rows == ["ok"]
        return {"ok": ok, "issues": [] if ok else rows[:50]}

    def foreign_key_summary(self) -> dict[str, Any]:
        violations = self.foreign_key_check()
        return {
            "ok": not violations,
            "violation_count": len(violations),
            "sample": [tuple(v) for v in violations[:15]],
        }

    def missing_tables(self, expected: tuple[str, ...]) -> list[str]:
        existing = set(self.table_names())
        return sorted(set(expected) - existing)

    def missing_columns(
        self, expected: dict[str, tuple[str, ...]]
    ) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        tables = set(self.table_names())
        for table, cols in expected.items():
            if table not in tables:
                out[table] = sorted(cols)
                continue
            have = set(self.column_names(table))
            absent = sorted(set(cols) - have)
            if absent:
                out[table] = absent
        return out

    def safe_write_probe(self) -> bool:
        """TEMP tablo ile yazma iznini test eder; gerçek veri değişmez."""

        try:
            self.conn.execute(
                "CREATE TEMP TABLE _hp_probe (id INTEGER PRIMARY KEY, v TEXT)"
            )
            self.conn.execute("INSERT INTO _hp_probe (v) VALUES ('p')")
            value = self.conn.execute(
                "SELECT v FROM _hp_probe LIMIT 1"
            ).fetchone()[0]
            self.conn.execute("DROP TABLE _hp_probe")
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            return value == "p"
        except sqlite3.Error:
            return False

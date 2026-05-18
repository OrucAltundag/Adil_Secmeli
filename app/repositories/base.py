# -*- coding: utf-8 -*-
"""Repository ortak yardımcıları."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    if columns:
        return {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
    return None


def fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    cols = [d[0] for d in cur.description] if cur.description else []
    return [row_to_dict(row, cols) or {} for row in cur.fetchall()]


def validate_identifier(name: str) -> str:
    if not SAFE_IDENTIFIER_RE.match(str(name or "")):
        raise ValueError(f"Geçersiz tablo/kolon adı: {name}")
    return str(name)

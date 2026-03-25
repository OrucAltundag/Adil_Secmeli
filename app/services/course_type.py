# -*- coding: utf-8 -*-
"""
Course-type compatibility helpers.

Different databases may keep the course type in different columns
(`DersTipi`, `ders_tipi`, `tip`, `tur`). This module provides a single
rule for elective/required detection and SQL predicate generation.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable


COURSE_TYPE_COLUMNS: tuple[str, ...] = ("DersTipi", "ders_tipi", "tip", "tur")
ELECTIVE_KEYWORDS: tuple[str, ...] = ("secmeli", "elective")
REQUIRED_KEYWORDS: tuple[str, ...] = ("zorunlu", "mandatory", "required", "core", "mecburi")

# Keep this mapping ASCII-safe in source using unicode escapes.
_TR_ASCII_MAP: tuple[tuple[str, str], ...] = (
    ("\u00e7", "c"),  # c
    ("\u00c7", "c"),  # C
    ("\u011f", "g"),  # g
    ("\u011e", "g"),  # G
    ("\u0131", "i"),  # i
    ("\u0130", "i"),  # I
    ("\u00f6", "o"),  # o
    ("\u00d6", "o"),  # O
    ("\u015f", "s"),  # s
    ("\u015e", "s"),  # S
    ("\u00fc", "u"),  # u
    ("\u00dc", "u"),  # U
)


def _normalize_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    for src, dst in _TR_ASCII_MAP:
        text = text.replace(src, dst)
    return text


def is_elective_value(value: str | None) -> bool:
    normalized = _normalize_text(value)
    return any(keyword in normalized for keyword in ELECTIVE_KEYWORDS)


def is_required_value(value: str | None) -> bool:
    normalized = _normalize_text(value)
    return any(keyword in normalized for keyword in REQUIRED_KEYWORDS)


def get_existing_type_columns(cur: sqlite3.Cursor, table_name: str = "ders") -> list[str]:
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = {str(row[1]) for row in cur.fetchall()}
    return [col for col in COURSE_TYPE_COLUMNS if col in cols]


def build_course_type_expr(cur: sqlite3.Cursor, alias: str = "d") -> str:
    cols = get_existing_type_columns(cur)
    if not cols:
        return "''"

    parts = [f"COALESCE({alias}.\"{col}\", '')" for col in cols]
    if len(parts) == 1:
        return parts[0]

    when_clauses = " ".join(f"WHEN TRIM({part}) <> '' THEN {part}" for part in parts)
    return f"(CASE {when_clauses} ELSE '' END)"


def _build_normalized_sql_text_expr(expr: str) -> str:
    normalized = f"LOWER({expr})"
    for src, dst in _TR_ASCII_MAP:
        normalized = f"REPLACE({normalized}, '{src}', '{dst}')"
    return normalized


def build_elective_predicate(cur: sqlite3.Cursor, alias: str = "d") -> str:
    type_expr = build_course_type_expr(cur=cur, alias=alias)
    if type_expr == "''":
        # Type column is unavailable; strict rule: nothing is accepted as elective.
        return "0=1"
    normalized_expr = _build_normalized_sql_text_expr(type_expr)
    return (
        "("
        f"{normalized_expr} LIKE '%secmeli%'"
        f" OR {normalized_expr} LIKE '%elective%'"
        ")"
    )


def build_required_predicate(cur: sqlite3.Cursor, alias: str = "d") -> str:
    type_expr = build_course_type_expr(cur=cur, alias=alias)
    if type_expr == "''":
        return "0=1"
    normalized_expr = _build_normalized_sql_text_expr(type_expr)
    return (
        "("
        f"{normalized_expr} LIKE '%zorunlu%'"
        f" OR {normalized_expr} LIKE '%mandatory%'"
        f" OR {normalized_expr} LIKE '%required%'"
        f" OR {normalized_expr} LIKE '%core%'"
        f" OR {normalized_expr} LIKE '%mecburi%'"
        ")"
    )


def filter_elective_course_ids(cur: sqlite3.Cursor, course_ids: Iterable[int]) -> set[int]:
    normalized_ids = sorted({int(course_id) for course_id in course_ids if course_id is not None})
    if not normalized_ids:
        return set()

    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    if elective_predicate == "0=1":
        return set()

    out: set[int] = set()
    chunk_size = 900
    for idx in range(0, len(normalized_ids), chunk_size):
        chunk = normalized_ids[idx : idx + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        cur.execute(
            f"""
            SELECT d.ders_id
            FROM ders d
            WHERE d.ders_id IN ({placeholders})
              AND {elective_predicate}
            """,
            tuple(chunk),
        )
        out.update(int(row[0]) for row in cur.fetchall() if row and row[0] is not None)
    return out

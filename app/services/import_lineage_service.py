# -*- coding: utf-8 -*-
"""Alan bazli veri kokeni ve manuel override servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_import_governance_schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_value_source(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    field_name: str,
    value: Any,
    source_type: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
    source_import_batch_id: int | None = None,
    source_row_id: int | None = None,
    is_locked: bool = False,
    created_by: str | None = None,
    deactivate_existing: bool = True,
) -> int:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    if deactivate_existing:
        cur.execute(
            """
            UPDATE criteria_value_sources
            SET is_active = 0
            WHERE course_id = ? AND year = ? AND field_name = ? AND is_active = 1
            """,
            (int(course_id), int(year), field_name),
        )
    value_text = "" if value is None else str(value)
    try:
        value_numeric = None if value is None or str(value).strip() == "" else float(value)
    except Exception:
        value_numeric = None
    cur.execute(
        """
        INSERT INTO criteria_value_sources (
            course_id, year, faculty_id, department_id, field_name, value_text, value_numeric,
            source_type, source_import_batch_id, source_row_id, is_locked, is_active,
            created_by, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            int(course_id),
            int(year),
            int(faculty_id) if faculty_id is not None else None,
            int(department_id) if department_id is not None else None,
            field_name,
            value_text,
            value_numeric,
            source_type,
            int(source_import_batch_id) if source_import_batch_id is not None else None,
            int(source_row_id) if source_row_id is not None else None,
            1 if is_locked else 0,
            created_by,
            _now(),
        ),
    )
    return int(cur.lastrowid)


def apply_manual_override(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    field_name: str,
    value: Any,
    override_reason: str,
    user: str | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    if not str(override_reason or "").strip():
        raise ValueError("Manuel override icin gerekce zorunludur.")
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id
        FROM criteria_value_sources
        WHERE course_id = ? AND year = ? AND field_name = ? AND is_active = 1
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(course_id), int(year), field_name),
    )
    previous = cur.fetchone()
    previous_id = int(previous[0]) if previous and previous[0] is not None else None
    new_id = record_value_source(
        conn=conn,
        course_id=course_id,
        year=year,
        field_name=field_name,
        value=value,
        source_type="override",
        faculty_id=faculty_id,
        department_id=department_id,
        created_by=user,
        deactivate_existing=True,
    )
    if previous_id is not None:
        cur.execute(
            """
            UPDATE criteria_value_sources
            SET overridden_by_source_id = ?, override_reason = ?
            WHERE id = ?
            """,
            (int(new_id), override_reason, int(previous_id)),
        )
    cur.execute(
        """
        UPDATE criteria_value_sources
        SET override_reason = ?
        WHERE id = ?
        """,
        (override_reason, int(new_id)),
    )
    return {"ok": True, "new_source_id": new_id, "previous_source_id": previous_id}


def list_value_sources(
    conn: sqlite3.Connection,
    course_id: int | None = None,
    year: int | None = None,
    field_name: str | None = None,
    active_only: bool = True,
    limit: int = 500,
) -> list[dict[str, Any]]:
    ensure_import_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if course_id is not None:
        where.append("course_id = ?")
        params.append(int(course_id))
    if year is not None:
        where.append("year = ?")
        params.append(int(year))
    if field_name:
        where.append("field_name = ?")
        params.append(field_name)
    if active_only:
        where.append("is_active = 1")
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT *
        FROM criteria_value_sources
        WHERE {' AND '.join(where)}
        ORDER BY course_id, year, field_name, id DESC
        LIMIT ?
        """,
        tuple(params + [int(limit)]),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    return [{key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else {} for row in rows]

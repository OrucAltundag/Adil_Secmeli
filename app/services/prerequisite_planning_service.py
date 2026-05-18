# -*- coding: utf-8 -*-
"""On kosul iliskileri ve pedagojik donem sirasi kontrolleri."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema
from app.services.course_semester_availability_service import normalize_semester

SEMESTER_ORDER = {"fall": 1, "spring": 2, "unassigned": 99}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}


def _fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    cols = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, cols) or {} for row in cur.fetchall()]


def create_prerequisite(
    conn: sqlite3.Connection,
    course_id: int,
    prerequisite_course_id: int,
    prerequisite_type: str = "hard",
    relation_note: str | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO course_prerequisites
            (course_id, prerequisite_course_id, prerequisite_type, relation_note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(course_id), int(prerequisite_course_id), prerequisite_type, relation_note, now, now),
    )
    cur.execute("SELECT * FROM course_prerequisites WHERE id = ?", (int(cur.lastrowid),))
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description]) or {}


def get_prerequisites(conn: sqlite3.Connection, course_id: int | None = None) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if course_id is not None:
        where.append("course_id = ?")
        params.append(int(course_id))
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM course_prerequisites WHERE {' AND '.join(where)} ORDER BY course_id, prerequisite_course_id", tuple(params))
    return _fetch_all_dicts(cur)


def check_prerequisite_order(assignments: list[dict[str, Any]], prerequisites: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    assignment_map: dict[int, str] = {}
    for item in assignments:
        if str(item.get("assigned_semester")) in {"fall", "spring"}:
            assignment_map[int(item["course_id"])] = normalize_semester(str(item.get("assigned_semester")))
    violations: list[dict[str, Any]] = []
    for prereq in prerequisites or []:
        course_id = int(prereq.get("course_id"))
        pre_id = int(prereq.get("prerequisite_course_id"))
        if course_id not in assignment_map or pre_id not in assignment_map:
            continue
        c_sem = assignment_map[course_id]
        p_sem = assignment_map[pre_id]
        if SEMESTER_ORDER[p_sem] > SEMESTER_ORDER[c_sem]:
            ptype = str(prereq.get("prerequisite_type") or "hard")
            severity = "error" if ptype == "hard" else "warning"
            violations.append(
                {
                    "course_id": course_id,
                    "constraint_type": "prerequisite",
                    "severity": severity,
                    "message": f"{course_id} dersi, ön koşulu {pre_id} dersinden önce planlanmış görünüyor.",
                    "suggestion": "Ön koşul dersini önceki döneme, bağlı dersi sonraki döneme taşıyın.",
                }
            )
    return violations


def calculate_prerequisite_penalty(assignments: list[dict[str, Any]], prerequisites: list[dict[str, Any]]) -> float:
    violations = check_prerequisite_order(assignments, prerequisites)
    return min(1.0, 0.25 * len([v for v in violations if v.get("severity") == "error"]) + 0.10 * len(violations))


def explain_prerequisite_decision(course_id: int, semester: str, prerequisites: list[dict[str, Any]]) -> str | None:
    related = [p for p in prerequisites if int(p.get("course_id")) == int(course_id)]
    if not related:
        return None
    return f"{course_id} dersi {semester} dönemine yerleştirilirken ön koşul ilişkileri kontrol edildi."

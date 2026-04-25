# -*- coding: utf-8 -*-
"""Hafif saat cakisma riski analizi."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}


def get_time_constraints(conn: sqlite3.Connection, course_id: int | None = None) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if course_id is not None:
        where.append("course_id = ?")
        params.append(int(course_id))
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM course_time_constraints WHERE {' AND '.join(where)} ORDER BY conflict_group, course_id", tuple(params))
    cols = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, cols) or {} for row in cur.fetchall()]


def estimate_conflict_risk(conn: sqlite3.Connection, plan: list[dict[str, Any]]) -> dict[str, Any]:
    constraints = {int(row["course_id"]): row for row in get_time_constraints(conn) if row.get("course_id") is not None}
    groups: dict[tuple[str, str], int] = {}
    for item in plan:
        c = constraints.get(int(item.get("course_id")))
        if not c or not c.get("conflict_group"):
            continue
        key = (str(c["conflict_group"]), str(item.get("assigned_semester")))
        groups[key] = groups.get(key, 0) + 1
    risky = {f"{group}:{semester}": count for (group, semester), count in groups.items() if count >= 2}
    level = "low"
    if any(count >= 3 for count in risky.values()):
        level = "high"
    elif risky:
        level = "medium"
    return {"risk_level": level, "risky_groups": risky}


def generate_conflict_warnings(conn: sqlite3.Connection, plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risk = estimate_conflict_risk(conn, plan)
    if risk["risk_level"] == "low":
        return []
    return [
        {
            "constraint_type": "time_conflict",
            "severity": "warning" if risk["risk_level"] == "medium" else "error",
            "message": "Aynı öğrenci kitlesinin alabileceği dersler aynı döneme yığılmış olabilir.",
            "suggestion": "Conflict group içindeki yüksek talep dersleri dönemlere dağıtın.",
        }
    ]

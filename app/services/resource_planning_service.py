# -*- coding: utf-8 -*-
"""Derslik/laboratuvar kaynak kisiti servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema
from app.services.course_semester_availability_service import normalize_semester


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


def create_resource(
    conn: sqlite3.Connection,
    resource_name: str,
    resource_type: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
    capacity: int | None = None,
    available_fall: bool = True,
    available_spring: bool = True,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO teaching_resources (
            resource_name, resource_type, faculty_id, department_id, capacity,
            available_fall, available_spring, is_active, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (resource_name, resource_type, faculty_id, department_id, capacity, 1 if available_fall else 0, 1 if available_spring else 0, now, now, notes),
    )
    cur.execute("SELECT * FROM teaching_resources WHERE id = ?", (int(cur.lastrowid),))
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description]) or {}


def list_resources(conn: sqlite3.Connection, resource_type: str | None = None) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["is_active = 1"]
    params: list[Any] = []
    if resource_type:
        where.append("resource_type = ?")
        params.append(resource_type)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM teaching_resources WHERE {' AND '.join(where)} ORDER BY resource_type, resource_name", tuple(params))
    return _fetch_all_dicts(cur)


def create_resource_requirement(
    conn: sqlite3.Connection,
    course_id: int,
    resource_type: str,
    required_capacity: int | None = None,
    required_hours: float | None = None,
    hard_requirement: bool = True,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO course_resource_requirements
            (course_id, resource_type, required_capacity, required_hours, hard_requirement, created_at, updated_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (int(course_id), resource_type, required_capacity, required_hours, 1 if hard_requirement else 0, now, now, notes),
    )
    cur.execute("SELECT * FROM course_resource_requirements WHERE id = ?", (int(cur.lastrowid),))
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description]) or {}


def list_resource_requirements(conn: sqlite3.Connection, course_id: int | None = None) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if course_id is not None:
        where.append("course_id = ?")
        params.append(int(course_id))
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM course_resource_requirements WHERE {' AND '.join(where)} ORDER BY course_id, resource_type", tuple(params))
    return _fetch_all_dicts(cur)


def get_course_resource_requirements(conn: sqlite3.Connection, course_id: int) -> list[dict[str, Any]]:
    return list_resource_requirements(conn, int(course_id))


def _resource_capacity_for_type(conn: sqlite3.Connection, resource_type: str, year: int, semester: str) -> tuple[int, float]:
    sem = normalize_semester(semester)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tr.id, tr.capacity, src.available_capacity, src.available_hours,
               tr.available_fall, tr.available_spring
        FROM teaching_resources tr
        LEFT JOIN semester_resource_capacity src
          ON src.resource_id = tr.id AND src.year = ? AND src.semester = ?
        WHERE tr.resource_type = ? AND tr.is_active = 1
        """,
        (int(year), sem, resource_type),
    )
    capacity = 0
    hours = 0.0
    for row in _fetch_all_dicts(cur):
        if sem == "fall" and not bool(row.get("available_fall")):
            continue
        if sem == "spring" and not bool(row.get("available_spring")):
            continue
        capacity += int(row.get("available_capacity") or row.get("capacity") or 0)
        hours += float(row.get("available_hours") or 0.0)
    return capacity, hours


def check_resource_feasibility(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    semester: str,
    usage: dict[tuple[str, str], dict[str, float]] | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    sem = normalize_semester(semester)
    usage = usage or {}
    violations = []
    for req in get_course_resource_requirements(conn, int(course_id)):
        resource_type = str(req.get("resource_type") or "")
        available_capacity, available_hours = _resource_capacity_for_type(conn, resource_type, int(year), sem)
        used = usage.get((resource_type, sem), {"capacity": 0.0, "hours": 0.0})
        required_capacity = float(req.get("required_capacity") or 0.0)
        required_hours = float(req.get("required_hours") or 0.0)
        if available_capacity and used["capacity"] + required_capacity > available_capacity:
            violations.append(f"{resource_type} kapasitesi aşılıyor.")
        if available_hours and used["hours"] + required_hours > available_hours:
            violations.append(f"{resource_type} saat kapasitesi aşılıyor.")
        if not available_capacity and bool(req.get("hard_requirement")):
            violations.append(f"{resource_type} için uygun kaynak bulunamadı.")
    return {
        "ok": not violations,
        "violations": violations,
        "message": "Kaynak kısıtları uygundur." if not violations else "Kaynak kısıtı ihlali var.",
    }


def calculate_resource_usage(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    usage: dict[str, int] = {}
    for item in assignments:
        for req in item.get("resource_requirements") or []:
            key = f"{req.get('resource_type')}:{item.get('assigned_semester')}"
            usage[key] = usage.get(key, 0) + 1
    return {"usage": usage}


def find_resource_conflicts(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"constraint_type": "resource", "severity": "warning", "message": item}
        for item in calculate_resource_usage(plan).get("overloaded", [])
    ]

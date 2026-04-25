# -*- coding: utf-8 -*-
"""Ogretim uyesi uygunlugu ve donemsel yuk kontrolu."""

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


def create_instructor(
    conn: sqlite3.Connection,
    name: str,
    email: str | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO instructors (name, email, faculty_id, department_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, email, faculty_id, department_id, 1 if is_active else 0, now, now),
    )
    cur.execute("SELECT * FROM instructors WHERE id = ?", (int(cur.lastrowid),))
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description]) or {}


def list_instructors(conn: sqlite3.Connection, faculty_id: int | None = None, department_id: int | None = None) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["is_active = 1"]
    params: list[Any] = []
    if faculty_id is not None:
        where.append("(faculty_id = ? OR faculty_id IS NULL)")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("(department_id = ? OR department_id IS NULL)")
        params.append(int(department_id))
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM instructors WHERE {' AND '.join(where)} ORDER BY name", tuple(params))
    return _fetch_all_dicts(cur)


def assign_course_instructor(
    conn: sqlite3.Connection,
    course_id: int,
    instructor_id: int,
    priority: int = 1,
    can_teach: bool = True,
    preferred: bool = False,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO course_instructor_assignments
            (course_id, instructor_id, priority, can_teach, preferred, created_at, updated_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (int(course_id), int(instructor_id), int(priority), 1 if can_teach else 0, 1 if preferred else 0, now, now, notes),
    )
    cur.execute("SELECT * FROM course_instructor_assignments WHERE id = ?", (int(cur.lastrowid),))
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description]) or {}


def upsert_instructor_availability(
    conn: sqlite3.Connection,
    instructor_id: int,
    year: int,
    semester: str,
    available: bool = True,
    max_elective_courses: int = 2,
    current_assigned_elective_count: int | None = None,
    unavailable_reason: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    sem = normalize_semester(semester)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO instructor_semester_availability (
            instructor_id, year, semester, available, max_elective_courses,
            current_assigned_elective_count, unavailable_reason, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(instructor_id),
            int(year),
            sem,
            1 if available else 0,
            int(max_elective_courses),
            current_assigned_elective_count,
            unavailable_reason,
            now,
            now,
            notes,
        ),
    )
    cur.execute("SELECT * FROM instructor_semester_availability WHERE id = ?", (int(cur.lastrowid),))
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description]) or {}


def list_instructor_availability(
    conn: sqlite3.Connection,
    year: int | None = None,
    semester: str | None = None,
    instructor_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if year is not None:
        where.append("year = ?")
        params.append(int(year))
    if semester:
        where.append("semester = ?")
        params.append(normalize_semester(semester))
    if instructor_id is not None:
        where.append("instructor_id = ?")
        params.append(int(instructor_id))
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM instructor_semester_availability WHERE {' AND '.join(where)} ORDER BY year DESC, semester, instructor_id",
        tuple(params),
    )
    return _fetch_all_dicts(cur)


def get_available_instructors(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    semester: str,
    assigned_counts: dict[tuple[int, str], int] | None = None,
) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    sem = normalize_semester(semester)
    assigned_counts = assigned_counts or {}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT i.*, cia.priority, cia.preferred, isa.available, isa.max_elective_courses,
               isa.current_assigned_elective_count, isa.unavailable_reason
        FROM course_instructor_assignments cia
        JOIN instructors i ON i.id = cia.instructor_id
        LEFT JOIN instructor_semester_availability isa
          ON isa.instructor_id = i.id AND isa.year = ? AND isa.semester = ?
        WHERE cia.course_id = ? AND cia.can_teach = 1 AND i.is_active = 1
        ORDER BY cia.preferred DESC, cia.priority ASC, i.name
        """,
        (int(year), sem, int(course_id)),
    )
    available: list[dict[str, Any]] = []
    for row in _fetch_all_dicts(cur):
        is_available = True if row.get("available") is None else bool(row.get("available"))
        max_load = int(row.get("max_elective_courses") or 2)
        current = int(row.get("current_assigned_elective_count") or 0) + int(assigned_counts.get((int(row["id"]), sem), 0))
        if is_available and current < max_load:
            row["remaining_capacity"] = max_load - current
            available.append(row)
    return available


def check_instructor_feasibility(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    semester: str,
    assigned_counts: dict[tuple[int, str], int] | None = None,
) -> dict[str, Any]:
    available = get_available_instructors(conn, course_id, year, semester, assigned_counts=assigned_counts)
    if available:
        chosen = available[0]
        return {
            "ok": True,
            "instructor_id": int(chosen["id"]),
            "message": f"{chosen.get('name')} {semester} dönemi için uygundur.",
            "warning": None,
        }
    return {
        "ok": False,
        "instructor_id": None,
        "message": "Bu ders için ilgili dönemde uygun öğretim üyesi bulunamadı.",
        "warning": "Öğretim üyesi uygunluğu eksik veya kapasite dolu.",
    }


def calculate_instructor_load(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    load: dict[str, int] = {}
    for item in assignments:
        instructor_id = item.get("instructor_id")
        if instructor_id is None:
            continue
        key = f"{instructor_id}:{item.get('assigned_semester')}"
        load[key] = load.get(key, 0) + 1
    return {"load": load, "overloaded": []}

# -*- coding: utf-8 -*-
"""Kriter tamlik gorev takip servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else {}
    data["missing_fields"] = _json_loads(data.get("missing_fields_json"), [])
    data["validation_issues"] = _json_loads(data.get("validation_issues_json"), [])
    return data


def _priority(missing_fields: list[str], validation_issues: list[dict[str, Any]]) -> str:
    if any(str(item.get("severity")) == "critical" for item in validation_issues):
        return "critical"
    if len(missing_fields) >= 3 or any(str(item.get("severity")) == "error" for item in validation_issues):
        return "high"
    if missing_fields:
        return "medium"
    return "low"


def generate_tasks_for_missing_criteria(
    conn: sqlite3.Connection,
    completion_result: dict[str, Any],
    assigned_role: str | None = None,
    created_by: str | None = None,
) -> list[dict[str, Any]]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    created: list[dict[str, Any]] = []
    scope_type = completion_result.get("scope_type") or "faculty"
    faculty_id = completion_result.get("faculty_id")
    department_id = completion_result.get("department_id")
    year = int(completion_result.get("year"))
    semester = completion_result.get("semester")
    cur = conn.cursor()
    by_course: dict[int, dict[str, Any]] = {}
    for row in completion_result.get("matrix") or []:
        if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid")):
            course_id = int(row["course_id"])
            by_course.setdefault(course_id, {"missing": [], "issues": []})
            by_course[course_id]["missing"].append(row.get("criterion_key"))
            if row.get("invalid_reason"):
                by_course[course_id]["issues"].append(
                    {
                        "criterion_key": row.get("criterion_key"),
                        "message": row.get("invalid_reason"),
                        "severity": "error",
                    }
                )
    for course_id, payload in by_course.items():
        missing_fields = sorted(set(str(item) for item in payload["missing"] if item))
        validation_issues = payload["issues"]
        cur.execute(
            """
            SELECT id
            FROM criteria_completion_tasks
            WHERE course_id = ? AND year = ?
              AND COALESCE(semester, '') = COALESCE(?, '')
              AND status NOT IN ('closed', 'approved')
            LIMIT 1
            """,
            (course_id, year, semester),
        )
        existing = cur.fetchone()
        if existing:
            continue
        cur.execute(
            """
            INSERT INTO criteria_completion_tasks (
                scope_type, faculty_id, department_id, course_id, year, semester,
                assigned_role, status, missing_fields_json, validation_issues_json,
                priority, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
            """,
            (
                "course",
                faculty_id,
                department_id,
                course_id,
                year,
                semester,
                assigned_role or ("department_coordinator" if scope_type == "department" else "faculty_coordinator"),
                _json_dumps(missing_fields),
                _json_dumps(validation_issues),
                _priority(missing_fields, validation_issues),
                created_by,
                _now(),
                _now(),
            ),
        )
        created.append(get_task(conn, int(cur.lastrowid)) or {})
    return created


def get_task(conn: sqlite3.Connection, task_id: int) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_tasks WHERE id = ?", (int(task_id),))
    return _row_to_dict(cur.fetchone())


def get_tasks(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    for col, value in (("year", year), ("faculty_id", faculty_id), ("department_id", department_id), ("status", status)):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(value)
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM criteria_completion_tasks WHERE {' AND '.join(where)} ORDER BY id DESC",
        tuple(params),
    )
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def assign_task(
    conn: sqlite3.Connection,
    task_id: int,
    assigned_to: str | None = None,
    assigned_role: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    conn.execute(
        """
        UPDATE criteria_completion_tasks
        SET assigned_to = COALESCE(?, assigned_to),
            assigned_role = COALESCE(?, assigned_role),
            due_date = COALESCE(?, due_date),
            updated_at = ?
        WHERE id = ?
        """,
        (assigned_to, assigned_role, due_date, _now(), int(task_id)),
    )
    return get_task(conn, int(task_id)) or {}


def update_task_status(
    conn: sqlite3.Connection,
    task_id: int,
    status: str,
    notes: str | None = None,
    approved_by: str | None = None,
) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    now = _now()
    conn.execute(
        """
        UPDATE criteria_completion_tasks
        SET status = ?, notes = COALESCE(?, notes), updated_at = ?,
            completed_at = CASE WHEN ? IN ('closed', 'approved') THEN COALESCE(completed_at, ?) ELSE completed_at END,
            approved_by = CASE WHEN ? = 'approved' THEN ? ELSE approved_by END,
            approved_at = CASE WHEN ? = 'approved' THEN ? ELSE approved_at END
        WHERE id = ?
        """,
        (status, notes, now, status, now, status, approved_by, status, now, int(task_id)),
    )
    return get_task(conn, int(task_id)) or {}


def close_completed_tasks(conn: sqlite3.Connection, completion_result: dict[str, Any]) -> int:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    incomplete_courses = {
        int(row["course_id"])
        for row in completion_result.get("matrix") or []
        if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
    }
    year = int(completion_result.get("year"))
    semester = completion_result.get("semester")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, course_id
        FROM criteria_completion_tasks
        WHERE year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
          AND status NOT IN ('closed', 'approved')
        """,
        (year, semester),
    )
    closed = 0
    for task_id, course_id in cur.fetchall():
        if course_id is not None and int(course_id) not in incomplete_courses:
            update_task_status(conn, int(task_id), "closed", notes="Eksikler tamamlandığı için otomatik kapatıldı.")
            closed += 1
    return closed

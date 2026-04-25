# -*- coding: utf-8 -*-
"""Kriter tamlik override/istisna servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema
from app.services.criteria_completion_policy_service import resolve_policy


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_semester(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value or "").strip()
    if not raw:
        return None
    return "Bahar" if raw.lower().startswith("b") else "Güz"


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


def request_override(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    reason: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
    missing_fields: list[str] | None = None,
    validation_issues: list[dict[str, Any]] | None = None,
    requested_by: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    semester = _normalize_semester(semester)
    policy = resolve_policy(conn, scope_type, int(year), faculty_id, department_id, semester)
    if not policy.get("allow_override"):
        raise ValueError("Aktif politika override talebine izin vermiyor.")
    if policy.get("override_requires_reason") and not str(reason or "").strip():
        raise ValueError("Override gerekçesi zorunludur.")
    status = "pending" if policy.get("override_requires_approval") else "approved"
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO criteria_completion_overrides (
            scope_type, faculty_id, department_id, course_id, year, semester,
            missing_fields_json, validation_issues_json, reason, requested_by,
            requested_at, approval_status, approved_by, approved_at, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scope_type,
            faculty_id,
            department_id,
            course_id,
            int(year),
            semester,
            _json_dumps(missing_fields or []),
            _json_dumps(validation_issues or []),
            reason,
            requested_by,
            now,
            status,
            requested_by if status == "approved" else None,
            now if status == "approved" else None,
            expires_at,
            now,
        ),
    )
    return get_override(conn, int(cur.lastrowid)) or {}


def get_override(conn: sqlite3.Connection, override_id: int) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_overrides WHERE id = ?", (int(override_id),))
    return _row_to_dict(cur.fetchone())


def approve_override(conn: sqlite3.Connection, override_id: int, approved_by: str | None = None) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE criteria_completion_overrides
        SET approval_status = 'approved', approved_by = ?, approved_at = ?
        WHERE id = ?
        """,
        (approved_by, _now(), int(override_id)),
    )
    return get_override(conn, int(override_id)) or {}


def reject_override(
    conn: sqlite3.Connection,
    override_id: int,
    rejection_reason: str,
    rejected_by: str | None = None,
) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE criteria_completion_overrides
        SET approval_status = 'rejected', rejected_by = ?, rejected_at = ?, rejection_reason = ?
        WHERE id = ?
        """,
        (rejected_by, _now(), rejection_reason, int(override_id)),
    )
    return get_override(conn, int(override_id)) or {}


def get_active_override(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    semester = _normalize_semester(semester)
    cur = conn.cursor()
    now = _now()
    cur.execute(
        """
        SELECT *
        FROM criteria_completion_overrides
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(course_id, -1) = COALESCE(?, -1)
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
          AND approval_status = 'approved'
          AND (expires_at IS NULL OR expires_at >= ?)
        ORDER BY id DESC
        LIMIT 1
        """,
        (scope_type, faculty_id, department_id, course_id, int(year), semester, now),
    )
    return _row_to_dict(cur.fetchone())


def list_overrides(
    conn: sqlite3.Connection,
    scope_type: str | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    approval_status: str | None = None,
) -> list[dict[str, Any]]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    for col, value in (
        ("scope_type", scope_type),
        ("year", year),
        ("faculty_id", faculty_id),
        ("department_id", department_id),
        ("approval_status", approval_status),
    ):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(value)
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM criteria_completion_overrides WHERE {' AND '.join(where)} ORDER BY id DESC",
        tuple(params),
    )
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def mark_override_used(conn: sqlite3.Connection, override_id: int, run_id: int | None = None) -> None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    conn.execute(
        """
        UPDATE criteria_completion_overrides
        SET used_at = ?, allowed_for_run_id = COALESCE(?, allowed_for_run_id)
        WHERE id = ?
        """,
        (_now(), run_id, int(override_id)),
    )

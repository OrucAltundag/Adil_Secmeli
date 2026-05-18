# -*- coding: utf-8 -*-
"""Kriter tamlik politikasi cozumleme servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema

DEFAULT_REQUIRED_FIELDS = [
    "total_students",
    "passed_students",
    "average_grade",
    "capacity",
    "enrolled_students",
]
DEFAULT_OPTIONAL_FIELDS = ["survey_count", "trend"]


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


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        data = {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}
    data["required_fields"] = _json_loads(data.get("required_fields_json"), DEFAULT_REQUIRED_FIELDS)
    data["optional_fields"] = _json_loads(data.get("optional_fields_json"), DEFAULT_OPTIONAL_FIELDS)
    for key in (
        "allow_new_course_missing_history",
        "block_on_invalid_numeric",
        "block_on_critical_issues",
        "allow_override",
        "override_requires_reason",
        "override_requires_approval",
        "is_active",
    ):
        data[key] = bool(data.get(key))
    return data


def create_default_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM criteria_completion_policies
        WHERE scope_type = 'global' AND is_active = 1
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row:
        return _row_to_dict(row) or {}
    now = _now()
    cur.execute(
        """
        INSERT INTO criteria_completion_policies (
            name, scope_type, required_completion_ratio, required_fields_json,
            optional_fields_json, allow_new_course_missing_history,
            new_course_grace_period_years, block_on_invalid_numeric,
            block_on_critical_issues, allow_override, override_requires_reason,
            override_requires_approval, is_active, created_at, updated_at, notes
        )
        VALUES (?, 'global', 1.0, ?, ?, 1, 2, 1, 1, 1, 1, 1, 1, ?, ?, ?)
        """,
        (
            "Varsayılan Kriter Tamlık Politikası",
            _json_dumps(DEFAULT_REQUIRED_FIELDS),
            _json_dumps(DEFAULT_OPTIONAL_FIELDS),
            now,
            now,
            "Geriye dönük güvenlik için zorunlu alanlarda %100 tamlık ister.",
        ),
    )
    return get_policy(conn, int(cur.lastrowid)) or {}


def get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_policies WHERE id = ?", (int(policy_id),))
    return _row_to_dict(cur.fetchone())


def create_completion_policy(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    required_completion_ratio: float = 1.0,
    required_fields: list[str] | None = None,
    optional_fields: list[str] | None = None,
    allow_new_course_missing_history: bool = True,
    new_course_grace_period_years: int = 2,
    min_survey_response_count: int | None = None,
    block_on_invalid_numeric: bool = True,
    block_on_critical_issues: bool = True,
    allow_override: bool = True,
    override_requires_reason: bool = True,
    override_requires_approval: bool = True,
    notes: str | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    semester = _normalize_semester(semester)
    if scope_type not in {"global", "faculty", "department"}:
        scope_type = "global"
    now = _now()
    cur = conn.cursor()
    if activate:
        where = ["scope_type = ?"]
        params: list[Any] = [scope_type]
        for col, value in (("faculty_id", faculty_id), ("department_id", department_id), ("year", year), ("semester", semester)):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(value)
        cur.execute(
            f"UPDATE criteria_completion_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
            tuple([now] + params),
        )
    cur.execute(
        """
        INSERT INTO criteria_completion_policies (
            name, scope_type, faculty_id, department_id, year, semester,
            required_completion_ratio, required_fields_json, optional_fields_json,
            allow_new_course_missing_history, new_course_grace_period_years,
            min_survey_response_count, block_on_invalid_numeric, block_on_critical_issues,
            allow_override, override_requires_reason, override_requires_approval,
            is_active, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            scope_type,
            faculty_id,
            department_id,
            year,
            semester,
            float(required_completion_ratio),
            _json_dumps(required_fields or DEFAULT_REQUIRED_FIELDS),
            _json_dumps(optional_fields or DEFAULT_OPTIONAL_FIELDS),
            1 if allow_new_course_missing_history else 0,
            int(new_course_grace_period_years),
            int(min_survey_response_count) if min_survey_response_count is not None else None,
            1 if block_on_invalid_numeric else 0,
            1 if block_on_critical_issues else 0,
            1 if allow_override else 0,
            1 if override_requires_reason else 0,
            1 if override_requires_approval else 0,
            1 if activate else 0,
            now,
            now,
            notes,
        ),
    )
    return get_policy(conn, int(cur.lastrowid)) or {}


def resolve_policy(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    semester = _normalize_semester(semester)
    create_default_policy(conn)
    candidates = [
        ("department", faculty_id, department_id, year, semester),
        ("department", faculty_id, department_id, year, None),
        ("faculty", faculty_id, None, year, semester),
        ("faculty", faculty_id, None, year, None),
        ("department", faculty_id, department_id, None, None),
        ("faculty", faculty_id, None, None, None),
        ("global", None, None, year, None),
        ("global", None, None, None, None),
    ]
    cur = conn.cursor()
    for cand_scope, cand_faculty, cand_department, cand_year, cand_semester in candidates:
        if cand_scope == "department" and department_id is None:
            continue
        if cand_scope == "faculty" and faculty_id is None:
            continue
        where = ["scope_type = ?", "is_active = 1"]
        params: list[Any] = [cand_scope]
        for col, value in (
            ("faculty_id", cand_faculty),
            ("department_id", cand_department),
            ("year", cand_year),
            ("semester", cand_semester),
        ):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(value)
        cur.execute(
            f"SELECT * FROM criteria_completion_policies WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
            tuple(params),
        )
        row = cur.fetchone()
        if row:
            return _row_to_dict(row) or {}
    return create_default_policy(conn)


def list_completion_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_policies ORDER BY is_active DESC, id DESC")
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def activate_completion_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]:
    policy = get_policy(conn, policy_id)
    if not policy:
        raise ValueError("Kriter tamlık politikası bulunamadı.")
    now = _now()
    cur = conn.cursor()
    where = ["scope_type = ?"]
    params: list[Any] = [policy["scope_type"]]
    for col in ("faculty_id", "department_id", "year", "semester"):
        value = policy.get(col)
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    cur.execute(
        f"UPDATE criteria_completion_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
        tuple([now] + params),
    )
    cur.execute("UPDATE criteria_completion_policies SET is_active = 1, updated_at = ? WHERE id = ?", (now, int(policy_id)))
    return get_policy(conn, policy_id) or {}

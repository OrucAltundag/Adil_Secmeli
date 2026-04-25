# -*- coding: utf-8 -*-
"""Havuz state machine politika cozumleme servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_pool_state_governance_schema


BOOL_FIELDS = {
    "require_approval_for_cancel",
    "require_approval_for_reactivation",
    "protect_accreditation_courses",
    "protect_strategic_courses",
    "protect_required_courses",
    "low_confidence_blocks_cancel",
    "low_confidence_blocks_rest",
    "allow_reactivation_from_rest",
    "allow_reactivation_from_cancelled",
    "reactivation_requires_manual_approval",
    "is_active",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_semester(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value or "").strip()
    if not raw:
        return None
    return "Bahar" if raw.lower().startswith("b") else "Guz"


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "evet", "on"}
    return bool(value)


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        data = {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}
    for field in BOOL_FIELDS:
        if field in data:
            data[field] = _bool(data[field])
    return data


def get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None:
    ensure_pool_state_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM pool_state_policies WHERE id = ?", (int(policy_id),))
    return _row_to_dict(cur.fetchone())


def create_default_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM pool_state_policies
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
        INSERT INTO pool_state_policies (
            name, scope_type, low_score_threshold, medium_score_threshold,
            high_score_threshold, pool_entry_threshold, rest_threshold,
            cancel_candidate_threshold, reactivation_threshold,
            rest_after_years_in_pool, cancel_after_years_in_rest,
            new_course_grace_period_years, revised_course_grace_period_years,
            require_approval_for_cancel, require_approval_for_reactivation,
            protect_accreditation_courses, protect_strategic_courses,
            protect_required_courses, low_confidence_blocks_cancel,
            low_confidence_blocks_rest, minimum_data_confidence_for_cancel,
            minimum_data_confidence_for_rest, allow_reactivation_from_rest,
            allow_reactivation_from_cancelled, reactivation_requires_manual_approval,
            is_active, created_at, updated_at, notes
        )
        VALUES (
            'Varsayılan Havuz State Politikası', 'global', 50, 70,
            80, 60, 45, 35, 75, 2, 2, 2, 1,
            1, 1, 1, 1, 1, 1, 1, 0.75, 0.60, 1, 0, 1,
            1, ?, ?, 'Kalıcı iptal ve reactivation kararlarını akademik onaya bağlar.'
        )
        """,
        (now, now),
    )
    return get_policy(conn, int(cur.lastrowid)) or {}


def create_pool_state_policy(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    activate: bool = True,
    notes: str | None = None,
    **values: Any,
) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    if scope_type not in {"global", "faculty", "department"}:
        scope_type = "global"
    semester = normalize_semester(semester)
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
            f"UPDATE pool_state_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
            tuple([now] + params),
        )
    defaults = {
        "low_score_threshold": 50.0,
        "medium_score_threshold": 70.0,
        "high_score_threshold": 80.0,
        "pool_entry_threshold": 60.0,
        "rest_threshold": 45.0,
        "cancel_candidate_threshold": 35.0,
        "reactivation_threshold": 75.0,
        "rest_after_years_in_pool": 2,
        "cancel_after_years_in_rest": 2,
        "max_years_in_pool": None,
        "new_course_grace_period_years": 2,
        "revised_course_grace_period_years": 1,
        "require_approval_for_cancel": True,
        "require_approval_for_reactivation": True,
        "protect_accreditation_courses": True,
        "protect_strategic_courses": True,
        "protect_required_courses": True,
        "low_confidence_blocks_cancel": True,
        "low_confidence_blocks_rest": True,
        "minimum_data_confidence_for_cancel": 0.75,
        "minimum_data_confidence_for_rest": 0.60,
        "allow_reactivation_from_rest": True,
        "allow_reactivation_from_cancelled": False,
        "reactivation_requires_manual_approval": True,
    }
    defaults.update(values)
    cur.execute(
        """
        INSERT INTO pool_state_policies (
            name, scope_type, faculty_id, department_id, year, semester,
            low_score_threshold, medium_score_threshold, high_score_threshold,
            pool_entry_threshold, rest_threshold, cancel_candidate_threshold,
            reactivation_threshold, rest_after_years_in_pool,
            cancel_after_years_in_rest, max_years_in_pool,
            new_course_grace_period_years, revised_course_grace_period_years,
            require_approval_for_cancel, require_approval_for_reactivation,
            protect_accreditation_courses, protect_strategic_courses,
            protect_required_courses, low_confidence_blocks_cancel,
            low_confidence_blocks_rest, minimum_data_confidence_for_cancel,
            minimum_data_confidence_for_rest, allow_reactivation_from_rest,
            allow_reactivation_from_cancelled, reactivation_requires_manual_approval,
            is_active, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            scope_type,
            faculty_id,
            department_id,
            year,
            semester,
            defaults["low_score_threshold"],
            defaults["medium_score_threshold"],
            defaults["high_score_threshold"],
            defaults["pool_entry_threshold"],
            defaults["rest_threshold"],
            defaults["cancel_candidate_threshold"],
            defaults["reactivation_threshold"],
            defaults["rest_after_years_in_pool"],
            defaults["cancel_after_years_in_rest"],
            defaults["max_years_in_pool"],
            defaults["new_course_grace_period_years"],
            defaults["revised_course_grace_period_years"],
            1 if defaults["require_approval_for_cancel"] else 0,
            1 if defaults["require_approval_for_reactivation"] else 0,
            1 if defaults["protect_accreditation_courses"] else 0,
            1 if defaults["protect_strategic_courses"] else 0,
            1 if defaults["protect_required_courses"] else 0,
            1 if defaults["low_confidence_blocks_cancel"] else 0,
            1 if defaults["low_confidence_blocks_rest"] else 0,
            defaults["minimum_data_confidence_for_cancel"],
            defaults["minimum_data_confidence_for_rest"],
            1 if defaults["allow_reactivation_from_rest"] else 0,
            1 if defaults["allow_reactivation_from_cancelled"] else 0,
            1 if defaults["reactivation_requires_manual_approval"] else 0,
            1 if activate else 0,
            now,
            now,
            notes,
        ),
    )
    return get_policy(conn, int(cur.lastrowid)) or {}


def resolve_policy(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    create_default_policy(conn)
    semester = normalize_semester(semester)
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
    for scope, fid, bid, cand_year, cand_semester in candidates:
        if scope == "department" and department_id is None:
            continue
        if scope == "faculty" and faculty_id is None:
            continue
        where = ["scope_type = ?", "is_active = 1"]
        params: list[Any] = [scope]
        for col, value in (("faculty_id", fid), ("department_id", bid), ("year", cand_year), ("semester", cand_semester)):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(value)
        cur.execute(
            f"SELECT * FROM pool_state_policies WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
            tuple(params),
        )
        row = cur.fetchone()
        if row:
            return _row_to_dict(row) or {}
    return create_default_policy(conn)


def list_pool_state_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_pool_state_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM pool_state_policies ORDER BY is_active DESC, id DESC")
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def activate_pool_state_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]:
    policy = get_policy(conn, int(policy_id))
    if not policy:
        raise ValueError("Havuz state politikası bulunamadı.")
    now = _now()
    where = ["scope_type = ?"]
    params: list[Any] = [policy["scope_type"]]
    for col in ("faculty_id", "department_id", "year", "semester"):
        value = policy.get(col)
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    conn.execute(
        f"UPDATE pool_state_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
        tuple([now] + params),
    )
    conn.execute("UPDATE pool_state_policies SET is_active = 1, updated_at = ? WHERE id = ?", (now, int(policy_id)))
    return get_policy(conn, int(policy_id)) or {}


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    errors = []
    if float(policy.get("cancel_candidate_threshold", 0)) > float(policy.get("rest_threshold", 0)):
        errors.append("cancel_candidate_threshold rest_threshold değerinden büyük olmamalı.")
    if float(policy.get("rest_threshold", 0)) > float(policy.get("pool_entry_threshold", 0)):
        errors.append("rest_threshold pool_entry_threshold değerinden büyük olmamalı.")
    return {"valid": not errors, "errors": errors}

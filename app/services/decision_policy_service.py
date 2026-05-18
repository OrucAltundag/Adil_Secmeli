# -*- coding: utf-8 -*-
"""Decision policy resolution and threshold classification."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_decision_governance_schema
from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
)

DEFAULT_POLICY = {
    "name": "Varsayilan Karar Politikasi",
    "scope_type": "global",
    "mode": "static_threshold",
    "curriculum_keep_threshold": 70.0,
    "pool_threshold": 50.0,
    "rest_threshold": 40.0,
    "cancel_candidate_threshold": 30.0,
    "new_course_grace_period_years": 2,
    "low_data_confidence_threshold": 0.50,
    "sensitivity_margin": 3.0,
    "require_manual_approval_for_cancel": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _bool(value: Any) -> bool:
    return bool(int(value or 0)) if not isinstance(value, bool) else value


def _row_to_policy(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    keys = row.keys() if hasattr(row, "keys") else []
    get = row.__getitem__

    def value(name: str, idx: int) -> Any:
        return get(name) if keys and name in keys else get(idx)

    return {
        "id": int(value("id", 0)),
        "name": str(value("name", 1) or ""),
        "scope_type": str(value("scope_type", 2) or "global"),
        "faculty_id": value("faculty_id", 3),
        "department_id": value("department_id", 4),
        "year": value("year", 5),
        "mode": str(value("mode", 6) or "static_threshold"),
        "curriculum_keep_threshold": float(value("curriculum_keep_threshold", 7) or 70.0),
        "pool_threshold": float(value("pool_threshold", 8) or 50.0),
        "rest_threshold": float(value("rest_threshold", 9) or 40.0),
        "cancel_candidate_threshold": (
            float(value("cancel_candidate_threshold", 10))
            if value("cancel_candidate_threshold", 10) is not None
            else None
        ),
        "min_success_rate": value("min_success_rate", 11),
        "min_survey_count": value("min_survey_count", 12),
        "min_enrollment_rate": value("min_enrollment_rate", 13),
        "new_course_grace_period_years": int(value("new_course_grace_period_years", 14) or 2),
        "low_data_confidence_threshold": float(value("low_data_confidence_threshold", 15) or 0.50),
        "sensitivity_margin": float(value("sensitivity_margin", 16) or 3.0),
        "top_percent_curriculum": value("top_percent_curriculum", 17),
        "middle_percent_pool": value("middle_percent_pool", 18),
        "bottom_percent_rest": value("bottom_percent_rest", 19),
        "require_manual_approval_for_cancel": _bool(value("require_manual_approval_for_cancel", 20)),
        "is_active": _bool(value("is_active", 21)),
        "created_at": value("created_at", 22),
        "updated_at": value("updated_at", 23),
        "notes": value("notes", 24),
    }


def _deactivate_same_scope(
    cur: sqlite3.Cursor,
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
) -> None:
    cur.execute(
        """
        UPDATE decision_policies
        SET is_active = 0, updated_at = ?
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(year, -1) = COALESCE(?, -1)
        """,
        (_now(), str(scope_type or "global"), faculty_id, department_id, year),
    )


def ensure_default_decision_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM decision_policies
        WHERE scope_type = 'global'
          AND year IS NULL
          AND is_active = 1
          AND name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (DEFAULT_POLICY["name"],),
    )
    row = cur.fetchone()
    if row:
        return _row_to_policy(row)
    return create_decision_policy(conn, **DEFAULT_POLICY, activate=True)


def create_decision_policy(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    mode: str = "static_threshold",
    curriculum_keep_threshold: float = 70.0,
    pool_threshold: float = 50.0,
    rest_threshold: float = 40.0,
    cancel_candidate_threshold: float | None = 30.0,
    min_success_rate: float | None = None,
    min_survey_count: int | None = None,
    min_enrollment_rate: float | None = None,
    new_course_grace_period_years: int = 2,
    low_data_confidence_threshold: float = 0.50,
    sensitivity_margin: float = 3.0,
    top_percent_curriculum: float | None = None,
    middle_percent_pool: float | None = None,
    bottom_percent_rest: float | None = None,
    require_manual_approval_for_cancel: bool = True,
    notes: str | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    ensure_decision_governance_schema(conn, commit=False)
    cur = conn.cursor()
    if activate:
        _deactivate_same_scope(cur, scope_type, faculty_id, department_id, year)
    cur.execute(
        """
        INSERT INTO decision_policies (
            name, scope_type, faculty_id, department_id, year, mode,
            curriculum_keep_threshold, pool_threshold, rest_threshold,
            cancel_candidate_threshold, min_success_rate, min_survey_count,
            min_enrollment_rate, new_course_grace_period_years,
            low_data_confidence_threshold, sensitivity_margin,
            top_percent_curriculum, middle_percent_pool, bottom_percent_rest,
            require_manual_approval_for_cancel, is_active, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(name),
            str(scope_type or "global"),
            faculty_id,
            department_id,
            year,
            str(mode or "static_threshold"),
            float(curriculum_keep_threshold),
            float(pool_threshold),
            float(rest_threshold),
            cancel_candidate_threshold,
            min_success_rate,
            min_survey_count,
            min_enrollment_rate,
            int(new_course_grace_period_years),
            float(low_data_confidence_threshold),
            float(sensitivity_margin),
            top_percent_curriculum,
            middle_percent_pool,
            bottom_percent_rest,
            1 if require_manual_approval_for_cancel else 0,
            1 if activate else 0,
            _now(),
            _now(),
            notes,
        ),
    )
    policy_id = int(cur.lastrowid)
    conn.commit()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (policy_id,))
    return _row_to_policy(cur.fetchone())


def resolve_decision_policy(
    conn: sqlite3.Connection,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    ensure_default_decision_policy(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    candidates = [
        ("department", faculty_id, department_id, year),
        ("faculty", faculty_id, None, year),
        ("department", faculty_id, department_id, None),
        ("faculty", faculty_id, None, None),
        ("global", None, None, year),
        ("global", None, None, None),
    ]
    for scope_type, fac_id, dep_id, policy_year in candidates:
        if scope_type == "department" and dep_id is None:
            continue
        if scope_type == "faculty" and fac_id is None:
            continue
        cur.execute(
            """
            SELECT *
            FROM decision_policies
            WHERE is_active = 1
              AND scope_type = ?
              AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
              AND COALESCE(department_id, -1) = COALESCE(?, -1)
              AND COALESCE(year, -1) = COALESCE(?, -1)
            ORDER BY id DESC
            LIMIT 1
            """,
            (scope_type, fac_id, dep_id, policy_year),
        )
        row = cur.fetchone()
        if row:
            return _row_to_policy(row)
    return ensure_default_decision_policy(conn)


def list_decision_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_default_decision_policy(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies ORDER BY is_active DESC, scope_type, year DESC, id DESC")
    return [_row_to_policy(row) for row in cur.fetchall()]


def activate_decision_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]:
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Karar politikasi bulunamadi: {policy_id}")
    policy = _row_to_policy(row)
    _deactivate_same_scope(
        cur,
        policy["scope_type"],
        policy["faculty_id"],
        policy["department_id"],
        policy["year"],
    )
    cur.execute(
        "UPDATE decision_policies SET is_active = 1, updated_at = ? WHERE id = ?",
        (_now(), int(policy_id)),
    )
    conn.commit()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    return _row_to_policy(cur.fetchone())


def classify_score(score: float | None, policy: dict[str, Any]) -> dict[str, Any]:
    safe_score = float(score or 0.0)
    cancel_threshold = policy.get("cancel_candidate_threshold")
    if cancel_threshold is not None and safe_score < float(cancel_threshold):
        return {
            "recommended_status": STATU_IPTAL,
            "rule_triggered": "cancel_candidate_threshold",
            "reason": f"Skor {float(cancel_threshold):.1f} iptal aday esiginin altinda.",
        }
    if safe_score < float(policy.get("rest_threshold", 40.0)):
        return {
            "recommended_status": STATU_DINLENMEDE,
            "rule_triggered": "rest_threshold",
            "reason": f"Skor {float(policy.get('rest_threshold', 40.0)):.1f} dinlenme esiginin altinda.",
        }
    if safe_score < float(policy.get("pool_threshold", 50.0)):
        return {
            "recommended_status": STATU_HAVUZDA,
            "rule_triggered": "pool_threshold",
            "reason": "Skor havuz esigi altinda, ancak dinlenme esiginin ustunde.",
        }
    if safe_score < float(policy.get("curriculum_keep_threshold", 70.0)):
        return {
            "recommended_status": STATU_HAVUZDA,
            "rule_triggered": "curriculum_keep_threshold",
            "reason": "Skor mufredatta kalma esiginin altinda.",
        }
    return {
        "recommended_status": STATU_MUFREDATTA,
        "rule_triggered": "curriculum_keep_threshold",
        "reason": "Skor mufredatta kalma esigini karsiliyor.",
    }


def status_label(status: int | None) -> str:
    labels = {
        STATU_MUFREDATTA: "mufredatta",
        STATU_HAVUZDA: "havuzda",
        STATU_DINLENMEDE: "dinlenmede",
        STATU_IPTAL: "iptal adayi",
    }
    return labels.get(int(status) if status is not None else 0, "belirsiz")

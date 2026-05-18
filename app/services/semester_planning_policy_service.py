# -*- coding: utf-8 -*-
"""Fakulte/bolum/yil bazli donem planlama politikasi servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema

BOOL_FIELDS = {
    "allow_unbalanced_distribution",
    "same_course_repeat_requires_approval",
    "consider_course_availability",
    "consider_instructor_availability",
    "consider_resource_constraints",
    "consider_prerequisites",
    "consider_required_course_load",
    "consider_expected_demand",
    "consider_capacity_balance",
    "consider_time_conflicts",
    "is_active",
}

DEFAULT_SOFT_WEIGHTS = {
    "score": 0.40,
    "semester_balance": 0.20,
    "demand_balance": 0.15,
    "instructor_fit": 0.10,
    "resource_fit": 0.10,
    "prerequisite_fit": 0.05,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "evet", "on"}
    return bool(value)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _load_json(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


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
    if "soft_constraint_weight_json" in data:
        data["soft_constraint_weights"] = _load_json(data.get("soft_constraint_weight_json"), DEFAULT_SOFT_WEIGHTS)
    return data


def _fetch_one_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None:
    columns = [d[0] for d in cur.description] if cur.description else []
    return _row_to_dict(cur.fetchone(), columns)


def _fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    columns = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, columns) or {} for row in cur.fetchall()]


def normalize_soft_weights(weights: dict[str, Any] | None) -> dict[str, float]:
    raw = dict(DEFAULT_SOFT_WEIGHTS)
    if weights:
        raw.update(weights)
    cleaned = {str(k): max(0.0, float(v or 0.0)) for k, v in raw.items()}
    total = sum(cleaned.values())
    if total <= 0:
        return dict(DEFAULT_SOFT_WEIGHTS)
    return {k: round(v / total, 6) for k, v in cleaned.items()}


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for field in ("total_elective_target", "fall_min", "fall_max", "spring_min", "spring_max", "max_semester_imbalance"):
        if int(policy.get(field, 0) or 0) < 0:
            errors.append(f"{field} negatif olamaz.")
    fall_min = int(policy.get("fall_min", 0) or 0)
    fall_max = int(policy.get("fall_max", 0) or 0)
    spring_min = int(policy.get("spring_min", 0) or 0)
    spring_max = int(policy.get("spring_max", 0) or 0)
    target = int(policy.get("total_elective_target", 0) or 0)
    if fall_min > fall_max:
        errors.append("Güz minimum değeri güz maksimum değerinden büyük olamaz.")
    if spring_min > spring_max:
        errors.append("Bahar minimum değeri bahar maksimum değerinden büyük olamaz.")
    if target < fall_min + spring_min:
        errors.append("Toplam seçmeli hedefi dönem minimumlarının toplamından küçük olamaz.")
    if target > fall_max + spring_max:
        errors.append("Toplam seçmeli hedefi dönem maksimumlarının toplamından büyük olamaz.")
    if policy.get("same_course_repeat_policy") not in {"disallow", "allow_if_high_demand", "allow_if_capacity_needed", "allow_with_approval"}:
        errors.append("Aynı ders tekrar politikası geçersiz.")
    if policy.get("hard_constraint_policy") not in {"strict", "warn_only", "allow_with_approval"}:
        errors.append("Hard constraint politikası geçersiz.")
    if target != fall_min + spring_min and not _bool(policy.get("allow_unbalanced_distribution")):
        warnings.append("Hedef minimum toplamından farklı; motor min/max aralığında denge onarımı uygulayacak.")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM semester_planning_policies WHERE id = ?", (int(policy_id),))
    return _fetch_one_dict(cur)


def seed_default_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM semester_planning_policies
        WHERE scope_type = 'global' AND faculty_id IS NULL AND department_id IS NULL
          AND year IS NULL AND curriculum_year IS NULL AND is_active = 1
        ORDER BY id DESC LIMIT 1
        """
    )
    row = _fetch_one_dict(cur)
    if row:
        return row
    now = _now()
    cur.execute(
        """
        INSERT INTO semester_planning_policies (
            name, scope_type, total_elective_target, fall_min, fall_max,
            spring_min, spring_max, max_semester_imbalance,
            allow_unbalanced_distribution, same_course_repeat_policy,
            same_course_repeat_requires_approval, consider_course_availability,
            consider_instructor_availability, consider_resource_constraints,
            consider_prerequisites, consider_required_course_load,
            consider_expected_demand, consider_capacity_balance,
            consider_time_conflicts, hard_constraint_policy,
            soft_constraint_weight_json, is_active, created_at, updated_at, notes
        )
        VALUES (
            'Varsayılan 4+4 Dönem Planlama Politikası', 'global',
            8, 4, 4, 4, 4, 0, 0, 'disallow', 1,
            1, 0, 0, 1, 0, 1, 1, 0, 'strict', ?, 1, ?, ?,
            'Geriye dönük uyumluluk için 4 güz + 4 bahar varsayılanıdır.'
        )
        """,
        (_json(DEFAULT_SOFT_WEIGHTS), now, now),
    )
    return get_policy(conn, int(cur.lastrowid)) or {}


def create_policy(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    curriculum_year: int | None = None,
    activate: bool = True,
    notes: str | None = None,
    **values: Any,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    if scope_type not in {"global", "faculty", "department"}:
        scope_type = "global"
    defaults: dict[str, Any] = {
        "total_elective_target": 8,
        "fall_min": 4,
        "fall_max": 4,
        "spring_min": 4,
        "spring_max": 4,
        "max_semester_imbalance": 0,
        "allow_unbalanced_distribution": False,
        "same_course_repeat_policy": "disallow",
        "same_course_repeat_requires_approval": True,
        "high_demand_repeat_threshold": None,
        "consider_course_availability": True,
        "consider_instructor_availability": False,
        "consider_resource_constraints": False,
        "consider_prerequisites": True,
        "consider_required_course_load": False,
        "consider_expected_demand": True,
        "consider_capacity_balance": True,
        "consider_time_conflicts": False,
        "minimum_plan_score": None,
        "hard_constraint_policy": "strict",
        "soft_constraint_weight_json": _json(normalize_soft_weights(values.pop("soft_constraint_weights", None))),
    }
    defaults.update(values)
    validation = validate_policy(defaults)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    now = _now()
    cur = conn.cursor()
    if activate:
        _deactivate_same_scope(conn, scope_type, faculty_id, department_id, year, curriculum_year)
    cur.execute(
        """
        INSERT INTO semester_planning_policies (
            name, scope_type, faculty_id, department_id, year, curriculum_year,
            total_elective_target, fall_min, fall_max, spring_min, spring_max,
            max_semester_imbalance, allow_unbalanced_distribution,
            same_course_repeat_policy, same_course_repeat_requires_approval,
            high_demand_repeat_threshold, consider_course_availability,
            consider_instructor_availability, consider_resource_constraints,
            consider_prerequisites, consider_required_course_load,
            consider_expected_demand, consider_capacity_balance,
            consider_time_conflicts, minimum_plan_score, hard_constraint_policy,
            soft_constraint_weight_json, is_active, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            scope_type,
            faculty_id,
            department_id,
            year,
            curriculum_year,
            defaults["total_elective_target"],
            defaults["fall_min"],
            defaults["fall_max"],
            defaults["spring_min"],
            defaults["spring_max"],
            defaults["max_semester_imbalance"],
            1 if defaults["allow_unbalanced_distribution"] else 0,
            defaults["same_course_repeat_policy"],
            1 if defaults["same_course_repeat_requires_approval"] else 0,
            defaults["high_demand_repeat_threshold"],
            1 if defaults["consider_course_availability"] else 0,
            1 if defaults["consider_instructor_availability"] else 0,
            1 if defaults["consider_resource_constraints"] else 0,
            1 if defaults["consider_prerequisites"] else 0,
            1 if defaults["consider_required_course_load"] else 0,
            1 if defaults["consider_expected_demand"] else 0,
            1 if defaults["consider_capacity_balance"] else 0,
            1 if defaults["consider_time_conflicts"] else 0,
            defaults["minimum_plan_score"],
            defaults["hard_constraint_policy"],
            defaults["soft_constraint_weight_json"],
            1 if activate else 0,
            now,
            now,
            notes,
        ),
    )
    return get_policy(conn, int(cur.lastrowid)) or {}


def _deactivate_same_scope(
    conn: sqlite3.Connection,
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
    curriculum_year: int | None,
) -> None:
    now = _now()
    where = ["scope_type = ?"]
    params: list[Any] = [scope_type]
    for col, value in (
        ("faculty_id", faculty_id),
        ("department_id", department_id),
        ("year", year),
        ("curriculum_year", curriculum_year),
    ):
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    conn.execute(
        f"UPDATE semester_planning_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
        tuple([now] + params),
    )


def update_policy(conn: sqlite3.Connection, policy_id: int, **values: Any) -> dict[str, Any]:
    policy = get_policy(conn, int(policy_id))
    if not policy:
        raise ValueError("Dönem planlama politikası bulunamadı.")
    allowed = {
        "name",
        "scope_type",
        "faculty_id",
        "department_id",
        "year",
        "curriculum_year",
        "total_elective_target",
        "fall_min",
        "fall_max",
        "spring_min",
        "spring_max",
        "max_semester_imbalance",
        "allow_unbalanced_distribution",
        "same_course_repeat_policy",
        "same_course_repeat_requires_approval",
        "high_demand_repeat_threshold",
        "consider_course_availability",
        "consider_instructor_availability",
        "consider_resource_constraints",
        "consider_prerequisites",
        "consider_required_course_load",
        "consider_expected_demand",
        "consider_capacity_balance",
        "consider_time_conflicts",
        "minimum_plan_score",
        "hard_constraint_policy",
        "soft_constraint_weight_json",
        "notes",
    }
    if "soft_constraint_weights" in values:
        values["soft_constraint_weight_json"] = _json(normalize_soft_weights(values.pop("soft_constraint_weights")))
    updates = {k: v for k, v in values.items() if k in allowed}
    merged = dict(policy)
    merged.update(updates)
    validation = validate_policy(merged)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    if not updates:
        return policy
    updates["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in updates)
    conn.execute(
        f"UPDATE semester_planning_policies SET {assignments} WHERE id = ?",
        tuple(updates.values()) + (int(policy_id),),
    )
    return get_policy(conn, int(policy_id)) or {}


def activate_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]:
    policy = get_policy(conn, int(policy_id))
    if not policy:
        raise ValueError("Dönem planlama politikası bulunamadı.")
    validation = validate_policy(policy)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    _deactivate_same_scope(
        conn,
        str(policy.get("scope_type") or "global"),
        policy.get("faculty_id"),
        policy.get("department_id"),
        policy.get("year"),
        policy.get("curriculum_year"),
    )
    conn.execute(
        "UPDATE semester_planning_policies SET is_active = 1, updated_at = ? WHERE id = ?",
        (_now(), int(policy_id)),
    )
    return get_policy(conn, int(policy_id)) or {}


def list_policies(
    conn: sqlite3.Connection,
    scope_type: str | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    seed_default_policy(conn)
    where = ["1=1"]
    params: list[Any] = []
    if scope_type:
        where.append("scope_type = ?")
        params.append(scope_type)
    if faculty_id is not None:
        where.append("faculty_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("department_id = ?")
        params.append(int(department_id))
    if year is not None:
        where.append("year = ?")
        params.append(int(year))
    if active_only:
        where.append("is_active = 1")
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM semester_planning_policies WHERE {' AND '.join(where)} ORDER BY is_active DESC, id DESC",
        tuple(params),
    )
    return _fetch_all_dicts(cur)


def resolve_policy(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    curriculum_year: int | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    seed_default_policy(conn)
    candidates = [
        ("department", faculty_id, department_id, year, curriculum_year),
        ("faculty", faculty_id, None, year, curriculum_year),
        ("department", faculty_id, department_id, None, None),
        ("faculty", faculty_id, None, None, None),
        ("global", None, None, year, curriculum_year),
        ("global", None, None, None, None),
    ]
    cur = conn.cursor()
    for scope, fid, bid, cand_year, cand_curriculum_year in candidates:
        if scope == "department" and department_id is None:
            continue
        if scope == "faculty" and faculty_id is None:
            continue
        where = ["scope_type = ?", "is_active = 1"]
        params: list[Any] = [scope]
        for col, value in (
            ("faculty_id", fid),
            ("department_id", bid),
            ("year", cand_year),
            ("curriculum_year", cand_curriculum_year),
        ):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(value)
        cur.execute(
            f"SELECT * FROM semester_planning_policies WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
            tuple(params),
        )
        row = _fetch_one_dict(cur)
        if row:
            return row
    return seed_default_policy(conn)

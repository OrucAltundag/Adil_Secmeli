# -*- coding: utf-8 -*-
"""Eksik kriter verisi risk skoru servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema

DEFAULT_FIELD_WEIGHTS = {
    "total_students": 0.18,
    "passed_students": 0.18,
    "average_grade": 0.22,
    "capacity": 0.16,
    "enrolled_students": 0.16,
    "survey_count": 0.06,
    "trend": 0.04,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _risk_level(score: float) -> str:
    if score >= 0.80:
        return "critical"
    if score >= 0.55:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def calculate_missing_data_risk(
    matrix_rows: list[dict[str, Any]],
    policy: dict[str, Any],
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    missing_required = sorted(
        {
            str(row.get("criterion_key"))
            for row in matrix_rows
            if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
        }
    )
    missing_optional = sorted(
        {
            str(row.get("criterion_key"))
            for row in matrix_rows
            if not row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
        }
    )
    required_weight = sum(DEFAULT_FIELD_WEIGHTS.get(field, 0.10) for field in missing_required)
    optional_weight = sum(DEFAULT_FIELD_WEIGHTS.get(field, 0.03) * 0.35 for field in missing_optional)
    affected_weight_sum = round(required_weight + optional_weight, 4)
    total_courses = max(1, len({row.get("course_id") for row in matrix_rows if row.get("course_id") is not None}))
    affected_courses = len(
        {
            row.get("course_id")
            for row in matrix_rows
            if row.get("course_id") is not None and (not row.get("is_present") or not row.get("is_valid"))
        }
    )
    course_factor = affected_courses / total_courses
    score = min(1.0, round((affected_weight_sum * 0.75) + (course_factor * 0.25), 4))
    level = _risk_level(score)
    if missing_required:
        explanation = (
            f"{len(missing_required)} zorunlu kriterde eksik/geçersiz veri var. "
            f"Etkilenen ağırlık toplamı yaklaşık {affected_weight_sum:.2f}; risk seviyesi {level}."
        )
    elif missing_optional:
        explanation = (
            f"Zorunlu kriterler tamam, ancak {len(missing_optional)} opsiyonel kriterde eksik veri var. "
            f"Karar riski {level} seviyesinde."
        )
    else:
        explanation = "Eksik kriter verisi tespit edilmedi; risk düşük."
    return {
        "scope_type": scope_type,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "course_id": course_id,
        "year": int(year),
        "semester": semester,
        "risk_score": score,
        "risk_level": level,
        "missing_required_fields": missing_required,
        "missing_optional_fields": missing_optional,
        "affected_weight_sum": affected_weight_sum,
        "explanation": explanation,
    }


def persist_missing_data_risk(conn: sqlite3.Connection, risk: dict[str, Any]) -> dict[str, Any]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM criteria_missing_data_risks
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(course_id, -1) = COALESCE(?, -1)
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
        """,
        (
            risk.get("scope_type"),
            risk.get("faculty_id"),
            risk.get("department_id"),
            risk.get("course_id"),
            int(risk.get("year")),
            risk.get("semester"),
        ),
    )
    cur.execute(
        """
        INSERT INTO criteria_missing_data_risks (
            scope_type, faculty_id, department_id, course_id, year, semester,
            risk_score, risk_level, missing_required_fields_json,
            missing_optional_fields_json, affected_weight_sum, explanation, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            risk.get("scope_type"),
            risk.get("faculty_id"),
            risk.get("department_id"),
            risk.get("course_id"),
            int(risk.get("year")),
            risk.get("semester"),
            float(risk.get("risk_score") or 0.0),
            risk.get("risk_level") or "low",
            _json_dumps(risk.get("missing_required_fields") or []),
            _json_dumps(risk.get("missing_optional_fields") or []),
            risk.get("affected_weight_sum"),
            risk.get("explanation"),
            _now(),
        ),
    )
    risk["id"] = int(cur.lastrowid)
    return risk


def get_missing_data_risk_report(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM criteria_missing_data_risks
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND course_id IS NULL
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
        ORDER BY id DESC
        LIMIT 1
        """,
        (scope_type, faculty_id, department_id, int(year), semester),
    )
    row = cur.fetchone()
    if not row:
        return None
    data = {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else {}
    for key in ("missing_required_fields_json", "missing_optional_fields_json"):
        try:
            data[key.replace("_json", "")] = json.loads(data.get(key) or "[]")
        except Exception:
            data[key.replace("_json", "")] = []
    return data

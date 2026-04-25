# -*- coding: utf-8 -*-
"""Zorunlu ders yuku ve donem workload metrikleri."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema
from app.services.course_semester_availability_service import normalize_semester


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}


def get_required_course_load(conn: sqlite3.Connection, department_id: int, year: int, semester: str) -> dict[str, Any] | None:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM semester_required_course_loads
        WHERE department_id = ? AND year = ? AND semester = ?
        ORDER BY id DESC LIMIT 1
        """,
        (int(department_id), int(year), normalize_semester(semester)),
    )
    return _row_to_dict(cur.fetchone(), [d[0] for d in cur.description] if cur.description else [])


def calculate_semester_workload(plan: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"fall": 0, "spring": 0}
    for item in plan:
        sem = str(item.get("assigned_semester") or "")
        if sem in counts:
            counts[sem] += 1
    return {
        "fall_workload": counts["fall"],
        "spring_workload": counts["spring"],
        "workload_imbalance": abs(counts["fall"] - counts["spring"]),
    }


def adjust_targets_by_required_load(policy: dict[str, Any], required_loads: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, Any], list[str]]:
    adjusted = dict(policy)
    warnings: list[str] = []
    for sem, max_field in (("fall", "fall_max"), ("spring", "spring_max")):
        load = (required_loads or {}).get(sem) or {}
        workload_score = float(load.get("workload_score") or 0.0)
        required_count = int(load.get("required_course_count") or 0)
        if workload_score >= 0.80 or required_count >= 6:
            adjusted[max_field] = max(int(adjusted.get(f"{sem}_min", 0) or 0), int(adjusted.get(max_field, 0) or 0) - 1)
            warnings.append(f"{'Güz' if sem == 'fall' else 'Bahar'} zorunlu ders yükü yüksek olduğu için seçmeli üst hedefi 1 azaltıldı.")
    return adjusted, warnings


def explain_workload_effect(policy: dict[str, Any], adjusted_policy: dict[str, Any]) -> str:
    if policy == adjusted_policy:
        return "Zorunlu ders yükü dönem hedeflerini değiştirmedi."
    return "Zorunlu ders yükü dönem seçmeli hedeflerine uyarı/ayar olarak yansıtıldı."

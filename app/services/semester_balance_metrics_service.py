# -*- coding: utf-8 -*-
"""Talep, kontenjan ve workload denge metrikleri."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def estimate_course_demand(conn: sqlite3.Connection, course_id: int, year: int) -> float:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    for query in (
        "SELECT anket_dersi_secen FROM ders_kriterleri WHERE ders_id = ? AND yil <= ? ORDER BY yil DESC, id DESC LIMIT 1",
        "SELECT talep_sayisi FROM populerlik WHERE ders_id = ? AND akademik_yil <= ? ORDER BY akademik_yil DESC, pop_id DESC LIMIT 1",
    ):
        try:
            cur.execute(query, (int(course_id), int(year)))
            row = cur.fetchone()
            if row and row[0] is not None:
                return max(0.0, _float(row[0]))
        except sqlite3.OperationalError:
            continue
    return 0.0


def estimate_course_capacity(conn: sqlite3.Connection, course_id: int, year: int) -> float:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    for query in (
        "SELECT kontenjan FROM ders_kriterleri WHERE ders_id = ? AND yil <= ? ORDER BY yil DESC, id DESC LIMIT 1",
        "SELECT kontenjan FROM populerlik WHERE ders_id = ? AND akademik_yil <= ? ORDER BY akademik_yil DESC, pop_id DESC LIMIT 1",
        "SELECT kontenjan FROM ders WHERE ders_id = ? LIMIT 1",
    ):
        try:
            params = (int(course_id), int(year)) if query.count("?") == 2 else (int(course_id),)
            cur.execute(query, params)
            row = cur.fetchone()
            if row and row[0] is not None:
                return max(0.0, _float(row[0]))
        except sqlite3.OperationalError:
            continue
    return 0.0


def calculate_semester_balance_metrics(plan: list[dict[str, Any]]) -> dict[str, Any]:
    fall = [p for p in plan if p.get("assigned_semester") == "fall"]
    spring = [p for p in plan if p.get("assigned_semester") == "spring"]
    fall_demand = sum(_float(p.get("expected_demand")) for p in fall)
    spring_demand = sum(_float(p.get("expected_demand")) for p in spring)
    fall_capacity = sum(_float(p.get("expected_capacity")) for p in fall)
    spring_capacity = sum(_float(p.get("expected_capacity")) for p in spring)
    fall_score = sum(_float(p.get("course_score")) for p in fall)
    spring_score = sum(_float(p.get("course_score")) for p in spring)
    return {
        "fall_course_count": len(fall),
        "spring_course_count": len(spring),
        "fall_expected_demand": fall_demand,
        "spring_expected_demand": spring_demand,
        "fall_total_capacity": fall_capacity,
        "spring_total_capacity": spring_capacity,
        "demand_imbalance": abs(fall_demand - spring_demand),
        "capacity_imbalance": abs(fall_capacity - spring_capacity),
        "workload_imbalance": abs(len(fall) - len(spring)),
        "fall_score_sum": fall_score,
        "spring_score_sum": spring_score,
    }


def calculate_plan_score(plan: list[dict[str, Any]], policy: dict[str, Any]) -> float:
    metrics = calculate_semester_balance_metrics(plan)
    weights = policy.get("soft_constraint_weights") or {
        "score": 0.40,
        "semester_balance": 0.20,
        "demand_balance": 0.15,
        "capacity_balance": 0.10,
    }
    selected = max(1, len([p for p in plan if p.get("assigned_semester") in {"fall", "spring"}]))
    avg_score = sum(_float(p.get("course_score")) for p in plan if p.get("assigned_semester") in {"fall", "spring"}) / selected
    semester_balance = max(0.0, 1.0 - min(metrics["workload_imbalance"], 8) / 8.0) * 100.0
    total_demand = max(1.0, metrics["fall_expected_demand"] + metrics["spring_expected_demand"])
    demand_balance = max(0.0, 1.0 - metrics["demand_imbalance"] / total_demand) * 100.0
    total_capacity = max(1.0, metrics["fall_total_capacity"] + metrics["spring_total_capacity"])
    capacity_balance = max(0.0, 1.0 - metrics["capacity_imbalance"] / total_capacity) * 100.0
    return round(
        avg_score * float(weights.get("score", 0.40))
        + semester_balance * float(weights.get("semester_balance", 0.20))
        + demand_balance * float(weights.get("demand_balance", 0.15))
        + capacity_balance * float(weights.get("capacity_balance", 0.10)),
        4,
    )


def generate_balance_warnings(metrics: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    max_imbalance = int(policy.get("max_semester_imbalance") or 0)
    if metrics.get("workload_imbalance", 0) > max_imbalance and not policy.get("allow_unbalanced_distribution"):
        warnings.append("Güz/Bahar ders sayısı hedeflenen dengenin dışında.")
    total_demand = float(metrics.get("fall_expected_demand", 0.0) + metrics.get("spring_expected_demand", 0.0))
    if total_demand > 0 and metrics.get("demand_imbalance", 0.0) / total_demand > 0.35:
        warnings.append("Ders sayısı dengeli olsa bile beklenen talep dönemler arasında belirgin dengesiz.")
    total_capacity = float(metrics.get("fall_total_capacity", 0.0) + metrics.get("spring_total_capacity", 0.0))
    if total_capacity > 0 and metrics.get("capacity_imbalance", 0.0) / total_capacity > 0.35:
        warnings.append("Kontenjan kapasitesi dönemler arasında belirgin dengesiz.")
    return warnings

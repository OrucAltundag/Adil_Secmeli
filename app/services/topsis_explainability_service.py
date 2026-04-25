# -*- coding: utf-8 -*-
"""TOPSIS score breakdown generation."""

from __future__ import annotations

import json
import math
import sqlite3
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return float(default)
        return value
    except (TypeError, ValueError):
        return float(default)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _normalize_weights(weights: dict[str, float], criteria_keys: list[str]) -> dict[str, float]:
    safe = {key: max(0.0, _safe_float(weights.get(key))) for key in criteria_keys}
    total = sum(safe.values()) or 1.0
    return {key: safe[key] / total for key in criteria_keys}


def calculate_topsis_breakdowns(
    course_rows: list[dict[str, Any]],
    weights: dict[str, float],
    criteria_keys: list[str] | None = None,
) -> dict[int, dict[str, Any]]:
    criteria = list(criteria_keys or ["basari", "trend", "populerlik", "anket"])
    if not course_rows:
        return {}
    normalized_weights = _normalize_weights(weights, criteria)

    sqrt_sums = {}
    for key in criteria:
        sq_sum = sum(_safe_float(row.get(key)) ** 2 for row in course_rows)
        sqrt_sums[key] = math.sqrt(sq_sum) if sq_sum > 1e-12 else 1.0

    normalized_rows = []
    weighted_rows = []
    for row in course_rows:
        normalized = {
            key: _safe_float(row.get(key)) / sqrt_sums[key]
            for key in criteria
        }
        weighted = {
            key: normalized[key] * normalized_weights[key]
            for key in criteria
        }
        normalized_rows.append(normalized)
        weighted_rows.append(weighted)

    positive = {key: max(row[key] for row in weighted_rows) for key in criteria}
    negative = {key: min(row[key] for row in weighted_rows) for key in criteria}

    breakdowns: dict[int, dict[str, Any]] = {}
    for idx, row in enumerate(course_rows):
        course_id = int(row.get("ders_id") or row.get("course_id") or 0)
        weighted = weighted_rows[idx]
        normalized = normalized_rows[idx]
        s_plus = math.sqrt(sum((weighted[key] - positive[key]) ** 2 for key in criteria))
        s_minus = math.sqrt(sum((weighted[key] - negative[key]) ** 2 for key in criteria))
        denominator = s_plus + s_minus
        closeness = s_minus / denominator if denominator > 1e-12 else 0.0
        contribution = {key: weighted[key] for key in criteria}
        breakdowns[course_id] = {
            "course_id": course_id,
            "raw_values": {key: _safe_float(row.get(key)) for key in criteria},
            "normalized_values": normalized,
            "weighted_values": weighted,
            "weights": normalized_weights,
            "positive_distance": s_plus,
            "negative_distance": s_minus,
            "closeness_coefficient": closeness,
            "final_score": closeness * 100.0,
            "contribution": contribution,
        }
    return breakdowns


def save_score_breakdown(
    cur: sqlite3.Cursor,
    decision_run_id: int | None,
    course_id: int,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    breakdown: dict[str, Any],
    ahp_profile_id: int | None = None,
) -> int:
    payload = (
        decision_run_id,
        int(course_id),
        int(year),
        faculty_id,
        department_id,
        _json_dump(breakdown.get("raw_values", {})),
        _json_dump(breakdown.get("normalized_values", {})),
        _json_dump(breakdown.get("weighted_values", {})),
        _json_dump(breakdown.get("weights", {})),
        float(breakdown.get("positive_distance") or 0.0),
        float(breakdown.get("negative_distance") or 0.0),
        float(breakdown.get("closeness_coefficient") or 0.0),
        float(breakdown.get("final_score") or 0.0),
        _json_dump(breakdown.get("contribution", {})),
    )
    try:
        cur.execute(
            """
            INSERT INTO course_score_breakdowns (
                decision_run_id, course_id, year, faculty_id, department_id,
                raw_values_json, normalized_values_json, weighted_values_json,
                weights_json, positive_distance, negative_distance,
                closeness_coefficient, final_score, contribution_json,
                ahp_profile_id, weighted_contribution_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                *payload,
                ahp_profile_id,
                _json_dump(breakdown.get("contribution", {})),
            ),
        )
    except sqlite3.OperationalError:
        # Eski snapshot semalarında yeni kolonlar olmayabilir; runtime schema
        # compatibility çalışana kadar eski insert şekliyle geriye uyum sağlanır.
        cur.execute(
            """
            INSERT INTO course_score_breakdowns (
                decision_run_id, course_id, year, faculty_id, department_id,
                raw_values_json, normalized_values_json, weighted_values_json,
                weights_json, positive_distance, negative_distance,
                closeness_coefficient, final_score, contribution_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
    return int(cur.lastrowid)


def short_score_explanation(breakdown: dict[str, Any]) -> str:
    raw = dict(breakdown.get("raw_values") or {})
    weights = dict(breakdown.get("weights") or {})
    if not raw:
        return "Skor kirilimi icin yeterli veri bulunmuyor."
    ordered_positive = sorted(raw.items(), key=lambda item: item[1] * float(weights.get(item[0], 0.0)), reverse=True)
    top = [key for key, _ in ordered_positive[:2]]
    weak = [key for key, value in ordered_positive[-2:] if value < 0.55]
    text = "Bu dersin skoru "
    if top:
        text += ", ".join(top) + " kriterlerindeki katkilarla olustu"
    if weak:
        text += "; " + ", ".join(weak) + " alanlari skoru sinirladi"
    return text + "."

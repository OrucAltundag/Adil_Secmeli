# -*- coding: utf-8 -*-
"""Sensitivity analysis for threshold-adjacent decisions."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.services.decision_policy_service import classify_score


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _thresholds(policy: dict[str, Any]) -> list[tuple[str, float]]:
    out = [
        ("curriculum_keep_threshold", float(policy.get("curriculum_keep_threshold", 70.0))),
        ("pool_threshold", float(policy.get("pool_threshold", 50.0))),
        ("rest_threshold", float(policy.get("rest_threshold", 40.0))),
    ]
    if policy.get("cancel_candidate_threshold") is not None:
        out.append(("cancel_candidate_threshold", float(policy.get("cancel_candidate_threshold"))))
    return out


def analyze_decision_sensitivity(
    score: float,
    policy: dict[str, Any],
    weights: dict[str, float] | None = None,
    raw_values: dict[str, float] | None = None,
) -> dict[str, Any]:
    base_score = float(score or 0.0)
    margin = float(policy.get("sensitivity_margin", 3.0) or 3.0)
    base_status = classify_score(base_score, policy)["recommended_status"]

    tested = []
    min_score = base_score
    max_score = base_score
    if weights and raw_values:
        for key, weight in weights.items():
            for delta in (-0.05, 0.05):
                varied = dict(weights)
                varied[key] = max(0.0, float(weight) * (1.0 + delta))
                total = sum(varied.values()) or 1.0
                varied = {k: v / total for k, v in varied.items()}
                weighted_raw = sum(float(raw_values.get(k, 0.0)) * varied.get(k, 0.0) for k in varied)
                varied_score = max(0.0, min(100.0, weighted_raw * 100.0))
                tested.append({"criterion": key, "delta": delta, "score": varied_score})
                min_score = min(min_score, varied_score)
                max_score = max(max_score, varied_score)
    else:
        min_score = max(0.0, base_score - margin)
        max_score = min(100.0, base_score + margin)
        tested.append({"method": "threshold_margin", "margin": margin})

    statuses = {
        classify_score(min_score, policy)["recommended_status"],
        classify_score(max_score, policy)["recommended_status"],
        base_status,
    }
    decision_changed = len(statuses) > 1

    nearest_name = None
    nearest_distance = None
    for name, threshold in _thresholds(policy):
        distance = abs(base_score - threshold)
        if nearest_distance is None or distance < nearest_distance:
            nearest_name = name
            nearest_distance = distance

    score_range = max_score - min_score
    if decision_changed or (nearest_distance is not None and nearest_distance <= margin):
        stability = "low"
        explanation = "Bu ders karar esigine yakin oldugu icin karar hassastir; akademik kurul incelemesi onerilir."
    elif score_range > margin * 2:
        stability = "medium"
        explanation = "Agirlik degisimleri skoru etkiliyor, ancak karar sinifi korunuyor."
    else:
        stability = "high"
        explanation = "Kucuk agirlik/esik degisimlerinde karar sinifi korunuyor."

    return {
        "base_score": base_score,
        "min_score": min_score,
        "max_score": max_score,
        "score_range": score_range,
        "decision_changed": decision_changed,
        "stability_level": stability,
        "tested_variations": tested,
        "nearest_threshold": nearest_name,
        "nearest_threshold_distance": nearest_distance,
        "explanation": explanation,
    }


def save_sensitivity_result(
    cur: sqlite3.Cursor,
    decision_run_id: int,
    course_id: int,
    sensitivity: dict[str, Any],
) -> int:
    cur.execute(
        """
        INSERT INTO decision_sensitivity_results (
            decision_run_id, course_id, base_score, min_score, max_score,
            score_range, decision_changed, stability_level,
            tested_variations_json, explanation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(decision_run_id),
            int(course_id),
            float(sensitivity.get("base_score") or 0.0),
            float(sensitivity.get("min_score") or 0.0),
            float(sensitivity.get("max_score") or 0.0),
            float(sensitivity.get("score_range") or 0.0),
            1 if sensitivity.get("decision_changed") else 0,
            str(sensitivity.get("stability_level") or "medium"),
            _json_dump(sensitivity.get("tested_variations", [])),
            str(sensitivity.get("explanation") or ""),
        ),
    )
    return int(cur.lastrowid)

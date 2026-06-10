# -*- coding: utf-8 -*-
"""AHP ağırlık duyarlılığı analizi servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema
from app.services.ahp_calculation_service import normalize_weights


def perturb_weights(weights: dict[str, float], criterion_key: str, delta: float) -> dict[str, float]:
    adjusted = {key: float(value or 0.0) for key, value in dict(weights or {}).items()}
    if criterion_key not in adjusted:
        return normalize_weights(adjusted)
    adjusted[criterion_key] = max(0.0, adjusted[criterion_key] * (1.0 + float(delta)))
    return normalize_weights(adjusted)


def run_weight_sensitivity_analysis(
    conn: sqlite3.Connection,
    decision_run_id: int,
    variation_percent: float = 0.05,
) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_runs WHERE id=?", (int(decision_run_id),))
    run = cur.fetchone()
    if not run:
        raise ValueError(f"Karar çalışması bulunamadı: {decision_run_id}")
    cur.execute(
        """
        SELECT *
        FROM course_score_breakdowns
        WHERE decision_run_id=?
        ORDER BY course_id
        """,
        (int(decision_run_id),),
    )
    rows = cur.fetchall()
    if not rows:
        raise ValueError("Sensitivity analizi için TOPSIS skor kırılımı bulunamadı.")

    base_weights = _json_load(run["ahp_weights_snapshot_json"], {})
    if not base_weights:
        base_weights = _json_load(rows[0]["weights_json"], {})
    criteria = list(base_weights.keys())
    variations = []
    for key in criteria:
        variations.append({"criterion_key": key, "delta": float(variation_percent)})
        variations.append({"criterion_key": key, "delta": -float(variation_percent)})

    items: list[dict[str, Any]] = []
    sensitive_courses: list[dict[str, Any]] = []
    stability_counts = {"high": 0, "medium": 0, "low": 0}
    for row in rows:
        raw_values = _json_load(row["raw_values_json"], {})
        base_score = float(row["final_score"] or 0.0)
        scores = [base_score]
        for variation in variations:
            varied_weights = perturb_weights(base_weights, variation["criterion_key"], variation["delta"])
            scores.append(_weighted_score(raw_values, varied_weights))
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
        stability = "high" if score_range < 3.0 else "medium" if score_range < 7.0 else "low"
        stability_counts[stability] += 1
        base_decision = _decision_bucket(base_score)
        changed_decisions = sorted({_decision_bucket(score) for score in scores if _decision_bucket(score) != base_decision})
        changed_decision = ", ".join(changed_decisions) if changed_decisions else None
        explanation = (
            f"Ağırlıklar ±%{float(variation_percent) * 100:.1f} değiştiğinde skor "
            f"{min_score:.2f}-{max_score:.2f} aralığında kaldı."
        )
        if changed_decision:
            explanation += f" Karar eşiği değişim riski: {changed_decision}."
        item = {
            "course_id": int(row["course_id"]),
            "base_score": base_score,
            "min_score": min_score,
            "max_score": max_score,
            "score_range": score_range,
            "base_decision": base_decision,
            "changed_decision": changed_decision,
            "stability_level": stability,
            "explanation": explanation,
        }
        items.append(item)
        if stability == "low" or changed_decision:
            sensitive_courses.append(item)

    cur.execute(
        """
        INSERT INTO ahp_sensitivity_results (
            decision_run_id, ahp_profile_id, variation_percent, tested_variations_json,
            affected_courses_count, sensitive_courses_json, stability_summary_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(decision_run_id),
            run["ahp_profile_id"],
            float(variation_percent),
            _json(variations),
            len(sensitive_courses),
            _json(sensitive_courses),
            _json(stability_counts),
            _now(),
        ),
    )
    result_id = int(cur.lastrowid or 0)
    for item in items:
        cur.execute(
            """
            INSERT INTO ahp_course_sensitivity_items (
                sensitivity_result_id, course_id, base_score, min_score, max_score,
                score_range, base_decision, changed_decision, stability_level,
                explanation, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                item["course_id"],
                item["base_score"],
                item["min_score"],
                item["max_score"],
                item["score_range"],
                item["base_decision"],
                item["changed_decision"],
                item["stability_level"],
                item["explanation"],
                _now(),
            ),
        )
    conn.commit()
    return get_sensitivity_result(conn, result_id)


def get_sensitivity_result(conn: sqlite3.Connection, result_id: int) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM ahp_sensitivity_results WHERE id=?", (int(result_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Sensitivity sonucu bulunamadı: {result_id}")
    result = _row_dict(row)
    result["tested_variations"] = _json_load(result.get("tested_variations_json"), [])
    result["sensitive_courses"] = _json_load(result.get("sensitive_courses_json"), [])
    result["stability_summary"] = _json_load(result.get("stability_summary_json"), {})
    cur.execute(
        "SELECT * FROM ahp_course_sensitivity_items WHERE sensitivity_result_id=? ORDER BY stability_level DESC, score_range DESC",
        (int(result_id),),
    )
    result["items"] = [_row_dict(item) for item in cur.fetchall()]
    return result


def get_latest_sensitivity_for_run(conn: sqlite3.Connection, decision_run_id: int) -> dict[str, Any] | None:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM ahp_sensitivity_results WHERE decision_run_id=? ORDER BY id DESC LIMIT 1",
        (int(decision_run_id),),
    )
    row = cur.fetchone()
    return get_sensitivity_result(conn, int(row["id"])) if row else None


def _weighted_score(raw_values: dict[str, Any], weights: dict[str, float]) -> float:
    score = 0.0
    for key, weight in weights.items():
        value = _safe_float(raw_values.get(key))
        if value <= 1.0:
            value *= 100.0
        score += value * float(weight or 0.0)
    return max(0.0, min(100.0, score))


def _decision_bucket(score: float) -> str:
    if score >= 70.0:
        return "mufredat"
    if score >= 50.0:
        return "havuz"
    if score >= 40.0:
        return "dinlenme"
    return "iptal_adayi"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

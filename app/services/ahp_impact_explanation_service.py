# -*- coding: utf-8 -*-
"""AHP ağırlık etkisi ve insan okunabilir açıklama servisi."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema
from app.services.ahp_profile_service import get_profile


def explain_weight_profile(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    weights = dict(profile.get("weights") or {})
    ordered = sorted(weights.items(), key=lambda item: float(item[1] or 0.0), reverse=True)
    highest = ordered[0] if ordered else (None, 0.0)
    lowest = ordered[-1] if ordered else (None, 0.0)
    return {
        "profile": profile,
        "highest_weight": {"criterion_key": highest[0], "weight": highest[1]},
        "lowest_weight": {"criterion_key": lowest[0], "weight": lowest[1]},
        "weight_table": [
            {"criterion_key": key, "weight": value, "percent": round(float(value) * 100.0, 2)}
            for key, value in ordered
        ],
        "summary_text": generate_ahp_human_readable_summary(profile),
    }


def generate_ahp_human_readable_summary(profile: dict[str, Any]) -> str:
    weights = dict(profile.get("weights") or {})
    if not weights:
        return "Bu AHP profili için ağırlık bilgisi bulunmuyor."
    ordered = sorted(weights.items(), key=lambda item: float(item[1] or 0.0), reverse=True)
    top_key, top_weight = ordered[0]
    low_key, low_weight = ordered[-1]
    cr = profile.get("consistency_ratio")
    cr_text = f"CR: {float(cr):.3f}" if cr is not None else "CR bilgisi yok"
    status_text = "tutarlı" if profile.get("is_consistent") else "tutarlılık uyarılı"
    return (
        f"{profile.get('profile_name') or profile.get('name')} profilinde en yüksek ağırlık "
        f"{top_key} kriterindedir (%{float(top_weight) * 100:.1f}). En düşük ağırlık "
        f"{low_key} kriterindedir (%{float(low_weight) * 100:.1f}). Profil {status_text}; {cr_text}."
    )


def generate_weight_impact_table(score_breakdown: dict[str, Any]) -> list[dict[str, Any]]:
    weights = dict(score_breakdown.get("weights") or {})
    raw = dict(score_breakdown.get("raw_values") or {})
    contribution = dict(score_breakdown.get("contribution") or score_breakdown.get("weighted_values") or {})
    rows = []
    for key in sorted(set(weights) | set(raw) | set(contribution)):
        rows.append(
            {
                "criterion_key": key,
                "raw_value": _safe_float(raw.get(key)),
                "weight": _safe_float(weights.get(key)),
                "weighted_contribution": _safe_float(contribution.get(key)),
            }
        )
    return sorted(rows, key=lambda row: row["weighted_contribution"], reverse=True)


def explain_course_weight_contribution(
    conn: sqlite3.Connection,
    course_id: int,
    decision_run_id: int,
) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT csb.*, d.kod AS course_code, d.ad AS course_name
        FROM course_score_breakdowns csb
        LEFT JOIN ders d ON d.ders_id = csb.course_id
        WHERE csb.course_id=? AND csb.decision_run_id=?
        ORDER BY csb.id DESC
        LIMIT 1
        """,
        (int(course_id), int(decision_run_id)),
    )
    row = cur.fetchone()
    if not row:
        return {
            "course_id": int(course_id),
            "decision_run_id": int(decision_run_id),
            "impact_table": [],
            "human_readable_text": "Bu ders için AHP/TOPSIS skor kırılımı bulunamadı.",
        }
    breakdown = {
        "weights": _json_load(row["weights_json"], {}),
        "raw_values": _json_load(row["raw_values_json"], {}),
        "weighted_values": _json_load(row["weighted_values_json"], {}),
        "contribution": _json_load(row["weighted_contribution_json"] if "weighted_contribution_json" in row.keys() else row["contribution_json"], {}),
        "final_score": row["final_score"],
    }
    table = generate_weight_impact_table(breakdown)
    top = table[0] if table else None
    course_label = row["course_code"] or row["course_name"] or str(course_id)
    if top:
        text = (
            f"{course_label} dersinde en yüksek AHP katkısı {top['criterion_key']} kriterinden gelmiştir. "
            f"Bu kriterin ağırlığı %{top['weight'] * 100:.1f}, ağırlıklı katkısı {top['weighted_contribution']:.4f}."
        )
    else:
        text = "Bu ders için katkı hesaplanamadı."
    return {
        "course_id": int(course_id),
        "decision_run_id": int(decision_run_id),
        "course_code": row["course_code"],
        "course_name": row["course_name"],
        "final_score": row["final_score"],
        "impact_table": table,
        "human_readable_text": text,
    }


def _json_load(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


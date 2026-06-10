# -*- coding: utf-8 -*-
"""Human and machine readable decision explanation builder."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.services.decision_policy_service import status_label


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_decision_explanation(
    course_code: str | None,
    course_name: str | None,
    decision: dict[str, Any],
    breakdown: dict[str, Any] | None = None,
    trend: dict[str, Any] | None = None,
    confidence: dict[str, Any] | None = None,
    governance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = float(decision.get("topsis_score") or 0.0)
    recommended = decision.get("recommended_status")
    final_status = decision.get("final_status", recommended)
    trend_label = (trend or {}).get("trend_label") or decision.get("trend_label")
    confidence_level = (confidence or {}).get("level") or "unknown"
    course_label = str(course_code or course_name or decision.get("course_id") or "Ders")

    positive_factors: list[str] = []
    negative_factors: list[str] = []
    secondary_reasons: list[str] = []

    raw = dict((breakdown or {}).get("raw_values") or {})
    for key, value in raw.items():
        try:
            value_f = float(value)
        except (TypeError, ValueError):
            continue
        if value_f >= 0.70:
            positive_factors.append(f"{key} guclu")
        elif value_f < 0.45:
            negative_factors.append(f"{key} zayif")

    if score >= 70:
        main_reason = "Yuksek TOPSIS skoru"
    elif score < 40:
        main_reason = "Dusuk TOPSIS skoru"
    else:
        main_reason = "Orta seviye TOPSIS skoru"

    if trend_label == "falling":
        negative_factors.append("son yillarda dusus egilimi")
        secondary_reasons.append("Son yillarda dusus egilimi gozlenmistir.")
    elif trend_label == "rising":
        positive_factors.append("son yillarda yukselis egilimi")
        secondary_reasons.append("Son yillarda yukselis egilimi gozlenmistir.")
    elif trend_label == "volatile":
        negative_factors.append("dalgalı trend")
        secondary_reasons.append("Trend dalgali oldugu icin karar temkinli yorumlanmalidir.")
    elif trend_label in {"new_course", "insufficient_data"}:
        secondary_reasons.append("Trend icin yeterli gecmis veri bulunmuyor.")

    if confidence_level == "low":
        negative_factors.append("dusuk veri guveni")
        secondary_reasons.append("Karar dusuk veri guveniyle uretilmistir; akademik inceleme onerilir.")
    elif confidence_level == "medium":
        secondary_reasons.append("Veri guveni orta seviyededir.")

    governance = governance or {}
    if governance.get("strategic_flag"):
        positive_factors.append("stratejik koruma")
        secondary_reasons.append("Ders stratejik olarak isaretlendigi icin otomatik iptal uygulanmamistir.")
    if governance.get("accreditation_flag"):
        positive_factors.append("akreditasyon korumasi")
        secondary_reasons.append("Ders akreditasyon kapsaminda korumalidir.")

    if decision.get("approval_required"):
        secondary_reasons.append("Bu karar akademik onay gerektirir.")

    human_parts = [
        f"{course_label} icin onerilen karar: {status_label(recommended)}; final durum: {status_label(final_status)}.",
        f"TOPSIS skoru {score:.1f}.",
    ]
    if secondary_reasons:
        human_parts.append(" ".join(secondary_reasons))
    elif positive_factors:
        human_parts.append("Karar olumlu faktorlerle desteklenmektedir.")
    if negative_factors and not secondary_reasons:
        human_parts.append("Dikkat edilmesi gereken faktorler: " + ", ".join(negative_factors) + ".")

    return {
        "main_reason": main_reason,
        "secondary_reasons": secondary_reasons,
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "rule_triggered": decision.get("rule_triggered"),
        "confidence_level": confidence_level,
        "human_readable_text": " ".join(human_parts),
    }


def save_decision_explanation(
    cur: sqlite3.Cursor,
    course_decision_id: int,
    explanation: dict[str, Any],
) -> int:
    cur.execute(
        """
        INSERT INTO course_decision_explanations (
            course_decision_id, main_reason, secondary_reasons_json,
            positive_factors_json, negative_factors_json, rule_triggered,
            confidence_level, human_readable_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(course_decision_id),
            str(explanation.get("main_reason") or ""),
            _json_dump(explanation.get("secondary_reasons", [])),
            _json_dump(explanation.get("positive_factors", [])),
            _json_dump(explanation.get("negative_factors", [])),
            explanation.get("rule_triggered"),
            explanation.get("confidence_level"),
            explanation.get("human_readable_text"),
        ),
    )
    return int(cur.lastrowid or 0)

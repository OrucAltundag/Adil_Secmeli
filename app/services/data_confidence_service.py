# -*- coding: utf-8 -*-
"""Data confidence scoring for course decisions."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def confidence_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def calculate_data_confidence(
    has_success_data: bool,
    has_popularity_data: bool,
    has_survey_data: bool,
    has_trend_data: bool,
    has_recent_data: bool,
    survey_count: int | None = None,
    data_points_count: int = 0,
    min_survey_count: int | None = None,
) -> dict[str, Any]:
    min_survey = int(min_survey_count or 10)
    score = 0.0
    missing_fields = []

    if has_success_data:
        score += 0.20
    else:
        missing_fields.append("basari")
    if has_popularity_data:
        score += 0.20
    else:
        missing_fields.append("populerlik")
    if has_survey_data:
        score += 0.20
    else:
        missing_fields.append("anket")
    if has_trend_data:
        score += 0.20
    else:
        missing_fields.append("trend")
    if has_recent_data:
        score += 0.10
    else:
        missing_fields.append("guncel_veri")
    if survey_count is not None and int(survey_count or 0) >= min_survey:
        score += 0.10
    elif has_survey_data:
        missing_fields.append("anket_orneklem")

    score = max(0.0, min(1.0, score))
    level = confidence_level(score)
    if missing_fields:
        explanation = (
            f"Veri guveni {score:.2f} / {level}. Eksik veya zayif alanlar: "
            + ", ".join(missing_fields)
            + ". Eksik kriterlerde hesaplama guvenli varsayilan/fallback degerlerle surduruldu."
        )
    else:
        explanation = f"Veri guveni {score:.2f} / {level}. Karar icin temel veri kaynaklari mevcut."

    return {
        "score": score,
        "level": level,
        "has_success_data": bool(has_success_data),
        "has_popularity_data": bool(has_popularity_data),
        "has_survey_data": bool(has_survey_data),
        "has_trend_data": bool(has_trend_data),
        "has_recent_data": bool(has_recent_data),
        "survey_count": survey_count,
        "data_points_count": int(data_points_count or 0),
        "missing_fields": missing_fields,
        "explanation": explanation,
    }


def calculate_course_data_confidence(
    cur: sqlite3.Cursor,
    course_id: int,
    year: int,
    semester: str | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    term_key = "b" if str(semester or "").strip().lower().startswith("b") else "g"
    has_success = False
    has_popularity = False
    has_survey = False
    survey_count = None
    has_recent = False

    try:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                   kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = ?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(course_id), int(year), term_key),
        )
        row = cur.fetchone()
        if row:
            toplam = _safe_float(row[0])
            gecen = _safe_float(row[1])
            ort = _safe_float(row[2])
            kontenjan = _safe_float(row[3])
            kayitli = _safe_float(row[4])
            survey_count = int(_safe_float(row[5], 0.0))
            survey_selected = _safe_float(row[6], 0.0)
            has_success = toplam > 0 and gecen >= 0 and ort > 0
            has_popularity = kontenjan > 0 and kayitli >= 0
            has_survey = survey_count > 0 and survey_selected >= 0
            has_recent = has_success or has_popularity or has_survey
    except sqlite3.OperationalError:
        pass

    if not has_success:
        try:
            cur.execute(
                """
                SELECT basari_orani, ortalama_not
                FROM performans
                WHERE ders_id = ? AND akademik_yil = ?
                ORDER BY pfrs_id DESC
                LIMIT 1
                """,
                (int(course_id), int(year)),
            )
            pf = cur.fetchone()
            has_success = bool(pf and (_safe_float(pf[0]) > 0 or _safe_float(pf[1]) > 0))
            has_recent = has_recent or has_success
        except sqlite3.OperationalError:
            pass

    if not has_popularity:
        try:
            cur.execute(
                """
                SELECT doluluk_orani, kontenjan
                FROM populerlik
                WHERE ders_id = ? AND akademik_yil = ?
                ORDER BY pop_id DESC
                LIMIT 1
                """,
                (int(course_id), int(year)),
            )
            pop = cur.fetchone()
            has_popularity = bool(pop and (_safe_float(pop[0]) > 0 or _safe_float(pop[1]) > 0))
            has_recent = has_recent or has_popularity
        except sqlite3.OperationalError:
            pass

    try:
        cur.execute(
            """
            SELECT COUNT(DISTINCT akademik_yil)
            FROM performans
            WHERE ders_id = ? AND akademik_yil <= ? AND basari_orani IS NOT NULL
            """,
            (int(course_id), int(year)),
        )
        data_points = int(cur.fetchone()[0] or 0)
    except sqlite3.OperationalError:
        data_points = 0
    has_trend = data_points >= 2

    return calculate_data_confidence(
        has_success_data=has_success,
        has_popularity_data=has_popularity,
        has_survey_data=has_survey,
        has_trend_data=has_trend,
        has_recent_data=has_recent,
        survey_count=survey_count,
        data_points_count=data_points,
        min_survey_count=(policy or {}).get("min_survey_count"),
    )


def save_data_confidence(
    cur: sqlite3.Cursor,
    decision_run_id: int | None,
    course_id: int,
    year: int,
    confidence: dict[str, Any],
) -> int:
    cur.execute(
        """
        INSERT INTO course_data_confidence (
            decision_run_id, course_id, year, score, level,
            has_success_data, has_popularity_data, has_survey_data,
            has_trend_data, has_recent_data, survey_count, data_points_count,
            missing_fields_json, explanation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_run_id,
            int(course_id),
            int(year),
            float(confidence["score"]),
            str(confidence["level"]),
            1 if confidence["has_success_data"] else 0,
            1 if confidence["has_popularity_data"] else 0,
            1 if confidence["has_survey_data"] else 0,
            1 if confidence["has_trend_data"] else 0,
            1 if confidence["has_recent_data"] else 0,
            confidence.get("survey_count"),
            int(confidence.get("data_points_count") or 0),
            _json_dump(confidence.get("missing_fields", [])),
            str(confidence.get("explanation") or ""),
        ),
    )
    return int(cur.lastrowid or 0)

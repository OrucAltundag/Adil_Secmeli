# -*- coding: utf-8 -*-
"""Advanced trend scoring and labeling for course performance history."""

from __future__ import annotations

import json
import math
import sqlite3
from statistics import pstdev
from typing import Any

TREND_DEFAULT_WEIGHTS = (0.50, 0.30, 0.20)


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


def weighted_trend_score(values_by_year: dict[int, float]) -> float:
    ordered = sorted(
        ((int(y), max(0.0, min(1.0, _safe_float(v)))) for y, v in values_by_year.items()),
        key=lambda item: item[0],
        reverse=True,
    )[: len(TREND_DEFAULT_WEIGHTS)]
    if not ordered:
        return 0.0
    usable = []
    for idx, (year, value) in enumerate(ordered):
        if value > 0:
            usable.append((year, value, TREND_DEFAULT_WEIGHTS[idx]))
    if not usable:
        return 0.0
    weight_sum = sum(item[2] for item in usable) or 1.0
    return sum(value * weight / weight_sum for _, value, weight in usable)


def analyze_trend_values(
    values_by_year: dict[int, float],
    target_year: int | None = None,
    first_seen_year: int | None = None,
    rising_threshold: float = 0.08,
    stable_threshold: float = 0.04,
    volatility_threshold: float = 0.18,
) -> dict[str, Any]:
    clean = {
        int(year): max(0.0, min(1.0, _safe_float(value)))
        for year, value in values_by_year.items()
        if value is not None
    }
    ordered = sorted(clean.items(), key=lambda item: item[0])
    data_points = len(ordered)
    if data_points == 0:
        return {
            "values_by_year": {},
            "trend_score": 0.0,
            "trend_label": "insufficient_data",
            "volatility_score": None,
            "data_points_count": 0,
            "explanation": "Trend icin yeterli gecmis veri bulunmuyor.",
        }
    if data_points == 1:
        label = "new_course" if target_year is not None and first_seen_year == target_year else "insufficient_data"
        explanation = (
            "Ders yeni gorundugu icin trend karari temkinli yorumlanmalidir."
            if label == "new_course"
            else "Trend icin yalnizca bir veri noktasi var."
        )
        return {
            "values_by_year": clean,
            "trend_score": weighted_trend_score(clean),
            "trend_label": label,
            "volatility_score": 0.0,
            "data_points_count": data_points,
            "explanation": explanation,
        }

    values = [value for _, value in ordered]
    volatility = pstdev(values) if len(values) > 1 else 0.0
    recent_values = values[-3:]
    total_change = recent_values[-1] - recent_values[0]
    step_changes = [recent_values[i] - recent_values[i - 1] for i in range(1, len(recent_values))]

    if volatility >= volatility_threshold and any(change > stable_threshold for change in step_changes) and any(
        change < -stable_threshold for change in step_changes
    ):
        label = "volatile"
        explanation = "Dersin gecmis degerleri belirgin dalgalanma gosteriyor."
    elif total_change >= rising_threshold and step_changes[-1] >= 0:
        label = "rising"
        explanation = "Dersin basari/talep gosterimleri son yillarda artis egiliminde."
    elif total_change <= -rising_threshold and step_changes[-1] <= 0:
        label = "falling"
        explanation = "Dersin basari/talep gosterimleri son yillarda dusus egiliminde."
    elif abs(total_change) <= stable_threshold and volatility < volatility_threshold:
        label = "stable"
        explanation = "Dersin gecmis performansi genel olarak dengeli seyrediyor."
    elif volatility >= volatility_threshold:
        label = "volatile"
        explanation = "Dersin trendi karar icin dalgali kabul edildi."
    else:
        label = "stable"
        explanation = "Belirgin yukselis veya dusus yok; trend stabil kabul edildi."

    return {
        "values_by_year": clean,
        "trend_score": weighted_trend_score(clean),
        "trend_label": label,
        "volatility_score": float(volatility),
        "data_points_count": data_points,
        "explanation": explanation,
    }


def analyze_course_trend(
    cur: sqlite3.Cursor,
    course_id: int,
    year: int,
) -> dict[str, Any]:
    values: dict[int, float] = {}
    try:
        cur.execute(
            """
            SELECT akademik_yil, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil <= ? AND basari_orani IS NOT NULL
            ORDER BY akademik_yil
            """,
            (int(course_id), int(year)),
        )
        for row in cur.fetchall():
            values[int(row[0])] = _safe_float(row[1])
    except sqlite3.OperationalError:
        pass

    if not values:
        try:
            cur.execute(
                """
                SELECT yil,
                       CASE WHEN toplam_ogrenci > 0 THEN CAST(gecen_ogrenci AS REAL) / toplam_ogrenci ELSE NULL END
                FROM ders_kriterleri
                WHERE ders_id = ? AND yil <= ?
                ORDER BY yil
                """,
                (int(course_id), int(year)),
            )
            for row in cur.fetchall():
                if row[1] is not None:
                    values[int(row[0])] = _safe_float(row[1])
        except sqlite3.OperationalError:
            pass

    first_seen = min(values.keys()) if values else None
    return analyze_trend_values(values, target_year=int(year), first_seen_year=first_seen)


def save_trend_analysis(
    cur: sqlite3.Cursor,
    decision_run_id: int | None,
    course_id: int,
    year: int,
    trend: dict[str, Any],
) -> int:
    cur.execute(
        """
        INSERT INTO course_trend_analysis (
            decision_run_id, course_id, year, values_by_year_json,
            trend_score, trend_label, volatility_score, data_points_count, explanation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_run_id,
            int(course_id),
            int(year),
            _json_dump(trend.get("values_by_year", {})),
            float(trend.get("trend_score") or 0.0),
            str(trend.get("trend_label") or "insufficient_data"),
            trend.get("volatility_score"),
            int(trend.get("data_points_count") or 0),
            str(trend.get("explanation") or ""),
        ),
    )
    return int(cur.lastrowid)

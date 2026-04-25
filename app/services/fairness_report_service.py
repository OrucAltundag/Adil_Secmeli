# -*- coding: utf-8 -*-
"""Fairness reporting for decision runs."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any

from app.services.havuz_karar import STATU_DINLENMEDE, STATU_HAVUZDA, STATU_IPTAL, STATU_MUFREDATTA


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def generate_fairness_report(
    cur: sqlite3.Cursor,
    decision_run_id: int,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    cur.execute(
        """
        SELECT cd.course_id, cd.final_status, cd.recommended_status,
               cd.department_id, cd.semester, cd.data_confidence_score,
               cd.decision_stability, cd.approval_required, cd.topsis_score,
               d.ad, d.kod
        FROM course_decisions cd
        LEFT JOIN ders d ON d.ders_id = cd.course_id
        WHERE cd.decision_run_id = ?
        """,
        (int(decision_run_id),),
    )
    rows = cur.fetchall()
    total = len(rows)

    status_counts = Counter()
    department_counts = Counter()
    semester_counts = Counter()
    low_confidence = 0
    sensitive_count = 0
    approval_count = 0
    cancel_candidates = 0
    high_success_low_demand = 0
    high_demand_low_success = 0

    for row in rows:
        final_status = int(row[1]) if row[1] is not None else 0
        status_counts[final_status] += 1
        if row[3] is not None:
            department_counts[int(row[3])] += 1
        if row[4]:
            semester_counts[str(row[4])] += 1
        if row[5] is not None and float(row[5]) < 0.50:
            low_confidence += 1
        if str(row[6] or "").lower() == "low":
            sensitive_count += 1
        if int(row[7] or 0):
            approval_count += 1
        if int(row[2] if row[2] is not None else final_status) == STATU_IPTAL:
            cancel_candidates += 1

    if rows:
        course_ids = [int(row[0]) for row in rows if row[0] is not None]
        if course_ids:
            placeholders = ",".join("?" for _ in course_ids)
            try:
                cur.execute(
                    f"""
                    SELECT ders_id,
                           AVG(CASE WHEN toplam_ogrenci > 0 THEN CAST(gecen_ogrenci AS REAL) / toplam_ogrenci ELSE NULL END) AS basari,
                           AVG(CASE WHEN kontenjan > 0 THEN CAST(kayitli_ogrenci AS REAL) / kontenjan ELSE NULL END) AS talep
                    FROM ders_kriterleri
                    WHERE yil = ? AND ders_id IN ({placeholders})
                    GROUP BY ders_id
                    """,
                    (int(year), *course_ids),
                )
                for metric in cur.fetchall():
                    success = float(metric[1] or 0.0)
                    demand = float(metric[2] or 0.0)
                    if success >= 0.75 and demand < 0.45:
                        high_success_low_demand += 1
                    if demand >= 0.75 and success < 0.45:
                        high_demand_low_success += 1
            except sqlite3.OperationalError:
                pass

    department_ratio = {
        str(department): count / total if total else 0.0
        for department, count in sorted(department_counts.items())
    }
    semester_ratio = {
        str(semester): count / total if total else 0.0
        for semester, count in sorted(semester_counts.items())
    }
    report = {
        "total_courses": total,
        "department_counts": dict(department_counts),
        "department_ratios": department_ratio,
        "semester_counts": dict(semester_counts),
        "semester_ratios": semester_ratio,
        "low_data_confidence_count": low_confidence,
        "sensitive_decision_count": sensitive_count,
        "manual_approval_required_count": approval_count,
        "popularity_only_selected_count": 0,
        "high_success_low_demand_count": high_success_low_demand,
        "high_demand_low_success_count": high_demand_low_success,
        "external_department_ratio": 0.0,
        "cancel_candidate_count": cancel_candidates,
        "rest_count": int(status_counts.get(STATU_DINLENMEDE, 0)),
        "curriculum_keep_count": int(status_counts.get(STATU_MUFREDATTA, 0)),
        "pool_count": int(status_counts.get(STATU_HAVUZDA, 0)),
        "cancel_count": int(status_counts.get(STATU_IPTAL, 0)),
    }
    summary = (
        f"{year} karar calismasinda {total} ders degerlendirildi. "
        f"{report['curriculum_keep_count']} ders mufredatta, {report['pool_count']} ders havuzda, "
        f"{report['rest_count']} ders dinlenmede/aday, {approval_count} karar akademik onay gerektiriyor. "
        f"Dusuk veri guvenli karar sayisi {low_confidence}, hassas karar sayisi {sensitive_count}."
    )
    return {
        "decision_run_id": int(decision_run_id),
        "faculty_id": faculty_id,
        "department_id": department_id,
        "year": int(year),
        "report": report,
        "summary_text": summary,
    }


def save_fairness_report(
    cur: sqlite3.Cursor,
    decision_run_id: int,
    faculty_id: int | None,
    department_id: int | None,
    year: int,
    report_pack: dict[str, Any],
) -> int:
    cur.execute(
        """
        INSERT INTO decision_fairness_reports (
            decision_run_id, faculty_id, department_id, year, report_json, summary_text
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            int(decision_run_id),
            faculty_id,
            department_id,
            int(year),
            _json_dump(report_pack.get("report", {})),
            str(report_pack.get("summary_text") or ""),
        ),
    )
    return int(cur.lastrowid)

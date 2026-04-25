# -*- coding: utf-8 -*-
"""Dönem planlama raporlama ve export servisi."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema
from app.services.semester_planning_engine import get_plan_run


def _load_json(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}


def _fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    cols = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, cols) or {} for row in cur.fetchall()]


def _csv_from_dicts(rows: list[dict[str, Any]], columns: list[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def get_semester_plan_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    run = get_plan_run(conn, int(run_id))
    if not run:
        raise ValueError("Dönem planı bulunamadı.")
    return {
        "run": run,
        "assignments": get_semester_plan_assignments(conn, int(run_id)),
        "violations": get_constraint_violations(conn, int(run_id)),
        "scenarios": compare_plan_scenarios(conn, int(run_id)),
        "report_text": generate_human_readable_plan_report(conn, int(run_id)),
    }


def get_semester_plan_assignments(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.*, d.kod AS course_code, d.ad AS course_name
        FROM semester_plan_course_assignments a
        LEFT JOIN ders d ON d.ders_id = a.course_id
        WHERE a.plan_run_id = ?
        ORDER BY CASE a.assigned_semester WHEN 'fall' THEN 1 WHEN 'spring' THEN 2 ELSE 3 END,
                 a.course_score DESC, a.course_id
        """,
        (int(run_id),),
    )
    return _fetch_all_dicts(cur)


def get_constraint_violations(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT v.*, d.kod AS course_code, d.ad AS course_name
        FROM semester_plan_constraint_violations v
        LEFT JOIN ders d ON d.ders_id = v.course_id
        WHERE v.plan_run_id = ?
        ORDER BY CASE v.severity WHEN 'critical' THEN 1 WHEN 'error' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END, v.id
        """,
        (int(run_id),),
    )
    return _fetch_all_dicts(cur)


def compare_plan_scenarios(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM semester_plan_scenarios WHERE plan_run_id = ? ORDER BY plan_score DESC", (int(run_id),))
    rows = _fetch_all_dicts(cur)
    for row in rows:
        row["fall_courses"] = _load_json(row.get("fall_courses_json"), [])
        row["spring_courses"] = _load_json(row.get("spring_courses_json"), [])
        row["metrics"] = _load_json(row.get("metrics_json"), {})
        row["constraint_violations"] = _load_json(row.get("constraint_violations_json"), [])
        row["explanations"] = _load_json(row.get("explanations_json"), [])
    return rows


def export_semester_plan(conn: sqlite3.Connection, run_id: int, format: str = "csv") -> str:
    rows = get_semester_plan_assignments(conn, int(run_id))
    return _csv_from_dicts(
        rows,
        [
            "plan_run_id",
            "course_id",
            "course_code",
            "course_name",
            "assigned_semester",
            "assignment_type",
            "course_score",
            "expected_demand",
            "expected_capacity",
            "constraint_status",
            "explanation",
        ],
    )


def export_constraint_violations(conn: sqlite3.Connection, run_id: int, format: str = "csv") -> str:
    rows = get_constraint_violations(conn, int(run_id))
    return _csv_from_dicts(rows, ["plan_run_id", "course_id", "course_code", "course_name", "constraint_type", "severity", "message", "suggestion"])


def generate_human_readable_plan_report(conn: sqlite3.Connection, run_id: int) -> str:
    run = get_plan_run(conn, int(run_id))
    if not run:
        raise ValueError("Dönem planı bulunamadı.")
    metrics = run.get("metrics") or {}
    assignments = get_semester_plan_assignments(conn, int(run_id))
    fall = [row for row in assignments if row.get("assigned_semester") == "fall"]
    spring = [row for row in assignments if row.get("assigned_semester") == "spring"]
    text = (
        f"{run.get('year')} dönem planında toplam {len(fall) + len(spring)} seçmeli yerleştirilmiştir. "
        f"Güz dönemine {len(fall)}, bahar dönemine {len(spring)} ders atanmıştır. "
        f"Plan skoru {round(float(run.get('plan_score') or 0.0), 2)}. "
        f"Talep dengesizliği {round(float(metrics.get('demand_imbalance') or 0.0), 2)}, "
        f"kontenjan dengesizliği {round(float(metrics.get('capacity_imbalance') or 0.0), 2)} olarak hesaplanmıştır."
    )
    explanations = [str(row.get("explanation")) for row in assignments[:3] if row.get("explanation")]
    if explanations:
        text += " Örnek açıklamalar: " + " ".join(explanations)
    return text

# -*- coding: utf-8 -*-
"""ML readiness raporu üretimi ve kalıcı kayıtları."""

from __future__ import annotations

from datetime import datetime
import json
import sqlite3
from typing import Any

from app.db.schema_compat import ensure_ml_governance_schema
from app.services.ml_algorithm_registry_service import list_algorithm_registry
from app.services.ml_feature_pipeline import build_course_feature_dataset
from app.services.ml_readiness_service import check_model_readiness


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def generate_ml_readiness_report(
    conn: sqlite3.Connection,
    *,
    scope: dict | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    save: bool = True,
) -> dict:
    ensure_ml_governance_schema(conn, commit=False)
    dataset = build_course_feature_dataset(conn, scope=scope, year=year, faculty_id=faculty_id, department_id=department_id, save_snapshot=save)
    algorithms = list_algorithm_registry(conn)
    readiness_rows = [
        check_model_readiness(conn, row["algorithm_key"], dataset, target_column="target_status").as_dict()
        for row in algorithms
    ]
    recommendations = estimate_required_additional_samples(readiness_rows)
    feature_quality = {
        "feature_schema_version": dataset.feature_schema_version,
        "sample_count": dataset.sample_count,
        "missing_features_summary": dataset.missing_features_summary,
        "warnings": dataset.warnings,
    }
    summary_text = _summary(dataset.sample_count, readiness_rows, recommendations)
    report = {
        "scope": scope or {"year": year, "faculty_id": faculty_id, "department_id": department_id},
        "year": year,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "sample_count": dataset.sample_count,
        "algorithm_readiness": readiness_rows,
        "feature_quality": feature_quality,
        "recommendations": recommendations,
        "summary_text": summary_text,
    }
    if save:
        report["id"] = save_readiness_report(conn, report)
    return report


def get_algorithm_readiness_table(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    algorithm_key: str | None = None,
) -> list[dict]:
    dataset = build_course_feature_dataset(conn, year=year, faculty_id=faculty_id, department_id=department_id)
    algorithms = [a for a in list_algorithm_registry(conn) if algorithm_key is None or a["algorithm_key"] == algorithm_key]
    return [check_model_readiness(conn, a["algorithm_key"], dataset, target_column="target_status").as_dict() for a in algorithms]


def estimate_required_additional_samples(readiness_rows: list[dict]) -> list[dict]:
    rows = []
    for row in readiness_rows:
        missing = max(0, int(row.get("required_min_samples") or 0) - int(row.get("sample_count") or 0))
        rows.append({
            "algorithm_key": row.get("algorithm_key"),
            "required_additional_samples": missing,
            "production_ready": bool(row.get("can_use_for_production_decision")),
        })
    return rows


def save_readiness_report(conn: sqlite3.Connection, report: dict) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ml_readiness_reports (
            scope_json, year, faculty_id, department_id, sample_count,
            algorithm_readiness_json, feature_quality_json, recommendations_json,
            summary_text, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _json(report.get("scope")),
            report.get("year"),
            report.get("faculty_id"),
            report.get("department_id"),
            int(report.get("sample_count") or 0),
            _json(report.get("algorithm_readiness")),
            _json(report.get("feature_quality")),
            _json(report.get("recommendations")),
            report.get("summary_text"),
            _now(),
        ),
    )
    return int(cur.lastrowid)


def list_readiness_reports(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM ml_readiness_reports ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 500)),))
    keys = [d[0] for d in cur.description]
    return [_report_row(row, keys) for row in cur.fetchall()]


def get_readiness_report(conn: sqlite3.Connection, report_id: int) -> dict | None:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM ml_readiness_reports WHERE id=? LIMIT 1", (int(report_id),))
    row = cur.fetchone()
    return _report_row(row, [d[0] for d in cur.description]) if row else None


def _summary(sample_count: int, rows: list[dict], recommendations: list[dict]) -> str:
    not_ready = [r for r in rows if r.get("readiness_level") in {"not_ready", "low"}]
    max_missing = max([int(r.get("required_additional_samples") or 0) for r in recommendations] or [0])
    return (
        f"Mevcut veri sayısı: {sample_count}. {len(not_ready)} ML algoritması minimum veri güvenlik eşiğinin altında. "
        f"En yüksek ek veri ihtiyacı {max_missing} ders-yıl kaydıdır. "
        "Mevcut veri miktarı düşük olduğunda ML modelleri nihai karar verici olarak kullanılmaz; nihai karar AHP/TOPSIS + kural motoru + state machine hattıyla üretilir."
    )


def _report_row(row: sqlite3.Row | tuple, keys: list[str]) -> dict:
    data = {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else dict(zip(keys, row))
    for key in ("scope_json", "algorithm_readiness_json", "feature_quality_json", "recommendations_json"):
        try:
            data[key[:-5]] = json.loads(data.get(key) or "{}")
        except Exception:
            data[key[:-5]] = {}
    return data

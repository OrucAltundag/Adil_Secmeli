# -*- coding: utf-8 -*-
"""ML model eğitim çalışması/version kayıt servisi."""

from __future__ import annotations

from datetime import datetime
import json
import sqlite3
from typing import Any

from app.db.schema_compat import ensure_ml_governance_schema


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def _loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def create_model_run(
    conn: sqlite3.Connection,
    *,
    algorithm_key: str,
    model_name: str,
    model_type: str,
    usage_role: str,
    model_version: str,
    feature_schema_version: str,
    training_sample_count: int,
    target_column: str | None = None,
    training_scope: dict | None = None,
    class_distribution: dict | None = None,
    parameters: dict | None = None,
    readiness_level: str | None = None,
    readiness_warnings: list | None = None,
    status: str = "created",
    created_by: str | None = None,
    notes: str | None = None,
) -> int:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ml_model_runs (
            algorithm_key, model_name, model_type, usage_role, model_version,
            feature_schema_version, training_scope_json, training_sample_count,
            target_column, class_distribution_json, parameters_json, readiness_level,
            readiness_warnings_json, status, created_at, created_by, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            algorithm_key,
            model_name,
            model_type,
            usage_role,
            model_version,
            feature_schema_version,
            _json(training_scope),
            int(training_sample_count or 0),
            target_column,
            _json(class_distribution),
            _json(parameters),
            readiness_level,
            _json(readiness_warnings or []),
            status,
            _now(),
            created_by,
            notes,
        ),
    )
    return int(cur.lastrowid)


def mark_trained(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    train_metrics: dict | None = None,
    validation_metrics: dict | None = None,
    cross_validation: dict | None = None,
    overfitting_report: dict | None = None,
    artifact_path: str | None = None,
) -> dict:
    ensure_ml_governance_schema(conn, commit=False)
    conn.execute(
        """
        UPDATE ml_model_runs
        SET status = 'trained',
            train_metrics_json = ?,
            validation_metrics_json = ?,
            cross_validation_json = ?,
            overfitting_report_json = ?,
            artifact_path = ?,
            completed_at = ?
        WHERE id = ?
        """,
        (
            _json(train_metrics),
            _json(validation_metrics),
            _json(cross_validation),
            _json(overfitting_report),
            artifact_path,
            _now(),
            int(run_id),
        ),
    )
    return get_model_run(conn, run_id) or {"id": run_id}


def mark_skipped(conn: sqlite3.Connection, run_id: int, reason: str) -> dict:
    conn.execute(
        "UPDATE ml_model_runs SET status='skipped', skip_reason=?, completed_at=? WHERE id=?",
        (reason, _now(), int(run_id)),
    )
    return get_model_run(conn, run_id) or {"id": run_id, "status": "skipped", "skip_reason": reason}


def mark_failed(conn: sqlite3.Connection, run_id: int, reason: str) -> dict:
    conn.execute(
        "UPDATE ml_model_runs SET status='failed', skip_reason=?, completed_at=? WHERE id=?",
        (reason, _now(), int(run_id)),
    )
    return get_model_run(conn, run_id) or {"id": run_id, "status": "failed", "skip_reason": reason}


def deprecate_model_run(conn: sqlite3.Connection, run_id: int, reason: str | None = None) -> dict:
    conn.execute(
        "UPDATE ml_model_runs SET status='deprecated', notes=COALESCE(notes, '') || ? WHERE id=?",
        (f"\nDeprecated: {reason or ''}", int(run_id)),
    )
    return get_model_run(conn, run_id) or {"id": run_id}


def get_latest_model_run(conn: sqlite3.Connection, algorithm_key: str, trained_only: bool = False) -> dict | None:
    ensure_ml_governance_schema(conn, commit=False)
    sql = "SELECT * FROM ml_model_runs WHERE algorithm_key = ?"
    params: list[Any] = [algorithm_key]
    if trained_only:
        sql += " AND status = 'trained'"
    sql += " ORDER BY id DESC LIMIT 1"
    cur = conn.cursor()
    cur.execute(sql, tuple(params))
    row = cur.fetchone()
    return _row_to_dict(row, [d[0] for d in cur.description]) if row else None


def get_model_run(conn: sqlite3.Connection, run_id: int) -> dict | None:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM ml_model_runs WHERE id = ? LIMIT 1", (int(run_id),))
    row = cur.fetchone()
    return _row_to_dict(row, [d[0] for d in cur.description]) if row else None


def list_model_runs(
    conn: sqlite3.Connection,
    *,
    algorithm_key: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    ensure_ml_governance_schema(conn, commit=False)
    sql = "SELECT * FROM ml_model_runs WHERE 1=1"
    params: list[Any] = []
    if algorithm_key:
        sql += " AND algorithm_key = ?"
        params.append(algorithm_key)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))
    cur = conn.cursor()
    cur.execute(sql, tuple(params))
    keys = [d[0] for d in cur.description]
    return [_row_to_dict(row, keys) for row in cur.fetchall()]


def _row_to_dict(row: sqlite3.Row | tuple, keys: list[str]) -> dict:
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        data = dict(zip(keys, row))
    for key in (
        "training_scope_json",
        "class_distribution_json",
        "parameters_json",
        "train_metrics_json",
        "validation_metrics_json",
        "cross_validation_json",
        "overfitting_report_json",
        "readiness_warnings_json",
    ):
        if key in data:
            data[key[:-5] if key.endswith("_json") else key] = _loads(data.get(key), [] if "warnings" in key else {})
    return data

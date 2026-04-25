# -*- coding: utf-8 -*-
"""Import karar etkisi raporu ve karar run baglantilari."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_import_governance_schema
from app.services.import_audit_service import get_import_batch


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return bool(cur.fetchone())


def link_decision_run_import_source(
    conn: sqlite3.Connection,
    decision_run_id: int | None,
    import_batch_id: int,
    import_type: str | None = None,
) -> int:
    ensure_import_governance_schema(conn, commit=False)
    batch = get_import_batch(conn, int(import_batch_id))
    import_type = import_type or str((batch or {}).get("import_type") or "other")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO decision_run_import_sources (decision_run_id, import_batch_id, import_type, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            int(decision_run_id) if decision_run_id is not None else None,
            int(import_batch_id),
            import_type,
            _now(),
        ),
    )
    return int(cur.lastrowid)


def _decision_map(cur: sqlite3.Cursor, run_id: int | None) -> dict[int, dict[str, Any]]:
    if run_id is None or not _table_exists(cur, "course_decisions"):
        return {}
    cur.execute(
        """
        SELECT course_id, final_status, recommended_status, topsis_score, data_confidence_score
        FROM course_decisions
        WHERE decision_run_id = ?
        """,
        (int(run_id),),
    )
    rows = cur.fetchall()
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        out[int(row[0])] = {
            "final_status": row[1],
            "recommended_status": row[2],
            "topsis_score": row[3],
            "data_confidence_score": row[4],
        }
    return out


def recalculate_import_impact(
    conn: sqlite3.Connection,
    import_batch_id: int,
    previous_decision_run_id: int | None = None,
    new_decision_run_id: int | None = None,
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    batch = get_import_batch(conn, int(import_batch_id))
    if not batch:
        raise ValueError("Import batch bulunamadi.")
    cur = conn.cursor()

    if new_decision_run_id is None and _table_exists(cur, "decision_run_import_sources"):
        cur.execute(
            """
            SELECT decision_run_id
            FROM decision_run_import_sources
            WHERE import_batch_id = ? AND decision_run_id IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(import_batch_id),),
        )
        row = cur.fetchone()
        new_decision_run_id = int(row[0]) if row and row[0] is not None else None

    previous_map = _decision_map(cur, previous_decision_run_id)
    new_map = _decision_map(cur, new_decision_run_id)

    changed_decision_count = 0
    curriculum_to_pool_count = 0
    pool_to_curriculum_count = 0
    rest_candidate_count = 0
    cancel_candidate_count = 0
    significant_score_change_count = 0
    data_confidence_improved_count = 0
    data_confidence_decreased_count = 0

    if previous_map and new_map:
        for course_id in sorted(set(previous_map) | set(new_map)):
            before = previous_map.get(course_id) or {}
            after = new_map.get(course_id) or {}
            if before.get("final_status") != after.get("final_status"):
                changed_decision_count += 1
                if before.get("final_status") == 1 and after.get("final_status") == 0:
                    curriculum_to_pool_count += 1
                if before.get("final_status") == 0 and after.get("final_status") == 1:
                    pool_to_curriculum_count += 1
            if after.get("final_status") == -1:
                rest_candidate_count += 1
            if after.get("final_status") == -2:
                cancel_candidate_count += 1
            try:
                if abs(float(after.get("topsis_score") or 0) - float(before.get("topsis_score") or 0)) >= 10.0:
                    significant_score_change_count += 1
            except Exception:
                pass
            try:
                before_conf = float(before.get("data_confidence_score") or 0)
                after_conf = float(after.get("data_confidence_score") or 0)
                if after_conf > before_conf:
                    data_confidence_improved_count += 1
                elif after_conf < before_conf:
                    data_confidence_decreased_count += 1
            except Exception:
                pass

    if not previous_map or not new_map:
        summary_text = (
            "Bu import icin karar etkisi raporu sinirli uretildi; onceki ve yeni decision_run "
            "baglantisi bulunmadigi icin karar degisimi hesaplanamadi."
        )
    else:
        summary_text = (
            f"Bu import sonrasi {changed_decision_count} dersin karari degisti. "
            f"{curriculum_to_pool_count} ders mufredattan havuza dustu, "
            f"{pool_to_curriculum_count} ders havuzdan mufredata cikti."
        )
    summary = {
        "import_batch_id": int(import_batch_id),
        "previous_decision_run_id": previous_decision_run_id,
        "new_decision_run_id": new_decision_run_id,
        "changed_decision_count": changed_decision_count,
        "summary_text": summary_text,
    }
    cur.execute("DELETE FROM import_impact_reports WHERE import_batch_id = ?", (int(import_batch_id),))
    cur.execute(
        """
        INSERT INTO import_impact_reports (
            import_batch_id, previous_decision_run_id, new_decision_run_id,
            changed_decision_count, curriculum_to_pool_count, pool_to_curriculum_count,
            rest_candidate_count, cancel_candidate_count, significant_score_change_count,
            data_confidence_improved_count, data_confidence_decreased_count,
            summary_json, summary_text, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(import_batch_id),
            int(previous_decision_run_id) if previous_decision_run_id is not None else None,
            int(new_decision_run_id) if new_decision_run_id is not None else None,
            changed_decision_count,
            curriculum_to_pool_count,
            pool_to_curriculum_count,
            rest_candidate_count,
            cancel_candidate_count,
            significant_score_change_count,
            data_confidence_improved_count,
            data_confidence_decreased_count,
            _json_dumps(summary),
            summary_text,
            _now(),
        ),
    )
    return {**summary, "id": int(cur.lastrowid)}


def get_import_impact(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM import_impact_reports
        WHERE import_batch_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(import_batch_id),),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else {}

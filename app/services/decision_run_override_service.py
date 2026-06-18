# -*- coding: utf-8 -*-
"""Gecici karar calistirmasini engelleme/iptal override is akisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_decision_run_override_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_run_override_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER NOT NULL,
            run_snapshot_json TEXT,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_by TEXT,
            requested_at TEXT NOT NULL,
            reviewed_by TEXT,
            reviewed_at TEXT,
            review_note TEXT,
            CHECK(status IN ('pending','approved','rejected'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_decision_run_override_status "
        "ON decision_run_override_requests(status, requested_at)"
    )


def request_decision_run_override(
    conn: sqlite3.Connection,
    decision_run_id: int,
    reason: str,
    requested_by: str | None = None,
) -> dict[str, Any]:
    ensure_decision_run_override_schema(conn)
    if not str(reason or "").strip():
        raise ValueError("Karari engelleme talebi icin gerekce zorunludur.")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_runs WHERE id=?", (int(decision_run_id),))
    run = cur.fetchone()
    if not run:
        raise ValueError("Karar calistirmasi bulunamadi.")
    cur.execute(
        "SELECT id FROM decision_run_override_requests WHERE decision_run_id=? AND status='pending'",
        (int(decision_run_id),),
    )
    if cur.fetchone():
        raise ValueError("Bu karar icin zaten bekleyen bir engelleme talebi var.")
    snapshot = {key: run[key] for key in run.keys()}
    cur.execute(
        """
        INSERT INTO decision_run_override_requests (
            decision_run_id, run_snapshot_json, reason, status, requested_by, requested_at
        ) VALUES (?, ?, ?, 'pending', ?, ?)
        """,
        (
            int(decision_run_id),
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str),
            str(reason).strip(),
            requested_by,
            _now(),
        ),
    )
    return get_decision_run_override(conn, int(cur.lastrowid or 0)) or {}


def get_decision_run_override(conn: sqlite3.Connection, request_id: int) -> dict[str, Any] | None:
    ensure_decision_run_override_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_run_override_requests WHERE id=?", (int(request_id),))
    row = cur.fetchone()
    return dict(row) if row else None


def list_decision_run_overrides(conn: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    ensure_decision_run_override_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if status:
        cur.execute(
            "SELECT * FROM decision_run_override_requests WHERE status=? ORDER BY id DESC",
            (str(status),),
        )
    else:
        cur.execute("SELECT * FROM decision_run_override_requests ORDER BY id DESC")
    return [dict(row) for row in cur.fetchall()]


def cancel_decision_run_override(
    conn: sqlite3.Connection,
    request_id: int,
) -> dict[str, Any]:
    """Henüz incelenmemiş engelleme talebini kuyruktan kaldırır.

    Onaylanmış/reddedilmiş kayıtlar denetim izi olduğundan silinemez. Yalnızca
    ``pending`` talep geri çekilebilir; karar çalıştırması ve çıktıları korunur.
    """
    ensure_decision_run_override_schema(conn)
    request = get_decision_run_override(conn, request_id)
    if not request:
        raise ValueError("Engelleme talebi bulunamadi.")
    if request.get("status") != "pending":
        raise ValueError("Yalniz bekleyen engelleme talepleri geri cekilebilir.")
    cur = conn.execute(
        "DELETE FROM decision_run_override_requests WHERE id=? AND status='pending'",
        (int(request_id),),
    )
    if int(cur.rowcount or 0) != 1:
        raise ValueError("Engelleme talebi artik beklemede degil; listeyi yenileyin.")
    return request


def _execute_optional(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...]) -> None:
    """Şema sürümleri arasında bulunmayan tablo/kolonu atla; gerçek DB hatasını yutma."""

    try:
        cur.execute(sql, params)
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        if "no such table" in message or "no such column" in message:
            return
        raise


def _delete_run_outputs(cur: sqlite3.Cursor, run_id: int) -> None:
    run_param = (int(run_id),)

    # Önce başka çıktı tablolarının işaret ettiği alt kayıtları sil.
    _execute_optional(
        cur,
        "DELETE FROM fairness_metric_items WHERE fairness_report_id IN "
        "(SELECT id FROM decision_fairness_reports WHERE decision_run_id=?)",
        run_param,
    )
    _execute_optional(
        cur,
        "DELETE FROM ahp_course_sensitivity_items WHERE sensitivity_result_id IN "
        "(SELECT id FROM ahp_sensitivity_results WHERE decision_run_id=?)",
        run_param,
    )
    _execute_optional(
        cur,
        "DELETE FROM course_state_approvals WHERE transition_id IN "
        "(SELECT id FROM course_state_transitions WHERE decision_run_id=?)",
        run_param,
    )
    _execute_optional(
        cur,
        "DELETE FROM course_decision_explanations WHERE course_decision_id IN "
        "(SELECT id FROM course_decisions WHERE decision_run_id=?)",
        run_param,
    )

    for table in (
        "candidate_course_recommendations",
        "course_score_breakdowns",
        "course_trend_analysis",
        "course_data_confidence",
        "decision_sensitivity_results",
        "data_coverage_reports",
        "decision_staleness_flags",
        "low_confidence_decision_flags",
        "post_decision_outcomes",
        "decision_run_import_sources",
        "ahp_sensitivity_results",
        "course_state_transitions",
        "decision_fairness_reports",
    ):
        _execute_optional(cur, f'DELETE FROM "{table}" WHERE decision_run_id=?', run_param)

    # İçe aktarma etki raporu aynı run'ı iki ayrı kolonda referanslayabilir.
    _execute_optional(
        cur,
        "DELETE FROM import_impact_reports WHERE previous_decision_run_id=? OR new_decision_run_id=?",
        (int(run_id), int(run_id)),
    )
    _execute_optional(cur, "DELETE FROM course_decisions WHERE decision_run_id=?", run_param)
    cur.execute("DELETE FROM decision_runs WHERE id=?", run_param)


def approve_decision_run_override(
    conn: sqlite3.Connection,
    request_id: int,
    reviewed_by: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    ensure_decision_run_override_schema(conn)
    request = get_decision_run_override(conn, request_id)
    if not request:
        raise ValueError("Engelleme talebi bulunamadi.")
    if request.get("status") != "pending":
        raise ValueError("Yalniz bekleyen engelleme talepleri onaylanabilir.")
    if requested_by := str(request.get("requested_by") or "").strip():
        if reviewed_by and requested_by == str(reviewed_by).strip():
            raise ValueError("Talebi acan kullanici ayni talebi onaylayamaz.")
    cur = conn.cursor()
    _delete_run_outputs(cur, int(request["decision_run_id"]))
    cur.execute(
        """
        UPDATE decision_run_override_requests
        SET status='approved', reviewed_by=?, reviewed_at=?, review_note=?
        WHERE id=? AND status='pending'
        """,
        (reviewed_by, _now(), review_note, int(request_id)),
    )
    return get_decision_run_override(conn, request_id) or {}


def reject_decision_run_override(
    conn: sqlite3.Connection,
    request_id: int,
    review_note: str,
    reviewed_by: str | None = None,
) -> dict[str, Any]:
    ensure_decision_run_override_schema(conn)
    if not str(review_note or "").strip():
        raise ValueError("Engelleme talebini reddetmek icin gerekce zorunludur.")
    request = get_decision_run_override(conn, request_id)
    if not request or request.get("status") != "pending":
        raise ValueError("Bekleyen engelleme talebi bulunamadi.")
    conn.execute(
        """
        UPDATE decision_run_override_requests
        SET status='rejected', reviewed_by=?, reviewed_at=?, review_note=?
        WHERE id=? AND status='pending'
        """,
        (reviewed_by, _now(), str(review_note).strip(), int(request_id)),
    )
    return get_decision_run_override(conn, request_id) or {}


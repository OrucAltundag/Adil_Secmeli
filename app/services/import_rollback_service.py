# -*- coding: utf-8 -*-
"""Import rollback ve pasifleme servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_import_governance_schema
from app.services.import_audit_service import get_import_batch, update_import_status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return bool(cur.fetchone())


def _column_names(cur: sqlite3.Cursor, table_name: str) -> set[str]:
    if not _table_exists(cur, table_name):
        return set()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(row[1]) for row in cur.fetchall()}


def _log(
    cur: sqlite3.Cursor,
    import_batch_id: int,
    action: str,
    table: str,
    message: str,
    affected_record_id: int | None = None,
    before: Any = None,
    after: Any = None,
) -> None:
    cur.execute(
        """
        INSERT INTO import_rollback_logs (
            import_batch_id, action, affected_table, affected_record_id,
            before_json, after_json, message, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(import_batch_id),
            action,
            table,
            int(affected_record_id) if affected_record_id is not None else None,
            _json_dumps(before) if before is not None else None,
            _json_dumps(after) if after is not None else None,
            message,
            _now(),
        ),
    )


def can_rollback(conn: sqlite3.Connection, import_batch_id: int) -> bool:
    batch = get_import_batch(conn, int(import_batch_id))
    return bool(batch and batch.get("status") not in {"rolled_back", "rejected", "failed"})


def get_rollback_plan(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    batch = get_import_batch(conn, int(import_batch_id))
    if not batch:
        return {"ok": False, "message": "Import batch bulunamadi.", "can_rollback": False}
    cur = conn.cursor()
    criteria_source_count = 0
    if _table_exists(cur, "criteria_value_sources"):
        cur.execute(
            "SELECT COUNT(*) FROM criteria_value_sources WHERE source_import_batch_id = ? AND is_active = 1",
            (int(import_batch_id),),
        )
        criteria_source_count = int((cur.fetchone() or [0])[0] or 0)
    linked_decision_runs = 0
    if _table_exists(cur, "decision_run_import_sources"):
        cur.execute(
            "SELECT COUNT(*) FROM decision_run_import_sources WHERE import_batch_id = ?",
            (int(import_batch_id),),
        )
        linked_decision_runs = int((cur.fetchone() or [0])[0] or 0)
    previous_id = batch.get("previous_import_batch_id")
    return {
        "ok": True,
        "can_rollback": can_rollback(conn, int(import_batch_id)),
        "import_batch_id": int(import_batch_id),
        "current_status": batch.get("status"),
        "will_mark_rolled_back": True,
        "previous_import_batch_id": previous_id,
        "will_reactivate_previous": bool(previous_id),
        "criteria_value_sources_to_deactivate": criteria_source_count,
        "linked_decision_runs_to_mark_stale": linked_decision_runs,
        "message": (
            "Rollback veri silmez; import batch rolled_back olur, alan kaynaklari pasiflenir "
            "ve varsa onceki import tekrar active yapilir."
        ),
    }


def rollback_import(
    conn: sqlite3.Connection,
    import_batch_id: int,
    reason: str,
    user: str | None = None,
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    if not can_rollback(conn, int(import_batch_id)):
        return {"ok": False, "message": "Bu import geri alinabilir durumda degil."}
    batch = get_import_batch(conn, int(import_batch_id))
    if not batch:
        return {"ok": False, "message": "Import batch bulunamadi."}

    cur = conn.cursor()
    plan = get_rollback_plan(conn, int(import_batch_id))

    if _table_exists(cur, "criteria_value_sources"):
        cur.execute(
            """
            UPDATE criteria_value_sources
            SET is_active = 0
            WHERE source_import_batch_id = ? AND is_active = 1
            """,
            (int(import_batch_id),),
        )
        _log(
            cur,
            int(import_batch_id),
            "deactivate_value_sources",
            "criteria_value_sources",
            f"{int(cur.rowcount or 0)} alan kaynak kaydi pasiflendi.",
        )

    source_table = batch.get("source_table")
    source_import_id = batch.get("source_import_id")
    if source_table and source_import_id is not None and _table_exists(cur, str(source_table)):
        cols = _column_names(cur, str(source_table))
        updates: list[str] = []
        params: list[Any] = []
        if "status" in cols:
            updates.append("status = ?")
            params.append("rolled_back")
        if "rolled_back_at" in cols:
            updates.append("rolled_back_at = ?")
            params.append(_now())
        if "rollback_reason" in cols:
            updates.append("rollback_reason = ?")
            params.append(reason)
        if updates:
            cur.execute(
                f"UPDATE {source_table} SET {', '.join(updates)} WHERE import_id = ?",
                tuple(params + [int(source_import_id)]),
            )
            _log(
                cur,
                int(import_batch_id),
                "mark_source_import_rolled_back",
                str(source_table),
                "Kaynak import kaydi rolled_back olarak isaretlendi.",
                affected_record_id=int(source_import_id),
            )

    previous_id = batch.get("previous_import_batch_id")
    if previous_id:
        cur.execute(
            """
            UPDATE import_batches
            SET status = 'active', superseded_by_import_batch_id = NULL, updated_at = ?
            WHERE id = ?
            """,
            (_now(), int(previous_id)),
        )
        _log(
            cur,
            int(import_batch_id),
            "reactivate_previous_import",
            "import_batches",
            f"Onceki import batch #{previous_id} tekrar active yapildi.",
            affected_record_id=int(previous_id),
        )

    update_import_status(conn, int(import_batch_id), "rolled_back", user=user, reason=reason)
    _log(
        cur,
        int(import_batch_id),
        "rollback_completed",
        "import_batches",
        reason,
        affected_record_id=int(import_batch_id),
        before={"status": batch.get("status")},
        after={"status": "rolled_back"},
    )
    return {"ok": True, "message": "Import geri alindi.", "plan": plan}

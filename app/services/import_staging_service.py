# -*- coding: utf-8 -*-
"""Canlı tablolara uygulanmadan önce bekleyen import payload/row staging alanı."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.services.import_audit_service import calculate_row_hash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_import_staging_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS import_staging_payloads (
            import_batch_id INTEGER PRIMARY KEY,
            import_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            staging_status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            decided_at TEXT,
            decided_by TEXT,
            decision_note TEXT
        );
        CREATE TABLE IF NOT EXISTS import_staging_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            import_type TEXT NOT NULL,
            row_number INTEGER NOT NULL,
            normalized_row_json TEXT NOT NULL,
            row_hash TEXT,
            row_status TEXT NOT NULL DEFAULT 'matched',
            matched_ders_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_import_staging_rows_batch
        ON import_staging_rows(import_batch_id, row_number);
        """
    )


def stage_import(
    conn: sqlite3.Connection,
    *,
    import_batch_id: int,
    import_type: str,
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ensure_import_staging_schema(conn)
    batch_id = int(import_batch_id)
    conn.execute("DELETE FROM import_staging_rows WHERE import_batch_id = ?", (batch_id,))
    conn.execute("DELETE FROM import_staging_payloads WHERE import_batch_id = ?", (batch_id,))
    conn.execute(
        """
        INSERT INTO import_staging_payloads
            (import_batch_id, import_type, payload_json, staging_status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (batch_id, str(import_type), json.dumps(payload, ensure_ascii=False, default=str), _now()),
    )
    for index, row in enumerate(rows, start=1):
        normalized = dict(row)
        row_number = int(normalized.get("row_no") or normalized.get("row_number") or index)
        conn.execute(
            """
            INSERT INTO import_staging_rows
                (import_batch_id, import_type, row_number, normalized_row_json,
                 row_hash, row_status, matched_ders_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                str(import_type),
                row_number,
                json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str),
                calculate_row_hash(normalized),
                str(normalized.get("row_status") or "matched"),
                normalized.get("matched_ders_id") or normalized.get("course_id"),
                _now(),
            ),
        )
    return {"ok": True, "import_batch_id": batch_id, "staged_row_count": len(rows)}


def get_staged_payload(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None:
    ensure_import_staging_schema(conn)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM import_staging_payloads WHERE import_batch_id = ?",
        (int(import_batch_id),),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["payload"] = json.loads(data.get("payload_json") or "{}")
    return data


def list_staged_rows(conn: sqlite3.Connection, import_batch_id: int, limit: int = 100000) -> list[dict[str, Any]]:
    ensure_import_staging_schema(conn)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT row_number AS row_no, row_status, matched_ders_id,
               row_hash, normalized_row_json
        FROM import_staging_rows
        WHERE import_batch_id = ?
        ORDER BY row_number
        LIMIT ?
        """,
        (int(import_batch_id), int(limit)),
    ).fetchall()
    return [dict(row) for row in rows]


def mark_staging_decision(
    conn: sqlite3.Connection,
    import_batch_id: int,
    status: str,
    *,
    user: str | None = None,
    note: str | None = None,
) -> None:
    ensure_import_staging_schema(conn)
    conn.execute(
        """
        UPDATE import_staging_payloads
        SET staging_status = ?, decided_at = ?, decided_by = ?, decision_note = ?
        WHERE import_batch_id = ?
        """,
        (str(status), _now(), user, note, int(import_batch_id)),
    )

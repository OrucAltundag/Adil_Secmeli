# -*- coding: utf-8 -*-
"""Import versiyonlari arasinda satir ve alan bazli diff uretir."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_import_governance_schema
from app.services.import_audit_service import get_import_batch, list_import_rows

IGNORED_FIELDS = {
    "row_id",
    "import_id",
    "import_batch_id",
    "issue_count",
    "row_hash",
    "normalized_row_json",
    "error_message",
    "row_status",
    "match_method",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        return round(value, 6)
    text = str(value).strip()
    if text == "":
        return None
    try:
        number = float(text)
        return round(number, 6)
    except Exception:
        return text.lower()


def _load_normalized_row(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("normalized_row_json")
    if raw:
        try:
            data = json.loads(str(raw))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {key: value for key, value in row.items() if key not in IGNORED_FIELDS}


def _entity_key(row: dict[str, Any]) -> str:
    if row.get("matched_ders_id") is not None:
        return f"course:{row.get('matched_ders_id')}"
    if row.get("ders_kodu"):
        return f"code:{str(row.get('ders_kodu')).strip().lower()}"
    if row.get("ders_adi"):
        return f"name:{str(row.get('ders_adi')).strip().lower()}"
    return f"row:{row.get('row_no') or row.get('row_id') or ''}"


def find_previous_import_batch(conn: sqlite3.Connection, import_batch_id: int) -> int | None:
    batch = get_import_batch(conn, import_batch_id)
    if not batch:
        return None
    if batch.get("previous_import_batch_id"):
        return int(batch["previous_import_batch_id"])
    cur = conn.cursor()
    where = ["id <> ?", "id < ?", "import_type = ?"]
    params: list[Any] = [int(import_batch_id), int(import_batch_id), batch.get("import_type")]
    for col in ("faculty_id", "department_id", "year", "semester"):
        value = batch.get(col)
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    cur.execute(
        f"""
        SELECT id
        FROM import_batches
        WHERE {' AND '.join(where)}
          AND status IN ('active', 'superseded', 'approved', 'validated')
        ORDER BY id DESC
        LIMIT 1
        """,
        tuple(params),
    )
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def recalculate_import_diff(
    conn: sqlite3.Connection,
    import_batch_id: int,
    compared_to_import_batch_id: int | None = None,
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    current_batch = get_import_batch(conn, int(import_batch_id))
    if not current_batch:
        raise ValueError("Import batch bulunamadi.")
    compared_to_import_batch_id = compared_to_import_batch_id or find_previous_import_batch(conn, int(import_batch_id))

    current_rows = list_import_rows(conn, int(import_batch_id), limit=100000)
    previous_rows = (
        list_import_rows(conn, int(compared_to_import_batch_id), limit=100000)
        if compared_to_import_batch_id is not None
        else []
    )
    current_map = {_entity_key(row): row for row in current_rows}
    previous_map = {_entity_key(row): row for row in previous_rows}
    all_keys = sorted(set(current_map) | set(previous_map))

    items: list[dict[str, Any]] = []
    added = removed = changed = unchanged = 0
    for key in all_keys:
        before = previous_map.get(key)
        after = current_map.get(key)
        course_id = (after or before or {}).get("matched_ders_id")
        if before is None and after is not None:
            added += 1
            items.append(
                {
                    "change_type": "added",
                    "entity_key": key,
                    "course_id": course_id,
                    "before_row_json": None,
                    "after_row_json": _json_dumps(_load_normalized_row(after)),
                    "message": f"{key} yeni importta eklendi.",
                }
            )
            continue
        if after is None and before is not None:
            removed += 1
            items.append(
                {
                    "change_type": "removed",
                    "entity_key": key,
                    "course_id": course_id,
                    "before_row_json": _json_dumps(_load_normalized_row(before)),
                    "after_row_json": None,
                    "message": f"{key} yeni dosyada bulunmuyor.",
                }
            )
            continue

        before_norm = _load_normalized_row(before or {})
        after_norm = _load_normalized_row(after or {})
        changed_fields = []
        for field in sorted(set(before_norm) | set(after_norm)):
            if field in IGNORED_FIELDS:
                continue
            before_value = _normalize_value(before_norm.get(field))
            after_value = _normalize_value(after_norm.get(field))
            if before_value != after_value:
                changed_fields.append((field, before_norm.get(field), after_norm.get(field)))
        if changed_fields:
            changed += 1
            for field, before_value, after_value in changed_fields:
                items.append(
                    {
                        "change_type": "changed",
                        "entity_key": key,
                        "course_id": course_id,
                        "field_name": field,
                        "before_value": None if before_value is None else str(before_value),
                        "after_value": None if after_value is None else str(after_value),
                        "before_row_json": _json_dumps(before_norm),
                        "after_row_json": _json_dumps(after_norm),
                        "message": f"{key} icin {field} degeri degisti.",
                    }
                )
        else:
            unchanged += 1
            items.append(
                {
                    "change_type": "unchanged",
                    "entity_key": key,
                    "course_id": course_id,
                    "before_row_json": _json_dumps(before_norm),
                    "after_row_json": _json_dumps(after_norm),
                    "message": f"{key} degismedi.",
                }
            )

    summary = {
        "import_batch_id": int(import_batch_id),
        "compared_to_import_batch_id": compared_to_import_batch_id,
        "added_count": added,
        "removed_count": removed,
        "changed_count": changed,
        "unchanged_count": unchanged,
    }
    cur = conn.cursor()
    cur.execute("DELETE FROM import_diff_items WHERE import_diff_id IN (SELECT id FROM import_diffs WHERE import_batch_id = ?)", (int(import_batch_id),))
    cur.execute("DELETE FROM import_diffs WHERE import_batch_id = ?", (int(import_batch_id),))
    cur.execute(
        """
        INSERT INTO import_diffs (
            import_batch_id, compared_to_import_batch_id, added_count, removed_count,
            changed_count, unchanged_count, summary_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(import_batch_id),
            int(compared_to_import_batch_id) if compared_to_import_batch_id is not None else None,
            added,
            removed,
            changed,
            unchanged,
            _json_dumps(summary),
            _now(),
        ),
    )
    diff_id = int(cur.lastrowid or 0)
    for item in items:
        cur.execute(
            """
            INSERT INTO import_diff_items (
                import_diff_id, change_type, entity_key, course_id, field_name,
                before_value, after_value, before_row_json, after_row_json, message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                diff_id,
                item.get("change_type"),
                item.get("entity_key"),
                item.get("course_id"),
                item.get("field_name"),
                item.get("before_value"),
                item.get("after_value"),
                item.get("before_row_json"),
                item.get("after_row_json"),
                item.get("message"),
            ),
        )
    return {"id": diff_id, **summary, "items": items}


def get_import_diff(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM import_diffs
        WHERE import_batch_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(import_batch_id),),
    )
    diff_row = cur.fetchone()
    if not diff_row:
        return None
    diff = {key: diff_row[key] for key in diff_row.keys()} if isinstance(diff_row, sqlite3.Row) else {}
    diff_id = int(diff.get("id") or diff_row[0])
    cur.execute("SELECT * FROM import_diff_items WHERE import_diff_id = ? ORDER BY id", (diff_id,))
    items = []
    for row in cur.fetchall():
        if isinstance(row, sqlite3.Row):
            items.append({key: row[key] for key in row.keys()})
    diff["items"] = items
    return diff

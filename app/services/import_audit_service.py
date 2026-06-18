# -*- coding: utf-8 -*-
"""Import audit trail ortak servisleri."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO

import pandas as pd

from app.db.schema_compat import ensure_import_governance_schema
from app.db.sqlite_connection import connect_sqlite

VALID_IMPORT_TYPES = {"criteria", "survey", "curriculum", "other"}
VALID_STATUSES = {
    "uploaded",
    "validated",
    "pending_review",
    "approved",
    "active",
    "superseded",
    "rejected",
    "rolled_back",
    "failed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return bool(cur.fetchone())


def _column_names(cur: sqlite3.Cursor, table_name: str) -> set[str]:
    if not _table_exists(cur, table_name):
        return set()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(row[1]) for row in cur.fetchall()}


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    if columns:
        return {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
    return {str(idx): value for idx, value in enumerate(row)}


def calculate_file_hash(file_path_or_bytes: str | os.PathLike[str] | bytes | bytearray | BinaryIO) -> str:
    """Dosya yolu, byte dizisi veya file-like obje icin SHA256 hesaplar."""
    digest = hashlib.sha256()
    if isinstance(file_path_or_bytes, (bytes, bytearray)):
        digest.update(bytes(file_path_or_bytes))
        return digest.hexdigest()
    if hasattr(file_path_or_bytes, "read"):
        stream = file_path_or_bytes  # type: ignore[assignment]
        pos = None
        try:
            pos = stream.tell()  # type: ignore[attr-defined]
        except Exception:
            pos = None
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):  # type: ignore[attr-defined]
            digest.update(chunk)
        if pos is not None:
            try:
                stream.seek(pos)  # type: ignore[attr-defined]
            except Exception:
                pass
        return digest.hexdigest()

    with open(file_path_or_bytes, "rb") as handle:  # type: ignore[arg-type]
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calculate_column_signature(columns: list[str] | tuple[str, ...] | None) -> str:
    normalized = [str(col or "").strip().lower().replace(" ", "_") for col in (columns or [])]
    return hashlib.sha256(_json_dumps(normalized).encode("utf-8")).hexdigest()


def calculate_row_hash(row_payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dumps(row_payload).encode("utf-8")).hexdigest()


def extract_excel_metadata(excel_path: str) -> dict[str, Any]:
    with pd.ExcelFile(excel_path) as xls:
        sheet_names = list(xls.sheet_names)
        data_sheet = next((name for name in sheet_names if str(name).strip().lower() != "meta"), sheet_names[0])
        df = pd.read_excel(xls, sheet_name=data_sheet)
    df.columns = [str(col).strip() for col in df.columns]
    return {
        "sheet_names": sheet_names,
        "data_sheet": data_sheet,
        "row_count": int(len(df.index)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
    }


def detect_duplicate_import(
    conn: sqlite3.Connection,
    file_hash: str | None,
    import_type: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    exclude_batch_id: int | None = None,
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    if not file_hash:
        return {"is_duplicate": False, "duplicate_batch": None}

    where = ["file_hash_sha256 = ?", "import_type = ?"]
    params: list[Any] = [file_hash, import_type]
    for col, value in (
        ("faculty_id", faculty_id),
        ("department_id", department_id),
        ("year", year),
        ("semester", semester),
    ):
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    if exclude_batch_id is not None:
        where.append("id <> ?")
        params.append(int(exclude_batch_id))

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT *
        FROM import_batches
        WHERE {' AND '.join(where)}
          AND status NOT IN ('rejected', 'rolled_back', 'failed')
        ORDER BY id DESC
        LIMIT 1
        """,
        tuple(params),
    )
    row = cur.fetchone()
    return {"is_duplicate": bool(row), "duplicate_batch": _row_to_dict(row)}


def _scope_type(faculty_id: int | None, department_id: int | None, school_id: int | None, semester: str | None) -> str | None:
    if semester:
        return "semester"
    if department_id is not None:
        return "department"
    if faculty_id is not None:
        return "faculty"
    if school_id is not None:
        return "school"
    return None


def _previous_active_batch(
    conn: sqlite3.Connection,
    import_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
    semester: str | None,
    exclude_batch_id: int | None = None,
) -> int | None:
    where = ["import_type = ?", "status = 'active'"]
    params: list[Any] = [import_type]
    for col, value in (
        ("faculty_id", faculty_id),
        ("department_id", department_id),
        ("year", year),
        ("semester", semester),
    ):
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    if exclude_batch_id is not None:
        where.append("id <> ?")
        params.append(int(exclude_batch_id))
    cur = conn.cursor()
    cur.execute(
        f"SELECT id FROM import_batches WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
        tuple(params),
    )
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def create_import_batch(
    conn: sqlite3.Connection,
    import_type: str,
    original_filename: str | None = None,
    stored_filename: str | None = None,
    file_path: str | None = None,
    file_bytes: bytes | None = None,
    sheet_names: list[str] | None = None,
    columns: list[str] | None = None,
    row_count: int = 0,
    column_count: int | None = None,
    school_id: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    uploaded_by: str | None = None,
    source_table: str | None = None,
    source_import_id: int | None = None,
    validation_summary: dict[str, Any] | None = None,
    notes: str | None = None,
    status: str = "uploaded",
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    if import_type not in VALID_IMPORT_TYPES:
        import_type = "other"
    if status not in VALID_STATUSES:
        status = "uploaded"

    if file_path and os.path.exists(file_path):
        file_hash = calculate_file_hash(file_path)
        file_size = int(os.path.getsize(file_path))
    elif file_bytes is not None:
        file_hash = calculate_file_hash(file_bytes)
        file_size = len(file_bytes)
    else:
        file_hash = None
        file_size = None

    duplicate = detect_duplicate_import(
        conn,
        file_hash=file_hash,
        import_type=import_type,
        faculty_id=faculty_id,
        department_id=department_id,
        year=year,
        semester=semester,
    )
    duplicate_batch = duplicate.get("duplicate_batch") or {}
    previous_batch_id = _previous_active_batch(
        conn,
        import_type=import_type,
        faculty_id=faculty_id,
        department_id=department_id,
        year=year,
        semester=semester,
    )
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO import_batches (
            import_type, source_table, source_import_id, original_filename, stored_filename,
            file_hash_sha256, file_size, sheet_names_json, row_count, column_count,
            column_signature_hash, scope_type, school_id, faculty_id, department_id,
            year, semester, uploaded_by, uploaded_at, status, previous_import_batch_id,
            duplicate_of_import_batch_id, validation_summary_json, notes, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_type,
            source_table,
            int(source_import_id) if source_import_id is not None else None,
            original_filename,
            stored_filename,
            file_hash,
            file_size,
            _json_dumps(sheet_names or []),
            int(row_count or 0),
            int(column_count if column_count is not None else len(columns or [])),
            calculate_column_signature(columns or []),
            _scope_type(faculty_id, department_id, school_id, semester),
            school_id,
            faculty_id,
            department_id,
            year,
            semester,
            uploaded_by,
            now,
            status,
            previous_batch_id,
            duplicate_batch.get("id"),
            _json_dumps(validation_summary or {}),
            notes,
            now,
            now,
        ),
    )
    batch_id = int(cur.lastrowid or 0)
    return {
        "id": batch_id,
        "import_batch_id": batch_id,
        "file_hash_sha256": file_hash,
        "file_size": file_size,
        "duplicate": bool(duplicate.get("is_duplicate")),
        "duplicate_of_import_batch_id": duplicate_batch.get("id"),
        "previous_import_batch_id": previous_batch_id,
        "status": status,
    }


def link_source_import(
    conn: sqlite3.Connection,
    import_batch_id: int,
    source_table: str,
    source_import_id: int,
    file_hash_sha256: str | None = None,
    file_size: int | None = None,
) -> None:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    now = _now()
    cur.execute(
        """
        UPDATE import_batches
        SET source_table = ?, source_import_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (source_table, int(source_import_id), now, int(import_batch_id)),
    )
    if _table_exists(cur, source_table):
        cols = _column_names(cur, source_table)
        updates: list[str] = []
        params: list[Any] = []
        for col, value in (
            ("import_batch_id", int(import_batch_id)),
            ("file_hash_sha256", file_hash_sha256),
            ("file_size", file_size),
        ):
            if col in cols:
                updates.append(f"{col} = ?")
                params.append(value)
        if updates:
            pk = "import_id"
            cur.execute(
                f"UPDATE {source_table} SET {', '.join(updates)} WHERE {pk} = ?",
                tuple(params + [int(source_import_id)]),
            )


def update_import_status(
    conn: sqlite3.Connection,
    import_batch_id: int,
    status: str,
    error_message: str | None = None,
    user: str | None = None,
    reason: str | None = None,
    validation_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    if status not in VALID_STATUSES:
        raise ValueError(f"Gecersiz import status: {status}")
    now = _now()
    updates = ["status = ?", "updated_at = ?"]
    params: list[Any] = [status, now]
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if validation_summary is not None:
        updates.append("validation_summary_json = ?")
        params.append(_json_dumps(validation_summary))
    if status == "approved":
        updates.extend(["approved_by = ?", "approved_at = ?"])
        params.extend([user, now])
    elif status == "rejected":
        updates.extend(["rejected_by = ?", "rejected_at = ?", "rejection_reason = ?"])
        params.extend([user, now, reason])
    elif status == "rolled_back":
        updates.extend(["rolled_back_by = ?", "rolled_back_at = ?", "rollback_reason = ?"])
        params.extend([user, now, reason])
    params.append(int(import_batch_id))
    cur = conn.cursor()
    cur.execute(f"UPDATE import_batches SET {', '.join(updates)} WHERE id = ?", tuple(params))
    return get_import_batch(conn, int(import_batch_id)) or {"id": int(import_batch_id), "status": status}


def validate_import(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]:
    issues = list_import_issues(conn, import_batch_id)
    critical_errors = [item for item in issues if item.get("severity") in {"error", "critical"}]
    status = "pending_review" if critical_errors else "validated"
    summary = {
        "issue_count": len(issues),
        "critical_error_count": len(critical_errors),
        "ok": not critical_errors,
    }
    batch = update_import_status(conn, import_batch_id, status, validation_summary=summary)
    return {"ok": not critical_errors, "status": status, "summary": summary, "batch": batch}


def approve_import(conn: sqlite3.Connection, import_batch_id: int, approved_by: str | None = None) -> dict[str, Any]:
    return update_import_status(conn, import_batch_id, "approved", user=approved_by)


def reject_import(
    conn: sqlite3.Connection,
    import_batch_id: int,
    reason: str,
    rejected_by: str | None = None,
) -> dict[str, Any]:
    return update_import_status(conn, import_batch_id, "rejected", user=rejected_by, reason=reason)


def activate_import(conn: sqlite3.Connection, import_batch_id: int, user: str | None = None) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    batch = get_import_batch(conn, import_batch_id)
    if not batch:
        raise ValueError("Import batch bulunamadi.")
    previous_id = _previous_active_batch(
        conn,
        import_type=str(batch.get("import_type") or "other"),
        faculty_id=batch.get("faculty_id"),
        department_id=batch.get("department_id"),
        year=batch.get("year"),
        semester=batch.get("semester"),
        exclude_batch_id=import_batch_id,
    )
    now = _now()
    cur = conn.cursor()
    if previous_id is not None:
        cur.execute(
            """
            UPDATE import_batches
            SET status = 'superseded', superseded_by_import_batch_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (int(import_batch_id), now, int(previous_id)),
        )
        cur.execute(
            "UPDATE import_batches SET previous_import_batch_id = COALESCE(previous_import_batch_id, ?) WHERE id = ?",
            (int(previous_id), int(import_batch_id)),
        )
    cur.execute(
        """
        UPDATE import_batches
        SET status = 'active', approved_by = COALESCE(approved_by, ?),
            approved_at = COALESCE(approved_at, ?), updated_at = ?
        WHERE id = ?
        """,
        (user, now, now, int(import_batch_id)),
    )
    return get_import_batch(conn, import_batch_id) or {"id": import_batch_id, "status": "active"}


def classify_issue(
    message: str | None,
    row_status: str | None = None,
    field_name: str | None = None,
) -> tuple[str, str, str]:
    text = f"{row_status or ''} {field_name or ''} {message or ''}".lower()
    severity = "warning"
    issue_type = "unknown_error"
    suggestion = "Satiri kontrol edip alan degerlerini sablonla uyumlu olacak sekilde duzeltin."

    if "kolon" in text or "header" in text:
        severity = "critical"
        issue_type = "missing_required_column" if "gerekli" in text else "invalid_header"
        suggestion = "Sablondaki zorunlu kolon adlarini kullanin ve kolon basliklarini degistirmeyin."
    elif "say" in text or "numeric" in text or "float" in text or "integer" in text or "int" in text:
        severity = "error"
        issue_type = "invalid_numeric_value"
        suggestion = "Bu alani sayisal deger olacak sekilde duzeltin. Ornek: 84 veya 84.5."
    elif "aralik" in text or "range" in text or "negatif" in text:
        severity = "error"
        issue_type = "out_of_range"
        suggestion = "Degeri beklenen aralik icine alin; negatif veya asiri buyuk degerleri duzeltin."
    elif "bulunamadi" in text or "esles" in text or "match" in text:
        severity = "error"
        issue_type = "course_not_matched"
        suggestion = "Ders kodu veya ders adini sistemdeki ders kaydi ile ayni olacak sekilde duzeltin."
    elif "ambiguous" in text or "belirsiz" in text:
        severity = "warning"
        issue_type = "ambiguous_course_match"
        suggestion = "Ders kodunu ekleyerek eslesmeyi tekil hale getirin."
    elif "duplicate" in text or "tekrar" in text or "ayni ders" in text:
        severity = "warning"
        issue_type = "duplicate_course"
        suggestion = "Ayni ders icin tek satir birakin veya tekrar eden satirlari birlestirin."
    elif "fakulte" in text or "bolum" in text or "scope" in text or "kapsam" in text:
        severity = "error"
        issue_type = "invalid_scope"
        suggestion = "Satirdaki fakulte/bolum bilgisini secili import kapsami ile uyumlu yapin."
    elif "yil" in text or "year" in text:
        severity = "error"
        issue_type = "invalid_year"
        suggestion = "Yil alanini secili akademik yil ile ayni olacak sekilde duzeltin."
    elif "donem" in text or "semester" in text:
        severity = "error"
        issue_type = "invalid_semester"
        suggestion = "Donem alanini Guz veya Bahar olacak sekilde duzeltin."
    elif row_status in {"skipped_override"}:
        severity = "info"
        issue_type = "invalid_scope"
        suggestion = "Daha ozel bolum importu aktif oldugu icin fakulte geneli satir uygulanmadi."

    return severity, issue_type, suggestion


def record_import_issue(
    conn: sqlite3.Connection,
    import_batch_id: int,
    row_number: int,
    message: str,
    source_row_id: int | None = None,
    severity: str | None = None,
    issue_type: str | None = None,
    field_name: str | None = None,
    raw_value: Any = None,
    normalized_value: Any = None,
    suggestion: str | None = None,
) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    inferred_severity, inferred_type, inferred_suggestion = classify_issue(message, None, field_name)
    severity = severity or inferred_severity
    issue_type = issue_type or inferred_type
    suggestion = suggestion or inferred_suggestion
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO import_row_issues (
            import_batch_id, source_row_id, row_number, severity, issue_type, field_name,
            raw_value, normalized_value, message, suggestion, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(import_batch_id),
            int(source_row_id) if source_row_id is not None else None,
            int(row_number or 0),
            severity,
            issue_type,
            field_name,
            None if raw_value is None else str(raw_value),
            None if normalized_value is None else str(normalized_value),
            message,
            suggestion,
            _now(),
        ),
    )
    issue_id = int(cur.lastrowid or 0)
    return {"id": issue_id, "severity": severity, "issue_type": issue_type, "suggestion": suggestion}


def get_import_batch(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM import_batches WHERE id = ?", (int(import_batch_id),))
    row = cur.fetchone()
    return _row_to_dict(row)


def list_import_batches(
    conn: sqlite3.Connection,
    import_type: str | None = None,
    status: str | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    ensure_import_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    for col, value in (
        ("import_type", import_type),
        ("status", status),
        ("year", year),
        ("faculty_id", faculty_id),
        ("department_id", department_id),
    ):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(value)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT *
        FROM import_batches
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
        LIMIT ?
        """,
        tuple(params + [int(limit)]),
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def _source_row_table(import_type: str | None) -> str | None:
    if import_type == "criteria":
        return "criteria_import_rows"
    if import_type == "survey":
        return "survey_import_rows"
    return None


def list_import_rows(conn: sqlite3.Connection, import_batch_id: int, limit: int = 500) -> list[dict[str, Any]]:
    batch = get_import_batch(conn, import_batch_id)
    if not batch:
        return []
    table = _source_row_table(batch.get("import_type"))
    if table is None:
        try:
            from app.services.import_staging_service import list_staged_rows

            return list_staged_rows(conn, import_batch_id, limit)
        except sqlite3.DatabaseError:
            return []
    cur = conn.cursor()
    if not _table_exists(cur, table):
        return []
    cols = _column_names(cur, table)
    if "import_batch_id" in cols:
        cur.execute(f"SELECT * FROM {table} WHERE import_batch_id = ? ORDER BY row_no LIMIT ?", (int(import_batch_id), int(limit)))
    else:
        source_import_id = batch.get("source_import_id")
        if source_import_id is None:
            return []
        cur.execute(f"SELECT * FROM {table} WHERE import_id = ? ORDER BY row_no LIMIT ?", (int(source_import_id), int(limit)))
    rows = [_row_to_dict(row) for row in cur.fetchall()]
    if rows:
        return rows
    try:
        from app.services.import_staging_service import list_staged_rows

        return list_staged_rows(conn, import_batch_id, limit)
    except sqlite3.DatabaseError:
        return []


def list_import_issues(conn: sqlite3.Connection, import_batch_id: int, limit: int = 500) -> list[dict[str, Any]]:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM import_row_issues
        WHERE import_batch_id = ?
        ORDER BY CASE severity
            WHEN 'critical' THEN 0
            WHEN 'error' THEN 1
            WHEN 'warning' THEN 2
            ELSE 3
        END, row_number, id
        LIMIT ?
        """,
        (int(import_batch_id), int(limit)),
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def mark_batch_failed_by_path(
    db_path: str,
    file_path: str,
    import_type: str,
    error_message: str,
    **scope: Any,
) -> dict[str, Any]:
    conn = connect_sqlite(db_path, row_factory=True)
    try:
        ensure_import_governance_schema(conn)
        batch = create_import_batch(
            conn,
            import_type=import_type,
            original_filename=scope.get("original_filename") or os.path.basename(file_path),
            file_path=file_path,
            faculty_id=scope.get("faculty_id"),
            department_id=scope.get("department_id"),
            year=scope.get("year"),
            semester=scope.get("semester"),
            status="failed",
            validation_summary={"ok": False, "errors": [error_message]},
        )
        update_import_status(conn, int(batch["id"]), "failed", error_message=error_message)
        conn.commit()
        return batch
    finally:
        conn.close()


def preview_import(
    db_path: str,
    file_path: str,
    import_type: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    uploaded_by: str | None = None,
) -> dict[str, Any]:
    metadata = extract_excel_metadata(file_path)
    conn = connect_sqlite(db_path, row_factory=True)
    try:
        ensure_import_governance_schema(conn)
        batch = create_import_batch(
            conn,
            import_type=import_type,
            original_filename=os.path.basename(file_path),
            file_path=file_path,
            sheet_names=metadata.get("sheet_names") or [],
            columns=metadata.get("columns") or [],
            row_count=int(metadata.get("row_count") or 0),
            column_count=int(metadata.get("column_count") or 0),
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            semester=semester,
            uploaded_by=uploaded_by,
            status="validated",
            validation_summary={"preview_only": True, "columns": metadata.get("columns") or []},
        )
        conn.commit()
        return {"ok": True, "batch": batch, "metadata": metadata}
    finally:
        conn.close()


def save_upload_to_temp(upload: Any) -> str:
    suffix = Path(str(getattr(upload, "filename", "") or "")).suffix or ".xlsx"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = upload.file.read()
        temp.write(content)
        return temp.name

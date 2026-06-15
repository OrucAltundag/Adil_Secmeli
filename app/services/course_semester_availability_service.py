# -*- coding: utf-8 -*-
"""Ders bazli donem uygunlugu servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "evet", "on"}
    return bool(value)


def normalize_semester(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"spring", "bahar", "b"} or raw.startswith("b"):
        return "spring"
    if raw in {"fall", "guz", "güz", "g"} or raw.startswith("g"):
        return "fall"
    return raw or "fall"


def display_semester(value: str | None) -> str:
    return "Bahar" if normalize_semester(value) == "spring" else "Güz"


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        data = {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}
    for key in ("allowed_fall", "allowed_spring"):
        if key in data:
            data[key] = _bool(data[key])
    return data


def _fetch_one_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None:
    columns = [d[0] for d in cur.description] if cur.description else []
    return _row_to_dict(cur.fetchone(), columns)


def _fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    columns = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, columns) or {} for row in cur.fetchall()]


def default_availability(course_id: int, year: int | None = None) -> dict[str, Any]:
    return {
        "id": None,
        "course_id": int(course_id),
        "year": year,
        "faculty_id": None,
        "department_id": None,
        "allowed_fall": True,
        "allowed_spring": True,
        "preferred_semester": "either",
        "availability_type": "always",
        "unavailable_reason": None,
        "notes": None,
    }


def get_course_availability(
    conn: sqlite3.Connection,
    course_id: int,
    year: int | None = None,
    department_id: int | None = None,
    faculty_id: int | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    candidates = [
        (year, faculty_id, department_id),
        (year, faculty_id, None),
        (year, None, None),
        (None, faculty_id, department_id),
        (None, faculty_id, None),
        (None, None, None),
    ]
    for cand_year, cand_faculty, cand_department in candidates:
        where = ["course_id = ?"]
        params: list[Any] = [int(course_id)]
        for col, value in (("year", cand_year), ("faculty_id", cand_faculty), ("department_id", cand_department)):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(int(value))
        cur.execute(
            f"SELECT * FROM course_semester_availability WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
            tuple(params),
        )
        row = _fetch_one_dict(cur)
        if row:
            return row
    return default_availability(course_id, year)


def get_courses_availability_batch(
    conn: sqlite3.Connection,
    course_ids: list[int],
    year: int | None = None,
    department_id: int | None = None,
    faculty_id: int | None = None,
) -> dict[int, dict[str, Any]]:
    """Birden çok ders için dönem uygunluğunu tek geçişte çözer.

    `get_course_availability` ile aynı kapsam-daraltma (yıl/fakülte/bölüm > genel)
    önceliğini uygular ama her ders için ayrı sorgu yerine, her aday kapsam için
    `course_id IN (...)` ile toplu sorgu çalıştırır. Bir ders için ilk eşleşen
    (en yüksek öncelikli) kapsam kazanır; eşleşmeyenler varsayılana düşer.
    """
    ids = [int(c) for c in dict.fromkeys(course_ids)]
    if not ids:
        return {}
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    candidates = [
        (year, faculty_id, department_id),
        (year, faculty_id, None),
        (year, None, None),
        (None, faculty_id, department_id),
        (None, faculty_id, None),
        (None, None, None),
    ]
    resolved: dict[int, dict[str, Any]] = {}
    for cand_year, cand_faculty, cand_department in candidates:
        if len(resolved) == len(ids):
            break
        where = [f"course_id IN ({placeholders})"]
        params: list[Any] = list(ids)
        for col, value in (("year", cand_year), ("faculty_id", cand_faculty), ("department_id", cand_department)):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(int(value))
        # id DESC: her ders için ilk görülen satır o kapsamdaki en güncel kayıttır.
        cur.execute(
            f"SELECT * FROM course_semester_availability WHERE {' AND '.join(where)} ORDER BY id DESC",
            tuple(params),
        )
        for row in _fetch_all_dicts(cur):
            cid = row.get("course_id")
            if cid is None:
                continue
            cid = int(cid)
            if cid not in resolved:
                resolved[cid] = row
    for cid in ids:
        resolved.setdefault(cid, default_availability(cid, year))
    return resolved


def validate_course_semester(
    conn: sqlite3.Connection,
    course_id: int,
    semester: str,
    year: int | None = None,
    department_id: int | None = None,
    faculty_id: int | None = None,
) -> dict[str, Any]:
    sem = normalize_semester(semester)
    availability = get_course_availability(conn, int(course_id), year=year, department_id=department_id, faculty_id=faculty_id)
    allowed = bool(availability["allowed_spring"] if sem == "spring" else availability["allowed_fall"])
    preferred = str(availability.get("preferred_semester") or "either")
    warnings: list[str] = []
    if allowed and preferred in {"fall", "spring"} and preferred != sem:
        warnings.append(f"Ders için tercih edilen dönem {display_semester(preferred)}; {display_semester(sem)} soft kısıt olarak daha zayıf.")
    message = (
        f"Ders {display_semester(sem)} dönemine uygundur."
        if allowed
        else f"Ders {display_semester(sem)} döneminde açılamaz: {availability.get('unavailable_reason') or 'dönem uygunluğu kapalı'}."
    )
    return {
        "course_id": int(course_id),
        "semester": sem,
        "allowed": allowed,
        "availability": availability,
        "warnings": warnings,
        "message": message,
        "suggestion": None if allowed else "Dersi diğer döneme taşıyın veya dönem uygunluğu kaydını güncelleyin.",
    }


def upsert_course_availability(
    conn: sqlite3.Connection,
    course_id: int,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    allowed_fall: bool = True,
    allowed_spring: bool = True,
    preferred_semester: str = "either",
    availability_type: str = "always",
    unavailable_reason: str | None = None,
    effective_from_year: int | None = None,
    effective_to_year: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO course_semester_availability (
            course_id, year, faculty_id, department_id, allowed_fall, allowed_spring,
            preferred_semester, availability_type, unavailable_reason,
            effective_from_year, effective_to_year, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(course_id),
            int(year) if year is not None else None,
            int(faculty_id) if faculty_id is not None else None,
            int(department_id) if department_id is not None else None,
            1 if allowed_fall else 0,
            1 if allowed_spring else 0,
            preferred_semester,
            availability_type,
            unavailable_reason,
            effective_from_year,
            effective_to_year,
            now,
            now,
            notes,
        ),
    )
    return get_course_availability(conn, int(course_id), year=year, department_id=department_id, faculty_id=faculty_id)


def list_availability_by_scope(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    for col, value in (("year", year), ("faculty_id", faculty_id), ("department_id", department_id), ("course_id", course_id)):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(int(value))
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM course_semester_availability WHERE {' AND '.join(where)} ORDER BY course_id, year DESC, id DESC",
        tuple(params),
    )
    return _fetch_all_dicts(cur)

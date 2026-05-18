from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any

from app.core.config import resolve_sqlite_db_path
from app.db.schema_compat import ensure_ders_code_schema
from app.services.db import get_raw_connection

_TR_ASCII_MAP: tuple[tuple[str, str], ...] = (
    ("\u00c7", "C"),
    ("\u00e7", "C"),
    ("\u011e", "G"),
    ("\u011f", "G"),
    ("\u0130", "I"),
    ("I", "I"),
    ("\u0131", "I"),
    ("\u00d6", "O"),
    ("\u00f6", "O"),
    ("\u015e", "S"),
    ("\u015f", "S"),
    ("\u00dc", "U"),
    ("\u00fc", "U"),
)


@dataclass(frozen=True)
class MissingCourseCodeRow:
    ders_id: int
    ders_adi: str
    bolum_id: int | None
    bolum_adi: str | None
    fakulte_id: int | None
    fakulte_adi: str | None
    generated_code: str
    existing_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_ascii_upper(value: str | None) -> str:
    text = str(value or "").strip().upper()
    for src, dst in _TR_ASCII_MAP:
        text = text.replace(src, dst)
    text = re.sub(r"[^A-Z0-9 ]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_name_initial(value: str | None, fallback: str = "X") -> str:
    normalized = normalize_ascii_upper(value)
    for ch in normalized:
        if "A" <= ch <= "Z":
            return ch
    return fallback


def build_course_code(fakulte_adi: str | None, bolum_adi: str | None, ders_id: int) -> str:
    faculty_initial = build_name_initial(fakulte_adi)
    department_initial = build_name_initial(bolum_adi)
    return f"{faculty_initial}{department_initial}{int(ders_id)}"


def _fetch_missing_course_code_rows(conn: sqlite3.Connection) -> list[MissingCourseCodeRow]:
    ensure_ders_code_schema(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            d.ders_id,
            COALESCE(d.ad, '') AS ders_adi,
            d.bolum_id,
            b.ad AS bolum_adi,
            COALESCE(d.fakulte_id, b.fakulte_id) AS resolved_fakulte_id,
            f.ad AS fakulte_adi,
            d.kod AS existing_code
        FROM ders d
        LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
        LEFT JOIN fakulte f ON f.fakulte_id = COALESCE(d.fakulte_id, b.fakulte_id)
        WHERE TRIM(COALESCE(d.kod, '')) = ''
        ORDER BY d.ders_id
        """
    )

    rows: list[MissingCourseCodeRow] = []
    for item in cur.fetchall():
        ders_id = int(item[0])
        ders_adi = str(item[1] or "").strip()
        bolum_id = int(item[2]) if item[2] is not None else None
        bolum_adi = str(item[3] or "").strip() or None
        fakulte_id = int(item[4]) if item[4] is not None else None
        fakulte_adi = str(item[5] or "").strip() or None
        existing_code = str(item[6] or "").strip() or None

        rows.append(
            MissingCourseCodeRow(
                ders_id=ders_id,
                ders_adi=ders_adi,
                bolum_id=bolum_id,
                bolum_adi=bolum_adi,
                fakulte_id=fakulte_id,
                fakulte_adi=fakulte_adi,
                generated_code=build_course_code(
                    fakulte_adi=fakulte_adi,
                    bolum_adi=bolum_adi,
                    ders_id=ders_id,
                ),
                existing_code=existing_code,
            )
        )
    return rows


def preview_missing_course_codes(db_path: str) -> dict[str, Any]:
    resolved_db_path = resolve_sqlite_db_path(db_path)
    if not resolved_db_path.exists():
        raise FileNotFoundError(f"Veritabani bulunamadi: {resolved_db_path}")

    conn = get_raw_connection(str(resolved_db_path))
    try:
        rows = _fetch_missing_course_code_rows(conn)
        return {
            "ok": True,
            "missing_count": len(rows),
            "rows": [row.as_dict() for row in rows],
        }
    finally:
        conn.close()


def apply_missing_course_codes(db_path: str) -> dict[str, Any]:
    resolved_db_path = resolve_sqlite_db_path(db_path)
    if not resolved_db_path.exists():
        raise FileNotFoundError(f"Veritabani bulunamadi: {resolved_db_path}")

    conn = get_raw_connection(str(resolved_db_path))
    try:
        rows = _fetch_missing_course_code_rows(conn)
        cur = conn.cursor()
        updated_count = 0

        for row in rows:
            cur.execute(
                """
                UPDATE ders
                SET kod = ?
                WHERE ders_id = ?
                  AND TRIM(COALESCE(kod, '')) = ''
                """,
                (row.generated_code, int(row.ders_id)),
            )
            updated_count += int(cur.rowcount or 0)

        conn.commit()

        cur.execute("SELECT COUNT(*) FROM ders WHERE TRIM(COALESCE(kod, '')) = ''")
        remaining_blank_count = int(cur.fetchone()[0] or 0)

        return {
            "ok": True,
            "updated_count": updated_count,
            "remaining_blank_count": remaining_blank_count,
            "rows": [row.as_dict() for row in rows],
        }
    finally:
        conn.close()

# -*- coding: utf-8 -*-
"""
Year-based criteria workflow state helpers.

Bu modul:
- Kriter giris tamamlama durumunu bolum/fakulte bazinda izler.
- Algoritma calisma durumunu yil/fakulte bazinda izler.
- Havuz ekraninda gorunecek "aktif yil" listesini yonetir.
- Sonraki yil uretiminde dis bolum dersi sayisini kaydeder.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.core.settings import load_settings
from app.services.course_type import filter_elective_course_ids


STATUS_NOT_STARTED = "not_started"
STATUS_PARTIAL = "partial"
STATUS_COMPLETED = "completed"

ALGORITHM_NOT_RUN = "not_run"
ALGORITHM_RAN = "ran"
ALGORITHM_FAILED = "failed"


def is_yearly_workflow_enabled() -> bool:
    raw_env = os.getenv("ENABLE_YEARLY_CRITERIA_WORKFLOW")
    if raw_env is not None:
        return str(raw_env).strip().lower() in {"1", "true", "yes", "on"}
    try:
        settings = load_settings(config_path="config.json")
        return bool(getattr(settings, "enable_yearly_criteria_workflow", True))
    except Exception:
        return True


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return bool(cur.fetchone())


def ensure_yearly_workflow_schema(
    conn: sqlite3.Connection,
    auto_commit: bool = True,
) -> dict[str, int]:
    cur = conn.cursor()
    changed = {"tables_created": 0, "indexes_created": 0}

    if not _table_exists(cur, "criteria_department_status"):
        cur.execute(
            """
            CREATE TABLE criteria_department_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fakulte_id INTEGER NOT NULL,
                bolum_id INTEGER NOT NULL,
                yil INTEGER NOT NULL,
                criteria_status TEXT NOT NULL DEFAULT 'not_started',
                required_course_count INTEGER NOT NULL DEFAULT 0,
                completed_course_count INTEGER NOT NULL DEFAULT 0,
                missing_course_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT,
                UNIQUE(fakulte_id, bolum_id, yil)
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "criteria_faculty_status"):
        cur.execute(
            """
            CREATE TABLE criteria_faculty_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fakulte_id INTEGER NOT NULL,
                yil INTEGER NOT NULL,
                criteria_status TEXT NOT NULL DEFAULT 'not_started',
                total_department_count INTEGER NOT NULL DEFAULT 0,
                completed_department_count INTEGER NOT NULL DEFAULT 0,
                algorithm_run_status TEXT NOT NULL DEFAULT 'not_run',
                algorithm_run_at TEXT,
                generated_year INTEGER,
                year_active INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT,
                UNIQUE(fakulte_id, yil)
            )
            """
        )
        changed["tables_created"] += 1

    if not _table_exists(cur, "curriculum_generation_audit"):
        cur.execute(
            """
            CREATE TABLE curriculum_generation_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fakulte_id INTEGER NOT NULL,
                bolum_id INTEGER NOT NULL,
                source_year INTEGER NOT NULL,
                generated_year INTEGER NOT NULL,
                dis_bolum_ders_sayisi INTEGER NOT NULL DEFAULT 0,
                run_at TEXT,
                UNIQUE(fakulte_id, bolum_id, source_year, generated_year)
            )
            """
        )
        changed["tables_created"] += 1

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_department_status_scope
        ON criteria_department_status (fakulte_id, bolum_id, yil)
        """
    )
    changed["indexes_created"] += 1
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_faculty_status_scope
        ON criteria_faculty_status (fakulte_id, yil)
        """
    )
    changed["indexes_created"] += 1
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_generation_audit_scope
        ON curriculum_generation_audit (fakulte_id, bolum_id, source_year, generated_year)
        """
    )
    changed["indexes_created"] += 1

    if auto_commit:
        conn.commit()
    return changed


def _faculty_name(cur: sqlite3.Cursor, fakulte_id: int) -> str:
    cur.execute("SELECT ad FROM fakulte WHERE fakulte_id = ? LIMIT 1", (int(fakulte_id),))
    row = cur.fetchone()
    return str(row[0]) if row and row[0] is not None else str(fakulte_id)


def _department_name(cur: sqlite3.Cursor, bolum_id: int) -> str:
    cur.execute("SELECT ad FROM bolum WHERE bolum_id = ? LIMIT 1", (int(bolum_id),))
    row = cur.fetchone()
    return str(row[0]) if row and row[0] is not None else str(bolum_id)


def _departments_for_faculty_year(cur: sqlite3.Cursor, fakulte_id: int, yil: int) -> list[tuple[int, str]]:
    cur.execute(
        """
        SELECT DISTINCT b.bolum_id, b.ad
        FROM bolum b
        WHERE b.fakulte_id = ?
          AND EXISTS (
              SELECT 1
              FROM mufredat m
              WHERE m.bolum_id = b.bolum_id
                AND m.akademik_yil = ?
          )
        ORDER BY b.ad
        """,
        (int(fakulte_id), int(yil)),
    )
    return [(int(r[0]), str(r[1] or "")) for r in cur.fetchall() if r and r[0] is not None]


def _required_department_course_ids(
    cur: sqlite3.Cursor,
    fakulte_id: int,
    bolum_id: int,
    yil: int,
) -> set[int]:
    cur.execute(
        """
        SELECT DISTINCT md.ders_id
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE b.fakulte_id = ?
          AND m.bolum_id = ?
          AND m.akademik_yil = ?
        """,
        (int(fakulte_id), int(bolum_id), int(yil)),
    )
    ids = {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
    return filter_elective_course_ids(cur, ids)


def _criteria_table_available(cur: sqlite3.Cursor) -> bool:
    return _table_exists(cur, "ders_kriterleri")


def _latest_criteria_row(cur: sqlite3.Cursor, ders_id: int, yil: int) -> tuple[Any, ...] | None:
    if not _criteria_table_available(cur):
        return None
    try:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
        return cur.fetchone()
    except sqlite3.OperationalError:
        return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _is_criteria_complete_row(row: tuple[Any, ...] | None) -> bool:
    if not row:
        return False
    toplam = _as_float(row[0], 0.0)
    gecen = _as_float(row[1], 0.0)
    ort = _as_float(row[2], 0.0)
    kont = _as_float(row[3], 0.0)
    kayitli = _as_float(row[4], 0.0)
    if toplam <= 0 or kont <= 0 or ort <= 0:
        return False
    if gecen < 0 or kayitli < 0:
        return False
    if gecen > toplam:
        return False
    return True


def get_missing_criteria(
    conn: sqlite3.Connection,
    yil: int,
    fakulte_id: int | None = None,
    bolum_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_yearly_workflow_schema(conn)
    cur = conn.cursor()

    departments: list[tuple[int, int, str, str]] = []
    if bolum_id is not None:
        cur.execute(
            """
            SELECT b.fakulte_id, b.bolum_id, b.ad, f.ad
            FROM bolum b
            LEFT JOIN fakulte f ON f.fakulte_id = b.fakulte_id
            WHERE b.bolum_id = ?
              AND (? IS NULL OR b.fakulte_id = ?)
            LIMIT 1
            """,
            (int(bolum_id), fakulte_id, fakulte_id),
        )
        row = cur.fetchone()
        if row and row[0] is not None and row[1] is not None:
            departments.append((int(row[0]), int(row[1]), str(row[2] or ""), str(row[3] or "")))
    elif fakulte_id is not None:
        cur.execute(
            """
            SELECT b.fakulte_id, b.bolum_id, b.ad, f.ad
            FROM bolum b
            LEFT JOIN fakulte f ON f.fakulte_id = b.fakulte_id
            WHERE b.fakulte_id = ?
              AND EXISTS (
                  SELECT 1 FROM mufredat m WHERE m.bolum_id = b.bolum_id AND m.akademik_yil = ?
              )
            ORDER BY b.ad
            """,
            (int(fakulte_id), int(yil)),
        )
        departments = [
            (int(r[0]), int(r[1]), str(r[2] or ""), str(r[3] or ""))
            for r in cur.fetchall()
            if r and r[0] is not None and r[1] is not None
        ]
    else:
        cur.execute(
            """
            SELECT b.fakulte_id, b.bolum_id, b.ad, f.ad
            FROM bolum b
            LEFT JOIN fakulte f ON f.fakulte_id = b.fakulte_id
            WHERE EXISTS (
                SELECT 1 FROM mufredat m WHERE m.bolum_id = b.bolum_id AND m.akademik_yil = ?
            )
            ORDER BY f.ad, b.ad
            """,
            (int(yil),),
        )
        departments = [
            (int(r[0]), int(r[1]), str(r[2] or ""), str(r[3] or ""))
            for r in cur.fetchall()
            if r and r[0] is not None and r[1] is not None
        ]

    missing: list[dict[str, Any]] = []
    for dep_fid, dep_bid, dep_name, fac_name in departments:
        required_ids = sorted(_required_department_course_ids(cur, dep_fid, dep_bid, int(yil)))
        if not required_ids:
            continue
        if required_ids:
            placeholders = ",".join("?" for _ in required_ids)
            cur.execute(
                f"SELECT ders_id, ad FROM ders WHERE ders_id IN ({placeholders})",
                tuple(required_ids),
            )
            ders_name_map = {int(r[0]): str(r[1] or "") for r in cur.fetchall() if r and r[0] is not None}
        else:
            ders_name_map = {}
        for ders_id in required_ids:
            if _is_criteria_complete_row(_latest_criteria_row(cur, int(ders_id), int(yil))):
                continue
            missing.append(
                {
                    "yil": int(yil),
                    "fakulte_id": int(dep_fid),
                    "fakulte": fac_name or str(dep_fid),
                    "bolum_id": int(dep_bid),
                    "bolum": dep_name or str(dep_bid),
                    "ders_id": int(ders_id),
                    "ders": ders_name_map.get(int(ders_id), str(ders_id)),
                }
            )
    return missing


def _department_progress(
    cur: sqlite3.Cursor,
    yil: int,
    fakulte_id: int,
    bolum_id: int,
) -> dict[str, Any]:
    required_ids = sorted(_required_department_course_ids(cur, fakulte_id, bolum_id, yil))
    required_count = len(required_ids)
    missing_ids = []
    for ders_id in required_ids:
        if not _is_criteria_complete_row(_latest_criteria_row(cur, ders_id, yil)):
            missing_ids.append(int(ders_id))
    missing_count = len(missing_ids)
    completed_count = max(0, required_count - missing_count)
    if required_count == 0:
        status = STATUS_NOT_STARTED
    elif missing_count == 0:
        status = STATUS_COMPLETED
    elif completed_count == 0:
        status = STATUS_NOT_STARTED
    else:
        status = STATUS_PARTIAL
    return {
        "criteria_status": status,
        "required_course_count": required_count,
        "completed_course_count": completed_count,
        "missing_course_count": missing_count,
        "missing_ids": missing_ids,
    }


def _upsert_department_status(
    cur: sqlite3.Cursor,
    fakulte_id: int,
    bolum_id: int,
    yil: int,
    progress: dict[str, Any],
) -> None:
    cur.execute(
        """
        INSERT INTO criteria_department_status
            (fakulte_id, bolum_id, yil, criteria_status,
             required_course_count, completed_course_count, missing_course_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fakulte_id, bolum_id, yil) DO UPDATE SET
            criteria_status = excluded.criteria_status,
            required_course_count = excluded.required_course_count,
            completed_course_count = excluded.completed_course_count,
            missing_course_count = excluded.missing_course_count,
            updated_at = excluded.updated_at
        """,
        (
            int(fakulte_id),
            int(bolum_id),
            int(yil),
            str(progress["criteria_status"]),
            int(progress["required_course_count"]),
            int(progress["completed_course_count"]),
            int(progress["missing_course_count"]),
            _now_utc(),
        ),
    )


def _upsert_faculty_status(
    cur: sqlite3.Cursor,
    fakulte_id: int,
    yil: int,
    criteria_status: str,
    total_department_count: int,
    completed_department_count: int,
    algorithm_run_status: str,
    generated_year: int | None,
    year_active: int,
) -> None:
    cur.execute(
        """
        INSERT INTO criteria_faculty_status
            (fakulte_id, yil, criteria_status, total_department_count, completed_department_count,
             algorithm_run_status, algorithm_run_at, generated_year, year_active, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        ON CONFLICT(fakulte_id, yil) DO UPDATE SET
            criteria_status = excluded.criteria_status,
            total_department_count = excluded.total_department_count,
            completed_department_count = excluded.completed_department_count,
            algorithm_run_status = excluded.algorithm_run_status,
            algorithm_run_at = CASE
                WHEN excluded.algorithm_run_status = 'not_run' THEN NULL
                ELSE criteria_faculty_status.algorithm_run_at
            END,
            generated_year = excluded.generated_year,
            year_active = excluded.year_active,
            updated_at = excluded.updated_at
        """,
        (
            int(fakulte_id),
            int(yil),
            str(criteria_status),
            int(total_department_count),
            int(completed_department_count),
            str(algorithm_run_status),
            int(generated_year) if generated_year is not None else None,
            int(year_active),
            _now_utc(),
        ),
    )


def is_department_criteria_complete(
    conn: sqlite3.Connection,
    yil: int,
    fakulte_id: int,
    bolum_id: int,
) -> bool:
    ensure_yearly_workflow_schema(conn)
    cur = conn.cursor()
    progress = _department_progress(cur, int(yil), int(fakulte_id), int(bolum_id))
    return str(progress["criteria_status"]) == STATUS_COMPLETED


def is_faculty_criteria_complete(
    conn: sqlite3.Connection,
    yil: int,
    fakulte_id: int,
    refresh: bool = True,
) -> bool:
    ensure_yearly_workflow_schema(conn)
    cur = conn.cursor()
    departments = _departments_for_faculty_year(cur, int(fakulte_id), int(yil))
    completed = 0
    for bolum_id, _bolum_name in departments:
        progress = _department_progress(cur, int(yil), int(fakulte_id), int(bolum_id))
        if refresh:
            _upsert_department_status(cur, int(fakulte_id), int(bolum_id), int(yil), progress)
        if str(progress["criteria_status"]) == STATUS_COMPLETED:
            completed += 1

    if not departments:
        status = STATUS_NOT_STARTED
    elif completed == len(departments):
        status = STATUS_COMPLETED
    elif completed == 0:
        status = STATUS_NOT_STARTED
    else:
        status = STATUS_PARTIAL

    if refresh:
        cur.execute(
            """
            SELECT algorithm_run_status, generated_year, year_active
            FROM criteria_faculty_status
            WHERE fakulte_id = ? AND yil = ?
            LIMIT 1
            """,
            (int(fakulte_id), int(yil)),
        )
        row = cur.fetchone()
        old_algo = str(row[0]) if row and row[0] else ALGORITHM_NOT_RUN
        old_generated = int(row[1]) if row and row[1] is not None else None
        old_active = int(row[2]) if row and row[2] is not None else 1
        _upsert_faculty_status(
            cur=cur,
            fakulte_id=int(fakulte_id),
            yil=int(yil),
            criteria_status=status,
            total_department_count=len(departments),
            completed_department_count=completed,
            algorithm_run_status=old_algo,
            generated_year=old_generated,
            year_active=old_active,
        )
        conn.commit()

    return status == STATUS_COMPLETED


def mark_criteria_status(
    conn: sqlite3.Connection,
    yil: int,
    fakulte_id: int,
    bolum_id: int | None = None,
) -> dict[str, Any]:
    """
    Kaydedilen kriter sonrasi durum tablosunu gunceller.
    - bolum_id verilirse bolum + fakulte durumunu gunceller.
    - bolum_id verilmezse fakultedeki tum bolumleri yeniden hesaplar.
    """
    ensure_yearly_workflow_schema(conn)
    cur = conn.cursor()
    yil = int(yil)
    fakulte_id = int(fakulte_id)
    previous_dep_status = None
    previous_fac_status = None

    if bolum_id is not None:
        bolum_id = int(bolum_id)
        cur.execute(
            """
            SELECT criteria_status
            FROM criteria_department_status
            WHERE fakulte_id = ? AND bolum_id = ? AND yil = ?
            LIMIT 1
            """,
            (fakulte_id, bolum_id, yil),
        )
        row = cur.fetchone()
        previous_dep_status = str(row[0]) if row and row[0] else None

    cur.execute(
        """
        SELECT criteria_status
        FROM criteria_faculty_status
        WHERE fakulte_id = ? AND yil = ?
        LIMIT 1
        """,
        (fakulte_id, yil),
    )
    row = cur.fetchone()
    previous_fac_status = str(row[0]) if row and row[0] else None

    departments = _departments_for_faculty_year(cur, fakulte_id, yil)
    if bolum_id is not None:
        departments = [item for item in departments if int(item[0]) == bolum_id]
        if not departments:
            departments = [(bolum_id, _department_name(cur, bolum_id))]

    department_result = None
    for dep_id, dep_name in departments:
        progress = _department_progress(cur, yil, fakulte_id, dep_id)
        _upsert_department_status(cur, fakulte_id, dep_id, yil, progress)
        if bolum_id is not None and int(dep_id) == int(bolum_id):
            department_result = {
                "bolum_id": int(dep_id),
                "bolum": dep_name or str(dep_id),
                **progress,
            }

    all_departments = _departments_for_faculty_year(cur, fakulte_id, yil)
    completed_count = 0
    for dep_id, _dep_name in all_departments:
        progress = _department_progress(cur, yil, fakulte_id, dep_id)
        _upsert_department_status(cur, fakulte_id, dep_id, yil, progress)
        if str(progress["criteria_status"]) == STATUS_COMPLETED:
            completed_count += 1

    if not all_departments:
        faculty_status = STATUS_NOT_STARTED
    elif completed_count == len(all_departments):
        faculty_status = STATUS_COMPLETED
    elif completed_count == 0:
        faculty_status = STATUS_NOT_STARTED
    else:
        faculty_status = STATUS_PARTIAL

    _upsert_faculty_status(
        cur=cur,
        fakulte_id=fakulte_id,
        yil=yil,
        criteria_status=faculty_status,
        total_department_count=len(all_departments),
        completed_department_count=completed_count,
        algorithm_run_status=ALGORITHM_NOT_RUN,
        generated_year=None,
        year_active=1,
    )
    conn.commit()

    dep_completed_now = bool(
        department_result
        and department_result.get("criteria_status") == STATUS_COMPLETED
        and previous_dep_status != STATUS_COMPLETED
    )
    fac_completed_now = bool(
        faculty_status == STATUS_COMPLETED and previous_fac_status != STATUS_COMPLETED
    )

    messages: list[str] = []
    if dep_completed_now and department_result:
        messages.append(
            f"{department_result['bolum']} bolumu, {yil} yili kriter girdisi tamamlanmistir."
        )
    if fac_completed_now:
        messages.append(
            f"{_faculty_name(cur, fakulte_id)} fakultesindeki tum bolumlerin {yil} yili kriter girdisi tamamlanmistir."
        )

    return {
        "yil": yil,
        "fakulte_id": fakulte_id,
        "fakulte": _faculty_name(cur, fakulte_id),
        "department": department_result,
        "faculty": {
            "criteria_status": faculty_status,
            "total_department_count": len(all_departments),
            "completed_department_count": completed_count,
        },
        "department_completed_now": dep_completed_now,
        "faculty_completed_now": fac_completed_now,
        "messages": messages,
    }


def get_faculty_year_status(
    conn: sqlite3.Connection,
    fakulte_id: int,
    yil: int,
    refresh: bool = False,
) -> dict[str, Any]:
    ensure_yearly_workflow_schema(conn)
    if refresh:
        is_faculty_criteria_complete(conn, int(yil), int(fakulte_id), refresh=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT criteria_status, total_department_count, completed_department_count,
               algorithm_run_status, algorithm_run_at, generated_year, year_active, updated_at
        FROM criteria_faculty_status
        WHERE fakulte_id = ? AND yil = ?
        LIMIT 1
        """,
        (int(fakulte_id), int(yil)),
    )
    row = cur.fetchone()
    if not row:
        return {
            "fakulte_id": int(fakulte_id),
            "yil": int(yil),
            "criteria_status": STATUS_NOT_STARTED,
            "total_department_count": 0,
            "completed_department_count": 0,
            "algorithm_run_status": ALGORITHM_NOT_RUN,
            "algorithm_run_at": None,
            "generated_year": None,
            "year_active": 0,
            "updated_at": None,
        }
    return {
        "fakulte_id": int(fakulte_id),
        "yil": int(yil),
        "criteria_status": str(row[0] or STATUS_NOT_STARTED),
        "total_department_count": int(row[1] or 0),
        "completed_department_count": int(row[2] or 0),
        "algorithm_run_status": str(row[3] or ALGORITHM_NOT_RUN),
        "algorithm_run_at": row[4],
        "generated_year": int(row[5]) if row[5] is not None else None,
        "year_active": int(row[6] or 0),
        "updated_at": row[7],
    }


def is_algorithm_run_for_year(conn: sqlite3.Connection, fakulte_id: int, yil: int) -> bool:
    status = get_faculty_year_status(conn, int(fakulte_id), int(yil), refresh=False)
    return str(status.get("algorithm_run_status")) == ALGORITHM_RAN


def mark_algorithm_run(
    conn: sqlite3.Connection,
    fakulte_id: int,
    source_year: int,
    generated_year: int | None,
    success: bool,
) -> None:
    ensure_yearly_workflow_schema(conn)
    cur = conn.cursor()

    current = get_faculty_year_status(conn, int(fakulte_id), int(source_year), refresh=False)
    algo_status = ALGORITHM_RAN if success else ALGORITHM_FAILED
    criteria_status = str(current.get("criteria_status") or STATUS_NOT_STARTED)
    total_count = int(current.get("total_department_count") or 0)
    completed_count = int(current.get("completed_department_count") or 0)
    if criteria_status == STATUS_NOT_STARTED and total_count == 0:
        is_faculty_criteria_complete(conn, int(source_year), int(fakulte_id), refresh=True)
        current = get_faculty_year_status(conn, int(fakulte_id), int(source_year), refresh=False)
        criteria_status = str(current.get("criteria_status") or STATUS_NOT_STARTED)
        total_count = int(current.get("total_department_count") or 0)
        completed_count = int(current.get("completed_department_count") or 0)

    cur.execute(
        """
        INSERT INTO criteria_faculty_status
            (fakulte_id, yil, criteria_status, total_department_count, completed_department_count,
             algorithm_run_status, algorithm_run_at, generated_year, year_active, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(fakulte_id, yil) DO UPDATE SET
            criteria_status = excluded.criteria_status,
            total_department_count = excluded.total_department_count,
            completed_department_count = excluded.completed_department_count,
            algorithm_run_status = excluded.algorithm_run_status,
            algorithm_run_at = excluded.algorithm_run_at,
            generated_year = excluded.generated_year,
            year_active = 1,
            updated_at = excluded.updated_at
        """,
        (
            int(fakulte_id),
            int(source_year),
            criteria_status,
            total_count,
            completed_count,
            algo_status,
            _now_utc(),
            int(generated_year) if generated_year is not None else None,
            _now_utc(),
        ),
    )

    if generated_year is not None and success:
        cur.execute(
            """
            INSERT INTO criteria_faculty_status
                (fakulte_id, yil, criteria_status, total_department_count, completed_department_count,
                 algorithm_run_status, algorithm_run_at, generated_year, year_active, updated_at)
            VALUES (?, ?, ?, 0, 0, ?, NULL, NULL, 1, ?)
            ON CONFLICT(fakulte_id, yil) DO UPDATE SET
                year_active = 1,
                updated_at = excluded.updated_at
            """,
            (
                int(fakulte_id),
                int(generated_year),
                STATUS_NOT_STARTED,
                ALGORITHM_NOT_RUN,
                _now_utc(),
            ),
        )

    conn.commit()


def reset_year_workflow_for_import(
    conn: sqlite3.Connection,
    yil: int,
    scopes: list[tuple[int, int]],
) -> dict[str, int]:
    """
    Import sonrasi yalnizca ilgili yil/fakulte/bolum kapsaminda workflow durumunu sifirlar.
    scopes: [(fakulte_id, bolum_id), ...]
    """
    ensure_yearly_workflow_schema(conn, auto_commit=False)
    cur = conn.cursor()
    yil = int(yil)

    unique_scopes = sorted({(int(fid), int(bid)) for fid, bid in scopes})
    faculties = sorted({int(fid) for fid, _ in unique_scopes})

    dep_updates = 0
    for fakulte_id, bolum_id in unique_scopes:
        cur.execute(
            """
            INSERT INTO criteria_department_status
                (fakulte_id, bolum_id, yil, criteria_status,
                 required_course_count, completed_course_count, missing_course_count, updated_at)
            VALUES (?, ?, ?, 'not_started', 0, 0, 0, ?)
            ON CONFLICT(fakulte_id, bolum_id, yil) DO UPDATE SET
                criteria_status = 'not_started',
                required_course_count = 0,
                completed_course_count = 0,
                missing_course_count = 0,
                updated_at = excluded.updated_at
            """,
            (fakulte_id, bolum_id, yil, _now_utc()),
        )
        dep_updates += 1

    fac_updates = 0
    for fakulte_id in faculties:
        cur.execute(
            """
            INSERT INTO criteria_faculty_status
                (fakulte_id, yil, criteria_status, total_department_count, completed_department_count,
                 algorithm_run_status, algorithm_run_at, generated_year, year_active, updated_at)
            VALUES (?, ?, 'not_started', 0, 0, 'not_run', NULL, NULL, 1, ?)
            ON CONFLICT(fakulte_id, yil) DO UPDATE SET
                criteria_status = 'not_started',
                completed_department_count = 0,
                algorithm_run_status = 'not_run',
                algorithm_run_at = NULL,
                generated_year = NULL,
                year_active = 1,
                updated_at = excluded.updated_at
            """,
            (int(fakulte_id), yil, _now_utc()),
        )
        fac_updates += 1

    conn.commit()
    return {"department_updates": dep_updates, "faculty_updates": fac_updates}


def list_active_years_for_faculty(conn: sqlite3.Connection, fakulte_id: int) -> list[int]:
    ensure_yearly_workflow_schema(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT yil
        FROM criteria_faculty_status
        WHERE fakulte_id = ? AND year_active = 1
        ORDER BY yil
        """,
        (int(fakulte_id),),
    )
    years = sorted({int(r[0]) for r in cur.fetchall() if r and r[0] is not None})
    if years:
        return years

    cur.execute(
        """
        SELECT DISTINCT yil FROM havuz WHERE fakulte_id = ?
        UNION
        SELECT DISTINCT m.akademik_yil
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        WHERE b.fakulte_id = ?
        ORDER BY 1
        """,
        (int(fakulte_id), int(fakulte_id)),
    )
    return sorted({int(r[0]) for r in cur.fetchall() if r and r[0] is not None})


def record_cross_department_usage(
    conn: sqlite3.Connection,
    fakulte_id: int,
    bolum_id: int,
    source_year: int,
    generated_year: int,
    dis_bolum_ders_sayisi: int,
) -> None:
    ensure_yearly_workflow_schema(conn, auto_commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO curriculum_generation_audit
            (fakulte_id, bolum_id, source_year, generated_year, dis_bolum_ders_sayisi, run_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(fakulte_id, bolum_id, source_year, generated_year) DO UPDATE SET
            dis_bolum_ders_sayisi = excluded.dis_bolum_ders_sayisi,
            run_at = excluded.run_at
        """,
        (
            int(fakulte_id),
            int(bolum_id),
            int(source_year),
            int(generated_year),
            int(dis_bolum_ders_sayisi),
            _now_utc(),
        ),
    )
    # Caller transaction boundary korunur; commit burada zorlanmaz.

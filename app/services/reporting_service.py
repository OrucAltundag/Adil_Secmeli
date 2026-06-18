from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from io import StringIO
from typing import Any

from app.db.schema_compat import ensure_reporting_schema
from app.services.calculation import (
    DROP_AVERAGE_GRADE_THRESHOLD,
    DROP_SCORE_THRESHOLD,
    POOL_ANKET_SCORE_SPREAD,
    POOL_DEFAULT_SCORE,
    ensure_pool_visibility_for_curriculum,
    get_faculty_year_topsis_results,
    persist_faculty_year_topsis_scores,
)
from app.services.course_type import build_elective_predicate
from app.services.criteria_completion_service import (
    get_completion_matrix,
    get_completion_summary,
    get_validation_issues,
)
from app.services.criteria_import_service import summarize_report_criteria_scope
from app.services.criteria_task_service import get_tasks
from app.services.import_audit_service import (
    get_import_batch,
    list_import_batches,
    list_import_issues,
    list_import_rows,
)
from app.services.import_diff_service import get_import_diff
from app.services.import_impact_service import get_import_impact
from app.services.import_quality_service import summarize_quality
from app.services.missing_data_risk_service import (
    get_missing_data_risk_report as _get_missing_data_risk_report,
)
from app.services.pool_state_machine_service import (
    get_course_state_history as _get_course_state_history,
)
from app.services.pool_state_machine_service import (
    get_pool_lifecycle_summary as _get_pool_lifecycle_summary,
)
from app.services.pool_state_machine_service import (
    get_protected_courses as _get_protected_courses,
)
from app.services.pool_state_machine_service import (
    get_reactivation_candidates as _get_reactivation_candidates,
)
from app.services.pool_state_machine_service import (
    list_pending_approvals as _list_pool_pending_approvals,
)
from app.services.pool_state_machine_service import (
    list_state_transitions as _list_state_transitions,
)
from app.services.yearly_workflow import (
    get_faculty_year_status,
    is_yearly_workflow_enabled,
)


def normalize_term(term: str | None) -> str:
    raw = str(term or "").strip().lower()
    if raw.startswith("b"):
        return "Bahar"
    return "Guz"


def term_key(term: str | None) -> str:
    return "b" if normalize_term(term) == "Bahar" else "g"


def status_label(status: int | None) -> str:
    value = int(status or 0)
    if value == 1:
        return "Mufredatta (1)"
    if value == -1:
        return "Dinlenmede (-1)"
    if value == -2:
        return "Kalici Iptal (-2)"
    return "Havuzda (0)"


def _conn_from_db(db):
    return getattr(db, "conn", None)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table_name})")
        return {str(row[1]) for row in cur.fetchall()}
    except Exception:
        return set()


def ensure_score_source_schema(db) -> None:
    conn = _conn_from_db(db)
    if conn is None:
        return
    ensure_reporting_schema(conn)


def _persist_score_source(db, year: int, term: str, score_map: dict[int, float]) -> None:
    ensure_score_source_schema(db)
    normalized_term = normalize_term(term)
    now = datetime.utcnow().isoformat(timespec="seconds")
    for ders_id, score in score_map.items():
        _, existing = db.run_sql(
            """
            SELECT skor_id
            FROM skor
            WHERE ders_id = ?
              AND akademik_yil = ?
              AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
            LIMIT 1
            """,
            (int(ders_id), int(year), term_key(normalized_term)),
        )
        if existing:
            db.run_sql(
                """
                UPDATE skor
                SET skor_top = ?, hesap_tarih = ?, donem = ?
                WHERE skor_id = ?
                """,
                (float(score), now, normalized_term, int(existing[0][0])),
            )
        else:
            db.run_sql(
                """
                INSERT INTO skor (ders_id, akademik_yil, donem, skor_top, hesap_tarih)
                VALUES (?, ?, ?, ?, ?)
                """,
                (int(ders_id), int(year), normalized_term, float(score), now),
            )


def ensure_report_scores(db, faculty_id: int, year: int, term: str) -> dict[str, Any]:
    conn = _conn_from_db(db)
    if conn is None:
        return {"ok": False, "reason": "db_connection_missing"}

    ensure_reporting_schema(conn)
    cur = conn.cursor()

    ensure_pool_visibility_for_curriculum(
        cur=cur,
        fakulte_id=int(faculty_id),
        akademik_yil=int(year),
        donem=normalize_term(term),
    )

    if is_yearly_workflow_enabled():
        status = get_faculty_year_status(
            conn=conn,
            fakulte_id=int(faculty_id),
            yil=int(year),
            refresh=True,
        )
        if str(status.get("algorithm_run_status") or "") != "ran":
            return {
                "ok": False,
                "reason": "algorithms_not_run",
                "status": status,
            }

    pack = get_faculty_year_topsis_results(
        cur=cur,
        fakulte_id=int(faculty_id),
        akademik_yil=int(year),
        donem=normalize_term(term),
        strict_ahp=True,
    )
    if not pack.get("ok"):
        return {"ok": False, "reason": pack.get("error", "score_generation_failed")}

    skor_map = {int(k): float(v) for k, v in dict(pack.get("scores") or {}).items()}
    if skor_map:
        persist_faculty_year_topsis_scores(
            cur=cur,
            fakulte_id=int(faculty_id),
            akademik_yil=int(year),
            skor_map=skor_map,
            ders_meta=dict(pack.get("ders_meta") or {}),
            donem=normalize_term(term),
        )
        conn.commit()
        _persist_score_source(db=db, year=int(year), term=normalize_term(term), score_map=skor_map)

    return {"ok": True, "score_count": len(skor_map)}


def fetch_curriculum_course_ids(db, faculty_id: int, year: int, term: str) -> set[int]:
    _, rows = db.run_sql(
        """
        SELECT DISTINCT md.ders_id
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE b.fakulte_id = ?
          AND m.akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
        """,
        (int(faculty_id), int(year), term_key(term)),
    )
    return {int(row[0]) for row in (rows or []) if row and row[0] is not None}


def _fetch_score_source_map(db, year: int, term: str) -> dict[int, float]:
    ensure_score_source_schema(db)
    _, rows = db.run_sql(
        """
        SELECT ders_id, skor_top
        FROM skor
        WHERE akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
        """,
        (int(year), term_key(term)),
    )
    return {
        int(ders_id): float(score)
        for ders_id, score in (rows or [])
        if ders_id is not None and score is not None
    }


def _fetch_pool_rows(db, faculty_id: int, year: int, term: str):
    conn = _conn_from_db(db)
    use_term = False
    elective_predicate = "0=1"
    if conn is not None:
        use_term = "donem" in _table_columns(conn, "havuz")
        try:
            elective_predicate = build_elective_predicate(cur=conn.cursor(), alias="d")
        except Exception:
            elective_predicate = "0=1"
        if elective_predicate == "0=1":
            elective_predicate = "1=1"

    if elective_predicate == "0=1":
        return []

    query = f"""
        SELECT
            CAST(h.ders_id AS INTEGER) AS ders_id,
            COALESCE(h.ders_adi, d.ad, 'Ders ' || h.ders_id) AS ders_adi,
            h.skor,
            h.sayac,
            h.statu,
            h.yil,
            COALESCE(h.donem, ?) AS donem
        FROM havuz h
        LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
        WHERE h.fakulte_id = ? AND h.yil = ?
          AND {elective_predicate}
    """
    params: list[Any] = [normalize_term(term), int(faculty_id), int(year)]
    if use_term:
        query += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
        params.append(term_key(term))

    query += " ORDER BY CASE WHEN h.skor IS NULL THEN 1 ELSE 0 END, h.skor DESC, h.statu DESC, ders_adi"
    _, rows = db.run_sql(query, tuple(params))
    return rows or []


def build_report_snapshot(
    db,
    faculty_id: int,
    faculty_name: str,
    year: int,
    term: str,
    department_name: str | None = None,
) -> dict[str, Any]:
    normalized_term = normalize_term(term)
    conn = _conn_from_db(db)
    elective_predicate = "0=1"
    department_id: int | None = None
    if conn is not None:
        try:
            elective_predicate = build_elective_predicate(cur=conn.cursor(), alias="d")
        except Exception:
            elective_predicate = "0=1"
        if elective_predicate == "0=1":
            elective_predicate = "1=1"
        if department_name:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT bolum_id
                    FROM bolum
                    WHERE fakulte_id = ? AND ad = ?
                    LIMIT 1
                    """,
                    (int(faculty_id), department_name),
                )
                row = cur.fetchone()
                department_id = int(row[0]) if row and row[0] is not None else None
            except Exception:
                department_id = None

    curriculum_ids = fetch_curriculum_course_ids(db, faculty_id, year, normalized_term)
    score_map = _fetch_score_source_map(db, year, normalized_term)
    pool_rows_raw = _fetch_pool_rows(db, faculty_id, year, normalized_term)

    pool_rows = []
    scores: list[float] = []
    rest_count = 0
    chosen_count = 0
    cancelled_count = 0

    for ders_id, ders_adi, skor, sayac, statu, row_year, row_term in pool_rows_raw:
        if ders_id is None:
            continue
        ders_id_int = int(ders_id)
        status = int(statu) if statu is not None else 0
        if status == -1:
            rest_count += 1
        elif status == 1:
            chosen_count += 1
        elif status == -2:
            cancelled_count += 1

        source_score = score_map.get(ders_id_int)
        score_value = source_score if source_score is not None else (float(skor) if skor is not None else None)
        if score_value is not None:
            scores.append(score_value)

        source = "TOPSIS" if ders_id_int in curriculum_ids else f"Anket ({POOL_DEFAULT_SCORE:.0f}+-{POOL_ANKET_SCORE_SPREAD:.0f})"
        pool_rows.append(
            {
                "ders_id": ders_id_int,
                "ders_adi": ders_adi,
                "skor": score_value,
                "sayac": int(sayac or 0),
                "statu": status_label(status),
                "yil": int(row_year),
                "kaynak": source,
                "donem": normalize_term(row_term),
            }
        )

    pool_rows.sort(
        key=lambda item: (
            item.get("skor") is None,
            -float(item.get("skor") or 0.0),
            str(item.get("ders_adi") or ""),
        )
    )

    curriculum_rows = []
    if conn is not None:
        department_filter = " AND b.ad = ?" if department_name else ""
        params: list[Any] = [int(faculty_id)]
        if department_name:
            params.append(department_name)
        params.extend([int(year), term_key(normalized_term)])
        _, curr_rows_raw = db.run_sql(
            f"""
            SELECT DISTINCT
                d.ders_id,
                d.ad,
                h.skor,
                m.donem,
                b.ad
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            JOIN ders d ON md.ders_id = d.ders_id
            JOIN bolum b ON m.bolum_id = b.bolum_id
            LEFT JOIN havuz h ON h.id = (
                SELECT h2.id
                FROM havuz h2
                WHERE CAST(h2.ders_id AS INTEGER) = d.ders_id
                  AND h2.yil = m.akademik_yil
                  AND LOWER(SUBSTR(TRIM(COALESCE(h2.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1))
                ORDER BY
                    CASE WHEN h2.skor IS NULL THEN 1 ELSE 0 END,
                    h2.skor DESC,
                    h2.id DESC
                LIMIT 1
            )
            WHERE b.fakulte_id = ?
              {department_filter}
              AND m.akademik_yil = ?
              AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
              AND {elective_predicate}
            ORDER BY
                CASE WHEN h.skor IS NULL THEN 1 ELSE 0 END,
                h.skor DESC,
                d.ad
            """,
            tuple(params),
        )
        curriculum_rows = [
            {
                "ders_id": int(ders_id),
                "ders_adi": ders_adi,
                "skor": score_map.get(int(ders_id), float(skor) if skor is not None else None),
                "kaynak": "TOPSIS",
                "donem": normalize_term(donem),
                "bolum": bolum_adi,
            }
            for ders_id, ders_adi, skor, donem, bolum_adi in (curr_rows_raw or [])
        ]

    avg_score = (sum(scores) / len(scores)) if scores else None
    criteria_import_summary = (
        summarize_report_criteria_scope(
            conn=conn,
            faculty_id=int(faculty_id),
            year=int(year),
            term=normalized_term,
            department_id=department_id,
        )
        if conn is not None
        else {"mode": "missing", "active_import": None, "display": "Aktif kriter dosyasi yok."}
    )
    try:
        active_ahp_summary = get_active_ahp_profile_summary(
            conn,
            year=int(year),
            faculty_id=int(faculty_id),
            department_id=department_id,
            semester=normalized_term,
        ) if conn is not None else {}
    except Exception:
        active_ahp_summary = {}

    notes = [
        f"Skor kaynaklari: mufredattaki dersler AHP+TOPSIS, mufredat disi dersler anket bazli {POOL_DEFAULT_SCORE:.0f}+-{POOL_ANKET_SCORE_SPREAD:.0f}.",
        f"Esikler: kesinlesme puani < {DROP_SCORE_THRESHOLD:.0f} veya ortalama not < {DROP_AVERAGE_GRADE_THRESHOLD:.0f}.",
        f"Rapor kapsami: Fakulte={faculty_name}, Yil={year}, Donem={normalized_term}" + (f", Bolum={department_name}" if department_name else ""),
        f"Kriter dosyasi: {criteria_import_summary.get('display')}",
    ]
    if active_ahp_summary:
        profile_info = active_ahp_summary.get("profile") or active_ahp_summary
        notes.append(
            "Aktif AHP profili: "
            f"#{profile_info.get('id')} "
            f"{profile_info.get('name') or profile_info.get('profile_name') or ''} "
            f"v{profile_info.get('version')}"
        )

    return {
        "pool_rows": pool_rows,
        "curriculum_rows": curriculum_rows,
        "criteria_import_summary": criteria_import_summary,
        "stats": {
            "total": len(pool_rows),
            "avg_score": avg_score,
            "rest_count": rest_count,
            "chosen_count": chosen_count,
            "cancelled_count": cancelled_count,
        },
        "notes": notes,
        "term": normalized_term,
    }


def get_import_history(conn: sqlite3.Connection, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    filters = filters or {}
    ensure_reporting_schema(conn)
    return list_import_batches(
        conn,
        import_type=filters.get("import_type"),
        status=filters.get("status"),
        year=filters.get("year"),
        faculty_id=filters.get("faculty_id"),
        department_id=filters.get("department_id"),
        limit=int(filters.get("limit") or 200),
    )


def get_import_quality_summary(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    return summarize_quality(conn, int(import_batch_id))


def get_import_diff_summary(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None:
    ensure_reporting_schema(conn)
    return get_import_diff(conn, int(import_batch_id))


def get_import_impact_summary(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None:
    ensure_reporting_schema(conn)
    return get_import_impact(conn, int(import_batch_id))


def export_import_issues(conn: sqlite3.Connection, import_batch_id: int) -> str:
    ensure_reporting_schema(conn)
    rows = list_import_issues(conn, int(import_batch_id), limit=100000)
    out = StringIO()
    fieldnames = [
        "row_number",
        "severity",
        "issue_type",
        "field_name",
        "raw_value",
        "message",
        "suggestion",
    ]
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return out.getvalue()


def export_import_audit_report(conn: sqlite3.Connection, import_batch_id: int, format: str = "csv") -> str:
    ensure_reporting_schema(conn)
    batch = get_import_batch(conn, int(import_batch_id)) or {}
    quality = summarize_quality(conn, int(import_batch_id))
    rows = list_import_rows(conn, int(import_batch_id), limit=100000)
    issues = list_import_issues(conn, int(import_batch_id), limit=100000)
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["Bolum", "Alan", "Deger"])
    for key in (
        "id",
        "import_type",
        "original_filename",
        "file_hash_sha256",
        "status",
        "quality_score",
        "quality_level",
        "year",
        "faculty_id",
        "department_id",
        "semester",
        "uploaded_at",
    ):
        writer.writerow(["Import", key, batch.get(key)])
    writer.writerow(["Kalite", "quality_score", quality.get("quality_score")])
    writer.writerow(["Kalite", "quality_level", quality.get("quality_level")])
    writer.writerow(["Ozet", "row_count", len(rows)])
    writer.writerow(["Ozet", "issue_count", len(issues)])
    return out.getvalue()


def get_criteria_completion_report(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    scope = "department" if department_id is not None else "faculty"
    summary = get_completion_summary(
        conn,
        scope_type=scope,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
        refresh=True,
    )
    return {
        "summary": {
            "scope_type": summary.get("scope_type"),
            "faculty_id": summary.get("faculty_id"),
            "department_id": summary.get("department_id"),
            "year": summary.get("year"),
            "semester": summary.get("semester"),
            "completion_ratio": summary.get("completion_ratio"),
            "completion_level": summary.get("completion_level"),
            "can_run_algorithm": summary.get("can_run_algorithm"),
            "blocking_reason": summary.get("blocking_reason"),
            "total_courses": summary.get("total_courses"),
            "completed_courses": summary.get("completed_courses"),
            "missing_courses": summary.get("missing_courses"),
            "invalid_courses": summary.get("invalid_courses"),
            "risk": summary.get("missing_data_risk"),
            "policy": summary.get("policy_name"),
        },
        "criterion_summary": summary.get("criterion_summary") or {},
    }


def get_criteria_completion_matrix_report(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    scope = "department" if department_id is not None else "faculty"
    return get_completion_matrix(
        conn,
        scope_type=scope,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
        refresh=True,
    )


def get_criteria_validation_report(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    scope = "department" if department_id is not None else "faculty"
    return get_validation_issues(
        conn,
        scope_type=scope,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
        refresh=True,
    )


def get_missing_data_risk_report(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any] | None:
    ensure_reporting_schema(conn)
    scope = "department" if department_id is not None else "faculty"
    report = _get_missing_data_risk_report(
        conn,
        scope_type=scope,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )
    if report:
        return report
    summary = get_completion_summary(
        conn,
        scope_type=scope,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
        refresh=True,
    )
    return summary.get("missing_data_risk")


def _csv_from_dicts(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return out.getvalue()


def export_criteria_completion_matrix(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    format: str = "csv",
) -> str:
    rows = get_criteria_completion_matrix_report(conn, year, faculty_id, department_id, semester)
    return _csv_from_dicts(
        rows,
        [
            "course_id",
            "course_code",
            "course_name",
            "criterion_key",
            "is_required",
            "is_present",
            "is_valid",
            "value_text",
            "missing_reason",
            "invalid_reason",
            "source_type",
        ],
    )


def export_validation_issues(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    format: str = "csv",
) -> str:
    rows = get_criteria_validation_report(conn, year, faculty_id, department_id, semester)
    return _csv_from_dicts(
        rows,
        ["course_id", "field_name", "criterion_key", "severity", "issue_type", "message", "suggestion"],
    )


def export_completion_tasks(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    status: str | None = None,
    format: str = "csv",
) -> str:
    ensure_reporting_schema(conn)
    rows = get_tasks(conn, year=year, faculty_id=faculty_id, department_id=department_id, status=status)
    return _csv_from_dicts(
        rows,
        [
            "id",
            "scope_type",
            "faculty_id",
            "department_id",
            "course_id",
            "year",
            "semester",
            "assigned_to",
            "assigned_role",
            "due_date",
            "status",
            "priority",
            "notes",
        ],
    )


def get_pool_lifecycle_summary(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    return _get_pool_lifecycle_summary(
        conn,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )


def get_course_state_history(conn: sqlite3.Connection, course_id: int) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    return _get_course_state_history(conn, int(course_id))


def get_pending_approvals(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    return _list_pool_pending_approvals(
        conn,
        year=year,
        faculty_id=faculty_id,
        department_id=department_id,
        status="pending",
    )


def get_reactivation_candidates(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    return _get_reactivation_candidates(conn, year=year, faculty_id=faculty_id, department_id=department_id)


def get_protected_courses(
    conn: sqlite3.Connection,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    return _get_protected_courses(conn, faculty_id=faculty_id, department_id=department_id)


def export_pool_lifecycle_report(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    format: str = "csv",
) -> str:
    ensure_reporting_schema(conn)
    rows = _list_state_transitions(
        conn,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        limit=100000,
    )
    return _csv_from_dicts(
        rows,
        [
            "id",
            "course_id",
            "course_code",
            "course_name",
            "year",
            "semester",
            "old_status",
            "recommended_status",
            "final_status",
            "lifecycle_label",
            "rule_applied",
            "topsis_score",
            "trend_label",
            "data_confidence_score",
            "approval_required",
            "approval_status",
            "explanation",
            "created_at",
        ],
    )


def export_state_transition_history(
    conn: sqlite3.Connection,
    course_id: int | None = None,
    year: int | None = None,
    format: str = "csv",
) -> str:
    ensure_reporting_schema(conn)
    rows = (
        _get_course_state_history(conn, int(course_id))
        if course_id is not None
        else _list_state_transitions(conn, year=year, limit=100000)
    )
    return _csv_from_dicts(
        rows,
        [
            "id",
            "course_id",
            "year",
            "semester",
            "old_status",
            "recommended_status",
            "final_status",
            "lifecycle_label",
            "trigger",
            "rule_applied",
            "approval_status",
            "override_applied",
            "explanation",
            "created_at",
        ],
    )


def get_ahp_profile_report(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    from app.services.ahp_reporting_service import get_ahp_profile_report as _report

    return _report(conn, int(profile_id))


def get_active_ahp_profile_summary(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    from app.services.ahp_reporting_service import (
        get_active_ahp_profile_summary as _summary,
    )

    return _summary(conn, year=year, faculty_id=faculty_id, department_id=department_id, semester=semester)


def get_decision_run_ahp_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    from app.services.ahp_reporting_service import (
        get_decision_run_ahp_summary as _summary,
    )

    return _summary(conn, int(run_id))


def export_ahp_profile_matrix(conn: sqlite3.Connection, profile_id: int, format: str = "csv") -> str:
    ensure_reporting_schema(conn)
    from app.services.ahp_reporting_service import export_ahp_profile_matrix as _export

    return _export(conn, int(profile_id), format=format)


def export_ahp_sensitivity_report(conn: sqlite3.Connection, run_id: int, format: str = "csv") -> str:
    ensure_reporting_schema(conn)
    from app.services.ahp_reporting_service import (
        export_ahp_sensitivity_report as _export,
    )

    return _export(conn, int(run_id), format=format)


def compare_ahp_profiles(conn: sqlite3.Connection, profile_a_id: int, profile_b_id: int) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    from app.services.ahp_reporting_service import compare_ahp_profiles as _compare

    return _compare(conn, int(profile_a_id), int(profile_b_id))


def get_semester_plan_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        get_semester_plan_summary as _summary,
    )

    return _summary(conn, int(run_id))


def get_semester_plan_assignments(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        get_semester_plan_assignments as _assignments,
    )

    return _assignments(conn, int(run_id))


def get_semester_plan_constraint_violations(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        get_constraint_violations as _violations,
    )

    return _violations(conn, int(run_id))


def compare_semester_plan_scenarios(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        compare_plan_scenarios as _scenarios,
    )

    return _scenarios(conn, int(run_id))


def export_semester_plan(conn: sqlite3.Connection, run_id: int, format: str = "csv") -> str:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        export_semester_plan as _export,
    )

    return _export(conn, int(run_id), format=format)


def export_semester_plan_constraint_violations(conn: sqlite3.Connection, run_id: int, format: str = "csv") -> str:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        export_constraint_violations as _export,
    )

    return _export(conn, int(run_id), format=format)


def generate_human_readable_semester_plan_report(conn: sqlite3.Connection, run_id: int) -> str:
    ensure_reporting_schema(conn)
    from app.services.semester_planning_reporting_service import (
        generate_human_readable_plan_report as _report,
    )

    return _report(conn, int(run_id))

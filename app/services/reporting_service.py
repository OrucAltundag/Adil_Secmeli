from __future__ import annotations

from datetime import datetime
import sqlite3
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

    pack = get_faculty_year_topsis_results(
        cur=cur,
        fakulte_id=int(faculty_id),
        akademik_yil=int(year),
        donem=normalize_term(term),
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
    if conn is not None:
        use_term = "donem" in _table_columns(conn, "havuz")

    query = """
        SELECT
            CAST(h.ders_id AS INTEGER) AS ders_id,
            COALESCE(h.ders_adi, d.ad, 'Ders ' || h.ders_id) AS ders_adi,
            h.skor,
            h.sayac,
            h.statu,
            h.yil
        FROM havuz h
        LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
        WHERE h.fakulte_id = ? AND h.yil = ?
    """
    params: list[Any] = [int(faculty_id), int(year)]
    if use_term:
        query += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
        params.append(term_key(term))

    query += " ORDER BY h.statu DESC, CASE WHEN h.skor IS NULL THEN 1 ELSE 0 END, h.skor DESC, ders_adi"
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
    curriculum_ids = fetch_curriculum_course_ids(db, faculty_id, year, normalized_term)
    score_map = _fetch_score_source_map(db, year, normalized_term)
    pool_rows_raw = _fetch_pool_rows(db, faculty_id, year, normalized_term)

    pool_rows = []
    scores: list[float] = []
    rest_count = 0
    chosen_count = 0
    cancelled_count = 0

    for ders_id, ders_adi, skor, sayac, statu, row_year in pool_rows_raw:
        status = int(statu) if statu is not None else 0
        if status == -1:
            rest_count += 1
        elif status == 1:
            chosen_count += 1
        elif status == -2:
            cancelled_count += 1

        source_score = score_map.get(int(ders_id)) if ders_id is not None else None
        score_value = source_score if source_score is not None else (float(skor) if skor is not None else None)
        if score_value is not None:
            scores.append(score_value)

        source = "TOPSIS" if int(ders_id) in curriculum_ids else f"Anket ({POOL_DEFAULT_SCORE:.0f}+-{POOL_ANKET_SCORE_SPREAD:.0f})"
        pool_rows.append(
            {
                "ders_id": int(ders_id),
                "ders_adi": ders_adi,
                "skor": score_value,
                "sayac": int(sayac or 0),
                "statu": status_label(status),
                "yil": int(row_year),
                "kaynak": source,
            }
        )

    curriculum_rows = []
    if department_name:
        _, curr_rows_raw = db.run_sql(
            """
            SELECT DISTINCT
                d.ders_id,
                d.ad,
                h.skor
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            JOIN ders d ON md.ders_id = d.ders_id
            JOIN bolum b ON m.bolum_id = b.bolum_id
            LEFT JOIN havuz h ON (
                CAST(h.ders_id AS INTEGER) = d.ders_id
                AND h.yil = m.akademik_yil
                AND h.fakulte_id = b.fakulte_id
            )
            WHERE b.fakulte_id = ?
              AND b.ad = ?
              AND m.akademik_yil = ?
              AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
            ORDER BY d.ad
            """,
            (int(faculty_id), department_name, int(year), term_key(normalized_term)),
        )
        curriculum_rows = [
            {
                "ders_id": int(ders_id),
                "ders_adi": ders_adi,
                "skor": score_map.get(int(ders_id), float(skor) if skor is not None else None),
                "kaynak": "TOPSIS",
            }
            for ders_id, ders_adi, skor in (curr_rows_raw or [])
        ]

    avg_score = round(sum(scores) / len(scores), 2) if scores else None
    notes = [
        f"Skor kaynaklari: mufredattaki dersler AHP+TOPSIS, mufredat disi dersler anket bazli {POOL_DEFAULT_SCORE:.0f}+-{POOL_ANKET_SCORE_SPREAD:.0f}.",
        f"Esikler: kesinlesme puani < {DROP_SCORE_THRESHOLD:.0f} veya ortalama not < {DROP_AVERAGE_GRADE_THRESHOLD:.0f}.",
        f"Rapor kapsami: Fakulte={faculty_name}, Yil={year}, Donem={normalized_term}" + (f", Bolum={department_name}" if department_name else ""),
    ]

    return {
        "pool_rows": pool_rows,
        "curriculum_rows": curriculum_rows,
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

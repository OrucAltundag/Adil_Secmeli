# -*- coding: utf-8 -*-
"""Geçici karar çalıştırmalarından onaylanabilir yıllık müfredat önizlemesi üretir."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.repositories.curriculum_repository import save_period_planning_result


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_review_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS curriculum_decision_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_year INTEGER NOT NULL,
            target_year INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            department_id INTEGER NOT NULL,
            fall_run_id INTEGER,
            spring_run_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            reviewed_by TEXT,
            reviewed_at TEXT,
            review_note TEXT,
            CHECK(status IN ('pending','approved','rejected'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_curriculum_review_scope "
        "ON curriculum_decision_reviews(source_year, faculty_id, department_id, status, id)"
    )


def _row_dict(cur: sqlite3.Cursor, row: sqlite3.Row | tuple | None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return {str(col[0]): row[index] for index, col in enumerate(cur.description or [])}


def _decode_review(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    result = dict(row)
    try:
        result["payload"] = json.loads(result.get("payload_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        result["payload"] = {}
    return result


def _latest_run(
    cur: sqlite3.Cursor,
    *,
    source_year: int,
    faculty_id: int,
    department_id: int,
    semester: str,
) -> int | None:
    cur.execute(
        """
        SELECT id
        FROM decision_runs
        WHERE year=? AND faculty_id=? AND LOWER(COALESCE(semester,'')) LIKE ?
          AND status='completed'
          AND (department_id=? OR department_id IS NULL)
        ORDER BY CASE WHEN department_id=? THEN 0 ELSE 1 END, id DESC
        LIMIT 1
        """,
        (
            int(source_year),
            int(faculty_id),
            "b%" if str(semester).lower().startswith("b") else "g%",
            int(department_id),
            int(department_id),
        ),
    )
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def _term_curriculum(cur: sqlite3.Cursor, year: int, faculty_id: int, department_id: int, semester: str) -> list[dict[str, Any]]:
    prefix = "b%" if str(semester).lower().startswith("b") else "g%"
    cur.execute(
        """
        SELECT DISTINCT d.ders_id, COALESCE(d.kod,''), COALESCE(d.ad,'')
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id=m.mufredat_id
        JOIN ders d ON d.ders_id=md.ders_id
        WHERE m.akademik_yil=? AND m.fakulte_id=? AND m.bolum_id=?
          AND LOWER(COALESCE(m.donem,'')) LIKE ?
        ORDER BY d.ad, d.ders_id
        """,
        (int(year), int(faculty_id), int(department_id), prefix),
    )
    return [
        {"course_id": int(row[0]), "course_code": str(row[1] or ""), "course_name": str(row[2] or "")}
        for row in cur.fetchall()
    ]


def _decisions(cur: sqlite3.Cursor, run_id: int | None, department_id: int) -> dict[int, dict[str, Any]]:
    if run_id is None:
        return {}
    cur.execute(
        """
        SELECT course_id, final_status, topsis_score, main_reason
        FROM course_decisions
        WHERE decision_run_id=? AND department_id=?
        """,
        (int(run_id), int(department_id)),
    )
    return {
        int(row[0]): {
            "final_status": row[1],
            "score": row[2],
            "reason": str(row[3] or ""),
        }
        for row in cur.fetchall()
    }


def _score_columns(cur: sqlite3.Cursor) -> set[str]:
    try:
        cur.execute("PRAGMA table_info(skor)")
        return {str(row[1]) for row in cur.fetchall()}
    except sqlite3.OperationalError:
        return set()


def _finalized_scores(cur: sqlite3.Cursor, course_ids: list[int], source_year: int) -> dict[int, float]:
    columns = _score_columns(cur)
    if not course_ids or not columns:
        return {}
    value_col = "skor_top" if "skor_top" in columns else "skor" if "skor" in columns else None
    year_col = "akademik_yil" if "akademik_yil" in columns else "yil" if "yil" in columns else None
    if value_col is None or year_col is None:
        return {}
    placeholders = ",".join("?" for _ in course_ids)
    cur.execute(
        f"SELECT ders_id, {year_col}, {value_col} FROM skor "
        f"WHERE CAST(ders_id AS INTEGER) IN ({placeholders}) AND {year_col}<=? "
        f"AND {value_col} IS NOT NULL ORDER BY {year_col} DESC",
        tuple(course_ids) + (int(source_year),),
    )
    scores: dict[int, float] = {}
    for course_id, _year, value in cur.fetchall():
        cid = int(course_id)
        if cid not in scores:
            scores[cid] = float(value)
    return scores


def _candidates(cur: sqlite3.Cursor, run_id: int | None, department_id: int, source_year: int) -> list[dict[str, Any]]:
    if run_id is None:
        return []
    try:
        cur.execute(
            """
            SELECT r.course_id, COALESCE(d.kod,''), COALESCE(d.ad,''), r.rank,
                   r.net_flow, COALESCE(r.reason,'')
            FROM candidate_course_recommendations r
            JOIN ders d ON d.ders_id=r.course_id
            WHERE r.decision_run_id=? AND d.bolum_id=?
            ORDER BY r.rank, r.id
            LIMIT 7
            """,
            (int(run_id), int(department_id)),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        return []
    ids = [int(row[0]) for row in rows]
    finalized = _finalized_scores(cur, ids, int(source_year))
    result = []
    for row in rows:
        cid = int(row[0])
        net_flow = float(row[4] or 0.0)
        score = finalized.get(cid, max(0.0, min(100.0, (net_flow + 1.0) * 50.0)))
        result.append(
            {
                "course_id": cid,
                "course_code": str(row[1] or ""),
                "course_name": str(row[2] or ""),
                "rank": int(row[3] or 0),
                "score": float(score),
                "score_source": "kesinlesme" if cid in finalized else "promethee_ii",
                "reason": str(row[5] or ""),
            }
        )
    return sorted(result, key=lambda item: (-float(item["score"]), int(item["rank"])))


def _build_term(
    current: list[dict[str, Any]],
    decisions: dict[int, dict[str, Any]],
    candidates: list[dict[str, Any]],
    globally_used: set[int],
) -> dict[str, Any]:
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for course in current:
        decision = decisions.get(int(course["course_id"]))
        # Karar satırı yoksa güvenli varsayım: mevcut dersi koru.
        if decision is None or int(decision.get("final_status") or 0) == 1:
            kept.append(
                {
                    **course,
                    "score": None if decision is None else decision.get("score"),
                    "origin": "mevcut",
                    "reason": "Karar verisi yok; mevcut ders korundu." if decision is None else decision.get("reason"),
                }
            )
            globally_used.add(int(course["course_id"]))
        else:
            dropped.append({**course, **decision, "origin": "dusen"})

    available = [item for item in candidates if int(item["course_id"]) not in globally_used]
    replacements: list[dict[str, Any]] = []
    for _dropped in dropped:
        if not available:
            break
        candidate = dict(available.pop(0))
        candidate["origin"] = "otomatik_yedek"
        replacements.append(candidate)
        globally_used.add(int(candidate["course_id"]))
    return {
        "items": kept + replacements,
        "dropped": dropped,
        "candidates": candidates,
        "replacement_shortage": max(0, len(dropped) - len(replacements)),
    }


def get_review(conn: sqlite3.Connection, review_id: int) -> dict[str, Any] | None:
    ensure_review_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM curriculum_decision_reviews WHERE id=?", (int(review_id),))
    return _decode_review(_row_dict(cur, cur.fetchone()))


def get_latest_review(conn: sqlite3.Connection, source_year: int, faculty_id: int, department_id: int) -> dict[str, Any] | None:
    ensure_review_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM curriculum_decision_reviews
        WHERE source_year=? AND faculty_id=? AND department_id=?
        ORDER BY id DESC LIMIT 1
        """,
        (int(source_year), int(faculty_id), int(department_id)),
    )
    return _decode_review(_row_dict(cur, cur.fetchone()))


def build_curriculum_review(conn: sqlite3.Connection, source_year: int, faculty_id: int, department_id: int) -> dict[str, Any]:
    """Güz+Bahar kararlarından hedef yıl için onay bekleyen nihai önizleme oluştur."""

    ensure_review_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    fall_run = _latest_run(cur, source_year=source_year, faculty_id=faculty_id, department_id=department_id, semester="Guz")
    spring_run = _latest_run(cur, source_year=source_year, faculty_id=faculty_id, department_id=department_id, semester="Bahar")
    if fall_run is None and spring_run is None:
        raise ValueError("Bu kapsam için tamamlanmış Güz/Bahar geçici karar çalıştırması bulunamadı.")

    latest = get_latest_review(conn, source_year, faculty_id, department_id)
    if (
        latest
        and latest.get("status") == "pending"
        and latest.get("fall_run_id") == fall_run
        and latest.get("spring_run_id") == spring_run
    ):
        return latest

    used: set[int] = set()
    fall_current = _term_curriculum(cur, source_year, faculty_id, department_id, "Guz")
    spring_current = _term_curriculum(cur, source_year, faculty_id, department_id, "Bahar")
    fall = _build_term(
        fall_current,
        _decisions(cur, fall_run, department_id),
        _candidates(cur, fall_run, department_id, source_year),
        used,
    )
    spring = _build_term(
        spring_current,
        _decisions(cur, spring_run, department_id),
        _candidates(cur, spring_run, department_id, source_year),
        used,
    )
    payload = {
        "source_year": int(source_year),
        "target_year": int(source_year) + 1,
        "faculty_id": int(faculty_id),
        "department_id": int(department_id),
        "fall": fall,
        "spring": spring,
    }
    now = _now()
    cur.execute(
        """
        INSERT INTO curriculum_decision_reviews (
            source_year, target_year, faculty_id, department_id, fall_run_id,
            spring_run_id, status, payload_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            int(source_year), int(source_year) + 1, int(faculty_id), int(department_id),
            fall_run, spring_run, json.dumps(payload, ensure_ascii=False, sort_keys=True), now, now,
        ),
    )
    return get_review(conn, int(cur.lastrowid or 0)) or {}


def replace_review_course(
    conn: sqlite3.Connection,
    review_id: int,
    *,
    semester: str,
    outgoing_course_id: int,
    incoming_course_id: int,
) -> dict[str, Any]:
    """Yalnız önizleme JSON'unu değiştirir; havuz statüsü/sayacı veya müfredat yazılmaz."""

    review = get_review(conn, review_id)
    if not review or review.get("status") != "pending":
        raise ValueError("Yalnız onay bekleyen müfredat önizlemesi değiştirilebilir.")
    term_key = "spring" if str(semester).lower().startswith("b") else "fall"
    payload = dict(review.get("payload") or {})
    term = dict(payload.get(term_key) or {})
    items = [dict(item) for item in term.get("items") or []]
    candidates = [dict(item) for item in term.get("candidates") or []]
    outgoing_index = next((i for i, item in enumerate(items) if int(item["course_id"]) == int(outgoing_course_id)), None)
    incoming = next((item for item in candidates if int(item["course_id"]) == int(incoming_course_id)), None)
    if outgoing_index is None:
        raise ValueError("Değiştirilecek ders önizlemede bulunamadı.")
    if incoming is None:
        raise ValueError("Yeni ders PROMETHEE II Top-7 aday listesinde bulunamadı.")
    all_ids = {
        int(item["course_id"])
        for key in ("fall", "spring")
        for item in (payload.get(key) or {}).get("items", [])
    }
    if int(incoming_course_id) in all_ids and int(incoming_course_id) != int(outgoing_course_id):
        raise ValueError("Seçilen aday yıllık önizlemede zaten bulunuyor.")
    incoming = {**incoming, "origin": "manuel_takas", "replaced_course_id": int(outgoing_course_id)}
    items[outgoing_index] = incoming
    term["items"] = items
    payload[term_key] = term
    conn.execute(
        "UPDATE curriculum_decision_reviews SET payload_json=?, updated_at=? WHERE id=? AND status='pending'",
        (json.dumps(payload, ensure_ascii=False, sort_keys=True), _now(), int(review_id)),
    )
    return get_review(conn, review_id) or {}


def approve_curriculum_review(
    conn: sqlite3.Connection,
    review_id: int,
    *,
    reviewed_by: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    review = get_review(conn, review_id)
    if not review or review.get("status") != "pending":
        raise ValueError("Yalnız onay bekleyen müfredat kararı onaylanabilir.")
    payload = dict(review.get("payload") or {})
    fall_ids = [int(item["course_id"]) for item in (payload.get("fall") or {}).get("items", [])]
    spring_ids = [int(item["course_id"]) for item in (payload.get("spring") or {}).get("items", [])]
    outcome = save_period_planning_result(
        conn,
        int(review["target_year"]),
        faculty_id=int(review["faculty_id"]),
        department_id=int(review["department_id"]),
        fall_course_ids=fall_ids,
        spring_course_ids=spring_ids,
    )
    conn.execute(
        """
        UPDATE curriculum_decision_reviews
        SET status='approved', reviewed_by=?, reviewed_at=?, review_note=?, updated_at=?
        WHERE id=? AND status='pending'
        """,
        (reviewed_by, _now(), review_note, _now(), int(review_id)),
    )
    result = get_review(conn, review_id) or {}
    result["write_outcome"] = outcome
    return result


def reject_curriculum_review(
    conn: sqlite3.Connection,
    review_id: int,
    *,
    reviewed_by: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    review = get_review(conn, review_id)
    if not review or review.get("status") != "pending":
        raise ValueError("Yalnız onay bekleyen müfredat kararı reddedilebilir.")
    conn.execute(
        """
        UPDATE curriculum_decision_reviews
        SET status='rejected', reviewed_by=?, reviewed_at=?, review_note=?, updated_at=?
        WHERE id=? AND status='pending'
        """,
        (reviewed_by, _now(), review_note, _now(), int(review_id)),
    )
    return get_review(conn, review_id) or {}

# -*- coding: utf-8 -*-
"""
Dual-semester curriculum rebuild engine.

Bu modul:
- GÃ¼z + Bahar uretimini ayni pipeline'da calistirir
- 8 derslik yillik kapasiteyi 4+4 bloklara dengeler
- Cross-semester cakismalari (bir dersin iki donemde birden secilmesi) engeller
- Donem-aware havuz statu/sayac guncellemesini uygular
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from app.core.config import resolve_sqlite_db_path
from app.services.course_type import build_elective_predicate
from app.services.db import get_raw_connection
from app.services.havuz_karar import (
    DONEM_BAHAR,
    DONEM_GUZ,
    calculate_next_status_semester,
    normalize_semester,
)
from app.services.semester_planning_engine import generate_semester_plan
from app.services.semester_planning_policy_service import resolve_policy

SEMESTER_ORDER = [DONEM_GUZ, DONEM_BAHAR]


@dataclass
class RebalanceResult:
    faculty_id: int
    year: int
    departments_processed: int
    conflicts_removed: int


def _term_token(term: str) -> str:
    normalized = normalize_semester(term)
    return "g" if normalized == DONEM_GUZ else "b"


def _havuz_has_donem(cur: sqlite3.Cursor) -> bool:
    cur.execute("PRAGMA table_info(havuz)")
    return "donem" in {str(row[1]) for row in cur.fetchall()}


def _fetch_or_create_curriculum_id(
    cur: sqlite3.Cursor,
    faculty_id: int,
    department_id: int,
    year: int,
    term: str,
) -> int:
    cur.execute(
        """
        SELECT mufredat_id
        FROM mufredat
        WHERE fakulte_id = ?
          AND bolum_id = ?
          AND akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
        ORDER BY COALESCE(versiyon, 0) DESC, mufredat_id DESC
        LIMIT 1
        """,
        (int(faculty_id), int(department_id), int(year), _term_token(term)),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])

    cur.execute(
        "SELECT COALESCE(MAX(versiyon), 0) FROM mufredat WHERE bolum_id = ?",
        (int(department_id),),
    )
    version = int((cur.fetchone() or [0])[0] or 0) + 1
    cur.execute(
        """
        INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon)
        VALUES (?, ?, ?, ?, 'Otomatik-Dual', ?)
        """,
        (int(faculty_id), int(department_id), int(year), normalize_semester(term), version),
    )
    return int(cur.lastrowid or 0)


def _fetch_curriculum_courses(
    cur: sqlite3.Cursor,
    department_id: int,
    year: int,
    term: str,
) -> list[int]:
    cur.execute(
        """
        SELECT DISTINCT md.ders_id
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE m.bolum_id = ?
          AND m.akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
        ORDER BY md.ders_id
        """,
        (int(department_id), int(year), _term_token(term)),
    )
    return [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]


def _fetch_candidate_courses(cur: sqlite3.Cursor, faculty_id: int, department_id: int) -> list[int]:
    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    if elective_predicate == "0=1":
        return []

    cur.execute(
        f"""
        SELECT DISTINCT d.ders_id
        FROM ders d
        LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
        WHERE (d.fakulte_id = ? OR b.fakulte_id = ?)
          AND {elective_predicate}
        ORDER BY CASE WHEN d.bolum_id = ? THEN 0 ELSE 1 END, d.ders_id
        """,
        (int(faculty_id), int(faculty_id), int(department_id)),
    )
    return [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]

def _scores_for_term(
    cur: sqlite3.Cursor,
    faculty_id: int,
    year: int,
    term: str,
    include_ids: list[int],
) -> dict[int, float]:
    from app.services.calculation import get_faculty_year_topsis_results

    pack = get_faculty_year_topsis_results(
        cur=cur,
        fakulte_id=int(faculty_id),
        akademik_yil=int(year),
        donem=normalize_semester(term),
        include_course_ids=include_ids,
    )
    if not pack.get("ok"):
        return {}
    return {int(k): float(v) for k, v in (pack.get("scores") or {}).items()}


def _sort_by_score(courses: list[int], score_map: dict[int, float]) -> list[int]:
    return sorted(
        [int(d) for d in courses],
        key=lambda d: (float(score_map.get(int(d), 0.0)), -int(d)),
        reverse=True,
    )


def _fill_block(
    current: list[int],
    ranking: list[int],
    blocked: set[int],
    block_size: int,
) -> list[int]:
    selected = list(dict.fromkeys(int(d) for d in current))
    for ders_id in ranking:
        if len(selected) >= int(block_size):
            break
        d_id = int(ders_id)
        if d_id in blocked or d_id in selected:
            continue
        selected.append(d_id)
    return selected[: int(block_size)]


def _rebalance_department(
    cur: sqlite3.Cursor,
    faculty_id: int,
    department_id: int,
    year: int,
    block_size: int = 4,
) -> tuple[dict[str, list[int]], int]:
    candidates = _fetch_candidate_courses(cur, faculty_id, department_id)
    if not candidates:
        return {
            DONEM_GUZ: _fetch_curriculum_courses(cur, department_id, year, DONEM_GUZ),
            DONEM_BAHAR: _fetch_curriculum_courses(cur, department_id, year, DONEM_BAHAR),
        }, 0

    scores_g = _scores_for_term(cur, faculty_id, year, DONEM_GUZ, candidates)
    scores_b = _scores_for_term(cur, faculty_id, year, DONEM_BAHAR, candidates)
    candidate_payload = []
    for ders_id in candidates:
        candidate_payload.append(
            {
                "course_id": int(ders_id),
                "score": max(float(scores_g.get(int(ders_id), 0.0)), float(scores_b.get(int(ders_id), 0.0))),
            }
        )

    policy = resolve_policy(
        cur.connection,
        year=int(year),
        faculty_id=int(faculty_id),
        department_id=int(department_id),
        curriculum_year=int(year),
    )
    # Eski block_size parametresi imza uyumlulugu icin korunur. Varsayilan
    # 4+4 artik policy'den gelir; farkli block_size veren legacy cagrilar
    # kapsamli policy yoksa ayni sonucu alabilsin diye runtime override edilir.
    if int(block_size) != 4 and policy.get("scope_type") == "global" and policy.get("name", "").startswith("Varsayılan"):
        policy = dict(policy)
        policy.update(
            {
                "total_elective_target": int(block_size) * 2,
                "fall_min": int(block_size),
                "fall_max": int(block_size),
                "spring_min": int(block_size),
                "spring_max": int(block_size),
            }
        )

    result = generate_semester_plan(
        cur.connection,
        year=int(year),
        faculty_id=int(faculty_id),
        department_id=int(department_id),
        candidate_courses=candidate_payload,
        policy=policy,
        curriculum_year=int(year),
        persist=True,
        run_name=f"Dual dönem planı {department_id}-{year}",
        generate_alternatives=True,
    )
    out = {
        DONEM_GUZ: [int(d) for d in result.get("fall_course_ids", [])],
        DONEM_BAHAR: [int(d) for d in result.get("spring_course_ids", [])],
    }
    conflicts_removed = len([v for v in result.get("constraint_violations", []) if v.get("constraint_type") == "repeat"])
    return out, conflicts_removed


def _persist_department_curricula(
    cur: sqlite3.Cursor,
    faculty_id: int,
    department_id: int,
    year: int,
    assignments: dict[str, list[int]],
) -> None:
    for term in SEMESTER_ORDER:
        mufredat_id = _fetch_or_create_curriculum_id(
            cur=cur,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            term=term,
        )
        cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (int(mufredat_id),))
        for ders_id in assignments.get(term, []):
            cur.execute(
                "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
                (int(mufredat_id), int(ders_id)),
            )


def _sync_havuz_dual_semester_state(
    cur: sqlite3.Cursor,
    faculty_id: int,
    year: int,
) -> int:
    if not _havuz_has_donem(cur):
        return 0

    term_selected: dict[str, set[int]] = {DONEM_GUZ: set(), DONEM_BAHAR: set()}
    cur.execute(
        """
        SELECT DISTINCT md.ders_id, m.donem
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE b.fakulte_id = ?
          AND m.akademik_yil = ?
        """,
        (int(faculty_id), int(year)),
    )
    for ders_id, term in cur.fetchall():
        if ders_id is None:
            continue
        term_selected[normalize_semester(term)].add(int(ders_id))

    all_selected = set(term_selected[DONEM_GUZ]) | set(term_selected[DONEM_BAHAR])
    prev_year = int(year) - 1

    cur.execute(
        """
        SELECT d.ders_id, d.bolum_id, d.ad
        FROM ders d
        LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
        WHERE d.fakulte_id = ? OR b.fakulte_id = ?
        """,
        (int(faculty_id), int(faculty_id)),
    )
    ders_meta = {
        int(r[0]): {
            "bolum_id": int(r[1]) if r[1] is not None else None,
            "ad": str(r[2] or ""),
        }
        for r in cur.fetchall()
        if r and r[0] is not None
    }

    course_ids = set(ders_meta.keys()) | all_selected
    updates = 0
    for term in SEMESTER_ORDER:
        token = normalize_semester(term)
        other = DONEM_BAHAR if token == DONEM_GUZ else DONEM_GUZ

        cur.execute(
            """
            SELECT CAST(ders_id AS INTEGER), statu, sayac
            FROM havuz
            WHERE fakulte_id = ? AND yil = ? AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
            """,
            (int(faculty_id), int(prev_year), _term_token(token)),
        )
        prev_map = {
            int(r[0]): (int(r[1] or 0), int(r[2] or 0))
            for r in cur.fetchall()
            if r and r[0] is not None
        }

        for ders_id in sorted(course_ids):
            prev_statu, prev_sayac = prev_map.get(int(ders_id), (0, 0))
            selected_current = int(ders_id) in term_selected[token]
            selected_other = int(ders_id) in term_selected[other]
            new_statu, new_sayac = calculate_next_status_semester(
                prev_statu=prev_statu,
                prev_sayac=prev_sayac,
                selected_in_current_semester=selected_current,
                selected_in_other_semester=selected_other,
            )

            meta = ders_meta.get(int(ders_id), {})
            bolum_id = meta.get("bolum_id")
            ders_adi = meta.get("ad", str(ders_id))

            cur.execute(
                """
                UPDATE havuz
                SET bolum_id = COALESCE(?, bolum_id),
                    ders_adi = CASE WHEN ? <> '' THEN ? ELSE ders_adi END,
                    statu = ?,
                    sayac = ?
                WHERE ders_id = ?
                  AND fakulte_id = ?
                  AND yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
                """,
                (
                    bolum_id,
                    ders_adi,
                    ders_adi,
                    int(new_statu),
                    int(new_sayac),
                    str(int(ders_id)),
                    int(faculty_id),
                    int(year),
                    _term_token(token),
                ),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        str(int(ders_id)),
                        int(year),
                        int(faculty_id),
                        bolum_id,
                        token,
                        int(new_statu),
                        int(new_sayac),
                        ders_adi,
                    ),
                )
            updates += 1

    return updates


def rebuild_school_curricula_dual_semester(
    db_path: str | None = None,
    base_year: int = 2022,
    max_rounds: int = 8,
    block_size: int = 4,
) -> dict[str, Any]:
    """
    Tum okul icin dual-semester (Guz+Bahar) rebuild.

    Akis:
    1) base_year sonrasi mufredati sifirla
    2) Guz ve Bahar pipeline'ini ayrica Ã¼ret
    3) Her faculty+year icin 4+4 blok dengesini enforce et
    4) Donem-aware havuz statu/sayac senkronizasyonu uygula
    """
    from app.services.calculation import (
        generate_curricula_until_stable,
        reset_future_curricula,
    )

    resolved_db_path = resolve_sqlite_db_path(db_path)
    if not resolved_db_path.exists():
        return {"ok": False, "error": f"DB bulunamadi: {resolved_db_path}"}
    db_path = str(resolved_db_path)

    reset = reset_future_curricula(db_path=db_path, base_year=int(base_year))
    if not reset.get("ok"):
        return {"ok": False, "reset": reset}

    generation_g = generate_curricula_until_stable(
        db_path=db_path,
        donem="G",
        max_rounds=int(max_rounds),
    )
    generation_b = generate_curricula_until_stable(
        db_path=db_path,
        donem="B",
        max_rounds=int(max_rounds),
    )

    generated_pairs = {
        (int(item.get("fakulte_id")), int(item.get("year_to")))
        for item in (generation_g.get("generated", []) + generation_b.get("generated", []))
        if item.get("fakulte_id") is not None and item.get("year_to") is not None
    }

    conn = get_raw_connection(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        if not generated_pairs:
            cur.execute(
                """
                SELECT DISTINCT m.fakulte_id, m.akademik_yil
                FROM mufredat m
                WHERE m.akademik_yil > ?
                """,
                (int(base_year),),
            )
            generated_pairs = {(int(r[0]), int(r[1])) for r in cur.fetchall() if r[0] is not None and r[1] is not None}

        rebalanced: list[dict[str, Any]] = []
        total_conflicts_removed = 0
        total_havuz_updates = 0
        for faculty_id, year in sorted(generated_pairs):
            cur.execute(
                "SELECT bolum_id FROM bolum WHERE fakulte_id = ? ORDER BY bolum_id",
                (int(faculty_id),),
            )
            departments = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]
            dept_processed = 0
            conflicts_removed = 0
            for bolum_id in departments:
                assignment, conflict_count = _rebalance_department(
                    cur=cur,
                    faculty_id=faculty_id,
                    department_id=bolum_id,
                    year=year,
                    block_size=int(block_size),
                )
                _persist_department_curricula(
                    cur=cur,
                    faculty_id=faculty_id,
                    department_id=bolum_id,
                    year=year,
                    assignments=assignment,
                )
                dept_processed += 1
                conflicts_removed += int(conflict_count)

            havuz_updates = _sync_havuz_dual_semester_state(
                cur=cur,
                faculty_id=faculty_id,
                year=year,
            )
            total_conflicts_removed += conflicts_removed
            total_havuz_updates += havuz_updates
            rebalanced.append(
                {
                    "fakulte_id": int(faculty_id),
                    "year": int(year),
                    "departments_processed": dept_processed,
                    "conflicts_removed": conflicts_removed,
                    "havuz_rows_updated": havuz_updates,
                }
            )

        conn.commit()
        return {
            "ok": bool(generation_g.get("ok", True)) and bool(generation_b.get("ok", True)),
            "reset": reset,
            "generation_guz": generation_g,
            "generation_bahar": generation_b,
            "rebalanced": rebalanced,
            "totals": {
                "pairs": len(generated_pairs),
                "conflicts_removed": total_conflicts_removed,
                "havuz_rows_updated": total_havuz_updates,
            },
        }
    except Exception as exc:
        conn.rollback()
        return {
            "ok": False,
            "error": str(exc),
            "reset": reset,
            "generation_guz": generation_g,
            "generation_bahar": generation_b,
        }
    finally:
        conn.close()

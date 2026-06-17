# -*- coding: utf-8 -*-
"""Ders takas (swap) servisi (§2.4).

Önerilen (havuzdaki) bir dersi müfredata alırken, aynı dönemden bir dersi
havuza geri gönderir — yani iki dersin statüsünü **karşılıklı** değiştirir
(Müfredatta <-> Havuzda). Yazma, mevcut/test edilmiş ``save_period_planning_result``
üzerinden yapılır (çift-dönem engeli ve müfredat bütünlüğü korunur); havuz
``final_status`` alanı best-effort güncellenir.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.curriculum_repository import (
    get_curriculum_courses_by_year_and_term,
    save_period_planning_result,
)
from app.services.course_curriculum_status_service import FALL, SPRING


def _term_norm(term: str) -> str:
    t = str(term or "").strip().lower()
    if t.startswith(("b", "s")):  # bahar / spring
        return SPRING
    return FALL  # güz / guz / fall / g


def swap_pool_curriculum_course(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int,
    department_id: int,
    term: str,
    incoming_course_id: int,
    outgoing_course_id: int | None = None,
) -> dict[str, Any]:
    """Havuzdaki ``incoming`` dersini müfredata alır; ``outgoing`` dersini havuza yollar.

    outgoing None ise yalnız ekleme yapılır (takas değil, salt ekleme). Müfredat
    bölüm bazlı olduğu için faculty_id + department_id zorunludur. Caller commit eder.
    """
    if faculty_id is None or department_id is None:
        return {"ok": False, "message": "Takas için Fakülte + Bölüm seçili olmalıdır (müfredat bölüm bazlıdır)."}
    target_term = _term_norm(term)

    fall = [int(c["course_id"]) for c in get_curriculum_courses_by_year_and_term(conn, year, FALL, faculty_id, department_id)]
    spring = [int(c["course_id"]) for c in get_curriculum_courses_by_year_and_term(conn, year, SPRING, faculty_id, department_id)]
    bucket = fall if target_term == FALL else spring

    if outgoing_course_id is not None and int(outgoing_course_id) in bucket:
        bucket.remove(int(outgoing_course_id))
    if int(incoming_course_id) not in bucket:
        bucket.append(int(incoming_course_id))

    if target_term == FALL:
        fall = bucket
    else:
        spring = bucket

    # Mevcut, çift-dönem engelli güvenli yazım hattı (ValueError fırlatabilir -> caller yakalar).
    outcome = save_period_planning_result(
        conn,
        int(year),
        faculty_id=int(faculty_id),
        department_id=int(department_id),
        fall_course_ids=fall,
        spring_course_ids=spring,
    )

    # Havuz statü takası (best-effort; tablo/kolon yoksa sessiz geç).
    try:
        conn.execute(
            "UPDATE havuz SET final_status='in_curriculum' WHERE ders_id=? AND yil=?",
            (int(incoming_course_id), int(year)),
        )
        if outgoing_course_id is not None:
            conn.execute(
                "UPDATE havuz SET final_status='in_pool' WHERE ders_id=? AND yil=?",
                (int(outgoing_course_id), int(year)),
            )
    except sqlite3.OperationalError:
        pass

    if outgoing_course_id is not None:
        msg = f"Takas tamam: ders {incoming_course_id} müfredata alındı, ders {outgoing_course_id} havuza gönderildi."
    else:
        msg = f"Ders {incoming_course_id} müfredata eklendi."
    return {"ok": True, "message": msg, **outcome}

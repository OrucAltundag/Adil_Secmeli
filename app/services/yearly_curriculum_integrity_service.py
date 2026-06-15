# -*- coding: utf-8 -*-
"""Yıllık müfredat bütünlük kontrolü.

Güz ve baharı aynı akademik yılın iki parçası kabul ederek tutarlılık denetler:

- Aynı ders aynı yıl içinde hem güz hem bahar müfredatında mı? (çakışma)
- Havuzdaki ders zaten o yıl müfredatta mı? (bilgilendirme)
- Müfredat satırında dönem bilgisi eksik mi?
- Güz/Bahar toplam seçmeli ders sayısı politikayla tutarlı mı?

Salt-okunur; tablo değiştirmez. Sonuç UI'de "Yıllık Müfredat Bütünlük
Kontrolü" panelinde gösterilir.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.curriculum_repository import get_period_planning_summary
from app.services.course_curriculum_status_service import (
    FALL,
    SPRING,
    get_pool_course_ids,
    get_yearly_curriculum_term_map,
)
from app.services.semester_planning_policy_service import resolve_policy

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


def _course_codes(conn: sqlite3.Connection, course_ids: list[int]) -> dict[int, str]:
    if not course_ids:
        return {}
    placeholders = ",".join("?" for _ in course_ids)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT ders_id, COALESCE(kod, ad, ders_id) FROM ders WHERE ders_id IN ({placeholders})",
            tuple(int(c) for c in course_ids),
        )
    except sqlite3.OperationalError:
        return {}
    return {int(r[0]): str(r[1]) for r in cur.fetchall() if r and r[0] is not None}


def _missing_term_count(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
) -> int:
    """Dönem bilgisi boş olan müfredat satırı sayısı (kapsam içinde)."""
    where = ["akademik_yil = ?", "TRIM(COALESCE(donem, '')) = ''"]
    params: list[Any] = [int(year)]
    if department_id is not None:
        where.append("bolum_id = ?")
        params.append(int(department_id))
    elif faculty_id is not None:
        where.append("fakulte_id = ?")
        params.append(int(faculty_id))
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) FROM mufredat WHERE {' AND '.join(where)}", tuple(params))
    except sqlite3.OperationalError:
        return 0
    return int((cur.fetchone() or [0])[0] or 0)


def check_yearly_curriculum_integrity(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """Yıllık müfredat bütünlük raporu döndürür.

    Dönüş: {ok, status, summary, issues:[{type,severity,message,course_ids}]}
    """
    year = int(year)
    term_map = get_yearly_curriculum_term_map(conn, year, faculty_id, department_id)
    pool_ids = get_pool_course_ids(conn, year, faculty_id, department_id)
    summary = get_period_planning_summary(conn, year, faculty_id, department_id)

    conflicts = sorted({cid for cid, terms in term_map.items() if FALL in terms and SPRING in terms})
    yearly_ids = set(term_map.keys())
    pool_in_curriculum = sorted(pool_ids & yearly_ids)
    missing_terms = _missing_term_count(conn, year, faculty_id, department_id)

    codes = _course_codes(conn, conflicts + pool_in_curriculum)
    issues: list[dict[str, Any]] = []

    if conflicts:
        names = ", ".join(codes.get(c, str(c)) for c in conflicts)
        issues.append(
            {
                "type": "duplicate_in_both_terms",
                "severity": SEVERITY_ERROR,
                "message": f"Aynı ders hem güz hem bahar müfredatında: {names}",
                "course_ids": conflicts,
            }
        )

    if pool_in_curriculum:
        names = ", ".join(codes.get(c, str(c)) for c in pool_in_curriculum)
        issues.append(
            {
                "type": "pool_already_in_curriculum",
                "severity": SEVERITY_INFO,
                "message": f"Havuzdaki ders zaten bu yıl müfredatta: {names}",
                "course_ids": pool_in_curriculum,
            }
        )

    if missing_terms:
        issues.append(
            {
                "type": "missing_term_info",
                "severity": SEVERITY_WARNING,
                "message": f"{missing_terms} müfredat kaydında dönem bilgisi eksik.",
                "course_ids": [],
            }
        )

    # Politika ile sayı tutarlılığı yalnız bölüm bazlı kapsamda anlamlıdır
    # (politika üst sınırı bölüm-dönem başınadır; fakülte/genel toplamla
    # kıyaslamak yanıltıcı olur).
    if department_id is not None:
        try:
            policy = resolve_policy(conn, year=year, faculty_id=faculty_id, department_id=department_id)
        except Exception:
            policy = {}
        for term, count_key, max_key, label in (
            (FALL, "fall_count", "fall_max", "Güz"),
            (SPRING, "spring_count", "spring_max", "Bahar"),
        ):
            count = int(summary.get(count_key, 0))
            max_value = int(policy.get(max_key) or 0)
            if max_value and count > max_value:
                issues.append(
                    {
                        "type": "term_count_over_max",
                        "severity": SEVERITY_WARNING,
                        "message": f"{label} müfredatında {count} ders var; politika üst sınırı {max_value}.",
                        "course_ids": [],
                    }
                )

    has_error = any(i["severity"] == SEVERITY_ERROR for i in issues)
    has_warning = any(i["severity"] == SEVERITY_WARNING for i in issues)
    if has_error:
        status = "Çakışma tespit edildi"
    elif has_warning:
        status = "Manuel inceleme önerilir"
    else:
        status = "Bütünlük sağlandı"

    return {
        "ok": not has_error,
        "status": status,
        "summary": summary,
        "issues": issues,
    }

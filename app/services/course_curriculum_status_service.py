# -*- coding: utf-8 -*-
"""Merkezi ders müfredat/havuz durumu servisi.

Bir akademik yılı Güz + Bahar olarak **tek bütün** kabul eder ve bir dersin o
yıl içindeki durumunu tek yerden hesaplar:

- Havuzda mı? (aday/alternatif kaynak)
- Güz müfredatında mı?
- Bahar müfredatında mı?
- Yıllık müfredatta var mı? (güz veya bahar)
- Hangi döneme eklenebilir? (bölüm bazlı tekrar engeli + dönem uygunluğu)
- Durum etiketi / renk / öneri

Kapsam **bölüm bazlıdır**: müfredat (bolum_id, akademik_yil, donem) anahtarıyla
tutulduğu için çakışma kontrolü (bolum_id, yıl, ders) üçlüsüyle yapılır.
department_id verilmezse fakülte, o da yoksa yıl genelinde değerlendirilir.

Bu servis salt-okunur durum hesaplar; müfredat/havuz tablolarını değiştirmez.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.course_semester_availability_service import (
    display_semester,
    get_course_availability,
    get_courses_availability_batch,
    normalize_semester,
)

FALL = "fall"
SPRING = "spring"

# Durum kodları (makine tarafı; UI etiket/renk eşlemesi aşağıdaki sözlükten gelir)
STATUS_CONFLICT = "conflict_both_terms"   # aynı ders hem güz hem bahar müfredatında
STATUS_IN_FALL = "in_fall_curriculum"
STATUS_IN_SPRING = "in_spring_curriculum"
STATUS_IN_POOL = "in_pool"
STATUS_NEW_SUGGESTION = "new_suggestion"
STATUS_UNKNOWN = "no_data"

# status_code -> (etiket, renk, öneri)  renk = UI için semantik jeton
_STATUS_META: dict[str, tuple[str, str, str]] = {
    STATUS_CONFLICT: ("Her iki dönemde de mevcut (çakışma)", "red", "Manuel inceleme gerekli"),
    STATUS_IN_FALL: ("Güz müfredatında mevcut", "green", "Tekrar eklenmemeli"),
    STATUS_IN_SPRING: ("Bahar müfredatında mevcut", "green", "Tekrar eklenmemeli"),
    STATUS_IN_POOL: ("Havuzda", "blue", "Müfredata önerilebilir"),
    STATUS_NEW_SUGGESTION: ("Yeni öneri", "purple", "Müfredata önerilebilir"),
    STATUS_UNKNOWN: ("Veri yok", "gray", "İnceleme gerekli"),
}


def _term_token(value: Any) -> str:
    """Müfredat 'donem' alanını 'g'/'b' tek harfe indirger (SQL ile uyumlu)."""
    return "b" if normalize_semester(value) == SPRING else "g"


def _scope_clause(
    *,
    faculty_id: int | None,
    department_id: int | None,
    fac_col: str,
    dep_col: str,
) -> tuple[str, list[Any]]:
    """Bölüm > fakülte > genel kapsam için WHERE parçası üretir."""
    clauses: list[str] = []
    params: list[Any] = []
    if department_id is not None:
        clauses.append(f"{dep_col} = ?")
        params.append(int(department_id))
    elif faculty_id is not None:
        clauses.append(f"{fac_col} = ?")
        params.append(int(faculty_id))
    return (" AND ".join(clauses), params)


def get_yearly_curriculum_term_map(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[int, set[str]]:
    """{course_id: {"fall","spring"}} — dersin o yıl hangi dönem(ler) müfredatında olduğu.

    Tek sorguda yıllık (güz+bahar) müfredat okunur; böylece dersin yıllık
    bütünlük durumu çıkarılabilir.
    """
    scope, params = _scope_clause(
        faculty_id=faculty_id,
        department_id=department_id,
        fac_col="m.fakulte_id",
        dep_col="m.bolum_id",
    )
    where = ["m.akademik_yil = ?"]
    sql_params: list[Any] = [int(year)]
    if scope:
        where.append(scope)
        sql_params.extend(params)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT DISTINCT md.ders_id,
               LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) AS term_key
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE {' AND '.join(where)}
        """,
        tuple(sql_params),
    )
    out: dict[int, set[str]] = {}
    for ders_id, term_key in cur.fetchall():
        if ders_id is None:
            continue
        term = SPRING if str(term_key or "").startswith("b") else FALL
        out.setdefault(int(ders_id), set()).add(term)
    return out


def get_pool_course_ids(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> set[int]:
    """O yıl havuzda (aday kaynak) bulunan ders id kümesi.

    havuz.ders_id metin olarak saklandığı için CAST kullanılır.
    """
    scope, params = _scope_clause(
        faculty_id=faculty_id,
        department_id=department_id,
        fac_col="fakulte_id",
        dep_col="bolum_id",
    )
    where = ["yil = ?"]
    sql_params: list[Any] = [int(year)]
    if scope:
        where.append(scope)
        sql_params.extend(params)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT DISTINCT CAST(ders_id AS INTEGER) FROM havuz WHERE {' AND '.join(where)}",
            tuple(sql_params),
        )
    except sqlite3.OperationalError:
        return set()
    return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}


def _build_status(
    *,
    course_id: int,
    year: int,
    terms: set[str],
    in_pool: bool,
    availability: dict[str, Any],
) -> dict[str, Any]:
    in_fall = FALL in terms
    in_spring = SPRING in terms
    in_yearly = in_fall or in_spring

    if in_fall and in_spring:
        status_code = STATUS_CONFLICT
    elif in_fall:
        status_code = STATUS_IN_FALL
    elif in_spring:
        status_code = STATUS_IN_SPRING
    elif in_pool:
        status_code = STATUS_IN_POOL
    else:
        status_code = STATUS_UNKNOWN

    label, color, recommendation = _STATUS_META[status_code]

    allowed_fall = bool(availability.get("allowed_fall", True))
    allowed_spring = bool(availability.get("allowed_spring", True))
    # Bölüm bazlı tekrar engeli: ders zaten yıllık müfredattaysa tekrar eklenemez.
    can_add_fall = (not in_yearly) and allowed_fall
    can_add_spring = (not in_yearly) and allowed_spring

    current_semester = None
    if in_fall and not in_spring:
        current_semester = FALL
    elif in_spring and not in_fall:
        current_semester = SPRING

    return {
        "course_id": int(course_id),
        "year": int(year),
        "in_pool": bool(in_pool),
        "in_fall_curriculum": in_fall,
        "in_spring_curriculum": in_spring,
        "in_yearly_curriculum": in_yearly,
        "current_semester": current_semester,
        "current_semester_label": display_semester(current_semester) if current_semester else None,
        "can_be_added_to_fall": can_add_fall,
        "can_be_added_to_spring": can_add_spring,
        "status_code": status_code,
        "status_label": label,
        "status_color": color,
        "recommendation": recommendation,
    }


def get_course_yearly_curriculum_status(
    conn: sqlite3.Connection,
    year: int,
    course_id: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """Tek bir ders için merkezi yıllık durum (bkz. modül başlığı)."""
    term_map = get_yearly_curriculum_term_map(conn, year, faculty_id, department_id)
    pool_ids = get_pool_course_ids(conn, year, faculty_id, department_id)
    availability = get_course_availability(
        conn, int(course_id), year=year, department_id=department_id, faculty_id=faculty_id
    )
    return _build_status(
        course_id=int(course_id),
        year=int(year),
        terms=term_map.get(int(course_id), set()),
        in_pool=int(course_id) in pool_ids,
        availability=availability,
    )


def check_course_exists_in_any_term(
    conn: sqlite3.Connection,
    year: int,
    course_id: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> bool:
    """Ders o akademik yıl içinde herhangi bir dönem müfredatında mı?"""
    term_map = get_yearly_curriculum_term_map(conn, year, faculty_id, department_id)
    return bool(term_map.get(int(course_id)))


def get_courses_status_batch(
    conn: sqlite3.Connection,
    year: int,
    course_ids: list[int],
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[int, dict[str, Any]]:
    """Birden çok ders için durumu tek seferde hesaplar (N+1 sorgudan kaçınır).

    term_map, havuz id'leri ve dönem uygunluğu üçü de toplu (batch) okunur;
    böylece ders sayısı arttıkça sorgu sayısı sabit kalır.
    """
    term_map = get_yearly_curriculum_term_map(conn, year, faculty_id, department_id)
    pool_ids = get_pool_course_ids(conn, year, faculty_id, department_id)
    availability_map = get_courses_availability_batch(
        conn, [int(c) for c in course_ids], year=year, department_id=department_id, faculty_id=faculty_id
    )
    out: dict[int, dict[str, Any]] = {}
    for raw in course_ids:
        cid = int(raw)
        out[cid] = _build_status(
            course_id=cid,
            year=int(year),
            terms=term_map.get(cid, set()),
            in_pool=cid in pool_ids,
            availability=availability_map.get(cid, {}),
        )
    return out

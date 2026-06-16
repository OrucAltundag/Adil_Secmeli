# -*- coding: utf-8 -*-
"""Müfredat verisi için repository.

Sınıf tabanlı `CurriculumRepository` listeleme için kalır. Dönem planlama
(Güz+Bahar bütünlüğü) ekranının ihtiyaç duyduğu yıl/dönem bazlı sorgular ise
modül seviyesinde fonksiyonlar olarak eklenmiştir; servisler `conn`'u doğrudan
geçirdiği için bu imza tutarlıdır. Kapsam bölüm > fakülte > genel sırasıyla
daraltılır.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts
from app.services.course_curriculum_status_service import (
    FALL,
    SPRING,
    check_course_exists_in_any_term,
    get_course_yearly_curriculum_status,
    get_courses_status_batch,
    get_pool_course_ids,
    get_yearly_curriculum_term_map,
)
from app.services.course_semester_availability_service import normalize_semester


class CurriculumRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_curricula(self, year: int | None = None, department_id: int | None = None, semester: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM mufredat WHERE 1=1"
        params: list[Any] = []
        if year is not None:
            query += " AND akademik_yil = ?"
            params.append(int(year))
        if department_id is not None:
            query += " AND bolum_id = ?"
            params.append(int(department_id))
        if semester:
            key = "b" if str(semester).lower().startswith("b") else "g"
            query += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
            params.append(key)
        query += " ORDER BY akademik_yil DESC, bolum_id"
        cur = self.conn.cursor()
        cur.execute(query, tuple(params))
        return fetch_all_dicts(cur)


# ---------------------------------------------------------------------------
# Modül seviyesi sorgular (Dönem Planlama / yıllık bütünlük)
# ---------------------------------------------------------------------------


def _scope_sql(
    *,
    faculty_id: int | None,
    department_id: int | None,
    fac_col: str,
    dep_col: str,
) -> tuple[str, list[Any]]:
    if department_id is not None:
        return (f" AND {dep_col} = ?", [int(department_id)])
    if faculty_id is not None:
        return (f" AND {fac_col} = ?", [int(faculty_id)])
    return ("", [])


def _latest_score_map(conn: sqlite3.Connection, year: int) -> dict[int, float]:
    """O yıla kadar (dahil) en yüksek toplam skoru ders bazında döndürür."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT ders_id, MAX(skor_top)
            FROM skor
            WHERE akademik_yil <= ?
            GROUP BY ders_id
            """,
            (int(year),),
        )
    except sqlite3.OperationalError:
        return {}
    out: dict[int, float] = {}
    for ders_id, score in cur.fetchall():
        if ders_id is None or score is None:
            continue
        try:
            out[int(ders_id)] = float(score)
        except (TypeError, ValueError):
            continue
    return out


def get_latest_curriculum_year_by_faculty(
    conn: sqlite3.Connection,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> int | None:
    """Seçili kapsam (fakülte / bölüm) için en son mevcut müfredat yılını döndürür.

    Bölüm verilirse bölüm bazlı, yalnız fakülte verilirse fakülte bazlı, hiçbiri
    yoksa genel en yüksek müfredat yılı döner. Müfredat yoksa ``None``.
    """
    scope, params = _scope_sql(
        faculty_id=faculty_id,
        department_id=department_id,
        fac_col="fakulte_id",
        dep_col="bolum_id",
    )
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT MAX(akademik_yil) FROM mufredat WHERE 1=1{scope}", tuple(params))
    except sqlite3.OperationalError:
        return None
    row = cur.fetchone()
    if not row or row[0] is None:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def get_confirmation_scores_by_scope_and_year(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[tuple[int, str], float]:
    """Kapsam+yıl için ders bazlı kesinleşme puanlarını (havuz.skor) döndürür.

    Anahtar: ``(ders_id, term_key)`` — term_key 'g' (güz) veya 'b' (bahar).
    Puanı olmayan ders sözlükte yer almaz (çağıran 'puan yok' olarak yorumlar).
    """
    scope, params = _scope_sql(
        faculty_id=faculty_id,
        department_id=department_id,
        fac_col="fakulte_id",
        dep_col="bolum_id",
    )
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT ders_id, donem, skor FROM havuz WHERE yil = ?{scope}",
            tuple([int(year)] + params),
        )
    except sqlite3.OperationalError:
        return {}
    out: dict[tuple[int, str], float] = {}
    for ders_id, donem, skor in cur.fetchall():
        if ders_id is None or skor is None:
            continue
        term_key = "b" if str(donem or "").strip().lower().startswith("b") else "g"
        try:
            out[(int(ders_id), term_key)] = float(skor)
        except (TypeError, ValueError):
            continue
    return out


def get_curriculum_courses_by_year(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    """Verilen yılın güz+bahar müfredatındaki dersleri dönem etiketiyle döndürür."""
    scope, params = _scope_sql(
        faculty_id=faculty_id,
        department_id=department_id,
        fac_col="m.fakulte_id",
        dep_col="m.bolum_id",
    )
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT DISTINCT md.ders_id,
               LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) AS term_key,
               d.kod, d.ad, d.bolum_id, COALESCE(d.fakulte_id, b.fakulte_id) AS fakulte_id,
               d.kontenjan, d.kredi, d.akts, m.durum
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        LEFT JOIN ders d ON d.ders_id = md.ders_id
        LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
        WHERE m.akademik_yil = ?{scope}
        ORDER BY term_key, d.kod
        """,
        tuple([int(year)] + params),
    )
    score_map = _latest_score_map(conn, year)
    rows: list[dict[str, Any]] = []
    for ders_id, term_key, kod, ad, bolum_id, fakulte_id, kontenjan, kredi, akts, durum in cur.fetchall():
        if ders_id is None:
            continue
        cid = int(ders_id)
        term = SPRING if str(term_key or "").startswith("b") else FALL
        rows.append(
            {
                "course_id": cid,
                "course_code": kod or str(cid),
                "course_name": ad or str(cid),
                "term": term,
                "department_id": bolum_id,
                "faculty_id": fakulte_id,
                "capacity": kontenjan,
                "credit": kredi,
                "ects": akts,
                "curriculum_status": durum,
                "score": score_map.get(cid, 0.0),
            }
        )
    return rows


def get_curriculum_courses_by_year_and_term(
    conn: sqlite3.Connection,
    year: int,
    term: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    """Belirli yıl + dönem (fall/spring) müfredat dersleri."""
    target = normalize_semester(term)
    return [
        row
        for row in get_curriculum_courses_by_year(conn, year, faculty_id, department_id)
        if row["term"] == target
    ]


def get_fall_curriculum_courses(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    return get_curriculum_courses_by_year_and_term(conn, year, FALL, faculty_id, department_id)


def get_spring_curriculum_courses(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    return get_curriculum_courses_by_year_and_term(conn, year, SPRING, faculty_id, department_id)


def get_pool_courses_by_year(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    """O yıl havuzdaki dersler (ders meta ve skor ile zenginleştirilmiş)."""
    scope, params = _scope_sql(
        faculty_id=faculty_id,
        department_id=department_id,
        fac_col="h.fakulte_id",
        dep_col="h.bolum_id",
    )
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT CAST(h.ders_id AS INTEGER) AS ders_id,
                   LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) AS term_key,
                   h.statu, h.sayac, h.skor, h.bolum_id, h.fakulte_id,
                   COALESCE(d.kod, h.ders_id) AS kod,
                   COALESCE(d.ad, h.ders_adi) AS ad,
                   d.kontenjan, d.kredi, d.akts
            FROM havuz h
            LEFT JOIN ders d ON d.ders_id = CAST(h.ders_id AS INTEGER)
            WHERE h.yil = ?{scope}
            ORDER BY kod
            """,
            tuple([int(year)] + params),
        )
    except sqlite3.OperationalError:
        return []
    score_map = _latest_score_map(conn, year)
    rows: list[dict[str, Any]] = []
    for ders_id, term_key, statu, sayac, skor, bolum_id, fakulte_id, kod, ad, kontenjan, kredi, akts in cur.fetchall():
        if ders_id is None:
            continue
        cid = int(ders_id)
        term = SPRING if str(term_key or "").startswith("b") else FALL
        try:
            score = float(skor) if skor is not None else score_map.get(cid, 0.0)
        except (TypeError, ValueError):
            score = score_map.get(cid, 0.0)
        rows.append(
            {
                "course_id": cid,
                "course_code": kod or str(cid),
                "course_name": ad or str(cid),
                "pool_term": term,
                "pool_status": int(statu) if statu is not None else None,
                "pool_counter": int(sayac) if sayac is not None else None,
                "department_id": bolum_id,
                "faculty_id": fakulte_id,
                "capacity": kontenjan,
                "credit": kredi,
                "ects": akts,
                "score": score,
            }
        )
    # Birleşik havuz semantiği: ders güz+bahar havuzunda ayrı satırlarsa tek
    # satıra indir (en yüksek statü/skor korunur; pool_term anlamını yitirir).
    deduped: dict[int, dict[str, Any]] = {}
    for row in rows:
        cid = int(row["course_id"])
        existing = deduped.get(cid)
        if existing is None:
            deduped[cid] = row
            continue
        if (row.get("pool_status") or -99) > (existing.get("pool_status") or -99):
            existing["pool_status"] = row.get("pool_status")
        existing["score"] = max(float(existing.get("score") or 0.0), float(row.get("score") or 0.0))
        for key in ("credit", "ects", "capacity", "department_id", "faculty_id"):
            if existing.get(key) is None and row.get(key) is not None:
                existing[key] = row.get(key)
    return list(deduped.values())


def get_pool_courses_with_curriculum_status(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    """Havuz dersleri + her ders için merkezi yıllık müfredat durumu.

    Havuzdaki bir dersin aynı yıl güz/bahar müfredatında olup olmadığını
    durum etiketiyle gösterir (bkz. CourseCurriculumStatusService).
    """
    pool_rows = get_pool_courses_by_year(conn, year, faculty_id, department_id)
    if not pool_rows:
        return []
    status_map = get_courses_status_batch(
        conn,
        year,
        [row["course_id"] for row in pool_rows],
        faculty_id=faculty_id,
        department_id=department_id,
    )
    merged: list[dict[str, Any]] = []
    for row in pool_rows:
        status = status_map.get(row["course_id"], {})
        merged.append({**row, **status})
    return merged


def get_course_yearly_curriculum_status_row(
    conn: sqlite3.Connection,
    year: int,
    course_id: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """Tek ders için merkezi durum (servise ince sarmalayıcı)."""
    return get_course_yearly_curriculum_status(
        conn, year, course_id, faculty_id=faculty_id, department_id=department_id
    )


def course_exists_in_any_term(
    conn: sqlite3.Connection,
    year: int,
    course_id: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> bool:
    """Ders o yıl herhangi bir dönem müfredatında mı? (çakışma/önleme için)."""
    return check_course_exists_in_any_term(
        conn, year, course_id, faculty_id=faculty_id, department_id=department_id
    )


def get_period_planning_summary(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """Dönem planlama özet kartları için sayımlar.

    Güz/Bahar müfredat ders sayıları, havuz sayısı, yıllık toplam, çakışma
    (aynı ders iki dönemde) ve yeni öneri (havuzda olup müfredatta olmayan)
    sayılarını döndürür.
    """
    term_map = get_yearly_curriculum_term_map(conn, year, faculty_id, department_id)
    pool_ids = get_pool_course_ids(conn, year, faculty_id, department_id)
    fall_courses = {cid for cid, terms in term_map.items() if FALL in terms}
    spring_courses = {cid for cid, terms in term_map.items() if SPRING in terms}
    conflicts = {cid for cid, terms in term_map.items() if FALL in terms and SPRING in terms}
    yearly = set(term_map.keys())
    new_suggestions = pool_ids - yearly
    return {
        "year": int(year),
        "fall_count": len(fall_courses),
        "spring_count": len(spring_courses),
        "pool_count": len(pool_ids),
        "yearly_total": len(yearly),
        "conflict_count": len(conflicts),
        "new_suggestion_count": len(new_suggestions),
        "conflict_course_ids": sorted(conflicts),
    }


def _fetch_or_create_curriculum_id(
    cur: sqlite3.Cursor,
    *,
    faculty_id: int,
    department_id: int,
    year: int,
    term: str,
) -> int:
    """Bölüm+yıl+dönem için müfredat satırını bulur, yoksa oluşturur."""
    term_token = "b" if normalize_semester(term) == SPRING else "g"
    donem_value = "Bahar" if term_token == "b" else "Guz"
    cur.execute(
        """
        SELECT mufredat_id FROM mufredat
        WHERE fakulte_id = ? AND bolum_id = ? AND akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
        ORDER BY COALESCE(versiyon, 0) DESC, mufredat_id DESC
        LIMIT 1
        """,
        (int(faculty_id), int(department_id), int(year), term_token),
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
        VALUES (?, ?, ?, ?, 'Dönem-Planlama', ?)
        """,
        (int(faculty_id), int(department_id), int(year), donem_value, version),
    )
    return int(cur.lastrowid or 0)


def _latest_decision_map(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[int, float]:
    """Kapsamdaki en güncel karar çalıştırmasından açılabilirlik (güven) skorları.

    Tablo/kolon yoksa boş döner; havuz görünümü yine de çalışır.
    """
    cur = conn.cursor()
    tables = {str(r[0]) for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "course_decisions" not in tables or "decision_runs" not in tables:
        return {}
    cd_cols = {str(r[1]) for r in cur.execute("PRAGMA table_info(course_decisions)").fetchall()}
    if "acilabilirlik_score" not in cd_cols:
        return {}
    where = ["dr.year = ?"]
    params: list[Any] = [int(year)]
    if faculty_id is not None:
        where.append("dr.faculty_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("dr.department_id = ?")
        params.append(int(department_id))
    try:
        cur.execute(
            f"""
            SELECT cd.course_id, cd.acilabilirlik_score
            FROM course_decisions cd
            WHERE cd.decision_run_id = (
                SELECT dr.id FROM decision_runs dr
                WHERE {' AND '.join(where)}
                ORDER BY dr.id DESC LIMIT 1
            )
            """,
            tuple(params),
        )
    except sqlite3.OperationalError:
        return {}
    out: dict[int, float] = {}
    for cid, score in cur.fetchall():
        if cid is None or score is None:
            continue
        try:
            out[int(cid)] = float(score)
        except (TypeError, ValueError):
            continue
    return out


def _pool_explanation(status: dict[str, Any]) -> str:
    code = status.get("status_code")
    if code == "conflict_both_terms":
        return "Ders aynı yıl hem güz hem bahar müfredatında görünüyor; çakışma incelenmeli."
    if code == "in_fall_curriculum":
        return "Ders bu yıl güz müfredatında bulunduğu için tekrar önerilmedi."
    if code == "in_spring_curriculum":
        return "Ders bu yıl bahar müfredatında bulunduğu için tekrar önerilmedi."
    if code == "in_pool":
        return "Ders havuzda aday olarak bekliyor; müfredata önerilebilir."
    return "Ders için yıllık müfredat bilgisi bulunamadı."


def get_pool_courses_with_curriculum_flags(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    """Birleşik havuz satırları: kredi/akts + yıllık durum bayrakları + güven + açıklama.

    Havuz Yönetimi birleşik tablosunu besler (spec madde 8/10).
    """
    pool_rows = get_pool_courses_with_curriculum_status(conn, year, faculty_id, department_id)
    if not pool_rows:
        return []
    decision_map = _latest_decision_map(conn, year, faculty_id, department_id)
    out: list[dict[str, Any]] = []
    for row in pool_rows:
        cid = int(row["course_id"])
        out.append(
            {
                **row,
                "credit": row.get("credit"),
                "ects": row.get("ects"),
                "recommendation_status": row.get("recommendation"),
                "final_decision": row.get("status_label"),
                "confidence_score": decision_map.get(cid),
                "explanation": _pool_explanation(row),
            }
        )
    return out


def get_unified_pool_by_year(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """Havuz Yönetimi tek-ekran paketi: birleşik havuz + güz/bahar müfredatı + özet."""
    return {
        "year": int(year),
        "pool_courses": get_pool_courses_with_curriculum_flags(conn, year, faculty_id, department_id),
        "fall_curriculum": get_fall_curriculum_courses(conn, year, faculty_id, department_id),
        "spring_curriculum": get_spring_curriculum_courses(conn, year, faculty_id, department_id),
        "summary": get_period_planning_summary(conn, year, faculty_id, department_id),
    }


# Spec'te istenen imza takma adları (mevcut fonksiyonlara ince sarmalayıcı)
def get_fall_curriculum_by_year(
    conn: sqlite3.Connection, year: int, faculty_id: int | None = None, department_id: int | None = None
) -> list[dict[str, Any]]:
    return get_fall_curriculum_courses(conn, year, faculty_id, department_id)


def get_spring_curriculum_by_year(
    conn: sqlite3.Connection, year: int, faculty_id: int | None = None, department_id: int | None = None
) -> list[dict[str, Any]]:
    return get_spring_curriculum_courses(conn, year, faculty_id, department_id)


def get_yearly_curriculum_summary(
    conn: sqlite3.Connection, year: int, faculty_id: int | None = None, department_id: int | None = None
) -> dict[str, Any]:
    return get_period_planning_summary(conn, year, faculty_id, department_id)


def get_course_curriculum_flags(
    conn: sqlite3.Connection, year: int, course_id: int, faculty_id: int | None = None, department_id: int | None = None
) -> dict[str, Any]:
    return get_course_yearly_curriculum_status_row(conn, year, course_id, faculty_id, department_id)


def check_course_in_fall_curriculum(
    conn: sqlite3.Connection, year: int, course_id: int, faculty_id: int | None = None, department_id: int | None = None
) -> bool:
    return bool(
        get_course_yearly_curriculum_status_row(conn, year, course_id, faculty_id, department_id).get(
            "in_fall_curriculum"
        )
    )


def check_course_in_spring_curriculum(
    conn: sqlite3.Connection, year: int, course_id: int, faculty_id: int | None = None, department_id: int | None = None
) -> bool:
    return bool(
        get_course_yearly_curriculum_status_row(conn, year, course_id, faculty_id, department_id).get(
            "in_spring_curriculum"
        )
    )


def save_period_planning_result(
    conn: sqlite3.Connection,
    year: int,
    *,
    faculty_id: int,
    department_id: int,
    fall_course_ids: list[int],
    spring_course_ids: list[int],
    plan_run_id: int | None = None,
) -> dict[str, Any]:
    """Dönem planlama sonucunu bölüm müfredatına yazar (çift-dönem engelli).

    Bölüm bazlı yıllık bütünlük kuralı gereği aynı ders hem güz hem bahar
    listesinde olamaz; varsa ValueError ile reddedilir. Caller commit eder.
    """
    fall = [int(c) for c in fall_course_ids]
    spring = [int(c) for c in spring_course_ids]
    overlap = sorted(set(fall) & set(spring))
    if overlap:
        raise ValueError(
            "Aynı ders aynı akademik yıl içinde hem güz hem bahar müfredatına "
            f"eklenemez. Çakışan ders id(leri): {overlap}"
        )
    cur = conn.cursor()
    has_run_col = "semester_plan_run_id" in {
        str(r[1]) for r in cur.execute("PRAGMA table_info(mufredat_ders)").fetchall()
    }
    written = {FALL: 0, SPRING: 0}
    for term, course_ids in ((FALL, fall), (SPRING, spring)):
        mufredat_id = _fetch_or_create_curriculum_id(
            cur,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            term=term,
        )
        cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (int(mufredat_id),))
        for ders_id in dict.fromkeys(course_ids):
            if has_run_col:
                cur.execute(
                    "INSERT INTO mufredat_ders (mufredat_id, ders_id, semester_plan_run_id) "
                    "VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                    (int(mufredat_id), int(ders_id), plan_run_id),
                )
            else:
                cur.execute(
                    "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?) "
                    "ON CONFLICT DO NOTHING",
                    (int(mufredat_id), int(ders_id)),
                )
            written[term] += 1
    return {
        "ok": True,
        "year": int(year),
        "faculty_id": int(faculty_id),
        "department_id": int(department_id),
        "fall_written": written[FALL],
        "spring_written": written[SPRING],
    }


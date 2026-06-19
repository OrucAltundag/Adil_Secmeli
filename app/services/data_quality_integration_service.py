# -*- coding: utf-8 -*-
"""
Data Quality Integration Service

Veri kalitesi servislerinin sqlite3 cursor tabanlı wrapperları.
Decision engine ile entegrasyon için cursor-safe fonksiyonlar sağlar.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _fac_dept_clause(faculty_id: Optional[int], department_id: Optional[int], alias: str = "d") -> str:
    """ders tablosu (alias) icin fakulte/bolum WHERE eki."""
    parts = []
    if faculty_id:
        parts.append(f"AND {alias}.fakulte_id = {int(faculty_id)}")
    if department_id:
        parts.append(f"AND {alias}.bolum_id = {int(department_id)}")
    return " ".join(parts)


def _count_distinct_courses(
    cur: sqlite3.Cursor,
    table: str,
    faculty_id: Optional[int],
    department_id: Optional[int],
    extra_where: str = "",
) -> int:
    """
    Verilen tabloda, ders tablosuna JOIN ile fakulte/bolum filtreli
    distinct ders_id sayisi. Tablo yoksa 0 doner.
    """
    fac_dept = _fac_dept_clause(faculty_id, department_id, alias="d")
    sql = (
        f"SELECT COUNT(DISTINCT t.ders_id) "
        f"FROM {table} t "
        f"JOIN ders d ON d.ders_id = t.ders_id "
        f"WHERE 1=1 {extra_where} {fac_dept}"
    )
    try:
        cur.execute(sql)
        return int(cur.fetchone()[0] or 0)
    except sqlite3.OperationalError:
        return 0


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _curriculum_course_ids(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int],
    department_id: Optional[int],
) -> set[int]:
    """Kapsam (fakulte/bolum) + yil icin MUFREDATTA bulunan ders_id kumesi.

    Kriter/performans/populerlik verisi YALNIZCA bu (zorunlu) kume icin
    beklenir. Once bolum uzerinden (canonical), basarisizsa mufredat.fakulte_id
    (legacy sema) ile dener; ikisinin birlesimini doner. Mufredat tanimli
    degilse bos kume doner (cagiran tarafta fallback uygulanir).
    """
    ids: set[int] = set()

    # 1) Canonical: bolum -> fakulte uzerinden
    try:
        where = ["m.akademik_yil = ?"]
        params: list[Any] = [int(year)]
        if faculty_id is not None:
            where.append("b.fakulte_id = ?")
            params.append(int(faculty_id))
        if department_id is not None:
            where.append("m.bolum_id = ?")
            params.append(int(department_id))
        cur.execute(
            f"""
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN bolum b ON b.bolum_id = m.bolum_id
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            WHERE {' AND '.join(where)}
            """,
            tuple(params),
        )
        ids |= {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
    except sqlite3.OperationalError:
        pass

    # 2) Legacy: mufredat.fakulte_id uzerinden. Canonical sorguda bolum
    # secildiyse legacy uyumluluk yolu da AYNI bolumle sinirlanmalidir.
    # Aksi halde secili bolum kumesine fakultenin diger bolumleri tekrar
    # eklenir ve Veri Yonetimi kartlari bolum degisse bile ayni gorunur.
    try:
        where = ["m.akademik_yil = ?"]
        params = [int(year)]
        if faculty_id is not None:
            where.append("m.fakulte_id = ?")
            params.append(int(faculty_id))
        if department_id is not None:
            where.append("m.bolum_id = ?")
            params.append(int(department_id))
        cur.execute(
            f"""
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            WHERE {' AND '.join(where)}
            """,
            tuple(params),
        )
        ids |= {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
    except sqlite3.OperationalError:
        pass

    return ids


def _count_courses_in_set(
    cur: sqlite3.Cursor,
    table: str,
    course_ids: set[int],
    extra_where: str = "",
) -> int:
    """Verilen ders_id kumesi icinde, `table` tablosunda extra_where kosulunu
    saglayan distinct ders sayisi. Kume bossa 0 doner."""
    if not course_ids:
        return 0
    placeholders = ",".join("?" for _ in course_ids)
    sql = (
        f"SELECT COUNT(DISTINCT t.ders_id) FROM {table} t "
        f"WHERE t.ders_id IN ({placeholders}) {extra_where}"
    )
    try:
        cur.execute(sql, tuple(int(i) for i in course_ids))
        return int(cur.fetchone()[0] or 0)
    except sqlite3.OperationalError:
        return 0


def assess_data_readiness_cursor(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
) -> dict[str, Any]:
    """
    Veri olgunluğunu değerlendir (cursor tabanlı).

    Returns:
        {
            'readiness_score': float (0-100),
            'readiness_level': str ('not_ready', 'low', 'medium', 'good', 'decision_ready'),
            'total_courses': int,
            'criteria_score': float,
            'performance_score': float,
            'popularity_score': float,
            'survey_score': float,
            'validation_score': float,
        }
    """
    try:
        # Toplam ders sayısı (baglam icin; ZORUNLU kume degil)
        where_fac = f"AND d.fakulte_id = {int(faculty_id)}" if faculty_id else ""
        where_dept = f"AND d.bolum_id = {int(department_id)}" if department_id else ""

        cur.execute(f"SELECT COUNT(*) FROM ders d WHERE 1=1 {where_fac} {where_dept}")
        total_courses = int(cur.fetchone()[0] or 0)

        if total_courses == 0:
            return {
                'readiness_score': 0.0,
                'readiness_level': 'not_ready',
                'total_courses': 0,
                'required_courses': 0,
                'curriculum_defined': False,
                'criteria_score': 0.0,
                'performance_score': 0.0,
                'popularity_score': 0.0,
                'survey_score': 0.0,
                'survey_required': False,
                'validation_score': 100.0,  # No issues means good score
                'formula_version': 2,
            }

        # ZORUNLU KUME = mufredattaki dersler. Kriter/performans/populerlik
        # YALNIZCA bu dersler icin beklenir; mufredat disi (havuz) dersleri
        # eksik perf/pop yuzunden olgunlugu DUSURMEZ.
        curriculum_ids = _curriculum_course_ids(cur, year, faculty_id, department_id)
        curriculum_defined = bool(curriculum_ids)
        required = len(curriculum_ids)

        if curriculum_defined:
            criteria_count = _count_courses_in_set(
                cur, "ders_kriterleri", curriculum_ids, f"AND t.yil = {int(year)}")
            perf_count = _count_courses_in_set(
                cur, "performans", curriculum_ids,
                f"AND t.akademik_yil = {int(year)} AND t.basari_orani IS NOT NULL")
            pop_count = _count_courses_in_set(
                cur, "populerlik", curriculum_ids,
                f"AND t.akademik_yil = {int(year)} AND t.doluluk_orani IS NOT NULL")
        else:
            # Mufredat tanimli degil -> eski (tum ders) paydasina geri dus.
            required = total_courses
            criteria_count = _count_distinct_courses(
                cur, "ders_kriterleri", faculty_id, department_id,
                extra_where=f"AND t.yil = {int(year)}")
            perf_count = _count_distinct_courses(
                cur, "performans", faculty_id, department_id,
                extra_where=f"AND t.akademik_yil = {int(year)} AND t.basari_orani IS NOT NULL")
            pop_count = _count_distinct_courses(
                cur, "populerlik", faculty_id, department_id,
                extra_where=f"AND t.akademik_yil = {int(year)} AND t.doluluk_orani IS NOT NULL")

        # Anket: HICBIR ders icin zorunlu degil -> yalnizca bilgi amacli (informatif).
        # Olgunluk skoruna GIRMEZ. Bir ders hic secilmemis olabilir.
        survey_count = _count_distinct_courses(
            cur, "anket_sonuclari", faculty_id, department_id,
            extra_where="AND t.oy_sayisi > 0",
        )

        # Validation issues — KAPSAM + MUFREDAT filtreli, DERS BAZINDA sayilir.
        # Onceki surum yil genelindeki TUM kritik satirlari sayiyordu; bu yuzden
        # (1) baska fakultelerin sorunlari da Tip'in skorunu dusuruyordu,
        # (2) tek bir dersin 5 bos alani 5 sorun = -125 ile skoru sifirliyordu.
        # Artik yalnizca SECILI kapsamdaki (ve mufredat tanimliysa mufredat)
        # derslerden, kritik sorunu OLAN farkli ders sayisi dikkate alinir.
        blocking_courses = 0
        try:
            where = ["severity = 'critical'", "year = ?"]
            params: list[Any] = [int(year)]
            if faculty_id is not None:
                where.append("(faculty_id = ? OR faculty_id IS NULL)")
                params.append(int(faculty_id))
            if curriculum_defined:
                ph = ",".join("?" for _ in curriculum_ids)
                where.append(f"course_id IN ({ph})")
                params.extend(int(i) for i in curriculum_ids)
            cur.execute(
                f"SELECT COUNT(DISTINCT course_id) FROM criteria_validation_issues "
                f"WHERE {' AND '.join(where)}",
                tuple(params),
            )
            blocking_courses = int(cur.fetchone()[0] or 0)
        except sqlite3.OperationalError:
            try:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM data_validation_issues
                    WHERE severity = 'critical' AND is_resolved = 0
                    """
                )
                blocking_courses = int(cur.fetchone()[0] or 0)
            except sqlite3.OperationalError:
                blocking_courses = 0

        denom = required if required > 0 else 1
        criteria_score = criteria_count / denom * 100
        performance_score = perf_count / denom * 100
        popularity_score = pop_count / denom * 100
        # Anket skoru bilgi amacli (tum ders paydasina gore) — gate'e girmez.
        survey_score = (survey_count / total_courses * 100) if total_courses > 0 else 0
        # Sorunlu ders orani kadar dus; mufredat tanimliysa orana, degilse -25/ders.
        if curriculum_defined and required > 0:
            validation_score = max(0.0, (required - blocking_courses) / required * 100)
        else:
            validation_score = max(0, 100 - (blocking_courses * 25))

        # === YENI FORMUL (v2) — anket HARIC, mufredat-tabanli ===
        # Agirliklar 1.0'a normalize (eski anket payi kriter/perf/pop'a dagitildi):
        readiness_score = (
            criteria_score * 0.50 +
            performance_score * 0.20 +
            popularity_score * 0.20 +
            validation_score * 0.10
        )

        # Determine level
        if readiness_score < 30:
            level = "not_ready"
        elif readiness_score < 50:
            level = "low"
        elif readiness_score < 70:
            level = "medium"
        elif readiness_score < 85:
            level = "good"
        else:
            level = "decision_ready"

        return {
            'readiness_score': round(readiness_score, 1),
            'readiness_level': level,
            'total_courses': total_courses,
            'required_courses': required,
            'curriculum_defined': curriculum_defined,
            'criteria_score': round(criteria_score, 1),
            'performance_score': round(performance_score, 1),
            'popularity_score': round(popularity_score, 1),
            'survey_score': round(survey_score, 1),
            'survey_required': False,
            'validation_score': round(validation_score, 1),
            'formula_version': 2,
        }
    except Exception as e:
        return {
            'readiness_score': 0.0,
            'readiness_level': 'not_ready',
            'total_courses': 0,
            'required_courses': 0,
            'curriculum_defined': False,
            'criteria_score': 0.0,
            'performance_score': 0.0,
            'popularity_score': 0.0,
            'survey_score': 0.0,
            'survey_required': False,
            'validation_score': 0.0,
            'formula_version': 2,
            'error': str(e),
        }


def generate_coverage_report_cursor(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
) -> dict[str, Any]:
    """
    Veri kapsama raporunu hesapla (cursor tabanlı).

    Returns:
        {
            'total_courses': int,
            'courses_with_criteria': int,
            'courses_with_performance': int,
            'courses_with_popularity': int,
            'courses_with_survey': int,
            'coverage_percentage': float (0-100),
            'by_faculty': {...},
            'by_department': {...},
        }
    """
    try:
        where_fac = f"AND d.fakulte_id = {int(faculty_id)}" if faculty_id else ""
        where_dept = f"AND d.bolum_id = {int(department_id)}" if department_id else ""

        cur.execute(f"SELECT COUNT(*) FROM ders d WHERE 1=1 {where_fac} {where_dept}")
        total_all_courses = int(cur.fetchone()[0] or 0)

        if total_all_courses == 0:
            return {
                'total_courses': 0,
                'total_all_courses': 0,
                'required_courses': 0,
                'curriculum_defined': False,
                'courses_with_criteria': 0,
                'courses_with_performance': 0,
                'courses_with_popularity': 0,
                'courses_with_survey': 0,
                'survey_required': False,
                'coverage_percentage': 0.0,
            }

        # ZORUNLU kume = mufredattaki dersler (kriter/perf/pop yalniz bunlar icin).
        curriculum_ids = _curriculum_course_ids(cur, year, faculty_id, department_id)
        curriculum_defined = bool(curriculum_ids)
        required = len(curriculum_ids)

        if curriculum_defined:
            with_criteria = _count_courses_in_set(
                cur, "ders_kriterleri", curriculum_ids, f"AND t.yil = {int(year)}")
            with_perf = _count_courses_in_set(
                cur, "performans", curriculum_ids,
                f"AND t.akademik_yil = {int(year)} AND t.basari_orani IS NOT NULL")
            with_pop = _count_courses_in_set(
                cur, "populerlik", curriculum_ids,
                f"AND t.akademik_yil = {int(year)} AND t.doluluk_orani IS NOT NULL")
        else:
            required = total_all_courses
            with_criteria = _count_distinct_courses(
                cur, "ders_kriterleri", faculty_id, department_id,
                extra_where=f"AND t.yil = {int(year)}")
            with_perf = _count_distinct_courses(
                cur, "performans", faculty_id, department_id,
                extra_where=f"AND t.akademik_yil = {int(year)} AND t.basari_orani IS NOT NULL")
            with_pop = _count_distinct_courses(
                cur, "populerlik", faculty_id, department_id,
                extra_where=f"AND t.akademik_yil = {int(year)} AND t.doluluk_orani IS NOT NULL")

        # Anket: informatif (kapsama yuzdesine GIRMEZ). Yeni anket importu degerleri
        # ders_kriterleri.anket_dersi_secen alanina yazar; bu yuzden ayni yil/kapsam
        # filtresiyle oradan sayilir (eski anket_sonuclari tablosu yil filtresiz oldugu
        # icin sismis sayim ureterek toplam ders sayisini asabiliyordu).
        if curriculum_defined:
            with_survey = _count_courses_in_set(
                cur, "ders_kriterleri", curriculum_ids,
                f"AND t.yil = {int(year)} AND COALESCE(t.anket_dersi_secen, 0) > 0")
        else:
            with_survey = _count_distinct_courses(
                cur, "ders_kriterleri", faculty_id, department_id,
                extra_where=f"AND t.yil = {int(year)} AND COALESCE(t.anket_dersi_secen, 0) > 0")

        # Kapsama yuzdesi: yalniz ZORUNLU veri tipleri (kriter/perf/pop), mufredat paydasi.
        denom = required if required > 0 else 1
        coverage = (
            (with_criteria / denom * 0.50) +
            (with_perf / denom * 0.25) +
            (with_pop / denom * 0.25)
        ) * 100

        return {
            # 'total_courses' = ZORUNLU payda (UI yuzdeleri bununla dogru cikar).
            'total_courses': required,
            'total_all_courses': total_all_courses,
            'required_courses': required,
            'curriculum_defined': curriculum_defined,
            'courses_with_criteria': with_criteria,
            'courses_with_performance': with_perf,
            'courses_with_popularity': with_pop,
            'courses_with_survey': with_survey,
            'survey_required': False,
            'coverage_percentage': round(coverage, 1),
        }
    except Exception as e:
        return {
            'total_courses': 0,
            'total_all_courses': 0,
            'required_courses': 0,
            'curriculum_defined': False,
            'courses_with_criteria': 0,
            'courses_with_performance': 0,
            'courses_with_popularity': 0,
            'courses_with_survey': 0,
            'survey_required': False,
            'coverage_percentage': 0.0,
            'error': str(e),
        }


def list_available_years(db_path: Optional[str] = None) -> list[int]:
    """Performans/mufredat/kriter tablolarindaki distinct akademik yillari doner.

    Baglantiyi kendi acar/kapatir; UI katmaninin DB acmasina gerek kalmaz.
    """
    from app.db.session import open_sqlite_connection

    conn = open_sqlite_connection(db_path or None, row_factory=True)
    try:
        cur = conn.cursor()
        year_values: set[int] = set()
        for query in (
            "SELECT DISTINCT akademik_yil FROM performans WHERE akademik_yil IS NOT NULL",
            "SELECT DISTINCT akademik_yil FROM mufredat WHERE akademik_yil IS NOT NULL",
            "SELECT DISTINCT yil FROM ders_kriterleri WHERE yil IS NOT NULL",
        ):
            try:
                cur.execute(query)
                for row in cur.fetchall():
                    if not row or row[0] is None:
                        continue
                    try:
                        year_values.add(int(row[0]))
                    except (TypeError, ValueError):
                        continue
            except sqlite3.OperationalError:
                continue
        return sorted(year_values, reverse=True)
    finally:
        conn.close()


def list_faculties(db_path: Optional[str] = None) -> list[tuple[int, str]]:
    """(fakulte_id, ad) listesini ada gore sirali doner."""
    from app.db.session import open_sqlite_connection

    conn = open_sqlite_connection(db_path or None, row_factory=True)
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
            return [(int(row[0]), str(row[1])) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            return []
    finally:
        conn.close()


def get_missing_data_matrix(
    db_path: Optional[str],
    year: int,
    faculty_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Eksik veri matrisi: en az bir veri tipi eksik olan dersleri doner.

    Her oge: {ders_id, kod, ad, criteria, performance, popularity, survey, trend}
    (bool alanlar). Tum dersler tam ise bos liste doner.
    """
    from app.db.session import open_sqlite_connection

    conn = open_sqlite_connection(db_path or None, row_factory=True)
    try:
        cur = conn.cursor()
        fac = f"AND d.fakulte_id = {int(faculty_id)}" if faculty_id else ""
        cur.execute(
            f"""
            SELECT d.ders_id, COALESCE(d.kod,''), COALESCE(d.ad,''),
              EXISTS(SELECT 1 FROM ders_kriterleri k
                     WHERE k.ders_id=d.ders_id AND k.yil=?) ,
              EXISTS(SELECT 1 FROM performans p
                     WHERE p.ders_id=d.ders_id AND p.akademik_yil=?
                           AND p.basari_orani IS NOT NULL),
              EXISTS(SELECT 1 FROM populerlik o
                     WHERE o.ders_id=d.ders_id AND o.akademik_yil=?
                           AND o.doluluk_orani IS NOT NULL),
              -- Anket tiki kapsama ozetiyle TUTARLI olmali: yeni anket importu
              -- ders_kriterleri.anket_dersi_secen'e yazar; eski veri anket_sonuclari'nda
              -- olabilir. Ikisinden BIRI varsa anket vardir (aksi halde "girili ama tik yok").
              (EXISTS(SELECT 1 FROM ders_kriterleri ak
                      WHERE ak.ders_id=d.ders_id AND ak.yil=?
                            AND COALESCE(ak.anket_dersi_secen, 0) > 0)
               OR EXISTS(SELECT 1 FROM anket_sonuclari a
                         WHERE a.ders_id=d.ders_id AND a.oy_sayisi>0)),
              (SELECT COUNT(DISTINCT akademik_yil) FROM performans p2
                     WHERE p2.ders_id=d.ders_id) >= 2
            FROM ders d
            WHERE 1=1 {fac}
            ORDER BY d.kod, d.ad
            """,
            (int(year), int(year), int(year), int(year)),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError as exc:
        conn.close()
        raise RuntimeError(f"Eksik veri sorgusu basarisiz: {exc}") from exc
    else:
        conn.close()

    result: list[dict[str, Any]] = []
    for r in rows:
        crit, perf, pop, srv, trend = bool(r[3]), bool(r[4]), bool(r[5]), bool(r[6]), bool(r[7])
        if crit and perf and pop and srv and trend:
            continue  # tam dersleri atla
        result.append({
            "ders_id": r[0],
            "kod": r[1],
            "ad": r[2],
            "criteria": crit,
            "performance": perf,
            "popularity": pop,
            "survey": srv,
            "trend": trend,
        })
    return result


def get_validation_issues(
    db_path: Optional[str],
    year: int,
    faculty_id: Optional[int] = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Dogrulama sorunlarini (criteria_validation_issues, yoksa
    data_validation_issues fallback) severity sirali doner."""
    from app.db.session import open_sqlite_connection

    conn = open_sqlite_connection(db_path or None, row_factory=True)
    try:
        cur = conn.cursor()
        fac = f"AND faculty_id = {int(faculty_id)}" if faculty_id else ""
        rows = []
        try:
            cur.execute(
                f"""
                SELECT id, COALESCE(issue_type,''), COALESCE(severity,''),
                       COALESCE(message,''), COALESCE(criterion_key,''),
                       COALESCE(created_at,'')
                FROM criteria_validation_issues
                WHERE year = ? {fac}
                ORDER BY CASE severity WHEN 'critical' THEN 0
                         WHEN 'warning' THEN 1 ELSE 2 END, id
                LIMIT {int(limit)}
                """,
                (int(year),),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            cur.execute(
                f"""
                SELECT id, COALESCE(issue_type,''), COALESCE(severity,''),
                       COALESCE(message,''), COALESCE(field_name,''),
                       COALESCE(created_at,'')
                FROM data_validation_issues
                WHERE is_resolved = 0
                ORDER BY id LIMIT {int(limit)}
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r[0],
            "issue_type": r[1],
            "severity": r[2],
            "message": r[3],
            "key": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


def build_quality_report(
    db_path: Optional[str],
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> dict[str, Any]:
    """Tam veri kalitesi raporu: readiness + coverage + eksik matris + sorunlar.

    Tek baglantida hesaplar; UI yalnizca sonucu render eder.
    """
    from app.db.session import open_sqlite_connection

    conn = open_sqlite_connection(db_path or None, row_factory=True)
    try:
        cur = conn.cursor()
        readiness = assess_data_readiness_cursor(cur, year, faculty_id, department_id)
        coverage = generate_coverage_report_cursor(cur, year, faculty_id, department_id)
    finally:
        conn.close()

    return {
        "year": int(year),
        "faculty_id": faculty_id,
        "readiness": readiness,
        "coverage": coverage,
        "missing_data": get_missing_data_matrix(db_path, year, faculty_id),
        "validation_issues": get_validation_issues(db_path, year, faculty_id),
    }


def save_data_coverage_report(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
    coverage_data: Optional[dict[str, Any]] = None,
) -> int:
    """
    Kapsama raporunu data_coverage_reports tablosuna kaydet.

    Returns:
        Report ID
    """
    if coverage_data is None:
        coverage_data = generate_coverage_report_cursor(cur, year, faculty_id, department_id, semester)

    try:
        from app.db.schema_compat import ensure_data_quality_schema

        ensure_data_quality_schema(cur.connection)
    except Exception:
        pass

    total_courses = int(coverage_data.get('total_courses') or 0)
    courses_with_criteria = int(coverage_data.get('courses_with_criteria') or 0)
    courses_with_performance = int(coverage_data.get('courses_with_performance') or 0)
    courses_with_popularity = int(coverage_data.get('courses_with_popularity') or 0)
    courses_with_survey = int(coverage_data.get('courses_with_survey') or 0)
    coverage_ratio = float(coverage_data.get('coverage_percentage') or 0.0) / 100.0
    scope_type = "department" if department_id is not None else ("faculty" if faculty_id is not None else "global")

    def ratio(value: int) -> float:
        return round(value / total_courses, 4) if total_courses else 0.0

    try:
        cur.execute(
            """
            INSERT INTO data_coverage_reports (
                scope_type, faculty_id, department_id, year, semester,
                total_courses, courses_with_criteria, courses_with_performance,
                courses_with_popularity, courses_with_survey, courses_with_score,
                courses_with_trend_data, criteria_coverage_ratio,
                performance_coverage_ratio, popularity_coverage_ratio,
                survey_coverage_ratio, score_coverage_ratio, trend_coverage_ratio,
                overall_coverage_score, missing_data_summary_json,
                recommendations_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope_type,
                int(faculty_id) if faculty_id else None,
                int(department_id) if department_id else None,
                int(year),
                str(semester) if semester else None,
                total_courses,
                courses_with_criteria,
                courses_with_performance,
                courses_with_popularity,
                courses_with_survey,
                0,
                0,
                ratio(courses_with_criteria),
                ratio(courses_with_performance),
                ratio(courses_with_popularity),
                ratio(courses_with_survey),
                0.0,
                0.0,
                round(coverage_ratio, 4),
                _json_dump(coverage_data),
                _json_dump([]),
                _now(),
            ),
        )
        return int(cur.lastrowid or 0)
    except sqlite3.OperationalError:
        return 0

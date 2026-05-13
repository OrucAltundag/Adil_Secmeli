# -*- coding: utf-8 -*-
"""Integrate the user-provided dataset bundle into the local SQLite system.

This importer is intentionally non-destructive for master data: it upserts
faculties, departments, courses, criteria, performance, popularity, survey
summaries, and benchmark CSV files without clearing the main tables.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "imports" / "files_20260512_2124"
DEFAULT_DB = PROJECT_ROOT / "data" / "adil_secmeli.db"
BENCHMARK_RAW_DIR = PROJECT_ROOT / "data" / "benchmark" / "raw_real"
REPORTS_DIR = PROJECT_ROOT / "reports"


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ş": "s",
        "ö": "o",
        "ü": "u",
        "ç": "c",
        "İ": "i",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text)
    return text


def clean_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def clean_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def clean_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_term(value: Any) -> str:
    text = normalize_text(value)
    if text.startswith("b"):
        return "Bahar"
    return "Güz"


def is_elective(value: Any) -> bool:
    return "secmeli" in normalize_text(value)


def parse_teaching_hours(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.match(r"^\s*(\d+)", text)
    if not match:
        return None
    return int(match.group(1))


def table_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    return {str(row[1]) for row in cur.execute(f"PRAGMA table_info({table})")}


def fetch_name_map(cur: sqlite3.Cursor, table: str, id_column: str, extra_where: str = "", params: tuple[Any, ...] = ()) -> dict[str, int]:
    rows = cur.execute(f"SELECT {id_column}, ad FROM {table} {extra_where}", params).fetchall()
    return {normalize_text(row[1]): int(row[0]) for row in rows if row[1] is not None}


def get_or_create_faculty(cur: sqlite3.Cursor, name: str, stats: dict[str, int]) -> int:
    normalized = normalize_text(name)
    faculty_map = fetch_name_map(cur, "fakulte", "fakulte_id")
    if normalized in faculty_map:
        return faculty_map[normalized]
    cur.execute("INSERT INTO fakulte (ad) VALUES (?)", (name.strip(),))
    stats["faculties_created"] += 1
    return int(cur.lastrowid)


def get_or_create_department(cur: sqlite3.Cursor, faculty_id: int, name: str, stats: dict[str, int]) -> int:
    normalized = normalize_text(name)
    dept_map = fetch_name_map(cur, "bolum", "bolum_id", "WHERE fakulte_id = ?", (faculty_id,))
    if normalized in dept_map:
        return dept_map[normalized]
    cur.execute("INSERT INTO bolum (fakulte_id, ad) VALUES (?, ?)", (faculty_id, name.strip()))
    stats["departments_created"] += 1
    return int(cur.lastrowid)


def find_course_id(cur: sqlite3.Cursor, code: str | None = None, name: str | None = None, department_id: int | None = None) -> int | None:
    if code:
        row = cur.execute(
            "SELECT ders_id FROM ders WHERE lower(trim(kod)) = lower(trim(?)) ORDER BY ders_id LIMIT 1",
            (code.strip(),),
        ).fetchone()
        if row:
            return int(row[0])
        return None
    if name and department_id is not None:
        row = cur.execute(
            """
            SELECT ders_id FROM ders
            WHERE bolum_id = ? AND lower(trim(ad)) = lower(trim(?))
            ORDER BY ders_id LIMIT 1
            """,
            (department_id, name.strip()),
        ).fetchone()
        if row:
            return int(row[0])
    if name:
        row = cur.execute(
            "SELECT ders_id FROM ders WHERE lower(trim(ad)) = lower(trim(?)) ORDER BY ders_id LIMIT 1",
            (name.strip(),),
        ).fetchone()
        if row:
            return int(row[0])
    return None


def upsert_course(
    cur: sqlite3.Cursor,
    *,
    faculty_id: int,
    department_id: int,
    code: str | None,
    name: str,
    credit: int | None,
    ects: int | None,
    course_type: str | None,
    content: str | None,
    stats: dict[str, int],
) -> int:
    course_id = find_course_id(cur, code=code, name=name, department_id=department_id)
    payload = {
        "bolum_id": department_id,
        "fakulte_id": faculty_id,
        "ad": name,
        "kredi": credit,
        "akts": ects,
        "bilgi": content,
        "alan": None,
        "status": 1,
        "DersTipi": course_type,
        "kod": code,
    }
    if course_id is None:
        cur.execute(
            """
            INSERT INTO ders (bolum_id, fakulte_id, ad, kredi, akts, bilgi, alan, status, DersTipi, kod)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["bolum_id"],
                payload["fakulte_id"],
                payload["ad"],
                payload["kredi"],
                payload["akts"],
                payload["bilgi"],
                payload["alan"],
                payload["status"],
                payload["DersTipi"],
                payload["kod"],
            ),
        )
        stats["courses_created"] += 1
        return int(cur.lastrowid)

    cur.execute(
        """
        UPDATE ders
        SET bolum_id = ?, fakulte_id = ?, ad = ?,
            kredi = COALESCE(?, kredi),
            akts = COALESCE(?, akts),
            bilgi = COALESCE(?, bilgi),
            status = COALESCE(status, 1),
            DersTipi = COALESCE(?, DersTipi),
            kod = COALESCE(?, kod)
        WHERE ders_id = ?
        """,
        (
            payload["bolum_id"],
            payload["fakulte_id"],
            payload["ad"],
            payload["kredi"],
            payload["akts"],
            payload["bilgi"],
            payload["DersTipi"],
            payload["kod"],
            course_id,
        ),
    )
    stats["courses_updated"] += 1
    return course_id


def load_master_courses(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> dict[str, int]:
    path = source_dir / "dersler_master_temiz.xlsx"
    df = pd.read_excel(path, sheet_name="Tüm Dersler")
    code_to_id: dict[str, int] = {}
    for _, row in df.iterrows():
        faculty = clean_text(row.get("FakülteAdı"))
        department = clean_text(row.get("BölümAdı"))
        name = clean_text(row.get("DersAdı"))
        code = clean_text(row.get("DersID"))
        if not faculty or not department or not name:
            stats["master_rows_skipped"] += 1
            continue
        faculty_id = get_or_create_faculty(cur, faculty, stats)
        department_id = get_or_create_department(cur, faculty_id, department, stats)
        course_id = upsert_course(
            cur,
            faculty_id=faculty_id,
            department_id=department_id,
            code=code,
            name=name,
            credit=parse_teaching_hours(row.get("T+U")),
            ects=clean_int(row.get("AKTS")),
            course_type=clean_text(row.get("DersTipi")),
            content=clean_text(row.get("Icerik")),
            stats=stats,
        )
        if code:
            code_to_id[normalize_text(code)] = course_id
    stats["master_rows_processed"] += int(len(df))
    return code_to_id


def resolve_scope_and_course(cur: sqlite3.Cursor, row: pd.Series, stats: dict[str, int]) -> tuple[int, int, int] | None:
    faculty = clean_text(row.get("fakulte") or row.get("fakulte_adi") or row.get("FakülteAdı"))
    department = clean_text(row.get("bolum") or row.get("BölümAdı"))
    code = clean_text(row.get("ders_kodu") or row.get("DersID") or row.get("Kod"))
    name = clean_text(row.get("ders_adi") or row.get("DersAdı"))
    if not faculty or not department or not name:
        stats["scope_rows_skipped"] += 1
        return None
    faculty_id = get_or_create_faculty(cur, faculty, stats)
    department_id = get_or_create_department(cur, faculty_id, department, stats)
    course_id = find_course_id(cur, code=code, name=name, department_id=department_id)
    if course_id is None:
        course_id = upsert_course(
            cur,
            faculty_id=faculty_id,
            department_id=department_id,
            code=code,
            name=name,
            credit=clean_int(row.get("kredi")),
            ects=clean_int(row.get("akts")),
            course_type=clean_text(row.get("zorunlu_secmeli")),
            content=None,
            stats=stats,
        )
        stats["courses_created_from_scoped_files"] += 1
    return faculty_id, department_id, course_id


def replace_curriculum_scope(
    cur: sqlite3.Cursor,
    faculty_id: int,
    department_id: int,
    year: int,
    term: str,
    course_ids: list[int],
) -> tuple[int, int]:
    existing = [
        int(row[0])
        for row in cur.execute(
            """
            SELECT mufredat_id FROM mufredat
            WHERE fakulte_id = ? AND bolum_id = ? AND akademik_yil = ? AND donem = ?
            ORDER BY COALESCE(versiyon, 0) DESC, mufredat_id DESC
            """,
            (faculty_id, department_id, year, term),
        ).fetchall()
    ]
    if existing:
        keep_id = existing[0]
        cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (keep_id,))
        for extra_id in existing[1:]:
            cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (extra_id,))
            cur.execute("DELETE FROM mufredat WHERE mufredat_id = ?", (extra_id,))
    else:
        cur.execute(
            """
            INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (faculty_id, department_id, year, term, "dataset_bundle", 1),
        )
        keep_id = int(cur.lastrowid)

    linked = 0
    for course_id in dict.fromkeys(course_ids):
        cur.execute(
            "INSERT OR IGNORE INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
            (keep_id, int(course_id)),
        )
        linked += 1
    return keep_id, linked


def upsert_pool_row(
    cur: sqlite3.Cursor,
    *,
    course_id: int,
    faculty_id: int,
    department_id: int,
    year: int,
    term: str,
    course_name: str | None,
    stats: dict[str, int],
) -> None:
    row = cur.execute(
        """
        SELECT id FROM havuz
        WHERE CAST(ders_id AS TEXT) = CAST(? AS TEXT)
          AND fakulte_id = ?
          AND yil = ?
        LIMIT 1
        """,
        (str(course_id), faculty_id, year),
    ).fetchone()
    if row:
        cur.execute(
            """
            UPDATE havuz
            SET bolum_id = ?,
                ders_adi = COALESCE(?, ders_adi),
                donem = COALESCE(donem, ?),
                statu = COALESCE(statu, 0)
            WHERE id = ?
            """,
            (department_id, course_name, term, int(row[0])),
        )
        stats["pool_rows_updated"] += 1
        return
    cur.execute(
        """
        INSERT INTO havuz (
            ders_id, yil, fakulte_id, bolum_id, alan, statu, sayac, skor,
            ders_adi, donem, approval_required
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (str(course_id), year, faculty_id, department_id, None, 0, 0, 0, course_name, term, 0),
    )
    stats["pool_rows_created"] += 1


def load_curriculum(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> None:
    path = source_dir / "mufredat_veri_seti.xlsx"
    df = pd.read_excel(path, sheet_name="mufredat")
    grouped: dict[tuple[int, int, int, str], list[int]] = defaultdict(list)
    for _, row in df.iterrows():
        resolved = resolve_scope_and_course(cur, row, stats)
        year = clean_int(row.get("akademik_yil"))
        if resolved is None or year is None:
            stats["curriculum_rows_skipped"] += 1
            continue
        faculty_id, department_id, course_id = resolved
        term = normalize_term(row.get("donem"))
        grouped[(faculty_id, department_id, year, term)].append(course_id)
        cur.execute(
            """
            UPDATE ders
            SET kredi = COALESCE(?, kredi),
                akts = COALESCE(?, akts),
                DersTipi = COALESCE(?, DersTipi)
            WHERE ders_id = ?
            """,
            (
                clean_int(row.get("kredi")),
                clean_int(row.get("akts")),
                clean_text(row.get("zorunlu_secmeli")),
                course_id,
            ),
        )
        if is_elective(row.get("zorunlu_secmeli")):
            upsert_pool_row(
                cur,
                course_id=course_id,
                faculty_id=faculty_id,
                department_id=department_id,
                year=year,
                term=term,
                course_name=clean_text(row.get("ders_adi")),
                stats=stats,
            )

    for (faculty_id, department_id, year, term), course_ids in grouped.items():
        _, linked = replace_curriculum_scope(cur, faculty_id, department_id, year, term, course_ids)
        stats["curriculum_scopes_updated"] += 1
        stats["curriculum_links_written"] += linked
    stats["curriculum_rows_processed"] += int(len(df))


def upsert_by_key(
    cur: sqlite3.Cursor,
    table: str,
    key_where: str,
    key_params: tuple[Any, ...],
    insert_sql: str,
    insert_params: tuple[Any, ...],
    update_sql: str,
    update_params: tuple[Any, ...],
) -> bool:
    row = cur.execute(f"SELECT 1 FROM {table} WHERE {key_where} LIMIT 1", key_params).fetchone()
    if row:
        cur.execute(update_sql, update_params)
        return False
    cur.execute(insert_sql, insert_params)
    return True


def load_criteria(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> None:
    path = source_dir / "kriter_veri_seti.xlsx"
    df = pd.read_excel(path, sheet_name="ders_kriterleri")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    faculty_totals: dict[tuple[str, int, str], int] = defaultdict(int)
    for _, row in df.iterrows():
        faculty = normalize_text(row.get("fakulte"))
        year = clean_int(row.get("yil"))
        term = normalize_term(row.get("donem"))
        faculty_totals[(faculty, int(year or 0), term)] += int(clean_int(row.get("kayitli_ogrenci"), 0) or 0)

    for _, row in df.iterrows():
        resolved = resolve_scope_and_course(cur, row, stats)
        year = clean_int(row.get("yil"))
        if resolved is None or year is None:
            stats["criteria_rows_skipped"] += 1
            continue
        faculty_id, _, course_id = resolved
        term = normalize_term(row.get("donem"))
        total = clean_int(row.get("toplam_ogrenci"), 0) or 0
        passed = clean_int(row.get("gecen_ogrenci"), 0) or 0
        average = clean_float(row.get("basari_ortalamasi"), 0.0) or 0.0
        capacity = clean_int(row.get("kontenjan"), 0) or 0
        enrolled = clean_int(row.get("kayitli_ogrenci"), 0) or 0
        survey_count = clean_int(row.get("anket_katilimci"), 0) or 0
        survey_selected = clean_int(row.get("anket_dersi_secen"), 0) or 0
        success_rate = passed / total if total > 0 else 0.0
        fill_rate = min(enrolled / capacity, 1.0) if capacity > 0 else 0.0
        faculty_total = faculty_totals[(normalize_text(row.get("fakulte")), year, term)]
        interest_rate = enrolled / faculty_total if faculty_total > 0 else 0.0

        inserted = upsert_by_key(
            cur,
            "ders_kriterleri",
            "ders_id = ? AND yil = ? AND donem = ?",
            (course_id, year, term),
            """
            INSERT INTO ders_kriterleri (
                ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
                basari_ortalamasi, kontenjan, kayitli_ogrenci,
                anket_katilimci, anket_dersi_secen, anket_veri_kaynagi,
                criteria_veri_kaynagi, criteria_updated_at, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                course_id,
                year,
                term,
                total,
                passed,
                average,
                capacity,
                enrolled,
                survey_count,
                survey_selected,
                "dataset_bundle",
                "dataset_bundle",
                now,
            ),
            """
            UPDATE ders_kriterleri
            SET toplam_ogrenci = ?, gecen_ogrenci = ?, basari_ortalamasi = ?,
                kontenjan = ?, kayitli_ogrenci = ?, anket_katilimci = ?,
                anket_dersi_secen = ?, anket_veri_kaynagi = ?,
                criteria_veri_kaynagi = ?, criteria_updated_at = ?, is_active = 1
            WHERE ders_id = ? AND yil = ? AND donem = ?
            """,
            (
                total,
                passed,
                average,
                capacity,
                enrolled,
                survey_count,
                survey_selected,
                "dataset_bundle",
                "dataset_bundle",
                now,
                course_id,
                year,
                term,
            ),
        )
        stats["criteria_rows_created" if inserted else "criteria_rows_updated"] += 1

        inserted_perf = upsert_by_key(
            cur,
            "performans",
            "ders_id = ? AND akademik_yil = ? AND donem = ?",
            (course_id, year, term),
            """
            INSERT INTO performans (ders_id, akademik_yil, donem, ortalama_not, basari_orani, ham_puan)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (course_id, year, term, average, success_rate, average),
            """
            UPDATE performans
            SET ortalama_not = ?, basari_orani = ?, ham_puan = ?
            WHERE ders_id = ? AND akademik_yil = ? AND donem = ?
            """,
            (average, success_rate, average, course_id, year, term),
        )
        stats["performance_rows_created" if inserted_perf else "performance_rows_updated"] += 1

        inserted_pop = upsert_by_key(
            cur,
            "populerlik",
            "ders_id = ? AND akademik_yil = ? AND donem = ?",
            (course_id, year, term),
            """
            INSERT INTO populerlik (
                ders_id, akademik_yil, donem, talep_sayisi, kontenjan,
                fakulte_mevcudu, doluluk_orani, ilgi_orani, ham_puan
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (course_id, year, term, enrolled, capacity, faculty_total, fill_rate, interest_rate, fill_rate),
            """
            UPDATE populerlik
            SET talep_sayisi = ?, kontenjan = ?, fakulte_mevcudu = ?,
                doluluk_orani = ?, ilgi_orani = ?, ham_puan = ?
            WHERE ders_id = ? AND akademik_yil = ? AND donem = ?
            """,
            (enrolled, capacity, faculty_total, fill_rate, interest_rate, fill_rate, course_id, year, term),
        )
        stats["popularity_rows_created" if inserted_pop else "popularity_rows_updated"] += 1
    stats["criteria_rows_processed"] += int(len(df))


def get_or_create_survey_form(cur: sqlite3.Cursor, faculty_id: int, year: int) -> int:
    name = f"Dataset Bundle Anket {year}"
    row = cur.execute(
        """
        SELECT form_id FROM anket_form
        WHERE ad = ? AND akademik_yil = ? AND donem = ? AND fakulte_id = ?
        LIMIT 1
        """,
        (name, year, "Genel", faculty_id),
    ).fetchone()
    if row:
        return int(row[0])
    cur.execute(
        """
        INSERT INTO anket_form (ad, akademik_yil, donem, fakulte_id, aktif_mi, aciklama)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, year, "Genel", faculty_id, 1, "files.zip anket_tercih_veri_seti.xlsx aktarımı"),
    )
    return int(cur.lastrowid)


def load_survey_summary(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> None:
    path = source_dir / "anket_tercih_veri_seti.xlsx"
    df = pd.read_excel(path, sheet_name="anket_sonuclari")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    max_by_scope: dict[tuple[str, int], int] = defaultdict(int)
    for _, row in df.iterrows():
        scope = (normalize_text(row.get("fakulte_adi")), int(clean_int(row.get("yil"), 0) or 0))
        max_by_scope[scope] = max(max_by_scope[scope], int(clean_int(row.get("oy_miktari"), 0) or 0))

    for _, row in df.iterrows():
        resolved = resolve_scope_and_course(cur, row, stats)
        year = clean_int(row.get("yil"))
        if resolved is None or year is None:
            stats["survey_rows_skipped"] += 1
            continue
        faculty_id, _, course_id = resolved
        votes = clean_int(row.get("oy_miktari"), 0) or 0
        form_id = get_or_create_survey_form(cur, faculty_id, year)
        max_votes = max_by_scope[(normalize_text(row.get("fakulte_adi")), year)]
        normalized = votes / max_votes if max_votes > 0 else 0.0

        row_exists = cur.execute(
            "SELECT 1 FROM anket_sonuclari WHERE form_id = ? AND ders_id = ? LIMIT 1",
            (form_id, course_id),
        ).fetchone()
        if row_exists:
            cur.execute(
                """
                UPDATE anket_sonuclari
                SET toplam_puan = ?, oy_sayisi = ?, ortalama_siddet = ?, a_norm = ?, hesaplanma_tarihi = ?
                WHERE form_id = ? AND ders_id = ?
                """,
                (float(votes), votes, normalized * 5.0, normalized, now, form_id, course_id),
            )
            stats["survey_results_updated"] += 1
        else:
            cur.execute(
                """
                INSERT INTO anket_sonuclari (
                    ders_id, form_id, toplam_puan, oy_sayisi, ortalama_siddet, a_norm, hesaplanma_tarihi
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (course_id, form_id, float(votes), votes, normalized * 5.0, normalized, now),
            )
            stats["survey_results_created"] += 1

        cur.execute(
            """
            UPDATE ders_kriterleri
            SET anket_dersi_secen = CASE
                    WHEN COALESCE(anket_dersi_secen, 0) = 0 THEN ?
                    ELSE anket_dersi_secen
                END,
                anket_veri_kaynagi = CASE
                    WHEN COALESCE(anket_dersi_secen, 0) = 0 THEN 'dataset_bundle_survey'
                    ELSE anket_veri_kaynagi
                END,
                anket_imported_at = COALESCE(anket_imported_at, ?)
            WHERE ders_id = ? AND yil = ?
            """,
            (votes, now, course_id, year),
        )
    stats["survey_rows_processed"] += int(len(df))


def copy_benchmark_csvs(source_dir: Path, stats: dict[str, int]) -> None:
    BENCHMARK_RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename in ["students.csv", "courses.csv", "preferences.csv", "survey_responses.csv", "allocations.csv"]:
        src = source_dir / filename
        dst = BENCHMARK_RAW_DIR / filename
        if not src.exists():
            stats["benchmark_csv_missing"] += 1
            continue
        shutil.copy2(src, dst)
        stats["benchmark_csv_copied"] += 1


def make_backup(db_path: Path) -> Path:
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_pre_dataset_import_{stamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def count_table(cur: sqlite3.Cursor, table: str) -> int:
    return int(cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def integrate(source_dir: Path, db_path: Path, *, backup: bool = True) -> dict[str, Any]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Dataset klasörü bulunamadı: {source_dir}")
    if not db_path.exists():
        raise FileNotFoundError(f"Veritabanı bulunamadı: {db_path}")

    stats: dict[str, int] = defaultdict(int)
    backup_path = make_backup(db_path) if backup else None
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        before = {
            table: count_table(cur, table)
            for table in ["fakulte", "bolum", "ders", "mufredat", "mufredat_ders", "havuz", "ders_kriterleri", "performans", "populerlik", "anket_sonuclari"]
        }
        load_master_courses(cur, source_dir, stats)
        load_curriculum(cur, source_dir, stats)
        load_criteria(cur, source_dir, stats)
        load_survey_summary(cur, source_dir, stats)
        copy_benchmark_csvs(source_dir, stats)
        conn.commit()
        after = {
            table: count_table(cur, table)
            for table in ["fakulte", "bolum", "ders", "mufredat", "mufredat_ders", "havuz", "ders_kriterleri", "performans", "populerlik", "anket_sonuclari"]
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    payload = {
        "source_dir": str(source_dir),
        "db_path": str(db_path),
        "backup_path": str(backup_path) if backup_path else None,
        "stats": dict(sorted(stats.items())),
        "before": before,
        "after": after,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"dataset_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Integrate files.zip dataset bundle into Adil Secmeli SQLite DB.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE), help="Extracted dataset bundle directory.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB), help="SQLite database path.")
    parser.add_argument("--no-backup", action="store_true", help="Skip DB backup before import.")
    args = parser.parse_args()

    payload = integrate(Path(args.source_dir), Path(args.db_path), backup=not args.no_backup)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

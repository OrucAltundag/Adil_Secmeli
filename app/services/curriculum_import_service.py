from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import re
import sqlite3
from typing import Any

import pandas as pd


DONEM_GUZ = "Guz"
DONEM_BAHAR = "Bahar"


def normalize_term(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if value.startswith("b"):
        return DONEM_BAHAR
    return DONEM_GUZ


def _normalize_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ş": "s",
        "ö": "o",
        "ü": "u",
        "ç": "c",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"\s+", " ", text)
    return text


def _find_col(columns: list[str], *candidates: str) -> str | None:
    norm_map = {_normalize_text(col): col for col in columns}
    for cand in candidates:
        key = _normalize_text(cand)
        if key in norm_map:
            return norm_map[key]
    return None


def _extract_rows_from_df(df: pd.DataFrame, sheet_name: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []

    col_fak = _find_col(list(df.columns), "Fakulte", "Fakülte", "Faculty")
    col_bol = _find_col(list(df.columns), "Bolum", "Bölüm", "Department")
    col_yil = _find_col(list(df.columns), "Yil", "Yıl", "Akademik Yil", "Akademik Yıl", "Year")
    col_don = _find_col(list(df.columns), "Donem", "Dönem", "Term", "Semester")
    col_ders_adi = _find_col(list(df.columns), "Ders Adi", "Ders Adı", "Course Name")
    col_ders_kod = _find_col(list(df.columns), "Ders Kodu", "Kod", "Course Code")

    if not (col_fak and col_bol and col_yil):
        warnings.append(f"{sheet_name}: gerekli kolonlar yok (fakulte/bolum/yil)")
        return rows, warnings

    # row-based format
    if col_ders_adi or col_ders_kod:
        for idx, row in df.iterrows():
            fakulte = row.get(col_fak)
            bolum = row.get(col_bol)
            yil = row.get(col_yil)
            term = row.get(col_don) if col_don else None
            ders_adi = row.get(col_ders_adi) if col_ders_adi else None
            ders_kodu = row.get(col_ders_kod) if col_ders_kod else None

            if pd.isna(fakulte) or pd.isna(bolum) or pd.isna(yil):
                continue
            if pd.isna(ders_adi) and pd.isna(ders_kodu):
                continue

            yil_num = _parse_year(yil)
            if yil_num is None:
                warnings.append(f"{sheet_name}[{idx}]: yil parse edilemedi -> {yil}")
                continue

            if pd.isna(term):
                # Sheet adindan term cikar.
                term = DONEM_BAHAR if "bahar" in _normalize_text(sheet_name) else DONEM_GUZ

            rows.append(
                {
                    "fakulte": str(fakulte).strip(),
                    "bolum": str(bolum).strip(),
                    "yil": yil_num,
                    "donem": normalize_term(str(term)),
                    "ders_adi": None if pd.isna(ders_adi) else str(ders_adi).strip(),
                    "ders_kodu": None if pd.isna(ders_kodu) else str(ders_kodu).strip(),
                    "sheet": sheet_name,
                }
            )
        return rows, warnings

    # wide format fallback: secmeli ders 1..12
    ders_cols = [col for col in df.columns if "ders" in _normalize_text(col)]
    for idx, row in df.iterrows():
        fakulte = row.get(col_fak)
        bolum = row.get(col_bol)
        yil = row.get(col_yil)
        term = row.get(col_don) if col_don else None
        if pd.isna(fakulte) or pd.isna(bolum) or pd.isna(yil):
            continue
        yil_num = _parse_year(yil)
        if yil_num is None:
            warnings.append(f"{sheet_name}[{idx}]: yil parse edilemedi -> {yil}")
            continue
        if pd.isna(term):
            term = DONEM_BAHAR if "bahar" in _normalize_text(sheet_name) else DONEM_GUZ

        for dc in ders_cols:
            ders_adi = row.get(dc)
            if pd.isna(ders_adi) or str(ders_adi).strip() == "":
                continue
            rows.append(
                {
                    "fakulte": str(fakulte).strip(),
                    "bolum": str(bolum).strip(),
                    "yil": yil_num,
                    "donem": normalize_term(str(term)),
                    "ders_adi": str(ders_adi).strip(),
                    "ders_kodu": None,
                    "sheet": sheet_name,
                }
            )
    return rows, warnings


def _parse_year(raw: Any) -> int | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip()
    found = re.search(r"(19|20)\d{2}", text)
    if found:
        return int(found.group())
    if text.isdigit():
        year = int(text)
        if 1900 <= year <= 2100:
            return year
    return None


def parse_curriculum_excel(excel_path: str) -> tuple[list[dict[str, Any]], list[str]]:
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel dosyasi bulunamadi: {excel_path}")
    xls = pd.ExcelFile(excel_path)
    all_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet_name=sheet)
        rows, warns = _extract_rows_from_df(df, sheet_name=sheet)
        all_rows.extend(rows)
        warnings.extend(warns)
    return all_rows, warnings


def _find_faculty_id(cur: sqlite3.Cursor, faculty_name: str) -> int | None:
    cur.execute("SELECT fakulte_id FROM fakulte WHERE lower(trim(ad)) = lower(trim(?)) LIMIT 1", (faculty_name,))
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute("SELECT fakulte_id FROM fakulte WHERE lower(ad) LIKE lower(?) LIMIT 1", (f"%{faculty_name.strip()}%",))
    row = cur.fetchone()
    return int(row[0]) if row else None


def _find_department_id(cur: sqlite3.Cursor, faculty_id: int, department_name: str) -> int | None:
    cur.execute(
        """
        SELECT bolum_id
        FROM bolum
        WHERE fakulte_id = ? AND lower(trim(ad)) = lower(trim(?))
        LIMIT 1
        """,
        (int(faculty_id), department_name),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        """
        SELECT bolum_id
        FROM bolum
        WHERE fakulte_id = ? AND lower(ad) LIKE lower(?)
        LIMIT 1
        """,
        (int(faculty_id), f"%{department_name.strip()}%"),
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def _find_course_id(cur: sqlite3.Cursor, ders_adi: str | None, ders_kodu: str | None) -> int | None:
    code = str(ders_kodu or "").strip()
    name = str(ders_adi or "").strip()

    if code:
        cur.execute("SELECT ders_id FROM ders WHERE lower(trim(kod)) = lower(trim(?)) LIMIT 1", (code,))
        row = cur.fetchone()
        if row:
            return int(row[0])

    if name:
        cur.execute("SELECT ders_id FROM ders WHERE lower(trim(ad)) = lower(trim(?)) LIMIT 1", (name,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur.execute("SELECT ders_id FROM ders WHERE lower(ad) LIKE lower(?) LIMIT 1", (f"%{name}%",))
        row = cur.fetchone()
        if row:
            return int(row[0])
    return None


def _get_or_create_scope_mufredat_id(
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
        """,
        (int(faculty_id), int(department_id), int(year), "b" if term == DONEM_BAHAR else "g"),
    )
    rows = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]
    if rows:
        keep_id = rows[0]
        for drop_id in rows[1:]:
            cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (int(drop_id),))
            cur.execute("DELETE FROM mufredat WHERE mufredat_id = ?", (int(drop_id),))
        return keep_id

    cur.execute("SELECT COALESCE(MAX(versiyon), 0) FROM mufredat WHERE bolum_id = ?", (int(department_id),))
    version = int((cur.fetchone() or [0])[0] or 0) + 1
    cur.execute(
        """
        INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon)
        VALUES (?, ?, ?, ?, 'Excel Upload', ?)
        """,
        (int(faculty_id), int(department_id), int(year), term, int(version)),
    )
    return int(cur.lastrowid)


def _fetch_scope_courses(cur: sqlite3.Cursor, mufredat_id: int) -> set[int]:
    cur.execute("SELECT ders_id FROM mufredat_ders WHERE mufredat_id = ?", (int(mufredat_id),))
    return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}


@dataclass
class ImportResult:
    ok: bool
    message: str
    target_year: int
    scopes_total: int = 0
    scopes_created: int = 0
    scopes_updated: int = 0
    scopes_unchanged: int = 0
    links_added: int = 0
    links_removed: int = 0
    warnings: list[str] | None = None
    errors: list[str] | None = None
    compare: list[dict[str, Any]] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def import_curriculum_excel(
    db_path: str,
    excel_path: str,
    target_year: int = 2022,
) -> dict[str, Any]:
    if not os.path.exists(db_path):
        return ImportResult(False, "Veritabani bulunamadi.", target_year=target_year).as_dict()
    if not os.path.exists(excel_path):
        return ImportResult(False, "Excel dosyasi bulunamadi.", target_year=target_year).as_dict()

    parsed_rows, warnings = parse_curriculum_excel(excel_path)
    if not parsed_rows:
        return ImportResult(False, "Excel icinde aktarilabilir satir yok.", target_year=target_year, warnings=warnings).as_dict()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    errors: list[str] = []
    scope_courses: dict[tuple[int, int, int, str], set[int]] = {}
    scope_names: dict[tuple[int, int, int, str], tuple[str, str]] = {}

    try:
        for item in parsed_rows:
            year = int(item["yil"])
            if year != int(target_year):
                errors.append(f"Yalnizca {target_year} aktarimi desteklenir. Satir yili={year}")
                continue

            faculty_id = _find_faculty_id(cur, item["fakulte"])
            if faculty_id is None:
                errors.append(f"Fakulte bulunamadi: {item['fakulte']}")
                continue
            department_id = _find_department_id(cur, faculty_id, item["bolum"])
            if department_id is None:
                errors.append(f"Bolum bulunamadi: {item['bolum']} (fakulte={item['fakulte']})")
                continue
            course_id = _find_course_id(cur, item.get("ders_adi"), item.get("ders_kodu"))
            if course_id is None:
                errors.append(f"Ders bulunamadi: kod={item.get('ders_kodu')} ad={item.get('ders_adi')}")
                continue

            scope = (int(faculty_id), int(department_id), int(year), normalize_term(item["donem"]))
            scope_courses.setdefault(scope, set()).add(int(course_id))
            scope_names[scope] = (item["fakulte"], item["bolum"])

        if errors:
            conn.rollback()
            return ImportResult(
                False,
                "Yukleme dogrulamasi basarisiz.",
                target_year=target_year,
                warnings=warnings,
                errors=errors,
            ).as_dict()

        # Cross-semester validation: ayni ders hem Guz hem Bahar'da olamaz.
        grouped_by_year_scope: dict[tuple[int, int, int], dict[str, set[int]]] = {}
        for (f_id, b_id, yil, term), ders_set in scope_courses.items():
            key = (f_id, b_id, yil)
            grouped_by_year_scope.setdefault(key, {DONEM_GUZ: set(), DONEM_BAHAR: set()})
            grouped_by_year_scope[key][term].update(ders_set)

        for (f_id, b_id, yil), term_map in grouped_by_year_scope.items():
            overlap = term_map[DONEM_GUZ] & term_map[DONEM_BAHAR]
            if overlap:
                placeholders = ",".join("?" for _ in overlap)
                cur.execute(f"SELECT ad FROM ders WHERE ders_id IN ({placeholders})", tuple(sorted(overlap)))
                overlap_names = [str(r[0]) for r in cur.fetchall()]
                errors.append(
                    f"Cross-semester ihlali (fakulte={f_id}, bolum={b_id}, yil={yil}): {', '.join(overlap_names)}"
                )

        if errors:
            conn.rollback()
            return ImportResult(
                False,
                "Cross-semester dogrulamasi basarisiz.",
                target_year=target_year,
                warnings=warnings,
                errors=errors,
            ).as_dict()

        created = 0
        updated = 0
        unchanged = 0
        links_added = 0
        links_removed = 0
        compare: list[dict[str, Any]] = []

        for scope, incoming_courses in sorted(scope_courses.items()):
            faculty_id, department_id, year, term = scope
            mufredat_id = _get_or_create_scope_mufredat_id(cur, faculty_id, department_id, year, term)
            existing_courses = _fetch_scope_courses(cur, mufredat_id)

            to_add = sorted(incoming_courses - existing_courses)
            to_remove = sorted(existing_courses - incoming_courses)

            if not existing_courses and incoming_courses:
                created += 1
            elif to_add or to_remove:
                updated += 1
            else:
                unchanged += 1

            for ders_id in to_remove:
                cur.execute(
                    "DELETE FROM mufredat_ders WHERE mufredat_id = ? AND ders_id = ?",
                    (int(mufredat_id), int(ders_id)),
                )
                links_removed += int(cur.rowcount or 0)

            for ders_id in to_add:
                cur.execute(
                    "INSERT OR IGNORE INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
                    (int(mufredat_id), int(ders_id)),
                )
                links_added += int(cur.rowcount or 0)

            faculty_name, department_name = scope_names.get(scope, (str(faculty_id), str(department_id)))
            compare.append(
                {
                    "fakulte": faculty_name,
                    "bolum": department_name,
                    "yil": year,
                    "donem": term,
                    "same": len(to_add) == 0 and len(to_remove) == 0,
                    "added_count": len(to_add),
                    "removed_count": len(to_remove),
                }
            )

        conn.commit()
        msg = (
            f"Yukleme tamamlandi. kapsam={len(scope_courses)}, olusturulan={created}, "
            f"guncellenen={updated}, ayni={unchanged}, eklenen_ders={links_added}, cikarilan_ders={links_removed}"
        )
        return ImportResult(
            True,
            msg,
            target_year=target_year,
            scopes_total=len(scope_courses),
            scopes_created=created,
            scopes_updated=updated,
            scopes_unchanged=unchanged,
            links_added=links_added,
            links_removed=links_removed,
            warnings=warnings,
            errors=[],
            compare=compare,
        ).as_dict()
    except Exception as exc:
        conn.rollback()
        return ImportResult(
            False,
            f"Yukleme hatasi: {exc}",
            target_year=target_year,
            warnings=warnings,
            errors=[str(exc)],
        ).as_dict()
    finally:
        conn.close()


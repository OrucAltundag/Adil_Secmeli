from __future__ import annotations

from dataclasses import dataclass
import re
import sqlite3

from app.services.course_type import build_elective_predicate


@dataclass(frozen=True)
class CourseCandidate:
    ders_id: int
    ders_kodu: str
    ders_adi: str
    in_year_scope: bool


@dataclass(frozen=True)
class CourseMatchResult:
    matched: bool
    ders_id: int | None = None
    ders_kodu: str | None = None
    ders_adi: str | None = None
    match_method: str | None = None
    error: str | None = None


def normalize_course_text(value: str | None) -> str:
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


def normalize_course_key(value: str | None) -> str:
    text = normalize_course_text(value)
    return re.sub(r"[^a-z0-9]+", "", text)


def _load_candidates(
    cur: sqlite3.Cursor,
    faculty_id: int,
    year: int,
    use_elective_filter: bool,
) -> list[CourseCandidate]:
    elective_predicate = "1=1"
    if use_elective_filter:
        elective_predicate = build_elective_predicate(cur=cur, alias="d")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('mufredat', 'mufredat_ders', 'bolum', 'havuz')")
    existing_tables = {str(row[0]) for row in cur.fetchall() if row and row[0]}
    year_scope_parts: list[str] = []
    params: list[int] = []

    if {"mufredat", "mufredat_ders", "bolum"}.issubset(existing_tables):
        year_scope_parts.append(
            """
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN bolum b ON b.bolum_id = m.bolum_id
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            WHERE b.fakulte_id = ?
              AND m.akademik_yil = ?
            """
        )
        params.extend([int(faculty_id), int(year)])

    if "havuz" in existing_tables:
        year_scope_parts.append(
            """
            SELECT DISTINCT CAST(h.ders_id AS INTEGER) AS ders_id
            FROM havuz h
            WHERE h.fakulte_id = ?
              AND h.yil = ?
            """
        )
        params.extend([int(faculty_id), int(year)])

    year_scope_query = " UNION ".join(year_scope_parts) if year_scope_parts else "SELECT NULL AS ders_id WHERE 1=0"

    query = f"""
        WITH year_scope AS (
            {year_scope_query}
        )
        SELECT DISTINCT
            d.ders_id,
            COALESCE(d.kod, '') AS ders_kodu,
            COALESCE(d.ad, '') AS ders_adi,
            CASE WHEN ys.ders_id IS NULL THEN 0 ELSE 1 END AS in_year_scope
        FROM ders d
        LEFT JOIN year_scope ys ON ys.ders_id = d.ders_id
        WHERE d.fakulte_id = ?
          AND {elective_predicate}
        ORDER BY
            CASE WHEN ys.ders_id IS NULL THEN 1 ELSE 0 END,
            d.ad,
            d.ders_id
    """
    params.append(int(faculty_id))
    cur.execute(query, tuple(params))
    return [
        CourseCandidate(
            ders_id=int(row[0]),
            ders_kodu=str(row[1] or ""),
            ders_adi=str(row[2] or ""),
            in_year_scope=bool(row[3]),
        )
        for row in cur.fetchall()
        if row and row[0] is not None
    ]


def load_faculty_course_candidates(
    cur: sqlite3.Cursor,
    faculty_id: int,
    year: int,
) -> list[CourseCandidate]:
    try:
        candidates = _load_candidates(cur=cur, faculty_id=faculty_id, year=year, use_elective_filter=True)
    except Exception:
        candidates = []

    if candidates:
        return candidates
    return _load_candidates(cur=cur, faculty_id=faculty_id, year=year, use_elective_filter=False)


def _select_candidate(matches: list[CourseCandidate]) -> tuple[CourseCandidate | None, str | None]:
    if not matches:
        return None, None
    if len(matches) == 1:
        return matches[0], None

    scoped = [item for item in matches if item.in_year_scope]
    if len(scoped) == 1:
        return scoped[0], None
    if len(scoped) > 1:
        return None, "Birden fazla ders yil kapsami icinde bulundu."
    return None, "Birden fazla ders bulundu."


def match_course_row(
    candidates: list[CourseCandidate],
    ders_kodu: str | None,
    ders_adi: str | None,
) -> CourseMatchResult:
    code_key = normalize_course_text(ders_kodu)
    name_key = normalize_course_text(ders_adi)
    loose_name_key = normalize_course_key(ders_adi)

    if code_key:
        code_matches = [item for item in candidates if normalize_course_text(item.ders_kodu) == code_key]
        selected, error = _select_candidate(code_matches)
        if selected:
            return CourseMatchResult(
                matched=True,
                ders_id=selected.ders_id,
                ders_kodu=selected.ders_kodu,
                ders_adi=selected.ders_adi,
                match_method="ders_kodu",
            )
        if error:
            return CourseMatchResult(matched=False, error=f"Ders kodu eslemesi belirsiz: {error}")

    if name_key:
        exact_matches = [item for item in candidates if normalize_course_text(item.ders_adi) == name_key]
        selected, error = _select_candidate(exact_matches)
        if selected:
            return CourseMatchResult(
                matched=True,
                ders_id=selected.ders_id,
                ders_kodu=selected.ders_kodu,
                ders_adi=selected.ders_adi,
                match_method="ders_adi",
            )
        if error:
            return CourseMatchResult(matched=False, error=f"Ders adi eslemesi belirsiz: {error}")

    if loose_name_key:
        normalized_matches = [item for item in candidates if normalize_course_key(item.ders_adi) == loose_name_key]
        selected, error = _select_candidate(normalized_matches)
        if selected:
            return CourseMatchResult(
                matched=True,
                ders_id=selected.ders_id,
                ders_kodu=selected.ders_kodu,
                ders_adi=selected.ders_adi,
                match_method="ders_adi_normalized",
            )
        if error:
            return CourseMatchResult(matched=False, error=f"Normalize ders adi eslemesi belirsiz: {error}")

    return CourseMatchResult(matched=False, error="Sistemde eslesen ders bulunamadi.")

# -*- coding: utf-8 -*-
"""Mufredat disi aday dersler icin PROMETHEE II + Top-7 cesitlilik servisi."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

CRITERIA = (
    "academic_fit",
    "curriculum_gap",
    "survey_demand",
    "resource_fit",
    "semester_fit",
    "non_overlap",
    "sector_value",
    "data_confidence",
)
CRITERION_LABELS = {
    "academic_fit": "akademik / bolum uygunlugu",
    "curriculum_gap": "mufredat boslugu katkisi",
    "survey_demand": "anket talebi",
    "resource_fit": "kaynak uygunlugu",
    "semester_fit": "donem / AKTS uygunlugu",
    "non_overlap": "tekrar / cakisma azligi",
    "sector_value": "sektorel / guncel deger",
    "data_confidence": "veri guveni",
}
DEFAULT_WEIGHTS = {
    "academic_fit": 0.20,
    "curriculum_gap": 0.20,
    "survey_demand": 0.15,
    "resource_fit": 0.15,
    "semester_fit": 0.10,
    "non_overlap": 0.10,
    "sector_value": 0.05,
    "data_confidence": 0.05,
}
DEFAULT_THRESHOLDS = {key: (5.0, 20.0) for key in CRITERIA}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def _normalize_weights(weights: dict[str, Any] | None) -> dict[str, float]:
    source = weights or DEFAULT_WEIGHTS
    clean = {key: max(0.0, _finite(source.get(key))) for key in CRITERIA}
    total = sum(clean.values())
    if total <= 1e-12:
        raise ValueError("PROMETHEE II kriter agirliklari bos veya gecersiz.")
    return {key: value / total for key, value in clean.items()}


def v_shape_preference(diff: float, q: float, p: float) -> float:
    if p <= q:
        raise ValueError("PROMETHEE tercih esigi p, kayitsizlik esigi q'dan buyuk olmalidir.")
    if diff <= q:
        return 0.0
    if diff >= p:
        return 1.0
    return max(0.0, min(1.0, (diff - q) / (p - q)))


def promethee_ii_rank(
    alternatives: list[dict[str, Any]],
    *,
    weights: dict[str, Any] | None = None,
    thresholds: dict[str, tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    """Ikili tercih indekslerinden phi+, phi- ve net phi uretir."""
    if not alternatives:
        return []
    normalized_weights = _normalize_weights(weights)
    threshold_map = thresholds or DEFAULT_THRESHOLDS
    n = len(alternatives)
    if n == 1:
        only = dict(alternatives[0])
        only.update({"phi_plus": 0.0, "phi_minus": 0.0, "net_flow": 0.0, "rank": 1})
        return [only]

    preference = [[0.0 for _ in range(n)] for _ in range(n)]
    for i, alternative in enumerate(alternatives):
        values_a = dict(alternative.get("criteria") or {})
        for j, other in enumerate(alternatives):
            if i == j:
                continue
            values_b = dict(other.get("criteria") or {})
            total = 0.0
            for key in CRITERIA:
                q, p = threshold_map.get(key, DEFAULT_THRESHOLDS[key])
                diff = _finite(values_a.get(key)) - _finite(values_b.get(key))
                total += normalized_weights[key] * v_shape_preference(diff, float(q), float(p))
            preference[i][j] = total

    ranked: list[dict[str, Any]] = []
    denominator = float(n - 1)
    for i, alternative in enumerate(alternatives):
        phi_plus = sum(preference[i][j] for j in range(n) if j != i) / denominator
        phi_minus = sum(preference[j][i] for j in range(n) if j != i) / denominator
        row = dict(alternative)
        row.update(
            {
                "phi_plus": phi_plus,
                "phi_minus": phi_minus,
                "net_flow": phi_plus - phi_minus,
                "weights": normalized_weights,
            }
        )
        ranked.append(row)
    ranked.sort(key=lambda item: (-float(item["net_flow"]), int(item.get("course_id") or 0)))
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    return ranked


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(token) > 1}


def _jaccard(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def select_top_with_diversity(
    ranked: list[dict[str, Any]],
    *,
    top_n: int = 7,
    ranking_weight: float = 0.75,
) -> list[dict[str, Any]]:
    """MMR-benzeri secim: PROMETHEE sirasi ana sinyal, benzerlik hafif ceza."""
    if not ranked or top_n <= 0:
        return []
    def normalized_flow(item: dict[str, Any]) -> float:
        # PROMETHEE net akis teorik olarak [-1, 1] araligindadir. Mutlak
        # normalizasyon, aday kumesindeki son sirayi zorunlu olarak 0 yapip
        # cesitlilik cezasini etkisizlestiren min-max yan etkisini onler.
        value = float(item.get("net_flow") or 0.0)
        return max(0.0, min(1.0, (value + 1.0) / 2.0))

    remaining = [dict(item) for item in ranked]
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < min(int(top_n), len(ranked)):
        best_index = 0
        best_score = -float("inf")
        for idx, item in enumerate(remaining):
            text = str(item.get("content_text") or item.get("name") or "")
            max_similarity = max(
                (_jaccard(text, str(chosen.get("content_text") or chosen.get("name") or "")) for chosen in selected),
                default=0.0,
            )
            diversity_score = ranking_weight * normalized_flow(item) - (1.0 - ranking_weight) * max_similarity
            if diversity_score > best_score:
                best_score = diversity_score
                best_index = idx
        chosen = remaining.pop(best_index)
        chosen["diversity_score"] = best_score
        selected.append(chosen)
    for rank, item in enumerate(selected, start=1):
        item["selected_rank"] = rank
    return selected


def neutral_survey_score(votes: int | None, max_votes: int) -> tuple[float, bool]:
    if votes is None:
        return 50.0, True
    if votes <= 0 or max_votes <= 0:
        return 50.0, False
    score = 50.0 + 50.0 * math.log1p(int(votes)) / math.log1p(int(max_votes))
    return min(100.0, score), False


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def ensure_candidate_recommendation_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_course_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            semester TEXT,
            rank INTEGER NOT NULL,
            promethee_rank INTEGER NOT NULL,
            phi_plus REAL NOT NULL,
            phi_minus REAL NOT NULL,
            net_flow REAL NOT NULL,
            diversity_score REAL,
            survey_neutral INTEGER NOT NULL DEFAULT 0,
            criteria_json TEXT,
            weights_json TEXT,
            reason TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(decision_run_id, course_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_candidate_recommendations_run "
        "ON candidate_course_recommendations (decision_run_id, rank)"
    )


def _scope_candidates(
    cur: sqlite3.Cursor,
    *,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
) -> list[dict[str, Any]]:
    cur.execute("PRAGMA table_info(ders)")
    course_columns = {str(row[1]) for row in cur.fetchall()}
    description_expr = "COALESCE(d.bilgi,'')" if "bilgi" in course_columns else "''"
    akts_expr = "d.akts" if "akts" in course_columns else "NULL"
    credit_expr = "d.kredi" if "kredi" in course_columns else "NULL"
    where: list[str] = []
    params: list[Any] = []
    if department_id is not None:
        where.append("d.bolum_id = ?")
        params.append(int(department_id))
    elif faculty_id is not None:
        where.append("COALESCE(d.fakulte_id, b.fakulte_id) = ?")
        params.append(int(faculty_id))
    where.append(
        "NOT EXISTS (SELECT 1 FROM mufredat_ders md JOIN mufredat m ON m.mufredat_id=md.mufredat_id "
        "WHERE md.ders_id=d.ders_id AND m.akademik_yil=? "
        "AND (? IS NULL OR m.fakulte_id=? OR b.fakulte_id=?) "
        "AND (? IS NULL OR m.bolum_id=?))"
    )
    params.extend([int(year), faculty_id, faculty_id, faculty_id, department_id, department_id])
    cur.execute(
        f"""
        SELECT d.ders_id, COALESCE(d.kod,''), COALESCE(d.ad,''), {description_expr},
               {akts_expr}, {credit_expr}, COALESCE(d.fakulte_id,b.fakulte_id), d.bolum_id
        FROM ders d
        LEFT JOIN bolum b ON b.bolum_id=d.bolum_id
        WHERE {' AND '.join(where)}
        ORDER BY d.ad, d.ders_id
        """,
        tuple(params),
    )
    return [
        {
            "course_id": int(row[0]),
            "code": str(row[1] or ""),
            "name": str(row[2] or ""),
            "description": str(row[3] or ""),
            "akts": row[4],
            "credit": row[5],
            "faculty_id": row[6],
            "department_id": row[7],
        }
        for row in cur.fetchall()
    ]


def _curriculum_texts(cur: sqlite3.Cursor, year: int, faculty_id: int | None, department_id: int | None) -> list[str]:
    params: list[Any] = [int(year), faculty_id, faculty_id, department_id, department_id]
    try:
        cur.execute(
            """
            SELECT COALESCE(d.ad,'') || ' ' || COALESCE(d.bilgi,'')
            FROM mufredat m
            JOIN mufredat_ders md ON md.mufredat_id=m.mufredat_id
            JOIN ders d ON d.ders_id=md.ders_id
            WHERE m.akademik_yil=?
              AND (? IS NULL OR m.fakulte_id=?)
              AND (? IS NULL OR m.bolum_id=?)
            """,
            tuple(params),
        )
        return [str(row[0] or "") for row in cur.fetchall()]
    except sqlite3.OperationalError:
        return []


def _latest_surveys(cur: sqlite3.Cursor, course_ids: list[int], year: int) -> dict[int, int | None]:
    result: dict[int, int | None] = {course_id: None for course_id in course_ids}
    if not course_ids or not _table_exists(cur, "ders_kriterleri"):
        return result
    placeholders = ",".join("?" for _ in course_ids)
    try:
        cur.execute(
            f"""
            SELECT dk.ders_id, dk.anket_dersi_secen
            FROM ders_kriterleri dk
            JOIN (
                SELECT ders_id, MAX(yil) AS max_yil FROM ders_kriterleri
                WHERE ders_id IN ({placeholders}) AND yil <= ? GROUP BY ders_id
            ) latest ON latest.ders_id=dk.ders_id AND latest.max_yil=dk.yil
            """,
            tuple(course_ids) + (int(year),),
        )
        for course_id, votes in cur.fetchall():
            result[int(course_id)] = None if votes is None else max(0, int(votes))
    except sqlite3.OperationalError:
        pass
    return result


def _instructor_availability(cur: sqlite3.Cursor, course_ids: list[int], year: int, semester: str | None) -> dict[int, tuple[float, float]]:
    result = {course_id: (50.0, 50.0) for course_id in course_ids}
    if not course_ids or not _table_exists(cur, "ders_ogretim"):
        return result
    placeholders = ",".join("?" for _ in course_ids)
    try:
        cur.execute(
            f"SELECT ders_id, donem FROM ders_ogretim WHERE ders_id IN ({placeholders}) AND (akademik_yil IS NULL OR akademik_yil<=?)",
            tuple(course_ids) + (int(year),),
        )
        target = "b" if str(semester or "").lower().startswith("b") else "g"
        seen: dict[int, list[str]] = {}
        for course_id, term in cur.fetchall():
            seen.setdefault(int(course_id), []).append(str(term or "").strip().lower())
        for course_id, terms in seen.items():
            semester_fit = 100.0 if any(term.startswith(target) for term in terms) else 65.0
            result[course_id] = (100.0, semester_fit)
    except sqlite3.OperationalError:
        pass
    return result


def _candidate_weights(conn: sqlite3.Connection, faculty_id: int | None, department_id: int | None, year: int) -> tuple[dict[str, float], str]:
    try:
        from app.services.ahp_profile_service import resolve_ahp_profile

        profile = resolve_ahp_profile(conn, faculty_id=faculty_id, department_id=department_id, year=year)
        weights = dict(profile.get("weights") or {})
        if all(key in weights for key in CRITERIA):
            return _normalize_weights(weights), f"AHP profil #{profile.get('id')}"
    except Exception:
        pass
    return dict(DEFAULT_WEIGHTS), "Belgelenmis uzman varsayilani"


def _reason(item: dict[str, Any]) -> str:
    criteria = dict(item.get("criteria") or {})
    ordered = sorted(criteria.items(), key=lambda pair: pair[1], reverse=True)
    strong = [CRITERION_LABELS[key] for key, _ in ordered[:2]]
    weak = [CRITERION_LABELS[key] for key, value in ordered if value < 45.0]
    parts = [
        f"PROMETHEE II net akis {float(item.get('net_flow') or 0.0):.4f}",
        "guclu alanlar: " + ", ".join(strong),
    ]
    if item.get("survey_neutral"):
        parts.append("anket verisi olmadigi icin talep sinyali notr (50) kabul edildi")
    else:
        parts.append("anket talebi bonus olarak hesaba katildi")
    if weak:
        parts.append("dikkat: " + ", ".join(weak[:2]))
    return "; ".join(parts) + "."


def generate_candidate_recommendations(
    conn: sqlite3.Connection,
    *,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    semester: str | None,
    decision_run_id: int | None,
    top_n: int = 7,
) -> dict[str, Any]:
    ensure_candidate_recommendation_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    candidates = _scope_candidates(
        cur,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
    )
    course_ids = [int(item["course_id"]) for item in candidates]
    surveys = _latest_surveys(cur, course_ids, int(year))
    max_votes = max((value or 0 for value in surveys.values()), default=0)
    availability = _instructor_availability(cur, course_ids, int(year), semester)
    curriculum_texts = _curriculum_texts(cur, int(year), faculty_id, department_id)
    weights, weight_source = _candidate_weights(conn, faculty_id, department_id, int(year))

    alternatives: list[dict[str, Any]] = []
    for candidate in candidates:
        course_id = int(candidate["course_id"])
        content = f"{candidate['name']} {candidate['description']}".strip()
        max_similarity = max((_jaccard(content, text) for text in curriculum_texts), default=0.0)
        non_overlap = 100.0 * (1.0 - max_similarity)
        academic_fit = 100.0 if department_id is not None and candidate.get("department_id") == department_id else 85.0
        survey_score, survey_neutral = neutral_survey_score(surveys.get(course_id), max_votes)
        resource_fit, semester_fit = availability.get(course_id, (50.0, 50.0))
        completeness = sum(
            [
                bool(candidate.get("description")),
                candidate.get("akts") is not None,
                candidate.get("credit") is not None,
                surveys.get(course_id) is not None,
                resource_fit > 50.0,
            ]
        )
        criteria = {
            "academic_fit": academic_fit,
            "curriculum_gap": 0.60 * academic_fit + 0.40 * non_overlap,
            "survey_demand": survey_score,
            "resource_fit": resource_fit,
            "semester_fit": semester_fit,
            "non_overlap": non_overlap,
            "sector_value": 50.0,
            "data_confidence": 20.0 * completeness,
        }
        alternatives.append(
            {
                **candidate,
                "content_text": content,
                "criteria": criteria,
                "survey_neutral": survey_neutral,
            }
        )

    ranked = promethee_ii_rank(alternatives, weights=weights)
    selected = select_top_with_diversity(ranked, top_n=top_n)
    for item in selected:
        item["reason"] = _reason(item)

    if decision_run_id is not None:
        cur.execute(
            "DELETE FROM candidate_course_recommendations WHERE decision_run_id=?",
            (int(decision_run_id),),
        )
        for item in selected:
            cur.execute(
                """
                INSERT INTO candidate_course_recommendations (
                    decision_run_id, course_id, year, faculty_id, department_id, semester,
                    rank, promethee_rank, phi_plus, phi_minus, net_flow, diversity_score,
                    survey_neutral, criteria_json, weights_json, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(decision_run_id), int(item["course_id"]), int(year), faculty_id,
                    department_id, semester, int(item["selected_rank"]), int(item["rank"]),
                    float(item["phi_plus"]), float(item["phi_minus"]), float(item["net_flow"]),
                    float(item.get("diversity_score") or 0.0), 1 if item.get("survey_neutral") else 0,
                    json.dumps(item.get("criteria") or {}, ensure_ascii=False, sort_keys=True),
                    json.dumps(weights, ensure_ascii=False, sort_keys=True), str(item["reason"]), _now(),
                ),
            )
    return {
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "weight_source": weight_source,
        "weights": weights,
        "ranked": ranked,
        "selected": selected,
    }


def list_candidate_recommendations(conn: sqlite3.Connection, decision_run_id: int) -> list[dict[str, Any]]:
    ensure_candidate_recommendation_schema(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.*, d.kod AS course_code, d.ad AS course_name
        FROM candidate_course_recommendations r
        JOIN ders d ON d.ders_id=r.course_id
        WHERE r.decision_run_id=? ORDER BY r.rank, r.id
        """,
        (int(decision_run_id),),
    )
    rows: list[dict[str, Any]] = []
    for row in cur.fetchall():
        item = dict(row)
        try:
            item["criteria"] = json.loads(item.get("criteria_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            item["criteria"] = {}
        rows.append(item)
    return rows

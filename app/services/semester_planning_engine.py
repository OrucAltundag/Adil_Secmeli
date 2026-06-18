# -*- coding: utf-8 -*-
"""Policy tabanli Guz/Bahar donem planlama motoru."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_semester_planning_schema
from app.services.course_curriculum_status_service import (
    get_yearly_curriculum_term_map,
)
from app.services.course_semester_availability_service import (
    display_semester,
    get_course_availability,
    validate_course_semester,
)
from app.services.course_type import build_elective_predicate
from app.services.instructor_planning_service import check_instructor_feasibility
from app.services.prerequisite_planning_service import (
    check_prerequisite_order,
    get_prerequisites,
)
from app.services.resource_planning_service import (
    check_resource_feasibility,
    get_course_resource_requirements,
)
from app.services.semester_balance_metrics_service import (
    calculate_plan_score,
    calculate_semester_balance_metrics,
    estimate_course_capacity,
    estimate_course_demand,
    generate_balance_warnings,
)
from app.services.semester_planning_policy_service import resolve_policy
from app.services.semester_workload_service import (
    adjust_targets_by_required_load,
    get_required_course_load,
)
from app.services.time_conflict_planning_service import generate_conflict_warnings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _load_json(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}


def _fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    columns = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, columns) or {} for row in cur.fetchall()]


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return {str(row[1]) for row in cur.fetchall()}
    except sqlite3.OperationalError:
        return set()


def _course_name_map(conn: sqlite3.Connection, course_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not course_ids:
        return {}
    cols = _table_columns(conn, "ders")
    wanted = [c for c in ("ders_id", "kod", "ad", "bolum_id", "fakulte_id", "kontenjan") if c in cols]
    if not wanted:
        return {int(cid): {"course_id": int(cid), "course_name": str(cid), "course_code": str(cid)} for cid in course_ids}
    placeholders = ",".join("?" for _ in course_ids)
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(wanted)} FROM ders WHERE ders_id IN ({placeholders})", tuple(int(c) for c in course_ids))
    data = {}
    for row in _fetch_all_dicts(cur):
        cid = int(row["ders_id"])
        data[cid] = {
            "course_id": cid,
            "course_code": row.get("kod") or str(cid),
            "course_name": row.get("ad") or str(cid),
            "department_id": row.get("bolum_id"),
            "faculty_id": row.get("fakulte_id"),
            "base_capacity": row.get("kontenjan"),
        }
    return data


def _fetch_candidate_courses(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    cur = conn.cursor()
    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    if elective_predicate == "0=1":
        return []
    where = [elective_predicate]
    params: list[Any] = []
    if faculty_id is not None:
        where.append("(d.fakulte_id = ? OR b.fakulte_id = ?)")
        params.extend([int(faculty_id), int(faculty_id)])
    if department_id is not None:
        where.append("(d.bolum_id = ? OR d.bolum_id IS NULL)")
        params.append(int(department_id))
    cur.execute(
        f"""
        SELECT DISTINCT d.ders_id, d.kod, d.ad, d.bolum_id, COALESCE(d.fakulte_id, b.fakulte_id) AS fakulte_id
        FROM ders d
        LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
        WHERE {' AND '.join(where)}
        ORDER BY CASE WHEN d.bolum_id = ? THEN 0 ELSE 1 END, d.ders_id
        """,
        tuple(params + [int(department_id or -1)]),
    )
    rows = _fetch_all_dicts(cur)
    # Faz 4: Önerilen Dersler (Karar Merkezi) çıktısı dönem planlamayı beslesin.
    # Açılabilirlik skoru kapsamdaki en güncel karar çalıştırmasından okunur;
    # yoksa eski davranışa (skor tablosu) geri düşülür.
    # Hedef yil henuz mufredatsiz oldugu icin PROMETHEE adaylari bir onceki
    # (karar kaynagi) yildaki gecici calistirmadan okunur.
    candidate_map = _latest_candidate_scores(conn, int(year) - 1, faculty_id, department_id)
    if not candidate_map:
        candidate_map = _latest_candidate_scores(conn, int(year), faculty_id, department_id)
    # Yeni hedef yil icin kaynak yil (year-1); eski/entegrasyon cagrilarinda
    # karar ve plan ayni yili tasiyabildigi icin once ayni yil, sonra onceki yil.
    acil_map = _latest_acilabilirlik_scores(conn, int(year), faculty_id, department_id)
    if not acil_map:
        acil_map = _latest_acilabilirlik_scores(conn, int(year) - 1, faculty_id, department_id)
    score_map = _latest_scores(conn, year)
    out = []
    for row in rows:
        cid = int(row["ders_id"])
        out.append(
            {
                "course_id": cid,
                "course_code": row.get("kod") or str(cid),
                "course_name": row.get("ad") or str(cid),
                "department_id": row.get("bolum_id"),
                "faculty_id": row.get("fakulte_id"),
                "score": candidate_map.get(cid, acil_map.get(cid, score_map.get(cid, 0.0))),
                "score_source": (
                    "promethee_ii" if cid in candidate_map
                    else "acilabilirlik" if cid in acil_map
                    else "skor"
                ),
            }
        )
    return out


def _latest_candidate_scores(
    conn: sqlite3.Connection,
    source_year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[int, float]:
    """En guncel PROMETHEE II Top-7 sonucunu 0-100 planlama skoruna cevirir."""
    tables = _existing_tables(conn)
    if "candidate_course_recommendations" not in tables or "decision_runs" not in tables:
        return {}
    where = ["dr.year = ?", "dr.status = 'completed'"]
    params: list[Any] = [int(source_year)]
    if faculty_id is not None:
        where.append("dr.faculty_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("IFNULL(dr.department_id, -1) IN (-1, ?)")
        params.append(int(department_id))
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT MAX(dr.id) FROM decision_runs dr WHERE {' AND '.join(where)}",
            tuple(params),
        )
        row = cur.fetchone()
        run_id = int(row[0]) if row and row[0] is not None else None
        if run_id is None:
            return {}
        cur.execute(
            "SELECT course_id, net_flow FROM candidate_course_recommendations WHERE decision_run_id=?",
            (run_id,),
        )
        return {
            int(course_id): max(0.0, min(100.0, (float(net_flow) + 1.0) * 50.0))
            for course_id, net_flow in cur.fetchall()
        }
    except sqlite3.OperationalError:
        return {}


def _latest_acilabilirlik_scores(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[int, float]:
    """Kapsamdaki en güncel karar çalıştırmasından açılabilirlik skorlarını okur.

    course_decisions.acilabilirlik_score (Faz 3) -> {course_id: skor}. İlgili
    yıl/fakülte/bölüm için en son `decision_run` esas alınır. Tablo, kolon ya da
    karar çalıştırması yoksa boş döner (planlama eski skor kaynağına döner).
    """
    tables = _existing_tables(conn)
    if "course_decisions" not in tables or "decision_runs" not in tables:
        return {}
    if "acilabilirlik_score" not in _table_columns(conn, "course_decisions"):
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
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT cd.course_id, cd.acilabilirlik_score
            FROM course_decisions cd
            JOIN decision_runs dr ON dr.id = cd.decision_run_id
            WHERE cd.decision_run_id = (
                SELECT dr2.id FROM decision_runs dr2
                WHERE {' AND '.join(where)}
                ORDER BY dr2.id DESC LIMIT 1
            )
            """,
            tuple(params),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError:
        return {}
    out: dict[int, float] = {}
    for row in rows:
        if row is None or row[0] is None or row[1] is None:
            continue
        out[int(row[0])] = _float(row[1])
    return out


def _latest_scores(conn: sqlite3.Connection, year: int) -> dict[int, float]:
    if "skor" not in _existing_tables(conn):
        return {}
    cols = _table_columns(conn, "skor")
    if not {"ders_id", "skor_top"}.issubset(cols):
        return {}
    year_col = "akademik_yil" if "akademik_yil" in cols else "yil" if "yil" in cols else None
    try:
        cur = conn.cursor()
        if year_col:
            cur.execute(
                f"""
                SELECT ders_id, MAX(skor_top) AS score
                FROM skor
                WHERE {year_col} <= ?
                GROUP BY ders_id
                """,
                (int(year),),
            )
        else:
            cur.execute("SELECT ders_id, MAX(skor_top) AS score FROM skor GROUP BY ders_id")
        return {int(row[0]): _float(row[1]) for row in cur.fetchall() if row and row[0] is not None}
    except sqlite3.OperationalError:
        return {}


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {str(row[0]) for row in cur.fetchall()}


def _prepare_candidates(
    conn: sqlite3.Connection,
    year: int,
    candidate_courses: list[Any] | None,
    faculty_id: int | None,
    department_id: int | None,
) -> list[dict[str, Any]]:
    if candidate_courses is None:
        candidates = _fetch_candidate_courses(conn, year=year, faculty_id=faculty_id, department_id=department_id)
    else:
        ids: list[int] = []
        raw_by_id: dict[int, dict[str, Any]] = {}
        for item in candidate_courses:
            if isinstance(item, dict):
                cid = int(item.get("course_id") or item.get("ders_id") or 0)
                raw_by_id[cid] = dict(item)
            else:
                cid = int(item)
                raw_by_id[cid] = {"course_id": cid}
            ids.append(cid)
        meta = _course_name_map(conn, ids)
        candidates = []
        for cid in ids:
            row = {**meta.get(cid, {"course_id": cid, "course_name": str(cid), "course_code": str(cid)}), **raw_by_id[cid]}
            row["course_id"] = cid
            row["score"] = _float(row.get("score", row.get("course_score", row.get("topsis_score", row.get("skor", 0.0)))))
            candidates.append(row)
    for row in candidates:
        cid = int(row["course_id"])
        row["expected_demand"] = _float(row.get("expected_demand"), estimate_course_demand(conn, cid, year))
        row["expected_capacity"] = _float(row.get("expected_capacity"), estimate_course_capacity(conn, cid, year))
        row["course_score"] = _float(row.get("course_score", row.get("score", 0.0)))
        row["availability"] = get_course_availability(conn, cid, year=year, department_id=department_id, faculty_id=faculty_id)
        row["resource_requirements"] = get_course_resource_requirements(conn, cid)
    return candidates


def _semester_allowed(candidate: dict[str, Any], semester: str) -> bool:
    availability = candidate.get("availability") or {}
    return bool(availability.get("allowed_spring") if semester == "spring" else availability.get("allowed_fall"))


def _semester_capacity(assignments: list[dict[str, Any]], semester: str) -> int:
    return len([a for a in assignments if a.get("assigned_semester") == semester])


def _choose_semester(candidate: dict[str, Any], assignments: list[dict[str, Any]], policy: dict[str, Any], scenario_type: str) -> list[str]:
    preferred = str((candidate.get("availability") or {}).get("preferred_semester") or "either")
    allowed = [sem for sem in ("fall", "spring") if _semester_allowed(candidate, sem)]
    if preferred in allowed:
        allowed = [preferred] + [sem for sem in allowed if sem != preferred]
    elif scenario_type == "balance_priority":
        allowed = sorted(allowed, key=lambda sem: _semester_capacity(assignments, sem))
    elif scenario_type == "demand_priority":
        allowed = sorted(allowed, key=lambda sem: sum(_float(a.get("expected_demand")) for a in assignments if a.get("assigned_semester") == sem))
    else:
        allowed = sorted(allowed, key=lambda sem: _semester_capacity(assignments, sem))
    return allowed


def _can_repeat(course_id: int, candidate: dict[str, Any], assignments: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[bool, str | None]:
    already = [a for a in assignments if int(a.get("course_id") or 0) == int(course_id) and a.get("assigned_semester") in {"fall", "spring"}]
    if not already:
        return True, None
    repeat_policy = str(policy.get("same_course_repeat_policy") or "disallow")
    if repeat_policy == "disallow":
        return False, "Aynı ders tekrar politikası bu dersin iki döneme yerleşmesini engelledi."
    if repeat_policy == "allow_if_high_demand":
        threshold = _float(policy.get("high_demand_repeat_threshold"), 0.0)
        if threshold and _float(candidate.get("expected_demand")) >= threshold:
            return True, "Yüksek talep eşiği nedeniyle aynı dersin tekrarına izin verildi."
        return False, "Ders talebi aynı ders tekrar eşiğini karşılamıyor."
    if repeat_policy in {"allow_if_capacity_needed", "allow_with_approval"}:
        return True, "Politika aynı ders tekrarını uyarılı olarak esnetiyor."
    return False, "Aynı ders tekrar politikası geçersiz."


def _fits_semester_counts(assignments: list[dict[str, Any]], semester: str, policy: dict[str, Any]) -> bool:
    max_value = int(policy.get("fall_max" if semester == "fall" else "spring_max") or 0)
    return _semester_capacity(assignments, semester) < max_value


def _assignment_explanation(candidate: dict[str, Any], semester: str, extra: list[str] | None = None) -> str:
    parts = [
        f"{candidate.get('course_code') or candidate.get('course_id')} {display_semester(semester)} dönemine yerleştirildi.",
        f"Skor: {round(_float(candidate.get('course_score')), 2)}.",
    ]
    availability = candidate.get("availability") or {}
    if availability.get("preferred_semester") in {"fall", "spring"}:
        parts.append(f"Tercih edilen dönem: {display_semester(availability.get('preferred_semester'))}.")
    if extra:
        parts.extend(extra)
    return " ".join(parts)


def generate_semester_plan(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    candidate_courses: list[Any] | None = None,
    policy: dict[str, Any] | None = None,
    curriculum_year: int | None = None,
    persist: bool = True,
    run_name: str | None = None,
    created_by: str | None = None,
    scenario_type: str = "score_priority",
    generate_alternatives: bool = True,
    respect_existing_curriculum: bool = False,
) -> dict[str, Any]:
    ensure_semester_planning_schema(conn, commit=False)
    year = int(year)
    policy = dict(policy or resolve_policy(conn, year=year, faculty_id=faculty_id, department_id=department_id, curriculum_year=curriculum_year))
    if policy.get("soft_constraint_weight_json") and not policy.get("soft_constraint_weights"):
        policy["soft_constraint_weights"] = _load_json(policy.get("soft_constraint_weight_json"), {})

    warnings: list[str] = []
    required_loads: dict[str, dict[str, Any]] = {}
    if policy.get("consider_required_course_load") and department_id is not None:
        for sem in ("fall", "spring"):
            load = get_required_course_load(conn, int(department_id), year, sem)
            if load:
                required_loads[sem] = load
        if required_loads:
            policy, workload_warnings = adjust_targets_by_required_load(policy, required_loads)
            warnings.extend(workload_warnings)

    candidates = _prepare_candidates(conn, year, candidate_courses, faculty_id, department_id)
    # Bölüm bazlı yıllık bütünlük: o yıl zaten müfredatta olan dersler yeni
    # öneri olarak tekrar dağıtılmaz (opt-in; varsayılan davranış değişmez).
    already_in_curriculum_ids: list[int] = []
    if respect_existing_curriculum:
        existing_term_map = get_yearly_curriculum_term_map(conn, year, faculty_id, department_id)
        if existing_term_map:
            kept: list[dict[str, Any]] = []
            for row in candidates:
                cid = int(row["course_id"])
                if cid in existing_term_map:
                    already_in_curriculum_ids.append(cid)
                else:
                    kept.append(row)
            candidates = kept
            if already_in_curriculum_ids:
                warnings.append(
                    f"{len(already_in_curriculum_ids)} ders bu akademik yıl müfredatında zaten bulunduğu için "
                    "yeni öneri listesinden çıkarıldı."
                )
    sorted_candidates = sorted(candidates, key=lambda row: (_float(row.get("course_score")), _float(row.get("expected_demand")), -int(row["course_id"])), reverse=True)
    if scenario_type == "demand_priority":
        sorted_candidates = sorted(candidates, key=lambda row: (_float(row.get("expected_demand")), _float(row.get("course_score"))), reverse=True)
    elif scenario_type == "balance_priority":
        sorted_candidates = sorted(candidates, key=lambda row: (_float(row.get("course_score")), -_float(row.get("expected_demand"))), reverse=True)

    assignments: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    assigned_instructor_counts: dict[tuple[int, str], int] = {}
    seen_selected: set[int] = set()
    target_total = int(policy.get("total_elective_target") or 8)

    for candidate in sorted_candidates:
        if len([a for a in assignments if a.get("assigned_semester") in {"fall", "spring"}]) >= target_total:
            break
        course_id = int(candidate["course_id"])
        repeat_ok, repeat_reason = _can_repeat(course_id, candidate, assignments, policy)
        if not repeat_ok:
            violations.append(
                {
                    "course_id": course_id,
                    "constraint_type": "repeat",
                    "severity": "warning",
                    "message": repeat_reason or "Aynı ders tekrarına izin verilmedi.",
                    "suggestion": "Talep yüksekse policy tekrar kuralını allow_if_high_demand olarak güncelleyin.",
                }
            )
            continue
        selected_semester = None
        selected_extra: list[str] = []
        blocked_reasons: list[dict[str, Any]] = []
        for sem in _choose_semester(candidate, assignments, policy, scenario_type):
            availability_result = validate_course_semester(conn, course_id, sem, year=year, department_id=department_id, faculty_id=faculty_id)
            if policy.get("consider_course_availability") and not availability_result["allowed"]:
                blocked_reasons.append(
                    {
                        "course_id": course_id,
                        "constraint_type": "semester_availability",
                        "severity": "error",
                        "message": availability_result["message"],
                        "suggestion": availability_result["suggestion"],
                    }
                )
                if str(policy.get("hard_constraint_policy")) == "strict":
                    continue
            if not _fits_semester_counts(assignments, sem, policy):
                blocked_reasons.append(
                    {
                        "course_id": course_id,
                        "constraint_type": "capacity",
                        "severity": "warning",
                        "message": f"{display_semester(sem)} maksimum ders sayısı dolu.",
                        "suggestion": "Dersi diğer döneme veya yedek listeye alın.",
                    }
                )
                continue
            if policy.get("consider_instructor_availability"):
                instructor = check_instructor_feasibility(conn, course_id, year, sem, assigned_counts=assigned_instructor_counts)
                if not instructor["ok"] and str(policy.get("hard_constraint_policy")) == "strict":
                    blocked_reasons.append(
                        {
                            "course_id": course_id,
                            "constraint_type": "instructor",
                            "severity": "error",
                            "message": instructor["message"],
                            "suggestion": "Öğretim üyesi uygunluğunu güncelleyin veya dersi diğer döneme taşıyın.",
                        }
                    )
                    continue
                if instructor.get("instructor_id"):
                    assigned_instructor_counts[(int(instructor["instructor_id"]), sem)] = assigned_instructor_counts.get((int(instructor["instructor_id"]), sem), 0) + 1
                    selected_extra.append(instructor["message"])
            if policy.get("consider_resource_constraints"):
                resource = check_resource_feasibility(conn, course_id, year, sem)
                if not resource["ok"] and str(policy.get("hard_constraint_policy")) == "strict":
                    blocked_reasons.extend(
                        {
                            "course_id": course_id,
                            "constraint_type": "resource",
                            "severity": "error",
                            "message": message,
                            "suggestion": "Kaynak kapasitesini artırın veya dersi diğer döneme taşıyın.",
                        }
                        for message in resource.get("violations", [])
                    )
                    continue
            selected_semester = sem
            if repeat_reason:
                selected_extra.append(repeat_reason)
            break
        if selected_semester:
            seen_selected.add(course_id)
            assignments.append(
                {
                    **candidate,
                    "assigned_semester": selected_semester,
                    "assignment_type": "selected",
                    "constraint_status": "ok",
                    "explanation": _assignment_explanation(candidate, selected_semester, selected_extra),
                }
            )
        else:
            violations.extend(blocked_reasons[:2])
            assignments.append(
                {
                    **candidate,
                    "assigned_semester": "unassigned",
                    "assignment_type": "rejected",
                    "constraint_status": "violation" if blocked_reasons else "warning",
                    "explanation": "Ders dönem hedefleri veya hard kısıtlar nedeniyle plana yerleşmedi.",
                }
            )

    if policy.get("consider_prerequisites"):
        prereq_violations = check_prerequisite_order(assignments, get_prerequisites(conn))
        violations.extend(prereq_violations)
        _repair_prerequisites(assignments, prereq_violations, policy)

    if policy.get("consider_time_conflicts"):
        violations.extend(generate_conflict_warnings(conn, assignments))

    selected_assignments = [a for a in assignments if a.get("assigned_semester") in {"fall", "spring"}]
    metrics = calculate_semester_balance_metrics(selected_assignments)
    metrics["total_plan_score"] = calculate_plan_score(selected_assignments, policy)
    warnings.extend(generate_balance_warnings(metrics, policy))
    plan_score = float(metrics["total_plan_score"])

    run_id = None
    scenarios: list[dict[str, Any]] = []
    if persist:
        run_id = _persist_plan(
            conn,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            policy=policy,
            candidates=candidates,
            assignments=assignments,
            violations=violations,
            metrics=metrics,
            warnings=warnings,
            plan_score=plan_score,
            run_name=run_name,
            created_by=created_by,
        )
    if generate_alternatives:
        scenarios = _build_alternative_scenarios(conn, year, faculty_id, department_id, candidates, policy, run_id)
    if persist and run_id is not None and scenarios:
        _persist_scenarios(conn, int(run_id), scenarios)

    fall = [a for a in selected_assignments if a["assigned_semester"] == "fall"]
    spring = [a for a in selected_assignments if a["assigned_semester"] == "spring"]
    unassigned = [a for a in assignments if a.get("assigned_semester") == "unassigned"]
    return {
        "ok": True,
        "plan_id": run_id,
        "year": year,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "policy": policy,
        "policy_snapshot_json": _json(policy),
        "fall_courses": fall,
        "spring_courses": spring,
        "fall_course_ids": [int(a["course_id"]) for a in fall],
        "spring_course_ids": [int(a["course_id"]) for a in spring],
        "unassigned_courses": unassigned,
        "rejected_courses": unassigned,
        "already_in_curriculum_ids": already_in_curriculum_ids,
        "plan_score": plan_score,
        "metrics": metrics,
        "constraint_violations": violations,
        "warnings": warnings,
        "explanations": [a.get("explanation") for a in selected_assignments if a.get("explanation")],
        "alternative_plans": scenarios,
    }


def _repair_prerequisites(assignments: list[dict[str, Any]], violations: list[dict[str, Any]], policy: dict[str, Any]) -> None:
    if not violations:
        return
    by_id = {int(a["course_id"]): a for a in assignments if a.get("assigned_semester") in {"fall", "spring"}}
    for violation in violations:
        if violation.get("severity") != "error":
            continue
        course_id = int(violation.get("course_id") or 0)
        item = by_id.get(course_id)
        if item and item.get("assigned_semester") == "fall" and int(policy.get("spring_max", 0) or 0) > len([a for a in assignments if a.get("assigned_semester") == "spring"]):
            item["assigned_semester"] = "spring"
            item["constraint_status"] = "warning"
            item["explanation"] = f"{item.get('course_code') or course_id} bahara taşındı; ön koşul sırası ihlalini azaltmak için dönem onarımı uygulandı."


def _persist_plan(
    conn: sqlite3.Connection,
    *,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    policy: dict[str, Any],
    candidates: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    metrics: dict[str, Any],
    warnings: list[str],
    plan_score: float,
    run_name: str | None,
    created_by: str | None,
) -> int:
    now = _now()
    selected = [a for a in assignments if a.get("assigned_semester") in {"fall", "spring"}]
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO semester_plan_runs (
            run_name, year, faculty_id, department_id, policy_id, total_candidate_count,
            selected_count, fall_count, spring_count, plan_score, status, metrics_json,
            policy_snapshot_json, warnings_json, created_at, completed_at, created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?)
        """,
        (
            run_name or f"Dönem Planı {year}",
            int(year),
            faculty_id,
            department_id,
            policy.get("id"),
            len(candidates),
            len(selected),
            len([a for a in selected if a.get("assigned_semester") == "fall"]),
            len([a for a in selected if a.get("assigned_semester") == "spring"]),
            plan_score,
            _json(metrics),
            _json(policy),
            _json(warnings),
            now,
            now,
            created_by,
        ),
    )
    run_id = int(cur.lastrowid or 0)
    for item in assignments:
        cur.execute(
            """
            INSERT INTO semester_plan_course_assignments (
                plan_run_id, course_id, assigned_semester, assignment_type, course_score,
                expected_demand, expected_capacity, constraint_status, explanation, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                int(item["course_id"]),
                item.get("assigned_semester"),
                item.get("assignment_type", "selected"),
                item.get("course_score"),
                item.get("expected_demand"),
                item.get("expected_capacity"),
                item.get("constraint_status", "ok"),
                item.get("explanation"),
                now,
            ),
        )
    for violation in violations:
        cur.execute(
            """
            INSERT INTO semester_plan_constraint_violations
                (plan_run_id, course_id, constraint_type, severity, message, suggestion, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                violation.get("course_id"),
                violation.get("constraint_type", "unknown"),
                violation.get("severity", "warning"),
                violation.get("message", ""),
                violation.get("suggestion"),
                now,
            ),
        )
    return run_id


def _build_alternative_scenarios(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    candidates: list[dict[str, Any]],
    policy: dict[str, Any],
    run_id: int | None,
) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for scenario_type, name in (
        ("score_priority", "Skor Öncelikli Plan"),
        ("balance_priority", "Dönem Dengesi Öncelikli Plan"),
        ("demand_priority", "Talep/Kontenjan Dengesi Öncelikli Plan"),
    ):
        result = generate_semester_plan(
            conn,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            candidate_courses=candidates,
            policy=policy,
            persist=False,
            scenario_type=scenario_type,
            generate_alternatives=False,
        )
        scenarios.append(
            {
                "plan_run_id": run_id,
                "scenario_name": name,
                "scenario_type": scenario_type,
                "fall_courses": result.get("fall_course_ids", []),
                "spring_courses": result.get("spring_course_ids", []),
                "metrics": result.get("metrics", {}),
                "constraint_violations": result.get("constraint_violations", []),
                "explanations": result.get("explanations", []),
                "plan_score": result.get("plan_score", 0.0),
            }
        )
    return scenarios


def _persist_scenarios(conn: sqlite3.Connection, run_id: int, scenarios: list[dict[str, Any]]) -> None:
    now = _now()
    cur = conn.cursor()
    for scenario in scenarios:
        cur.execute(
            """
            INSERT INTO semester_plan_scenarios (
                plan_run_id, scenario_name, scenario_type, fall_courses_json,
                spring_courses_json, metrics_json, constraint_violations_json,
                explanations_json, plan_score, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(run_id),
                scenario["scenario_name"],
                scenario["scenario_type"],
                _json(scenario.get("fall_courses", [])),
                _json(scenario.get("spring_courses", [])),
                _json(scenario.get("metrics", {})),
                _json(scenario.get("constraint_violations", [])),
                _json(scenario.get("explanations", [])),
                scenario.get("plan_score"),
                now,
            ),
        )


def get_plan_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    ensure_semester_planning_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM semester_plan_runs WHERE id = ?", (int(run_id),))
    row = _row_to_dict(cur.fetchone(), [d[0] for d in cur.description] if cur.description else [])
    if row:
        row["metrics"] = _load_json(row.get("metrics_json"), {})
        row["warnings"] = _load_json(row.get("warnings_json"), [])
        row["policy_snapshot"] = _load_json(row.get("policy_snapshot_json"), {})
    return row


def list_plan_runs(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_semester_planning_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    for col, value in (("year", year), ("faculty_id", faculty_id), ("department_id", department_id)):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(int(value))
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM semester_plan_runs WHERE {' AND '.join(where)} ORDER BY id DESC",
        tuple(params),
    )
    return [_row_to_dict(row, [d[0] for d in cur.description]) or {} for row in cur.fetchall()]

# -*- coding: utf-8 -*-
"""Decision run persistence and governance integration."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from app.services.db import get_raw_connection
import traceback
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema, ensure_decision_governance_schema
from app.services.ahp_profile_service import DEFAULT_CRITERIA_KEYS, resolve_ahp_profile
from app.services.data_confidence_service import calculate_course_data_confidence, save_data_confidence
from app.services.data_quality_integration_service import (
    assess_data_readiness_cursor,
    generate_coverage_report_cursor,
    save_data_coverage_report,
)
from app.services.decision_policy_service import classify_score, resolve_decision_policy
from app.services.explanation_engine import build_decision_explanation, save_decision_explanation
from app.services.fairness_report_service import generate_fairness_report, save_fairness_report
from app.services.havuz_karar import STATU_DINLENMEDE, STATU_HAVUZDA, STATU_IPTAL
from app.services.sensitivity_analysis_service import analyze_decision_sensitivity, save_sensitivity_result
from app.services.topsis_explainability_service import calculate_topsis_breakdowns, save_score_breakdown
from app.services.trend_analysis_service import analyze_course_trend, save_trend_analysis

ALGORITHM_VERSION = "ahp-topsis-trend-governance-v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _hash_payload(value: Any) -> str:
    payload = _json_dump(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_semester(value: str | None) -> str:
    return "Bahar" if str(value or "").strip().lower().startswith("b") else "Guz"


def _term_key(value: str | None) -> str:
    return "b" if _normalize_semester(value) == "Bahar" else "g"


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...], columns: list[str] | None = None) -> dict[str, Any]:
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return {columns[idx]: row[idx] for idx in range(len(columns or []))}


def _fetch_governance_flags(cur: sqlite3.Cursor, course_id: int) -> dict[str, Any]:
    try:
        cur.execute(
            """
            SELECT strategic_flag, accreditation_flag, instructor_changed,
                   content_updated, protected_until_year, notes
            FROM course_governance_flags
            WHERE course_id = ?
            LIMIT 1
            """,
            (int(course_id),),
        )
        row = cur.fetchone()
    except Exception:
        row = None
    if not row:
        return {
            "strategic_flag": False,
            "accreditation_flag": False,
            "instructor_changed": False,
            "content_updated": False,
            "protected_until_year": None,
            "notes": None,
        }
    return {
        "strategic_flag": bool(row[0]),
        "accreditation_flag": bool(row[1]),
        "instructor_changed": bool(row[2]),
        "content_updated": bool(row[3]),
        "protected_until_year": row[4],
        "notes": row[5],
    }


def _first_seen_year(cur: sqlite3.Cursor, course_id: int) -> int | None:
    years: list[int] = []
    queries = [
        ("SELECT MIN(akademik_yil) FROM performans WHERE ders_id = ?", (int(course_id),)),
        ("SELECT MIN(akademik_yil) FROM populerlik WHERE ders_id = ?", (int(course_id),)),
        ("SELECT MIN(yil) FROM ders_kriterleri WHERE ders_id = ?", (int(course_id),)),
        ("SELECT MIN(yil) FROM havuz WHERE CAST(ders_id AS INTEGER) = ?", (int(course_id),)),
    ]
    for query, params in queries:
        try:
            cur.execute(query, params)
            value = cur.fetchone()[0]
            if value is not None:
                years.append(int(value))
        except Exception:
            continue
    return min(years) if years else None


def _old_status(cur: sqlite3.Cursor, course_id: int, year: int, faculty_id: int | None, semester: str | None) -> int | None:
    try:
        cur.execute(
            """
            SELECT statu
            FROM havuz
            WHERE CAST(ders_id AS INTEGER) = ?
              AND yil = ?
              AND (? IS NULL OR fakulte_id = ?)
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = ?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(course_id), int(year), faculty_id, faculty_id, _term_key(semester)),
        )
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    except Exception:
        return None


def _course_meta(cur: sqlite3.Cursor, course_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not course_ids:
        return {}
    out: dict[int, dict[str, Any]] = {}
    for idx in range(0, len(course_ids), 900):
        chunk = course_ids[idx : idx + 900]
        placeholders = ",".join("?" for _ in chunk)
        cur.execute(
            f"""
            SELECT ders_id, kod, ad, fakulte_id, bolum_id
            FROM ders
            WHERE ders_id IN ({placeholders})
            """,
            tuple(chunk),
        )
        for row in cur.fetchall():
            out[int(row[0])] = {
                "course_id": int(row[0]),
                "code": str(row[1] or ""),
                "name": str(row[2] or ""),
                "faculty_id": int(row[3]) if row[3] is not None else None,
                "department_id": int(row[4]) if row[4] is not None else None,
            }
    return out


def _apply_governance(
    recommended_status: int,
    old_status: int | None,
    year: int,
    policy: dict[str, Any],
    governance: dict[str, Any],
    confidence: dict[str, Any],
    first_seen_year: int | None,
    sensitivity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    approval_required = False
    approval_reason_parts: list[str] = []
    final_status = int(recommended_status)

    protected_until = governance.get("protected_until_year")
    is_protected = protected_until is not None and int(protected_until) >= int(year)
    hard_decision = int(recommended_status) in {STATU_IPTAL, STATU_DINLENMEDE}
    is_new = (
        first_seen_year is not None
        and int(year) - int(first_seen_year) < int(policy.get("new_course_grace_period_years", 2) or 2)
    )

    if governance.get("strategic_flag") and hard_decision:
        approval_required = True
        approval_reason_parts.append("Stratejik ders korumasi")
        final_status = old_status if old_status is not None and int(old_status) > STATU_DINLENMEDE else STATU_HAVUZDA
    if governance.get("accreditation_flag") and hard_decision:
        approval_required = True
        approval_reason_parts.append("Akreditasyon korumasi")
        final_status = old_status if old_status is not None and int(old_status) > STATU_DINLENMEDE else STATU_HAVUZDA
    if is_protected and hard_decision:
        approval_required = True
        approval_reason_parts.append(f"{protected_until} yilina kadar korumali")
        final_status = old_status if old_status is not None and int(old_status) > STATU_DINLENMEDE else STATU_HAVUZDA
    if is_new and hard_decision:
        approval_required = True
        approval_reason_parts.append("Yeni ders grace period kapsaminda")
        final_status = max(final_status, STATU_DINLENMEDE)

    low_conf_threshold = float(policy.get("low_data_confidence_threshold", 0.50) or 0.50)
    if float(confidence.get("score") or 0.0) < low_conf_threshold and hard_decision:
        approval_required = True
        approval_reason_parts.append("Veri guveni dusuk")
        final_status = max(final_status, STATU_DINLENMEDE)

    if int(recommended_status) == STATU_IPTAL and policy.get("require_manual_approval_for_cancel", True):
        approval_required = True
        approval_reason_parts.append("Kalici iptal icin akademik onay gerekli")
        final_status = max(final_status, STATU_DINLENMEDE)

    if sensitivity and sensitivity.get("stability_level") == "low" and hard_decision:
        approval_required = True
        approval_reason_parts.append("Karar esige yakin/hassas")

    return {
        "final_status": int(final_status),
        "approval_required": approval_required,
        "approval_status": "pending" if approval_required else None,
        "approval_reason": "; ".join(dict.fromkeys(approval_reason_parts)) if approval_reason_parts else None,
    }


def create_decision_run(
    cur: sqlite3.Cursor,
    run_name: str,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    semester: str | None,
    ahp_profile_id: int | None,
    decision_policy_id: int | None,
    input_data_hash: str | None,
    created_by: str | None = None,
    status: str = "started",
    ahp_profile_version: int | None = None,
    ahp_weights_snapshot: dict[str, Any] | None = None,
    ahp_consistency_ratio: float | None = None,
    ahp_profile_status_at_run: str | None = None,
    ahp_profile_source: str | None = None,
) -> int:
    try:
        ensure_ahp_governance_schema(cur.connection, commit=False)
    except Exception:
        pass
    cur.execute(
        """
        INSERT INTO decision_runs (
            run_name, year, faculty_id, department_id, semester, algorithm_version,
            ahp_profile_id, ahp_profile_version, ahp_weights_snapshot_json,
            ahp_consistency_ratio, ahp_profile_status_at_run, ahp_profile_source,
            decision_policy_id, input_data_hash, status, started_at, created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(run_name),
            int(year),
            faculty_id,
            department_id,
            _normalize_semester(semester),
            ALGORITHM_VERSION,
            ahp_profile_id,
            ahp_profile_version,
            _json_dump(ahp_weights_snapshot or {}),
            ahp_consistency_ratio,
            ahp_profile_status_at_run,
            ahp_profile_source,
            decision_policy_id,
            input_data_hash,
            status,
            _now(),
            created_by,
        ),
    )
    return int(cur.lastrowid)


def mark_decision_run_completed(cur: sqlite3.Cursor, run_id: int, summary: dict[str, Any]) -> None:
    cur.execute(
        """
        UPDATE decision_runs
        SET status = 'completed', completed_at = ?, summary_json = ?, error_message = NULL
        WHERE id = ?
        """,
        (_now(), _json_dump(summary), int(run_id)),
    )


def mark_decision_run_failed(cur: sqlite3.Cursor, run_id: int, error_message: str, summary: dict[str, Any] | None = None) -> None:
    cur.execute(
        """
        UPDATE decision_runs
        SET status = 'failed', completed_at = ?, summary_json = ?, error_message = ?
        WHERE id = ?
        """,
        (_now(), _json_dump(summary or {}), str(error_message), int(run_id)),
    )


def record_decision_run_for_faculty_year(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None,
    semester: str | None = "Guz",
    department_id: int | None = None,
    generation_result: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    ahp_profile = resolve_ahp_profile(conn, faculty_id=faculty_id, department_id=department_id, year=year)
    policy = resolve_decision_policy(conn, faculty_id=faculty_id, department_id=department_id, year=year)

    # PHASE 1: Veri olgunluğunu değerlendir
    readiness_result = assess_data_readiness_cursor(
        cur=cur,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )

    from app.services.calculation import get_faculty_year_topsis_results

    score_pack = get_faculty_year_topsis_results(
        cur=cur,
        fakulte_id=int(faculty_id) if faculty_id is not None else 0,
        akademik_yil=int(year),
        donem=semester,
    )
    if not score_pack.get("ok"):
        raise RuntimeError(score_pack.get("error", "TOPSIS skorlari uretilemedi."))

    skor_map = {int(k): float(v or 0.0) for k, v in dict(score_pack.get("scores", {})).items()}
    metric_map = {int(k): dict(v) for k, v in dict(score_pack.get("metric_map", {})).items()}
    course_ids = sorted(metric_map.keys())
    meta_map = _course_meta(cur, course_ids)

    input_hash = _hash_payload(
        {
            "year": int(year),
            "faculty_id": faculty_id,
            "department_id": department_id,
            "semester": _normalize_semester(semester),
            "scores": skor_map,
            "metrics": metric_map,
            "ahp_profile_id": ahp_profile["id"],
            "policy_id": policy["id"],
        }
    )
    run_id = create_decision_run(
        cur=cur,
        run_name=f"{year} {faculty_id or 'genel'} {_normalize_semester(semester)} karar calismasi",
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
        ahp_profile_id=int(ahp_profile["id"]),
        decision_policy_id=int(policy["id"]),
        input_data_hash=input_hash,
        created_by=created_by,
        ahp_profile_version=int(ahp_profile.get("version") or 1),
        ahp_weights_snapshot=dict(ahp_profile.get("weights") or {}),
        ahp_consistency_ratio=ahp_profile.get("consistency_ratio"),
        ahp_profile_status_at_run=str(ahp_profile.get("status") or ""),
        ahp_profile_source=str(ahp_profile.get("source") or ""),
    )

    criteria_keys = [key for key in ahp_profile.get("criteria_keys", DEFAULT_CRITERIA_KEYS) if key in DEFAULT_CRITERIA_KEYS]
    if not criteria_keys:
        criteria_keys = list(DEFAULT_CRITERIA_KEYS)
    weights = {key: float(ahp_profile["weights"].get(key, 0.0)) for key in criteria_keys}
    course_rows = []
    for course_id in course_ids:
        row = {"course_id": course_id, "ders_id": course_id}
        row.update(metric_map.get(course_id, {}))
        course_rows.append(row)
    breakdowns = calculate_topsis_breakdowns(course_rows, weights=weights, criteria_keys=criteria_keys)

    # PHASE 1: Veri kapsama raporunu hesapla
    coverage_report = generate_coverage_report_cursor(
        cur=cur,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )
    save_data_coverage_report(cur, int(year), faculty_id, department_id, semester, coverage_report)

    inserted = 0
    approval_count = 0
    low_confidence_count = 0
    sensitive_count = 0
    status_counts: dict[str, int] = {}

    for course_id in course_ids:
        meta = meta_map.get(course_id, {})
        department = meta.get("department_id")
        score = float(skor_map.get(course_id, 0.0))
        classification = classify_score(score, policy)
        old_status = _old_status(cur, course_id, int(year), faculty_id, semester)
        governance = _fetch_governance_flags(cur, course_id)
        first_seen = _first_seen_year(cur, course_id)
        confidence = calculate_course_data_confidence(cur, course_id, int(year), semester, policy=policy)
        trend = analyze_course_trend(cur, course_id, int(year))
        breakdown = breakdowns.get(course_id, {})
        if breakdown:
            breakdown["final_score"] = score
        sensitivity = analyze_decision_sensitivity(
            score=score,
            policy=policy,
            weights=dict(breakdown.get("weights") or weights),
            raw_values=dict(breakdown.get("raw_values") or metric_map.get(course_id, {})),
        )
        governance_result = _apply_governance(
            recommended_status=int(classification["recommended_status"]),
            old_status=old_status,
            year=int(year),
            policy=policy,
            governance=governance,
            confidence=confidence,
            first_seen_year=first_seen,
            sensitivity=sensitivity,
        )
        if confidence["level"] == "low":
            low_confidence_count += 1
        if sensitivity["stability_level"] == "low":
            sensitive_count += 1
        if governance_result["approval_required"]:
            approval_count += 1

        decision_payload = {
            "course_id": course_id,
            "recommended_status": int(classification["recommended_status"]),
            "final_status": int(governance_result["final_status"]),
            "topsis_score": score,
            "trend_score": float(trend.get("trend_score") or 0.0),
            "trend_label": str(trend.get("trend_label") or ""),
            "data_confidence_score": float(confidence.get("score") or 0.0),
            "decision_stability": str(sensitivity.get("stability_level") or "medium"),
            "approval_required": bool(governance_result["approval_required"]),
            "approval_reason": governance_result["approval_reason"],
            "main_reason": classification["reason"],
            "rule_triggered": classification["rule_triggered"],
        }
        explanation = build_decision_explanation(
            course_code=meta.get("code"),
            course_name=meta.get("name"),
            decision=decision_payload,
            breakdown=breakdown,
            trend=trend,
            confidence=confidence,
            governance=governance,
        )
        main_reason = explanation.get("main_reason") or classification["reason"]
        cur.execute(
            """
            INSERT INTO course_decisions (
                decision_run_id, course_id, year, faculty_id, department_id, semester,
                old_status, recommended_status, final_status, topsis_score,
                trend_score, trend_label, data_confidence_score, decision_stability,
                approval_required, approval_status, approval_reason,
                override_applied, override_reason, main_reason, rule_triggered
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(run_id),
                int(course_id),
                int(year),
                faculty_id,
                department,
                _normalize_semester(semester),
                old_status,
                int(classification["recommended_status"]),
                int(governance_result["final_status"]),
                score,
                float(trend.get("trend_score") or 0.0),
                str(trend.get("trend_label") or ""),
                float(confidence.get("score") or 0.0),
                str(sensitivity.get("stability_level") or "medium"),
                1 if governance_result["approval_required"] else 0,
                governance_result["approval_status"],
                governance_result["approval_reason"],
                1 if int(governance_result["final_status"]) != int(classification["recommended_status"]) else 0,
                governance_result["approval_reason"],
                str(main_reason),
                str(classification["rule_triggered"]),
            ),
        )
        decision_id = int(cur.lastrowid)

        if breakdown:
            save_score_breakdown(
                cur,
                run_id,
                course_id,
                int(year),
                faculty_id,
                department,
                breakdown,
                ahp_profile_id=int(ahp_profile["id"]),
            )
        save_trend_analysis(cur, run_id, course_id, int(year), trend)
        save_data_confidence(cur, run_id, course_id, int(year), confidence)
        save_sensitivity_result(cur, run_id, course_id, sensitivity)
        save_decision_explanation(cur, decision_id, explanation)

        inserted += 1
        status_key = str(governance_result["final_status"])
        status_counts[status_key] = status_counts.get(status_key, 0) + 1

    fairness = generate_fairness_report(cur, run_id, int(year), faculty_id, department_id)
    save_fairness_report(cur, run_id, faculty_id, department_id, int(year), fairness)
    summary = {
        "course_count": inserted,
        "approval_required_count": approval_count,
        "low_data_confidence_count": low_confidence_count,
        "sensitive_decision_count": sensitive_count,
        "status_counts": status_counts,
        "generation_result": generation_result or {},
        "fairness_summary": fairness.get("summary_text"),
    }
    mark_decision_run_completed(cur, run_id, summary)
    return {
        "ok": True,
        "decision_run_id": int(run_id),
        "summary": summary,
        "ahp_profile": ahp_profile,
        "decision_policy": policy,
    }


def record_failed_decision_run(
    db_path: str,
    year: int,
    faculty_id: int | None,
    semester: str | None,
    error_message: str,
    department_id: int | None = None,
) -> dict[str, Any]:
    conn = get_raw_connection(db_path)
    conn.row_factory = sqlite3.Row
    try:
        ensure_ahp_governance_schema(conn, commit=False)
        ahp_profile = resolve_ahp_profile(conn, faculty_id=faculty_id, department_id=department_id, year=year)
        policy = resolve_decision_policy(conn, faculty_id=faculty_id, department_id=department_id, year=year)
        cur = conn.cursor()
        run_id = create_decision_run(
            cur,
            run_name=f"{year} {faculty_id or 'genel'} basarisiz karar calismasi",
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=semester,
            ahp_profile_id=int(ahp_profile["id"]),
            decision_policy_id=int(policy["id"]),
            input_data_hash=None,
            status="failed",
            ahp_profile_version=int(ahp_profile.get("version") or 1),
            ahp_weights_snapshot=dict(ahp_profile.get("weights") or {}),
            ahp_consistency_ratio=ahp_profile.get("consistency_ratio"),
            ahp_profile_status_at_run=str(ahp_profile.get("status") or ""),
            ahp_profile_source=str(ahp_profile.get("source") or ""),
        )
        mark_decision_run_failed(cur, run_id, error_message)
        conn.commit()
        return {"ok": False, "decision_run_id": int(run_id), "error": str(error_message)}
    finally:
        conn.close()


def list_decision_runs(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT dr.*, ap.name AS ahp_profile_name, dp.name AS decision_policy_name
        FROM decision_runs dr
        LEFT JOIN ahp_weight_profiles ap ON ap.id = dr.ahp_profile_id
        LEFT JOIN decision_policies dp ON dp.id = dr.decision_policy_id
        ORDER BY dr.id DESC
        LIMIT ?
        """,
        (int(limit),),
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def get_decision_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_runs WHERE id = ?", (int(run_id),))
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def list_course_decisions(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cd.*, d.kod AS course_code, d.ad AS course_name,
               e.human_readable_text
        FROM course_decisions cd
        LEFT JOIN ders d ON d.ders_id = cd.course_id
        LEFT JOIN course_decision_explanations e ON e.course_decision_id = cd.id
        WHERE cd.decision_run_id = ?
        ORDER BY cd.approval_required DESC, cd.topsis_score DESC, d.ad
        """,
        (int(run_id),),
    )
    return [_row_to_dict(row) for row in cur.fetchall()]


def get_course_decision_explanation(conn: sqlite3.Connection, decision_id: int) -> dict[str, Any] | None:
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM course_decision_explanations
        WHERE course_decision_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(decision_id),),
    )
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def execute_decision_run(
    db_path: str,
    year: int,
    faculty_id: int,
    semester: str | None = "Guz",
) -> dict[str, Any]:
    from app.services.calculation import generate_next_year_curricula

    result = generate_next_year_curricula(
        db_path=db_path,
        fakulte_id=int(faculty_id),
        akademik_yil=int(year),
        donem=semester or "Guz",
    )
    if not result.get("ok"):
        record_failed_decision_run(db_path, year, faculty_id, semester, result.get("error", "Bilinmeyen hata"))
        return result
    return result


def safe_record_decision_run(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None,
    semester: str | None,
    generation_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return record_decision_run_for_faculty_year(
            conn=conn,
            year=int(year),
            faculty_id=faculty_id,
            semester=semester,
            generation_result=generation_result,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

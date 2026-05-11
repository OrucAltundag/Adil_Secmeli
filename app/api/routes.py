# =============================================================================
# app/api/routes.py - REST API Endpoint Tanimlari
# =============================================================================

from __future__ import annotations

import os
import sqlite3
from typing import Any, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile, Depends
from app.schemas.auth import UserContext
from app.services.permission_service import require_action

from app.core.config import load_app_config
from app.core.settings import load_settings
from app.db.session import open_sqlite_connection
from app.db.sqlite_connection import connect_sqlite
from app.db.schema_compat import ensure_reporting_schema
from app.schemas.common import ApiResponse
from app.schemas.ahp import (
    AHPApprovalRequest,
    AHPCalculateRequest,
    AHPCloneRequest,
    AHPCriterionRequest,
    AHPProfileCreateRequest,
    AHPProfileUpdateRequest,
    AHPRejectRequest,
    AHPSensitivityRequest,
)
from app.services.calculation import run_all_algorithms_for_year
from app.services.course_service import CourseService
from app.services.course_type import build_elective_predicate
from app.services.curriculum_import_service import import_curriculum_excel
from app.services.survey_import_service import import_survey_excel
from app.services.ahp_profile_service import (
    activate_ahp_profile,
    approve_profile,
    archive_profile,
    clone_profile,
    create_profile,
    create_ahp_profile,
    get_profile,
    list_stale_decisions,
    list_ahp_profiles,
    reject_profile,
    resolve_active_profile,
    resolve_stale_decision,
    submit_for_approval,
    update_profile,
    validate_profile,
)
from app.services.ahp_calculation_service import calculate_weights_from_pairwise_matrix, validate_pairwise_matrix
from app.services.ahp_impact_explanation_service import explain_course_weight_contribution, explain_weight_profile
from app.services.ahp_sensitivity_service import get_latest_sensitivity_for_run, run_weight_sensitivity_analysis
from app.services.criteria_definition_service import (
    create_or_update_criterion,
    deactivate_criterion,
    list_active_criteria,
)
from app.services.yearly_workflow import (
    get_faculty_year_status,
    list_active_years_for_faculty,
)
from app.services.decision_policy_service import (
    activate_decision_policy,
    create_decision_policy,
    list_decision_policies,
)
from app.services.decision_run_service import (
    get_course_decision_explanation,
    get_decision_run,
    list_course_decisions,
    list_decision_runs,
)
from app.services.import_audit_service import (
    activate_import,
    approve_import,
    get_import_batch,
    list_import_batches,
    list_import_issues,
    list_import_rows,
    preview_import,
    reject_import,
    save_upload_to_temp,
    update_import_status,
    validate_import,
)
from app.services.import_diff_service import get_import_diff, recalculate_import_diff
from app.services.import_impact_service import get_import_impact, recalculate_import_impact
from app.services.import_lineage_service import list_value_sources
from app.services.import_quality_service import evaluate_import_quality, summarize_quality
from app.services.import_rollback_service import get_rollback_plan, rollback_import
from app.services.criteria_completion_service import (
    can_run_algorithm as criteria_can_run_algorithm,
    get_completion_history,
    get_completion_matrix,
    get_completion_summary,
    get_validation_issues,
)
from app.services.criteria_completion_policy_service import (
    activate_completion_policy,
    create_completion_policy,
    list_completion_policies,
)
from app.services.criteria_override_service import (
    approve_override,
    list_overrides,
    reject_override,
    request_override,
)
from app.services.criteria_task_service import (
    generate_tasks_for_missing_criteria,
    get_tasks,
    update_task_status,
)
from app.services.missing_data_risk_service import get_missing_data_risk_report
from app.services.pool_state_machine_service import (
    approve_state_approval,
    create_course_state_override,
    evaluate_course_state_transition,
    evaluate_scope_transitions,
    get_course_state_history,
    get_governance_flags,
    get_pool_lifecycle_summary,
    get_protected_courses,
    get_reactivation_candidates,
    list_overrides as list_pool_overrides,
    list_pending_approvals as list_pool_pending_approvals,
    list_state_transitions,
    reject_state_approval,
    upsert_governance_flags,
)
from app.services.pool_state_policy_service import (
    activate_pool_state_policy,
    create_pool_state_policy,
    list_pool_state_policies,
)
from app.services.system_service import SystemService
from app.schemas.ml import (
    MLAlgorithmUpdateRequest,
    MLFeatureSnapshotRequest,
    MLPredictBatchRequest,
    MLPredictCourseRequest,
    MLReadinessReportRequest,
    MLTrainRequest,
)
from app.schemas.algorithm_governance import (
    AlgorithmGovernanceUpdateRequest,
    DataGuardCheckRequest,
    GovernedBenchmarkRunRequest,
)
from app.schemas.semester_planning import (
    CourseAvailabilityRequest,
    InstructorAvailabilityRequest,
    InstructorRequest,
    PrerequisiteRequest,
    ResourceRequirementRequest,
    SemesterPlanGenerateRequest,
    SemesterPlanningPolicyRequest,
    TeachingResourceRequest,
)
from app.services.algorithm_data_guard_service import check_data_requirements
from app.services.algorithm_governance_report_service import (
    generate_algorithm_role_report,
    generate_benchmark_statistical_report,
    generate_clustering_report,
)
from app.services.algorithm_governance_service import (
    get_algorithm_governance,
    get_allowed_algorithms_for_task,
    list_algorithm_governance,
    list_task_mappings,
    seed_default_algorithm_registry as seed_default_governance_registry,
    update_algorithm_role,
)
from app.services.governed_benchmark_service import (
    execute_governed_benchmark_run,
    get_governed_benchmark_run,
    get_governed_run_clustering,
    get_governed_run_diagnostics,
    get_governed_run_leakage,
    get_governed_run_metrics,
    get_governed_run_report,
    get_governed_run_statistics,
    get_governed_run_validation,
    list_governed_benchmark_runs,
)
from app.services.ml_algorithm_registry_service import (
    list_algorithm_registry,
    seed_default_algorithm_registry,
    update_algorithm_usage_role,
)
from app.services.ml_explainability_service import get_prediction_explanation
from app.services.ml_feature_pipeline import build_course_feature_dataset, save_feature_snapshot
from app.services.ml_model_registry_service import (
    deprecate_model_run,
    get_model_run,
    list_model_runs,
)
from app.services.ml_prediction_service import list_predictions, predict_batch, predict_course
from app.services.ml_readiness_report_service import (
    generate_ml_readiness_report,
    get_algorithm_readiness_table,
    get_readiness_report,
    list_readiness_reports,
)
from app.services.ml_training_service import train_model_run
from app.services.course_semester_availability_service import list_availability_by_scope, upsert_course_availability
from app.services.instructor_planning_service import (
    create_instructor,
    list_instructor_availability,
    list_instructors,
    upsert_instructor_availability,
)
from app.services.prerequisite_planning_service import create_prerequisite, get_prerequisites
from app.services.resource_planning_service import (
    create_resource,
    create_resource_requirement,
    list_resource_requirements,
    list_resources,
)
from app.services.semester_planning_engine import generate_semester_plan, get_plan_run, list_plan_runs
from app.services.semester_planning_policy_service import (
    activate_policy as activate_semester_planning_policy,
    create_policy as create_semester_planning_policy,
    list_policies as list_semester_planning_policies,
    update_policy as update_semester_planning_policy,
)
from app.services.semester_planning_reporting_service import (
    compare_plan_scenarios,
    get_constraint_violations,
    get_semester_plan_assignments,
    get_semester_plan_summary,
)

router = APIRouter()


def _normalize_donem(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("b"):
        return "Bahar"
    return "Guz"


def _donem_key(value: str | None) -> str:
    return "b" if _normalize_donem(value) == "Bahar" else "g"


def _get_db_path() -> str:
    settings = load_settings(config_path="config.json")
    return settings.db_path


def _open_connection() -> sqlite3.Connection:
    path = _get_db_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail="Veritabani bulunamadi")
    conn = connect_sqlite(path, row_factory=True)
    ensure_reporting_schema(conn)
    return conn


def _run_query(query: str, params: tuple = ()) -> tuple[list[str], list[list]]:
    conn = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [list(r) for r in rows]
    finally:
        conn.close()


def _havuz_has_donem(conn: sqlite3.Connection) -> bool:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(havuz)")
    return "donem" in {str(row[1]) for row in cur.fetchall()}


@router.get("/dersler")
def ders_listesi(fakulte_id: Optional[int] = None, secmeli_only: bool = False):
    conn = _open_connection()
    try:
        rows = CourseService(conn).list_courses(faculty_id=fakulte_id, elective_only=secmeli_only).unwrap()
        cols = list(rows[0].keys()) if rows else ["ders_id", "kod", "ad", "kredi", "akts", "fakulte_id", "bolum_id", "course_type"]
        return {"columns": cols, "data": [[row.get(col) for col in cols] for row in rows]}
    finally:
        conn.close()


@router.get("/skorlar")
def skor_listesi(akademik_yil: Optional[int] = None, donem: Optional[str] = None):
    q = """
        SELECT s.ders_id, d.ad, s.akademik_yil, s.donem,
               s.b_norm, s.p_norm, s.a_norm, s.g_norm, s.skor_top
        FROM skor s
        JOIN ders d ON s.ders_id = d.ders_id
        WHERE 1=1
    """
    params: list = []
    if akademik_yil:
        q += " AND s.akademik_yil = ?"
        params.append(int(akademik_yil))
    if donem:
        q += " AND LOWER(SUBSTR(TRIM(COALESCE(s.donem, '')), 1, 1)) = ?"
        params.append(_donem_key(donem))
    q += " ORDER BY s.skor_top DESC"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


@router.get("/havuz")
def havuz_listesi(
    yil: int,
    fakulte_id: Optional[int] = None,
    bolum_id: Optional[int] = None,
    donem: Optional[str] = None,
):
    conn = _open_connection()
    try:
        use_term = bool(donem) and _havuz_has_donem(conn)
        cur = conn.cursor()
        elective_predicate = build_elective_predicate(cur=cur, alias="d")
        q = f"""
            SELECT
                h.ders_id,
                d.ad,
                h.yil,
                h.fakulte_id,
                h.donem,
                h.statu,
                h.sayac,
                h.skor,
                COALESCE(d.bolum_id, h.bolum_id) AS kaynak_bolum_id,
                b.ad AS kaynak_bolum
            FROM havuz h
            LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
            LEFT JOIN bolum b ON b.bolum_id = COALESCE(d.bolum_id, h.bolum_id)
            WHERE h.yil = ?
              AND {elective_predicate}
        """
        params: list = [int(yil)]
        if fakulte_id is not None:
            q += " AND h.fakulte_id = ?"
            params.append(int(fakulte_id))
        if bolum_id is not None:
            q += " AND COALESCE(d.bolum_id, h.bolum_id) = ?"
            params.append(int(bolum_id))
        if use_term:
            q += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
            params.append(_donem_key(donem))
        q += " ORDER BY CASE WHEN h.skor IS NULL THEN 1 ELSE 0 END, h.skor DESC, h.statu DESC, d.ad"

        cur.execute(q, tuple(params))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return {"columns": cols, "data": [list(r) for r in rows]}
    finally:
        conn.close()


@router.get("/mufredat")
def mufredat_listesi(akademik_yil: int, bolum_id: Optional[int] = None, donem: Optional[str] = None):
    q = """
        SELECT md.mders_id, m.akademik_yil, m.bolum_id, m.donem, md.ders_id, d.ad
        FROM mufredat m
        JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
        JOIN ders d ON md.ders_id = d.ders_id
        WHERE m.akademik_yil = ?
    """
    params: list = [int(akademik_yil)]
    if bolum_id is not None:
        q += " AND m.bolum_id = ?"
        params.append(int(bolum_id))
    if donem:
        q += " AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?"
        params.append(_donem_key(donem))
    q += " ORDER BY d.ad"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


@router.get("/akademik-plan")
def akademik_plan(fakulte_id: int, yil: int):
    conn = _open_connection()
    try:
        cur = conn.cursor()
        out = {"fakulte_id": int(fakulte_id), "yil": int(yil), "guz": [], "bahar": [], "overlap_count": 0}
        for term in ("g", "b"):
            cur.execute(
                """
                SELECT DISTINCT md.ders_id, d.ad
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                JOIN ders d ON d.ders_id = md.ders_id
                WHERE b.fakulte_id = ?
                  AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
                ORDER BY d.ad
                """,
                (int(fakulte_id), int(yil), term),
            )
            rows = [{"ders_id": int(r[0]), "ders_adi": str(r[1] or "")} for r in cur.fetchall()]
            if term == "g":
                out["guz"] = rows
            else:
                out["bahar"] = rows

        guz_ids = {int(item["ders_id"]) for item in out["guz"]}
        bahar_ids = {int(item["ders_id"]) for item in out["bahar"]}
        out["overlap_count"] = len(guz_ids & bahar_ids)
        out["guz_count"] = len(guz_ids)
        out["bahar_count"] = len(bahar_ids)
        out["balanced_4_plus_4"] = out["guz_count"] == 4 and out["bahar_count"] == 4 and out["overlap_count"] == 0
        return out
    finally:
        conn.close()


@router.get("/fakulteler")
def fakulte_listesi():
    conn = _open_connection()
    try:
        rows = CourseService(conn).list_faculties().unwrap()
        cols = list(rows[0].keys()) if rows else ["fakulte_id", "ad", "kampus"]
        return {"columns": cols, "data": [[row.get(col) for col in cols] for row in rows]}
    finally:
        conn.close()


@router.get("/health")
def health():
    conn = _open_connection()
    try:
        result = SystemService(conn=conn, config=load_app_config()).health()
        return result.to_api()
    finally:
        conn.close()


@router.get("/system/info")
def system_info():
    conn = _open_connection()
    try:
        result = SystemService(conn=conn, config=load_app_config()).health()
        return result.to_api()
    finally:
        conn.close()


@router.get("/system/health")
def system_health():
    conn = _open_connection()
    try:
        result = SystemService(conn=conn, config=load_app_config()).health()
        return result.to_api()
    finally:
        conn.close()


@router.get("/system/schema-health")
def system_schema_health():
    conn = _open_connection()
    try:
        result = SystemService(conn=conn, config=load_app_config()).schema_health()
        return result.to_api()
    finally:
        conn.close()


@router.get("/system/architecture-audit")
def system_architecture_audit():
    result = SystemService(config=load_app_config()).architecture_audit()
    return result.to_api()


@router.get("/system/config-summary")
def system_config_summary():
    result = SystemService(config=load_app_config()).config_summary()
    return result.to_api()


@router.get("/system/sql-console/audit-logs")
def system_sql_console_audit_logs(limit: int = 50):
    conn = _open_connection()
    try:
        result = SystemService(conn=conn, config=load_app_config()).sql_console_audit_logs(limit=limit)
        return result.to_api()
    finally:
        conn.close()


@router.get("/kriter/durum")
def kriter_durumu(fakulte_id: int, yil: int):
    conn = _open_connection()
    try:
        status = get_faculty_year_status(
            conn=conn,
            fakulte_id=int(fakulte_id),
            yil=int(yil),
            refresh=True,
        )
        return status
    finally:
        conn.close()


@router.get("/kriter/tamlik")
def kriter_tamlik(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        scope = "department" if department_id is not None else "faculty"
        return get_completion_summary(
            conn,
            scope_type=scope,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=_normalize_donem(semester) if semester else None,
            refresh=True,
        )
    finally:
        conn.close()


@router.get("/kriter/tamlik/matrix")
def kriter_tamlik_matrix(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        scope = "department" if department_id is not None else "faculty"
        return {
            "data": get_completion_matrix(
                conn,
                scope_type=scope,
                year=int(year),
                faculty_id=faculty_id,
                department_id=department_id,
                semester=_normalize_donem(semester) if semester else None,
                refresh=True,
            )
        }
    finally:
        conn.close()


@router.get("/kriter/tamlik/issues")
def kriter_tamlik_issues(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        scope = "department" if department_id is not None else "faculty"
        return {
            "data": get_validation_issues(
                conn,
                scope_type=scope,
                year=int(year),
                faculty_id=faculty_id,
                department_id=department_id,
                semester=_normalize_donem(semester) if semester else None,
                refresh=True,
            )
        }
    finally:
        conn.close()


@router.post("/kriter/tamlik/validate")
def kriter_tamlik_validate(payload: dict[str, Any] = Body(default_factory=dict)):
    year = payload.get("year") or payload.get("yil")
    if year is None:
        raise HTTPException(status_code=400, detail="year/yil zorunludur")
    faculty_id = payload.get("faculty_id") or payload.get("fakulte_id")
    department_id = payload.get("department_id") or payload.get("bolum_id")
    semester = payload.get("semester") or payload.get("donem")
    conn = _open_connection()
    try:
        scope = "department" if department_id is not None else "faculty"
        summary = get_completion_summary(
            conn,
            scope_type=scope,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=_normalize_donem(semester) if semester else None,
            refresh=True,
        )
        conn.commit()
        return summary
    finally:
        conn.close()


@router.get("/kriter/tamlik/policies")
def kriter_tamlik_policies():
    conn = _open_connection()
    try:
        return {"data": list_completion_policies(conn)}
    finally:
        conn.close()


@router.post("/kriter/tamlik/policies")
def kriter_tamlik_policy_create(payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        policy = create_completion_policy(
            conn,
            name=str(payload.get("name") or "Yeni Kriter Tamlık Politikası"),
            scope_type=str(payload.get("scope_type") or "global"),
            faculty_id=payload.get("faculty_id") or payload.get("fakulte_id"),
            department_id=payload.get("department_id") or payload.get("bolum_id"),
            year=payload.get("year") or payload.get("yil"),
            semester=payload.get("semester") or payload.get("donem"),
            required_completion_ratio=float(payload.get("required_completion_ratio", 1.0)),
            required_fields=payload.get("required_fields"),
            optional_fields=payload.get("optional_fields"),
            allow_new_course_missing_history=bool(payload.get("allow_new_course_missing_history", True)),
            new_course_grace_period_years=int(payload.get("new_course_grace_period_years", 2)),
            min_survey_response_count=payload.get("min_survey_response_count"),
            block_on_invalid_numeric=bool(payload.get("block_on_invalid_numeric", True)),
            block_on_critical_issues=bool(payload.get("block_on_critical_issues", True)),
            allow_override=bool(payload.get("allow_override", True)),
            override_requires_reason=bool(payload.get("override_requires_reason", True)),
            override_requires_approval=bool(payload.get("override_requires_approval", True)),
            notes=payload.get("notes"),
            activate=bool(payload.get("activate", True)),
        )
        conn.commit()
        return policy
    finally:
        conn.close()


@router.post("/kriter/tamlik/policies/{policy_id}/activate")
def kriter_tamlik_policy_activate(policy_id: int):
    conn = _open_connection()
    try:
        result = activate_completion_policy(conn, int(policy_id))
        conn.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.get("/kriter/tamlik/risk")
def kriter_tamlik_risk(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        scope = "department" if department_id is not None else "faculty"
        summary = get_completion_summary(
            conn,
            scope_type=scope,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=_normalize_donem(semester) if semester else None,
            refresh=True,
        )
        report = get_missing_data_risk_report(
            conn,
            scope_type=scope,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=_normalize_donem(semester) if semester else None,
        )
        return report or summary.get("missing_data_risk") or {}
    finally:
        conn.close()


@router.get("/kriter/tamlik/tasks")
def kriter_tamlik_tasks(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
):
    conn = _open_connection()
    try:
        return {"data": get_tasks(conn, year=year, faculty_id=faculty_id, department_id=department_id, status=status)}
    finally:
        conn.close()


@router.post("/kriter/tamlik/tasks")
def kriter_tamlik_task_create(payload: dict[str, Any] = Body(default_factory=dict)):
    year = payload.get("year") or payload.get("yil")
    faculty_id = payload.get("faculty_id") or payload.get("fakulte_id")
    department_id = payload.get("department_id") or payload.get("bolum_id")
    if year is None or faculty_id is None:
        raise HTTPException(status_code=400, detail="year/yil ve faculty_id/fakulte_id zorunludur")
    conn = _open_connection()
    try:
        scope = "department" if department_id is not None else "faculty"
        summary = get_completion_summary(
            conn,
            scope_type=scope,
            year=int(year),
            faculty_id=int(faculty_id),
            department_id=int(department_id) if department_id is not None else None,
            semester=payload.get("semester") or payload.get("donem"),
            refresh=True,
        )
        tasks = generate_tasks_for_missing_criteria(
            conn,
            summary,
            assigned_role=payload.get("assigned_role"),
            created_by=payload.get("created_by"),
        )
        conn.commit()
        return {"data": tasks}
    finally:
        conn.close()


@router.patch("/kriter/tamlik/tasks/{task_id}")
def kriter_tamlik_task_update(task_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status zorunludur")
    conn = _open_connection()
    try:
        task = update_task_status(
            conn,
            int(task_id),
            status=str(status),
            notes=payload.get("notes"),
            approved_by=payload.get("approved_by"),
        )
        conn.commit()
        return task
    finally:
        conn.close()


@router.get("/kriter/tamlik/overrides")
def kriter_tamlik_overrides(
    scope_type: Optional[str] = None,
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    approval_status: Optional[str] = None,
):
    conn = _open_connection()
    try:
        return {
            "data": list_overrides(
                conn,
                scope_type=scope_type,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
                approval_status=approval_status,
            )
        }
    finally:
        conn.close()


@router.post("/kriter/tamlik/overrides/request")
def kriter_tamlik_override_request(payload: dict[str, Any] = Body(default_factory=dict)):
    year = payload.get("year") or payload.get("yil")
    reason = str(payload.get("reason") or "").strip()
    if year is None or not reason:
        raise HTTPException(status_code=400, detail="year/yil ve reason zorunludur")
    conn = _open_connection()
    try:
        override = request_override(
            conn,
            scope_type=str(payload.get("scope_type") or ("department" if payload.get("department_id") or payload.get("bolum_id") else "faculty")),
            year=int(year),
            faculty_id=payload.get("faculty_id") or payload.get("fakulte_id"),
            department_id=payload.get("department_id") or payload.get("bolum_id"),
            course_id=payload.get("course_id") or payload.get("ders_id"),
            semester=payload.get("semester") or payload.get("donem"),
            missing_fields=payload.get("missing_fields"),
            validation_issues=payload.get("validation_issues"),
            reason=reason,
            requested_by=payload.get("requested_by"),
            expires_at=payload.get("expires_at"),
        )
        conn.commit()
        return override
    finally:
        conn.close()


@router.post("/kriter/tamlik/overrides/{override_id}/approve")
def kriter_tamlik_override_approve(override_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        override = approve_override(conn, int(override_id), approved_by=payload.get("approved_by"))
        conn.commit()
        return override
    finally:
        conn.close()


@router.post("/kriter/tamlik/overrides/{override_id}/reject")
def kriter_tamlik_override_reject(override_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    reason = str(payload.get("rejection_reason") or payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Reddetme gerekçesi zorunludur")
    conn = _open_connection()
    try:
        override = reject_override(
            conn,
            int(override_id),
            rejection_reason=reason,
            rejected_by=payload.get("rejected_by"),
        )
        conn.commit()
        return override
    finally:
        conn.close()


@router.get("/kriter/tamlik/history")
def kriter_tamlik_history(
    scope_type: Optional[str] = None,
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        return {
            "data": get_completion_history(
                conn,
                scope_type=scope_type,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
                semester=_normalize_donem(semester) if semester else None,
            )
        }
    finally:
        conn.close()


@router.get("/kriter/tamlik/can-run")
def kriter_tamlik_can_run(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        return criteria_can_run_algorithm(
            conn,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=_normalize_donem(semester) if semester else None,
            scope_type="department" if department_id is not None else "faculty",
        )
    finally:
        conn.close()


@router.get("/yillar/aktif")
def aktif_yillar(fakulte_id: int):
    conn = _open_connection()
    try:
        years = list_active_years_for_faculty(conn=conn, fakulte_id=int(fakulte_id))
        return {"fakulte_id": int(fakulte_id), "years": years}
    finally:
        conn.close()


@router.post("/algoritma/tumunu-calistir")
def algoritma_tumunu_calistir(yil: int, donem: Optional[str] = "Guz", user: UserContext = Depends(require_action("run_algorithm"))):
    result = run_all_algorithms_for_year(
        yil=int(yil),
        db_path=_get_db_path(),
        donem=_normalize_donem(donem),
    )
    if not result.get("ok") and not result.get("processed"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/mufredat/yukle")
async def mufredat_yukle(file: UploadFile = File(...), hedef_yil: int = Form(...), user: UserContext = Depends(require_action("import_data"))):
    filename = str(file.filename or "")
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Sadece .xlsx dosyasi desteklenir")

    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Veritabani bulunamadi")

    import tempfile

    fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        content = await file.read()
        with open(temp_path, "wb") as fh:
            fh.write(content)
        result = import_curriculum_excel(
            db_path=db_path,
            excel_path=temp_path,
            target_year=int(hedef_yil),
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@router.post("/anket/yukle")
async def anket_yukle(
    file: UploadFile = File(...),
    fakulte_id: int = Form(...),
    hedef_yil: int = Form(...),
):
    filename = str(file.filename or "")
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Sadece .xlsx dosyasi desteklenir")

    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Veritabani bulunamadi")

    import tempfile

    fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        content = await file.read()
        with open(temp_path, "wb") as fh:
            fh.write(content)
        result = import_survey_excel(
            db_path=db_path,
            excel_path=temp_path,
            faculty_id=int(fakulte_id),
            year=int(hedef_yil),
            source_filename=filename,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@router.get("/decision/ahp-profiles")
def decision_ahp_profiles():
    conn = _open_connection()
    try:
        return {"data": list_ahp_profiles(conn)}
    finally:
        conn.close()


@router.post("/decision/ahp-profiles")
def decision_ahp_profile_create(payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        profile = create_ahp_profile(
            conn=conn,
            name=str(payload.get("name") or "Yeni AHP Profili"),
            scope_type=str(payload.get("scope_type") or "global"),
            faculty_id=payload.get("faculty_id"),
            department_id=payload.get("department_id"),
            year=payload.get("year"),
            criteria_keys=payload.get("criteria_keys"),
            pairwise_matrix=payload.get("pairwise_matrix"),
            weights=payload.get("weights"),
            source=str(payload.get("source") or "manual"),
            created_by=payload.get("created_by"),
            notes=payload.get("notes"),
            activate=bool(payload.get("activate", True)),
        )
        return profile
    finally:
        conn.close()


@router.post("/decision/ahp-profiles/{profile_id}/activate")
def decision_ahp_profile_activate(profile_id: int):
    conn = _open_connection()
    try:
        return activate_ahp_profile(conn, int(profile_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.get("/decision/policies")
def decision_policies():
    conn = _open_connection()
    try:
        return {"data": list_decision_policies(conn)}
    finally:
        conn.close()


@router.post("/decision/policies")
def decision_policy_create(payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        policy = create_decision_policy(
            conn=conn,
            name=str(payload.get("name") or "Yeni Karar Politikasi"),
            scope_type=str(payload.get("scope_type") or "global"),
            faculty_id=payload.get("faculty_id"),
            department_id=payload.get("department_id"),
            year=payload.get("year"),
            mode=str(payload.get("mode") or "static_threshold"),
            curriculum_keep_threshold=float(payload.get("curriculum_keep_threshold", 70.0)),
            pool_threshold=float(payload.get("pool_threshold", 50.0)),
            rest_threshold=float(payload.get("rest_threshold", 40.0)),
            cancel_candidate_threshold=payload.get("cancel_candidate_threshold", 30.0),
            min_success_rate=payload.get("min_success_rate"),
            min_survey_count=payload.get("min_survey_count"),
            min_enrollment_rate=payload.get("min_enrollment_rate"),
            new_course_grace_period_years=int(payload.get("new_course_grace_period_years", 2)),
            low_data_confidence_threshold=float(payload.get("low_data_confidence_threshold", 0.50)),
            sensitivity_margin=float(payload.get("sensitivity_margin", 3.0)),
            top_percent_curriculum=payload.get("top_percent_curriculum"),
            middle_percent_pool=payload.get("middle_percent_pool"),
            bottom_percent_rest=payload.get("bottom_percent_rest"),
            require_manual_approval_for_cancel=bool(payload.get("require_manual_approval_for_cancel", True)),
            notes=payload.get("notes"),
            activate=bool(payload.get("activate", True)),
        )
        return policy
    finally:
        conn.close()


@router.post("/decision/policies/{policy_id}/activate")
def decision_policy_activate(policy_id: int):
    conn = _open_connection()
    try:
        return activate_decision_policy(conn, int(policy_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.get("/decision/runs")
def decision_runs():
    conn = _open_connection()
    try:
        return {"data": list_decision_runs(conn)}
    finally:
        conn.close()


@router.post("/decision/runs/execute")
def decision_runs_execute(payload: dict[str, Any] = Body(default_factory=dict)):
    year = payload.get("year") or payload.get("yil")
    faculty_id = payload.get("faculty_id") or payload.get("fakulte_id")
    semester = payload.get("semester") or payload.get("donem") or "Guz"
    if year is None or faculty_id is None:
        raise HTTPException(status_code=400, detail="year/yil ve faculty_id/fakulte_id zorunludur")
    result = run_all_algorithms_for_year(
        yil=int(year),
        db_path=_get_db_path(),
        donem=_normalize_donem(str(semester)),
        fakulte_id=int(faculty_id),
    )
    if not result.get("ok") and not result.get("processed"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/decision/runs/{run_id}")
def decision_run_detail(run_id: int):
    conn = _open_connection()
    try:
        run = get_decision_run(conn, int(run_id))
        if not run:
            raise HTTPException(status_code=404, detail="Karar calistirmasi bulunamadi")
        run["summary"] = _safe_json(run.get("summary_json"), {})
        return run
    finally:
        conn.close()


@router.get("/decision/runs/{run_id}/courses")
def decision_run_courses(run_id: int):
    conn = _open_connection()
    try:
        return {"data": list_course_decisions(conn, int(run_id))}
    finally:
        conn.close()


@router.get("/decision/course-decisions/{decision_id}/explanation")
def decision_course_explanation(decision_id: int):
    conn = _open_connection()
    try:
        explanation = get_course_decision_explanation(conn, int(decision_id))
        if not explanation:
            raise HTTPException(status_code=404, detail="Aciklama bulunamadi")
        explanation["secondary_reasons"] = _safe_json(explanation.get("secondary_reasons_json"), [])
        explanation["positive_factors"] = _safe_json(explanation.get("positive_factors_json"), [])
        explanation["negative_factors"] = _safe_json(explanation.get("negative_factors_json"), [])
        return explanation
    finally:
        conn.close()


@router.get("/decision/runs/{run_id}/fairness")
def decision_run_fairness(run_id: int):
    cols, rows = _run_query(
        """
        SELECT id, decision_run_id, faculty_id, department_id, year, report_json, summary_text, created_at
        FROM decision_fairness_reports
        WHERE decision_run_id = ?
        ORDER BY id DESC
        """,
        (int(run_id),),
    )
    data = []
    for row in rows:
        item = dict(zip(cols, row))
        item["report"] = _safe_json(item.get("report_json"), {})
        data.append(item)
    return {"data": data}


@router.get("/decision/runs/{run_id}/sensitivity")
def decision_run_sensitivity(run_id: int):
    cols, rows = _run_query(
        """
        SELECT dsr.*, d.kod AS course_code, d.ad AS course_name
        FROM decision_sensitivity_results dsr
        LEFT JOIN ders d ON d.ders_id = dsr.course_id
        WHERE dsr.decision_run_id = ?
        ORDER BY CASE dsr.stability_level WHEN 'low' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                 dsr.score_range DESC
        """,
        (int(run_id),),
    )
    data = []
    for row in rows:
        item = dict(zip(cols, row))
        item["tested_variations"] = _safe_json(item.get("tested_variations_json"), [])
        data.append(item)
    return {"data": data}


@router.get("/decision/runs/{run_id}/data-confidence")
def decision_run_data_confidence(run_id: int):
    cols, rows = _run_query(
        """
        SELECT cdc.*, d.kod AS course_code, d.ad AS course_name
        FROM course_data_confidence cdc
        LEFT JOIN ders d ON d.ders_id = cdc.course_id
        WHERE cdc.decision_run_id = ?
        ORDER BY cdc.score ASC, d.ad
        """,
        (int(run_id),),
    )
    data = []
    for row in rows:
        item = dict(zip(cols, row))
        item["missing_fields"] = _safe_json(item.get("missing_fields_json"), [])
        data.append(item)
    return {"data": data}


@router.get("/imports")
def import_history(
    import_type: Optional[str] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    limit: int = 200,
):
    conn = _open_connection()
    try:
        return {
            "data": list_import_batches(
                conn,
                import_type=import_type,
                status=status,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
                limit=limit,
            )
        }
    finally:
        conn.close()


@router.post("/imports/preview")
async def import_preview(
    file: UploadFile = File(...),
    import_type: str = Form("criteria"),
    faculty_id: Optional[int] = Form(None),
    department_id: Optional[int] = Form(None),
    year: Optional[int] = Form(None),
    semester: Optional[str] = Form(None),
):
    temp_path = save_upload_to_temp(file)
    try:
        return preview_import(
            db_path=_get_db_path(),
            file_path=temp_path,
            import_type=import_type,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            semester=semester,
        )
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


@router.get("/imports/value-sources")
def import_value_sources(
    course_id: Optional[int] = None,
    year: Optional[int] = None,
    field_name: Optional[str] = None,
    active_only: bool = True,
):
    conn = _open_connection()
    try:
        return {
            "data": list_value_sources(
                conn,
                course_id=course_id,
                year=year,
                field_name=field_name,
                active_only=active_only,
            )
        }
    finally:
        conn.close()


@router.get("/courses/{course_id}/value-sources")
def course_value_sources(course_id: int, year: Optional[int] = None, active_only: bool = True):
    conn = _open_connection()
    try:
        return {"data": list_value_sources(conn, course_id=int(course_id), year=year, active_only=active_only)}
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}")
def import_detail(import_batch_id: int):
    conn = _open_connection()
    try:
        batch = get_import_batch(conn, int(import_batch_id))
        if not batch:
            raise HTTPException(status_code=404, detail="Import kaydi bulunamadi")
        batch["sheet_names"] = _safe_json(batch.get("sheet_names_json"), [])
        batch["validation_summary"] = _safe_json(batch.get("validation_summary_json"), {})
        return batch
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}/rows")
def import_rows(import_batch_id: int, limit: int = 500):
    conn = _open_connection()
    try:
        return {"data": list_import_rows(conn, int(import_batch_id), limit=limit)}
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}/issues")
def import_issues(import_batch_id: int, limit: int = 500):
    conn = _open_connection()
    try:
        return {"data": list_import_issues(conn, int(import_batch_id), limit=limit)}
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}/quality")
def import_quality(import_batch_id: int):
    conn = _open_connection()
    try:
        return summarize_quality(conn, int(import_batch_id))
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/quality/recalculate")
def import_quality_recalculate(import_batch_id: int):
    conn = _open_connection()
    try:
        result = evaluate_import_quality(conn, int(import_batch_id))
        conn.commit()
        return result.as_dict()
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/validate")
def import_validate(import_batch_id: int):
    conn = _open_connection()
    try:
        result = validate_import(conn, int(import_batch_id))
        conn.commit()
        return result
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/approve")
def import_approve(import_batch_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = approve_import(conn, int(import_batch_id), approved_by=payload.get("approved_by"))
        conn.commit()
        return result
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/reject")
def import_reject(import_batch_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    reason = str(payload.get("reason") or payload.get("rejection_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Reddetme gerekcesi zorunludur")
    conn = _open_connection()
    try:
        result = reject_import(conn, int(import_batch_id), reason=reason, rejected_by=payload.get("rejected_by"))
        conn.commit()
        return result
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/activate")
def import_activate(import_batch_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = activate_import(conn, int(import_batch_id), user=payload.get("user"))
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}/diff")
def import_diff(import_batch_id: int):
    conn = _open_connection()
    try:
        diff = get_import_diff(conn, int(import_batch_id))
        if diff is None:
            diff = recalculate_import_diff(conn, int(import_batch_id))
            conn.commit()
        return diff
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/diff/recalculate")
def import_diff_recalculate(import_batch_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = recalculate_import_diff(
            conn,
            int(import_batch_id),
            compared_to_import_batch_id=payload.get("compared_to_import_batch_id"),
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}/rollback-plan")
def import_rollback_plan(import_batch_id: int):
    conn = _open_connection()
    try:
        return get_rollback_plan(conn, int(import_batch_id))
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/rollback")
def import_rollback(import_batch_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    reason = str(payload.get("reason") or payload.get("rollback_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rollback gerekcesi zorunludur")
    conn = _open_connection()
    try:
        result = rollback_import(conn, int(import_batch_id), reason=reason, user=payload.get("user"))
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/imports/{import_batch_id}/impact")
def import_impact(import_batch_id: int):
    conn = _open_connection()
    try:
        impact = get_import_impact(conn, int(import_batch_id))
        if impact is None:
            impact = recalculate_import_impact(conn, int(import_batch_id))
            conn.commit()
        return impact
    finally:
        conn.close()


@router.post("/imports/{import_batch_id}/impact/recalculate")
def import_impact_recalculate(import_batch_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = recalculate_import_impact(
            conn,
            int(import_batch_id),
            previous_decision_run_id=payload.get("previous_decision_run_id"),
            new_decision_run_id=payload.get("new_decision_run_id"),
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/havuz/state-policies")
def havuz_state_policies():
    conn = _open_connection()
    try:
        return {"data": list_pool_state_policies(conn)}
    finally:
        conn.close()


@router.post("/havuz/state-policies")
def havuz_state_policy_create(payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = create_pool_state_policy(
            conn,
            name=str(payload.get("name") or "Havuz State Politikası"),
            scope_type=str(payload.get("scope_type") or "global"),
            faculty_id=payload.get("faculty_id"),
            department_id=payload.get("department_id"),
            year=payload.get("year"),
            semester=payload.get("semester"),
            activate=bool(payload.get("activate", True)),
            notes=payload.get("notes"),
            **{k: v for k, v in payload.items() if k not in {"name", "scope_type", "faculty_id", "department_id", "year", "semester", "activate", "notes"}},
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.post("/havuz/state-policies/{policy_id}/activate")
def havuz_state_policy_activate(policy_id: int):
    conn = _open_connection()
    try:
        result = activate_pool_state_policy(conn, int(policy_id))
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/havuz/courses/{course_id}/governance")
def havuz_course_governance(course_id: int):
    conn = _open_connection()
    try:
        return get_governance_flags(conn, int(course_id))
    finally:
        conn.close()


@router.post("/havuz/courses/{course_id}/governance")
@router.patch("/havuz/courses/{course_id}/governance")
def havuz_course_governance_update(course_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = upsert_governance_flags(conn, int(course_id), **payload)
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/havuz/state-transitions")
def havuz_state_transition_list(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    course_id: Optional[int] = None,
    status: Optional[int] = None,
    approval_status: Optional[str] = None,
):
    conn = _open_connection()
    try:
        return {
            "data": list_state_transitions(
                conn,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
                course_id=course_id,
                status=status,
                approval_status=approval_status,
            )
        }
    finally:
        conn.close()


@router.get("/havuz/courses/{course_id}/state-history")
def havuz_course_state_history(course_id: int):
    conn = _open_connection()
    try:
        return {"data": get_course_state_history(conn, int(course_id))}
    finally:
        conn.close()


@router.post("/havuz/evaluate")
def havuz_evaluate(payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        if payload.get("course_id") is not None:
            result = evaluate_course_state_transition(conn, dict(payload))
            if payload.get("save"):
                from app.services.pool_state_machine_service import save_state_transition, update_havuz_lifecycle

                transition_id = save_state_transition(conn, result)
                update_havuz_lifecycle(conn, result, transition_id)
                conn.commit()
            return result
        if payload.get("year") is None:
            raise HTTPException(status_code=400, detail="course_id veya year zorunludur")
        result = evaluate_scope_transitions(
            conn,
            year=int(payload["year"]),
            faculty_id=payload.get("faculty_id"),
            department_id=payload.get("department_id"),
            semester=payload.get("semester"),
            save=bool(payload.get("save", False)),
        )
        if payload.get("save"):
            conn.commit()
        return {"data": result}
    finally:
        conn.close()


@router.get("/havuz/approvals")
def havuz_approvals(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = "pending",
):
    conn = _open_connection()
    try:
        return {
            "data": list_pool_pending_approvals(
                conn,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
                status=status,
            )
        }
    finally:
        conn.close()


@router.post("/havuz/approvals/{approval_id}/approve")
def havuz_approval_approve(approval_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = approve_state_approval(
            conn,
            int(approval_id),
            reviewed_by=payload.get("reviewed_by"),
            review_note=payload.get("review_note"),
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.post("/havuz/approvals/{approval_id}/reject")
def havuz_approval_reject(approval_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = reject_state_approval(
            conn,
            int(approval_id),
            reviewed_by=payload.get("reviewed_by"),
            review_note=payload.get("review_note"),
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/havuz/overrides")
def havuz_overrides(year: Optional[int] = None, course_id: Optional[int] = None, active_only: bool = False):
    conn = _open_connection()
    try:
        return {"data": list_pool_overrides(conn, year=year, course_id=course_id, active_only=active_only)}
    finally:
        conn.close()


@router.post("/havuz/overrides")
def havuz_override_create(payload: dict[str, Any] = Body(default_factory=dict)):
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Override gerekcesi zorunludur")
    conn = _open_connection()
    try:
        result = create_course_state_override(
            conn,
            course_id=int(payload["course_id"]),
            year=int(payload["year"]),
            semester=payload.get("semester"),
            overridden_final_status=int(payload["overridden_final_status"]),
            recommended_status=payload.get("recommended_status"),
            reason=reason,
            requested_by=payload.get("requested_by"),
            approved_by=payload.get("approved_by"),
            expires_at=payload.get("expires_at"),
            transition_id=payload.get("transition_id"),
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.patch("/havuz/overrides/{override_id}")
def havuz_override_update(override_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        allowed = {k: payload[k] for k in ("reason", "expires_at", "is_active") if k in payload}
        if not allowed:
            raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
        assignments = ", ".join(f"{key} = ?" for key in allowed)
        conn.execute(
            f"UPDATE course_state_overrides SET {assignments} WHERE id = ?",
            tuple(allowed.values()) + (int(override_id),),
        )
        conn.commit()
        return {"ok": True, "id": int(override_id)}
    finally:
        conn.close()


@router.get("/havuz/lifecycle-summary")
def havuz_lifecycle_summary(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        return get_pool_lifecycle_summary(
            conn,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=semester,
        )
    finally:
        conn.close()


@router.get("/havuz/reactivation-candidates")
def havuz_reactivation_candidates(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
):
    conn = _open_connection()
    try:
        return {
            "data": get_reactivation_candidates(
                conn,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
            )
        }
    finally:
        conn.close()


@router.get("/havuz/protected-courses")
def havuz_protected_courses(faculty_id: Optional[int] = None, department_id: Optional[int] = None):
    conn = _open_connection()
    try:
        return {"data": get_protected_courses(conn, faculty_id=faculty_id, department_id=department_id)}
    finally:
        conn.close()


def _api_response(*, data: Any, message: str | None = None, warnings: list[Any] | None = None, meta: dict[str, Any] | None = None) -> dict:
    response = ApiResponse(data=data, message=message, warnings=warnings or [], meta=meta or {})
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return response.dict()


def _payload_dict(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_none=True)
    if hasattr(payload, "dict"):
        return payload.dict(exclude_none=True)
    return dict(payload or {})


@router.get("/ahp/criteria")
def ahp_criteria():
    conn = _open_connection()
    try:
        data = list_active_criteria(conn)
        conn.commit()
        return _api_response(data=data, message="AHP karar kriterleri listelendi.")
    finally:
        conn.close()


@router.post("/ahp/criteria")
def ahp_criteria_create(payload: AHPCriterionRequest):
    conn = _open_connection()
    try:
        data = create_or_update_criterion(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="AHP kriter tanımı kaydedildi.")
    finally:
        conn.close()


@router.patch("/ahp/criteria/{criterion_key}")
def ahp_criteria_update(criterion_key: str, payload: AHPCriterionRequest):
    conn = _open_connection()
    try:
        data = _payload_dict(payload)
        data["criterion_key"] = criterion_key
        result = create_or_update_criterion(conn, **data)
        conn.commit()
        return _api_response(data=result, message="AHP kriter tanımı güncellendi.")
    finally:
        conn.close()


@router.delete("/ahp/criteria/{criterion_key}")
def ahp_criteria_deactivate(criterion_key: str):
    conn = _open_connection()
    try:
        data = deactivate_criterion(conn, criterion_key)
        conn.commit()
        return _api_response(data=data, message="AHP kriter tanımı pasifleştirildi.")
    finally:
        conn.close()


@router.get("/ahp/profiles")
def ahp_profiles(
    scope_type: Optional[str] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    year: Optional[int] = None,
    semester: Optional[str] = None,
    status: Optional[str] = None,
    is_active: Optional[int] = None,
):
    conn = _open_connection()
    try:
        filters = {
            "scope_type": scope_type,
            "faculty_id": faculty_id,
            "department_id": department_id,
            "year": year,
            "semester": semester,
            "status": status,
            "is_active": is_active,
        }
        data = list_ahp_profiles(conn, {k: v for k, v in filters.items() if v is not None})
        conn.commit()
        return _api_response(data=data, message="AHP profilleri listelendi.")
    finally:
        conn.close()


@router.get("/ahp/profiles/active")
def ahp_profiles_active(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    conn = _open_connection()
    try:
        data = resolve_active_profile(
            conn,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            semester=semester,
        )
        conn.commit()
        return _api_response(data=data, message="Aktif AHP profili çözümlendi.")
    finally:
        conn.close()


@router.get("/ahp/profiles/{profile_id}")
def ahp_profile_detail(profile_id: int):
    conn = _open_connection()
    try:
        profile = get_profile(conn, int(profile_id))
        if not profile:
            raise HTTPException(status_code=404, detail="AHP profili bulunamadı.")
        return _api_response(data=profile)
    finally:
        conn.close()


@router.post("/ahp/profiles")
def ahp_profile_create(payload: AHPProfileCreateRequest):
    conn = _open_connection()
    try:
        data = create_profile(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="AHP profili oluşturuldu.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.patch("/ahp/profiles/{profile_id}")
def ahp_profile_update(profile_id: int, payload: AHPProfileUpdateRequest):
    conn = _open_connection()
    try:
        data = update_profile(conn, int(profile_id), **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="AHP profili güncellendi.")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/validate")
def ahp_profile_validate(profile_id: int):
    conn = _open_connection()
    try:
        data = validate_profile(conn, int(profile_id))
        return _api_response(data=data, message="AHP profili doğrulandı.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/submit")
def ahp_profile_submit(profile_id: int, payload: AHPApprovalRequest = Body(default_factory=AHPApprovalRequest)):
    conn = _open_connection()
    try:
        data = submit_for_approval(conn, int(profile_id), actor=payload.actor)
        return _api_response(data=data, message="AHP profili onaya gönderildi.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/approve")
def ahp_profile_approve(profile_id: int, payload: AHPApprovalRequest = Body(default_factory=AHPApprovalRequest)):
    conn = _open_connection()
    try:
        data = approve_profile(conn, int(profile_id), approved_by=payload.approved_by or payload.actor)
        return _api_response(data=data, message="AHP profili onaylandı.")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/reject")
def ahp_profile_reject(profile_id: int, payload: AHPRejectRequest):
    conn = _open_connection()
    try:
        data = reject_profile(conn, int(profile_id), reason=payload.reason, rejected_by=payload.rejected_by)
        return _api_response(data=data, message="AHP profili reddedildi.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/activate")
def ahp_profile_activate(profile_id: int, payload: AHPApprovalRequest = Body(default_factory=AHPApprovalRequest)):
    conn = _open_connection()
    try:
        data = activate_ahp_profile(conn, int(profile_id), actor=payload.actor)
        return _api_response(data=data, message="AHP profili aktif yapıldı.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/archive")
def ahp_profile_archive(profile_id: int, payload: AHPApprovalRequest = Body(default_factory=AHPApprovalRequest)):
    conn = _open_connection()
    try:
        data = archive_profile(conn, int(profile_id), actor=payload.actor)
        return _api_response(data=data, message="AHP profili arşivlendi.")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/profiles/{profile_id}/clone")
def ahp_profile_clone(profile_id: int, payload: AHPCloneRequest):
    conn = _open_connection()
    try:
        data = clone_profile(conn, int(profile_id), new_scope=payload.new_scope, new_year=payload.new_year, actor=payload.actor)
        return _api_response(data=data, message="AHP profili klonlandı.")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.post("/ahp/calculate")
def ahp_calculate(payload: AHPCalculateRequest):
    try:
        result = calculate_weights_from_pairwise_matrix(payload.criteria_keys, payload.pairwise_matrix, method=payload.method)
        return _api_response(data=result.to_dict(), message="AHP ağırlıkları hesaplandı.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ahp/consistency-check")
def ahp_consistency_check(payload: AHPCalculateRequest):
    validation = validate_pairwise_matrix(payload.pairwise_matrix, payload.criteria_keys)
    if not validation.is_valid:
        return _api_response(data=validation.to_dict(), message="AHP matrisi geçersiz.", warnings=validation.warnings)
    result = calculate_weights_from_pairwise_matrix(payload.criteria_keys, payload.pairwise_matrix, method=payload.method)
    return _api_response(data=result.to_dict(), message="AHP tutarlılık kontrolü tamamlandı.")


@router.get("/ahp/profiles/{profile_id}/impact")
def ahp_profile_impact(profile_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=explain_weight_profile(conn, int(profile_id)), message="AHP profil etkisi açıklandı.")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        conn.close()


@router.get("/ahp/decision-runs/{run_id}/impact")
def ahp_decision_run_impact(run_id: int, course_id: Optional[int] = None):
    conn = _open_connection()
    try:
        if course_id is not None:
            data = explain_course_weight_contribution(conn, int(course_id), int(run_id))
        else:
            run = get_decision_run(conn, int(run_id))
            if not run:
                raise HTTPException(status_code=404, detail="Karar çalışması bulunamadı.")
            profile_id = run.get("ahp_profile_id")
            data = explain_weight_profile(conn, int(profile_id)) if profile_id else {"message": "AHP profili bağlı değil."}
        return _api_response(data=data, message="AHP karar etkisi hazırlandı.")
    finally:
        conn.close()


@router.post("/ahp/decision-runs/{run_id}/sensitivity")
def ahp_decision_run_sensitivity(run_id: int, payload: AHPSensitivityRequest = Body(default_factory=AHPSensitivityRequest)):
    conn = _open_connection()
    try:
        data = run_weight_sensitivity_analysis(conn, int(run_id), variation_percent=float(payload.variation_percent))
        return _api_response(data=data, message="AHP sensitivity analizi tamamlandı.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.get("/ahp/decision-runs/{run_id}/sensitivity")
def ahp_decision_run_sensitivity_get(run_id: int):
    conn = _open_connection()
    try:
        data = get_latest_sensitivity_for_run(conn, int(run_id))
        return _api_response(data=data, message="AHP sensitivity sonucu getirildi.")
    finally:
        conn.close()


@router.get("/ahp/stale-decisions")
def ahp_stale_decisions(unresolved_only: bool = True):
    conn = _open_connection()
    try:
        return _api_response(data=list_stale_decisions(conn, unresolved_only=unresolved_only), message="AHP stale kararları listelendi.")
    finally:
        conn.close()


@router.post("/ahp/stale-decisions/{stale_id}/resolve")
def ahp_stale_decision_resolve(stale_id: int, payload: AHPApprovalRequest = Body(default_factory=AHPApprovalRequest)):
    conn = _open_connection()
    try:
        data = resolve_stale_decision(conn, int(stale_id), resolved_by=payload.actor)
        return _api_response(data=data, message="AHP stale işareti kapatıldı.")
    finally:
        conn.close()


@router.get("/semester-planning/policies")
def semester_planning_policies(
    scope_type: Optional[str] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    year: Optional[int] = None,
    active_only: bool = False,
):
    conn = _open_connection()
    try:
        data = list_semester_planning_policies(conn, scope_type=scope_type, faculty_id=faculty_id, department_id=department_id, year=year, active_only=active_only)
        conn.commit()
        return _api_response(data=data, message="Dönem planlama politikaları listelendi.")
    finally:
        conn.close()


@router.post("/semester-planning/policies")
def semester_planning_policy_create(payload: SemesterPlanningPolicyRequest):
    conn = _open_connection()
    try:
        data = create_semester_planning_policy(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Dönem planlama politikası oluşturuldu.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.patch("/semester-planning/policies/{policy_id}")
def semester_planning_policy_update(policy_id: int, payload: SemesterPlanningPolicyRequest):
    conn = _open_connection()
    try:
        data = update_semester_planning_policy(conn, int(policy_id), **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Dönem planlama politikası güncellendi.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.post("/semester-planning/policies/{policy_id}/activate")
def semester_planning_policy_activate(policy_id: int):
    conn = _open_connection()
    try:
        data = activate_semester_planning_policy(conn, int(policy_id))
        conn.commit()
        return _api_response(data=data, message="Dönem planlama politikası aktif yapıldı.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.get("/semester-planning/course-availability")
def semester_planning_course_availability(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    course_id: Optional[int] = None,
):
    conn = _open_connection()
    try:
        return _api_response(
            data=list_availability_by_scope(conn, year=year, faculty_id=faculty_id, department_id=department_id, course_id=course_id),
            message="Ders dönem uygunlukları listelendi.",
        )
    finally:
        conn.close()


@router.post("/semester-planning/course-availability")
def semester_planning_course_availability_create(payload: CourseAvailabilityRequest):
    conn = _open_connection()
    try:
        data = upsert_course_availability(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Ders dönem uygunluğu kaydedildi.")
    finally:
        conn.close()


@router.patch("/semester-planning/course-availability/{availability_id}")
def semester_planning_course_availability_patch(availability_id: int, payload: CourseAvailabilityRequest):
    # Geriye donuk guvenli yol: yeni scope kaydi ekleyerek son kaydi etkin kabul eder.
    return semester_planning_course_availability_create(payload)


@router.get("/semester-planning/instructors")
def semester_planning_instructors(faculty_id: Optional[int] = None, department_id: Optional[int] = None):
    conn = _open_connection()
    try:
        return _api_response(data=list_instructors(conn, faculty_id=faculty_id, department_id=department_id), message="Öğretim üyeleri listelendi.")
    finally:
        conn.close()


@router.post("/semester-planning/instructors")
def semester_planning_instructor_create(payload: InstructorRequest):
    conn = _open_connection()
    try:
        data = create_instructor(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Öğretim üyesi kaydedildi.")
    finally:
        conn.close()


@router.get("/semester-planning/instructor-availability")
def semester_planning_instructor_availability(year: Optional[int] = None, semester: Optional[str] = None, instructor_id: Optional[int] = None):
    conn = _open_connection()
    try:
        return _api_response(data=list_instructor_availability(conn, year=year, semester=semester, instructor_id=instructor_id), message="Öğretim üyesi uygunluğu listelendi.")
    finally:
        conn.close()


@router.post("/semester-planning/instructor-availability")
def semester_planning_instructor_availability_create(payload: InstructorAvailabilityRequest):
    conn = _open_connection()
    try:
        data = upsert_instructor_availability(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Öğretim üyesi uygunluğu kaydedildi.")
    finally:
        conn.close()


@router.get("/semester-planning/resources")
def semester_planning_resources(resource_type: Optional[str] = None):
    conn = _open_connection()
    try:
        return _api_response(data=list_resources(conn, resource_type=resource_type), message="Öğretim kaynakları listelendi.")
    finally:
        conn.close()


@router.post("/semester-planning/resources")
def semester_planning_resource_create(payload: TeachingResourceRequest):
    conn = _open_connection()
    try:
        data = create_resource(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Öğretim kaynağı kaydedildi.")
    finally:
        conn.close()


@router.get("/semester-planning/resource-requirements")
def semester_planning_resource_requirements(course_id: Optional[int] = None):
    conn = _open_connection()
    try:
        return _api_response(data=list_resource_requirements(conn, course_id=course_id), message="Ders kaynak ihtiyaçları listelendi.")
    finally:
        conn.close()


@router.post("/semester-planning/resource-requirements")
def semester_planning_resource_requirement_create(payload: ResourceRequirementRequest):
    conn = _open_connection()
    try:
        data = create_resource_requirement(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Ders kaynak ihtiyacı kaydedildi.")
    finally:
        conn.close()


@router.get("/semester-planning/prerequisites")
def semester_planning_prerequisites(course_id: Optional[int] = None):
    conn = _open_connection()
    try:
        return _api_response(data=get_prerequisites(conn, course_id=course_id), message="Ön koşullar listelendi.")
    finally:
        conn.close()


@router.post("/semester-planning/prerequisites")
def semester_planning_prerequisite_create(payload: PrerequisiteRequest):
    conn = _open_connection()
    try:
        data = create_prerequisite(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Ön koşul kaydedildi.")
    finally:
        conn.close()


@router.post("/semester-planning/generate")
def semester_planning_generate(payload: SemesterPlanGenerateRequest):
    conn = _open_connection()
    try:
        data = generate_semester_plan(conn, **_payload_dict(payload))
        conn.commit()
        return _api_response(data=data, message="Dönem planı üretildi.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@router.post("/semester-planning/generate-alternatives")
def semester_planning_generate_alternatives(payload: SemesterPlanGenerateRequest):
    request = _payload_dict(payload)
    request["generate_alternatives"] = True
    return semester_planning_generate(SemesterPlanGenerateRequest(**request))


@router.get("/semester-planning/runs")
def semester_planning_runs(year: Optional[int] = None, faculty_id: Optional[int] = None, department_id: Optional[int] = None):
    conn = _open_connection()
    try:
        return _api_response(data=list_plan_runs(conn, year=year, faculty_id=faculty_id, department_id=department_id), message="Dönem planı çalışmaları listelendi.")
    finally:
        conn.close()


@router.get("/semester-planning/runs/{run_id}")
def semester_planning_run_detail(run_id: int):
    conn = _open_connection()
    try:
        data = get_plan_run(conn, int(run_id))
        if not data:
            raise HTTPException(status_code=404, detail="Dönem planı bulunamadı.")
        return _api_response(data=data, message="Dönem planı getirildi.")
    finally:
        conn.close()


@router.get("/semester-planning/runs/{run_id}/assignments")
def semester_planning_run_assignments(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_semester_plan_assignments(conn, int(run_id)), message="Dönem planı ders atamaları getirildi.")
    finally:
        conn.close()


@router.get("/semester-planning/runs/{run_id}/violations")
def semester_planning_run_violations(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_constraint_violations(conn, int(run_id)), message="Dönem planı kısıt ihlalleri getirildi.")
    finally:
        conn.close()


@router.get("/semester-planning/runs/{run_id}/scenarios")
def semester_planning_run_scenarios(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=compare_plan_scenarios(conn, int(run_id)), message="Dönem planı alternatif senaryoları getirildi.")
    finally:
        conn.close()


@router.get("/semester-planning/runs/{run_id}/report")
def semester_planning_run_report(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_semester_plan_summary(conn, int(run_id)), message="Dönem planlama raporu hazırlandı.")
    finally:
        conn.close()


@router.get("/algorithms/governance")
def algorithms_governance(usage_role: Optional[str] = None):
    conn = _open_connection()
    try:
        data = list_algorithm_governance(conn, usage_role=usage_role)
        conn.commit()
        return _api_response(data=data, message="Algoritma yönetişimi registry listelendi.")
    finally:
        conn.close()


@router.get("/algorithms/governance/report")
def algorithms_governance_report():
    conn = _open_connection()
    try:
        report = generate_algorithm_role_report(conn)
        conn.commit()
        return _api_response(data=report, message="Algoritma yönetişimi raporu üretildi.")
    finally:
        conn.close()


@router.get("/algorithms/governance/{algorithm_key}")
def algorithms_governance_detail(algorithm_key: str):
    conn = _open_connection()
    try:
        return _api_response(data=get_algorithm_governance(conn, algorithm_key))
    finally:
        conn.close()


@router.patch("/algorithms/governance/{algorithm_key}")
def algorithms_governance_update(algorithm_key: str, payload: AlgorithmGovernanceUpdateRequest):
    conn = _open_connection()
    try:
        result = update_algorithm_role(
            conn,
            algorithm_key,
            usage_role=payload.usage_role,
            can_affect_final_decision=payload.can_affect_final_decision,
            minimum_sample_count=payload.minimum_sample_count,
            user_facing_warning=payload.user_facing_warning,
        )
        conn.commit()
        return _api_response(data=result, message="Algoritma yönetişimi kaydı güncellendi.")
    finally:
        conn.close()


@router.get("/algorithms/tasks")
def algorithms_tasks():
    conn = _open_connection()
    try:
        seed_default_governance_registry(conn)
        conn.commit()
        return _api_response(data=list_task_mappings(conn), message="Problem-algoritma eşleştirme matrisi listelendi.")
    finally:
        conn.close()


@router.get("/algorithms/tasks/{task_key}/algorithms")
def algorithms_for_task(task_key: str):
    conn = _open_connection()
    try:
        return _api_response(data=get_allowed_algorithms_for_task(conn, task_key), message="Göreve uygun algoritmalar listelendi.")
    finally:
        conn.close()


@router.post("/algorithms/data-guard/check")
def algorithms_data_guard_check(payload: DataGuardCheckRequest):
    conn = _open_connection()
    try:
        result = check_data_requirements(
            conn,
            payload.algorithm_key,
            X=payload.X,
            y=payload.y,
            task_type=payload.task_type,
            sample_count=payload.sample_count,
            feature_count=payload.feature_count,
            n_clusters=payload.n_clusters,
        )
        conn.commit()
        return _api_response(data=result.to_dict(), message="Algoritma veri uygunluk kontrolü tamamlandı.")
    finally:
        conn.close()


@router.post("/benchmark/governed-runs/execute")
def benchmark_governed_run_execute(payload: GovernedBenchmarkRunRequest):
    conn = _open_connection()
    try:
        result = execute_governed_benchmark_run(conn, payload.to_payload())
        conn.commit()
        return _api_response(data=result, message="Governed benchmark çalıştırması tamamlandı.")
    finally:
        conn.close()


@router.get("/benchmark/governed-runs")
def benchmark_governed_runs(limit: int = 100):
    conn = _open_connection()
    try:
        return _api_response(data=list_governed_benchmark_runs(conn, limit=limit))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/metrics")
def benchmark_governed_run_metrics(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_metrics(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/validation")
def benchmark_governed_run_validation(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_validation(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/statistics")
def benchmark_governed_run_statistics(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_statistics(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/diagnostics")
def benchmark_governed_run_diagnostics(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_diagnostics(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/leakage")
def benchmark_governed_run_leakage(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_leakage(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/clustering")
def benchmark_governed_run_clustering(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_clustering(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/report")
def benchmark_governed_run_report(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=get_governed_run_report(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/statistical-report")
def benchmark_governed_run_statistical_report(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=generate_benchmark_statistical_report(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}/clustering-report")
def benchmark_governed_run_clustering_report(run_id: int):
    conn = _open_connection()
    try:
        return _api_response(data=generate_clustering_report(conn, int(run_id)))
    finally:
        conn.close()


@router.get("/benchmark/governed-runs/{run_id}")
def benchmark_governed_run_detail(run_id: int):
    conn = _open_connection()
    try:
        run = get_governed_benchmark_run(conn, int(run_id))
        if not run:
            raise HTTPException(status_code=404, detail="Governed benchmark run bulunamadı")
        return _api_response(data=run)
    finally:
        conn.close()


@router.get("/ml/algorithms")
def ml_algorithms():
    conn = _open_connection()
    try:
        data = list_algorithm_registry(conn)
        conn.commit()
        return _api_response(data=data, message="ML algoritma registry listelendi.")
    finally:
        conn.close()


@router.patch("/ml/algorithms/{algorithm_key}")
def ml_algorithm_update(algorithm_key: str, payload: MLAlgorithmUpdateRequest):
    conn = _open_connection()
    try:
        result = update_algorithm_usage_role(
            conn,
            algorithm_key,
            usage_role=payload.usage_role,
            default_enabled=payload.default_enabled,
            min_training_samples=payload.min_training_samples,
            min_samples_per_class=payload.min_samples_per_class,
            notes=payload.notes,
        )
        conn.commit()
        return _api_response(data=result, message="ML algoritma konumlandırması güncellendi.")
    finally:
        conn.close()


@router.get("/ml/readiness")
def ml_readiness(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    algorithm_key: Optional[str] = None,
):
    conn = _open_connection()
    try:
        seed_default_algorithm_registry(conn)
        conn.commit()
        rows = get_algorithm_readiness_table(
            conn,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            algorithm_key=algorithm_key,
        )
        return _api_response(data=rows, message="ML readiness kontrolü tamamlandı.")
    finally:
        conn.close()


@router.post("/ml/readiness/report")
def ml_readiness_report_create(payload: MLReadinessReportRequest):
    conn = _open_connection()
    try:
        report = generate_ml_readiness_report(
            conn,
            year=payload.year,
            faculty_id=payload.faculty_id,
            department_id=payload.department_id,
            save=payload.save,
        )
        conn.commit()
        return _api_response(data=report, message="ML readiness raporu üretildi.")
    finally:
        conn.close()


@router.get("/ml/features/summary")
def ml_features_summary(
    year: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
):
    conn = _open_connection()
    try:
        dataset = build_course_feature_dataset(conn, year=year, faculty_id=faculty_id, department_id=department_id)
        return _api_response(
            data={
                "feature_schema_version": dataset.feature_schema_version,
                "sample_count": dataset.sample_count,
                "feature_names": dataset.feature_names,
                "missing_features_summary": dataset.missing_features_summary,
                "imputation_strategy": dataset.imputation_strategy,
                "normalization_summary": dataset.normalization_summary,
                "warnings": dataset.warnings,
            },
            message="ML feature özeti üretildi.",
        )
    finally:
        conn.close()


@router.post("/ml/features/build-snapshot")
def ml_features_build_snapshot(payload: MLFeatureSnapshotRequest):
    conn = _open_connection()
    try:
        dataset = build_course_feature_dataset(
            conn,
            scope=payload.scope,
            year=payload.year,
            faculty_id=payload.faculty_id,
            department_id=payload.department_id,
        )
        snapshot_id = save_feature_snapshot(
            conn,
            dataset,
            scope=payload.scope,
            year=payload.year,
            faculty_id=payload.faculty_id,
            department_id=payload.department_id,
        )
        conn.commit()
        return _api_response(data={"snapshot_id": snapshot_id, "sample_count": dataset.sample_count}, message="ML feature snapshot kaydedildi.")
    finally:
        conn.close()


@router.get("/ml/model-runs")
def ml_model_runs(algorithm_key: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    conn = _open_connection()
    try:
        return _api_response(data=list_model_runs(conn, algorithm_key=algorithm_key, status=status, limit=limit))
    finally:
        conn.close()


@router.post("/ml/model-runs/train")
def ml_model_run_train(payload: MLTrainRequest):
    conn = _open_connection()
    try:
        result = train_model_run(
            conn,
            algorithm_key=payload.algorithm_key,
            year=payload.year,
            faculty_id=payload.faculty_id,
            department_id=payload.department_id,
            created_by=payload.created_by,
        )
        conn.commit()
        return _api_response(data=result, message="ML model çalışma kaydı üretildi.")
    finally:
        conn.close()


@router.get("/ml/model-runs/{run_id}")
def ml_model_run_detail(run_id: int):
    conn = _open_connection()
    try:
        run = get_model_run(conn, int(run_id))
        if not run:
            raise HTTPException(status_code=404, detail="ML model run bulunamadı")
        return _api_response(data=run)
    finally:
        conn.close()


@router.post("/ml/model-runs/{run_id}/deprecate")
def ml_model_run_deprecate(run_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    conn = _open_connection()
    try:
        result = deprecate_model_run(conn, int(run_id), reason=payload.get("reason"))
        conn.commit()
        return _api_response(data=result, message="ML model run deprecated olarak işaretlendi.")
    finally:
        conn.close()


@router.get("/ml/predictions")
def ml_prediction_list(
    course_id: Optional[int] = None,
    algorithm_key: Optional[str] = None,
    limit: int = 100,
):
    conn = _open_connection()
    try:
        return _api_response(data=list_predictions(conn, course_id=course_id, algorithm_key=algorithm_key, limit=limit))
    finally:
        conn.close()


@router.post("/ml/predictions/predict-course")
def ml_predict_course(payload: MLPredictCourseRequest):
    conn = _open_connection()
    try:
        result = predict_course(
            conn,
            algorithm_key=payload.algorithm_key,
            course_id=payload.course_id,
            year=payload.year,
            faculty_id=payload.faculty_id,
            department_id=payload.department_id,
            prediction_type=payload.prediction_type,
        )
        conn.commit()
        return _api_response(data=result, message="ML destekleyici tahmin üretildi.")
    finally:
        conn.close()


@router.post("/ml/predictions/predict-batch")
def ml_predict_batch(payload: MLPredictBatchRequest):
    conn = _open_connection()
    try:
        result = predict_batch(
            conn,
            algorithm_key=payload.algorithm_key,
            course_ids=payload.course_ids,
            year=payload.year,
            faculty_id=payload.faculty_id,
            department_id=payload.department_id,
        )
        conn.commit()
        return _api_response(data=result, message="ML toplu destekleyici tahmin üretildi.")
    finally:
        conn.close()


@router.get("/ml/predictions/{prediction_id}/explanation")
def ml_prediction_explanation(prediction_id: int):
    conn = _open_connection()
    try:
        explanation = get_prediction_explanation(conn, int(prediction_id))
        if not explanation:
            raise HTTPException(status_code=404, detail="ML tahmin açıklaması bulunamadı")
        return _api_response(data=explanation)
    finally:
        conn.close()


@router.get("/ml/readiness-reports")
def ml_readiness_reports(limit: int = 100):
    conn = _open_connection()
    try:
        return _api_response(data=list_readiness_reports(conn, limit=limit))
    finally:
        conn.close()


@router.get("/ml/readiness-reports/{report_id}")
def ml_readiness_report_detail(report_id: int):
    conn = _open_connection()
    try:
        report = get_readiness_report(conn, int(report_id))
        if not report:
            raise HTTPException(status_code=404, detail="ML readiness raporu bulunamadı")
        return _api_response(data=report)
    finally:
        conn.close()


def _safe_json(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        import json

        return json.loads(value)
    except Exception:
        return default


# =============================================================================
# VERİ KALİTESİ API ENDPOİNTLERİ (PHASE 3)
# =============================================================================

@router.get("/data/coverage")
def data_coverage(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    """Veri kapsama raporunu al"""
    from app.services.data_quality_integration_service import generate_coverage_report_cursor
    
    conn = _open_connection()
    try:
        cur = conn.cursor()
        report = generate_coverage_report_cursor(
            cur, int(year), faculty_id, department_id, semester
        )
        return {
            "data": report,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        conn.close()


@router.get("/data/readiness")
def data_readiness(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
):
    """Veri olgunluğu değerlendirmesini al"""
    from app.services.data_quality_integration_service import assess_data_readiness_cursor
    
    conn = _open_connection()
    try:
        cur = conn.cursor()
        assessment = assess_data_readiness_cursor(
            cur, int(year), faculty_id, department_id, semester
        )
        return {
            "data": assessment,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        conn.close()


@router.get("/data/confidence")
def data_confidence(
    year: Optional[int] = None,
    course_id: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    level: Optional[str] = None,
    limit: int = 500,
):
    """Ders veri güveni kayıtlarını listele."""
    where_parts = []
    params: list[Any] = []
    if year is not None:
        where_parts.append("cdc.year = ?")
        params.append(int(year))
    if course_id is not None:
        where_parts.append("cdc.course_id = ?")
        params.append(int(course_id))
    if faculty_id is not None:
        where_parts.append("d.fakulte_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where_parts.append("d.bolum_id = ?")
        params.append(int(department_id))
    if level:
        where_parts.append("cdc.level = ?")
        params.append(level)
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    try:
        cols, rows = _run_query(
            f"""
            SELECT cdc.id, cdc.decision_run_id, cdc.course_id, cdc.year,
                   d.kod AS course_code, d.ad AS course_name,
                   cdc.score AS confidence_score, cdc.level AS confidence_level,
                   cdc.has_success_data, cdc.has_popularity_data,
                   cdc.has_survey_data, cdc.has_trend_data, cdc.has_recent_data,
                   cdc.survey_count, cdc.data_points_count,
                   cdc.missing_fields_json, cdc.explanation, cdc.created_at
            FROM course_data_confidence cdc
            LEFT JOIN ders d ON d.ders_id = cdc.course_id
            WHERE {where_clause}
            ORDER BY cdc.score ASC, d.ad
            LIMIT ?
            """,
            params + [limit],
        )
    except sqlite3.OperationalError:
        return {"data": [], "count": 0}

    data = []
    for row in rows:
        item = dict(zip(cols, row))
        item["missing_fields"] = _safe_json(item.get("missing_fields_json"), [])
        data.append(item)
    return {"data": data, "count": len(data)}


@router.post("/data/coverage/generate")
def data_coverage_generate(payload: dict[str, Any] = Body(default_factory=dict)):
    """Yeni kapsama raporu oluştur ve kaydet"""
    year = payload.get("year") or payload.get("yil")
    if year is None:
        raise HTTPException(status_code=400, detail="year/yil zorunludur")
    
    from app.services.data_quality_integration_service import (
        generate_coverage_report_cursor,
        save_data_coverage_report,
    )
    
    conn = _open_connection()
    try:
        cur = conn.cursor()
        faculty_id = payload.get("faculty_id") or payload.get("fakulte_id")
        department_id = payload.get("department_id") or payload.get("bolum_id")
        semester = payload.get("semester") or payload.get("donem")
        
        report = generate_coverage_report_cursor(
            cur, int(year), faculty_id, department_id, semester
        )
        report_id = save_data_coverage_report(
            cur, int(year), faculty_id, department_id, semester, report
        )
        conn.commit()
        
        return {
            "ok": True,
            "report_id": report_id,
            "data": report,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        conn.close()


@router.get("/data/missing")
def data_missing(
    year: int,
    course_id: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    severity: Optional[str] = None,
    limit: int = 500,
):
    """Eksik veri öğelerini listele"""
    where_parts = ["year = ?"]
    params: list[Any] = [int(year)]
    if course_id is not None:
        where_parts.append("course_id = ?")
        params.append(int(course_id))
    if faculty_id is not None:
        where_parts.append("faculty_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where_parts.append("department_id = ?")
        params.append(int(department_id))
    if severity:
        where_parts.append("severity = ?")
        params.append(severity)
    where_clause = " AND ".join(where_parts)
    cols, rows = _run_query(
        """
        SELECT id, course_id, year, semester, missing_field, severity,
               message, detected_at,
               CASE WHEN resolved_at IS NULL THEN 0 ELSE 1 END AS is_resolved,
               resolved_at, resolved_by
        FROM missing_data_items
        WHERE """ + where_clause + """
        ORDER BY severity DESC, detected_at DESC
        LIMIT ?
        """,
        params + [limit],
    )
    
    data = []
    for row in rows:
        data.append(dict(zip(cols, row)))
    
    return {"data": data, "count": len(data)}


@router.post("/data/missing/{item_id}/resolve")
def data_missing_resolve(item_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    """Eksik veri öğesini çözüldü olarak işaretle"""
    conn = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE missing_data_items
            SET resolved_at = ?, resolved_by = ?
            WHERE id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                payload.get("resolved_by", "system"),
                int(item_id),
            ),
        )
        conn.commit()
        return {"ok": True, "id": int(item_id), "resolved": cur.rowcount > 0}
    finally:
        conn.close()


@router.get("/data/validation-issues")
def data_validation_issues(
    year: Optional[int] = None,
    severity: Optional[str] = None,
    is_resolved: Optional[int] = None,
    limit: int = 500,
):
    """Doğrulama sorunlarını listele"""
    where_parts = []
    params: list[Any] = []
    
    if year:
        where_parts.append("year = ?")
        params.append(int(year))
    if severity:
        where_parts.append("severity = ?")
        params.append(severity)
    if is_resolved is not None:
        where_parts.append("is_resolved = ?")
        params.append(int(is_resolved))
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    cols, rows = _run_query(
        f"""
        SELECT id, course_id, issue_type, severity, message,
               is_resolved, created_at, resolved_at
        FROM data_validation_issues
        WHERE {where_clause}
        ORDER BY severity DESC, created_at DESC
        LIMIT ?
        """,
        params + [limit],
    )
    
    data = []
    for row in rows:
        data.append(dict(zip(cols, row)))
    
    return {"data": data, "count": len(data)}


@router.post("/data/validation-issues/{issue_id}/resolve")
def data_validation_issue_resolve(issue_id: int, payload: dict[str, Any] = Body(default_factory=dict)):
    """Doğrulama sorununu çözüldü olarak işaretle"""
    conn = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE data_validation_issues
            SET is_resolved = 1, resolved_at = ?, resolved_by = ?
            WHERE id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                payload.get("resolved_by", "system"),
                int(issue_id),
            ),
        )
        conn.commit()
        return {"ok": True, "id": int(issue_id), "resolved": cur.rowcount > 0}
    finally:
        conn.close()


@router.get("/data/collection-priorities")
def data_collection_priorities(
    year: Optional[int] = None,
    is_completed: Optional[int] = None,
    limit: int = 100,
):
    """Veri toplama önceliklerini listele"""
    where_parts = []
    params: list[Any] = []
    
    if year:
        where_parts.append("year = ?")
        params.append(int(year))
    if is_completed is not None:
        where_parts.append("status = ?")
        params.append("completed" if int(is_completed) else "open")
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    cols, rows = _run_query(
        f"""
        SELECT id, course_id,
               target_entity_type AS data_type,
               priority_rank AS priority_level,
               priority_reason AS reason,
               expected_impact AS estimated_effort,
               CASE WHEN status = 'completed' THEN 1 ELSE 0 END AS is_completed,
               status, created_at
        FROM data_collection_priorities
        WHERE {where_clause}
        ORDER BY priority_rank ASC, course_id
        LIMIT ?
        """,
        params + [limit],
    )
    
    data = []
    for row in rows:
        data.append(dict(zip(cols, row)))
    
    return {"data": data, "count": len(data)}


@router.post("/data/collection-priorities/{priority_id}/complete")
def data_collection_priority_complete(priority_id: int):
    """Veri toplama önceliğini tamamlandı olarak işaretle"""
    conn = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE data_collection_priorities
            SET status = 'completed', completed_at = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), int(priority_id)),
        )
        conn.commit()
        return {"ok": True, "id": int(priority_id), "completed": cur.rowcount > 0}
    finally:
        conn.close()


@router.get("/decisions/outcomes")
def decisions_outcomes(
    run_id: Optional[int] = None,
    year: Optional[int] = None,
    course_id: Optional[int] = None,
    confidence_level: Optional[str] = None,
    limit: int = 500,
):
    """Karar sonuçlarını listele (outcome tracking)"""
    where_parts = []
    params: list[Any] = []
    
    if run_id:
        where_parts.append("cd.decision_run_id = ?")
        params.append(int(run_id))
    if year:
        where_parts.append("cd.year = ?")
        params.append(int(year))
    if course_id:
        where_parts.append("cd.course_id = ?")
        params.append(int(course_id))
    if confidence_level:
        # confidence_level: 'low', 'medium', 'high'
        where_parts.append(
            "(CASE WHEN cd.data_confidence_score >= 0.75 THEN 'high' "
            "WHEN cd.data_confidence_score >= 0.50 THEN 'medium' ELSE 'low' END) = ?"
        )
        params.append(confidence_level)
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    try:
        cols, rows = _run_query(
            f"""
            SELECT cd.id, cd.decision_run_id, cd.course_id, cd.year,
                   d.kod, d.ad, cd.final_status, cd.topsis_score,
                   cd.data_confidence_score, cd.approval_required,
                   cd.approval_reason, cd.main_reason
            FROM course_decisions cd
            LEFT JOIN ders d ON d.ders_id = cd.course_id
            WHERE {where_clause}
            ORDER BY cd.data_confidence_score ASC, cd.topsis_score DESC
            LIMIT ?
            """,
            params + [limit],
        )
        
        data = []
        for row in rows:
            data.append(dict(zip(cols, row)))
        
        return {"data": data, "count": len(data)}
    except sqlite3.OperationalError:
        return {"data": [], "count": 0, "error": "course_decisions tablosu bulunamadı"}


from datetime import datetime, timezone

from __future__ import annotations

import sqlite3

import pytest

from app.db.schema_compat import ensure_ahp_governance_schema
from app.services.ahp_calculation_service import (
    calculate_weights_from_pairwise_matrix,
    validate_pairwise_matrix,
)
from app.services.ahp_impact_explanation_service import explain_weight_profile
from app.services.ahp_profile_policy_service import resolve_policy
from app.services.ahp_profile_service import (
    DEFAULT_CRITERIA_KEYS,
    activate_profile,
    approve_profile,
    create_profile,
    list_stale_decisions,
    resolve_active_profile,
    seed_default_profile,
    submit_for_approval,
    validate_profile,
)
from app.services.ahp_sensitivity_service import run_weight_sensitivity_analysis
from app.services.criteria_definition_service import (
    seed_default_decision_criteria,
)
from app.services.decision_run_service import create_decision_run


@pytest.fixture()
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    ensure_ahp_governance_schema(connection)
    yield connection
    connection.close()


def test_default_criteria_are_seeded(conn):
    criteria = seed_default_decision_criteria(conn)
    keys = {row["criterion_key"] for row in criteria}
    assert {"basari", "trend", "populerlik", "anket"}.issubset(keys)
    assert all(row["is_benefit"] for row in criteria if row["criterion_key"] in keys)


def test_ahp_matrix_validation_rules():
    invalid = validate_pairwise_matrix([[1, 2]], ["basari"])
    assert invalid.is_valid is False
    diagonal = validate_pairwise_matrix([[2]], ["basari"])
    assert any(issue["code"] == "diagonal_not_one" for issue in diagonal.issues)
    reciprocal = validate_pairwise_matrix([[1, 3], [2, 1]], ["basari", "trend"])
    assert any(issue["code"] == "reciprocal_mismatch" for issue in reciprocal.issues)
    negative = validate_pairwise_matrix([[1, -1], [-1, 1]], ["basari", "trend"])
    assert any(issue["code"] == "non_positive_value" for issue in negative.issues)


def test_weight_calculation_and_consistency():
    matrix = [[1, 2, 4], [0.5, 1, 2], [0.25, 0.5, 1]]
    result = calculate_weights_from_pairwise_matrix(["basari", "trend", "anket"], matrix)
    assert abs(sum(result.weights.values()) - 1.0) < 1e-9
    assert result.weights["basari"] > result.weights["trend"] > result.weights["anket"]
    assert result.consistency_ratio <= 0.10
    inconsistent = calculate_weights_from_pairwise_matrix(
        ["basari", "trend", "anket"],
        [[1, 9, 1], [1 / 9, 1, 9], [1, 1 / 9, 1]],
    )
    assert inconsistent.consistency_ratio > 0.10
    two = calculate_weights_from_pairwise_matrix(["basari", "trend"], [[1, 3], [1 / 3, 1]])
    assert two.consistency_ratio == 0.0


def test_default_profile_is_active(conn):
    profile = seed_default_profile(conn)
    assert profile["scope_type"] == "global"
    assert profile["is_active"] is True
    assert profile["status"] == "active"
    assert profile["weights"]["basari"] == pytest.approx(0.35, abs=0.01)


def test_profile_resolution_priority(conn):
    seed_default_profile(conn)
    faculty = create_profile(
        conn,
        profile_name="Fakülte 2026",
        scope_type="faculty",
        faculty_id=1,
        year=2026,
        source="expert",
        status="approved",
        activate=True,
    )
    department = create_profile(
        conn,
        profile_name="Bölüm 2026",
        scope_type="department",
        faculty_id=1,
        department_id=10,
        year=2026,
        source="expert",
        status="approved",
        activate=True,
    )
    resolved = resolve_active_profile(conn, year=2026, faculty_id=1, department_id=10)
    assert resolved["id"] == department["id"]
    resolved_faculty = resolve_active_profile(conn, year=2026, faculty_id=1)
    assert resolved_faculty["id"] == faculty["id"]


def test_profile_lifecycle_and_policy(conn):
    profile = create_profile(conn, profile_name="Taslak", source="expert", status="draft")
    with pytest.raises(ValueError):
        activate_profile(conn, profile["id"])
    validated = validate_profile(conn, profile["id"])
    assert validated["status"] == "validated"
    pending = submit_for_approval(conn, profile["id"], actor="koordinator")
    assert pending["status"] == "pending_approval"
    approved = approve_profile(conn, profile["id"], approved_by="dekan")
    assert approved["status"] == "approved"
    active = activate_profile(conn, profile["id"], actor="dekan")
    assert active["status"] == "active"
    policy = resolve_policy(conn)
    assert policy["max_consistency_ratio"] == pytest.approx(0.10)


def test_decision_run_stores_ahp_snapshot_and_staleness(conn):
    old_profile = seed_default_profile(conn)
    cur = conn.cursor()
    run_id = create_decision_run(
        cur,
        run_name="Test karar",
        year=2026,
        faculty_id=None,
        department_id=None,
        semester="Guz",
        ahp_profile_id=old_profile["id"],
        decision_policy_id=None,
        input_data_hash="hash",
        ahp_profile_version=old_profile["version"],
        ahp_weights_snapshot=old_profile["weights"],
        ahp_consistency_ratio=old_profile["consistency_ratio"],
        ahp_profile_status_at_run=old_profile["status"],
        ahp_profile_source=old_profile["source"],
    )
    conn.commit()
    cur.execute("SELECT ahp_profile_id, ahp_weights_snapshot_json FROM decision_runs WHERE id=?", (run_id,))
    row = cur.fetchone()
    assert int(row["ahp_profile_id"]) == int(old_profile["id"])
    assert "basari" in row["ahp_weights_snapshot_json"]
    create_profile(
        conn,
        profile_name="Yeni global",
        scope_type="global",
        source="expert",
        status="approved",
        weights={"basari": 0.4, "trend": 0.2, "populerlik": 0.2, "anket": 0.2},
        activate=True,
    )
    stale = list_stale_decisions(conn)
    assert any(int(item["decision_run_id"]) == int(run_id) for item in stale)


def test_impact_and_sensitivity(conn):
    profile = seed_default_profile(conn)
    cur = conn.cursor()
    run_id = create_decision_run(
        cur,
        run_name="Sensitivity run",
        year=2026,
        faculty_id=1,
        department_id=10,
        semester="Guz",
        ahp_profile_id=profile["id"],
        decision_policy_id=None,
        input_data_hash="hash",
        ahp_profile_version=profile["version"],
        ahp_weights_snapshot=profile["weights"],
        ahp_consistency_ratio=profile["consistency_ratio"],
        ahp_profile_status_at_run=profile["status"],
        ahp_profile_source=profile["source"],
    )
    cur.execute(
        """
        INSERT INTO course_score_breakdowns (
            decision_run_id, course_id, year, faculty_id, department_id,
            raw_values_json, normalized_values_json, weighted_values_json,
            weights_json, positive_distance, negative_distance,
            closeness_coefficient, final_score, contribution_json,
            ahp_profile_id, weighted_contribution_json
        )
        VALUES (?, 101, 2026, 1, 10, ?, '{}', '{}', ?, 0.1, 0.9, 0.9, 69.5, '{}', ?, '{}')
        """,
        (
            run_id,
            '{"basari": 0.72, "trend": 0.60, "populerlik": 0.80, "anket": 0.70}',
            '{"basari": 0.35, "trend": 0.25, "populerlik": 0.20, "anket": 0.20}',
            profile["id"],
        ),
    )
    conn.commit()
    impact = explain_weight_profile(conn, profile["id"])
    assert "basari" in impact["summary_text"]
    sensitivity = run_weight_sensitivity_analysis(conn, run_id, variation_percent=0.05)
    assert sensitivity["decision_run_id"] == run_id
    assert sensitivity["items"]


def test_ahp_api_smoke(monkeypatch, tmp_path):
    from app.api import routes
    from app.schemas.ahp import AHPCalculateRequest

    path = tmp_path / "ahp.db"
    db = sqlite3.connect(path)
    try:
        ensure_ahp_governance_schema(db)
    finally:
        db.close()
    monkeypatch.setattr(routes, "_get_db_path", lambda: str(path))
    profiles = routes.ahp_profiles()
    assert profiles["success"] is True
    calculated = routes.ahp_calculate(
        AHPCalculateRequest(
            criteria_keys=DEFAULT_CRITERIA_KEYS,
            pairwise_matrix=[[1, 1.4, 1.75, 1.75], [1 / 1.4, 1, 1.25, 1.25], [1 / 1.75, 1 / 1.25, 1, 1], [1 / 1.75, 1 / 1.25, 1, 1]],
        )
    )
    assert calculated["success"] is True
    consistency = routes.ahp_consistency_check(
        AHPCalculateRequest(criteria_keys=["a", "b"], pairwise_matrix=[[1, 3], [1 / 3, 1]])
    )
    assert consistency["success"] is True


def test_ahp_ui_importable():
    from app.ui.tabs.ahp_weight_page import AHPWeightPage

    assert AHPWeightPage is not None

from app.services.electre_tri_b_service import (
    assign_course_electre_tri_b,
    compare_to_profile,
    partial_concordance,
)


WEIGHTS = {"basari": 0.411, "trend": 0.201, "populerlik": 0.194, "anket": 0.194}
POLICY = {
    "curriculum_keep_threshold": 70,
    "pool_threshold": 50,
    "rest_threshold": 40,
    "cancel_candidate_threshold": 30,
    "electre_lambda": 0.65,
}


def test_partial_concordance_uses_q_p_linear_transition():
    assert partial_concordance(0.70, 0.70, 0.05, 0.15) == 1.0
    assert partial_concordance(0.55, 0.70, 0.05, 0.15) == 0.0
    assert partial_concordance(0.60, 0.70, 0.05, 0.15) == 0.5


def test_success_veto_blocks_high_profile():
    comparison = compare_to_profile(
        {"basari": 0.30, "trend": 0.90, "populerlik": 0.95, "anket": 0.90},
        {"name": "Mufredat", "status": 1, "values": {key: 0.70 for key in WEIGHTS}},
        WEIGHTS,
    )
    assert comparison["concordance"] > 0.5
    assert comparison["credibility"] == 0.0
    assert comparison["vetoed_criteria"] == ["basari"]


def test_pessimistic_assignment_selects_highest_outranked_profile():
    result = assign_course_electre_tri_b(
        {"basari": 0.48, "trend": 0.50, "populerlik": 0.8333, "anket": 0.50},
        WEIGHTS,
        POLICY,
    )
    assert result["category"] == "Havuz"
    assert result["recommended_status"] == 0
    assert result["classification_method"] == "electre_tri_b"
    assert len(result["comparisons"]) == 2


def test_course_below_rest_profile_is_cancel_candidate():
    result = assign_course_electre_tri_b(
        {"basari": 0.10, "trend": 0.20, "populerlik": 0.15, "anket": 0.20},
        WEIGHTS,
        POLICY,
    )
    assert result["category"] == "Iptal adayi"
    assert result["recommended_status"] == -2
    assert result["requires_manual_approval"] is True

import pytest

from app.services.candidate_recommendation_service import (
    neutral_survey_score,
    promethee_ii_rank,
    select_top_with_diversity,
    v_shape_preference,
)


def _alt(course_id, score, text):
    criteria = {
        "academic_fit": score,
        "curriculum_gap": score,
        "survey_demand": score,
        "resource_fit": score,
        "semester_fit": score,
        "non_overlap": score,
        "sector_value": score,
        "data_confidence": score,
    }
    return {"course_id": course_id, "name": text, "content_text": text, "criteria": criteria}


def test_v_shape_with_indifference():
    assert v_shape_preference(4, 5, 20) == 0.0
    assert v_shape_preference(20, 5, 20) == 1.0
    assert v_shape_preference(12.5, 5, 20) == pytest.approx(0.5)


def test_promethee_flows_use_n_minus_one_and_rank_descending():
    ranked = promethee_ii_rank([_alt(1, 90, "A"), _alt(2, 50, "B"), _alt(3, 10, "C")])
    assert [row["course_id"] for row in ranked] == [1, 2, 3]
    assert ranked[0]["phi_plus"] == pytest.approx(1.0)
    assert ranked[0]["phi_minus"] == pytest.approx(0.0)
    assert ranked[-1]["net_flow"] == pytest.approx(-1.0)


def test_missing_survey_is_neutral_not_zero():
    assert neutral_survey_score(None, 10) == (50.0, True)
    score, neutral = neutral_survey_score(5, 10)
    assert score > 50.0
    assert neutral is False


def test_diversity_can_prefer_distinct_course_in_top_list():
    ranked = [
        {**_alt(1, 90, "mutfak kültürü"), "net_flow": 1.0, "rank": 1},
        {**_alt(2, 89, "mutfak kültürü"), "net_flow": 0.95, "rank": 2},
        {**_alt(3, 85, "restoran yönetimi"), "net_flow": 0.90, "rank": 3},
    ]
    selected = select_top_with_diversity(ranked, top_n=2, ranking_weight=0.75)
    assert [row["course_id"] for row in selected] == [1, 3]

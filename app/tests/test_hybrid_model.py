# -*- coding: utf-8 -*-
"""Hibrit karar modeli (AHP-TOPSIS) + karşılaştırmalı değerlendirme testleri."""

from __future__ import annotations

import pytest

from app.services.hybrid_model_service import (
    MODEL_AHP_SAW,
    MODEL_ESIT_TOPSIS,
    MODEL_HIBRIT,
    compare_models,
    format_comparison_report,
    rank_from_scores,
    topsis_scores,
    weighted_sum_scores,
)

IDS = ["A", "B", "C", "D", "E"]
M = [[85, 70, 90, 60], [60, 80, 55, 75], [95, 50, 70, 40], [40, 90, 30, 85], [75, 65, 80, 70]]
KEYS = ["basari", "trend", "populerlik", "anket"]
W = [0.45, 0.20, 0.20, 0.15]


def test_topsis_scores_in_unit_range():
    s = topsis_scores(M, weights=W)
    assert len(s) == 5
    assert all(0.0 <= x <= 1.0 for x in s)


def test_weighted_sum_scores_in_unit_range():
    s = weighted_sum_scores(M, weights=W)
    assert all(0.0 <= x <= 1.0 for x in s)


def test_rank_is_permutation():
    s = topsis_scores(M, weights=W)
    r = rank_from_scores(s)
    assert sorted(r) == [1, 2, 3, 4, 5]
    # En yuksek skor 1. sirada
    assert r[s.index(max(s))] == 1


def test_compare_models_structure():
    res = compare_models(IDS, M, KEYS, W)
    assert set(res["models"]) == {MODEL_ESIT_TOPSIS, MODEL_AHP_SAW, MODEL_HIBRIT}
    assert len(res["comparisons"]) == 3
    for c in res["comparisons"]:
        assert "spearman" in c and "kendall_tau" in c
    assert len(res["ranking_table"]) == 5
    # ranking_table hibrit sirasina gore sirali
    siralar = [r["hibrit_sira"] for r in res["ranking_table"]]
    assert siralar == sorted(siralar)


def test_hybrid_differs_from_equal_weight_when_weights_skewed():
    # Cok carpik agirlik -> hibrit sirasi esit-agirlik TOPSIS'ten farkli olabilmeli
    res = compare_models(IDS, M, KEYS, [0.85, 0.05, 0.05, 0.05])
    hib = res["models"][MODEL_HIBRIT]["ranking"]
    eq = res["models"][MODEL_ESIT_TOPSIS]["ranking"]
    # En azindan skorlar farkli (siralama ayni cikabilir ama skorlar degismeli)
    assert res["models"][MODEL_HIBRIT]["scores"] != res["models"][MODEL_ESIT_TOPSIS]["scores"]
    assert isinstance(hib, list) and isinstance(eq, list)


def test_cost_criterion_inverted():
    # 2 ders, tek kriter MALIYET (dusuk iyi). Dusuk degerli ders 1. olmali.
    s = topsis_scores([[10.0], [90.0]], weights=[1.0], benefit=[False])
    assert s[0] > s[1]


def test_report_is_text():
    txt = format_comparison_report(compare_models(IDS, M, KEYS, W))
    assert "HIBRIT" in txt and "Spearman" in txt


def test_validation_errors():
    with pytest.raises(ValueError):
        compare_models(["X"], M, KEYS, W)  # course_ids sayisi uyumsuz

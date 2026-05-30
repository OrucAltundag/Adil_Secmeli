# -*- coding: utf-8 -*-
"""Algoritma Öneri Motoru governance/readiness uyarıları testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.decision_engine_page import DecisionEnginePage, build_candidate_rows, canonical_algorithm_key

pytestmark = pytest.mark.benchmark


class FakeDecisionApi:
    def get_recommendation(self, payload):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "algorithm": "LogisticRegression",
                "confidence": 0.79,
                "reason": "Küçük ve açıklanabilir veri profili.",
                "source": "rules",
                "candidates": ["LogisticRegression", "RandomForest"],
                "used_run_count": 0,
                "data_coverage": {"used_run_count": 0, "coverage_note": "Kural tabanlı öneri."},
            },
        )

    def get_algorithm_governance(self):
        return ApiResult(
            ok=True,
            data={
                "success": True,
                "data": [
                    {
                        "algorithm_key": "logistic_regression",
                        "algorithm_family": "ml",
                        "usage_role": "benchmark_only",
                        "user_facing_warning": "Benchmark baseline.",
                    },
                    {"algorithm_key": "random_forest", "algorithm_family": "ml", "usage_role": "advisory_ml"},
                ],
            },
        )

    def get_ml_readiness(self):
        return ApiResult(
            ok=True,
            data={
                "success": True,
                "data": [
                    {
                        "algorithm_key": "logistic_regression",
                        "readiness_level": "low",
                        "can_train": False,
                        "warnings": ["Minimum sample yetersiz."],
                    }
                ],
            },
        )

    def get_runs(self):
        return ApiResult(ok=True, data={"runs": []})


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_algorithm_name_is_canonicalized_for_governance_lookup():
    assert canonical_algorithm_key("LogisticRegression") == "logistic_regression"
    assert canonical_algorithm_key("XGBoostLike") == "xgboost"


def test_candidate_rows_explain_benchmark_only_elimination():
    recommendation = {"algorithm": "LogisticRegression", "reason": "Kural önerisi.", "candidates": ["LogisticRegression", "RandomForest"]}
    governance = [
        {"algorithm_key": "logistic_regression", "usage_role": "benchmark_only", "algorithm_family": "ml"},
        {"algorithm_key": "random_forest", "usage_role": "advisory_ml", "algorithm_family": "ml"},
    ]
    rows = build_candidate_rows(recommendation, governance, [])

    assert rows[0]["Durum"] == "Önerildi"
    assert rows[0]["Rol"] == "Sadece benchmark"
    assert rows[1]["Durum"] == "Elendi"


def test_decision_engine_shows_benchmark_only_warning_for_recommendation():
    root = _root_or_skip()
    try:
        page = DecisionEnginePage(root, FakeDecisionApi())

        assert page.role_card.value_label.cget("text") == "Sadece benchmark"
        assert page.final_card.value_label.cget("text") == "Hayır"
        assert "benchmark_only" in page.banner.label.cget("text")
        assert page.history_card.value_label.cget("text") == "0 run"
    finally:
        root.destroy()

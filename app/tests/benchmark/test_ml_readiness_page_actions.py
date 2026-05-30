# -*- coding: utf-8 -*-
"""ML readiness sayfası guard, rozet ve rapor aksiyonları testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.ml_readiness_page import MLReadinessPage, format_prediction_row

pytestmark = pytest.mark.benchmark


class FakeMLApi:
    def __init__(self) -> None:
        self.trained = False

    def get_ml_readiness(self):
        return ApiResult(
            ok=True,
            data={
                "success": True,
                "data": [
                    {
                        "algorithm_key": "random_forest",
                        "usage_role": "advisory_ml",
                        "sample_count": 12,
                        "required_min_samples": 200,
                        "readiness_level": "not_ready",
                        "can_train": False,
                        "can_use_for_production_decision": False,
                        "blocking_reasons": ["Minimum eğitim örneği sağlanmıyor."],
                    }
                ],
            },
        )

    def get_ml_model_runs(self):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def get_ml_predictions(self):
        return ApiResult(
            ok=True,
            data={
                "success": True,
                "data": [
                    {
                        "id": 5,
                        "algorithm_key": "random_forest",
                        "fallback_used": True,
                        "advisory_only": True,
                        "should_influence_decision": False,
                        "confidence_level": "low",
                        "uncertainty_reasons": ["sample düşük"],
                    }
                ],
            },
        )

    def get_ml_readiness_reports(self):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def train_ml_model(self, payload):
        self.trained = True
        return ApiResult(ok=True, data={"success": True, "data": {"status": "completed"}})


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_prediction_flags_are_translated_to_badges():
    row = format_prediction_row(
        {
            "id": 10,
            "algorithm_key": "random_forest",
            "fallback_used": True,
            "advisory_only": True,
            "should_influence_decision": False,
            "confidence_score": 0.41,
            "fallback_reason": "model yok",
        }
    )

    assert row["Fallback"] == "Evet"
    assert row["Advisory"] == "Evet"
    assert row["Karara Etki"] == "Hayır"
    assert row["Neden"] == "model yok"


def test_train_is_blocked_when_minimum_sample_guard_fails():
    root = _root_or_skip()
    api = FakeMLApi()
    try:
        page = MLReadinessPage(root, api)

        page.train_model()

        assert api.trained is False
        assert "Model train engellendi" in page.banner.label.cget("text")
        prediction_values = page.prediction_table.tree.item(page.prediction_table.tree.get_children()[0], "values")
        assert "Evet" in prediction_values
    finally:
        root.destroy()

# -*- coding: utf-8 -*-
"""Algorithm Comparison gerçek run ve baseline davranışı testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.comparison_page import ComparisonPage, _with_baseline_fields

pytestmark = pytest.mark.benchmark


class FakeComparisonApi:
    def __init__(self) -> None:
        self.selected_run_ids_for_comparison = ["run_1"]

    def get_run_detail(self, run_id):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "summary": {"run_id": run_id, "scenario_name": "real_ml_prediction"},
                "comparison_table": [
                    {"algorithm": "RandomPredictor", "classification.accuracy": 0.25, "classification.f1": 0.20},
                    {"algorithm": "RandomForest", "classification.accuracy": 0.75, "classification.f1": 0.70},
                ],
            },
        )

    def get_runs(self):
        return ApiResult(ok=True, used_mock=False, data={"runs": []})


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_baseline_diff_is_calculated_when_baseline_exists():
    rows = [{"algorithm": "RandomPredictor", "accuracy": 0.25}, {"algorithm": "RandomForest", "accuracy": 0.75}]

    row = _with_baseline_fields(rows[1], rows, "accuracy")

    assert row["baseline_diff"] == pytest.approx(0.5)
    assert row["confidence_interval"] == "—"


def test_comparison_loads_selected_run_rows_and_switches_line_view():
    root = _root_or_skip()
    try:
        page = ComparisonPage(root, FakeComparisonApi())

        assert [row["algorithm"] for row in page.rows] == ["RandomPredictor", "RandomForest"]
        assert "accuracy" in page.metric_cb["values"]
        page.view_cb.set("Çizgi grafik")
        page.apply_filters()

        assert page.chart_frame.pack_info()
    finally:
        root.destroy()

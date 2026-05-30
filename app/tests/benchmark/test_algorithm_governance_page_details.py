# -*- coding: utf-8 -*-
"""Algoritma Yönetişimi governed run detay paneli testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.algorithm_governance_page import AlgorithmGovernancePage

pytestmark = pytest.mark.benchmark


class FakeGovernanceApi:
    def __init__(self) -> None:
        self.executed = False

    def get_algorithm_governance(self):
        return ApiResult(
            ok=True,
            data={
                "success": True,
                "data": [
                    {
                        "display_name": "AHP",
                        "algorithm_family": "mcdm",
                        "task_type": "ranking",
                        "usage_role": "production_decision",
                        "can_affect_final_decision": True,
                        "minimum_sample_count": 2,
                        "recommended_metrics": ["rank_stability"],
                        "user_facing_warning": "Ana karar motoru.",
                    }
                ],
            },
        )

    def get_algorithm_tasks(self):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def get_governed_runs(self):
        return ApiResult(ok=True, data={"success": True, "data": [{"id": 7, "task_type": "classification", "sample_count": 4, "feature_count": 1, "status": "completed", "primary_metric_name": "f1_macro", "started_at": "2026-05-30"}]})

    def get_governed_run_metrics(self, run_id):
        return ApiResult(ok=True, data={"success": True, "data": [{"benchmark_run_id": run_id, "algorithm_key": "majority_class_predictor"}]})

    def get_governed_run_validation(self, run_id):
        return ApiResult(ok=True, data={"success": True, "data": [{"benchmark_run_id": run_id, "fold_count": 3}]})

    def get_governed_run_statistics(self, run_id):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def get_governed_run_diagnostics(self, run_id):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def get_governed_run_leakage(self, run_id):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def get_governed_run_clustering(self, run_id):
        return ApiResult(ok=True, data={"success": True, "data": []})

    def execute_governed_run(self, payload):
        self.executed = True
        return ApiResult(ok=True, data={"success": True, "data": {"run_id": 8}}, used_mock=False)


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_algorithm_governance_loads_run_details_and_executes_form():
    root = _root_or_skip()
    api = FakeGovernanceApi()
    try:
        page = AlgorithmGovernancePage(root, api)

        metrics_text = page.detail_previews["metrics"].text.get("1.0", "end")
        assert "majority_class_predictor" in metrics_text

        page.execute_governed_run()
        assert api.executed is True
    finally:
        root.destroy()

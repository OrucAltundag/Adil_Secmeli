# -*- coding: utf-8 -*-
"""Benchmark Dashboard readiness ve gerçek metrik bağlama testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.dashboard_page import DashboardPage

pytestmark = pytest.mark.benchmark


class FakeDashboardApi:
    def __init__(self, *, dataset_loaded: bool = True) -> None:
        self.last_dataset_name = "test_dataset" if dataset_loaded else None
        self.last_dataset_used_mock = False
        self.last_dataset = {"quality_summary": {"row_count": 42}} if dataset_loaded else None
        self.executed_payload = None

    def get_algorithms(self):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "algorithms": [
                    {"name": "AHP", "group": "mcdm"},
                    {"name": "TOPSIS", "group": "mcdm"},
                    {"name": "RandomForest", "group": "ml"},
                ]
            },
        )

    def get_scenarios(self):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "scenarios": [
                    {
                        "name": "real_mcdm_recommendation",
                        "description": "MCDM",
                        "problem_type": "ranking",
                        "default_algorithms": ["AHP", "TOPSIS"],
                    }
                ]
            },
        )

    def execute_run(self, payload):
        self.executed_payload = payload
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "summary": {
                    "run_id": "run_test",
                    "scenario_name": "real_mcdm_recommendation",
                    "dataset_name": "test_dataset",
                    "status": "completed",
                    "started_at": "2026-05-30T12:00:00",
                    "algorithms": ["AHP", "TOPSIS"],
                },
                "comparison_table": [
                    {"algorithm": "AHP", "recommendation.hit_at_k": 0.8, "recommendation.ndcg_at_k": 0.7, "performance.latency_ms": 12.0},
                    {"algorithm": "TOPSIS", "recommendation.hit_at_k": 0.9, "recommendation.ndcg_at_k": 0.75, "performance.latency_ms": 9.0},
                ],
            },
        )


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_dashboard_filters_algorithms_and_enables_run_when_ready():
    root = _root_or_skip()
    try:
        page = DashboardPage(root, FakeDashboardApi(dataset_loaded=True))

        assert set(page.algorithm_vars) == {"AHP", "TOPSIS"}
        assert page.run_btn.instate(["!disabled"])

        page.run_benchmark()

        assert page.metric_cards["hit_at_10"].value_label.cget("text") == "0.9"
        assert page.metric_cards["latency_ms"].value_label.cget("text") == "9.0"
    finally:
        root.destroy()


def test_dashboard_disables_run_without_loaded_dataset():
    root = _root_or_skip()
    try:
        page = DashboardPage(root, FakeDashboardApi(dataset_loaded=False))

        assert page.run_btn.instate(["disabled"])
        assert page.readiness_cards["dataset"].value_label.cget("text") == "Eksik"
    finally:
        root.destroy()

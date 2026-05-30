# -*- coding: utf-8 -*-
"""Yerleştirme Adaleti gerçek run çıktısı ve parametre payload testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.allocation_fairness_page import AllocationFairnessPage, normalize_allocation_result

pytestmark = pytest.mark.benchmark


def _allocation_payload() -> dict:
    return {
        "summary": {"run_id": "run_alloc", "scenario_name": "allocation_fairness"},
        "comparison_table": [
            {
                "algorithm": "GaleShapley",
                "fairness.average_rank": 1.0,
                "fairness.top_k_satisfaction": 1.0,
                "fairness.envy_score": 0.0,
                "fairness.seat_fill_rate": 0.5,
            }
        ],
        "details": {
            "results": {
                "GaleShapley": {
                    "output": {
                        "assignments": [
                            {
                                "student_id": 1,
                                "course_id": 101,
                                "rank_received": 1,
                                "allocated": True,
                                "faculty_id": 10,
                                "department_id": 20,
                                "course_capacity": 1,
                            },
                            {
                                "student_id": 2,
                                "course_id": None,
                                "rank_received": None,
                                "allocated": False,
                                "faculty_id": 10,
                                "department_id": 21,
                                "unassigned_reason": "Kontenjan dolu.",
                            },
                        ]
                    },
                    "metrics": {
                        "fairness": {
                            "average_rank": 1.0,
                            "top_k_satisfaction": 1.0,
                            "envy_score": 0.0,
                            "seat_fill_rate": 0.5,
                        }
                    },
                }
            }
        },
    }


class FakeAllocationApi:
    def __init__(self) -> None:
        self.payload = None

    def execute_run(self, payload):
        self.payload = payload
        return ApiResult(ok=True, data=_allocation_payload(), used_mock=False)


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_allocation_result_builds_assignments_breakdown_and_issues():
    view = normalize_allocation_result(_allocation_payload(), top_k=3)

    assert view["fairness_rows"][0]["assigned"] == 1
    assert view["fairness_rows"][0]["unassigned"] == 1
    assert any(row["scope"] == "Bölüm" and row["group"] == "20" for row in view["breakdown_rows"])
    assert any(row["type"] == "Atanmayan" and row["reason"] == "Kontenjan dolu." for row in view["issue_rows"])
    assert view["transfer"]["status"] == "İnceleme gerekli"


def test_allocation_page_sends_ui_parameters_to_payload():
    root = _root_or_skip()
    api = FakeAllocationApi()
    try:
        page = AllocationFairnessPage(root, api)
        page.top_k_var.set(5)
        page.capacity_scale_var.set(1.3)
        page.priority_var.set("Tercih sırası")
        page.department_rule_var.set("Esnek")

        page.run_allocation()

        assert api.payload["scenario"] == "allocation_fairness"
        assert api.payload["top_k"] == 5
        assert api.payload["allocation_parameters"]["capacity_scale"] == 1.3
        assert api.payload["allocation_parameters"]["priority_rule"] == "preference_rank"
        assert api.payload["allocation_parameters"]["department_rule"] == "flexible"
        assert page.metric_cards["transfer"].value_label.cget("text") == "İnceleme gerekli"
    finally:
        root.destroy()

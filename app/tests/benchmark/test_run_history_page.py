# -*- coding: utf-8 -*-
"""Run History tarih filtresi, detay ve sepet davranışı testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.run_history_page import RunHistoryPage, _date_in_range, _parse_date_range, _row_datetime

pytestmark = pytest.mark.benchmark


class FakeRunHistoryApi:
    def __init__(self) -> None:
        self.selected_run_ids_for_comparison = []

    def get_runs(self):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "runs": [
                    {"run_id": "run_1", "date": "2024-05-18 10:00:00", "scenario": "real_mcdm_recommendation", "dataset": "d1", "algorithms_count": 2, "status": "completed"},
                    {"run_id": "run_2", "date": "2024-06-01 10:00:00", "scenario": "real_ml_prediction", "dataset": "d2", "algorithms_count": 1, "status": "completed"},
                ]
            },
        )

    def get_governed_runs(self):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={"success": True, "data": [{"id": 7, "task_type": "classification", "status": "completed", "started_at": "2024-05-17T09:00:00"}]},
        )

    def get_run_detail(self, run_id):
        return ApiResult(
            ok=True,
            used_mock=False,
            data={
                "summary": {"run_id": run_id, "status": "completed"},
                "comparison_table": [{"algorithm": "AHP", "recommendation.hit_at_k": 0.8}],
                "details": {"validation": [{"fold": 1}], "diagnostics": {"ok": True}, "leakage": {"blocked": False}},
            },
        )


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_date_range_helpers_include_full_end_day():
    start, end = _parse_date_range("2024-05-01 - 2024-05-18")

    assert _date_in_range(_row_datetime({"date": "2024-05-18 10:00:00"}), start, end)
    assert not _date_in_range(_row_datetime({"date": "2024-06-01 10:00:00"}), start, end)


def test_run_history_filters_details_adds_basket_and_exports_json(monkeypatch, tmp_path):
    root = _root_or_skip()
    api = FakeRunHistoryApi()
    try:
        page = RunHistoryPage(root, api)
        page.date_entry.delete(0, tk.END)
        page.date_entry.insert(0, "2024-05-01 - 2024-05-18")

        page.apply_filters()

        children = page.table.tree.get_children()
        assert len(children) == 2
        page.source_cb.set("Classic JSON")
        page.apply_filters()
        children = page.table.tree.get_children()
        assert len(children) == 1
        page.table.tree.selection_set(children[0])
        page.show_detail()
        page.compare_selected()
        monkeypatch.chdir(tmp_path)
        page.export_detail("json")

        assert api.selected_run_ids_for_comparison == ["run_1"]
        assert page.last_detail["summary"]["run_id"] == "run_1"
        assert (tmp_path / "reports" / "benchmark_exports" / "run_1.json").exists()
    finally:
        root.destroy()

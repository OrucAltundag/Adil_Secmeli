# -*- coding: utf-8 -*-
"""Dataset Lab sayfası için gerçek veri bağlama smoke testleri."""

from __future__ import annotations

import tkinter as tk

import pytest

from app.ui.benchmark.api_client import ApiResult
from app.ui.benchmark.pages.dataset_lab_page import DatasetLabPage

pytestmark = pytest.mark.benchmark


class FakeDatasetApi:
    def __init__(self, *, used_mock: bool = False) -> None:
        self.used_mock = used_mock
        self.last_payload = None

    def load_dataset(self, payload):
        self.last_payload = payload
        return ApiResult(
            ok=not self.used_mock,
            used_mock=self.used_mock,
            data={
                "dataset_name": "test_dataset",
                "layer_counts": {
                    "raw_real": {"students": 2, "courses": 1, "preferences": 2},
                    "derived": {"student_course_features": 2},
                    "synthetic": {"5k": 5000},
                },
                "preview": {
                    "layer": "derived",
                    "table": "student_course_features",
                    "columns": ["course_id", "score"],
                    "rows": [{"course_id": 10, "score": 0.75}, {"course_id": 11, "score": 0.65}],
                },
                "quality_summary": {
                    "row_count": 2,
                    "column_count": 2,
                    "missing_ratio": 0.0,
                    "target_column": "course_id",
                    "target_present": True,
                    "class_distribution": {"10": 1, "11": 1},
                },
            },
        )


def _root_or_skip():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    root.withdraw()
    return root


def test_dataset_lab_loads_real_preview_and_quality_cards():
    root = _root_or_skip()
    api = FakeDatasetApi()
    try:
        page = DatasetLabPage(root, api)
        page.selected_file.set("data/benchmark/raw_real")

        page.load_dataset()

        assert api.last_payload["source_type"] == "csv"
        assert api.last_payload["synth_noise_std"] == 0.03
        assert page.preview_table.columns == ["course_id", "score"]
        assert page.quality_cards["target_present"].value_label.cget("text") == "Var"
        assert "Gerçek API" in page.source_badge.label.cget("text")
    finally:
        root.destroy()


def test_dataset_lab_preflight_reports_missing_csv_folder():
    root = _root_or_skip()
    try:
        page = DatasetLabPage(root, FakeDatasetApi())
        ok, message = page._preflight_source("data/benchmark/not_found")

        assert ok is False
        assert "CSV klasörü bulunamadı" in message
    finally:
        root.destroy()

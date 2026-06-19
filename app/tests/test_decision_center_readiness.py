from __future__ import annotations

import logging

import pytest

from app.ui.tabs.decision_center_page import DecisionCenterPage


class _WidgetStub:
    def __init__(self, value=""):
        self.value = value
        self.text = ""

    def get(self, *args):
        return self.value

    def delete(self, *args):
        self.text = ""

    def insert(self, *args):
        self.text += str(args[-1])

    def config(self, **kwargs):
        self.text = kwargs.get("text", self.text)


@pytest.mark.parametrize(
    ("year", "expected_status", "expected_message"),
    [
        ("", "Fakülte ve yıl seçimi bekleniyor.", "fakülte ve yıl seçiniz"),
        ("geçersiz", "Geçerli bir yıl seçimi bekleniyor.", "geçerli bir yıl seçiniz"),
    ],
)
def test_load_readiness_handles_missing_or_invalid_year_without_error(
    year, expected_status, expected_message, caplog
):
    page = object.__new__(DecisionCenterPage)
    page.txt_readiness = _WidgetStub()
    page.lbl_readiness = _WidgetStub()
    page.tree_overrides = None
    page._override_ids = {}
    page._last_readiness_gate = {"stale": True}
    page.cb_year = _WidgetStub(year)
    page.cb_faculty = _WidgetStub("Mühendislik")
    page._faculty_map = {"Mühendislik": 1}

    with caplog.at_level(logging.ERROR):
        page._load_readiness()

    assert page.lbl_readiness.text == expected_status
    assert expected_message in page.txt_readiness.text
    assert page._last_readiness_gate is None
    assert "Hazırlık kontrolü yüklenemedi" not in caplog.text

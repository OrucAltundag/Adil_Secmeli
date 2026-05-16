# -*- coding: utf-8 -*-
"""Algoritma kataloğu testleri."""

from __future__ import annotations

import pytest

from app.health.health_registry import algorithm_catalog
from app.services.health_service import list_algorithm_catalog

pytestmark = pytest.mark.unit

VALID_STATUS = {"ACTIVE", "PLANNED", "NOT_APPLICABLE"}

REQUIRED_ACTIVE = {
    "SQLite Connection Test",
    "Schema Validation",
    "AHP Consistency Ratio Check",
    "AHP Weight Sum Check",
    "TOPSIS Normalization Check",
    "Layer Violation Detection",
    "Weighted Scoring",
}


def test_catalog_items_have_required_keys():
    catalog = algorithm_catalog()
    assert len(catalog) > 50
    for item in catalog:
        assert {"name", "status", "purpose", "used_in"} <= set(item)
        assert item["status"] in VALID_STATUS


def test_catalog_is_deduplicated_by_name():
    names = [i["name"].strip().lower() for i in algorithm_catalog()]
    assert len(names) == len(set(names))


def test_required_active_algorithms_present():
    active = {
        i["name"]
        for i in algorithm_catalog()
        if i["status"] == "ACTIVE"
    }
    missing = REQUIRED_ACTIVE - active
    assert not missing, f"Eksik ACTIVE kalemler: {missing}"


def test_service_exposes_catalog():
    assert list_algorithm_catalog() == algorithm_catalog()
    assert any(i["status"] == "PLANNED" for i in list_algorithm_catalog())

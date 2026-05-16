# -*- coding: utf-8 -*-
"""Sağlık skoru testleri."""

from __future__ import annotations

import pytest

from app.health.health_score import (
    BUCKET_WEIGHTS,
    compute_overall_score,
    overall_status_for,
)
from app.health.models import HealthCheckResult

pytestmark = pytest.mark.unit


def _r(category: str, status: str) -> HealthCheckResult:
    return HealthCheckResult(category=category, name="t", status=status)


def test_bucket_weights_sum_to_one():
    assert abs(sum(BUCKET_WEIGHTS.values()) - 1.0) < 1e-9


def test_overall_status_bands():
    assert overall_status_for(95) == "SAĞLIKLI"
    assert overall_status_for(75) == "UYARI"
    assert overall_status_for(50) == "RİSKLİ"
    assert overall_status_for(10) == "KRİTİK"


def test_all_ok_is_full_score():
    results = [_r("Veritabanı", "OK"), _r("Şema", "OK")]
    score, buckets = compute_overall_score(results)
    assert score == 100.0
    assert "database" in buckets and buckets["database"] == 100.0


def test_fixed_counts_as_full_score():
    results = [_r("Veritabanı", "FIXED")]
    score, _ = compute_overall_score(results)
    assert score == 100.0


def test_skipped_is_neutral():
    results = [_r("Veritabanı", "OK"), _r("Performans", "SKIPPED")]
    score, buckets = compute_overall_score(results)
    assert score == 100.0


def test_critical_lowers_score():
    results = [_r("Veritabanı", "CRITICAL")]
    score, _ = compute_overall_score(results)
    assert score < 30.0


def test_empty_results_default_full():
    score, buckets = compute_overall_score([])
    assert score == 100.0
    assert buckets == {}

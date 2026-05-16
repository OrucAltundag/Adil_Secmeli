# -*- coding: utf-8 -*-
"""Sağlık veri modelleri testleri."""

from __future__ import annotations

import pytest

from app.health.models import (
    HealthCheckResult,
    HealthReport,
    HealthSeverity,
    HealthStatus,
)

pytestmark = pytest.mark.unit


def test_status_enum_has_fixed():
    assert HealthStatus.FIXED.value == "FIXED"
    assert HealthStatus.coerce("fixed") is HealthStatus.FIXED
    assert HealthStatus.coerce("bilinmeyen") is HealthStatus.OK


def test_severity_coerce():
    assert HealthSeverity.coerce("high") is HealthSeverity.HIGH
    assert HealthSeverity.coerce(None) is HealthSeverity.MEDIUM


def test_check_result_to_dict_has_autofix_fields():
    res = HealthCheckResult(category="X", name="Y", status="OK")
    data = res.to_dict()
    assert data["auto_fix_available"] is False
    assert data["auto_fix_applied"] is False
    assert data["status"] == "OK"
    assert data["timestamp"]


def test_check_result_normalizes_status_and_severity():
    res = HealthCheckResult(
        category="X", name="Y", status="warning", severity="critical"
    )
    assert res.status == "WARNING"
    assert res.severity == "CRITICAL"
    assert res.is_problem is True


def test_report_to_dict_has_fixed_count():
    rep = HealthReport(
        overall_status="SAĞLIKLI",
        score=95.0,
        total_checks=1,
        ok_count=1,
        warning_count=0,
        critical_count=0,
        failed_count=0,
        skipped_count=0,
        results=[HealthCheckResult(category="X", name="Y")],
        fixed_count=2,
    )
    data = rep.to_dict()
    assert data["fixed_count"] == 2
    assert data["score"] == 95.0
    assert len(data["results"]) == 1
    assert rep.results_by_category()["X"]

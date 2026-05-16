# -*- coding: utf-8 -*-
"""Health runner mod testleri (geçici DB; gerçek veri kullanılmaz)."""

from __future__ import annotations

import sqlite3

import pytest

from app.health.health_runner import HealthRunner
from app.health.models import HealthReport, HealthStatus

pytestmark = pytest.mark.db


@pytest.fixture
def tmp_db_path(tmp_path):
    path = str(tmp_path / "health_runner.db")
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE havuz (id INTEGER PRIMARY KEY, ders_id INTEGER,
                            yil INTEGER, statu INTEGER);
        CREATE TABLE ders_kriterleri (id INTEGER PRIMARY KEY,
                            ders_id INTEGER, yil INTEGER, donem INTEGER);
        INSERT INTO ders (ders_id, ad) VALUES (1, 'Test Ders');
        INSERT INTO havuz (ders_id, yil, statu) VALUES (1, 2026, 0);
        """
    )
    conn.commit()
    conn.close()
    return path


def _counts_consistent(report: HealthReport) -> bool:
    summed = (
        report.ok_count
        + report.info_count
        + report.warning_count
        + report.critical_count
        + report.failed_count
        + report.skipped_count
        + report.fixed_count
    )
    return summed == report.total_checks


def test_quick_mode_returns_report(tmp_db_path):
    report = HealthRunner(db_path=tmp_db_path).run("quick")
    assert isinstance(report, HealthReport)
    assert report.mode == "quick"
    assert report.total_checks > 0
    assert _counts_consistent(report)


def test_full_mode_no_crash_and_no_failed_core(tmp_db_path):
    report = HealthRunner(db_path=tmp_db_path).run("full")
    assert report.mode == "full"
    assert report.total_checks >= report.ok_count
    assert _counts_consistent(report)
    # Bir kontrol patlasa bile runner çökmemeli; rapor üretilmeli.
    assert report.overall_status in {"SAĞLIKLI", "UYARI", "RİSKLİ", "KRİTİK"}


def test_audit_mode_subset(tmp_db_path):
    report = HealthRunner(db_path=tmp_db_path).run("audit")
    full = HealthRunner(db_path=tmp_db_path).run("full")
    assert report.total_checks < full.total_checks
    assert _counts_consistent(report)


def test_invalid_mode_falls_back_to_full(tmp_db_path):
    report = HealthRunner(db_path=tmp_db_path).run("bilinmeyen")
    assert report.mode == "full"


def test_repair_mode_safe(tmp_db_path):
    report = HealthRunner(db_path=tmp_db_path).run("repair")
    assert report.mode == "repair"
    # repair sadece güvenli sonuçlar üretir; FAILED/CRITICAL beklenmez.
    assert report.failed_count == 0
    statuses = {r.status for r in report.results}
    assert statuses.issubset(
        {
            HealthStatus.FIXED.value,
            HealthStatus.OK.value,
            HealthStatus.INFO.value,
            HealthStatus.SKIPPED.value,
            HealthStatus.WARNING.value,
        }
    )

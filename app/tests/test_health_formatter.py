# -*- coding: utf-8 -*-
"""Sağlık formatter testleri."""

from __future__ import annotations

import pytest

from app.health.health_formatter import (
    format_algorithm_catalog,
    format_report,
)
from app.health.models import HealthCheckResult, HealthReport
from app.ui.tabs.system_health_page import format_report_snapshot

pytestmark = pytest.mark.unit


def _report() -> HealthReport:
    results = [
        HealthCheckResult(
            category="Veritabanı",
            name="SQLite bağlantı kontrolü",
            status="OK",
            message="Veritabanı bağlantısı başarılı.",
            detail="data/adil_secmeli.db",
            suggestion="İşlem gerekmiyor.",
            source="SQLiteConnectionCheck",
            duration_ms=12.0,
        ),
        HealthCheckResult(
            category="Otomatik Düzeltme",
            name="Eksik logs klasörü oluşturuldu",
            status="FIXED",
            message="logs klasörü güvenli şekilde oluşturuldu.",
            source="auto_repair",
            auto_fix_available=True,
            auto_fix_applied=True,
        ),
    ]
    return HealthReport(
        overall_status="SAĞLIKLI",
        score=98.0,
        total_checks=2,
        ok_count=1,
        warning_count=0,
        critical_count=0,
        failed_count=0,
        skipped_count=0,
        fixed_count=1,
        results=results,
        summary_message="Sistem sağlıklı.",
    )


def test_format_report_structure():
    text = format_report(_report(), developer=False)
    assert "GENEL SİSTEM SAĞLIĞI" in text
    assert "Sağlık Puanı : 98 / 100" in text
    assert "Düzeltildi   : 1" in text
    assert "VERITABANI" in text or "VERİTABANI" in text
    assert "Kaynak   : SQLiteConnectionCheck" in text
    assert "[FIXED]" in text


def test_format_report_developer_adds_severity():
    text = format_report(_report(), developer=True)
    assert "Önem" in text


def test_format_algorithm_catalog():
    text = format_algorithm_catalog()
    assert "MEVCUT KONTROLLER / ALGORİTMALAR" in text
    assert "[ACTIVE]" in text
    assert "[PLANNED]" in text


def test_format_report_snapshot_marks_previous_report():
    text = format_report_snapshot(_report(), developer=False)
    assert "ÖNCEKİ SAĞLIK KONTROLÜ" in text
    assert "Yeni değerler 'Sağlık Raporu' sekmesinde kalır." in text
    assert "Önceki Puan   : 98 / 100" in text
    assert "GENEL SİSTEM SAĞLIĞI" in text

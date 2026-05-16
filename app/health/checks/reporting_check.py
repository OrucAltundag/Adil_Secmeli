# -*- coding: utf-8 -*-
"""Raporlama ve dışa aktarma sağlık kontrolleri."""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path

from app.health.checks.base_check import BaseHealthCheck
from app.health.health_config import REPORT_DIR_NAME
from app.health.models import HealthContext, HealthSeverity, HealthStatus


class ReportDirectoryCheck(BaseHealthCheck):
    name = "Rapor klasörü kontrolü"
    category = "Raporlama / Analiz"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.reporting_check.ReportDirectoryCheck"

    def run(self, context: HealthContext):
        report_dir = context.root_path / REPORT_DIR_NAME
        report_dir.mkdir(parents=True, exist_ok=True)
        return self.result(
            HealthStatus.OK,
            "Rapor klasörü mevcut ve erişilebilir.",
            detail=str(report_dir),
            metadata={"report_dir": str(report_dir)},
        )


class ExportPermissionCheck(BaseHealthCheck):
    name = "Rapor dışa aktarma yazma izni kontrolü"
    category = "Raporlama / Analiz"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.reporting_check.ExportPermissionCheck"

    def run(self, context: HealthContext):
        report_dir = context.root_path / REPORT_DIR_NAME
        report_dir.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix="health_export_", suffix=".tmp", dir=str(report_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("health export probe")
        finally:
            Path(path).unlink(missing_ok=True)
        return self.result(
            HealthStatus.OK,
            "Rapor klasörüne test dosyası yazılıp temizlenebildi.",
            detail=str(report_dir),
        )


class PDFExportCheck(BaseHealthCheck):
    name = "PDF export altyapısı kontrolü"
    category = "Raporlama / Analiz"
    source = "app.health.checks.reporting_check.PDFExportCheck"

    def run(self, context: HealthContext):
        packages = ("reportlab", "weasyprint")
        available = [package for package in packages if importlib.util.find_spec(package)]
        status = HealthStatus.OK if available else HealthStatus.SKIPPED
        return self.result(
            status,
            "PDF export bağımlılıkları değerlendirildi.",
            detail=f"Kullanılabilir paketler: {', '.join(available) or 'yok'}",
            suggestion="PDF export gerekiyorsa reportlab veya weasyprint bağımlılığını ekleyin.",
        )


class ExcelExportCheck(BaseHealthCheck):
    name = "Excel export altyapısı kontrolü"
    category = "Raporlama / Analiz"
    source = "app.health.checks.reporting_check.ExcelExportCheck"

    def run(self, context: HealthContext):
        packages = ("openpyxl", "xlsxwriter")
        available = [package for package in packages if importlib.util.find_spec(package)]
        status = HealthStatus.OK if available else HealthStatus.SKIPPED
        return self.result(status, "Excel export bağımlılıkları değerlendirildi.", detail=", ".join(available) or "yok")


class ImportFileValidationCheck(BaseHealthCheck):
    name = "Import dosya doğrulama kontrolü"
    category = "Raporlama / Analiz"
    source = "app.health.checks.reporting_check.ImportFileValidationCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Import dosya doğrulama kontrolleri güvenlik servisleriyle aşamalı genişletilecek.",
            suggestion="Dosya uzantısı, MIME tipi ve satır limiti kontrollerini merkezi import servisine bağlayın.",
        )

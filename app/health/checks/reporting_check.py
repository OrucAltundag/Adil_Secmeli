# -*- coding: utf-8 -*-
"""Raporlama / dışa aktarma sağlık kontrolleri."""

from __future__ import annotations

import importlib.util
import os
import tempfile

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _ReportingCheck(BaseHealthCheck):
    category = "Raporlama"
    score_bucket = "reporting_analytics"


class ReportDirectoryCheck(_ReportingCheck):
    name = "Rapor dizini kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        path = context.health_config.reports_path()
        if path.exists():
            return self.ok(
                "Rapor dizini mevcut.",
                detail=str(path),
                metadata={"path": str(path)},
            )
        try:
            path.mkdir(parents=True, exist_ok=True)
            return self.info(
                "Rapor dizini bulunamadı, oluşturuldu.",
                detail=str(path),
                suggestion="Bilgilendirme amaçlıdır.",
                metadata={"path": str(path), "created": True},
            )
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Rapor dizini oluşturulamadı.",
                detail=f"{type(exc).__name__}: {exc} ({path})",
                suggestion="Yazma izni olan bir rapor klasörü tanımlayın.",
            )


class ExportPermissionCheck(_ReportingCheck):
    name = "Dışa aktarma yazma izni kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        path = context.health_config.reports_path()
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".health_write_probe.tmp"
        try:
            probe.write_text("probe", encoding="utf-8")
            content = probe.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Rapor klasörüne yazma izni yok.",
                detail=f"{type(exc).__name__}: {exc} ({path})",
                suggestion="Yazma izni olan bir klasör seçin.",
            )
        finally:
            try:
                if probe.exists():
                    probe.unlink()
            except Exception:
                pass
        if content != "probe":
            return self.warning(
                "Yazma testi doğrulanamadı.",
                detail="Yazılan ve okunan içerik eşleşmedi.",
                suggestion="Disk/izin durumunu kontrol edin.",
            )
        return self.ok(
            "Rapor klasörüne yazılabiliyor (geçici dosya temizlendi).",
            detail=str(path),
        )


class PDFExportCheck(_ReportingCheck):
    name = "PDF dışa aktarma altyapısı kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        available = [
            name
            for name in ("reportlab", "fpdf", "weasyprint")
            if importlib.util.find_spec(name) is not None
        ]
        if not available:
            return self.info(
                "PDF dışa aktarma kütüphanesi bulunamadı.",
                detail="reportlab/fpdf/weasyprint yüklü değil.",
                suggestion="PDF çıktısı gerekiyorsa 'pip install reportlab' kurun.",
            )
        return self.ok(
            "PDF dışa aktarma altyapısı mevcut.",
            detail=f"Bulunan kütüphane(ler): {', '.join(available)}",
            metadata={"libraries": available},
        )


class ExcelExportCheck(_ReportingCheck):
    name = "Excel dışa aktarma kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        if importlib.util.find_spec("openpyxl") is None:
            return self.warning(
                "Excel dışa aktarma için openpyxl yok.",
                detail="openpyxl modülü bulunamadı.",
                suggestion="'pip install openpyxl' komutunu çalıştırın.",
            )
        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            if ws is None:
                raise RuntimeError("Workbook aktif sayfası alınamadı.")
            ws["A1"] = "health"
            fd, tmp = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd)
            wb.save(tmp)
            ok = os.path.getsize(tmp) > 0
            os.unlink(tmp)
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Excel test dosyası üretilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="openpyxl kurulumunu doğrulayın.",
            )
        if not ok:
            return self.warning(
                "Excel test dosyası boş üretildi.",
                detail="Kaydedilen xlsx boyutu 0.",
                suggestion="Disk/izin durumunu kontrol edin.",
            )
        return self.ok(
            "Excel dışa aktarma çalışıyor (test dosyası üretildi ve silindi).",
            detail="openpyxl ile geçici .xlsx üretildi.",
        )


class ImportFileValidationCheck(_ReportingCheck):
    name = "Import dosya doğrulama kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        allowed = context.app_config.allowed_upload_extensions
        try:
            from app.services import file_upload_security_service  # noqa: F401

            has_service = True
        except Exception:  # noqa: BLE001
            has_service = False
        if not has_service:
            return self.info(
                "Dosya doğrulama servisi bulunamadı.",
                detail="file_upload_security_service import edilemedi.",
                suggestion="Import güvenlik servisini kontrol edin.",
            )
        return self.ok(
            "Yüklenen dosya formatları doğrulanabiliyor.",
            detail=f"İzinli uzantılar: {allowed}",
            metadata={"allowed_extensions": allowed},
        )

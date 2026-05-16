# -*- coding: utf-8 -*-
"""Log sağlık kontrolleri."""

from __future__ import annotations

from collections import deque

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _LogCheck(BaseHealthCheck):
    category = "Log"
    score_bucket = "architecture"

    def _log_files(self, context: HealthContext):
        logs_dir = context.health_config.logs_path()
        if not logs_dir.exists():
            return None
        return sorted(logs_dir.glob("*.log"))


class LogDirectoryCheck(_LogCheck):
    name = "Log dizini kontrolü"
    quick = True
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        logs_dir = context.health_config.logs_path()
        if not logs_dir.exists():
            return self.info(
                "Log dizini bulunamadı.",
                detail=str(logs_dir),
                suggestion="Loglama yapılandırmasını/log klasörünü oluşturun.",
            )
        files = list(logs_dir.glob("*.log"))
        return self.ok(
            f"Log dizini mevcut ({len(files)} log dosyası).",
            detail=str(logs_dir),
            metadata={"log_files": len(files)},
        )


class ErrorLogScannerCheck(_LogCheck):
    name = "Hata logu tarayıcı"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        files = self._log_files(context)
        if not files:
            return self.info(
                "Taranacak log dosyası yok.",
                detail="logs/*.log bulunamadı.",
                suggestion="Loglama etkinleştirildikten sonra tekrar kontrol edin.",
            )
        errors = 0
        samples: list[str] = []
        for log_file in files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        if " ERROR " in line or " CRITICAL " in line:
                            errors += 1
                            if len(samples) < 5:
                                samples.append(line.strip()[:200])
            except Exception:  # noqa: BLE001
                continue
        if errors:
            sev = self.critical if errors > 50 else self.warning
            return sev(
                f"Loglarda {errors} ERROR/CRITICAL satırı var.",
                detail="Örnekler:\n- " + "\n- ".join(samples),
                suggestion="Hataların kök nedenini inceleyin.",
                metadata={"error_count": errors},
            )
        return self.ok(
            "Loglarda ERROR/CRITICAL satırı bulunmadı.",
            detail=f"{len(files)} log dosyası tarandı.",
        )


class WarningCounterCheck(_LogCheck):
    name = "Uyarı sayacı"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        files = self._log_files(context)
        if not files:
            return self.info(
                "Taranacak log dosyası yok.",
                detail="logs/*.log bulunamadı.",
                suggestion="Loglama etkinleştirildikten sonra tekrar kontrol edin.",
            )
        warnings = 0
        for log_file in files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as fh:
                    warnings += sum(1 for line in fh if " WARNING " in line)
            except Exception:  # noqa: BLE001
                continue
        if warnings > 200:
            return self.warning(
                f"Loglarda çok sayıda WARNING var ({warnings}).",
                detail="Uyarı yoğunluğu yüksek.",
                suggestion="Tekrarlayan uyarıların kaynağını giderin.",
                metadata={"warning_count": warnings},
            )
        return self.ok(
            f"Log uyarı sayısı makul ({warnings}).",
            detail=f"{len(files)} log dosyası tarandı.",
            metadata={"warning_count": warnings},
        )


class LastErrorSnapshotCheck(_LogCheck):
    name = "Son hata anlık görüntüsü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        files = self._log_files(context)
        if not files:
            return self.info(
                "Log dosyası yok; son hata gösterilemiyor.",
                detail="logs/*.log bulunamadı.",
                suggestion="Loglama etkinleştirin.",
            )
        last_error = None
        for log_file in files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as fh:
                    tail = deque(fh, maxlen=500)
                for line in reversed(tail):
                    if " ERROR " in line or " CRITICAL " in line:
                        last_error = line.strip()[:300]
                        break
            except Exception:  # noqa: BLE001
                continue
            if last_error:
                break
        if not last_error:
            return self.ok(
                "Son loglarda hata yok.",
                detail="ERROR/CRITICAL satırı bulunamadı.",
            )
        return self.info(
            "Son kaydedilen hata gösteriliyor.",
            detail=last_error,
            suggestion="Hata tekrar ediyorsa kök nedeni giderin.",
        )

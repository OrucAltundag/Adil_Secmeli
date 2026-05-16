# -*- coding: utf-8 -*-
"""Test paketi sağlık kontrolleri (testleri ÇALIŞTIRMAZ; yalnızca varlık/araç)."""

from __future__ import annotations

import importlib.util

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _TestSuiteCheck(BaseHealthCheck):
    category = "Test Paketi"
    score_bucket = "ops"


class TestDirectoryCheck(_TestSuiteCheck):
    name = "Test klasörü kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        root = context.root
        candidates = [root / "app" / "tests", root / "tests"]
        existing = [p for p in candidates if p.is_dir()]
        if not existing:
            return self.warning(
                "Test klasörü bulunamadı.",
                detail="app/tests veya tests yok.",
                suggestion="Test paketini ekleyin.",
            )
        test_files = []
        for p in existing:
            test_files += list(p.rglob("test_*.py"))
        return self.ok(
            f"Test paketi mevcut ({len(test_files)} test dosyası).",
            detail="Klasörler: "
            + ", ".join(str(p.relative_to(root).as_posix()) for p in existing),
            metadata={"test_files": len(test_files)},
        )


class TestRunnerScriptCheck(_TestSuiteCheck):
    name = "Test çalıştırıcı script kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        script = context.root / "scripts" / "run_tests.py"
        if not script.exists():
            return self.info(
                "scripts/run_tests.py bulunamadı.",
                detail=str(script),
                suggestion="Toplu test çalıştırma scripti opsiyoneldir.",
            )
        return self.ok(
            "Test çalıştırıcı script mevcut.",
            detail=str(script),
        )


class PytestAvailabilityCheck(_TestSuiteCheck):
    name = "pytest erişilebilirlik kontrolü"
    quick = True
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        if importlib.util.find_spec("pytest") is None:
            return self.info(
                "pytest yüklü değil.",
                detail="pytest modülü bulunamadı.",
                suggestion="Test çalıştırmak için 'pip install pytest' kurun.",
            )
        markers_file = None
        for name in ("pytest.ini", "pyproject.toml", "setup.cfg"):
            if (context.root / name).exists():
                markers_file = name
                break
        return self.ok(
            "pytest erişilebilir.",
            detail=f"pytest mevcut; yapılandırma: {markers_file or 'varsayılan'}",
            suggestion="Testleri 'python -m pytest app/tests' ile çalıştırın.",
        )

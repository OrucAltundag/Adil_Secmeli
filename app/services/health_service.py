# -*- coding: utf-8 -*-
"""Sağlık merkezi backend servisi (UI ve API için tek giriş noktası).

UI doğrudan health_runner'a değil bu servise bağlanır. Son rapor
hafızada tutulur; JSON/TXT olarak dışa aktarılabilir.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from app.core.config import AppConfig, load_app_config
from app.core.permissions import UserContext
from app.core.result import ServiceResult
from app.health.health_formatter import format_algorithm_catalog, format_report
from app.health.health_registry import algorithm_catalog
from app.health.health_runner import HealthRunner
from app.health.models import HealthReport

_LAST_REPORT: HealthReport | None = None
_LOCK = threading.Lock()


class HealthService:
    """Sağlık kontrollerini çalıştırır ve raporu yönetir."""

    def __init__(
        self,
        db_path: str | None = None,
        config: AppConfig | None = None,
        user_context: UserContext | None = None,
    ):
        self.config = config or load_app_config()
        self.db_path = db_path or self.config.sqlite_db_path
        self.user_context = user_context

    def _run(self, mode: str) -> HealthReport:
        global _LAST_REPORT
        runner = HealthRunner(
            db_path=self.db_path,
            config=self.config,
            user_context=self.user_context,
        )
        report = runner.run(mode=mode)
        with _LOCK:
            _LAST_REPORT = report
        return report

    def run_quick_health_check(self) -> HealthReport:
        return self._run("quick")

    def run_full_health_check(self) -> HealthReport:
        return self._run("full")

    def run_auto_repair(self) -> HealthReport:
        """Yalnızca güvenli otomatik düzeltmeleri çalıştırır."""

        return self._run("repair")

    def run_audit_health_check(self) -> HealthReport:
        """Mimari/güvenlik/bağımlılık/log odaklı derin tarama."""

        return self._run("audit")

    def get_last_health_report(self) -> HealthReport | None:
        with _LOCK:
            return _LAST_REPORT

    def list_available_checks(self) -> list[dict[str, Any]]:
        """Kayıtlı tüm kontrolleri (ad/kategori/quick) listeler."""

        from app.health.health_registry import all_checks

        return [
            {
                "name": check.name,
                "category": check.category,
                "source": check.__class__.__name__,
                "quick": getattr(check, "quick", False),
            }
            for check in all_checks()
        ]

    def list_algorithm_catalog(self) -> list[dict[str, Any]]:
        return algorithm_catalog()

    # -- Dışa aktarma ------------------------------------------------------------
    def _resolve_report(self, report: HealthReport | None) -> HealthReport:
        report = report or self.get_last_health_report()
        if report is None:
            report = self.run_full_health_check()
        return report

    def export_health_report_txt(
        self, path: str, report: HealthReport | None = None, *, developer: bool = True
    ) -> ServiceResult:
        report = self._resolve_report(report)
        text = format_report(report, developer=developer)
        text += "\n" + format_algorithm_catalog()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            return ServiceResult.fail(
                "Sağlık raporu TXT olarak yazılamadı.",
                errors=[{"path": path, "error": str(exc)}],
            )
        return ServiceResult.ok({"path": os.path.abspath(path)}, message="TXT rapor kaydedildi.")

    def export_health_report_json(
        self, path: str, report: HealthReport | None = None
    ) -> ServiceResult:
        report = self._resolve_report(report)
        payload: dict[str, Any] = report.to_dict()
        payload["algorithm_catalog"] = algorithm_catalog()
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            return ServiceResult.fail(
                "Sağlık raporu JSON olarak yazılamadı.",
                errors=[{"path": path, "error": str(exc)}],
            )
        return ServiceResult.ok({"path": os.path.abspath(path)}, message="JSON rapor kaydedildi.")

    def get_algorithm_catalog(self) -> list[dict[str, str]]:
        return algorithm_catalog()


# -- Modül düzeyi kolaylık fonksiyonları ----------------------------------------
def run_quick_health_check(
    db_path: str | None = None,
    config: AppConfig | None = None,
    user_context: UserContext | None = None,
) -> HealthReport:
    return HealthService(db_path, config, user_context).run_quick_health_check()


def run_full_health_check(
    db_path: str | None = None,
    config: AppConfig | None = None,
    user_context: UserContext | None = None,
) -> HealthReport:
    return HealthService(db_path, config, user_context).run_full_health_check()


def run_auto_repair(
    db_path: str | None = None,
    config: AppConfig | None = None,
    user_context: UserContext | None = None,
) -> HealthReport:
    return HealthService(db_path, config, user_context).run_auto_repair()


def run_audit_health_check(
    db_path: str | None = None,
    config: AppConfig | None = None,
    user_context: UserContext | None = None,
) -> HealthReport:
    return HealthService(db_path, config, user_context).run_audit_health_check()


def list_available_checks() -> list[dict[str, str]]:
    return HealthService().list_available_checks()


def list_algorithm_catalog() -> list[dict[str, str]]:
    return algorithm_catalog()


def get_last_health_report() -> HealthReport | None:
    with _LOCK:
        return _LAST_REPORT


def export_health_report_txt(path: str, report: HealthReport | None = None) -> ServiceResult:
    return HealthService().export_health_report_txt(path, report)


def export_health_report_json(path: str, report: HealthReport | None = None) -> ServiceResult:
    return HealthService().export_health_report_json(path, report)


def get_algorithm_catalog() -> list[dict[str, str]]:
    return algorithm_catalog()

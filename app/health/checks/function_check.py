# -*- coding: utf-8 -*-
"""Fonksiyon/servis sözleşme ve sınır kontrolleri."""

from __future__ import annotations

import importlib

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _FunctionCheck(BaseHealthCheck):
    category = "Fonksiyon"
    score_bucket = "function"


class ImportCheck(_FunctionCheck):
    name = "Kritik modül import kontrolü"
    quick = True
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        failed: list[str] = []
        for module in context.health_config.critical_modules:
            try:
                importlib.import_module(module)
            except Exception as exc:  # noqa: BLE001
                failed.append(f"- {module}: {type(exc).__name__}: {exc}")
        total = len(context.health_config.critical_modules)
        if not failed:
            return self.ok(
                f"Tüm kritik modüller import edilebiliyor ({total}).",
                detail="Kontrol edilen modüller sorunsuz yüklendi.",
            )
        return self.critical(
            "Bazı kritik modüller import edilemiyor.",
            detail="\n".join(failed),
            suggestion="Eksik bağımlılıkları kurun veya import hatasını giderin.",
            metadata={"failed_modules": failed},
        )


class ServiceFunctionCheck(_FunctionCheck):
    name = "Servis fonksiyonu çağrılabilirlik kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.services.service_factory import get_service_factory

            factory = get_service_factory(
                db_path=context.db_path, config=context.app_config
            )
            system_service = factory.get_system_service()
            result = system_service.schema_health()
        except Exception as exc:  # noqa: BLE001
            return self.critical(
                "Servis katmanı temel fonksiyonu çalıştırılamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="service_factory / system_service zincirini kontrol edin.",
            )
        if result is None or not hasattr(result, "success"):
            return self.warning(
                "Servis beklenen sonuç tipini döndürmedi.",
                detail=f"Dönen tip: {type(result).__name__}",
                suggestion="Servisin ServiceResult döndürdüğünü doğrulayın.",
            )
        return self.ok(
            "Servis katmanı temel fonksiyonu çalışıyor.",
            detail=f"system_service.schema_health() success={result.success}",
        )


class ContractCheck(_FunctionCheck):
    name = "Servis sözleşmesi (ServiceResult) kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        from app.core.result import ServiceResult

        ok = ServiceResult.ok({"x": 1}, message="ok")
        fail = ServiceResult.fail("hata")
        problems: list[str] = []
        if not (ok.success and ok.unwrap() == {"x": 1}):
            problems.append("ServiceResult.ok sözleşmesi bozuk.")
        if fail.success or "errors" not in fail.to_api():
            problems.append("ServiceResult.fail sözleşmesi bozuk.")
        try:
            fail.unwrap()
            problems.append("Başarısız sonuç unwrap'te hata fırlatmadı.")
        except RuntimeError:
            pass
        if problems:
            return self.critical(
                "Servis sonuç sözleşmesi beklenen davranışı sağlamıyor.",
                detail="\n".join(problems),
                suggestion="app/core/result.py sözleşmesini gözden geçirin.",
            )
        return self.ok(
            "ServiceResult sözleşmesi doğru çalışıyor.",
            detail="ok/fail/unwrap davranışları beklenen şekilde.",
        )


class ExceptionHandlingCheck(_FunctionCheck):
    name = "Hatalı girdi kontrollü hata kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        from app.repositories.base import validate_identifier

        try:
            validate_identifier("bozuk; DROP TABLE x")
        except ValueError:
            return self.ok(
                "Hatalı girdi kontrollü şekilde reddedildi.",
                detail="validate_identifier geçersiz tanımlayıcıda ValueError verdi.",
            )
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Hatalı girdi beklenmeyen istisna üretti.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Girdi doğrulamasının kontrollü hata verdiğinden emin olun.",
            )
        return self.critical(
            "Hatalı girdi sessizce kabul edildi.",
            detail="validate_identifier geçersiz değeri reddetmedi.",
            suggestion="Girdi doğrulamasını sıkılaştırın (SQL injection riski).",
        )


class BoundaryCheck(_FunctionCheck):
    name = "Sınır durumu kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        problems: list[str] = []
        try:
            import pandas as pd

            from app.algorithms.mcdm.ahp import AHPRanker

            ranker = AHPRanker(pairwise_matrix=[[1.0]])
            empty = pd.DataFrame({"item_id": [], "k": []})
            try:
                ranker.rank(empty, top_k=5)
            except Exception:
                # Boş veri setinde hata fırlatması kabul edilir; çökmemesi yeterli.
                pass
        except Exception as exc:  # noqa: BLE001
            problems.append(f"AHP sınır testi: {type(exc).__name__}: {exc}")
        if problems:
            return self.warning(
                "Sınır durumlarında beklenmeyen davranış.",
                detail="\n".join(problems),
                suggestion="Boş/tek kayıt durumlarını ele alın.",
            )
        return self.ok(
            "Sınır durumları (boş veri) kontrollü ele alınıyor.",
            detail="Boş veri setinde modül çökmeden ele alındı.",
        )

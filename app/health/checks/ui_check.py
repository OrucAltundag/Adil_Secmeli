# -*- coding: utf-8 -*-
"""UI sağlık kontrolleri (import düzeyinde; Tk penceresi açmaz)."""

from __future__ import annotations

import importlib

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity

EXPECTED_TABS = {
    "SystemHealthPage": "app.ui.tabs.system_health_page",
    "SecurityReadinessPage": "app.ui.tabs.security_readiness_page",
    "DataManagementPage": "app.ui.tabs.data_management_page",
    "DataQualityPage": "app.ui.tabs.data_quality_page",
    "CalcTab": "app.ui.tabs.calc_tab",
    "AHPWeightPage": "app.ui.tabs.ahp_weight_page",
    "DecisionCenterPage": "app.ui.tabs.decision_center_page",
    "SemesterPlanningPage": "app.ui.tabs.semester_planning_page",
    "ToolsTab": "app.ui.tabs.tools_tab",
    "AnalysisTab": "app.ui.tabs.analysis_tab",
    "ViewTab": "app.ui.tabs.view_tab",
}


class _UICheck(BaseHealthCheck):
    category = "UI"
    score_bucket = "architecture"


class TabRegistrationCheck(_UICheck):
    name = "Sekme kayıt kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            main_src = (context.root / "app" / "main.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "app/main.py okunamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Ana uygulama dosyasının varlığını kontrol edin.",
            )
        missing = [
            cls
            for cls in EXPECTED_TABS
            if "self.nb.add(" not in main_src or cls not in main_src
        ]
        if missing:
            return self.warning(
                "Bazı sekmeler ana pencerede kayıtlı görünmüyor.",
                detail="Eksik referans: " + ", ".join(missing),
                suggestion="main.py içinde sekme kayıtlarını doğrulayın.",
                metadata={"missing": missing},
            )
        return self.ok(
            f"Tüm beklenen sekmeler kayıtlı ({len(EXPECTED_TABS)}).",
            detail="main.py içinde sekme sınıfları referanslanıyor.",
        )


class PageLoadCheck(_UICheck):
    name = "Sayfa import kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        failed: list[str] = []
        for cls_name, module in EXPECTED_TABS.items():
            try:
                mod = importlib.import_module(module)
                if not hasattr(mod, cls_name):
                    failed.append(f"- {module}: {cls_name} sınıfı yok")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"- {module}: {type(exc).__name__}: {exc}")
        if failed:
            return self.critical(
                "Bazı sekme sınıfları import edilemiyor.",
                detail="\n".join(failed),
                suggestion="İlgili sayfa modüllerindeki import hatalarını giderin.",
                metadata={"failed": len(failed)},
            )
        return self.ok(
            f"Tüm sekme sınıfları import edilebiliyor ({len(EXPECTED_TABS)}).",
            detail="UI sayfa modülleri sorunsuz yüklendi.",
        )


class WidgetExistenceCheck(_UICheck):
    name = "Sistem Sağlığı widget kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.ui.tabs import system_health_page

            src = (context.root / "app" / "ui" / "tabs" / "system_health_page.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Sistem Sağlığı sayfası incelenemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="system_health_page.py dosyasını kontrol edin.",
            )
        has_class = hasattr(system_health_page, "SystemHealthPage")
        has_button = "Health Check" in src or "Sağlık" in src
        has_output = "Text" in src or "Treeview" in src
        if has_class and has_button and has_output:
            return self.ok(
                "Sistem Sağlığı sayfasında buton ve çıktı alanı mevcut.",
                detail="SystemHealthPage + buton + çıktı widget'ı bulundu.",
            )
        return self.warning(
            "Sistem Sağlığı sayfasında beklenen bileşenler eksik olabilir.",
            detail=f"class={has_class}, button={has_button}, output={has_output}",
            suggestion="Buton ve çıktı alanının tanımlı olduğundan emin olun.",
        )


class EmptyStateCheck(_UICheck):
    name = "Boş durum dayanıklılık kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        # UI'ın boş veri durumunu, veri katmanını boş sorgulayarak dolaylı doğrularız.
        with context.repository() as repo:
            tables = repo.table_names()
            empty = [t for t in tables if repo.row_count(t) == 0]
        return self.info(
            "Boş durum bilgisi çıkarıldı.",
            detail=(
                f"Toplam tablo: {len(tables)}, boş tablo: {len(empty)}. "
                "Sayfalar boş veri uyarısı gösterecek şekilde tasarlanmalıdır."
            ),
            suggestion="Veri yokken sayfaların kullanıcı dostu uyarı verdiğini doğrulayın.",
            metadata={"empty_tables": len(empty)},
        )

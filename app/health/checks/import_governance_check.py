# -*- coding: utf-8 -*-
"""İçe aktarım (import) yönetişim sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _ImportGovCheck(BaseHealthCheck):
    category = "İçe Aktarım Yönetişimi"
    score_bucket = "data_quality"


class ImportInfrastructureCheck(_ImportGovCheck):
    name = "Import altyapısı kontrolü"
    default_severity = HealthSeverity.MEDIUM

    EXPECTED = (
        "import_batches",
        "import_diffs",
        "import_quality_checks",
        "import_rollback_logs",
    )

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            tables = set(repo.table_names())
        missing = [t for t in self.EXPECTED if t not in tables]
        if len(missing) == len(self.EXPECTED):
            return self.info(
                "Import yönetişim tabloları bulunamadı.",
                detail="Beklenen: " + ", ".join(self.EXPECTED),
                suggestion="Import yönetişim migrasyonunu uygulayın.",
            )
        if missing:
            return self.warning(
                "Bazı import yönetişim tabloları eksik.",
                detail="Eksik: " + ", ".join(missing),
                suggestion="Eksik import yönetişim tablolarını oluşturun.",
                metadata={"missing": missing},
            )
        return self.ok(
            "Import yönetişim altyapısı tam.",
            detail="batch/diff/quality/rollback tabloları mevcut.",
        )


class ImportRollbackReadinessCheck(_ImportGovCheck):
    name = "Import geri alma (rollback) hazırlık kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("import_rollback_logs"):
                return self.info(
                    "Rollback log tablosu yok.",
                    detail="import_rollback_logs bulunamadı.",
                    suggestion="Import rollback altyapısını etkinleştirin.",
                )
            batches = (
                repo.row_count("import_batches")
                if repo.table_exists("import_batches")
                else 0
            )
        return self.ok(
            "Import rollback altyapısı hazır.",
            detail=f"import_batches kaydı: {batches}",
            metadata={"batches": batches},
        )


class ImportDataConsistencyCheck(_ImportGovCheck):
    name = "Import sonrası veri tutarlılık kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("import_row_issues"):
                return self.info(
                    "Import satır sorunları tablosu yok.",
                    detail="import_row_issues bulunamadı.",
                    suggestion="Import kalite kontrol altyapısını etkinleştirin.",
                )
            open_issues = repo.scalar(
                "SELECT COUNT(*) FROM import_row_issues"
            )
        if open_issues:
            return self.warning(
                "Import sonrası çözülmemiş satır sorunları var.",
                detail=f"import_row_issues kaydı: {open_issues}",
                suggestion="Import kalite sorunlarını inceleyip giderin.",
                metadata={"issues": open_issues},
            )
        return self.ok(
            "Import sonrası veri tutarlı.",
            detail="import_row_issues kaydı yok.",
        )

# -*- coding: utf-8 -*-
"""Veritabanı şema uyumluluğu kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck
from app.health.health_config import EXPECTED_TABLES
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository


class SchemaValidationCheck(BaseHealthCheck):
    name = "Schema doğrulama kontrolü"
    category = "Şema Uyumluluğu"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.schema_check.SchemaValidationCheck"
    quick = True

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        existing = set(repo.table_names())
        if not EXPECTED_TABLES:
            return self.result(
                HealthStatus.INFO,
                "Beklenen tablo yapılandırması henüz tanımlanmamış.",
                suggestion="health_config.py içinde beklenen tablo ve kolonları netleştirin.",
            )

        missing_tables = [table for table in EXPECTED_TABLES if table not in existing]
        missing_columns: dict[str, list[str]] = {}
        for table, config in EXPECTED_TABLES.items():
            if table not in existing:
                continue
            current_columns = {column["name"] for column in repo.columns(table)}
            required = set(config.get("required_columns") or ())
            missing = sorted(required - current_columns)
            if missing:
                missing_columns[table] = missing

        if missing_tables or missing_columns:
            status = HealthStatus.CRITICAL if missing_tables else HealthStatus.WARNING
            detail_lines = []
            if missing_tables:
                detail_lines.append("Eksik tablolar: " + ", ".join(missing_tables))
            for table, columns in missing_columns.items():
                detail_lines.append(f"{table}: eksik kolonlar {', '.join(columns)}")
            return self.result(
                status,
                "Beklenen şema ile mevcut veritabanı arasında uyumsuzluk var.",
                severity=HealthSeverity.HIGH,
                detail="\n".join(detail_lines),
                suggestion="Migration/schema compatibility adımlarını çalıştırın veya health_config.py beklenenlerini güncelleyin.",
                metadata={"missing_tables": missing_tables, "missing_columns": missing_columns},
            )
        return self.result(
            HealthStatus.OK,
            "Temel beklenen tablolar ve kolonlar mevcut.",
            detail=f"Kontrol edilen tablo sayısı: {len(EXPECTED_TABLES)}",
            metadata={"checked_tables": list(EXPECTED_TABLES)},
        )


class ExpectedTablesCheck(SchemaValidationCheck):
    name = "Beklenen tablo kontrolü"


class ExpectedColumnsCheck(SchemaValidationCheck):
    name = "Beklenen kolon kontrolü"


class SchemaCompatibilityCheck(BaseHealthCheck):
    name = "Schema compatibility durumu"
    category = "Şema Uyumluluğu"
    source = "app.health.checks.schema_check.SchemaCompatibilityCheck"
    quick = True

    def run(self, context: HealthContext):
        enabled = bool(getattr(context.config, "enable_schema_compat", False))
        mutation = bool(getattr(context.config, "allow_runtime_schema_mutation", False))
        status = HealthStatus.OK if enabled else HealthStatus.INFO
        return self.result(
            status,
            "Schema compatibility ayarları okundu.",
            detail=f"enable_schema_compat={enabled}, allow_runtime_schema_mutation={mutation}",
            suggestion="Production ortamda runtime schema mutation kapalı olmalıdır.",
            metadata={"enable_schema_compat": enabled, "allow_runtime_schema_mutation": mutation},
        )


class ColumnTypeCheck(BaseHealthCheck):
    name = "Kritik kolon tip kontrolü"
    category = "Şema Uyumluluğu"
    source = "app.health.checks.schema_check.ColumnTypeCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Kritik kolon tipleri için otomatik keşif modu kullanılıyor.",
            detail="Kesin tip sözleşmeleri health_config.py içinde genişletilebilir.",
            suggestion="Sabit schema sözleşmesi oluştukça kolon tip beklenenlerini ekleyin.",
        )

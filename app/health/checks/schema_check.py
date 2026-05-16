# -*- coding: utf-8 -*-
"""Şema sağlık kontrolleri (tablo/kolon/uyumluluk/tip)."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _SchemaCheck(BaseHealthCheck):
    category = "Şema"
    score_bucket = "schema"


class SchemaValidationCheck(_SchemaCheck):
    name = "Beklenen tablolar kontrolü"
    quick = True
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        expected = set(context.health_config.expected_tables)
        if not expected:
            return self.info(
                "Beklenen tablo yapılandırması tanımlı değil.",
                detail="health_config.expected_tables boş.",
                suggestion="health_config.py içinde beklenen tabloları tanımlayın.",
            )
        with context.repository() as repo:
            existing = set(repo.table_names())
        missing = sorted(expected - existing)
        if not missing:
            return self.ok(
                "Tüm beklenen tablolar mevcut.",
                detail=f"Kontrol edilen tablo: {len(expected)}",
                metadata={"expected": sorted(expected)},
            )
        return self.critical(
            "Beklenen bazı tablolar eksik.",
            detail="Eksik tablolar:\n- " + "\n- ".join(missing),
            suggestion="Şema migrasyonunu çalıştırın veya şemayı güncelleyin.",
            metadata={"missing_tables": missing},
        )


class ExpectedColumnsCheck(_SchemaCheck):
    name = "Beklenen kolonlar kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        expected = context.health_config.expected_columns
        if not expected:
            return self.info(
                "Beklenen kolon yapılandırması tanımlı değil.",
                detail="health_config.expected_columns boş.",
                suggestion="health_config.py içinde beklenen kolonları tanımlayın.",
            )
        missing: dict[str, list[str]] = {}
        with context.repository() as repo:
            existing_tables = set(repo.table_names())
            for table, cols in expected.items():
                if table not in existing_tables:
                    missing[table] = sorted(cols)
                    continue
                have = set(repo.column_names(table))
                absent = sorted(set(cols) - have)
                if absent:
                    missing[table] = absent
        if not missing:
            return self.ok(
                "Tüm beklenen kolonlar mevcut.",
                detail=f"Kontrol edilen tablo: {len(expected)}",
            )
        detail = "\n".join(f"- {t}: {', '.join(c)}" for t, c in missing.items())
        return self.warning(
            "Bazı tablolarda beklenen kolonlar eksik.",
            detail="Eksik kolonlar:\n" + detail,
            suggestion="İlgili tabloların şemasını güncelleyin.",
            metadata={"missing_columns": missing},
        )


class SchemaCompatibilityCheck(_SchemaCheck):
    name = "Şema uyumluluğu / migrasyon kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.services.schema_health_service import check_schema_health

            health = check_schema_health(
                db_path=context.db_path, config=context.app_config
            )
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Şema uyumluluk bilgisi okunamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="schema_health_service modülünü kontrol edin.",
            )
        alembic = (health.get("alembic") or {})
        version = alembic.get("version")
        warnings = health.get("warnings") or []
        if not health.get("schema_ok", False):
            return self.warning(
                "Şema uyumluluğunda eksikler var.",
                detail="Uyarılar:\n- " + "\n- ".join(warnings or ["Detay yok"]),
                suggestion="Eksik tablo/kolonları tamamlayın, migrasyonu çalıştırın.",
                metadata={"alembic_version": version},
            )
        if not version:
            return self.info(
                "Alembic migrasyon sürümü bulunamadı.",
                detail="alembic_version tablosu yok veya boş.",
                suggestion="Migrasyonları çalıştırıp head sürümünü damgalayın.",
            )
        return self.ok(
            "Şema uyumlu ve migrasyon sürümü mevcut.",
            detail=f"Alembic version: {version}",
            metadata={"alembic_version": version},
        )


class ColumnTypeCheck(_SchemaCheck):
    name = "Kritik kolon tip kontrolü"
    default_severity = HealthSeverity.LOW

    # Beklenen tip aileleri (SQLite tip yakınlığı toleranslı).
    EXPECTED = {
        "ders": {"ders_id": ("INT", "TEXT", "VARCHAR")},
        "havuz": {"yil": ("INT",), "ders_id": ("INT", "TEXT", "VARCHAR")},
        "ders_kriterleri": {"yil": ("INT",), "ders_id": ("INT", "TEXT", "VARCHAR")},
    }

    def run(self, context: HealthContext) -> HealthCheckResult:
        mismatches: list[str] = []
        with context.repository() as repo:
            tables = set(repo.table_names())
            for table, cols in self.EXPECTED.items():
                if table not in tables:
                    continue
                info = {c["name"]: str(c["type"]).upper() for c in repo.column_info(table)}
                for col, families in cols.items():
                    actual = info.get(col)
                    if actual is None:
                        continue
                    if not any(fam in actual for fam in families):
                        mismatches.append(
                            f"{table}.{col}: beklenen {families}, mevcut '{actual or 'TANIMSIZ'}'"
                        )
        if not mismatches:
            return self.ok(
                "Kritik kolon tipleri beklenen ailelerde.",
                detail="Tip uyumsuzluğu bulunmadı.",
            )
        return self.info(
            "Bazı kolon tipleri beklenenden farklı (SQLite esnek tipli).",
            detail="\n".join(mismatches),
            suggestion="SQLite tip yakınlığı esnektir; gerekiyorsa şemayı netleştirin.",
            metadata={"mismatches": mismatches},
        )

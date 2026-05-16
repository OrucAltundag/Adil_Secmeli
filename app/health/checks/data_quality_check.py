# -*- coding: utf-8 -*-
"""Veri kalitesi kontrolleri (eksik, tekrar, aralık, yetim, profil, aykırı)."""

from __future__ import annotations

import statistics

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _DataQualityCheck(BaseHealthCheck):
    category = "Veri Kalitesi"
    score_bucket = "data_quality"


class MissingValueCheck(_DataQualityCheck):
    name = "Eksik / boş değer kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        rules = context.health_config.critical_not_null
        problems: list[str] = []
        total_missing = 0
        with context.repository() as repo:
            tables = set(repo.table_names())
            for table, columns in rules.items():
                if table not in tables:
                    continue
                have = set(repo.column_names(table))
                for col in columns:
                    if col not in have:
                        continue
                    nulls = repo.null_count(table, col)
                    if nulls:
                        total_missing += nulls
                        problems.append(f"- {table}.{col}: {nulls} boş kayıt")
        if not problems:
            return self.ok(
                "Kritik alanlarda eksik değer bulunmadı.",
                detail="Tanımlı zorunlu kolonlar dolu.",
            )
        sev = self.critical if total_missing > 100 else self.warning
        return sev(
            "Bazı zorunlu alanlarda eksik veri var.",
            detail="\n".join(problems),
            suggestion="Eksik zorunlu alanları tamamlayın veya kaydı düzeltin.",
            metadata={"total_missing": total_missing},
        )


class DuplicateRecordCheck(_DataQualityCheck):
    name = "Tekrarlı kayıt kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        rules = context.health_config.duplicate_keys
        problems: list[str] = []
        with context.repository() as repo:
            tables = set(repo.table_names())
            for table, keys in rules.items():
                if table not in tables:
                    continue
                have = set(repo.column_names(table))
                if not set(keys).issubset(have):
                    continue
                dups = repo.duplicate_groups(table, keys)
                if dups:
                    problems.append(
                        f"- {table} ({', '.join(keys)}): {dups} tekrarlı grup"
                    )
        if not problems:
            return self.ok(
                "Aynı anahtarda tekrarlı kayıt bulunmadı.",
                detail="Ders/dönem/yıl bazlı tekrarlar kontrol edildi.",
            )
        return self.warning(
            "Tekrarlı kayıtlar tespit edildi.",
            detail="\n".join(problems),
            suggestion="Tekrarlı kayıtları birleştirin veya benzersiz kısıt ekleyin.",
            metadata={"groups": problems},
        )


class RangeValidationCheck(_DataQualityCheck):
    name = "Değer aralığı kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        rules = context.health_config.non_negative_columns
        problems: list[str] = []
        with context.repository() as repo:
            tables = set(repo.table_names())
            for table, columns in rules.items():
                if table not in tables:
                    continue
                have = set(repo.column_names(table))
                for col in columns:
                    if col not in have:
                        continue
                    neg = repo.negative_count(table, col)
                    if neg:
                        problems.append(f"- {table}.{col}: {neg} negatif değer")
        if not problems:
            return self.ok(
                "Sayısal alanlarda mantıksız negatif değer yok.",
                detail="Kredi/kontenjan/öğrenci sayıları negatif değil.",
            )
        return self.warning(
            "Bazı sayısal alanlarda negatif değer var.",
            detail="\n".join(problems),
            suggestion="Negatif kredi/kontenjan/oran değerlerini düzeltin.",
            metadata={"problems": problems},
        )


class OrphanRecordCheck(_DataQualityCheck):
    name = "Yetim kayıt kontrolü"
    default_severity = HealthSeverity.MEDIUM

    # (çocuk_tablo, çocuk_kolon) -> (ebeveyn_tablo, ebeveyn_kolon)
    RELATIONS = [
        ("havuz", "ders_id", "ders", "ders_id"),
        ("ders_kriterleri", "ders_id", "ders", "ders_id"),
        ("ders", "bolum_id", "bolum", "bolum_id"),
    ]

    def run(self, context: HealthContext) -> HealthCheckResult:
        problems: list[str] = []
        with context.repository() as repo:
            tables = set(repo.table_names())
            for child, ckey, parent, pkey in self.RELATIONS:
                if child not in tables or parent not in tables:
                    continue
                if ckey not in set(repo.column_names(child)):
                    continue
                if pkey not in set(repo.column_names(parent)):
                    continue
                orphans = repo.scalar(
                    f"SELECT COUNT(*) FROM {child} c "
                    f"WHERE c.{ckey} IS NOT NULL AND NOT EXISTS "
                    f"(SELECT 1 FROM {parent} p WHERE p.{pkey} = c.{ckey})"
                )
                if orphans:
                    problems.append(
                        f"- {child}.{ckey} -> {parent}.{pkey}: {orphans} yetim kayıt"
                    )
        if not problems:
            return self.ok(
                "Kimlik ilişkilerinde yetim kayıt bulunmadı.",
                detail="ders/havuz/ders_kriterleri ilişkileri tutarlı.",
            )
        return self.warning(
            "İlişkilerde yetim kayıtlar var.",
            detail="\n".join(problems),
            suggestion="Eşleşmeyen kayıtları temizleyin veya eksik ana kaydı ekleyin.",
            metadata={"problems": problems},
        )


class DataProfilingCheck(_DataQualityCheck):
    name = "Veri profili özeti"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        lines: list[str] = []
        empty_tables: list[str] = []
        with context.repository() as repo:
            tables = set(repo.table_names())
            for table in context.health_config.profiling_tables:
                if table not in tables:
                    continue
                count = repo.row_count(table)
                cols = repo.column_names(table)
                lines.append(f"- {table}: {count} kayıt, {len(cols)} kolon")
                if count == 0:
                    empty_tables.append(table)
        if not lines:
            return self.info(
                "Profil çıkarılacak tablo bulunamadı.",
                detail="health_config.profiling_tables ile eşleşen tablo yok.",
            )
        detail = "Tablo profili:\n" + "\n".join(lines)
        if empty_tables:
            return self.warning(
                f"Bazı çekirdek tablolar boş ({len(empty_tables)}).",
                detail=detail + "\nBoş tablolar: " + ", ".join(empty_tables),
                suggestion="Boş çekirdek tablolar için veri import edin.",
                metadata={"empty_tables": empty_tables},
            )
        return self.ok(
            "Veri profili çıkarıldı.",
            detail=detail,
            suggestion="Bilgilendirme amaçlıdır.",
        )


class OutlierDetectionCheck(_DataQualityCheck):
    name = "Aykırı değer (IQR) kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        findings: list[str] = []
        with context.repository() as repo:
            tables = set(repo.table_names())
            for table, columns in context.health_config.outlier_targets.items():
                if table not in tables:
                    continue
                have = set(repo.column_names(table))
                for col in columns:
                    if col not in have:
                        continue
                    values = repo.numeric_values(table, col)
                    if len(values) < 8:
                        continue
                    values_sorted = sorted(values)
                    q1 = statistics.quantiles(values_sorted, n=4)[0]
                    q3 = statistics.quantiles(values_sorted, n=4)[2]
                    iqr = q3 - q1
                    if iqr <= 0:
                        continue
                    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                    outliers = [v for v in values if v < low or v > high]
                    if outliers:
                        findings.append(
                            f"- {table}.{col}: {len(outliers)} aykırı "
                            f"(aralık {low:.1f}–{high:.1f})"
                        )
        if not findings:
            return self.ok(
                "Belirgin aykırı değer tespit edilmedi.",
                detail="IQR yöntemiyle sayısal kolonlar tarandı.",
            )
        return self.warning(
            "Sayısal kolonlarda aykırı değerler var.",
            detail="\n".join(findings),
            suggestion="Aykırı değerleri inceleyin; veri girişi hatası olabilir.",
            metadata={"findings": findings},
        )

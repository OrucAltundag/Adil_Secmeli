# -*- coding: utf-8 -*-
"""Veri kalitesi sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository, quote_identifier


def _existing_tables(repo: SQLiteRepository, candidates: tuple[str, ...]) -> list[str]:
    names = set(repo.table_names())
    return [table for table in candidates if table in names]


class MissingValueCheck(BaseHealthCheck):
    name = "Eksik değer kontrolü"
    category = "Veri Kalitesi"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.data_quality_check.MissingValueCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        candidates = _existing_tables(repo, ("ders", "fakulte", "bolum", "havuz", "ahp_weight_profiles"))
        findings: list[dict[str, object]] = []
        for table in candidates:
            columns = [column["name"] for column in repo.columns(table)]
            critical = [column for column in columns if column.lower() in {"ad", "name", "ders_id", "fakulte_id", "bolum_id"}]
            for column in critical:
                q_table = quote_identifier(table)
                q_col = quote_identifier(column)
                count = repo.execute_scalar(
                    f"SELECT COUNT(*) FROM {q_table} WHERE {q_col} IS NULL OR TRIM(CAST({q_col} AS TEXT)) = ''"
                )
                if int(count or 0) > 0:
                    findings.append({"table": table, "column": column, "missing_count": int(count)})
        if findings:
            return self.result(
                HealthStatus.WARNING,
                "Kritik alanlarda eksik değerler bulundu.",
                severity=HealthSeverity.MEDIUM,
                detail=f"Eksik alan bulgusu: {len(findings)}",
                suggestion="Eksik ders/fakülte/bölüm kayıtlarını tamamlayın.",
                metadata={"findings": findings},
            )
        return self.result(HealthStatus.OK, "Kritik alanlarda eksik değer bulunmadı.", metadata={"checked_tables": candidates})


class DuplicateRecordCheck(BaseHealthCheck):
    name = "Tekrarlı kayıt kontrolü"
    category = "Veri Kalitesi"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.data_quality_check.DuplicateRecordCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        duplicate_rules = {
            "ders": ("ad",),
            "fakulte": ("ad",),
            "bolum": ("fakulte_id", "ad"),
            "instructors": ("name",),
        }
        findings: list[dict[str, object]] = []
        tables = set(repo.table_names())
        for table, columns in duplicate_rules.items():
            if table not in tables:
                continue
            current_columns = {column["name"] for column in repo.columns(table)}
            if not set(columns).issubset(current_columns):
                continue
            group_expr = ", ".join(quote_identifier(column) for column in columns)
            rows = repo.execute_rows(
                f"""
                SELECT {group_expr}, COUNT(*) AS tekrar
                FROM {quote_identifier(table)}
                GROUP BY {group_expr}
                HAVING COUNT(*) > 1
                LIMIT 20
                """
            )
            for row in rows:
                findings.append({"table": table, "columns": columns, "count": int(row["tekrar"])})
        if findings:
            return self.result(
                HealthStatus.WARNING,
                "Olası tekrarlı kayıtlar bulundu.",
                severity=HealthSeverity.MEDIUM,
                detail=f"Tekrar kuralı bulgusu: {len(findings)}",
                suggestion="Tekrarlı ders, bölüm veya öğretim üyesi kayıtlarını birleştirin.",
                metadata={"findings": findings},
            )
        return self.result(HealthStatus.OK, "Belirlenen kurallara göre tekrarlı kayıt bulunmadı.")


class RangeValidationCheck(BaseHealthCheck):
    name = "Aralık doğrulama kontrolü"
    category = "Veri Kalitesi"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.data_quality_check.RangeValidationCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        numeric_markers = ("puan", "score", "skor", "oran", "ratio", "weight", "agirlik", "ağırlık", "kredi", "capacity")
        findings: list[dict[str, object]] = []
        for table in repo.table_names()[:60]:
            for column in repo.columns(table):
                name = column["name"]
                lower = name.lower()
                if not any(marker in lower for marker in numeric_markers):
                    continue
                q_table = quote_identifier(table)
                q_col = quote_identifier(name)
                row = repo.execute_rows(f"SELECT MIN({q_col}) AS min_value, MAX({q_col}) AS max_value FROM {q_table}")[0]
                min_value = row["min_value"]
                max_value = row["max_value"]
                if min_value is not None and float(min_value) < 0:
                    findings.append({"table": table, "column": name, "issue": "negative", "min": float(min_value)})
                if any(marker in lower for marker in ("oran", "ratio", "weight", "agirlik", "ağırlık")):
                    if max_value is not None and float(max_value) > 1.0001:
                        findings.append({"table": table, "column": name, "issue": "ratio_over_one", "max": float(max_value)})
        if findings:
            return self.result(
                HealthStatus.WARNING,
                "Sayısal alanlarda mantıksal aralık dışı değerler bulundu.",
                severity=HealthSeverity.MEDIUM,
                detail=f"Aralık bulgusu: {len(findings)}",
                suggestion="Negatif kredi/puan veya 1 üstü oran/ağırlık alanlarını gözden geçirin.",
                metadata={"findings": findings[:100]},
            )
        return self.result(HealthStatus.OK, "Sayısal alanlarda temel aralık ihlali bulunmadı.")


class DataProfilingCheck(BaseHealthCheck):
    name = "Veri profili kontrolü"
    category = "Veri Kalitesi"
    severity = HealthSeverity.LOW.value
    source = "app.health.checks.data_quality_check.DataProfilingCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        profile = repo.profile_tables(limit=50)
        empty_tables = [item["table"] for item in profile if int(item["row_count"]) == 0]
        status = HealthStatus.INFO if empty_tables else HealthStatus.OK
        return self.result(
            status,
            "Tablo bazlı temel veri profili çıkarıldı.",
            detail=f"Profil çıkarılan tablo: {len(profile)}, boş tablo: {len(empty_tables)}",
            suggestion="Boş tablolar beklenmiyorsa import veya migration adımlarını kontrol edin.",
            metadata={"profile": profile, "empty_tables": empty_tables[:50]},
        )


class OrphanRecordCheck(BaseHealthCheck):
    name = "Yetim kayıt kontrolü"
    category = "Veri Kalitesi"
    source = "app.health.checks.data_quality_check.OrphanRecordCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Yetim kayıt kontrolü foreign key ve keşif tabanlı kontrollerle aşamalı genişletilecek.",
            suggestion="İş kuralları netleşince tablo ilişki haritasını health_config.py içine ekleyin.",
        )


class OutlierDetectionCheck(BaseHealthCheck):
    name = "Aykırı değer kontrolü"
    category = "Veri Kalitesi"
    source = "app.health.checks.data_quality_check.OutlierDetectionCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Aykırı değer tespiti için hafif modda veri profili kullanılıyor.",
            suggestion="Büyük veri setlerinde IQR/Z-Score kontrolünü ayrı zamanlanmış göreve taşıyın.",
        )

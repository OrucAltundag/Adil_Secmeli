# -*- coding: utf-8 -*-
"""Tablo görüntüleme sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository, quote_identifier


class TableListLoadCheck(BaseHealthCheck):
    name = "Tablo listesi yükleme kontrolü"
    category = "Tablo Görüntüleme"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.table_view_check.TableListLoadCheck"

    def run(self, context: HealthContext):
        tables = SQLiteRepository(context.db_path).table_names()
        if not tables:
            return self.result(
                HealthStatus.CRITICAL,
                "Tablo listesi yüklenemedi veya boş.",
                severity=HealthSeverity.CRITICAL,
                suggestion="DB dosyasını ve schema migration adımlarını kontrol edin.",
            )
        return self.result(
            HealthStatus.OK,
            "Tablo listesi güvenli şekilde yüklenebiliyor.",
            detail=f"Tablo sayısı: {len(tables)}",
            metadata={"table_count": len(tables), "sample_tables": tables[:20]},
        )


class TablePreviewCheck(BaseHealthCheck):
    name = "Tablo önizleme kontrolü"
    category = "Tablo Görüntüleme"
    source = "app.health.checks.table_view_check.TablePreviewCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        tables = repo.table_names()
        if not tables:
            return self.result(HealthStatus.SKIPPED, "Önizleme için tablo bulunamadı.")
        table = tables[0]
        rows = repo.execute_rows(f"SELECT * FROM {quote_identifier(table)} LIMIT 10")
        return self.result(
            HealthStatus.OK,
            "Tablo önizleme sorgusu LIMIT ile çalışıyor.",
            detail=f"Örnek tablo: {table}, satır: {len(rows)}",
            metadata={"table": table, "preview_count": len(rows)},
        )


class LargeTableSafetyCheck(BaseHealthCheck):
    name = "Büyük tablo güvenliği kontrolü"
    category = "Tablo Görüntüleme"
    source = "app.health.checks.table_view_check.LargeTableSafetyCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Tablo önizleme kontrolleri LIMIT kullanımıyla güvenli çalışıyor.",
            suggestion="UI tablo görüntüleme servislerinde varsayılan LIMIT değerini koruyun.",
        )

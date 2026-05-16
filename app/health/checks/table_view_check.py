# -*- coding: utf-8 -*-
"""Tablo görüntüleme sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _TableViewCheck(BaseHealthCheck):
    category = "Tablo Görüntüleme"
    score_bucket = "reporting_analytics"


class TableListLoadCheck(_TableViewCheck):
    name = "Tablo listesi yükleme kontrolü"
    quick = True
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            tables = repo.table_names()
        if not tables:
            return self.warning(
                "Hiç tablo listelenemedi.",
                detail="sqlite_master kullanıcı tablosu döndürmedi.",
                suggestion="Veritabanı bağlantısını ve şemayı kontrol edin.",
            )
        return self.ok(
            f"Tablolar listelenebiliyor ({len(tables)} tablo).",
            detail="İlk tablolar: " + ", ".join(tables[:8]),
            metadata={"table_count": len(tables)},
        )


class TablePreviewCheck(_TableViewCheck):
    name = "Tablo önizleme kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        limit = context.health_config.table_preview_limit
        with context.repository() as repo:
            tables = repo.table_names()
            target = next((t for t in ("ders", "havuz") if t in tables), None)
            if target is None and tables:
                target = tables[0]
            if not target:
                return self.info(
                    "Önizlenecek tablo yok.",
                    detail="Veritabanında kullanıcı tablosu bulunamadı.",
                    suggestion="Şema migrasyonunu çalıştırın.",
                )
            cols, rows = repo.preview(target, limit=limit)
        return self.ok(
            f"'{target}' tablosu güvenle önizlenebiliyor.",
            detail=f"İlk {len(rows)} kayıt (LIMIT {limit}), {len(cols)} kolon.",
            metadata={"table": target, "previewed_rows": len(rows)},
        )


class LargeTableSafetyCheck(_TableViewCheck):
    name = "Büyük tablo güvenliği (LIMIT) kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        limit = context.health_config.large_table_row_limit
        big: list[str] = []
        with context.repository() as repo:
            for table in repo.table_names():
                try:
                    count = repo.row_count(table)
                except Exception:  # noqa: BLE001
                    continue
                if count > limit:
                    big.append(f"- {table}: {count} kayıt")
        if not big:
            return self.ok(
                "Büyük tablo bulunmadı; LIMIT kullanımı güvenli.",
                detail=f"Eşik: {limit} kayıt",
            )
        return self.info(
            f"Büyük tablolar var ({len(big)}); önizlemede LIMIT şart.",
            detail="\n".join(big[:15]),
            suggestion="Tablo görüntülemede daima LIMIT/sayfalama kullanın.",
            metadata={"large_tables": len(big)},
        )

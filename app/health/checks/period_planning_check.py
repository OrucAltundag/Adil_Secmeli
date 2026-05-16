# -*- coding: utf-8 -*-
"""Dönem planlama sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _PeriodCheck(BaseHealthCheck):
    category = "Dönem Planlama"
    score_bucket = "ahp_decision"


class PeriodDataAvailabilityCheck(_PeriodCheck):
    name = "Dönem verisi mevcudiyeti kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("ders_kriterleri"):
                return self.info(
                    "Dönem verisi tablosu bulunamadı.",
                    detail="ders_kriterleri tablosu yok.",
                    suggestion="Müfredat/kriter verisini import edin.",
                )
            cols = set(repo.column_names("ders_kriterleri"))
            if "donem" not in cols:
                return self.info(
                    "Dönem kolonu bulunamadı.",
                    detail="ders_kriterleri.donem yok.",
                    suggestion="Şema uyumluluğunu çalıştırın.",
                )
            distinct = repo.scalar(
                "SELECT COUNT(DISTINCT donem) FROM ders_kriterleri WHERE donem IS NOT NULL"
            )
        if not distinct:
            return self.warning(
                "Tanımlı dönem verisi yok.",
                detail="ders_kriterleri içinde dönem değeri bulunamadı.",
                suggestion="Dönem bilgisini içeren veri import edin.",
            )
        return self.ok(
            f"Dönem verisi mevcut ({distinct} farklı dönem).",
            detail=f"Benzersiz dönem sayısı: {distinct}",
            metadata={"distinct_periods": distinct},
        )


class CoursePeriodMappingCheck(_PeriodCheck):
    name = "Ders-dönem eşleşmesi kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("ders_kriterleri") or not repo.table_exists(
                "ders"
            ):
                return self.info(
                    "Eşleşme için gerekli tablolar yok.",
                    detail="ders ve/veya ders_kriterleri eksik.",
                    suggestion="Çekirdek tabloları oluşturun.",
                )
            unmatched = repo.scalar(
                "SELECT COUNT(*) FROM ders_kriterleri k "
                "WHERE k.ders_id IS NOT NULL AND NOT EXISTS "
                "(SELECT 1 FROM ders d WHERE d.ders_id = k.ders_id)"
            )
        if unmatched:
            return self.warning(
                "Ders-dönem eşleşmelerinde tutarsızlık var.",
                detail=f"{unmatched} kriter kaydı bir derse bağlı değil.",
                suggestion="Eşleşmeyen kriter kayıtlarını ilgili derslere bağlayın.",
                metadata={"unmatched": unmatched},
            )
        return self.ok(
            "Ders-dönem eşleşmeleri tutarlı.",
            detail="Tüm kriter kayıtları geçerli bir derse bağlı.",
        )


class CapacityConflictCheck(_PeriodCheck):
    name = "Kapasite/yük çakışması kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("ders_kriterleri"):
                return self.info(
                    "Kapasite kontrolü için veri yok.",
                    detail="ders_kriterleri tablosu yok.",
                    suggestion="Kontenjan/öğrenci verisini import edin.",
                )
            cols = set(repo.column_names("ders_kriterleri"))
            if not {"kontenjan", "kayitli_ogrenci"}.issubset(cols):
                return self.info(
                    "Kapasite kolonları eksik.",
                    detail="kontenjan/kayitli_ogrenci kolonları yok.",
                    suggestion="Şemayı güncelleyin.",
                )
            over = repo.scalar(
                "SELECT COUNT(*) FROM ders_kriterleri "
                "WHERE kontenjan IS NOT NULL AND kayitli_ogrenci IS NOT NULL "
                "AND CAST(kayitli_ogrenci AS REAL) > CAST(kontenjan AS REAL)"
            )
        if over:
            return self.warning(
                "Kapasite aşımı olan kayıtlar var.",
                detail=f"{over} kayıtta kayıtlı öğrenci > kontenjan.",
                suggestion="Kontenjan/kayıt verisini gözden geçirin.",
                metadata={"over_capacity": over},
            )
        return self.ok(
            "Kapasite çakışması bulunmadı.",
            detail="Kayıtlı öğrenci sayıları kontenjanı aşmıyor.",
        )


class PlanningRuleCheck(_PeriodCheck):
    name = "Planlama kuralı kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            tables = set(repo.table_names())
            has_runs = "semester_plan_runs" in tables
            has_policies = "semester_planning_policies" in tables
        if not has_runs and not has_policies:
            return self.info(
                "Dönem planlama altyapısı henüz kullanılmamış.",
                detail="semester_plan_runs / semester_planning_policies yok veya boş.",
                suggestion="Dönem Planlama sekmesinden bir plan çalıştırın.",
            )
        return self.ok(
            "Temel planlama altyapısı mevcut.",
            detail=f"plan_runs={has_runs}, policies={has_policies}",
        )

# -*- coding: utf-8 -*-
"""Havuz (ders) yaşam döngüsü / state machine sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _PoolCheck(BaseHealthCheck):
    category = "Havuz Yaşam Döngüsü"
    score_bucket = "ahp_topsis_decision"


class PoolStateMachineCheck(_PoolCheck):
    name = "Havuz state machine kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.services import pool_state_machine_service  # noqa: F401

            available = True
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Havuz state machine servisi import edilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="pool_state_machine_service modülünü kontrol edin.",
            )
        with context.repository() as repo:
            has_transitions = repo.table_exists("course_state_transitions")
        if available and has_transitions:
            return self.ok(
                "Havuz state machine altyapısı mevcut.",
                detail="pool_state_machine_service + course_state_transitions hazır.",
            )
        return self.info(
            "State machine altyapısı kısmen mevcut.",
            detail=f"servis={available}, transitions_tablosu={has_transitions}",
            suggestion="State geçiş tablolarını oluşturun.",
        )


class PoolStatusValidityCheck(_PoolCheck):
    name = "Havuz statü geçerlilik kontrolü"
    default_severity = HealthSeverity.MEDIUM

    # Bilinen mantıksal statü kümesi (0..n) — esnek; yalnızca tip/None denetimi.
    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("havuz") or "statu" not in set(
                repo.column_names("havuz")
            ):
                return self.info(
                    "Havuz statü kolonu bulunamadı.",
                    detail="havuz.statu mevcut değil.",
                    suggestion="Havuz şemasını kontrol edin.",
                )
            null_statu = repo.scalar(
                "SELECT COUNT(*) FROM havuz WHERE statu IS NULL"
            )
            total = repo.row_count("havuz")
            distinct = repo.fetchall(
                "SELECT DISTINCT statu FROM havuz LIMIT 20"
            )
        if total and null_statu:
            return self.warning(
                "Bazı havuz kayıtlarında statü boş.",
                detail=f"{null_statu}/{total} kayıtta statu NULL",
                suggestion="Eksik statü değerlerini state machine ile doldurun.",
                metadata={"null_statu": null_statu},
            )
        return self.ok(
            "Havuz statüleri geçerli.",
            detail=f"toplam={total}, farklı statü={[d[0] for d in distinct]}",
            metadata={"total": total},
        )


class PoolTransitionConsistencyCheck(_PoolCheck):
    name = "Havuz geçiş tutarlılık kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("course_state_transitions"):
                return self.info(
                    "Geçiş kaydı tablosu yok.",
                    detail="course_state_transitions bulunamadı.",
                    suggestion="State geçişleri kaydedildiğinde oluşur.",
                )
            total = repo.row_count("course_state_transitions")
        return self.ok(
            f"Havuz geçiş kayıtları tutarlı ({total}).",
            detail="course_state_transitions erişilebilir.",
            metadata={"transitions": total},
        )

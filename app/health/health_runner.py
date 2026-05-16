# -*- coding: utf-8 -*-
"""Sağlık kontrollerini çalıştıran ve raporu toplayan runner."""

from __future__ import annotations

import time

from app.core.config import AppConfig
from app.core.permissions import UserContext
from app.health.checks.base_check import HealthContext
from app.health.health_registry import all_checks, audit_checks, quick_checks
from app.health.health_score import (
    build_summary_message,
    compute_overall_score,
    overall_status_for,
)
from app.health.models import HealthCheckResult, HealthReport, HealthStatus

VALID_MODES = ("quick", "full", "repair", "audit")


class HealthRunner:
    """Kayıtlı kontrolleri quick/full modda çalıştırır, skor üretir."""

    def __init__(
        self,
        db_path: str | None = None,
        config: AppConfig | None = None,
        user_context: UserContext | None = None,
    ):
        self.db_path = db_path
        self.config = config
        self.user_context = user_context

    def run(self, mode: str = "full") -> HealthReport:
        mode = str(mode).lower()
        if mode not in VALID_MODES:
            mode = "full"
        context = HealthContext.build(
            db_path=self.db_path,
            config=self.config,
            user_context=self.user_context,
            mode=mode,
        )

        started = time.perf_counter()
        results: list[HealthCheckResult] = []

        if mode == "repair":
            from app.health.auto_repair import AutoRepair

            results = AutoRepair(config=context.health_config).run(context=context)
            for result in results:
                result.metadata.setdefault("score_bucket", "ops")
        else:
            if mode == "quick":
                checks = quick_checks()
            elif mode == "audit":
                checks = audit_checks()
            else:
                checks = all_checks()
            for check in checks:
                result = check.safe_run(context)
                result.metadata.setdefault(
                    "score_bucket", getattr(check, "score_bucket", "architecture")
                )
                results.append(result)
        total_ms = (time.perf_counter() - started) * 1000.0

        score, category_scores = compute_overall_score(results)
        overall = overall_status_for(score)
        summary = build_summary_message(score, overall, results)

        def _count(status: HealthStatus) -> int:
            return sum(1 for r in results if r.status == status.value)

        return HealthReport(
            overall_status=overall,
            score=score,
            total_checks=len(results),
            ok_count=_count(HealthStatus.OK),
            info_count=_count(HealthStatus.INFO),
            warning_count=_count(HealthStatus.WARNING),
            critical_count=_count(HealthStatus.CRITICAL),
            failed_count=_count(HealthStatus.FAILED),
            skipped_count=_count(HealthStatus.SKIPPED),
            fixed_count=_count(HealthStatus.FIXED),
            results=results,
            summary_message=summary,
            mode=mode,
            duration_ms=total_ms,
            category_scores=category_scores,
        )


def run_health(
    mode: str = "full",
    db_path: str | None = None,
    config: AppConfig | None = None,
    user_context: UserContext | None = None,
) -> HealthReport:
    return HealthRunner(
        db_path=db_path, config=config, user_context=user_context
    ).run(mode=mode)

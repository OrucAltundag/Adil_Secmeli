# -*- coding: utf-8 -*-
"""TOPSIS algoritması sağlık kontrolleri."""

from __future__ import annotations

import math

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _TopsisCheck(BaseHealthCheck):
    category = "TOPSIS"
    score_bucket = "ahp_topsis_decision"

    def _sample(self):
        import pandas as pd

        return pd.DataFrame(
            {
                "item_id": [1, 2, 3, 4],
                "k1": [0.2, 0.5, 0.9, 0.1],
                "k2": [0.8, 0.4, 0.1, 0.6],
                "k3": [0.3, 0.7, 0.5, 0.9],
            }
        )


class TopsisDataAvailabilityCheck(_TopsisCheck):
    name = "TOPSIS veri uygunluğu kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            havuz = repo.row_count("havuz") if repo.table_exists("havuz") else 0
            kriter = (
                repo.row_count("ders_kriterleri")
                if repo.table_exists("ders_kriterleri")
                else 0
            )
        if havuz == 0 or kriter == 0:
            return self.warning(
                "TOPSIS için yeterli veri yok.",
                detail=f"havuz={havuz}, ders_kriterleri={kriter}",
                suggestion="Havuz ve kriter verisini tamamlayın.",
            )
        return self.ok(
            "TOPSIS için temel veri mevcut.",
            detail=f"havuz={havuz}, ders_kriterleri={kriter}",
            metadata={"havuz": havuz, "kriter": kriter},
        )


class TopsisNormalizationCheck(_TopsisCheck):
    name = "TOPSIS normalizasyon kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.algorithms.mcdm.topsis import TOPSISRanker
        except Exception as exc:  # noqa: BLE001
            return self.skipped(
                "TOPSIS modülü import edilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Algoritma bağımlılıklarını kontrol edin.",
            )
        ranker = TOPSISRanker()
        output = ranker.rank(self._sample(), top_k=4)
        recs = getattr(output, "recommendations", []) or []
        if not recs:
            return self.critical(
                "TOPSIS sıralaması üretilemedi (boş sonuç).",
                detail="Örnek veride normalize/ağırlıklı matris sonuç vermedi.",
                suggestion="TOPSIS normalize adımını inceleyin.",
            )
        scores = [r.get("score") for r in recs]
        bad = [
            s
            for s in scores
            if s is None or isinstance(s, float) and (math.isnan(s) or math.isinf(s))
        ]
        if bad:
            return self.critical(
                "TOPSIS skorlarında NaN/None/inf var.",
                detail=f"Sorunlu skorlar: {bad}",
                suggestion="Normalize/ideal çözüm hesabını gözden geçirin.",
            )
        out_of_range = [s for s in scores if not (-1e-6 <= float(s) <= 1 + 1e-6)]
        if out_of_range:
            return self.warning(
                "TOPSIS yakınlık skorları 0-1 aralığı dışında.",
                detail=f"Aralık dışı: {out_of_range}",
                suggestion="Yakınlık katsayısı hesabını doğrulayın.",
            )
        return self.ok(
            "TOPSIS normalizasyonu ve skorları sağlıklı.",
            detail=f"{len(recs)} alternatif, skorlar 0-1 aralığında.",
            metadata={"top_score": max(float(s) for s in scores)},
        )


class TopsisRankingValidityCheck(_TopsisCheck):
    name = "TOPSIS sıralama geçerlilik kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.algorithms.mcdm.topsis import TOPSISRanker
        except Exception as exc:  # noqa: BLE001
            return self.skipped(
                "TOPSIS modülü import edilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
            )
        output = TOPSISRanker().rank(self._sample(), top_k=4)
        recs = getattr(output, "recommendations", []) or []
        ranks = [r.get("rank") for r in recs]
        scores = [float(r.get("score", 0)) for r in recs]
        monotonic = all(
            scores[i] >= scores[i + 1] - 1e-9 for i in range(len(scores) - 1)
        )
        if sorted(ranks) != list(range(1, len(recs) + 1)) or not monotonic:
            return self.warning(
                "TOPSIS sıralaması tutarsız.",
                detail=f"ranks={ranks}, skor monoton={monotonic}",
                suggestion="Sıralama (sort) ve rank atamasını gözden geçirin.",
            )
        return self.ok(
            "TOPSIS sıralaması tutarlı ve monoton.",
            detail=f"{len(recs)} alternatif doğru sıralandı.",
        )

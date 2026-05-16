# -*- coding: utf-8 -*-
"""Karar Merkezi sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _DecisionCheck(BaseHealthCheck):
    category = "Karar Merkezi"
    score_bucket = "ahp_decision"


class DecisionInputCheck(_DecisionCheck):
    name = "Karar girdisi kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            tables = set(repo.table_names())
            havuz = repo.row_count("havuz") if "havuz" in tables else 0
            kriter = (
                repo.row_count("ders_kriterleri")
                if "ders_kriterleri" in tables
                else 0
            )
        if havuz == 0 or kriter == 0:
            return self.warning(
                "Karar algoritması için gerekli girişler eksik.",
                detail=f"havuz={havuz} kayıt, ders_kriterleri={kriter} kayıt",
                suggestion="Havuz ve ders kriteri verisini tamamlayın.",
                metadata={"havuz": havuz, "kriter": kriter},
            )
        return self.ok(
            "Karar için temel girdiler mevcut.",
            detail=f"havuz={havuz}, ders_kriterleri={kriter}",
            metadata={"havuz": havuz, "kriter": kriter},
        )


class RankingGenerationCheck(_DecisionCheck):
    name = "Sıralama üretimi kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            import pandas as pd

            from app.algorithms.mcdm.topsis import TOPSISRanker
        except Exception as exc:  # noqa: BLE001
            return self.skipped(
                "Sıralama algoritması import edilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Algoritma bağımlılıklarını kontrol edin.",
            )
        df = pd.DataFrame(
            {"item_id": [1, 2, 3], "k1": [0.2, 0.5, 0.9], "k2": [0.8, 0.4, 0.1]}
        )
        try:
            ranker = TOPSISRanker()
            output = ranker.rank(df, top_k=3)
            recs = getattr(output, "recommendations", None) or getattr(
                output, "result", None
            )
        except Exception as exc:  # noqa: BLE001
            return self.critical(
                "Alternatif sıralaması üretilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Karar algoritması (TOPSIS) hattını inceleyin.",
            )
        if not recs:
            return self.warning(
                "Sıralama sonucu boş döndü.",
                detail="Örnek veride sıralama üretilemedi.",
                suggestion="Algoritma çıktısını ve veri biçimini doğrulayın.",
            )
        return self.ok(
            "Alternatif sıralaması üretilebiliyor.",
            detail=f"Örnek TOPSIS sıralaması {len(recs)} öğe döndürdü.",
        )


class ScoreNormalizationCheck(_DecisionCheck):
    name = "Skor normalizasyonu kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("havuz") or "skor" not in set(
                repo.column_names("havuz")
            ):
                return self.info(
                    "Skor kolonu bulunamadı.",
                    detail="havuz.skor mevcut değil.",
                    suggestion="Skorlama çalıştırıldıktan sonra tekrar kontrol edin.",
                )
            row = repo.fetchone(
                "SELECT MIN(skor), MAX(skor), COUNT(skor) FROM havuz WHERE skor IS NOT NULL"
            )
        mn, mx, cnt = (row or (None, None, 0))
        if not cnt:
            return self.info(
                "Henüz hesaplanmış skor yok.",
                detail="havuz.skor tüm satırlarda NULL.",
                suggestion="Skorlama/karar algoritmasını çalıştırın.",
            )
        if mn is not None and (mn < -1e-6):
            return self.warning(
                "Skorlarda negatif değer var (normalizasyon şüphesi).",
                detail=f"min={mn}, max={mx}, adet={cnt}",
                suggestion="Skor normalizasyon adımını gözden geçirin.",
                metadata={"min": mn, "max": mx},
            )
        return self.ok(
            "Skorlar normalize edilebilir aralıkta.",
            detail=f"min={mn}, max={mx}, adet={cnt}",
            metadata={"min": mn, "max": mx, "count": cnt},
        )


class DecisionResultConsistencyCheck(_DecisionCheck):
    name = "Karar sonucu tutarlılık kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("course_decisions"):
                return self.info(
                    "Karar sonuç tablosu bulunamadı.",
                    detail="course_decisions tablosu yok.",
                    suggestion="Karar çalıştırıldıktan sonra tekrar kontrol edin.",
                )
            total = repo.row_count("course_decisions")
            cols = set(repo.column_names("course_decisions"))
        if total == 0:
            return self.info(
                "Henüz kayıtlı karar sonucu yok.",
                detail="course_decisions boş.",
                suggestion="Karar Merkezi'nden bir karar çalıştırın.",
            )
        score_col = next(
            (c for c in ("score", "skor", "final_score") if c in cols), None
        )
        if score_col:
            with context.repository() as repo:
                bad = repo.scalar(
                    f"SELECT COUNT(*) FROM course_decisions "
                    f"WHERE {score_col} IS NULL OR CAST({score_col} AS REAL) < 0"
                )
            if bad:
                return self.warning(
                    "Bazı karar sonuçlarında geçersiz skor var.",
                    detail=f"{bad} kayıtta NULL/negatif {score_col}",
                    suggestion="Karar skorlarını yeniden hesaplayın.",
                    metadata={"invalid": bad},
                )
        return self.ok(
            f"Karar sonuçları tutarlı ({total} kayıt).",
            detail="Boş/NaN/negatif mantıksız değer bulunmadı.",
            metadata={"total": total},
        )

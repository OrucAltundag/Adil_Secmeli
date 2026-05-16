# -*- coding: utf-8 -*-
"""Ağırlıklı genel sağlık puanı hesaplama.

Her kontrol kategorisinden bir skor bucket'ına eşlenir. Bucket içi
ortalama, bucket ağırlığıyla çarpılarak 0-100 arası genel puan üretilir.
SKIPPED nötrdür (ortalamaya katılmaz); FIXED tam puandır.
"""

from __future__ import annotations

from typing import Iterable

from app.health.models import (
    OVERALL_CRITICAL,
    OVERALL_HEALTHY,
    OVERALL_RISKY,
    OVERALL_WARNING,
    HealthCheckResult,
    HealthStatus,
)

# Skor bucket ağırlıkları (toplam = 1.0).
BUCKET_WEIGHTS: dict[str, float] = {
    "database": 0.15,
    "schema": 0.10,
    "data_quality": 0.10,
    "ahp_topsis_decision": 0.15,
    "period_planning": 0.08,
    "reporting_analytics_benchmark": 0.10,
    "api_ui": 0.10,
    "security": 0.10,
    "architecture": 0.07,
    "ops": 0.05,
}

BUCKET_LABELS_TR: dict[str, str] = {
    "database": "Veritabanı",
    "schema": "Şema",
    "data_quality": "Veri Kalitesi",
    "ahp_topsis_decision": "AHP / TOPSIS / Karar",
    "period_planning": "Dönem Planlama",
    "reporting_analytics_benchmark": "Raporlama / Analiz / Benchmark",
    "api_ui": "API / UI",
    "security": "Güvenlik",
    "architecture": "Mimari",
    "ops": "Test / Bağımlılık / Log / Yedek",
}

# Kontrol kategorisi -> skor bucket eşlemesi.
CATEGORY_TO_BUCKET: dict[str, str] = {
    "Sistem": "ops",
    "Başlangıç": "ops",
    "Veritabanı": "database",
    "Performans": "database",
    "Şema": "schema",
    "Veri Kalitesi": "data_quality",
    "İçe Aktarım Yönetişimi": "data_quality",
    "Fonksiyon": "architecture",
    "Mimari": "architecture",
    "AHP": "ahp_topsis_decision",
    "TOPSIS": "ahp_topsis_decision",
    "Karar Merkezi": "ahp_topsis_decision",
    "Havuz Yaşam Döngüsü": "ahp_topsis_decision",
    "Dönem Planlama": "period_planning",
    "Raporlama": "reporting_analytics_benchmark",
    "Analiz & Grafik": "reporting_analytics_benchmark",
    "Benchmark": "reporting_analytics_benchmark",
    "ML Yönetişimi": "reporting_analytics_benchmark",
    "API": "api_ui",
    "UI": "api_ui",
    "Tablo Görüntüleme": "api_ui",
    "Güvenlik": "security",
    "Bağımlılık": "ops",
    "Yapılandırma": "ops",
    "Log": "ops",
    "Yedekleme": "ops",
    "Test Paketi": "ops",
}

# Durum -> tutulan puan oranı (1.0 = tam puan).
STATUS_MULTIPLIER: dict[str, float] = {
    HealthStatus.OK.value: 1.0,
    HealthStatus.FIXED.value: 1.0,
    HealthStatus.INFO.value: 0.97,
    HealthStatus.WARNING.value: 0.60,
    HealthStatus.CRITICAL.value: 0.20,
    HealthStatus.FAILED.value: 0.10,
}


def _bucket_of(result: HealthCheckResult) -> str:
    bucket = CATEGORY_TO_BUCKET.get(result.category)
    if bucket in BUCKET_WEIGHTS:
        return bucket
    meta_bucket = str(result.metadata.get("score_bucket") or "").strip()
    if meta_bucket in BUCKET_WEIGHTS:
        return meta_bucket
    return "architecture"


def overall_status_for(score: float) -> str:
    if score >= 90:
        return OVERALL_HEALTHY
    if score >= 70:
        return OVERALL_WARNING
    if score >= 40:
        return OVERALL_RISKY
    return OVERALL_CRITICAL


def compute_category_scores(results: Iterable[HealthCheckResult]) -> dict[str, float]:
    """Bucket bazlı 0-100 puanları döndürür (SKIPPED nötr)."""

    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for result in results:
        if result.status == HealthStatus.SKIPPED.value:
            continue
        bucket = _bucket_of(result)
        multiplier = STATUS_MULTIPLIER.get(result.status, 0.5)
        sums[bucket] = sums.get(bucket, 0.0) + multiplier
        counts[bucket] = counts.get(bucket, 0) + 1
    return {
        bucket: round((sums[bucket] / counts[bucket]) * 100.0, 1)
        for bucket in sums
        if counts.get(bucket)
    }


def compute_overall_score(
    results: list[HealthCheckResult],
) -> tuple[float, dict[str, float]]:
    """Ağırlıklı genel puanı ve bucket puanlarını hesaplar."""

    category_scores = compute_category_scores(results)
    if not category_scores:
        return 100.0, category_scores
    total_weight = sum(
        BUCKET_WEIGHTS.get(bucket, 0.0) for bucket in category_scores
    )
    if total_weight <= 0:
        return (
            round(sum(category_scores.values()) / len(category_scores), 1),
            category_scores,
        )
    weighted = sum(
        category_scores[bucket] * BUCKET_WEIGHTS.get(bucket, 0.0)
        for bucket in category_scores
    )
    return round(weighted / total_weight, 1), category_scores


def build_summary_message(
    score: float, overall_status: str, results: list[HealthCheckResult]
) -> str:
    """Kullanıcıya gösterilecek Türkçe özet cümlesi üretir."""

    fixed = sum(1 for r in results if r.status == HealthStatus.FIXED.value)
    problem_buckets = sorted(
        {
            BUCKET_LABELS_TR.get(_bucket_of(r), "Diğer")
            for r in results
            if r.is_problem
        }
    )
    fixed_note = f" {fixed} sorun otomatik düzeltildi." if fixed else ""
    if overall_status == OVERALL_HEALTHY:
        return (
            f"Sistem genel olarak sağlıklı görünüyor (puan {score:.0f}/100)."
            f"{fixed_note} Kritik bir aksiyon gerekmiyor."
        )
    if not problem_buckets:
        return (
            f"Sistem çalışıyor (puan {score:.0f}/100);{fixed_note} yalnızca "
            "bilgi düzeyinde notlar var."
        )
    konular = ", ".join(problem_buckets)
    return (
        f"Sistem çalışıyor ancak iyileştirme gerekiyor (puan {score:.0f}/100)."
        f"{fixed_note} Öne çıkan konular: {konular}."
    )

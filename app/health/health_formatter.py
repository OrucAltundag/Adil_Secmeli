# -*- coding: utf-8 -*-
"""Sağlık raporunu Türkçe, kategorili ve okunabilir metne çevirir."""

from __future__ import annotations

from app.health.health_registry import algorithm_catalog
from app.health.health_score import BUCKET_LABELS_TR
from app.health.models import (
    SEVERITY_LABELS_TR,
    STATUS_LABELS_TR,
    HealthReport,
)

LINE = "=" * 50
SUB = "-" * 50

# Rapor içinde kategori sırası.
CATEGORY_ORDER = [
    "Sistem",
    "Başlangıç",
    "Veritabanı",
    "Şema",
    "Yapılandırma",
    "Bağımlılık",
    "Veri Kalitesi",
    "İçe Aktarım Yönetişimi",
    "Fonksiyon",
    "AHP",
    "TOPSIS",
    "Karar Merkezi",
    "Havuz Yaşam Döngüsü",
    "Dönem Planlama",
    "Raporlama",
    "Analiz & Grafik",
    "Benchmark",
    "ML Yönetişimi",
    "API",
    "UI",
    "Tablo Görüntüleme",
    "Güvenlik",
    "Performans",
    "Mimari",
    "Log",
    "Yedekleme",
    "Test Paketi",
]


def _status_tag(status: str) -> str:
    return f"[{status}] ({STATUS_LABELS_TR.get(status, status)})"


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …"


def format_report(report: HealthReport, *, developer: bool = False) -> str:
    """Genel + kategori bazlı Türkçe rapor metni üretir."""

    detail_limit = 4000 if developer else 600
    lines: list[str] = []
    lines.append(LINE)
    lines.append("GENEL SİSTEM SAĞLIĞI")
    lines.append(LINE)
    lines.append(f"Durum        : {report.overall_status}")
    lines.append(f"Sağlık Puanı : {report.score:.0f} / 100")
    lines.append(f"Mod          : {'Hızlı' if report.mode == 'quick' else 'Tam'}")
    lines.append(f"Toplam Test  : {report.total_checks}")
    lines.append(f"Başarılı     : {report.ok_count}")
    lines.append(f"Bilgi        : {report.info_count}")
    lines.append(f"Uyarı        : {report.warning_count}")
    lines.append(f"Kritik       : {report.critical_count}")
    lines.append(f"Başarısız    : {report.failed_count}")
    lines.append(f"Düzeltildi   : {report.fixed_count}")
    lines.append(f"Atlandı      : {report.skipped_count}")
    lines.append(f"Süre         : {report.duration_ms:.0f} ms")
    lines.append(f"Son Kontrol  : {report.generated_at}")
    lines.append("")
    lines.append("Özet:")
    lines.append(report.summary_message)

    if report.category_scores:
        lines.append("")
        lines.append("Kategori Puanları:")
        for bucket, value in sorted(
            report.category_scores.items(), key=lambda kv: kv[1]
        ):
            label = BUCKET_LABELS_TR.get(bucket, bucket)
            lines.append(f"- {label}: {value:.0f} / 100")

    grouped = report.results_by_category()
    ordered = [c for c in CATEGORY_ORDER if c in grouped]
    ordered += [c for c in grouped if c not in CATEGORY_ORDER]

    for category in ordered:
        results = grouped[category]
        lines.append("")
        lines.append(LINE)
        lines.append(category.upper())
        lines.append(LINE)
        for result in results:
            lines.append(f"{_status_tag(result.status)} {result.name}")
            lines.append(f"Açıklama : {result.message}")
            detail = _trim(result.detail, detail_limit)
            if detail:
                if "\n" in detail:
                    lines.append("Detay    :")
                    for dline in detail.splitlines():
                        lines.append(f"  {dline}")
                else:
                    lines.append(f"Detay    : {detail}")
            if result.suggestion:
                lines.append(f"Öneri    : {result.suggestion}")
            if result.auto_fix_available and not result.auto_fix_applied:
                lines.append("Oto.Düzelt: Mevcut (Güvenli düzeltme uygulanabilir)")
            elif result.auto_fix_applied:
                lines.append("Oto.Düzelt: Uygulandı")
            lines.append(f"Süre     : {result.duration_ms:.0f} ms")
            lines.append(f"Kaynak   : {result.source}")
            if developer:
                lines.append(
                    f"Önem     : {SEVERITY_LABELS_TR.get(result.severity, result.severity)}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_algorithm_catalog() -> str:
    """Aktif/planlanan/uygun değil algoritma kataloğunu metne çevirir."""

    catalog = algorithm_catalog()
    counts = {"ACTIVE": 0, "PLANNED": 0, "NOT_APPLICABLE": 0}
    for item in catalog:
        counts[item.get("status", "PLANNED")] = (
            counts.get(item.get("status", "PLANNED"), 0) + 1
        )
    lines: list[str] = []
    lines.append(LINE)
    lines.append("MEVCUT KONTROLLER / ALGORİTMALAR")
    lines.append(LINE)
    lines.append(
        f"Aktif: {counts.get('ACTIVE', 0)}  •  "
        f"Planlanan: {counts.get('PLANNED', 0)}  •  "
        f"Uygun Değil: {counts.get('NOT_APPLICABLE', 0)}  •  "
        f"Toplam: {len(catalog)}"
    )
    lines.append("")
    label = {
        "ACTIVE": "Çalışıyor",
        "PLANNED": "Planlandı",
        "NOT_APPLICABLE": "Gerekli değil",
    }
    for item in catalog:
        status = item.get("status", "PLANNED")
        lines.append(f"[{status}] {item.get('name')}")
        lines.append(f"Amaç          : {item.get('purpose', '')}")
        lines.append(f"Kullanıldığı Yer: {item.get('used_in', '')}")
        lines.append(
            f"Durum         : {item.get('state', label.get(status, status))}"
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

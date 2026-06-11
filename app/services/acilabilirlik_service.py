# -*- coding: utf-8 -*-
"""Açılabilirlik (acilabilirlik) skoru ve Önerilen Dersler servisi.

Faz 3 (docs/nihai_senaryo.md) kapsaminda eklendi.

Açılabilirlik skoru, bir dersin akademik olarak guclu olmasinin (TOPSIS) yani
sira o DONEM gercekten acilabilir olup olmadigini olcer. Bir ders yuksek
TOPSIS skoruna sahip olabilir ama talep dusukse, veri guveni zayifsa ya da
o donem kaynak/uygunluk yoksa acilamayabilir.

Formul (nihai_senaryo.md §4):

    Acilabilirlik =
        0.45 × TOPSIS        +
        0.25 × Talep         +
        0.15 × Veri_Guveni   +
        0.10 × Donem_Uygunluk +
        0.05 × Kaynak_Uygunluk

Tum bilesenler 0–100 olceginde; cikti da 0–100.

Tasarim notu: `Donem_Uygunluk` ve `Kaynak_Uygunluk` ilk implementasyonda
varsayilan 100.0 ("bilinmiyor, kisit yok") kabul edilir. Kisit verisi
eklendiginde formul kendiliginden dogru sonuca yaklasir.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
)

# Açılabilirlik skoru agirliklari — toplam 1.0.
W_TOPSIS = 0.45
W_TALEP = 0.25
W_VERI_GUVENI = 0.15
W_DONEM_UYGUNLUK = 0.10
W_KAYNAK_UYGUNLUK = 0.05

# Kisit verisi henuz yokken kullanilan varsayilanlar (0–100 olceginde).
DEFAULT_DONEM_UYGUNLUK = 100.0
DEFAULT_KAYNAK_UYGUNLUK = 100.0

# Öneri kategorileri (UI'da gosterilen etiketler).
KATEGORI_GUCLU = "Açılması Güçlü Önerilen"
KATEGORI_SARTLI = "Şartlı Açılması Önerilen"
KATEGORI_HAVUZ = "Havuzda Kalması Önerilen"
KATEGORI_DINLENME = "Dinlenmeye Alınması Önerilen"
KATEGORI_IPTAL = "İptal Adayı"
KATEGORI_BILINMIYOR = "Sınıflandırılamadı"


def _clamp_0_100(value: Any, default: float = 0.0) -> float:
    """Degeri 0–100 araligina kelepceler; gecersizse `default` doner."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(0.0, min(100.0, v))


def compute_acilabilirlik_score(
    topsis_score: float,
    talep_score: float,
    veri_guveni: float,
    donem_uygunluk: float = DEFAULT_DONEM_UYGUNLUK,
    kaynak_uygunluk: float = DEFAULT_KAYNAK_UYGUNLUK,
) -> float:
    """Açılabilirlik skorunu (0–100) hesaplar.

    Tum girdiler 0–100 olceginde beklenir; aralik disindakiler kelepcelenir.
    """
    topsis = _clamp_0_100(topsis_score)
    talep = _clamp_0_100(talep_score)
    guven = _clamp_0_100(veri_guveni)
    donem = _clamp_0_100(donem_uygunluk, DEFAULT_DONEM_UYGUNLUK)
    kaynak = _clamp_0_100(kaynak_uygunluk, DEFAULT_KAYNAK_UYGUNLUK)
    skor = (
        W_TOPSIS * topsis
        + W_TALEP * talep
        + W_VERI_GUVENI * guven
        + W_DONEM_UYGUNLUK * donem
        + W_KAYNAK_UYGUNLUK * kaynak
    )
    return round(skor, 2)


def derive_talep_score(metrics: dict[str, Any] | None) -> float:
    """Ders metriklerinden talep skorunu (0–100) turetir.

    `populerlik` (doluluk_orani, 0–1) ve `anket` (tercih orani, 0–1) sinyalleri
    kullanilir. Ikisi de varsa ortalamasi, biri varsa o, hicbiri yoksa 0 doner.
    `get_faculty_year_topsis_results` metric_map'i bu anahtarlari 0–1 olceginde
    saglar.
    """
    if not metrics:
        return 0.0
    signals: list[float] = []
    for key in ("populerlik", "anket"):
        raw = metrics.get(key)
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        signals.append(max(0.0, min(1.0, v)) * 100.0)
    if not signals:
        return 0.0
    return round(sum(signals) / len(signals), 2)


def categorize_recommendation(
    final_status: int | None,
    approval_required: bool = False,
) -> str:
    """Final statu + onay gerekliligine gore öneri kategorisi doner.

    Müfredatta + onay gerekmiyor  → güçlü öneri
    Müfredatta + onay gerekiyor   → şartlı öneri
    Havuzda                        → havuzda kalma
    Dinlenmede                     → dinlenme
    İptal                          → iptal adayı
    """
    if final_status is None:
        return KATEGORI_BILINMIYOR
    try:
        status = int(final_status)
    except (TypeError, ValueError):
        return KATEGORI_BILINMIYOR
    if status == STATU_MUFREDATTA:
        return KATEGORI_SARTLI if approval_required else KATEGORI_GUCLU
    if status == STATU_HAVUZDA:
        return KATEGORI_HAVUZ
    if status == STATU_DINLENMEDE:
        return KATEGORI_DINLENME
    if status == STATU_IPTAL:
        return KATEGORI_IPTAL
    return KATEGORI_BILINMIYOR


def _populerlik_talep(conn: sqlite3.Connection, course_id: int, year: int) -> float:
    """course_decisions'ta acilabilirlik_score NULL ise fallback talep skoru.

    populerlik tablosundan doluluk_orani okur (0–1 → 0–100).
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT doluluk_orani FROM populerlik "
            "WHERE ders_id = ? AND akademik_yil = ? "
            "ORDER BY rowid DESC LIMIT 1",
            (int(course_id), int(year)),
        )
        row = cur.fetchone()
    except sqlite3.Error:
        return 0.0
    if not row or row[0] is None:
        return 0.0
    try:
        return max(0.0, min(1.0, float(row[0]))) * 100.0
    except (TypeError, ValueError):
        return 0.0


def list_recommended_courses(
    conn: sqlite3.Connection,
    run_id: int,
) -> list[dict[str, Any]]:
    """Bir karar calistirmasi icin Önerilen Dersler listesini doner.

    Her satir: course_decisions alanlari + `acilabilirlik` (0–100) +
    `oneri_kategori`. Açılabilirlik skoruna gore azalan sirada doner.

    `acilabilirlik_score` kolonu doluysa onu kullanir; NULL ise (eski run'lar)
    topsis_score + data_confidence_score + populerlik fallback'iyle aninda
    hesaplar. Boylece Faz 3'ten once uretilmis run'lar da gosterilebilir.
    """
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cd.*, d.kod AS course_code, d.ad AS course_name
        FROM course_decisions cd
        LEFT JOIN ders d ON d.ders_id = cd.course_id
        WHERE cd.decision_run_id = ?
        """,
        (int(run_id),),
    )
    rows = [dict(r) for r in cur.fetchall()]

    enriched: list[dict[str, Any]] = []
    for row in rows:
        stored = row.get("acilabilirlik_score")
        if stored is not None:
            try:
                acilabilirlik = float(stored)
            except (TypeError, ValueError):
                acilabilirlik = None
        else:
            acilabilirlik = None

        if acilabilirlik is None:
            # Fallback: eski run — kolon bos. Anlik hesapla.
            topsis = row.get("topsis_score") or 0.0
            guven = (row.get("data_confidence_score") or 0.0) * 100.0
            talep = _populerlik_talep(conn, int(row.get("course_id") or 0), int(row.get("year") or 0))
            acilabilirlik = compute_acilabilirlik_score(
                topsis_score=topsis,
                talep_score=talep,
                veri_guveni=guven,
            )

        row["acilabilirlik"] = round(float(acilabilirlik), 2)
        row["oneri_kategori"] = categorize_recommendation(
            row.get("final_status"),
            bool(row.get("approval_required")),
        )
        enriched.append(row)

    enriched.sort(key=lambda r: r["acilabilirlik"], reverse=True)
    return enriched

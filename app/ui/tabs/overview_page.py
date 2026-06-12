# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs/overview_page.py — Genel Bakış / Algoritma Rehberi
# =============================================================================
# Sistemin ne iş yaptığını, karar boru hattını ve kullanılan her algoritmanın
# NEDEN kullanıldığını + matematiksel formülünü + çıktısının arayüzde NEREDE
# görüleceğini tek ekranda özetler. Salt bilgilendirme; DB bağımlılığı yoktur.
# =============================================================================

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Renk paleti (mevcut sayfalarla uyumlu)
BG = "#f8fafc"
INK = "#0f172a"
MUTED = "#475569"
ACCENT = "#1565C0"

# Karar boru hattı adımları (tek bakışta akış)
PIPELINE = [
    ("1", "Kriter Verisi", "Kriter & Havuz → Kriter Girdi", "#0369a1"),
    ("2", "AHP Ağırlık", "AHP Ağırlık Yönetimi", "#7c3aed"),
    ("3", "TOPSIS Skor", "Karar Merkezi → Ders Kararları", "#0891b2"),
    ("4", "Trend + Veri Güveni", "Karar Merkezi → Ders Kararları", "#059669"),
    ("5", "Karar Politikası", "Karar Merkezi → Karar Politikaları", "#d97706"),
    ("6", "Açılabilirlik", "Karar Merkezi → Önerilen Dersler", "#6d28d9"),
    ("7", "Dönem Planı", "Dönem Planlama", "#be123c"),
]

# Her algoritma: (ad, ne işe yarar / neden, formül, çıktı nerede görülür)
ALGORITMALAR = [
    (
        "AHP — Analitik Hiyerarşi Süreci",
        "Akademik kurulun 'hangi kriter daha önemli?' kararını sayıya çevirir. "
        "Kriterleri (başarı, trend, popülerlik, anket) ikili karşılaştırır ve "
        "tutarlı ağırlıklar üretir.",
        "Ağırlık = ikili karşılaştırma matrisinin geometrik ortalama normalizasyonu.\n"
        "Tutarlılık: CR = CI / RI ,  CI = (λmax − n) / (n − 1).  Kabul: CR ≤ 0.10.",
        "AHP Ağırlık Yönetimi → ağırlıklar + CR değeri (ve onay akışı).",
    ),
    (
        "TOPSIS — İdeal Çözüme Yakınlık",
        "Dersleri çok kriterli olarak sıralar: ideal (en iyi) çözüme yakın, "
        "negatif-ideale uzak ders daha güçlü adaydır.",
        "Normalize → AHP ağırlıklarıyla çarp → ideal (S⁺) ve negatif-ideal (S⁻) "
        "uzaklıkları.\nYakınlık: C = S⁻ / (S⁺ + S⁻) , 0–1 → ×100 ile 0–100.",
        "Karar Merkezi → Ders Kararları (TOPSIS skoru) + skor kırılımı.",
    ),
    (
        "Trend Analizi",
        "Dersin yıllar içindeki gidişatını (yükselen / düşen / sabit) ölçer; "
        "tek yıllık dalgalanmaya değil eğilime bakar.",
        "Ağırlıklı yıllık değişim — son yıllar daha ağır (örn. 0.50 / 0.30 / 0.20). "
        "Pozitif = yükselen, negatif = düşen eğilim.",
        "Karar Merkezi → Ders Kararları (trend etiketi) + Ders Lab.",
    ),
    (
        "Veri Güveni",
        "Bir kararın ne kadar sağlam veriye dayandığını işaretler. Eksik kriter / "
        "anket / geçmiş veri güveni düşürür; düşük güvenli kararlar tekrar incelenir.",
        "Veri bileşenlerinin (kriter, performans, popülerlik, anket, geçmiş) "
        "doluluk ağırlıklı toplamı, 0–1 aralığında.",
        "Karar Merkezi → Ders Kararları (veri güveni) + Hassas Kararlar.",
    ),
    (
        "Karar Politikası (Eşik Tabanlı Sınıflandırma)",
        "TOPSIS skorunu akademik statüye çevirir. Eşikler fakülte kararıyla "
        "değiştirilebilir; kalıcı iptal her zaman manuel onay ister.",
        "Skor ≥ 70 → Müfredatta   |   ≥ 50 → Havuzda   |   < 40 → Dinlenme   |   "
        "≤ 30 → İptal Adayı.",
        "Karar Merkezi → Karar Politikaları (aktif eşikler).",
    ),
    (
        "Açılabilirlik Skoru",
        "Dersin akademik gücünün (TOPSIS) yanı sıra O DÖNEM fiilen açılabilir "
        "olup olmadığını ölçer. Önerilen Dersler sıralamasını ve dönem planı "
        "aday seçimini besler.",
        "Açılabilirlik = 0.45·TOPSIS + 0.25·Talep + 0.15·Veri Güveni "
        "+ 0.10·Dönem Uygunluk + 0.05·Kaynak Uygunluk  (hepsi 0–100).",
        "Karar Merkezi → Önerilen Dersler (açılabilirlik + kategori).",
    ),
    (
        "Dönem Planlama (Kısıtlı Atama)",
        "Açılabilirliği yüksek dersleri Güz/Bahar dönemlerine; kontenjan, ön "
        "koşul, öğretim üyesi ve kaynak kısıtlarını gözeterek dengeli dağıtır.",
        "Hedef: 8 seçmeli (Güz 4 / Bahar 4). Adaylar açılabilirlik skoruna göre "
        "sıralanır; hard kısıtlar yerleşimi engelleyebilir.",
        "Dönem Planlama → Güz/Bahar planı + kısıt ihlalleri + alternatifler.",
    ),
]


class OverviewPage(ttk.Frame):
    """Genel Bakış / Algoritma Rehberi — sistemin tek-bakışta özeti."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._build()

    # --- kaydırılabilir gövde ------------------------------------------------
    def _build(self) -> None:
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=BG)

        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Fare tekerleği ile kaydırma
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        self._build_header(body)
        self._build_pipeline(body)
        self._build_algorithms(body)
        self._build_quickstart(body)

    def _build_header(self, parent) -> None:
        box = tk.Frame(parent, bg=ACCENT)
        box.pack(fill=tk.X, padx=16, pady=(16, 8))
        tk.Label(
            box, text="Seçmeli Ders Karar Destek Sistemi",
            bg=ACCENT, fg="white", font=("Segoe UI", 17, "bold"), anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(12, 2))
        tk.Label(
            box,
            text="Fakültenin hangi seçmeli dersleri açacağına, havuzda bekleteceğine, "
            "dinlenmeye alacağına veya iptal adayı yapacağına; geçmiş başarı, talep, "
            "anket ve trend verisini AHP + TOPSIS ile birleştirerek AÇIKLANABİLİR "
            "öneriler üretir. Nihai kararı her zaman akademik kurul verir.",
            bg=ACCENT, fg="#e2e8f0", font=("Segoe UI", 10),
            wraplength=900, justify="left", anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(0, 12))

    def _build_pipeline(self, parent) -> None:
        ttk.Label(
            parent, text="Karar Boru Hattı — Veriden Plana",
            font=("Segoe UI", 13, "bold"), foreground=INK, background=BG,
        ).pack(anchor="w", padx=16, pady=(10, 4))

        row = tk.Frame(parent, bg=BG)
        row.pack(fill=tk.X, padx=12, pady=(0, 10))
        for i, (no, ad, yer, renk) in enumerate(PIPELINE):
            card = tk.Frame(row, bg=renk)
            card.grid(row=0, column=i * 2, sticky="nsew", padx=2, pady=2, ipadx=4, ipady=4)
            tk.Label(card, text=f"{no}. {ad}", bg=renk, fg="white",
                     font=("Segoe UI", 9, "bold"), wraplength=120, justify="center").pack(padx=6, pady=(4, 0))
            tk.Label(card, text=yer, bg=renk, fg="#e2e8f0",
                     font=("Segoe UI", 7), wraplength=120, justify="center").pack(padx=6, pady=(0, 4))
            if i < len(PIPELINE) - 1:
                tk.Label(row, text="→", bg=BG, fg=MUTED, font=("Segoe UI", 12, "bold")).grid(
                    row=0, column=i * 2 + 1)
        for i in range(len(PIPELINE)):
            row.columnconfigure(i * 2, weight=1)

    def _build_algorithms(self, parent) -> None:
        ttk.Label(
            parent, text="Kullanılan Algoritmalar — Neden ve Nasıl?",
            font=("Segoe UI", 13, "bold"), foreground=INK, background=BG,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        for ad, neden, formul, nerede in ALGORITMALAR:
            card = tk.Frame(parent, bg="white", highlightbackground="#cbd5e1", highlightthickness=1)
            card.pack(fill=tk.X, padx=16, pady=5)
            tk.Label(card, text=ad, bg="white", fg=ACCENT,
                     font=("Segoe UI", 11, "bold"), anchor="w").pack(fill=tk.X, padx=12, pady=(8, 2))
            tk.Label(card, text=neden, bg="white", fg=INK, font=("Segoe UI", 9),
                     wraplength=860, justify="left", anchor="w").pack(fill=tk.X, padx=12, pady=(0, 6))

            frm = tk.Frame(card, bg="#f1f5f9")
            frm.pack(fill=tk.X, padx=12, pady=(0, 6))
            tk.Label(frm, text="Formül / Mantık", bg="#f1f5f9", fg=MUTED,
                     font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X, padx=8, pady=(4, 0))
            tk.Label(frm, text=formul, bg="#f1f5f9", fg="#0f172a",
                     font=("Consolas", 9), wraplength=840, justify="left", anchor="w").pack(
                fill=tk.X, padx=8, pady=(0, 6))

            tk.Label(card, text=f"📍 Çıktı nerede:  {nerede}", bg="white", fg="#15803d",
                     font=("Segoe UI", 9, "italic"), anchor="w").pack(fill=tk.X, padx=12, pady=(0, 8))

    def _build_quickstart(self, parent) -> None:
        box = tk.Frame(parent, bg="#0f172a")
        box.pack(fill=tk.X, padx=16, pady=(12, 18))
        tk.Label(box, text="Hızlı Başlangıç — Sırayla", bg="#0f172a", fg="white",
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X, padx=12, pady=(10, 4))
        adimlar = (
            "1) Sistem → Sistem Sağlığı: 'Tam Sağlık Kontrolü'\n"
            "2) Veri → Veri Yönetimi / Veri Kalitesi: kapsam (2022 / fakülte) seç\n"
            "3) Kriter & Havuz → Kriter Girdi: eksik kriterleri elle gir\n"
            "4) AHP Ağırlık Yönetimi: profil oluştur, CR ≤ 0.10, aktif yap\n"
            "5) Karar Merkezi → Karar Politikaları: aktif politika + Hazırlık 'Hazır'\n"
            "6) Karar Merkezi → Çalıştırmalar: 'Yeni Karar Çalıştır'\n"
            "7) Karar Merkezi → Önerilen Dersler / Ders Kararları: sonuçları incele\n"
            "8) Dönem Planlama: 'Plan Üret' → Güz/Bahar planı\n"
            "9) Raporlama & Analiz: CSV/Excel dışa aktar"
        )
        tk.Label(box, text=adimlar, bg="#0f172a", fg="#e2e8f0", font=("Segoe UI", 9),
                 justify="left", anchor="w").pack(fill=tk.X, padx=12, pady=(0, 12))

    def refresh(self, force_reload: bool = False) -> None:
        """Statik içerik; yenileme gerektirmez (arayüz tutarlılığı için var)."""
        return None

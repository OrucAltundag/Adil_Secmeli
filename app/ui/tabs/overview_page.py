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
    ("1", "Sağlık + Veri", "Sistem Sağlığı / Veri Kalitesi", "#0369a1"),
    ("2", "Trend + LR", "Veri → Trend", "#059669"),
    ("3", "Kriter + AHP", "Kriter Girdi / AHP Yönetimi", "#7c3aed"),
    ("4", "TOPSIS", "TOPSIS Kararı", "#0891b2"),
    ("5", "Geçici Karar", "Algoritma Kontrol", "#2563eb"),
    ("6", "ELECTRE + DT", "Karar Merkezi → Ders Kararları", "#d97706"),
    ("7", "PROMETHEE II", "Karar Merkezi → Önerilen Dersler", "#6d28d9"),
    ("8", "Müfredat Onayı", "Havuz Yaşam Döngüsü", "#be123c"),
    ("9", "Dönem Planı", "Dönem Planlama", "#9f1239"),
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
        "Trend Analizi + Lineer Regresyon (LR)",
        "Dersin yıllar içindeki gidişatını (yükselen / düşen / sabit) ölçer; "
        "tek yıllık dalgalanmaya değil eğilime bakar.",
        "Ağırlıklı trend: son 3 yıl 0.50 / 0.30 / 0.20. LR: y = β0 + β1·x; "
        "son üç kesinleşme puanından bir sonraki yıl için 0–100 tahmin üretir.",
        "Veri → Trend (geçmiş değerler, ağırlıklı trend ve LR tahmini).",
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
        "ELECTRE TRI-B — Kriter Bazlı Statü Ataması",
        "Dersi yalnız toplam puanla değil; başarı, trend, doluluk ve anket değerlerini "
        "Müfredat/Havuz/Dinlenme sınır profilleriyle ayrı ayrı karşılaştırarak sınıflandırır.",
        "Uyum (concordance) + uyumsuzluk/veto → credibility σ(a,b). "
        "σ ≥ λ ise ders ilgili sınır profilini geçer; varsayılan λ=0.65.",
        "Karar Merkezi → Karar Politikaları / Ders Kararları.",
    ),
    (
        "Decision Tree — Bağımsız İkinci Görüş",
        "Geçmişte uygulanmış final statülerinden öğrenerek ELECTRE önerisini kontrol eder. "
        "Nihai kararı değiştirmez; uyum veya çatışmayı kurul incelemesine sunar.",
        "Özellikler: başarı, trend, LR trend tahmini, doluluk, anket, TOPSIS, veri güveni, "
        "eski statü. En az 100 geçmiş örnek ve sınıf başına 10 kayıt gerekir.",
        "Karar Merkezi → Ders Kararları (DT Önerisi / ELECTRE-DT).",
    ),
    (
        "PROMETHEE II — Müfredat Dışı Top-7 Öneri",
        "Aktif müfredatta olmayan adayları ikili karşılaştırır; net akış ve çeşitlilik "
        "kontrolüyle fakülte/bölüm kapsamına en uygun en fazla 7 dersi önerir.",
        "π(a,b)=Σw·P(a−b); φ+=ortalama üstünlük, φ−=ortalama yenilgi, net akış φ=φ+−φ−. "
        "Son seçimde benzer derslere çeşitlilik cezası uygulanır.",
        "Karar Merkezi → Önerilen Dersler.",
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
            "anket ve trend verisini AHP, TOPSIS, ELECTRE TRI-B ve PROMETHEE II ile birleştirerek AÇIKLANABİLİR "
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
            "2) Veri → Veri Yönetimi: bölüm kapsamı, import geçmişi, kalite ve onay\n"
            "3) Veri → Veri Kalitesi: kapsam raporu; Veri → Trend: geçmiş + LR tahmini\n"
            "4) Karar Süreci → Kriter & Havuz: kriterleri incele; AHP'de CR ≤ 0.10\n"
            "5) TOPSIS Kararı: bölüm bazlı göreli sıralama ve formül dökümü\n"
            "6) Algoritma Kontrol & Ders Lab: 'Sonraki Yıl Kararını Hesapla'\n"
            "7) Karar Merkezi → Hazırlık / Karar Politikaları / Ders Kararları\n"
            "8) Karar Merkezi → Önerilen Dersler (PROMETHEE II Top-7)\n"
            "9) Havuz Yaşam Döngüsü: önizle, gerekirse değiştir, müfredatı onayla\n"
            "10) Havuz Yönetimi → Dönem Planlama → Rapor & Yükleme"
        )
        tk.Label(box, text=adimlar, bg="#0f172a", fg="#e2e8f0", font=("Segoe UI", 9),
                 justify="left", anchor="w").pack(fill=tk.X, padx=12, pady=(0, 12))

    def refresh(self, force_reload: bool = False) -> None:
        """Statik içerik; yenileme gerektirmez (arayüz tutarlılığı için var)."""
        return None

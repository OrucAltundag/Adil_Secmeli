# -*- coding: utf-8 -*-
"""Veri Kalitesi Kontrol Paneli"""

from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from app.core.config import load_app_config
from app.services.data_quality_integration_service import (
    build_quality_report,
    list_available_years,
    list_faculties,
)


class DataQualityPage(ttk.Frame):
    """Veri kalitesi ve kapsama raporu"""

    def __init__(self, parent, app=None, db_path=None):
        super().__init__(parent)
        self.app = app
        self.db_path = db_path or (getattr(app, "db_path", None) if app else None)
        self.config = load_app_config() if not app else getattr(app, "app_config", load_app_config())
        self._setup_ui()

    def _refresh_db_path(self) -> str | None:
        app_path = getattr(self.app, "db_path", None) if self.app else None
        cfg_path = getattr(self.config, "sqlite_db_path", None)
        for candidate in (app_path, self.db_path, cfg_path):
            if candidate:
                self.db_path = os.path.abspath(str(candidate))
                return self.db_path
        return None

    def _require_db_path(self) -> str:
        db_path = self._refresh_db_path()
        if not db_path:
            raise RuntimeError("Veritabanı bağlantısı bulunamadı. Üst menüden geçerli veritabanı dosyasını seçin.")
        return db_path

    def _setup_ui(self):
        """UI bileşenlerini kur"""
        # Ana kontrol barı
        ctrl_frame = ttk.Frame(self, padding=8)
        ctrl_frame.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(ctrl_frame, text="Akademik Yıl").pack(side=tk.LEFT)
        self.year_combo = ttk.Combobox(ctrl_frame, width=10, state="readonly")
        self.year_combo.pack(side=tk.LEFT, padx=(4, 12))
        self._populate_years()

        ttk.Label(ctrl_frame, text="Fakülte").pack(side=tk.LEFT)
        self.faculty_combo = ttk.Combobox(ctrl_frame, width=28, state="readonly")
        self.faculty_combo.pack(side=tk.LEFT, padx=(4, 12))
        self._populate_faculties()

        ttk.Button(ctrl_frame, text="Raporla Oluştur", command=self._generate_report).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl_frame, text="Yenile", command=self._refresh).pack(side=tk.LEFT)

        # Notebook: Sekmeleri ayır
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._build_summary_tab()
        self._build_coverage_tab()
        self._build_readiness_tab()
        self._build_missing_data_tab()
        self._build_validation_issues_tab()

    def _tab_info(self, parent, baslik, ne_ise_yarar, veri_kaynagi, dogruluk, renk="#1565C0"):
        """Her sekmenin üstüne; amaç, veri kaynağı ve doğruluk açıklayan bilgi kutusu."""
        box = tk.Frame(parent, bg=renk)
        box.pack(fill=tk.X, pady=(0, 6))
        inner = tk.Frame(box, bg="#F4F8FE")
        inner.pack(fill=tk.X, padx=2, pady=2)
        tk.Label(
            inner, text=baslik, bg="#F4F8FE", fg=renk,
            font=("Segoe UI", 10, "bold"), anchor=tk.W,
        ).pack(fill=tk.X, padx=10, pady=(5, 2))
        tk.Label(
            inner, text="Ne işe yarar:  " + ne_ise_yarar,
            bg="#F4F8FE", fg="#2A2A2A", font=("Segoe UI", 8),
            anchor=tk.W, justify=tk.LEFT, wraplength=1150,
        ).pack(fill=tk.X, padx=10, pady=1)
        tk.Label(
            inner, text="Veri kaynağı:  " + veri_kaynagi,
            bg="#FFF6DF", fg="#6B4E00", font=("Segoe UI", 8, "bold"),
            anchor=tk.W, justify=tk.LEFT, wraplength=1150,
        ).pack(fill=tk.X, padx=10, pady=2, ipady=2)
        tk.Label(
            inner, text="Doğruluk / nasıl ölçülür:  " + dogruluk,
            bg="#F4F8FE", fg="#1B5E20", font=("Segoe UI", 8),
            anchor=tk.W, justify=tk.LEFT, wraplength=1150,
        ).pack(fill=tk.X, padx=10, pady=(1, 5))

    def _build_summary_tab(self):
        """Veri Özeti sekmesi"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Veri Özeti")

        content = ttk.Frame(frame, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        self._tab_info(
            content,
            "Veri Özeti — Genel Durum Panosu",
            "Seçili yıl ve fakülte için verinin ne kadar tam olduğunu tek bakışta gösterir: "
            "toplam ders, kaç dersin kriter/performans/popülerlik/anket verisi var ve genel "
            "kapsama yüzdesi. Karar almadan önce ilk bakılacak sekmedir.",
            "ders, ders_kriterleri, performans, populerlik, anket_sonuclari tabloları. "
            "Bu veriler 'Veri Yönetimi' sekmesinden Excel içe aktarılarak doldurulur.",
            "Kapsama %, ağırlıklı ortalamadır: kriter %40 + performans %25 + popülerlik %20 + "
            "anket %15. Sayımlar seçili yıl ve fakülteye göre filtrelenir (distinct ders_id).",
        )

        # Stat grid
        stats_frame = ttk.LabelFrame(content, text="İstatistikler", padding=8)
        stats_frame.pack(fill=tk.X, pady=(0, 8))

        self.stat_labels = {}
        stats = [
            ("Toplam Ders", "total_courses"),
            ("Kriter Verisi Olan", "courses_with_criteria"),
            ("Performans Verisi Olan", "courses_with_performance"),
            ("Populerlik Verisi Olan", "courses_with_popularity"),
            ("Anket Verisi Olan", "courses_with_survey"),
            ("Kapsama %", "coverage_percentage"),
        ]

        for i, (label, key) in enumerate(stats):
            ttk.Label(stats_frame, text=f"{label}:").grid(row=i // 3, column=(i % 3) * 2, sticky=tk.W, padx=4, pady=4)
            self.stat_labels[key] = ttk.Label(stats_frame, text="-", foreground="blue")
            self.stat_labels[key].grid(row=i // 3, column=(i % 3) * 2 + 1, sticky=tk.W, padx=4, pady=4)

        # Info text
        self.summary_text = tk.Text(content, height=10, wrap=tk.WORD, font=("Courier", 9))
        self.summary_text.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL, command=self.summary_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.config(yscrollcommand=scrollbar.set)

    def _build_coverage_tab(self):
        """Kapsama Raporu sekmesi"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Kapsama Raporu")

        content = ttk.Frame(frame, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        self._tab_info(
            content,
            "Kapsama Raporu — Veri Tipi Bazında Doluluk",
            "Her veri tipinin (kriter, performans, popülerlik, anket) ders bazında ne oranda "
            "dolu olduğunu çubuk grafiklerle gösterir ve hangi tipte kaç ders eksik olduğunu listeler.",
            "ders_kriterleri (yıl filtreli), performans/populerlik (akademik_yil + değer dolu), "
            "anket_sonuclari (oy_sayisi>0). Hepsi seçili fakülteye göre ders JOIN'i ile filtrelenir.",
            "Oran = (o veriye sahip distinct ders) / (filtrelenen toplam ders) × 100. "
            "Eksikse 'Veri Yönetimi'nden ilgili Excel'i içe aktarın.",
            renk="#00838F",
        )

        # Progress bars
        metrics = [
            ("Kriter Kapsama", "criteria"),
            ("Performans Kapsama", "performance"),
            ("Populerlik Kapsama", "popularity"),
            ("Anket Kapsama", "survey"),
        ]

        self.progress_bars = {}
        self.progress_value_labels = {}
        for label, key in metrics:
            header = ttk.Frame(content)
            header.pack(fill=tk.X, pady=(8, 2))
            ttk.Label(header, text=label).pack(side=tk.LEFT)
            value_label = ttk.Label(header, text="0 / 0  (%0.0)")
            value_label.pack(side=tk.RIGHT)
            self.progress_value_labels[key] = value_label
            pb = ttk.Progressbar(content, mode="determinate", maximum=100)
            pb.pack(fill=tk.X, pady=(0, 8))
            self.progress_bars[key] = pb

        # Details
        self.coverage_text = tk.Text(content, height=12, wrap=tk.WORD, font=("Courier", 9))
        self.coverage_text.pack(fill=tk.BOTH, expand=True, pady=8)

    def _build_readiness_tab(self):
        """Veri Olgunluğu sekmesi"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Veri Olgunluğu")

        content = ttk.Frame(frame, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        self._tab_info(
            content,
            "Veri Olgunluğu — Karar Alınabilir mi?",
            "Tüm veri tiplerini ve doğrulama kalitesini tek bir 0-100 skora indirger ve "
            "'karar alınabilir' seviyesine ulaşıp ulaşmadığınızı söyler. Bileşen skorları "
            "hangi alana yüklenmeniz gerektiğini gösterir.",
            "assess_data_readiness servisi: ders_kriterleri/performans/populerlik/anket + "
            "criteria_validation_issues (kritik sorun sayısı).",
            "Skor = kriter %40 + performans %15 + popülerlik %15 + anket %15 + doğrulama %15. "
            "Her kritik doğrulama sorunu doğrulama skorundan 25 puan düşürür. ≥85 = karar hazır.",
            renk="#6A1B9A",
        )

        # Readiness gauge
        gauge_frame = ttk.LabelFrame(content, text="Hazırlık Seviyesi", padding=8)
        gauge_frame.pack(fill=tk.X, pady=(0, 8))

        self.readiness_label = ttk.Label(gauge_frame, text="-", font=("Arial", 24, "bold"))
        self.readiness_label.pack()

        self.readiness_pb = ttk.Progressbar(gauge_frame, mode="determinate", maximum=100)
        self.readiness_pb.pack(fill=tk.X, pady=8)

        # Details
        self.readiness_text = tk.Text(content, height=14, wrap=tk.WORD, font=("Courier", 9))
        self.readiness_text.pack(fill=tk.BOTH, expand=True)

    def _build_missing_data_tab(self):
        """Eksik Veri sekmesi"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Eksik Veri Matrisi")

        content = ttk.Frame(frame, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        self._tab_info(
            content,
            "Eksik Veri Matrisi — Hangi Dersin Nesi Eksik?",
            "En az bir veri tipi eksik olan dersleri tek tek listeler. Her hücre ✓ (var) "
            "veya ✗ (eksik) gösterir; böylece tam olarak hangi ders için hangi Excel'i "
            "içe aktarmanız gerektiğini görürsünüz.",
            "ders tablosu (seçili fakülte) + her veri tablosunda o dersin/yılın kaydı var mı "
            "kontrolü (EXISTS sorgusu).",
            "✗ = o ders+yıl için ilgili tabloda kayıt yok veya değer NULL. Tam dersler "
            "listede gösterilmez (sadece eksiği olanlar).",
            renk="#C62828",
        )

        # Treeview
        cols = ("Ders", "Kriter", "Performans", "Populerlik", "Anket", "Trend")
        self.missing_tree = ttk.Treeview(content, columns=cols[1:], height=18)
        self.missing_tree.column("#0", width=200, anchor=tk.W)
        self.missing_tree.heading("#0", text=cols[0])

        for col in cols[1:]:
            self.missing_tree.column(col, width=80, anchor=tk.CENTER)
            self.missing_tree.heading(col, text=col)

        scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL, command=self.missing_tree.yview)
        self.missing_tree.config(yscrollcommand=scrollbar.set)

        self.missing_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_validation_issues_tab(self):
        """Validation İssues sekmesi"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Doğrulama Sorunları")

        content = ttk.Frame(frame, padding=12)
        content.pack(fill=tk.BOTH, expand=True)
        self._tab_info(
            content,
            "Doğrulama Sorunları — Hatalı / Şüpheli Veri Girişleri",
            "İçe aktarılan veride tespit edilen tutarsızlıkları listeler: aralık dışı değer, "
            "negatif sayı, %100'ü aşan oran, eksik zorunlu alan vb. Kritik sorunlar karar "
            "almayı engeller; bunlar düzeltilmeden algoritma güvenilir çalışmaz.",
            "criteria_validation_issues tablosu (içe aktarma sırasında doğrulama motoru üretir). "
            "Boşsa data_validation_issues'a düşülür.",
            "Şiddet: 'critical' = bloklar, 'warning' = uyarı. Yanlış değeri 'Veri Yönetimi'nde "
            "düzeltip yeniden içe aktarın; sorun otomatik kaybolur.",
            renk="#E65100",
        )

        # Issue list
        cols = ("ID", "Tür", "Şiddet", "Mesaj", "İçin Gerekli", "Durum")
        self.issues_tree = ttk.Treeview(content, columns=cols[1:], height=16)
        self.issues_tree.column("#0", width=40, anchor=tk.CENTER)
        self.issues_tree.heading("#0", text=cols[0])

        widths = [80, 80, 400, 100, 100]
        for i, col in enumerate(cols[1:]):
            self.issues_tree.column(col, width=widths[i], anchor=tk.W)
            self.issues_tree.heading(col, text=col)

        scrollbar = ttk.Scrollbar(content, orient=tk.VERTICAL, command=self.issues_tree.yview)
        self.issues_tree.config(yscrollcommand=scrollbar.set)

        self.issues_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _populate_years(self):
        """Akademik yılları doldur (servis üzerinden)"""
        try:
            previous = self.year_combo.get() if hasattr(self, "year_combo") else ""
            db_path = self._refresh_db_path()
            year_values = list_available_years(db_path) if db_path else []
            years = [str(year) for year in year_values]
            self.year_combo["values"] = years
            if previous in years:
                self.year_combo.set(previous)
            elif years:
                self.year_combo.current(0)
            else:
                self.year_combo.set("")
        except Exception as e:
            print(f"Yıl yükleme hatası: {e}")

    def _populate_faculties(self):
        """Fakülteleri doldur (servis üzerinden)"""
        try:
            previous = self.faculty_combo.get() if hasattr(self, "faculty_combo") else ""
            db_path = self._refresh_db_path()
            faculties = [
                f"{ad} (ID: {fid})" for fid, ad in (list_faculties(db_path) if db_path else [])
            ]
            self.faculty_combo["values"] = ["Tümü"] + faculties
            if previous in self.faculty_combo["values"]:
                self.faculty_combo.set(previous)
            else:
                self.faculty_combo.current(0)
        except Exception as e:
            self.faculty_combo["values"] = ["Tümü"]
            self.faculty_combo.current(0)
            print(f"Fakülte yükleme hatası: {e}")

    def _get_selected_faculty_id(self):
        """Seçili fakülteTidini al"""
        val = self.faculty_combo.get()
        if val == "Tümü" or not val:
            return None
        try:
            return int(val.split("(ID: ")[-1].rstrip(")"))
        except (ValueError, IndexError):
            return None

    def _generate_report(self):
        """Rapor oluştur"""
        self._refresh_db_path()
        if not self.year_combo.get():
            self._populate_years()
        if not self.faculty_combo.get():
            self._populate_faculties()

        year_str = self.year_combo.get()
        if not year_str:
            messagebox.showwarning(
                "Veri Kalitesi",
                "Rapor oluşturmak için akademik yıl bulunamadı. Veri Yönetimi sekmesinden müfredat/kriter verisi içe aktarın.",
            )
            return

        try:
            year = int(year_str)
            faculty_id = self._get_selected_faculty_id()
            db_path = self._require_db_path()

            # Tüm rapor servis katmanında tek seferde hesaplanır
            report = build_quality_report(db_path, year, faculty_id)

            self._update_summary(report["readiness"], report["coverage"])
            self._update_coverage(report["coverage"])
            self._update_readiness(report["readiness"])
            self._update_missing_data(report["missing_data"])
            self._update_validation_issues(report["validation_issues"], year)

        except Exception as e:
            messagebox.showerror("Rapor Hatası", str(e))

    def _update_summary(self, readiness: dict, coverage: dict):
        """Summary sekmesini güncelle"""
        self.summary_text.delete("1.0", tk.END)

        # Stats
        self.stat_labels["total_courses"].config(text=str(coverage.get("total_courses", 0)))
        self.stat_labels["courses_with_criteria"].config(text=str(coverage.get("courses_with_criteria", 0)))
        self.stat_labels["courses_with_performance"].config(text=str(coverage.get("courses_with_performance", 0)))
        self.stat_labels["courses_with_popularity"].config(text=str(coverage.get("courses_with_popularity", 0)))
        self.stat_labels["courses_with_survey"].config(text=str(coverage.get("courses_with_survey", 0)))
        self.stat_labels["coverage_percentage"].config(text=f"{coverage.get('coverage_percentage', 0):.1f}%")

        # Text
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summary_text.insert(
            tk.END,
            f"""Raporlama Tarihi: {now}

VERİ KALITESI ÖZETİ
==================

Genel Durum:
- Olgunluk Skoru: {readiness.get('readiness_score', 0):.1f}/100  (formül v{readiness.get('formula_version', 2)})
- Hazırlık Seviyesi: {readiness.get('readiness_level', 'Bilinmeyen')}

ZORUNLU veri yalnızca MÜFREDATTAKİ dersler için beklenir.
- Müfredat (zorunlu) ders sayısı: {coverage.get('required_courses', coverage.get('total_courses', 0))}
- Fakültedeki toplam ders: {coverage.get('total_all_courses', coverage.get('total_courses', 0))}

Kapsama Oranları (payda = müfredat dersi):
- Kriter Verili: {coverage.get('courses_with_criteria', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_criteria', 0) / coverage.get('total_courses', 1) * 100:.1f}%)  [ZORUNLU]
- Performans: {coverage.get('courses_with_performance', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_performance', 0) / coverage.get('total_courses', 1) * 100:.1f}%)  [ZORUNLU]
- Populerlik: {coverage.get('courses_with_popularity', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_popularity', 0) / coverage.get('total_courses', 1) * 100:.1f}%)  [ZORUNLU]
- Anket: {coverage.get('courses_with_survey', 0)} ders  [BİLGİ AMAÇLI — zorunlu değil, olgunluğu düşürmez]

Genel Kapsama (zorunlu veri): {coverage.get('coverage_percentage', 0):.1f}%

Sonuç: {'VERİ HAZIR - Karar alınabilir' if readiness.get('readiness_level') in ['good', 'decision_ready'] else 'VERİ EKSİK - Müfredat derslerinin kriterlerini tamamlayın'}
""",
        )

    def _update_coverage(self, coverage: dict):
        """Coverage sekmesini güncelle"""
        self.coverage_text.delete("1.0", tk.END)
        total = coverage.get("total_courses", 1)

        # Progress bars + yuzde etiketleri (0..100 araliginda kistirilir)
        bar_counts = {
            "criteria": coverage.get("courses_with_criteria", 0),
            "performance": coverage.get("courses_with_performance", 0),
            "popularity": coverage.get("courses_with_popularity", 0),
            "survey": coverage.get("courses_with_survey", 0),
        }
        for key, count in bar_counts.items():
            pct = (count / total * 100) if total > 0 else 0.0
            pct_clamped = max(0.0, min(100.0, pct))
            self.progress_bars[key].config(value=pct_clamped)
            label = self.progress_value_labels.get(key)
            if label is not None:
                label.config(text=f"{count} / {total}  (%{pct:.1f})")

        # Text
        self.coverage_text.insert(
            tk.END,
            f"""KAPSAMA RAPORU
================

Müfredat (zorunlu) ders: {coverage.get("required_courses", total)}   |   Fakülte toplam ders: {coverage.get("total_all_courses", total)}
Not: Kriter/Performans/Popülerlik yalnızca MÜFREDATTAKİ dersler için zorunludur.
Müfredat dışı (havuz) dersler eksik veri yüzünden olgunluğu DÜŞÜRMEZ.

Zorunlu Veri Kapsaması (payda = müfredat dersi = {total}):
- Kriter Verisi: {coverage.get("courses_with_criteria", 0)} / {total} ({total and coverage.get("courses_with_criteria", 0) / total * 100:.1f}%)
- Performans Verisi: {coverage.get("courses_with_performance", 0)} / {total} ({total and coverage.get("courses_with_performance", 0) / total * 100:.1f}%)
- Populerlik Verisi: {coverage.get("courses_with_popularity", 0)} / {total} ({total and coverage.get("courses_with_popularity", 0) / total * 100:.1f}%)

Anket Verisi (BİLGİ AMAÇLI — zorunlu değil): {coverage.get("courses_with_survey", 0)} ders
  Bir ders hiç seçilmemiş olabilir; anket eksikliği olgunluğu düşürmez.

Genel Kapsama Oranı (zorunlu veri): {coverage.get("coverage_percentage", 0):.1f}%

Eksik Veri Alanları:
""",
        )

        # List missing
        if total > 0:
            missing_criteria = total - coverage.get("courses_with_criteria", 0)
            missing_perf = total - coverage.get("courses_with_performance", 0)
            missing_pop = total - coverage.get("courses_with_popularity", 0)
            missing_survey = total - coverage.get("courses_with_survey", 0)

            if missing_criteria > 0:
                self.coverage_text.insert(tk.END, f"- {missing_criteria} derse kriter verisi eksik\n")
            if missing_perf > 0:
                self.coverage_text.insert(tk.END, f"- {missing_perf} derse performans verisi eksik\n")
            if missing_pop > 0:
                self.coverage_text.insert(tk.END, f"- {missing_pop} derse populerlik verisi eksik\n")
            if missing_survey > 0:
                self.coverage_text.insert(tk.END, f"- {missing_survey} derse anket verisi eksik\n")

    def _update_readiness(self, readiness: dict):
        """Readiness sekmesini güncelle"""
        score = readiness.get("readiness_score", 0)
        level = readiness.get("readiness_level", "Bilinmeyen")

        # Update label
        level_text = {
            "not_ready": "HAZIR DEĞİL",
            "low": "DÜŞÜK",
            "medium": "ORTA",
            "good": "İYİ",
            "decision_ready": "KARAR ALMALIYIZ",
        }.get(level, "Bilinmeyen")

        color = {
            "not_ready": "red",
            "low": "orange",
            "medium": "goldenrod",
            "good": "blue",
            "decision_ready": "green",
        }.get(level, "black")

        self.readiness_label.config(text=f"{level_text}\n({score:.1f}/100)", foreground=color)
        self.readiness_pb.config(value=score)

        # Text
        self.readiness_text.delete("1.0", tk.END)
        self.readiness_text.insert(
            tk.END,
            f"""VERİ OLGGUNLUĞU DEĞERLENDİRMESİ
====================================

Genel Hazırlık Skoru: {score:.1f}/100

Hazırlık Seviyesi: {level_text}

Bileşen Skorları:
- Kriter Tamlığı: {readiness.get("criteria_score", 0):.1f}/100
- Performans Verisi: {readiness.get("performance_score", 0):.1f}/100
- Populerlik Verisi: {readiness.get("popularity_score", 0):.1f}/100
- Anket Verisi: {readiness.get("survey_score", 0):.1f}/100
- Doğrulama Kalitesi: {readiness.get("validation_score", 0):.1f}/100

Tavsiyeler:
""",
        )

        if score < 50:
            self.readiness_text.insert(
                tk.END,
                """
⚠️  VERİ YETERSIZ: Karar almadan önce:
    1. Kriter verilerini gözden geçirin
    2. Eksik performans ve populerlik verilerini ekleyin
    3. Anket sonuçlarını güncelleyin
    4. Doğrulama işlemlerini tamamlayın
""",
            )
        elif score < 70:
            self.readiness_text.insert(
                tk.END,
                """
⚠️  VERİ KISMEN HAZIR: Daha iyi sonuç için:
    1. Eksik verileri tamamlamaya devam edin
    2. Doğrulama sorunlarını giderin
    3. Trend verileri kontrolünü yapın
""",
            )
        else:
            self.readiness_text.insert(
                tk.END,
                """
✓ VERİ YETERLI: Karar alma işlemlerine devam edebilirsiniz.
  Yüksek veri kalitesi ile güvenli kararlar alabilirsiniz.
""",
            )

    def _update_missing_data(self, rows: list[dict]):
        """Eksik Veri Matrisi sekmesini doldur (servis verisiyle)."""
        for item in self.missing_tree.get_children():
            self.missing_tree.delete(item)

        mark = lambda v: "✓" if v else "✗"
        for r in rows:
            crit = bool(r.get("criteria"))
            label = f"{r.get('kod','')} {r.get('ad','')}".strip() or f"#{r.get('ders_id')}"
            iid = self.missing_tree.insert(
                "", tk.END, text=label,
                values=(
                    mark(crit), mark(r.get("performance")), mark(r.get("popularity")),
                    mark(r.get("survey")), mark(r.get("trend")),
                ),
            )
            if not crit:
                self.missing_tree.item(iid, tags=("eksik",))
        self.missing_tree.tag_configure("eksik", background="#FFEBEE")
        if not rows:
            self.missing_tree.insert(
                "", tk.END, text="(Tüm dersler tam)",
                values=("✓", "✓", "✓", "✓", "✓"),
            )

    def _update_validation_issues(self, rows: list[dict], year: int):
        """Doğrulama Sorunları sekmesini doldur (servis verisiyle)."""
        for item in self.issues_tree.get_children():
            self.issues_tree.delete(item)

        if not rows:
            self.issues_tree.insert(
                "", tk.END, text="—",
                values=("", "TEMIZ", f"{year} yılı için doğrulama sorunu yok.", "", ""),
            )
            return

        for r in rows:
            severity = str(r.get("severity", ""))
            iid = self.issues_tree.insert(
                "", tk.END, text=str(r.get("id", "")),
                values=(
                    r.get("issue_type", ""), severity, r.get("message", ""),
                    r.get("key", ""), r.get("created_at", ""),
                ),
            )
            if severity.lower() == "critical":
                self.issues_tree.item(iid, tags=("critical",))
            elif severity.lower() == "warning":
                self.issues_tree.item(iid, tags=("warning",))
        self.issues_tree.tag_configure("critical", background="#FFCDD2")
        self.issues_tree.tag_configure("warning", background="#FFF3CD")

    def _refresh(self):
        """Sayfayı yenile"""
        self._refresh_db_path()
        self._populate_years()
        self._populate_faculties()
        if self.year_combo.get():
            self._generate_report()

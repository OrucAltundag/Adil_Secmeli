# -*- coding: utf-8 -*-
"""Veri Kalitesi Kontrol Paneli"""

from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from app.core.config import load_app_config
from app.db.sqlite_connection import connect_sqlite
from app.services.data_quality_integration_service import (
    assess_data_readiness_cursor,
    generate_coverage_report_cursor,
)


class DataQualityPage(ttk.Frame):
    """Veri kalitesi ve kapsama raporu"""

    def __init__(self, parent, app=None, db_path=None):
        super().__init__(parent)
        self.app = app
        self.db_path = db_path or (getattr(app, "db_path", None) if app else None)
        self.config = load_app_config() if not app else getattr(app, "app_config", load_app_config())
        self._setup_ui()

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

    def _build_summary_tab(self):
        """Veri Özeti sekmesi"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Veri Özeti")

        content = ttk.Frame(frame, padding=12)
        content.pack(fill=tk.BOTH, expand=True)

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

        # Progress bars
        metrics = [
            ("Kriter Kapsama", "criteria"),
            ("Performans Kapsama", "performance"),
            ("Populerlik Kapsama", "popularity"),
            ("Anket Kapsama", "survey"),
        ]

        self.progress_bars = {}
        for label, key in metrics:
            ttk.Label(content, text=label).pack(fill=tk.X, pady=(8, 2))
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
        """Akademik yılları doldur"""
        try:
            if not self.db_path:
                return
            conn = connect_sqlite(self.db_path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT akademik_yil FROM performans ORDER BY akademik_yil DESC")
                years = [str(row[0]) for row in cur.fetchall()]
                self.year_combo["values"] = years or ["2022", "2023", "2024"]
                if years:
                    self.year_combo.current(0)
            finally:
                conn.close()
        except Exception as e:
            print(f"Yıl yükleme hatası: {e}")

    def _populate_faculties(self):
        """Fakülteleri doldur"""
        try:
            if not self.db_path:
                return
            conn = connect_sqlite(self.db_path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
                faculties = [f"{row[1]} (ID: {row[0]})" for row in cur.fetchall()]
                self.faculty_combo["values"] = ["Tümü"] + faculties
                self.faculty_combo.current(0)
            finally:
                conn.close()
        except Exception as e:
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
        year_str = self.year_combo.get()
        if not year_str:
            messagebox.showwarning("Uyarı", "Lütfen akademik yıl seçin.")
            return

        try:
            year = int(year_str)
            faculty_id = self._get_selected_faculty_id()

            if not self.db_path:
                messagebox.showerror("Hata", "Veritabanı yolu ayarlanmamış.")
                return

            conn = connect_sqlite(self.db_path)
            try:
                cur = conn.cursor()

                # Readiness
                readiness = assess_data_readiness_cursor(cur, year, faculty_id)
                # Coverage
                coverage = generate_coverage_report_cursor(cur, year, faculty_id)

                # Update UI
                self._update_summary(readiness, coverage)
                self._update_coverage(coverage)
                self._update_readiness(readiness)

            finally:
                conn.close()

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
- Olgunluk Skoru: {readiness.get('readiness_score', 0):.1f}/100
- Hazırlık Seviyesi: {readiness.get('readiness_level', 'Bilinmeyen')}

Kapsama Oranları:
- Toplam Ders: {coverage.get('total_courses', 0)}
- Kriter Verili: {coverage.get('courses_with_criteria', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_criteria', 0) / coverage.get('total_courses', 1) * 100:.1f}%)
- Performans: {coverage.get('courses_with_performance', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_performance', 0) / coverage.get('total_courses', 1) * 100:.1f}%)
- Populerlik: {coverage.get('courses_with_popularity', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_popularity', 0) / coverage.get('total_courses', 1) * 100:.1f}%)
- Anket: {coverage.get('courses_with_survey', 0)} ({coverage.get('total_courses', 1) and coverage.get('courses_with_survey', 0) / coverage.get('total_courses', 1) * 100:.1f}%)

Genel Kapsama: {coverage.get('coverage_percentage', 0):.1f}%

Sonuç: {'VERİ HAZIR - Karar alınabilir' if readiness.get('readiness_level') in ['good', 'decision_ready'] else 'VERİ EKSİK - Lütfen veri tamamlayın'}
""",
        )

    def _update_coverage(self, coverage: dict):
        """Coverage sekmesini güncelle"""
        self.coverage_text.delete("1.0", tk.END)
        total = coverage.get("total_courses", 1)

        # Progress bars
        if total > 0:
            self.progress_bars["criteria"].config(value=(coverage.get("courses_with_criteria", 0) / total * 100))
            self.progress_bars["performance"].config(value=(coverage.get("courses_with_performance", 0) / total * 100))
            self.progress_bars["popularity"].config(value=(coverage.get("courses_with_popularity", 0) / total * 100))
            self.progress_bars["survey"].config(value=(coverage.get("courses_with_survey", 0) / total * 100))

        # Text
        self.coverage_text.insert(
            tk.END,
            f"""KAPSAMA RAPORU
================

Toplam Ders: {coverage.get("total_courses", 0)}

Detaylı Kapsama:
- Kriter Verisi: {coverage.get("courses_with_criteria", 0)} / {total} ({coverage.get("total_courses", 1) and coverage.get("courses_with_criteria", 0) / total * 100:.1f}%)
- Performans Verisi: {coverage.get("courses_with_performance", 0)} / {total} ({coverage.get("total_courses", 1) and coverage.get("courses_with_performance", 0) / total * 100:.1f}%)
- Populerlik Verisi: {coverage.get("courses_with_popularity", 0)} / {total} ({coverage.get("total_courses", 1) and coverage.get("courses_with_popularity", 0) / total * 100:.1f}%)
- Anket Verisi: {coverage.get("courses_with_survey", 0)} / {total} ({coverage.get("total_courses", 1) and coverage.get("courses_with_survey", 0) / total * 100:.1f}%)

Genel Kapsama Oranı: {coverage.get("coverage_percentage", 0):.1f}%

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

    def _refresh(self):
        """Sayfayı yenile"""
        self._generate_report()

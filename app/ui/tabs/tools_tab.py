# -*- coding: utf-8 -*-
"""
Rapor & Yukleme sekmesi.

Bolgeler:
1) Veri Yukleme (secili akademik yil)
2) Raporlama (havuz + mufredat)
3) Disa Aktarim (CSV/Excel)
"""

from __future__ import annotations

import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

import pandas as pd

<<<<<<< HEAD
from app.db.sqlite_connection import is_database_locked_error
=======
from app.db.sqlite_connection import connect_sqlite, is_database_locked_error
>>>>>>> b9e88394022006b16fd391988c0080a07e411942
from app.services.criteria_import_service import (
    FACULTY_SCOPE_LABEL,
    import_criteria_excel as run_criteria_import,
    normalize_department_scope_name,
    write_criteria_template_excel,
)
from app.services.curriculum_import_service import import_curriculum_excel as run_curriculum_import
from app.services.havuz_karar import mufredat_durumunu_esitle
from app.services.reporting_service import build_report_snapshot, ensure_report_scores
from app.services.system_service import SystemService
from app.services.survey_import_service import (
    import_survey_excel as run_survey_import,
    write_survey_template_excel,
)


class ToolsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db
        self.db_path = getattr(app, "db_path", None)

        self.cb_fakulte: ttk.Combobox | None = None
        self.cb_bolum: ttk.Combobox | None = None
        self.cb_yil: ttk.Combobox | None = None
        self.cb_donem: ttk.Combobox | None = None

        self.btn_import: ttk.Button | None = None
        self.btn_criteria_import: ttk.Button | None = None
        self.btn_criteria_template: ttk.Button | None = None
        self.btn_survey_import: ttk.Button | None = None
        self.btn_survey_template: ttk.Button | None = None
        self.lbl_import_state: ttk.Label | None = None

        self.lbl_pool_total: ttk.Label | None = None
        self.lbl_pool_avg: ttk.Label | None = None
        self.lbl_pool_rest: ttk.Label | None = None
        self.lbl_pool_chosen: ttk.Label | None = None
        self.lbl_pool_cancelled: ttk.Label | None = None
        self.lbl_criteria_source: ttk.Label | None = None

        self.tree_pool: ttk.Treeview | None = None
        self.tree_curr: ttk.Treeview | None = None
        self.txt_log: tk.Text | None = None

        self._last_pool_rows: list[dict] = []
        self._last_curr_rows: list[dict] = []

        self._build_ui()
        self.refresh()

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _db_ready(self) -> bool:
        return bool(getattr(self.db, "conn", None))

    def log(self, msg: str):
        if not self.txt_log:
            return
        self.txt_log.insert(tk.END, str(msg) + "\n")
        self.txt_log.see(tk.END)

    def _format_operation_error(self, exc: Exception) -> str:
        if is_database_locked_error(exc):
            return (
                "Veritabani su anda baska bir islem tarafindan kullaniliyor. "
                "Lutfen devam eden yukleme/rapor islemi bittikten sonra tekrar deneyin. "
                "Sorun surerse uygulamayi kapatip yeniden acin."
            )
        return str(exc)

    def _release_ui_db_connection(self) -> bool:
        """Close the long-lived UI connection before service-level write operations."""
        conn = getattr(self.db, "conn", None)
        if conn is None:
            return False
        try:
            try:
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            conn.close()
        finally:
            self.db.conn = None
        return True

    def _restore_ui_db_connection(self):
        self.db_path = getattr(self.app, "db_path", self.db_path)
        if self._db_ready() or not self.db_path or not os.path.exists(self.db_path):
            return
        self.db.connect(self.db_path)

    def _run_external_db_operation(self, operation):
        released = self._release_ui_db_connection()
        try:
            return operation()
        finally:
            if released:
                try:
                    self._restore_ui_db_connection()
                except Exception as exc:
                    self.log(f"Veritabani baglantisi yeniden acilamadi: {exc}")

    def _set_import_state_label(self, text: str):
        if self.lbl_import_state:
            self.lbl_import_state.config(text=text)

    def _selected_faculty_scope(self) -> tuple[int | None, str | None, int | None]:
        faculty_name = self.cb_fakulte.get().strip() if self.cb_fakulte else ""
        year = self._parse_year_text(self.cb_yil.get()) if self.cb_yil else None
        if not faculty_name or year is None or not self._db_ready():
            return None, (faculty_name or None), year
        try:
            _, rows = self.db.run_sql(
                "SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1",
                (faculty_name,),
            )
            if not rows:
                return None, faculty_name, year
            return int(rows[0][0]), faculty_name, int(year)
        except Exception:
            return None, faculty_name, year

    def _selected_department_name(self) -> str | None:
        return normalize_department_scope_name(self.cb_bolum.get() if self.cb_bolum else None)

    def _selected_department_id(self) -> int | None:
        department_name = self._selected_department_name()
        faculty_id, _, _ = self._selected_faculty_scope()
        if faculty_id is None or not department_name or not self._db_ready():
            return None
        try:
            _, rows = self.db.run_sql(
                "SELECT bolum_id FROM bolum WHERE fakulte_id = ? AND ad = ? LIMIT 1",
                (int(faculty_id), department_name),
            )
            if not rows:
                return None
            return int(rows[0][0])
        except Exception:
            return None

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------
    def _build_ui(self):
        # ---------- Filters ----------
        top = ttk.LabelFrame(self, text="Filtreler", padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Fakulte:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_fakulte = ttk.Combobox(top, state="readonly", width=30)
        self.cb_fakulte.pack(side=tk.LEFT, padx=(0, 12))
        self.cb_fakulte.bind("<<ComboboxSelected>>", self._on_faculty_change)

        ttk.Label(top, text="Bolum:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_bolum = ttk.Combobox(top, state="readonly", width=28)
        self.cb_bolum.pack(side=tk.LEFT, padx=(0, 12))
        self.cb_bolum.bind("<<ComboboxSelected>>", self._on_department_change)

        ttk.Label(top, text="Yil:").pack(side=tk.LEFT, padx=(0, 6))
        # Ilk mufredat yuklemesinde kullanicinin acikca yil yazabilmesi gerekir;
        # bu nedenle yillari DB'den oneriyoruz ama combobox'i yazilabilir tutuyoruz.
        self.cb_yil = ttk.Combobox(top, state="normal", width=10)
        self.cb_yil.pack(side=tk.LEFT, padx=(0, 12))
        self.cb_yil.bind("<<ComboboxSelected>>", self._on_year_change)
        self.cb_yil.bind("<Return>", self._commit_year_input)
        self.cb_yil.bind("<FocusOut>", self._commit_year_input)
        self.cb_yil.bind("<KeyRelease>", lambda _e: self._update_import_state())

        ttk.Label(top, text="Donem:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_donem = ttk.Combobox(top, state="readonly", width=10, values=["Guz", "Bahar"])
        self.cb_donem.pack(side=tk.LEFT, padx=(0, 12))
        self.cb_donem.current(0)
        self.cb_donem.bind("<<ComboboxSelected>>", lambda _e: self.load_report())

        ttk.Button(top, text="Rapor Getir", command=self.load_report).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Statu/Yil Esitle", command=self.sync_status_year).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="DB Yedekle", command=self.backup_db).pack(side=tk.LEFT, padx=4)

        # ---------- Zone A: Import ----------
        # Yıl kısıtlaması kaldırıldı - yükleme seçili yıl için yapılır
        self._import_zone = ttk.LabelFrame(self, text="A) Veri Yukleme", padding=10)
        self._import_zone.pack(fill=tk.X, pady=(8, 8))

        self.btn_import = ttk.Button(self._import_zone, text="Mufredat Excel Yukle", command=self.import_curriculum_excel)
        self.btn_import.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_criteria_template = ttk.Button(
            self._import_zone,
            text="Kriter Sablonu Indir",
            command=self.download_criteria_template,
        )
        self.btn_criteria_template.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_criteria_import = ttk.Button(
            self._import_zone,
            text="Kriter Dosyasi Yukle",
            command=self.import_criteria_excel,
        )
        self.btn_criteria_import.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_survey_template = ttk.Button(
            self._import_zone,
            text="Anket Sablonu Indir",
            command=self.download_survey_template,
        )
        self.btn_survey_template.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_survey_import = ttk.Button(
            self._import_zone,
            text="Anket Sonuclari Yukle",
            command=self.import_survey_excel,
        )
        self.btn_survey_import.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_import_state = ttk.Label(
            self._import_zone,
            text="Mufredat, kriter ve anket yukleme secili yil icin aktiftir.",
        )
        self.lbl_import_state.pack(side=tk.LEFT)

        # ---------- Zone B: Reporting ----------
        report_zone = ttk.LabelFrame(self, text="B) Raporlama", padding=8)
        report_zone.pack(fill=tk.BOTH, expand=True)

        summary = ttk.LabelFrame(report_zone, text="Ozet", padding=8)
        summary.pack(fill=tk.X, pady=(0, 8))

        self.lbl_pool_total = ttk.Label(summary, text="Havuz Toplam: -", width=24)
        self.lbl_pool_avg = ttk.Label(summary, text="Ortalama Skor: -", width=24)
        self.lbl_pool_rest = ttk.Label(summary, text="Dinlenmede(-1): -", width=20)
        self.lbl_pool_chosen = ttk.Label(summary, text="Mufredatta(1): -", width=20)
        self.lbl_pool_cancelled = ttk.Label(summary, text="Kalici Iptal(-2): -", width=20)

        self.lbl_pool_total.pack(side=tk.LEFT, padx=6)
        self.lbl_pool_avg.pack(side=tk.LEFT, padx=6)
        self.lbl_pool_rest.pack(side=tk.LEFT, padx=6)
        self.lbl_pool_chosen.pack(side=tk.LEFT, padx=6)
        self.lbl_pool_cancelled.pack(side=tk.LEFT, padx=6)
        self.lbl_criteria_source = ttk.Label(summary, text="Kriter Dosyasi: -")
        self.lbl_criteria_source.pack(fill=tk.X, padx=6, pady=(8, 0))

        paned = tk.PanedWindow(report_zone, orient=tk.HORIZONTAL, sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(paned, text="Havuz (Filtreli)", padding=6)
        right = ttk.LabelFrame(paned, text="Mufredat (Filtreli)", padding=6)
        paned.add(left, stretch="always")
        paned.add(right, stretch="always")

        pool_cols = ("ders_id", "ders_adi", "skor", "kaynak", "sayac", "statu", "yil")
        self.tree_pool = ttk.Treeview(left, columns=pool_cols, show="headings", height=16)
        self.tree_pool.pack(fill=tk.BOTH, expand=True)
        self.tree_pool.heading("ders_id", text="ID")
        self.tree_pool.heading("ders_adi", text="Ders Adi")
        self.tree_pool.heading("skor", text="Skor")
        self.tree_pool.heading("kaynak", text="Skor Kaynagi")
        self.tree_pool.heading("sayac", text="Sayac")
        self.tree_pool.heading("statu", text="Durum")
        self.tree_pool.heading("yil", text="Yil")
        self.tree_pool.column("ders_id", width=80, anchor="center")
        self.tree_pool.column("ders_adi", width=250)
        self.tree_pool.column("skor", width=80, anchor="center")
        self.tree_pool.column("kaynak", width=120, anchor="center")
        self.tree_pool.column("sayac", width=70, anchor="center")
        self.tree_pool.column("statu", width=130, anchor="center")
        self.tree_pool.column("yil", width=70, anchor="center")
        sb_pool = ttk.Scrollbar(left, orient="vertical", command=self.tree_pool.yview)
        self.tree_pool.configure(yscrollcommand=sb_pool.set)
        sb_pool.pack(side=tk.RIGHT, fill=tk.Y)

        curr_cols = ("ders_id", "ders_adi", "skor", "kaynak")
        self.tree_curr = ttk.Treeview(right, columns=curr_cols, show="headings", height=16)
        self.tree_curr.pack(fill=tk.BOTH, expand=True)
        self.tree_curr.heading("ders_id", text="ID")
        self.tree_curr.heading("ders_adi", text="Ders Adi")
        self.tree_curr.heading("skor", text="Skor")
        self.tree_curr.heading("kaynak", text="Skor Kaynagi")
        self.tree_curr.column("ders_id", width=80, anchor="center")
        self.tree_curr.column("ders_adi", width=260)
        self.tree_curr.column("skor", width=90, anchor="center")
        self.tree_curr.column("kaynak", width=120, anchor="center")
        sb_curr = ttk.Scrollbar(right, orient="vertical", command=self.tree_curr.yview)
        self.tree_curr.configure(yscrollcommand=sb_curr.set)
        sb_curr.pack(side=tk.RIGHT, fill=tk.Y)

        # ---------- Zone C: Export ----------
        bottom = ttk.LabelFrame(self, text="C) Disa Aktarim / Log", padding=8)
        bottom.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(bottom, text="Havuz CSV", command=lambda: self.export_current("pool", "csv")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Havuz Excel", command=lambda: self.export_current("pool", "xlsx")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Mufredat CSV", command=lambda: self.export_current("curr", "csv")).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Mufredat Excel", command=lambda: self.export_current("curr", "xlsx")).pack(side=tk.LEFT, padx=4)

        self.txt_log = tk.Text(bottom, height=6)
        self.txt_log.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(8, 0))

    # ---------------------------------------------------------
    # Data refresh
    # ---------------------------------------------------------
    def refresh(self):
        self.db_path = getattr(self.app, "db_path", self.db_path)
        if not self._db_ready():
            self._set_import_state_label("Veritabani baglantisi yok. Veritabani secildiginde aktif olur.")
            self._clear_views()
            return

        self._fill_faculties()
        self._fill_years()
        self._update_import_state()
        self.load_report()

    def _clear_views(self):
        if self.tree_pool:
            self.tree_pool.delete(*self.tree_pool.get_children())
        if self.tree_curr:
            self.tree_curr.delete(*self.tree_curr.get_children())

    def _parse_year_text(self, raw: str | None) -> int | None:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            year = int(text)
        except Exception:
            return None
        return year if year > 0 else None

    def _merge_year_values(self, years: list[str], extra_year: int | None = None) -> list[str]:
        merged = {str(int(y)) for y in years if self._parse_year_text(y) is not None}
        if extra_year is not None:
            merged.add(str(int(extra_year)))
        return sorted(merged, key=lambda item: int(item))

    def _commit_year_input(self, _event=None):
        if not self.cb_yil:
            return
        year = self._parse_year_text(self.cb_yil.get())
        if year is not None:
            merged = self._merge_year_values(list(self.cb_yil.cget("values") or []), year)
            self.cb_yil["values"] = merged
            self.cb_yil.set(str(year))
        self._update_import_state()
        self.load_report()

    def _fill_years(self):
        """Yil listesi: secili fakultenin gercek mufredat yillari (global sabit aralik yok)."""
        if not self.cb_yil or not self._db_ready():
            return
        try:
            current_year = self._parse_year_text(self.cb_yil.get())
            faculty_name = self.cb_fakulte.get() if self.cb_fakulte else ""
            if not faculty_name:
                self.cb_yil["values"] = []
                if current_year is None:
                    self.cb_yil.set("")
                return
            _, fid_rows = self.db.run_sql(
                "SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1",
                (faculty_name,),
            )
            if not fid_rows:
                self.cb_yil["values"] = []
                if current_year is None:
                    self.cb_yil.set("")
                return
            faculty_id = int(fid_rows[0][0])
            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT m.akademik_yil
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ?
                ORDER BY m.akademik_yil
                """,
                (faculty_id,),
            )
            years = [str(int(r[0])) for r in (rows or []) if r and r[0] is not None]
            if not years:
                # Ilk mufredat yuklemesi: henuz kayit yok; tek onerilen yil (sabit aralik degil)
                years = [str(datetime.datetime.now().year)]
            years = self._merge_year_values(years, current_year)
            self.cb_yil["values"] = years
            if current_year is not None:
                self.cb_yil.set(str(current_year))
            elif self.cb_yil.get() not in years:
                self.cb_yil.set(years[-1])
        except Exception as exc:
            self.log(f"Yil listesi yuklenemedi: {exc}")

    def _fill_faculties(self):
        if not self.cb_fakulte or not self._db_ready():
            return
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte ORDER BY ad")
            faculties = [str(r[0]) for r in (rows or []) if r and r[0] is not None]
            self.cb_fakulte["values"] = faculties
            if faculties and self.cb_fakulte.get() not in faculties:
                self.cb_fakulte.set(faculties[0])
                self._on_faculty_change(None)
        except Exception as exc:
            self.log(f"Fakulte listesi yuklenemedi: {exc}")

    def _on_faculty_change(self, _event):
        if not self._db_ready() or not self.cb_fakulte or not self.cb_bolum:
            return
        faculty_name = self.cb_fakulte.get()
        if not faculty_name:
            return
        try:
            _, fid_rows = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1", (faculty_name,))
            if not fid_rows:
                return
            faculty_id = int(fid_rows[0][0])
            _, bol_rows = self.db.run_sql(
                "SELECT ad FROM bolum WHERE fakulte_id = ? ORDER BY ad",
                (faculty_id,),
            )
            departments = [FACULTY_SCOPE_LABEL]
            departments.extend(str(r[0]) for r in (bol_rows or []) if r and r[0] is not None)
            self.cb_bolum["values"] = departments
            if self.cb_bolum.get() not in departments:
                self.cb_bolum.set(FACULTY_SCOPE_LABEL)
        except Exception as exc:
            self.log(f"Bolum listesi yuklenemedi: {exc}")
        finally:
            self._fill_years()
            self._update_import_state()
            self.load_report()

    def _on_year_change(self, _event):
        self._update_import_state()
        self.load_report()

    def _on_department_change(self, _event):
        self._update_import_state()
        self.load_report()

    def _update_import_state(self):
        """Yükleme durumunu günceller - artık yıl kısıtlaması yok, seçili yıl için yükleme yapılır."""
        year = self.cb_yil.get() if self.cb_yil else ""
        parsed_year = self._parse_year_text(year)
        # Yıl kısıtlaması kaldırıldı - yükleme her zaman aktif (DB bağlantısı varsa)
        active = self._db_ready() and parsed_year is not None
        if self.btn_import:
            self.btn_import.config(state=("normal" if active else "disabled"))
        criteria_active = active and bool((self.cb_fakulte.get() if self.cb_fakulte else "").strip())
        if self.btn_criteria_import:
            self.btn_criteria_import.config(state=("normal" if criteria_active else "disabled"))
        if self.btn_criteria_template:
            self.btn_criteria_template.config(state=("normal" if criteria_active else "disabled"))
        survey_active = active and bool((self.cb_fakulte.get() if self.cb_fakulte else "").strip())
        if self.btn_survey_import:
            self.btn_survey_import.config(state=("normal" if survey_active else "disabled"))
        if self.btn_survey_template:
            self.btn_survey_template.config(state=("normal" if survey_active else "disabled"))
        # Zone başlığını dinamik güncelle
        if hasattr(self, "_import_zone") and self._import_zone:
            self._import_zone.config(text=f"A) Veri Yukleme ({year})" if year else "A) Veri Yukleme")
        if not self._db_ready():
            self._set_import_state_label("Veritabani baglantisi yok.")
        elif year and parsed_year is None:
            self._set_import_state_label("Gecerli bir akademik yil giriniz.")
        elif not criteria_active:
            self._set_import_state_label("Kriter ve anket yukleme icin fakulte ve yil seciniz.")
        elif active:
            scope_text = self._selected_department_name() or FACULTY_SCOPE_LABEL
            self._set_import_state_label(f"Yukleme aktif: {scope_text} / {parsed_year}.")

    # ---------------------------------------------------------
    # Reporting
    # ---------------------------------------------------------
    def load_report(self):
        if not self._db_ready():
            return
        if not self.cb_fakulte or not self.cb_yil:
            return

        faculty_name = self.cb_fakulte.get()
        year_raw = self.cb_yil.get()
        term = self.cb_donem.get() if self.cb_donem else "Guz"
        department_name = self._selected_department_name()

        if not faculty_name or not year_raw:
            return
        try:
            year = int(year_raw)
        except Exception:
            return

        try:
            _, fid_rows = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1", (faculty_name,))
            if not fid_rows:
                self.log(f"Fakulte bulunamadi: {faculty_name}")
                return
            faculty_id = int(fid_rows[0][0])
        except Exception as exc:
            self.log(f"Fakulte cozumleme hatasi: {exc}")
            return

        score_result = ensure_report_scores(self.db, faculty_id, year, term)
        if not score_result.get("ok"):
            self.log(f"Skor guncelleme uyarisi: {score_result.get('reason')}")

        try:
            snapshot = build_report_snapshot(
                db=self.db,
                faculty_id=faculty_id,
                faculty_name=faculty_name,
                year=year,
                term=term,
                department_name=department_name or None,
            )
        except Exception as exc:
            self.log(f"Rapor olusturma hatasi: {exc}")
            return

        self._last_pool_rows = list(snapshot.get("pool_rows") or [])
        self._last_curr_rows = list(snapshot.get("curriculum_rows") or [])
        self._render_snapshot(snapshot)

    def _render_snapshot(self, snapshot: dict[str, Any]):
        if self.tree_pool:
            self.tree_pool.delete(*self.tree_pool.get_children())
            for row in self._last_pool_rows:
                score_text = "-" if row.get("skor") is None else f"{float(row['skor']):.2f}"
                self.tree_pool.insert(
                    "",
                    tk.END,
                    values=(
                        row.get("ders_id"),
                        row.get("ders_adi"),
                        score_text,
                        row.get("kaynak"),
                        row.get("sayac"),
                        row.get("statu"),
                        row.get("yil"),
                    ),
                )

        if self.tree_curr:
            self.tree_curr.delete(*self.tree_curr.get_children())
            for row in self._last_curr_rows:
                score_text = "-" if row.get("skor") is None else f"{float(row['skor']):.2f}"
                self.tree_curr.insert(
                    "",
                    tk.END,
                    values=(row.get("ders_id"), row.get("ders_adi"), score_text, row.get("kaynak")),
                )

        stats = snapshot.get("stats") or {}
        if self.lbl_pool_total:
            self.lbl_pool_total.config(text=f"Havuz Toplam: {stats.get('total', 0)}")
        if self.lbl_pool_avg:
            avg_score = stats.get("avg_score")
            self.lbl_pool_avg.config(text=f"Ortalama Skor: {'-' if avg_score is None else f'{float(avg_score):.2f}'}")
        if self.lbl_pool_rest:
            self.lbl_pool_rest.config(text=f"Dinlenmede(-1): {stats.get('rest_count', 0)}")
        if self.lbl_pool_chosen:
            self.lbl_pool_chosen.config(text=f"Mufredatta(1): {stats.get('chosen_count', 0)}")
        if self.lbl_pool_cancelled:
            self.lbl_pool_cancelled.config(text=f"Kalici Iptal(-2): {stats.get('cancelled_count', 0)}")
        if self.lbl_criteria_source:
            summary = snapshot.get("criteria_import_summary") or {}
            self.lbl_criteria_source.config(text=f"Kriter Dosyasi: {summary.get('display', '-')}")

        for note in snapshot.get("notes", []):
            self.log(note)

    # ---------------------------------------------------------
    # Zone A - Import
    # ---------------------------------------------------------
    def download_criteria_template(self):
        if not self._db_ready():
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return

        faculty_id, faculty_name, year = self._selected_faculty_scope()
        department_id = self._selected_department_id()
        department_name = self._selected_department_name()
        term = self.cb_donem.get() if self.cb_donem else "Guz"
        if faculty_id is None or year is None or not faculty_name:
            messagebox.showwarning("Uyari", "Once fakulte ve akademik yil seciniz.")
            return

        scope_label = department_name or FACULTY_SCOPE_LABEL
        default_name = f"kriter_sablonu_{faculty_name}_{scope_label}_{year}_{term}.xlsx".replace(" ", "_")
        target_path = filedialog.asksaveasfilename(
            title="Kriter Sablonunu Kaydet",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel", "*.xlsx"), ("Tum dosyalar", "*.*")],
        )
        if not target_path:
            return

        try:
            self._run_external_db_operation(
                lambda: write_criteria_template_excel(
                    target_path=target_path,
                    faculty_name=faculty_name,
                    department_name=department_name,
                    year=year,
                    term=term,
                    db_path=self.db_path,
                    faculty_id=faculty_id,
                    department_id=department_id,
                )
            )
            self.log(f"Kriter sablonu yazildi: {target_path}")
            messagebox.showinfo("Tamam", "Kriter sablonu olusturuldu.")
        except Exception as exc:
            self.log(f"Kriter sablonu olusturma hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))

    def import_criteria_excel(self):
        if not self._db_ready():
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return
        if not self.db_path or not os.path.exists(self.db_path):
            messagebox.showwarning("Uyari", "Veritabani dosyasi bulunamadi.")
            return

        faculty_id, faculty_name, year = self._selected_faculty_scope()
        department_id = self._selected_department_id()
        department_name = self._selected_department_name()
        term = self.cb_donem.get() if self.cb_donem else "Guz"
        if faculty_id is None or year is None or not faculty_name:
            messagebox.showwarning("Uyari", "Once fakulte ve akademik yil seciniz.")
            return

        excel_path = filedialog.askopenfilename(
            title="Kriter Excel sec",
            filetypes=[("Excel", "*.xlsx"), ("Tum dosyalar", "*.*")],
        )
        if not excel_path:
            return

        try:
            result = self._run_external_db_operation(
                lambda: run_criteria_import(
                    db_path=self.db_path,
                    excel_path=excel_path,
                    faculty_id=faculty_id,
                    year=year,
                    term=term,
                    department_id=department_id,
                    source_filename=os.path.basename(excel_path),
                )
            )
        except Exception as exc:
            self.log(f"Kriter yukleme hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))
            return
        if result.get("ok"):
            scope_text = department_name or FACULTY_SCOPE_LABEL
            self.log("Kriter yukleme basarili:")
            self.log(result.get("message", ""))
            self.log(
                f" - Kapsam: {faculty_name} / {scope_text} / {year} / {term}"
            )
            self.log(
                f" - Eslesen ders: {result.get('matched_count', 0)} | "
                f"Guncellenen kriter: {result.get('updated_course_count', 0)} | "
                f"Yeni kriter satiri: {result.get('created_course_count', 0)}"
            )
            replace = result.get("replace") or {}
            self.log(
                f" - Onceki ayni kapsam supersede edildi: import={replace.get('previous_imports_superseded', 0)} "
                f"kriter_reset={replace.get('criteria_rows_reset', 0)} "
                f"performans_silindi={replace.get('performance_rows_deleted', 0)} "
                f"populerlik_silindi={replace.get('popularity_rows_deleted', 0)}"
            )
            if int(result.get("skipped_department_overrides") or 0) > 0:
                self.log(
                    f" - Fakulte geneli importta daha ozel bolum override'lari korundu: "
                    f"{result.get('skipped_department_overrides')}"
                )
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showinfo("Tamam", result.get("message", "Kriter yukleme tamamlandi."))
            self.refresh()
            try:
                self.app.tab_calc.refresh(force_reload=True)
            except Exception:
                pass
            try:
                self.app.tab_view.refresh()
            except Exception:
                pass
        else:
            self.log("Kriter yukleme basarisiz:")
            self.log(result.get("message", ""))
            self.log(
                f" - Eslesen ders: {result.get('matched_count', 0)} | "
                f"Eslesemeyen satir: {result.get('unmatched_count', 0)}"
            )
            for err in result.get("errors", []):
                self.log(f"Hata: {err}")
            for row in result.get("unmatched_rows", [])[:30]:
                self.log(
                    f" - Eslesemedi (satir {row.get('row_no')}): "
                    f"kod={row.get('ders_kodu')} ad={row.get('ders_adi')} neden={row.get('error_message')}"
                )
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showerror("Hata", result.get("message", "Kriter yukleme basarisiz."))

    def download_survey_template(self):
        if not self._db_ready():
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return

        faculty_id, faculty_name, year = self._selected_faculty_scope()
        if faculty_id is None or year is None:
            messagebox.showwarning("Uyari", "Once fakulte ve akademik yil seciniz.")
            return

        default_name = f"anket_sablonu_{faculty_name}_{year}.xlsx".replace(" ", "_")
        target_path = filedialog.asksaveasfilename(
            title="Anket Sablonunu Kaydet",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel", "*.xlsx"), ("Tum dosyalar", "*.*")],
        )
        if not target_path:
            return

        try:
            self._run_external_db_operation(
                lambda: write_survey_template_excel(
                    target_path=target_path,
                    faculty_name=faculty_name,
                    year=year,
                    db_path=self.db_path,
                    faculty_id=faculty_id,
                )
            )
            self.log(f"Anket sablonu yazildi: {target_path}")
            messagebox.showinfo("Tamam", "Anket sablonu olusturuldu.")
        except Exception as exc:
            self.log(f"Anket sablonu olusturma hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))

    def import_curriculum_excel(self):
        if not self._db_ready():
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return
        if not self.cb_yil or not (self.cb_yil.get() or "").strip():
            messagebox.showwarning("Uyari", "Once akademik yil seciniz.")
            return
        try:
            target_year = int(self.cb_yil.get())
        except Exception:
            messagebox.showwarning("Uyari", "Gecerli bir akademik yil seciniz.")
            return
        if not self.db_path or not os.path.exists(self.db_path):
            messagebox.showwarning("Uyari", "Veritabani dosyasi bulunamadi.")
            return

        excel_path = filedialog.askopenfilename(
            title="Mufredat Excel sec",
            filetypes=[("Excel", "*.xlsx"), ("Tum dosyalar", "*.*")],
        )
        if not excel_path:
            return

        try:
            result = self._run_external_db_operation(
                lambda: run_curriculum_import(
                    db_path=self.db_path,
                    excel_path=excel_path,
                    target_year=target_year,
                )
            )
        except Exception as exc:
            self.log(f"Yukleme hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))
            return
        if result.get("ok"):
            self.log("Yukleme basarili:")
            self.log(result.get("message", ""))
            for comp in result.get("compare", [])[:30]:
                self.log(
                    f" - {comp['fakulte']} / {comp['bolum']} / {comp['yil']} / {comp['donem']} -> "
                    f"same={comp['same']} add={comp['added_count']} remove={comp['removed_count']}"
                )
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showinfo("Tamam", result.get("message", "Yukleme tamamlandi."))
            self.refresh()
            try:
                self.app.tab_calc.refresh(force_reload=True)
            except Exception:
                pass
        else:
            self.log("Yukleme basarisiz:")
            self.log(result.get("message", ""))
            for err in result.get("errors", []):
                self.log(f"Hata: {err}")
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showerror("Hata", result.get("message", "Yukleme basarisiz."))

    def import_survey_excel(self):
        if not self._db_ready():
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return
        if not self.db_path or not os.path.exists(self.db_path):
            messagebox.showwarning("Uyari", "Veritabani dosyasi bulunamadi.")
            return

        faculty_id, faculty_name, year = self._selected_faculty_scope()
        if faculty_id is None or year is None or not faculty_name:
            messagebox.showwarning("Uyari", "Once fakulte ve akademik yil seciniz.")
            return

        excel_path = filedialog.askopenfilename(
            title="Anket Excel sec",
            filetypes=[("Excel", "*.xlsx"), ("Tum dosyalar", "*.*")],
        )
        if not excel_path:
            return

        try:
            result = self._run_external_db_operation(
                lambda: run_survey_import(
                    db_path=self.db_path,
                    excel_path=excel_path,
                    faculty_id=faculty_id,
                    year=year,
                    source_filename=os.path.basename(excel_path),
                )
            )
        except Exception as exc:
            self.log(f"Anket yukleme hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))
            return
        if result.get("ok"):
            self.log("Anket yukleme basarili:")
            self.log(result.get("message", ""))
            self.log(
                f" - Fakulte: {faculty_name} | Yil: {year} | Toplam katilimci: {result.get('total_participants', 0)}"
            )
            self.log(
                f" - Eslesen ders: {result.get('matched_count', 0)} | "
                f"Guncellenen kriter: {result.get('updated_course_count', 0)} | "
                f"Yeni kriter satiri: {result.get('created_course_count', 0)}"
            )
            replace = result.get("replace") or {}
            self.log(
                f" - Onceki anket verileri temizlendi: import={replace.get('previous_import_deleted', 0)} "
                f"satir={replace.get('previous_rows_deleted', 0)} kriter_reset={replace.get('criteria_rows_reset', 0)}"
            )
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showinfo("Tamam", result.get("message", "Anket yukleme tamamlandi."))
            self.refresh()
            try:
                self.app.tab_calc.refresh(force_reload=True)
            except Exception:
                pass
            try:
                self.app.tab_view.refresh()
            except Exception:
                pass
            try:
                if hasattr(self.app, "tab_calc") and hasattr(self.app.tab_calc, "criteria_view"):
                    self.app.tab_calc.criteria_view.load_courses()
            except Exception:
                pass
        else:
            self.log("Anket yukleme basarisiz:")
            self.log(result.get("message", ""))
            self.log(
                f" - Eslesen ders: {result.get('matched_count', 0)} | "
                f"Eslesemeyen satir: {result.get('unmatched_count', 0)}"
            )
            for err in result.get("errors", []):
                self.log(f"Hata: {err}")
            for row in result.get("unmatched_rows", [])[:30]:
                self.log(
                    f" - Eslesemedi (satir {row.get('row_no')}): "
                    f"kod={row.get('ders_kodu')} ad={row.get('ders_adi')} neden={row.get('error_message')}"
                )
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showerror("Hata", result.get("message", "Anket yukleme basarisiz."))

    # ---------------------------------------------------------
    # Zone B - Actions
    # ---------------------------------------------------------
    def sync_status_year(self):
        if not self._db_ready() or not self.db_path:
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return
        if not messagebox.askyesno("Onay", "Statu/Yil esitleme calistirilsin mi?"):
            return

        try:
            _, rows = self.db.run_sql(
                """
                SELECT MIN(yil), MAX(yil)
                FROM (
                    SELECT yil FROM havuz
                    UNION
                    SELECT akademik_yil AS yil FROM mufredat
                )
                """
            )
            if not rows or rows[0][0] is None:
                messagebox.showwarning("Uyari", "Havuz veya mufredat icin yil bulunamadi.")
                return
            min_yil = int(rows[0][0])
            max_yil = int(rows[0][1]) if rows[0][1] is not None else min_yil
            self._run_external_db_operation(
                lambda: mufredat_durumunu_esitle(
                    self.db_path,
                    baslangic_yili=min_yil,
                    bitis_yili=max_yil,
                )
            )
            self.log("Statu/Yil esitleme tamamlandi.")
            self.load_report()
            messagebox.showinfo("Tamam", "Statu/Yil esitleme tamamlandi.")
        except Exception as exc:
            self.log(f"Statu/Yil esitleme hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))

    def backup_db(self):
        if not self.db_path or not os.path.exists(self.db_path):
            messagebox.showwarning("Uyari", "Yedeklenecek veritabani bulunamadi.")
            return

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"adil_secmeli_backup_{ts}.db"
        target = filedialog.asksaveasfilename(
            title="DB Yedek Kaydet",
            defaultextension=".db",
            initialfile=default_name,
            filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("Tum dosyalar", "*.*")],
        )
        if not target:
            return

        try:
            def _backup():
<<<<<<< HEAD
                SystemService(db_path=self.db_path).backup_database(target, source_path=self.db_path).unwrap()
=======
                source = connect_sqlite(self.db_path)
                target_conn = connect_sqlite(target)
                try:
                    source.backup(target_conn)
                finally:
                    target_conn.close()
                    source.close()
>>>>>>> b9e88394022006b16fd391988c0080a07e411942

            self._run_external_db_operation(_backup)
            self.log(f"DB yedeklendi: {target}")
            messagebox.showinfo("Tamam", "Yedek alindi.")
        except Exception as exc:
            self.log(f"DB yedekleme hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))

    # ---------------------------------------------------------
    # Zone C - Export
    # ---------------------------------------------------------
    def export_current(self, which: str, fmt: str):
        rows = self._last_pool_rows if which == "pool" else self._last_curr_rows
        if not rows:
            messagebox.showwarning("Uyari", "Disa aktarilacak veri yok.")
            return

        if which == "pool":
            df = pd.DataFrame(rows, columns=["ders_id", "ders_adi", "skor", "kaynak", "sayac", "statu", "yil"])
            default_name = f"havuz_{self.cb_yil.get() if self.cb_yil else 'rapor'}.{fmt}"
        else:
            df = pd.DataFrame(rows, columns=["ders_id", "ders_adi", "skor", "kaynak"])
            default_name = f"mufredat_{self.cb_yil.get() if self.cb_yil else 'rapor'}.{fmt}"

        path = filedialog.asksaveasfilename(
            title="Disa Aktar",
            defaultextension=f".{fmt}",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("Tum dosyalar", "*.*")],
        )
        if not path:
            return

        try:
            if fmt == "csv":
                df.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                df.to_excel(path, index=False)
            self.log(f"Export tamamlandi: {path}")
            messagebox.showinfo("Tamam", "Disa aktarim tamamlandi.")
        except Exception as exc:
            self.log(f"Export hatasi: {exc}")
            messagebox.showerror("Hata", self._format_operation_error(exc))

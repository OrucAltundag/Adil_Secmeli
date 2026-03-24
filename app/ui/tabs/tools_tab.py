# -*- coding: utf-8 -*-
"""
Rapor & Yukleme sekmesi.

Bolgeler:
1) Veri Yukleme (2022)
2) Raporlama (havuz + mufredat)
3) Disa Aktarim (CSV/Excel)
"""

from __future__ import annotations

import datetime
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

import pandas as pd

from app.services.curriculum_import_service import import_curriculum_excel as run_curriculum_import
from app.services.havuz_karar import muhendislik_mufredat_durumunu_esitle
from app.services.reporting_service import build_report_snapshot, ensure_report_scores


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
        self.lbl_import_state: ttk.Label | None = None

        self.lbl_pool_total: ttk.Label | None = None
        self.lbl_pool_avg: ttk.Label | None = None
        self.lbl_pool_rest: ttk.Label | None = None
        self.lbl_pool_chosen: ttk.Label | None = None
        self.lbl_pool_cancelled: ttk.Label | None = None

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

    def _set_import_state_label(self, text: str):
        if self.lbl_import_state:
            self.lbl_import_state.config(text=text)

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
        self.cb_bolum.bind("<<ComboboxSelected>>", lambda _e: self.load_report())

        ttk.Label(top, text="Yil:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_yil = ttk.Combobox(top, state="readonly", width=10)
        self.cb_yil.pack(side=tk.LEFT, padx=(0, 12))
        self.cb_yil.bind("<<ComboboxSelected>>", self._on_year_change)

        ttk.Label(top, text="Donem:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_donem = ttk.Combobox(top, state="readonly", width=10, values=["Guz", "Bahar"])
        self.cb_donem.pack(side=tk.LEFT, padx=(0, 12))
        self.cb_donem.current(0)
        self.cb_donem.bind("<<ComboboxSelected>>", lambda _e: self.load_report())

        ttk.Button(top, text="Rapor Getir", command=self.load_report).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Statu/Yil Esitle", command=self.sync_status_year).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="DB Yedekle", command=self.backup_db).pack(side=tk.LEFT, padx=4)

        # ---------- Zone A: Import ----------
        import_zone = ttk.LabelFrame(self, text="A) Veri Yukleme (2022)", padding=10)
        import_zone.pack(fill=tk.X, pady=(8, 8))

        self.btn_import = ttk.Button(import_zone, text="Excel Sec ve Yukle", command=self.import_curriculum_excel)
        self.btn_import.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_import_state = ttk.Label(
            import_zone,
            text="Yukleme yalnizca yil=2022 seciminde aktiftir.",
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

        self._fill_years()
        self._fill_faculties()
        self._update_import_state()
        self.load_report()

    def _clear_views(self):
        if self.tree_pool:
            self.tree_pool.delete(*self.tree_pool.get_children())
        if self.tree_curr:
            self.tree_curr.delete(*self.tree_curr.get_children())

    def _fill_years(self):
        if not self.cb_yil or not self._db_ready():
            return
        try:
            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT yil FROM (
                    SELECT yil FROM havuz
                    UNION
                    SELECT akademik_yil AS yil FROM mufredat
                )
                WHERE yil IS NOT NULL
                ORDER BY yil
                """
            )
            years = [str(r[0]) for r in (rows or [])]
            if not years:
                years = [str(datetime.datetime.now().year)]
            self.cb_yil["values"] = years
            if self.cb_yil.get() not in years:
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
            departments = [str(r[0]) for r in (bol_rows or []) if r and r[0] is not None]
            self.cb_bolum["values"] = departments
            if departments and self.cb_bolum.get() not in departments:
                self.cb_bolum.set(departments[0])
        except Exception as exc:
            self.log(f"Bolum listesi yuklenemedi: {exc}")
        finally:
            self.load_report()

    def _on_year_change(self, _event):
        self._update_import_state()
        self.load_report()

    def _update_import_state(self):
        year = self.cb_yil.get() if self.cb_yil else ""
        active = self._db_ready() and year == "2022"
        if self.btn_import:
            self.btn_import.config(state=("normal" if active else "disabled"))
        if not self._db_ready():
            self._set_import_state_label("Veritabani baglantisi yok.")
        elif active:
            self._set_import_state_label("Yukleme aktif: 2022 secili.")
        else:
            self._set_import_state_label("Yukleme pasif: yalnizca 2022 yilinda aktif.")

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
        department_name = self.cb_bolum.get() if self.cb_bolum else None

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

        for note in snapshot.get("notes", []):
            self.log(note)

    # ---------------------------------------------------------
    # Zone A - Import
    # ---------------------------------------------------------
    def import_curriculum_excel(self):
        if not self._db_ready():
            messagebox.showwarning("Uyari", "Veritabani baglantisi yok.")
            return
        if not self.cb_yil or self.cb_yil.get() != "2022":
            messagebox.showwarning("Kisit", "Yukleme sadece 2022 yili seciliyken aktiftir.")
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

        result = run_curriculum_import(db_path=self.db_path, excel_path=excel_path, target_year=2022)
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
        else:
            self.log("Yukleme basarisiz:")
            self.log(result.get("message", ""))
            for err in result.get("errors", []):
                self.log(f"Hata: {err}")
            for warn in result.get("warnings", []):
                self.log(f"Uyari: {warn}")
            messagebox.showerror("Hata", result.get("message", "Yukleme basarisiz."))

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
            min_yil = int(rows[0][0]) if rows and rows[0][0] is not None else 2022
            max_yil = int(rows[0][1]) if rows and rows[0][1] is not None else min_yil
            muhendislik_mufredat_durumunu_esitle(
                self.db_path,
                baslangic_yili=min_yil,
                bitis_yili=max_yil,
            )
            self.log("Statu/Yil esitleme tamamlandi.")
            self.load_report()
            messagebox.showinfo("Tamam", "Statu/Yil esitleme tamamlandi.")
        except Exception as exc:
            self.log(f"Statu/Yil esitleme hatasi: {exc}")
            messagebox.showerror("Hata", str(exc))

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
            shutil.copy2(self.db_path, target)
            self.log(f"DB yedeklendi: {target}")
            messagebox.showinfo("Tamam", "Yedek alindi.")
        except Exception as exc:
            self.log(f"DB yedekleme hatasi: {exc}")
            messagebox.showerror("Hata", str(exc))

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
            messagebox.showerror("Hata", str(exc))

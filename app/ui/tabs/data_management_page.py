# -*- coding: utf-8 -*-
"""Veri Yönetimi merkezi: import, kalite, diff, onay ve rollback işlemleri."""

from __future__ import annotations

import json
import os
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

from app.db.session import open_sqlite_connection
from app.services.data_management_center_service import (
    execute_import_request,
    get_dashboard_context,
    get_import_bundle,
    get_import_type_specs,
    recalculate_import_artifact,
    write_import_template,
)
from app.services.import_audit_service import (
    activate_import,
    approve_import,
    list_import_batches,
    reject_import,
)
from app.services.import_quality_service import evaluate_import_quality
from app.services.import_rollback_service import get_rollback_plan, rollback_import


class DataManagementPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: Any | None = None):
        super().__init__(parent)
        self.app = app
        self.selected_import_batch_id: int | None = None
        self._faculty_options: dict[str, int | None] = {"Tumu": None}
        self._department_options: dict[str, int | None] = {"Tumu": None}
        self._import_type_options: dict[str, str] = {}
        self._suppress_filter_events = False
        self._build_ui()
        self.refresh_center()

    def _db_path(self) -> str | None:
        path = getattr(self.app, "db_path", None)
        return os.path.abspath(path) if path else None

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Sistem şu anda işlem yapamıyor. Lütfen veritabanı ve dosya bilgilerini kontrol edin."

    def _connect(self) -> sqlite3.Connection:
        path = self._db_path()
        if not path or not os.path.exists(path):
            raise FileNotFoundError(self._friendly_backend_error())
        return open_sqlite_connection(path, row_factory=True)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Veri Yönetimi Merkezi", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(top, text="Yenile", command=self.refresh_center).pack(side=tk.RIGHT, padx=4)
        self.status_var = tk.StringVar(value="Veri yönetimi yükleniyor.")
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        filter_bar = ttk.Frame(self, padding=(8, 0, 8, 6))
        filter_bar.pack(fill=tk.X)
        ttk.Label(filter_bar, text="Yıl").pack(side=tk.LEFT)
        self.year_combo = ttk.Combobox(filter_bar, width=10, state="readonly")
        self.year_combo.pack(side=tk.LEFT, padx=(4, 12))
        self.year_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(filter_bar, text="Fakülte").pack(side=tk.LEFT)
        self.faculty_combo = ttk.Combobox(filter_bar, width=30, state="readonly")
        self.faculty_combo.pack(side=tk.LEFT, padx=(4, 12))
        self.faculty_combo.bind("<<ComboboxSelected>>", self._on_faculty_change)

        ttk.Label(filter_bar, text="Bölüm").pack(side=tk.LEFT)
        self.department_combo = ttk.Combobox(filter_bar, width=30, state="readonly")
        self.department_combo.pack(side=tk.LEFT, padx=(4, 12))
        self.department_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.dashboard_tab = ttk.Frame(self.nb, padding=8)
        self.import_tab = ttk.Frame(self.nb, padding=8)
        self.history_tab = ttk.Frame(self.nb, padding=8)
        self.detail_tab = ttk.Frame(self.nb, padding=8)
        self.rows_tab = ttk.Frame(self.nb, padding=8)
        self.quality_tab = ttk.Frame(self.nb, padding=8)
        self.diff_tab = ttk.Frame(self.nb, padding=8)
        self.rollback_tab = ttk.Frame(self.nb, padding=8)
        self.impact_tab = ttk.Frame(self.nb, padding=8)

        self.nb.add(self.dashboard_tab, text="Merkez")
        self.nb.add(self.import_tab, text="Yeni Import")
        self.nb.add(self.history_tab, text="Import Geçmişi")
        self.nb.add(self.detail_tab, text="Import Detayı")
        self.nb.add(self.rows_tab, text="Satır Sonuçları")
        self.nb.add(self.quality_tab, text="Kalite Kontrol")
        self.nb.add(self.diff_tab, text="Diff / Karşılaştırma")
        self.nb.add(self.rollback_tab, text="Rollback & Onay")
        self.nb.add(self.impact_tab, text="Karar Etkisi")

        self._build_dashboard_tab()
        self._build_import_tab()
        self._build_history_tab()
        self._build_text_tabs()

    def _build_dashboard_tab(self) -> None:
        cards = ttk.LabelFrame(self.dashboard_tab, text="Veri Durumu", padding=10)
        cards.pack(fill=tk.X)
        self.dashboard_labels: dict[str, ttk.Label] = {}
        items = [
            ("Toplam Ders", "total_courses"),
            ("Genel Kapsama", "coverage"),
            ("Olgunluk", "readiness"),
            ("Kriter Eksik", "missing_criteria"),
            ("Anket Eksik", "missing_survey"),
            ("Son Import", "latest_import"),
        ]
        for idx, (label, key) in enumerate(items):
            ttk.Label(cards, text=f"{label}:").grid(row=idx // 3, column=(idx % 3) * 2, sticky=tk.W, padx=6, pady=5)
            value = ttk.Label(cards, text="-", foreground="#0B5CAD")
            value.grid(row=idx // 3, column=(idx % 3) * 2 + 1, sticky=tk.W, padx=6, pady=5)
            self.dashboard_labels[key] = value

        body = ttk.Frame(self.dashboard_tab)
        body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        left = ttk.LabelFrame(body, text="Tamamlanacak Veri", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        cols = ("type", "missing")
        self.missing_tree = ttk.Treeview(left, columns=cols, show="headings", height=8)
        self.missing_tree.heading("type", text="Veri Tipi")
        self.missing_tree.heading("missing", text="Eksik Ders")
        self.missing_tree.column("type", width=180, anchor=tk.W)
        self.missing_tree.column("missing", width=90, anchor=tk.CENTER)
        self.missing_tree.pack(fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(body, text="Sıradaki İşler", padding=8)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.action_text = ScrolledText(right, height=8, wrap=tk.WORD)
        self.action_text.pack(fill=tk.BOTH, expand=True)
        self.action_text.configure(state=tk.DISABLED)

        latest = ttk.LabelFrame(self.dashboard_tab, text="Son Importlar", padding=8)
        latest.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        latest_cols = ("id", "type", "file", "status", "quality", "uploaded")
        self.latest_tree = ttk.Treeview(latest, columns=latest_cols, show="headings", height=6)
        for col, text, width in (
            ("id", "ID", 60),
            ("type", "Tür", 100),
            ("file", "Dosya", 260),
            ("status", "Durum", 110),
            ("quality", "Kalite", 90),
            ("uploaded", "Yükleme", 160),
        ):
            self.latest_tree.heading(col, text=text)
            self.latest_tree.column(col, width=width, anchor=tk.W)
        self.latest_tree.pack(fill=tk.BOTH, expand=True)
        self.latest_tree.bind("<Double-1>", self._open_latest_import)

    def _build_import_tab(self) -> None:
        form = ttk.LabelFrame(self.import_tab, text="Dosya Yükle", padding=10)
        form.pack(fill=tk.X)

        ttk.Label(form, text="Veri tipi").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.import_type_combo = ttk.Combobox(form, width=34, state="readonly")
        self.import_type_combo.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)
        self.import_type_combo.bind("<<ComboboxSelected>>", self._update_import_requirements)

        ttk.Label(form, text="Excel dosyası").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.file_path_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.file_path_var, width=70).grid(row=1, column=1, sticky=tk.EW, padx=4, pady=4)
        ttk.Button(form, text="Seç", command=self._select_import_file).grid(row=1, column=2, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="Yıl").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        self.import_year_combo = ttk.Combobox(form, width=10, state="readonly")
        self.import_year_combo.grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text="Dönem").grid(row=2, column=1, sticky=tk.W, padx=(120, 4), pady=4)
        self.term_combo = ttk.Combobox(form, width=10, state="readonly", values=("Guz", "Bahar"))
        self.term_combo.current(0)
        self.term_combo.grid(row=2, column=1, sticky=tk.W, padx=(170, 4), pady=4)

        self.auto_activate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Kalite uygunsa aktif yap", variable=self.auto_activate_var).grid(
            row=2, column=2, sticky=tk.W, padx=4, pady=4
        )

        ttk.Button(form, text="Şablon Oluştur", command=self._write_template).grid(row=3, column=0, sticky=tk.W, padx=4, pady=8)
        ttk.Button(form, text="Importu Başlat", command=self._run_import).grid(row=3, column=1, sticky=tk.W, padx=4, pady=8)
        form.columnconfigure(1, weight=1)

        req = ttk.LabelFrame(self.import_tab, text="Seçili Veri Tipi", padding=8)
        req.pack(fill=tk.X, pady=(8, 0))
        self.requirements_text = tk.Text(req, height=5, wrap=tk.WORD)
        self.requirements_text.pack(fill=tk.X)
        self.requirements_text.configure(state=tk.DISABLED)

        result = ttk.LabelFrame(self.import_tab, text="Import Sonucu", padding=8)
        result.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.import_result_text = self._make_text(result, height=14)

        self._load_import_type_options()

    def _build_history_tab(self) -> None:
        toolbar = ttk.Frame(self.history_tab)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="Geçmişi Yenile", command=self.refresh_imports).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Seçili Importu Aç", command=self.load_selected_import).pack(side=tk.LEFT, padx=4)

        columns = (
            "id",
            "type",
            "filename",
            "year",
            "faculty",
            "department",
            "semester",
            "status",
            "quality",
            "level",
            "rows",
            "uploaded",
            "duplicate",
        )
        self.history_tree = ttk.Treeview(self.history_tab, columns=columns, show="headings", height=18)
        headers = {
            "id": "ID",
            "type": "Tür",
            "filename": "Dosya",
            "year": "Yıl",
            "faculty": "Fakülte",
            "department": "Bölüm",
            "semester": "Dönem",
            "status": "Durum",
            "quality": "Kalite",
            "level": "Seviye",
            "rows": "Satır",
            "uploaded": "Yükleme",
            "duplicate": "Duplicate",
        }
        for col in columns:
            self.history_tree.heading(col, text=headers[col])
            self.history_tree.column(col, width=105 if col != "filename" else 240, anchor=tk.W)
        self.history_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(self.history_tab, orient=tk.VERTICAL, command=self.history_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)
        self.history_tree.bind("<Double-1>", lambda _event: self.load_selected_import())

    def _build_text_tabs(self) -> None:
        self.detail_text = self._make_text(self.detail_tab)
        self.rows_text = self._make_text(self.rows_tab)

        quality_top = ttk.Frame(self.quality_tab)
        quality_top.pack(fill=tk.X)
        ttk.Button(quality_top, text="Kaliteyi Yeniden Hesapla", command=self.recalculate_quality).pack(side=tk.LEFT)
        self.quality_text = self._make_text(self.quality_tab)

        diff_top = ttk.Frame(self.diff_tab)
        diff_top.pack(fill=tk.X)
        ttk.Button(diff_top, text="Diff Hesapla", command=self.recalculate_diff).pack(side=tk.LEFT)
        self.diff_text = self._make_text(self.diff_tab)

        rb_top = ttk.Frame(self.rollback_tab)
        rb_top.pack(fill=tk.X)
        ttk.Button(rb_top, text="Onayla", command=self.approve_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(rb_top, text="Aktif Yap", command=self.activate_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(rb_top, text="Reddet", command=self.reject_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(rb_top, text="Rollback Planı", command=self.load_rollback_plan).pack(side=tk.LEFT, padx=2)
        ttk.Button(rb_top, text="Geri Al", command=self.rollback_selected).pack(side=tk.LEFT, padx=2)
        self.rollback_text = self._make_text(self.rollback_tab)

        impact_top = ttk.Frame(self.impact_tab)
        impact_top.pack(fill=tk.X)
        ttk.Button(impact_top, text="Etki Raporu Hesapla", command=self.recalculate_impact).pack(side=tk.LEFT)
        self.impact_text = self._make_text(self.impact_tab)

    def _make_text(self, parent: tk.Misc, height: int = 24) -> ScrolledText:
        text = ScrolledText(parent, height=height, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, pady=6)
        text.configure(state=tk.DISABLED)
        return text

    def _set_text(self, widget: tk.Text | ScrolledText, value: Any) -> None:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value or "")
        widget.configure(state=tk.DISABLED)

    def _load_import_type_options(self) -> None:
        specs = get_import_type_specs()
        self._import_type_options = {item["label"]: item["key"] for item in specs}
        self.import_type_combo["values"] = list(self._import_type_options.keys())
        if specs:
            self.import_type_combo.current(0)
        self._update_import_requirements()

    def refresh_center(self) -> None:
        path = self._db_path()
        if not path:
            self.status_var.set("Veritabanı seçilmedi.")
            return
        try:
            year = self._selected_year(default=None)
            faculty_id = self._selected_faculty_id()
            department_id = self._selected_department_id()
            context = get_dashboard_context(path, year=year, faculty_id=faculty_id, department_id=department_id)
            self._populate_filter_values(context)
            self._update_dashboard(context)
            self.refresh_imports()
            self.status_var.set("Veri yönetimi güncellendi.")
        except Exception:
            self.status_var.set("Veri yönetimi yüklenemedi.")
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

    def _populate_filter_values(self, context: dict[str, Any]) -> None:
        self._suppress_filter_events = True
        try:
            selected_year = str(context.get("selected_year") or "")
            years = [str(item) for item in context.get("years") or []]
            self.year_combo["values"] = years
            self.import_year_combo["values"] = years
            if selected_year and selected_year in years:
                self.year_combo.set(selected_year)
                if not self.import_year_combo.get():
                    self.import_year_combo.set(selected_year)
            elif years:
                self.year_combo.current(0)
                if not self.import_year_combo.get():
                    self.import_year_combo.current(0)

            current_faculty = self.faculty_combo.get()
            self._faculty_options = {"Tumu": None}
            for item in context.get("faculties") or []:
                self._faculty_options[f"{item['name']} (ID: {item['id']})"] = int(item["id"])
            self.faculty_combo["values"] = list(self._faculty_options.keys())
            self.faculty_combo.set(current_faculty if current_faculty in self._faculty_options else "Tumu")

            current_department = self.department_combo.get()
            self._department_options = {"Tumu": None}
            for item in context.get("departments") or []:
                self._department_options[f"{item['name']} (ID: {item['id']})"] = int(item["id"])
            self.department_combo["values"] = list(self._department_options.keys())
            self.department_combo.set(current_department if current_department in self._department_options else "Tumu")
        finally:
            self._suppress_filter_events = False

    def _update_dashboard(self, context: dict[str, Any]) -> None:
        coverage = context.get("coverage") or {}
        readiness = context.get("readiness") or {}
        missing = context.get("missing") or {}
        latest = context.get("latest_imports") or []

        self.dashboard_labels["total_courses"].config(text=str(coverage.get("total_courses", 0)))
        self.dashboard_labels["coverage"].config(text=f"{float(coverage.get('coverage_percentage') or 0):.1f}%")
        self.dashboard_labels["readiness"].config(text=f"{float(readiness.get('readiness_score') or 0):.1f}/100")
        self.dashboard_labels["missing_criteria"].config(text=str(missing.get("criteria", 0)))
        self.dashboard_labels["missing_survey"].config(text=str(missing.get("survey", 0)))
        self.dashboard_labels["latest_import"].config(text=str(latest[0].get("uploaded_at") or latest[0].get("created_at") or "-") if latest else "-")

        for item in self.missing_tree.get_children():
            self.missing_tree.delete(item)
        labels = {
            "criteria": "Kriter / Performans",
            "performance": "Performans",
            "popularity": "Populerlik",
            "survey": "Anket",
            "trend": "Trend",
        }
        for key, label in labels.items():
            self.missing_tree.insert("", tk.END, values=(label, int(missing.get(key, 0))))

        self._set_text(self.action_text, "\n".join(f"- {item}" for item in context.get("next_actions") or []))

        for item in self.latest_tree.get_children():
            self.latest_tree.delete(item)
        for row in latest:
            self.latest_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("id"),
                    row.get("import_type") or "",
                    row.get("original_filename") or "",
                    row.get("status") or "",
                    row.get("quality_score") if row.get("quality_score") is not None else "",
                    row.get("uploaded_at") or row.get("created_at") or "",
                ),
            )

    def refresh_imports(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            with self._connect() as conn:
                rows = list_import_batches(conn, limit=500)
            if not rows:
                self.status_var.set("Henüz import kaydı yok.")
                return
            for row in rows:
                self.history_tree.insert(
                    "",
                    tk.END,
                    values=(
                        row.get("id"),
                        row.get("import_type"),
                        row.get("original_filename") or "",
                        row.get("year") or "",
                        row.get("faculty_id") or "",
                        row.get("department_id") or "",
                        row.get("semester") or "",
                        row.get("status") or "",
                        row.get("quality_score") if row.get("quality_score") is not None else "",
                        row.get("quality_level") or "",
                        row.get("row_count") or 0,
                        row.get("uploaded_at") or row.get("created_at") or "",
                        "Evet" if row.get("duplicate_of_import_batch_id") else "",
                    ),
                )
            self.status_var.set(f"{len(rows)} import kaydı listelendi.")
        except Exception:
            self.status_var.set("Import geçmişi yüklenemedi.")
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

    def _on_filter_change(self, _event: Any = None) -> None:
        if not self._suppress_filter_events:
            self.refresh_center()

    def _on_faculty_change(self, _event: Any = None) -> None:
        if self._suppress_filter_events:
            return
        self.department_combo.set("Tumu")
        self.refresh_center()

    def _selected_year(self, default: int | None = 2022) -> int | None:
        value = self.year_combo.get() or self.import_year_combo.get()
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _selected_import_year(self) -> int:
        value = self.import_year_combo.get() or self.year_combo.get() or "2022"
        try:
            return int(value)
        except ValueError:
            return 2022

    def _selected_faculty_id(self) -> int | None:
        return self._faculty_options.get(self.faculty_combo.get())

    def _selected_department_id(self) -> int | None:
        return self._department_options.get(self.department_combo.get())

    def _selected_import_type(self) -> str:
        return self._import_type_options.get(self.import_type_combo.get(), "criteria")

    def _select_import_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Excel dosyası seç",
            filetypes=[("Excel dosyaları", "*.xlsx *.xls"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            self.file_path_var.set(path)

    def _write_template(self) -> None:
        path = self._db_path()
        if not path:
            messagebox.showerror("Şablon", "Veritabanı seçilmedi.")
            return
        default_name = f"{self._selected_import_type()}_sablon_{self._selected_import_year()}.xlsx"
        target_path = filedialog.asksaveasfilename(
            title="Şablon dosyası oluştur",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel dosyaları", "*.xlsx")],
        )
        if not target_path:
            return
        try:
            result = write_import_template(
                db_path=path,
                import_type=self._selected_import_type(),
                target_path=target_path,
                year=self._selected_import_year(),
                faculty_id=self._selected_faculty_id(),
                department_id=self._selected_department_id(),
                term=self.term_combo.get() or "Guz",
            )
            self._set_text(self.import_result_text, result)
            if result.get("ok"):
                messagebox.showinfo("Şablon", result.get("message") or "Şablon oluşturuldu.")
            else:
                messagebox.showwarning("Şablon", result.get("message") or "Şablon oluşturulamadı.")
        except Exception:
            messagebox.showerror("Şablon", self._friendly_backend_error())

    def _update_import_requirements(self, _event: Any = None) -> None:
        selected = self._selected_import_type()
        specs = {item["key"]: item for item in get_import_type_specs()}
        spec = specs.get(selected, {})
        columns = ", ".join(spec.get("expected_columns") or [])
        text = (
            f"{spec.get('label', selected)}\n"
            f"Kapsam: {spec.get('required_scope', '-')}\n"
            f"Beklenen kolonlar: {columns}\n"
            f"Not: Import sonucu kalite kontrol, diff ve karar etkisi otomatik kaydedilir."
        )
        self._set_text(self.requirements_text, text)

    def _run_import(self) -> None:
        path = self._db_path()
        excel_path = self.file_path_var.get().strip()
        if not path:
            messagebox.showerror("Import", "Veritabanı seçilmedi.")
            return
        if not excel_path:
            messagebox.showwarning("Import", "Önce Excel dosyası seçin.")
            return
        if not messagebox.askyesno("Import", "Seçili dosya veritabanına aktarılsın mı?"):
            return
        try:
            result = execute_import_request(
                db_path=path,
                import_type=self._selected_import_type(),
                excel_path=excel_path,
                year=self._selected_import_year(),
                faculty_id=self._selected_faculty_id(),
                department_id=self._selected_department_id(),
                term=self.term_combo.get() or "Guz",
                auto_activate=bool(self.auto_activate_var.get()),
                uploaded_by="desktop-ui",
            )
            self._set_text(self.import_result_text, result)
            batch_id = result.get("import_batch_id")
            if batch_id:
                self.selected_import_batch_id = int(batch_id)
                self.load_selected_import()
                self.nb.select(self.detail_tab)
            self.refresh_center()
            self._refresh_related_views()
            if result.get("ok"):
                messagebox.showinfo("Import", result.get("message") or "Import tamamlandı.")
            else:
                messagebox.showwarning("Import", result.get("message") or "Import tamamlanamadı.")
        except Exception:
            messagebox.showerror("Import", self._friendly_backend_error())

    def _refresh_related_views(self) -> None:
        if not self.app:
            return
        for attr, method_name in (
            ("tab_data_quality", "_refresh"),
            ("tab_calc", "refresh"),
            ("tab_tools", "refresh"),
            ("tab_view", "refresh"),
        ):
            target = getattr(self.app, attr, None)
            method = getattr(target, method_name, None)
            if not callable(method):
                continue
            try:
                method()
            except TypeError:
                try:
                    method(force_reload=True)
                except Exception:
                    pass
            except Exception:
                pass

    def _open_latest_import(self, _event: Any = None) -> None:
        selected = self.latest_tree.selection()
        if not selected:
            return
        values = self.latest_tree.item(selected[0], "values")
        if not values:
            return
        self.selected_import_batch_id = int(values[0])
        self.load_selected_import()
        self.nb.select(self.detail_tab)

    def _on_history_select(self, _event: Any = None) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        values = self.history_tree.item(selected[0], "values")
        if not values:
            return
        self.selected_import_batch_id = int(values[0])

    def load_selected_import(self) -> None:
        import_batch_id = self.selected_import_batch_id
        if import_batch_id is None:
            selected = self.history_tree.selection()
            if selected:
                values = self.history_tree.item(selected[0], "values")
                import_batch_id = int(values[0]) if values else None
                self.selected_import_batch_id = import_batch_id
        if import_batch_id is None:
            messagebox.showinfo("Veri Yönetimi", "Önce bir import seçin.")
            return
        try:
            path = self._db_path()
            if not path:
                raise FileNotFoundError(self._friendly_backend_error())
            bundle = get_import_bundle(path, int(import_batch_id))
            self._set_text(self.detail_text, bundle.get("batch") or {})
            self._set_text(self.rows_text, {"rows": bundle.get("rows") or [], "issues": bundle.get("issues") or []})
            self._set_text(self.quality_text, bundle.get("quality") or {})
            self._set_text(
                self.diff_text,
                bundle.get("diff") or "Bu import için henüz diff raporu yok. 'Diff Hesapla' butonunu kullanın.",
            )
            self._set_text(self.rollback_text, bundle.get("rollback") or {})
            self._set_text(self.impact_text, bundle.get("impact") or "Bu import için henüz karar etkisi raporu yok.")
        except Exception:
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

    def recalculate_quality(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Kalite", "Önce bir import seçin.")
            return
        try:
            with self._connect() as conn:
                quality = evaluate_import_quality(conn, self.selected_import_batch_id)
                conn.commit()
            self._set_text(self.quality_text, quality.as_dict())
            self.refresh_center()
        except Exception:
            messagebox.showerror("Kalite", self._friendly_backend_error())

    def recalculate_diff(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Diff", "Önce bir import seçin.")
            return
        try:
            path = self._db_path()
            if not path:
                raise FileNotFoundError(self._friendly_backend_error())
            diff = recalculate_import_artifact(path, self.selected_import_batch_id, "diff")
            self._set_text(self.diff_text, diff)
            self.refresh_center()
        except Exception:
            messagebox.showerror("Diff", self._friendly_backend_error())

    def recalculate_impact(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Karar Etkisi", "Önce bir import seçin.")
            return
        try:
            path = self._db_path()
            if not path:
                raise FileNotFoundError(self._friendly_backend_error())
            impact = recalculate_import_artifact(path, self.selected_import_batch_id, "impact")
            self._set_text(self.impact_text, impact)
            self.refresh_center()
        except Exception:
            messagebox.showerror("Karar Etkisi", self._friendly_backend_error())

    def load_rollback_plan(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Rollback", "Önce bir import seçin.")
            return
        try:
            with self._connect() as conn:
                plan = get_rollback_plan(conn, self.selected_import_batch_id)
            self._set_text(self.rollback_text, plan)
        except Exception:
            messagebox.showerror("Rollback", self._friendly_backend_error())

    def approve_selected(self) -> None:
        self._status_action(lambda conn, batch_id: approve_import(conn, batch_id, approved_by="desktop-ui"), "Import onaylandı.")

    def activate_selected(self) -> None:
        self._status_action(lambda conn, batch_id: activate_import(conn, batch_id, user="desktop-ui"), "Import aktif yapıldı.")

    def reject_selected(self) -> None:
        self._status_action(
            lambda conn, batch_id: reject_import(conn, batch_id, reason="UI uzerinden reddedildi.", rejected_by="desktop-ui"),
            "Import reddedildi.",
        )

    def rollback_selected(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Rollback", "Önce bir import seçin.")
            return
        if not messagebox.askyesno("Rollback", "Seçili import geri alınsın mı? Bu işlem ilgili importu pasifler."):
            return
        self._status_action(
            lambda conn, batch_id: rollback_import(conn, batch_id, reason="UI uzerinden rollback.", user="desktop-ui"),
            "Import geri alındı.",
        )

    def _status_action(self, func: Any, success_message: str) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Veri Yönetimi", "Önce bir import seçin.")
            return
        try:
            with self._connect() as conn:
                result = func(conn, self.selected_import_batch_id)
                evaluate_import_quality(conn, self.selected_import_batch_id)
                conn.commit()
            messagebox.showinfo("Veri Yönetimi", success_message)
            self.refresh_center()
            self.load_selected_import()
            self._set_text(self.rollback_text, result)
            self._refresh_related_views()
        except Exception:
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

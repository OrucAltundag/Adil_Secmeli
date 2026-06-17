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
    export_student_criteria_dataset,
    generate_criteria_from_student_dataset,
    get_dashboard_context,
    get_import_bundle,
    get_import_type_specs,
    recalculate_import_artifact,
    write_import_template,
)
from app.services.criteria_import_service import apply_pending_criteria_import
from app.services.import_audit_service import (
    activate_import,
    approve_import,
    list_import_batches,
    reject_import,
)
from app.services.import_history_service import cleanup_import_history, preview_cleanup
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

    # ------------------------------------------------------------------
    # Uzun ömürlü UI bağlantısını yazma işlemlerinden önce serbest bırakma.
    #
    # Bu ekran import/temizleme/onay için KENDİ kısa ömürlü yazıcı bağlantısını
    # açar. Aynı anda uygulamanın uzun ömürlü `app.db.conn` bağlantısı bir
    # okuma/işlem snapshot'ı tutuyorsa, SQLite tek-yazıcı kısıtı yüzünden
    # yazıcı bağlantı busy_timeout (8sn) boyunca BEKLER (UI donar) ve ardından
    # "database is locked" hatası verir. `tools_tab` aynı sorunu bu release/
    # restore deseniyle çözüyor; aynı deseni burada da uyguluyoruz.
    # ------------------------------------------------------------------
    def _release_ui_db_connection(self) -> bool:
        """Servis-seviyesi yazma işleminden önce uzun ömürlü UI bağlantısını kapatır."""
        db = getattr(self.app, "db", None)
        conn = getattr(db, "conn", None)
        if db is None or conn is None:
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
            try:
                db.conn = None
            except Exception:
                pass
        return True

    def _restore_ui_db_connection(self) -> None:
        db = getattr(self.app, "db", None)
        path = self._db_path()
        if db is None or not path or not os.path.exists(path):
            return
        try:
            db.connect(path)
        except Exception:
            pass

    def _run_external_db_operation(self, operation: Any) -> Any:
        """Uzun ömürlü UI bağlantısını bırakıp `operation()` çağırır; sonra geri açar."""
        released = self._release_ui_db_connection()
        try:
            return operation()
        finally:
            if released:
                self._restore_ui_db_connection()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Veri Yönetimi Merkezi", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(top, text="Yenile", command=self.refresh_center).pack(side=tk.RIGHT, padx=4)
        # §7: Teknik sekmeler (Import Detayı / Satır Sonuçları) varsayılan gizli;
        # geliştirici/admin görünümünde açılır. Bilgi silinmez, yalnız gizlenir.
        self.developer_view_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top,
            text="Geliştirici görünümü",
            variable=self.developer_view_var,
            command=self._apply_developer_view,
        ).pack(side=tk.RIGHT, padx=8)
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
        self._apply_developer_view()

    def _apply_developer_view(self) -> None:
        """§7: Import Detayı + Satır Sonuçları sekmelerini geliştirici görünümüne göre aç/gizle."""
        state = "normal" if self.developer_view_var.get() else "hidden"
        for tab in (getattr(self, "detail_tab", None), getattr(self, "rows_tab", None)):
            if tab is None:
                continue
            try:
                self.nb.tab(tab, state=state)
            except Exception:
                pass

    def _select_inspect_tab(self) -> None:
        """İncele/aç sonrası: geliştirici görünümünde Detay, normalde Kalite sekmesini seç."""
        target = self.detail_tab if self.developer_view_var.get() else self.quality_tab
        try:
            self.nb.select(target)
        except Exception:
            pass

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
        self.file_path_var.trace_add("write", self._on_file_path_change)
        self._file_entry = ttk.Entry(form, textvariable=self.file_path_var, width=70)
        self._file_entry.grid(row=1, column=1, sticky=tk.EW, padx=4, pady=4)
        ttk.Button(form, text="Seç", command=self._select_import_file).grid(row=1, column=2, sticky=tk.W, padx=4, pady=4)

        # Import artık YILLIK çalışır; ayrı Güz/Bahar dönem seçimi kaldırıldı.
        # Dönem bilgisi (gerekliyse) dosyadan okunur veya backend varsayılanını
        # kullanır; eski kayıtlar etkilenmez.
        ttk.Label(form, text="Akademik yıl").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        self.import_year_combo = ttk.Combobox(form, width=10, state="readonly")
        self.import_year_combo.grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)

        self.auto_activate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Kalite uygunsa aktif yap", variable=self.auto_activate_var).grid(
            row=2, column=2, sticky=tk.W, padx=4, pady=4
        )

        # Bu import hangi kapsama uygulanacak? (üst filtreden okunur — net görünsün)
        self.scope_indicator_var = tk.StringVar(value="")
        ttk.Label(form, textvariable=self.scope_indicator_var, foreground="#0B5CAD").grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=4, pady=(2, 0)
        )
        self.import_year_combo.bind("<<ComboboxSelected>>", self._update_scope_indicator)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=8)
        self._btn_template = ttk.Button(btn_frame, text="Şablon Oluştur", command=self._write_template)
        self._btn_template.pack(side=tk.LEFT, padx=(0, 6))
        # §3: öğrenci-kriter modunda gösterilen özel buton (başlangıçta gizli).
        self._btn_student_dataset = ttk.Button(
            btn_frame, text="Kriter Veri Seti İndir", command=self._export_student_criteria
        )
        self._btn_import = ttk.Button(btn_frame, text="Importu Başlat", command=self._run_import, state="disabled")
        self._btn_import.pack(side=tk.LEFT, padx=(0, 6))
        self._import_status_lbl = ttk.Label(btn_frame, text="", foreground="#64748b")
        self._import_status_lbl.pack(side=tk.LEFT, padx=6)
        form.columnconfigure(1, weight=1)

        req = ttk.LabelFrame(self.import_tab, text="Seçili Veri Tipi", padding=8)
        req.pack(fill=tk.X, pady=(8, 0))
        self.requirements_text = tk.Text(req, height=9, wrap=tk.WORD)
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
        ttk.Button(toolbar, text="Import Kaydını İncele", command=self.load_selected_import).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Import Geçmişini Temizle", command=self.cleanup_import_history_action).pack(side=tk.RIGHT)
        ttk.Label(
            toolbar,
            text="(Eski/tamamlanmış kayıtlar arşivlenir; aktif, onaylı ve karara bağlı kayıtlar korunur.)",
            foreground="#64748b",
        ).pack(side=tk.RIGHT, padx=8)

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
        self._update_scope_indicator()

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

    def cleanup_import_history_action(self) -> None:
        """Import geçmişini güvenli şekilde temizler (arşivler).

        Önce kaç kaydın temizleneceği/korunacağı gösterilir, onay alınır; sonra
        terminal kayıtlar arşiv tablosuna taşınır. Gerçek veri silinmez.
        """
        # Uzun ömürlü UI bağlantısını bırak: arşivleme yazıcısı kilide takılıp
        # UI'yi dondurmasın. İşlem (önizleme + onay diyaloğu + arşivleme) boyunca
        # bağlantı kapalı kalır, sonunda yeniden açılır.
        released = self._release_ui_db_connection()
        try:
            try:
                with self._connect() as conn:
                    preview = preview_cleanup(conn)
            except Exception:
                messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())
                return

            cleanable = int(preview.get("cleanable_count", 0))
            protected = int(preview.get("protected_count", 0))
            if cleanable == 0:
                messagebox.showinfo(
                    "Import Geçmişini Temizle",
                    f"Temizlenecek eski import kaydı yok.\n{protected} aktif/korunan kayıt mevcut.",
                )
                return
            if not messagebox.askyesno(
                "Import Geçmişini Temizle",
                "Import geçmişini temizlemek üzeresiniz. Bu işlem eski/tamamlanmış import "
                "kayıtlarını arşivleyecek (ekrandan kaldıracak) ve ilgili işlem loglarını "
                "temizleyecektir.\n\n"
                f"  • Arşivlenecek kayıt : {cleanable}\n"
                f"  • Korunacak kayıt    : {protected} (aktif / onaylı / karara bağlı)\n\n"
                "Gerçek ders, havuz, müfredat ve skor verileri ETKİLENMEZ.\n\n"
                "Onaylıyor musunuz?",
                icon="warning",
            ):
                return
            try:
                with self._connect() as conn:
                    result = cleanup_import_history(conn, user="desktop-ui")
                    conn.commit()
            except Exception:
                messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())
                return
        finally:
            if released:
                self._restore_ui_db_connection()
        self.refresh_center()
        self.status_var.set(result.get("message") or "Import geçmişi temizlendi.")
        messagebox.showinfo("Import Geçmişini Temizle", result.get("message") or "Import geçmişi temizlendi.")

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

    def _import_term(self) -> str | None:
        """Import artık yıllık; dönem seçimi yok. Dönem dosyadan ya da backend
        varsayılanından (``term or "Guz"``) gelir."""
        return None

    def _on_file_path_change(self, *_args: Any) -> None:
        path = self.file_path_var.get().strip()
        has_file = bool(path and os.path.exists(path))
        btn = getattr(self, "_btn_import", None)
        if btn:
            btn.configure(state="normal" if has_file else "disabled")
        lbl = getattr(self, "_import_status_lbl", None)
        if lbl:
            if has_file:
                lbl.configure(text="Dosya hazır. 'Importu Başlat' butonuna basın.", foreground="#16a34a")
            elif path:
                lbl.configure(text="Dosya bulunamadı.", foreground="#dc2626")
            else:
                lbl.configure(text="Önce Excel dosyası seçin.", foreground="#64748b")

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
                term=self._import_term() or "Guz",
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
        columns = "\n  • " + "\n  • ".join(spec.get("expected_columns") or [])
        tables = ", ".join(spec.get("affected_tables") or []) or "-"
        rollback = "Evet (Rollback & Onay sekmesinden)" if spec.get("rollback_supported") else "Hayır (geri alınamaz)"
        approval = (
            "Evet — önce onay gerekir"
            if spec.get("approval_required")
            else "Hayır — kalite uygunsa otomatik aktif olur"
        )
        text = (
            f"Veri Tipi          : {spec.get('label', selected)}\n"
            f"Kapsam             : {spec.get('required_scope', '-')}\n"
            f"Etkilenen tablolar : {tables}\n"
            f"\nAçıklama:\n{spec.get('description', '-')}\n"
            f"\nBeklenen Kolonlar:{columns}\n"
            f"\nEksik kolon olursa : {spec.get('on_missing_columns') or '-'}\n"
            f"Import sonrası      : {spec.get('post_import') or '-'}\n"
            f"Rollback mümkün mü  : {rollback}\n"
            f"Onay gerekiyor mu   : {approval}"
        )
        self._set_text(self.requirements_text, text)
        self._update_scope_indicator()
        self._update_template_button_state(selected)

    def _update_template_button_state(self, selected: str) -> None:
        """§2/§3: Öğrenci-veri-setinden-kriter modunda klasik şablon üretimi anlamsız;
        klasik buton pasifleşir ve yerine 'Kriter Veri Seti İndir' butonu gelir."""
        btn = getattr(self, "_btn_template", None)
        student_btn = getattr(self, "_btn_student_dataset", None)
        if btn is None:
            return
        if selected == "student_criteria":
            btn.configure(state="disabled")
            if student_btn is not None and student_btn.winfo_manager() != "pack":
                student_btn.pack(side=tk.LEFT, padx=(0, 6), after=btn)
            lbl = getattr(self, "_import_status_lbl", None)
            if lbl and not self.file_path_var.get().strip():
                lbl.configure(
                    text="Bu modda klasik şablon indirilemez. Öğrenci verisinden kriter veri seti üretip indirin.",
                    foreground="#64748b",
                )
        else:
            btn.configure(state="normal")
            if student_btn is not None and student_btn.winfo_manager() == "pack":
                student_btn.pack_forget()

    def _export_student_criteria(self) -> None:
        """§3: Öğrenci verisinden kriter veri setini üretip indirilebilir Excel'e yazar (uygulama YOK)."""
        excel_path = self.file_path_var.get().strip()
        if not excel_path or not os.path.exists(excel_path):
            messagebox.showwarning("Kriter Veri Seti", "Önce öğrenci not veri seti dosyasını 'Seç' ile yükleyin.")
            return
        year = self._selected_import_year()
        target = filedialog.asksaveasfilename(
            title="Kriter veri setini kaydet",
            defaultextension=".xlsx",
            initialfile=f"kriter_veri_seti_{year}.xlsx",
            filetypes=[("Excel dosyaları", "*.xlsx")],
        )
        if not target:
            return
        try:
            result = export_student_criteria_dataset(excel_path=excel_path, year=year, target_path=target)
        except Exception:
            messagebox.showerror("Kriter Veri Seti", self._friendly_backend_error())
            return
        self._set_text(self.import_result_text, result)
        if result.get("ok"):
            messagebox.showinfo(
                "Kriter Veri Seti",
                f"{result.get('message')}\n\nDosya:\n{result.get('path')}\n\n"
                "Bu dosyayı 'Kriter / Performans / Popülerlik' türünü seçerek (onaylı) içe aktarabilirsiniz.",
            )
        else:
            messagebox.showwarning("Kriter Veri Seti", result.get("message") or "Kriter veri seti üretilemedi.")

    def _update_scope_indicator(self, _event: Any = None) -> None:
        """Import'un uygulanacağı kapsamı (fakülte/bölüm/yıl) net gösterir. Yıllık çalışır."""
        if not hasattr(self, "scope_indicator_var"):
            return
        faculty = self.faculty_combo.get() or "Tumu"
        department = self.department_combo.get() or "Tumu"
        year = self.import_year_combo.get() or self.year_combo.get() or "-"
        selected = self._selected_import_type()
        if selected == "curriculum":
            scope = f"➤ Bu import şu kapsama uygulanacak →  Akademik yıl: {year}  (Fakülte/Bölüm/Dönem dosyadan okunur)"
        elif selected == "student_criteria":
            scope = f"➤ Bu import şu kapsama uygulanacak →  Akademik yıl: {year}  (ders kodu ile eşleşir; tüm kapsam)"
        else:
            scope = (
                f"➤ Bu import şu kapsama uygulanacak →  Fakülte: {faculty}  |  "
                f"Bölüm: {department}  |  Akademik yıl: {year}  (yıllık)"
            )
        self.scope_indicator_var.set(scope)

    def _confirm_student_criteria(self, db_path: str, excel_path: str, year: int) -> bool:
        """Öğrenci veri setinden kriter üretimini önizler ve kullanıcıdan onay alır.

        Kuru çalışma (dry-run) ile hiçbir yazma yapmadan eşleşen/eşleşmeyen ders
        sayısını ve örnek hesaplanan kriterleri gösterir.
        """
        try:
            preview = self._run_external_db_operation(
                lambda: generate_criteria_from_student_dataset(
                    db_path=db_path, excel_path=excel_path, year=int(year), dry_run=True
                )
            )
        except Exception:
            messagebox.showerror("Kriter Önizleme", self._friendly_backend_error())
            return False

        if not preview.get("ok"):
            messagebox.showwarning(
                "Kriter Önizleme",
                preview.get("message") or "Öğrenci veri setinden kriter hesaplanamadı.",
            )
            return False

        matched = int(preview.get("rows_matched", 0))
        skipped = int(preview.get("rows_skipped", 0))
        total = int(preview.get("rows_loaded", 0))
        rows = preview.get("preview_rows") or []
        sample_lines = []
        for r in rows[:8]:
            sample_lines.append(
                f"  • {r.get('kod')} ({r.get('donem')}): "
                f"başarı {float(r.get('basari_orani') or 0):.2f}, "
                f"ort {float(r.get('ortalama_not') or 0):.1f}, "
                f"doluluk {float(r.get('doluluk_orani') or 0):.2f}"
            )
        if len(rows) > 8:
            sample_lines.append(f"  ... ve {len(rows) - 8} ders daha")

        unmatched = preview.get("eslesmeyen") or []
        unmatched_line = ""
        if unmatched:
            uns = ", ".join(str(k) for k in unmatched[:10])
            unmatched_line = (
                f"\n⚠ Eşleşmeyen {len(unmatched)} ders kodu (atlanacak): {uns}"
                + (" ..." if len(unmatched) > 10 else "")
                + "\n"
            )

        message = (
            f"Öğrenci veri setinden {year} yılı için kriterler hesaplandı (önizleme):\n\n"
            f"  • Toplam satır     : {total}\n"
            f"  • Eşleşen ders     : {matched}\n"
            f"  • Atlanan (eşleşmeyen): {skipped}\n"
            f"{unmatched_line}\n"
            "Örnek hesaplanan kriterler:\n"
            + ("\n".join(sample_lines) if sample_lines else "  (örnek yok)")
            + f"\n\nBu işlem {year} yılı kriter/performans/popülerlik verilerini yeniden "
            "yazacaktır. Devam edilsin mi?"
        )
        return bool(messagebox.askyesno("Öğrenci Veri Setinden Kriter Oluştur", message, icon="question"))

    def _run_import(self) -> None:
        path = self._db_path()
        excel_path = self.file_path_var.get().strip()
        if not path:
            messagebox.showerror("Import", "Veritabanı seçilmedi.")
            return
        if not excel_path or not os.path.exists(excel_path):
            messagebox.showwarning("Import", "Önce geçerli bir Excel dosyası seçin.")
            return

        import_type = self._selected_import_type()
        year = self._selected_import_year()
        import_filename = os.path.basename(excel_path)

        # Müfredat importu: yılın eski müfredatı sıfırlanacak — kullanıcıya uyar
        if import_type == "curriculum":
            uyari = (
                f"DİKKAT: Bu işlem {year} yılına ait mevcut müfredat bağlantılarını\n"
                f"sıfırlayacak ve dosyadaki yeni verilerle değiştirecektir.\n\n"
                f"  • Seçilen yıl  : {year}\n"
                f"  • Dosya        : {import_filename}\n"
                f"  • Diğer yıllar : ETKİLENMEZ\n\n"
                f"Devam etmek istiyor musunuz?"
            )
            if not messagebox.askyesno("Müfredat Sıfırlama Onayı", uyari, icon="warning"):
                return
        elif import_type == "student_criteria":
            # Önce kuru çalışma (dry-run) ile önizleme göster, sonra onayla.
            if not self._confirm_student_criteria(path, excel_path, year):
                return
        elif import_type == "criteria":
            if not messagebox.askyesno(
                "Kriter Import Onayı",
                f"Seçili kriter dosyası ({import_filename}) yüklensin mi?\n\nYıl: {year}\n\n"
                "Kriterler HEMEN uygulanmaz; import 'Onay Bekliyor' durumunda kalır. "
                "Mevcut aktif kriterler değişmez. Uygulamak için 'Rollback & Onay' "
                "sekmesinden 'Aktif Yap' butonunu kullanın.",
            ):
                return
        else:
            if not messagebox.askyesno(
                "Import Onayı",
                f"Seçili dosya ({import_filename}) veritabanına aktarılsın mı?\n\nYıl: {year}",
            ):
                return

        lbl = getattr(self, "_import_status_lbl", None)
        btn = getattr(self, "_btn_import", None)
        if lbl:
            lbl.configure(text="Import çalışıyor, lütfen bekleyin...", foreground="#d97706")
        if btn:
            btn.configure(state="disabled")
        self.update_idletasks()

        try:
            # Yazıcı import, uygulamanın uzun ömürlü bağlantısıyla kilit yarışına
            # girmesin diye UI bağlantısını bırakıp çalıştır, sonra geri aç.
            result = self._run_external_db_operation(
                lambda: execute_import_request(
                    db_path=path,
                    import_type=import_type,
                    excel_path=excel_path,
                    year=year,
                    faculty_id=self._selected_faculty_id(),
                    department_id=self._selected_department_id(),
                    term=self._import_term() or "Guz",
                    auto_activate=bool(self.auto_activate_var.get()),
                    uploaded_by="desktop-ui",
                    # §5: Kriter importu DIREKT uygulanmaz; onay bekler. Diğer türler
                    # mevcut davranışla anında uygulanır.
                    apply_now=(import_type != "criteria"),
                )
            )
            readable = self._format_import_result(result, import_type, year, import_filename)
            self._set_text(self.import_result_text, readable)
            batch_id = result.get("import_batch_id")
            if batch_id:
                self.selected_import_batch_id = int(batch_id)
                self.load_selected_import()
                self._select_inspect_tab()
            self.refresh_center()
            self._refresh_related_views()
            if result.get("ok"):
                if lbl:
                    lbl.configure(text="Import başarılı.", foreground="#16a34a")
                messagebox.showinfo("Import Başarılı", self._build_success_message(result, import_type, year))
            else:
                if lbl:
                    lbl.configure(text="Import başarısız.", foreground="#dc2626")
                messagebox.showwarning("Import Başarısız", result.get("message") or "Import tamamlanamadı.")
        except Exception:
            if lbl:
                lbl.configure(text="Import hatası.", foreground="#dc2626")
            messagebox.showerror("Import", self._friendly_backend_error())
        finally:
            if btn and self.file_path_var.get().strip():
                btn.configure(state="normal")

    @staticmethod
    def _format_import_result(result: dict[str, Any], import_type: str, year: int, filename: str) -> str:
        lines: list[str] = []
        ok = result.get("ok", False)
        lines.append(f"{'✓ BAŞARILI' if ok else '✗ BAŞARISIZ'} — {import_type.upper()} Import")
        lines.append(f"Yıl: {year}  |  Dosya: {filename}")
        lines.append("-" * 60)
        msg = result.get("message", "")
        if msg:
            lines.append(f"Mesaj: {msg}")
        lines.append("")

        if import_type == "curriculum":
            sc_total = result.get("scopes_total", 0)
            sc_created = result.get("scopes_created", 0)
            sc_updated = result.get("scopes_updated", 0)
            sc_same = result.get("scopes_unchanged", 0)
            lines.append("── Müfredat Özeti ──────────────────────────────")
            lines.append(f"  Toplam kapsam     : {sc_total}")
            lines.append(f"  Yeni oluşturulan  : {sc_created}")
            lines.append(f"  Güncellenen       : {sc_updated}")
            lines.append(f"  Değişmeyen        : {sc_same}")
            lines.append(f"  Eklenen ders bağı : {result.get('links_added', 0)}")
            lines.append(f"  Çıkarılan ders bağ: {result.get('links_removed', 0)}")
            lines.append("")
            lines.append("── Sıfırlanan Veriler ──────────────────────────")
            lines.append(f"  Kriter satırı     : {result.get('criteria_rows_deleted', 0)}")
            lines.append(f"  Performans satırı : {result.get('performance_rows_deleted', 0)}")
            lines.append(f"  Popülerlik satırı : {result.get('popularity_rows_deleted', 0)}")
            lines.append(f"  Havuz skoru       : {result.get('pool_scores_cleared', 0)}")
            lines.append("")
            if result.get("criteria_rows_deleted", 0) > 0 or result.get("pool_scores_cleared", 0) > 0:
                lines.append("⚠ Yeni müfredat sonrası kriter ve skor verileri sıfırlandı.")
                lines.append("  Bu yıl için algoritmaların yeniden çalıştırılması gerekiyor.")
            compare = result.get("compare") or []
            if compare:
                lines.append("")
                lines.append("── Kapsam Detayı ───────────────────────────────")
                for c in compare[:10]:
                    status = "DEĞİŞMEDİ" if c.get("same") else f"+{c.get('added_count', 0)} / -{c.get('removed_count', 0)}"
                    lines.append(f"  {c.get('fakulte', '')[:20]} / {c.get('bolum', '')[:20]} ({c.get('donem', '')}) → {status}")
                if len(compare) > 10:
                    lines.append(f"  ... ve {len(compare) - 10} kapsam daha")
        elif import_type == "criteria":
            lines.append("── Kriter Import Özeti ─────────────────────────")
            for key, label in (
                ("rows_loaded", "Yüklenen satır"),
                ("rows_matched", "Eşleşen satır"),
                ("rows_skipped", "Atlanan satır"),
                ("rows_failed", "Hatalı satır"),
                ("import_batch_id", "Import batch ID"),
            ):
                val = result.get(key)
                if val is not None:
                    lines.append(f"  {label:20}: {val}")
        elif import_type == "survey":
            lines.append("── Anket Import Özeti ──────────────────────────")
            for key, label in (
                ("rows_loaded", "Yüklenen satır"),
                ("rows_matched", "Eşleşen satır"),
                ("import_batch_id", "Import batch ID"),
            ):
                val = result.get(key)
                if val is not None:
                    lines.append(f"  {label:20}: {val}")
        elif import_type == "student_criteria":
            lines.append("── Öğrenci Veri Setinden Kriter Üretimi ────────")
            for key, label in (
                ("rows_loaded", "Toplam satır"),
                ("rows_matched", "Eşleşen ders (kriter yazıldı)"),
                ("rows_skipped", "Atlanan (eşleşmeyen)"),
                ("performans_yazilan", "Performans satırı"),
                ("populerlik_yazilan", "Popülerlik satırı"),
            ):
                val = result.get(key)
                if val is not None:
                    lines.append(f"  {label:30}: {val}")
            eslesmeyen = result.get("eslesmeyen") or []
            if eslesmeyen:
                lines.append("")
                lines.append("  Eşleşmeyen ders kodları:")
                for kod in eslesmeyen[:20]:
                    lines.append(f"    - {kod}")
                if len(eslesmeyen) > 20:
                    lines.append(f"    ... ve {len(eslesmeyen) - 20} kod daha")

        batch_id = result.get("import_batch_id")
        if batch_id:
            lines.append("")
            lines.append(f"Import Batch ID    : {batch_id}")
            lines.append(f"Kalite puanı       : {result.get('quality_score', '-')}")
            lines.append(f"Kalite seviyesi    : {result.get('quality_level', '-')}")
            lines.append(f"Import durumu      : {result.get('import_status', '-')}")
            lines.append("")
            lines.append("Rollback & Onay sekmesinden onaylayabilir veya geri alabilirsiniz.")

        warnings = result.get("warnings") or []
        if warnings:
            lines.append("")
            lines.append("── Uyarılar ────────────────────────────────────")
            for w in warnings[:10]:
                lines.append(f"  ⚠ {w}")
            if len(warnings) > 10:
                lines.append(f"  ... ve {len(warnings) - 10} uyarı daha")

        errors = result.get("errors") or []
        if errors:
            lines.append("")
            lines.append("── Hatalar ─────────────────────────────────────")
            for e in errors[:10]:
                lines.append(f"  ✗ {e}")
            if len(errors) > 10:
                lines.append(f"  ... ve {len(errors) - 10} hata daha")

        return "\n".join(lines)

    @staticmethod
    def _build_success_message(result: dict[str, Any], import_type: str, year: int) -> str:
        batch_id = result.get("import_batch_id", "?")
        if import_type == "curriculum":
            sc = result.get("scopes_total", 0)
            added = result.get("links_added", 0)
            removed = result.get("links_removed", 0)
            reset = result.get("criteria_rows_deleted", 0)
            msg = f"{year} yılı müfredatı başarıyla güncellendi.\n\n"
            msg += f"  • {sc} kapsam işlendi, {added} ders eklendi, {removed} ders çıkarıldı\n"
            if reset > 0:
                msg += f"  • {reset} kriter kaydı sıfırlandı (yeniden hesaplama gerekir)\n"
            msg += f"\nImport Batch ID: {batch_id}\n"
            msg += "Rollback & Onay sekmesinden onaylayabilirsiniz."
            return msg
        if import_type == "student_criteria":
            matched = result.get("rows_matched", 0)
            skipped = result.get("rows_skipped", 0)
            return (
                f"{year} yılı için öğrenci veri setinden kriterler üretildi.\n\n"
                f"  • {matched} ders için kriter/performans/popülerlik yazıldı\n"
                f"  • {skipped} ders kodu eşleşmedi (atlandı)\n\n"
                "Veri Kalitesi ve Karar Merkezi ekranları güncellendi."
            )
        return f"Import tamamlandı. Batch ID: {batch_id}"

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
        self._select_inspect_tab()

    def _on_history_select(self, _event: Any = None) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        values = self.history_tree.item(selected[0], "values")
        if not values:
            return
        self.selected_import_batch_id = int(values[0])

    @staticmethod
    def _pct(value: Any) -> str:
        try:
            return f"%{float(value) * 100:.0f}"
        except (TypeError, ValueError):
            return "-"

    @classmethod
    def _format_quality_text(cls, q: dict[str, Any] | None) -> str:
        """§8: sayısal kalite skorunu okunabilir, kullanıcı dostu bir özete çevirir."""
        if not q or not isinstance(q, dict):
            return "Bu import için henüz kalite raporu yok. 'Kaliteyi Yeniden Hesapla' butonunu kullanın."
        score = float(q.get("quality_score") or 0.0)
        level = str(q.get("quality_level") or "")
        level_tr = {"high": "Çok iyi", "medium": "Kullanılabilir", "low": "Riskli"}.get(level, level or "-")
        verdict = {
            "high": "Evet — bu veri karar algoritmasında güvenle kullanılabilir.",
            "medium": "Evet, ancak işaretlenen eksik/aykırı alanları gözden geçirin.",
            "low": "Önerilmez — önce kritik sorunları düzeltin.",
        }.get(level, "Belirsiz.")
        req_ok = q.get("required_columns_ok")
        req_ok = (req_ok in (1, "1", True, "True", "true")) if not isinstance(req_ok, bool) else req_ok
        lines = [
            f"GENEL VERİ KALİTE SKORU: %{score * 100:.0f}  ({level_tr})",
            f"Karar algoritmasında kullanılabilir mi? → {verdict}",
            "",
            "── Skor Bileşenleri ─────────────────────────────",
            f"  Zorunlu kolonlar tam mı     : {'Evet' if req_ok else 'Hayır'}",
            f"  Başarılı satır oranı        : {cls._pct(q.get('successful_row_ratio'))}",
            f"  Ders eşleşme oranı          : {cls._pct(q.get('matched_course_ratio'))}",
            f"  Sayısal değer geçerliliği   : {cls._pct(q.get('valid_numeric_ratio'))}",
            "",
            "── Tespit Edilen Sorunlar ───────────────────────",
            f"  Eksik zorunlu alan          : {int(q.get('missing_required_count') or 0)}",
            f"  Eşleşmeyen kayıt            : {int(q.get('unmatched_row_count') or 0)}",
            f"  Geçersiz sayısal değer      : {int(q.get('invalid_numeric_count') or 0)}",
            f"  Aralık dışı değer           : {int(q.get('out_of_range_count') or 0)}",
            f"  Tekrarlı kayıt              : {int(q.get('duplicate_row_count') or 0)}",
            f"  Uyarı / Hata                : {int(q.get('warning_count') or 0)} / {int(q.get('error_count') or 0)}",
        ]
        summary = q.get("summary") if isinstance(q.get("summary"), dict) else {}
        itc = (summary or {}).get("issue_type_counts") or {}
        if itc:
            lines.append("")
            lines.append("── Sorun Türü Dağılımı ──────────────────────────")
            for key, val in itc.items():
                lines.append(f"  {key}: {val}")
        rc = (summary or {}).get("row_count")
        if rc:
            lines.append("")
            lines.append(f"İncelenen satır sayısı: {rc}")
        return "\n".join(lines)

    @staticmethod
    def _format_diff_text(diff: Any) -> str:
        """§9: diff sonucunu 'bu import uygulanırsa ne değişir' özetine çevirir."""
        if not diff or not isinstance(diff, dict):
            return "Bu import için henüz diff raporu yok. 'Diff Hesapla' butonunu kullanın."
        added = int(diff.get("added_count") or 0)
        removed = int(diff.get("removed_count") or 0)
        changed = int(diff.get("changed_count") or 0)
        unchanged = int(diff.get("unchanged_count") or 0)
        lines = [
            "DEĞİŞİKLİK KARŞILAŞTIRMASI (DIFF)",
            f"Bu import uygulanırsa {added + removed + changed} kayıt etkilenecek:",
            f"  • Eklenecek kayıt    : {added}",
            f"  • Güncellenecek      : {changed}",
            f"  • Çıkarılacak/pasif  : {removed}",
            f"  • Değişmeyen         : {unchanged}",
        ]
        items = diff.get("items") or []
        detail = [it for it in items if it.get("change_type") in ("changed", "added", "removed")]
        if detail:
            label = {"changed": "GÜNCELLENDİ", "added": "EKLENDİ", "removed": "ÇIKARILDI"}
            lines.append("")
            lines.append("── Alan Bazlı Değişiklikler (ilk 30) ────────────")
            for it in detail[:30]:
                ct = label.get(it.get("change_type"), str(it.get("change_type")))
                key = it.get("entity_key") or it.get("course_id") or ""
                field = it.get("field_name")
                if field:
                    lines.append(f"  [{ct}] {key} · {field}: {it.get('before_value')} → {it.get('after_value')}")
                else:
                    lines.append(f"  [{ct}] {key}")
            if len(detail) > 30:
                lines.append(f"  ... ve {len(detail) - 30} değişiklik daha")
        return "\n".join(lines)

    @staticmethod
    def _format_impact_text(impact: Any) -> str:
        """§11: karar etkisi sonucunu okunabilir özete çevirir."""
        if not impact or not isinstance(impact, dict):
            return "Bu import için henüz karar etkisi raporu yok. 'Etki Raporu Hesapla' butonunu kullanın."
        lines = ["KARAR ETKİSİ"]
        if impact.get("summary_text"):
            lines.append(str(impact.get("summary_text")))
        lines.extend([
            "",
            "── Özet ─────────────────────────────────────────",
            f"  Kararı değişen ders          : {int(impact.get('changed_decision_count') or 0)}",
            f"  Müfredattan havuza düşen     : {int(impact.get('curriculum_to_pool_count') or 0)}",
            f"  Havuzdan müfredata çıkan     : {int(impact.get('pool_to_curriculum_count') or 0)}",
            f"  Dinlendirme adayı            : {int(impact.get('rest_candidate_count') or 0)}",
            f"  İptal adayı                  : {int(impact.get('cancel_candidate_count') or 0)}",
            f"  Anlamlı skor değişimi        : {int(impact.get('significant_score_change_count') or 0)}",
            f"  Veri güveni artan / azalan   : "
            f"{int(impact.get('data_confidence_improved_count') or 0)} / "
            f"{int(impact.get('data_confidence_decreased_count') or 0)}",
        ])
        return "\n".join(lines)

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
            self._set_text(self.quality_text, self._format_quality_text(bundle.get("quality")))
            self._set_text(self.diff_text, self._format_diff_text(bundle.get("diff")))
            self._set_text(self.rollback_text, bundle.get("rollback") or {})
            self._set_text(self.impact_text, self._format_impact_text(bundle.get("impact")))
        except Exception:
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

    def recalculate_quality(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Kalite", "Önce bir import seçin.")
            return
        def _op() -> Any:
            with self._connect() as conn:
                quality = evaluate_import_quality(conn, self.selected_import_batch_id)
                conn.commit()
            return quality

        try:
            quality = self._run_external_db_operation(_op)
            self._set_text(self.quality_text, self._format_quality_text(quality.as_dict()))
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
            diff = self._run_external_db_operation(
                lambda: recalculate_import_artifact(path, self.selected_import_batch_id, "diff")
            )
            self._set_text(self.diff_text, self._format_diff_text(diff))
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
            impact = self._run_external_db_operation(
                lambda: recalculate_import_artifact(path, self.selected_import_batch_id, "impact")
            )
            self._set_text(self.impact_text, self._format_impact_text(impact))
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
        # §5: Onay bekleyen (staged) kriter importu ise canlı uygula; değilse normal aktive et.
        self._status_action(self._activate_or_apply, "Import aktif yapıldı / kriterler uygulandı.")

    @staticmethod
    def _activate_or_apply(conn: sqlite3.Connection, batch_id: int) -> Any:
        result = apply_pending_criteria_import(conn, batch_id, user="desktop-ui")
        if isinstance(result, dict) and result.get("ok"):
            return result
        # Kriter importu değil ya da uygulanacak staged satır yok → normal aktive.
        return activate_import(conn, batch_id, user="desktop-ui")

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
        def _op() -> Any:
            with self._connect() as conn:
                outcome = func(conn, self.selected_import_batch_id)
                evaluate_import_quality(conn, self.selected_import_batch_id)
                conn.commit()
            return outcome

        try:
            result = self._run_external_db_operation(_op)
            messagebox.showinfo("Veri Yönetimi", success_message)
            self.refresh_center()
            self.load_selected_import()
            self._set_text(self.rollback_text, result)
            self._refresh_related_views()
        except Exception:
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

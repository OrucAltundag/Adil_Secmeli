# -*- coding: utf-8 -*-
"""Veri Yonetimi sekmesi: import audit trail, kalite ve rollback gorunumu."""

from __future__ import annotations

import json
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

from app.db.session import open_sqlite_connection
from app.services.import_audit_service import (
    activate_import,
    approve_import,
    get_import_batch,
    list_import_batches,
    list_import_issues,
    list_import_rows,
    reject_import,
)
from app.services.import_diff_service import get_import_diff, recalculate_import_diff
from app.services.import_impact_service import (
    get_import_impact,
    recalculate_import_impact,
)
from app.services.import_quality_service import (
    evaluate_import_quality,
    summarize_quality,
)
from app.services.import_rollback_service import get_rollback_plan, rollback_import


class DataManagementPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: Any | None = None):
        super().__init__(parent)
        self.app = app
        self.selected_import_batch_id: int | None = None
        self._build_ui()
        self.status_var.set("Import geçmişi için Yenile'ye basın.")

    def _db_path(self) -> str | None:
        path = getattr(self.app, "db_path", None)
        return os.path.abspath(path) if path else None

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Sistem şu anda işlem yapamıyor. Lütfen daha sonra tekrar deneyin."

    def _connect(self) -> sqlite3.Connection:
        path = self._db_path()
        if not path or not os.path.exists(path):
            raise FileNotFoundError(self._friendly_backend_error())
        return open_sqlite_connection(path, row_factory=True)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Veri Yönetimi", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(top, text="Yenile", command=self.refresh_imports).pack(side=tk.RIGHT, padx=4)

        self.status_var = tk.StringVar(value="Import geçmişi yükleniyor.")
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.history_tab = ttk.Frame(self.nb, padding=8)
        self.detail_tab = ttk.Frame(self.nb, padding=8)
        self.rows_tab = ttk.Frame(self.nb, padding=8)
        self.quality_tab = ttk.Frame(self.nb, padding=8)
        self.diff_tab = ttk.Frame(self.nb, padding=8)
        self.rollback_tab = ttk.Frame(self.nb, padding=8)
        self.impact_tab = ttk.Frame(self.nb, padding=8)

        self.nb.add(self.history_tab, text="Import Geçmişi")
        self.nb.add(self.detail_tab, text="Import Detayı")
        self.nb.add(self.rows_tab, text="Satır Sonuçları")
        self.nb.add(self.quality_tab, text="Kalite Kontrol")
        self.nb.add(self.diff_tab, text="Diff / Karşılaştırma")
        self.nb.add(self.rollback_tab, text="Rollback & Onay")
        self.nb.add(self.impact_tab, text="Karar Etkisi")

        self._build_history()
        self._build_text_tabs()

    def _build_history(self) -> None:
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
            self.history_tree.column(col, width=110 if col != "filename" else 220, anchor=tk.W)
        self.history_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(self.history_tab, orient=tk.VERTICAL, command=self.history_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)

    def _build_text_tabs(self) -> None:
        self.detail_text = self._make_text(self.detail_tab)
        self.rows_text = self._make_text(self.rows_tab)
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

    def _make_text(self, parent: tk.Misc) -> ScrolledText:
        text = ScrolledText(parent, height=24, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, pady=6)
        text.configure(state=tk.DISABLED)
        return text

    def _set_text(self, widget: ScrolledText, value: Any) -> None:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value or "")
        widget.configure(state=tk.DISABLED)

    def refresh_imports(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        try:
            with self._connect() as conn:
                rows = list_import_batches(conn, limit=500)
            if not rows:
                self.status_var.set("Henüz import kaydı bulunmuyor.")
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

    def _on_history_select(self, _event: Any = None) -> None:
        selected = self.history_tree.selection()
        if not selected:
            return
        values = self.history_tree.item(selected[0], "values")
        if not values:
            return
        self.selected_import_batch_id = int(values[0])
        self.load_selected_import()

    def load_selected_import(self) -> None:
        import_batch_id = self.selected_import_batch_id
        if import_batch_id is None:
            return
        try:
            with self._connect() as conn:
                batch = get_import_batch(conn, import_batch_id) or {}
                rows = list_import_rows(conn, import_batch_id, limit=300)
                issues = list_import_issues(conn, import_batch_id, limit=300)
                quality = summarize_quality(conn, import_batch_id)
                diff = get_import_diff(conn, import_batch_id)
                plan = get_rollback_plan(conn, import_batch_id)
                impact = get_import_impact(conn, import_batch_id)
            self._set_text(self.detail_text, batch)
            self._set_text(self.rows_text, {"rows": rows, "issues": issues})
            self._set_text(self.quality_text, quality)
            self._set_text(self.diff_text, diff or "Bu import için henüz diff raporu yok. 'Diff Hesapla' butonunu kullanın.")
            self._set_text(self.rollback_text, plan)
            self._set_text(self.impact_text, impact or "Bu import için henüz karar etkisi raporu yok.")
        except Exception:
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

    def recalculate_diff(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Veri Yönetimi", "Önce bir import seçin.")
            return
        try:
            with self._connect() as conn:
                diff = recalculate_import_diff(conn, self.selected_import_batch_id)
                conn.commit()
            self._set_text(self.diff_text, diff)
        except Exception:
            messagebox.showerror("Diff", self._friendly_backend_error())

    def recalculate_impact(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Veri Yönetimi", "Önce bir import seçin.")
            return
        try:
            with self._connect() as conn:
                impact = recalculate_import_impact(conn, self.selected_import_batch_id)
                conn.commit()
            self._set_text(self.impact_text, impact)
        except Exception:
            messagebox.showerror("Karar Etkisi", self._friendly_backend_error())

    def load_rollback_plan(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Veri Yönetimi", "Önce bir import seçin.")
            return
        try:
            with self._connect() as conn:
                plan = get_rollback_plan(conn, self.selected_import_batch_id)
            self._set_text(self.rollback_text, plan)
        except Exception:
            messagebox.showerror("Rollback", self._friendly_backend_error())

    def approve_selected(self) -> None:
        self._status_action(lambda conn, batch_id: approve_import(conn, batch_id), "Import onaylandı.")

    def activate_selected(self) -> None:
        self._status_action(lambda conn, batch_id: activate_import(conn, batch_id), "Import aktif yapıldı.")

    def reject_selected(self) -> None:
        self._status_action(
            lambda conn, batch_id: reject_import(conn, batch_id, reason="UI uzerinden reddedildi."),
            "Import reddedildi.",
        )

    def rollback_selected(self) -> None:
        if self.selected_import_batch_id is None:
            messagebox.showinfo("Veri Yönetimi", "Önce bir import seçin.")
            return
        if not messagebox.askyesno("Rollback", "Seçili import geri alınsın mı? Bu işlem veri silmez; kayıtları pasifler."):
            return
        self._status_action(
            lambda conn, batch_id: rollback_import(conn, batch_id, reason="UI uzerinden rollback."),
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
            self.refresh_imports()
            self.load_selected_import()
            self._set_text(self.rollback_text, result)
        except Exception:
            messagebox.showerror("Veri Yönetimi", self._friendly_backend_error())

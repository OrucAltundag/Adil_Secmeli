# -*- coding: utf-8 -*-
"""Sistem Sağlığı ve mimari denetim paneli."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.core.config import load_app_config
from app.core.permissions import UserContext
from app.services.service_factory import get_service_factory


class SystemHealthPage(ttk.Frame):
    def __init__(self, parent, app=None, system_service=None, user_context=None, config=None):
        super().__init__(parent)
        self.app = app
        self.config = config or getattr(app, "app_config", None) or load_app_config()
        self.user_context = user_context or getattr(app, "user_context", None) or UserContext.demo_admin(self.config)
        self._system_service = system_service
        self._build_ui()

    def _service(self):
        if self._system_service is not None:
            return self._system_service
        db_path = getattr(self.app, "db_path", None)
        return get_service_factory(db_path=db_path, config=self.config).get_system_service()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Sistem Sağlığı", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(top, text="Health Check", command=self.refresh).pack(side=tk.RIGHT)

        self.txt = tk.Text(self, height=18, wrap=tk.WORD)
        self.txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.txt.insert(tk.END, "Sistem sağlığı için Health Check düğmesine basın.")

    def refresh(self):
        self.txt.delete("1.0", tk.END)
        try:
            vm = self._service().view_model(self.user_context)
            self.txt.insert(tk.END, "\n".join(vm.lines()))
            self.txt.insert(tk.END, "\n\nMimari denetim özeti:\n")
            findings = self._service().architecture_findings().unwrap()
            if not findings:
                self.txt.insert(tk.END, "- UI katmanında doğrudan DB erişimi bulgusu yok.\n")
                return
            for item in findings:
                reason = item.get("allowlist_reason") or "Aşamalı refactor bekliyor"
                pattern = item.get("pattern") or item.get("patterns") or "bilinmeyen"
                line = item.get("line")
                line_info = f":{line}" if line else ""
                self.txt.insert(tk.END, f"- {item['file']}{line_info}: {pattern} | {reason}\n")
        except Exception as exc:
            messagebox.showerror("Sistem Sağlığı", str(exc))

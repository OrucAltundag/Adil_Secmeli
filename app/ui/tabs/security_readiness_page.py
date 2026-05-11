# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import logging

from app.core.config import load_app_config
from app.services.security_health_service import SecurityHealthService

logger = logging.getLogger(__name__)

class SecurityReadinessPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config = load_app_config()
        self.health_service = SecurityHealthService(self.config)
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        self.lbl_title = ttk.Label(header_frame, text="Güvenlik ve Üretim Hazırlığı", font=("Helvetica", 16, "bold"))
        self.lbl_title.pack(side=tk.LEFT)

        btn_refresh = ttk.Button(header_frame, text="Yenile", command=self.refresh_data)
        btn_refresh.pack(side=tk.RIGHT)

        # Overview Frame
        self.overview_frame = ttk.LabelFrame(self, text="Genel Durum")
        self.overview_frame.pack(fill=tk.X, padx=10, pady=5)

        self.lbl_score = ttk.Label(self.overview_frame, text="Skor: --/100", font=("Helvetica", 14))
        self.lbl_score.pack(side=tk.LEFT, padx=10, pady=10)

        self.lbl_level = ttk.Label(self.overview_frame, text="Seviye: --", font=("Helvetica", 12))
        self.lbl_level.pack(side=tk.LEFT, padx=10, pady=10)

        self.lbl_env = ttk.Label(self.overview_frame, text=f"Ortam: {self.config.environment}", font=("Helvetica", 12))
        self.lbl_env.pack(side=tk.LEFT, padx=10, pady=10)

        # Details Treeview
        details_frame = ttk.LabelFrame(self, text="Güvenlik Kontrolleri")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("name", "status", "message")
        self.tree = ttk.Treeview(details_frame, columns=cols, show="headings")
        self.tree.heading("name", text="Kontrol Adı")
        self.tree.heading("status", text="Durum")
        self.tree.heading("message", text="Açıklama")

        self.tree.column("name", width=200)
        self.tree.column("status", width=100)
        self.tree.column("message", width=400)

        scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_data(self):
        try:
            data = self.health_service.check_security_configuration()
            self._update_ui(data)
        except Exception as e:
            logger.exception("Security readiness refresh failed: %s", e)
            self._update_ui({
                "score": 0,
                "max_score": 100,
                "level": "unknown",
                "checks": [
                    {
                        "name": "Security readiness",
                        "status": "fail",
                        "message": f"Güvenlik durumu okunamadı: {e}",
                    }
                ],
            })

    def _update_ui(self, data):
        self.lbl_score.config(text=f"Skor: {data.get('score', 0)}/{data.get('max_score', 100)}")
        
        level = data.get('level', 'unknown')
        color = "red" if level in ["unsafe", "demo_only"] else ("orange" if level == "partially_ready" else "green")
        self.lbl_level.config(text=f"Seviye: {level.upper()}", foreground=color)
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        for check in data.get('checks', []):
            self.tree.insert("", tk.END, values=(check['name'], check['status'].upper(), check['message']))

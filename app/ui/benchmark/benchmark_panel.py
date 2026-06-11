from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark.api_client import BenchmarkApiClient
from app.ui.benchmark.pages import (
    AlgorithmExplorerPage,
    AlgorithmGovernancePage,
    AllocationFairnessPage,
    ComparisonPage,
    DashboardPage,
    DatasetLabPage,
    DecisionEnginePage,
    MLReadinessPage,
    RunHistoryPage,
)
from app.ui.benchmark.widgets import COLORS


class BenchmarkPanel(ttk.Frame):
    """Main Benchmark Platform tab with left navigation and stacked pages."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self.api = BenchmarkApiClient()
        self.nav_buttons: dict[str, tk.Button] = {}
        self.pages: dict[str, ttk.Frame] = {}
        self.active_page = ""
        self._build()

    def _build(self) -> None:
        self.configure(style="BenchmarkRoot.TFrame")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.nav = tk.Frame(self, bg=COLORS["navy"], width=230)
        self.nav.grid(row=0, column=0, sticky="ns")
        self.nav.grid_propagate(False)

        title = tk.Label(
            self.nav,
            text="Benchmark\nPlatformu",
            bg=COLORS["navy"],
            fg="#FFFFFF",
            font=("Segoe UI", 16, "bold"),
            justify="left",
        )
        title.pack(fill=tk.X, padx=18, pady=(20, 18))

        self.stack = ttk.Frame(self)
        self.stack.grid(row=0, column=1, sticky="nsew")
        self.stack.rowconfigure(0, weight=1)
        self.stack.columnconfigure(0, weight=1)

        nav_groups = [
            {
                "header": "GENEL",
                "pages": [
                    ("dashboard", "Benchmark Paneli", DashboardPage),
                ],
            },
            {
                "header": "ALGORİTMA ARAÇLARI",
                "pages": [
                    ("algorithm_explorer", "Algoritma Rehberi", AlgorithmExplorerPage),
                    ("algorithm_governance", "Algoritma Yönetişimi", AlgorithmGovernancePage),
                    ("comparison", "Algoritma Karşılaştırma", ComparisonPage),
                ],
            },
            {
                "header": "ML & KARAR",
                "pages": [
                    ("ml_readiness", "ML Güvenilirlik", MLReadinessPage),
                    ("decision_engine", "Algoritma Önerisi", DecisionEnginePage),
                ],
            },
            {
                "header": "VERİ & ADALET",
                "pages": [
                    ("dataset_lab", "Veri Seti Laboratuvarı", DatasetLabPage),
                    ("allocation_fairness", "Yerleştirme Adaleti", AllocationFairnessPage),
                ],
            },
            {
                "header": "GEÇMİŞ",
                "pages": [
                    ("run_history", "Çalıştırma Geçmişi", RunHistoryPage),
                ],
            },
        ]

        for group in nav_groups:
            self._add_nav_section_header(group["header"])
            for key, label, page_cls in group["pages"]:
                self._add_nav_button(key, label)
                page = page_cls(self.stack, self.api)
                page.grid(row=0, column=0, sticky="nsew")
                self.pages[key] = page

        footer = tk.Label(
            self.nav,
            text="API: http://127.0.0.1:8000\nAPI yoksa örnek veri gösterilir",
            bg=COLORS["navy"],
            fg="#CBD5E1",
            font=("Segoe UI", 8),
            justify="left",
        )
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=18, pady=16)

        self.show_page("dashboard")

    def _add_nav_section_header(self, text: str) -> None:
        lbl = tk.Label(
            self.nav,
            text=text,
            bg=COLORS["navy"],
            fg="#64748B",
            font=("Segoe UI", 7, "bold"),
            anchor="w",
        )
        lbl.pack(fill=tk.X, padx=18, pady=(12, 2))

    def _add_nav_button(self, key: str, label: str) -> None:
        btn = tk.Button(
            self.nav,
            text=label,
            anchor="w",
            command=lambda k=key: self.show_page(k),
            bg=COLORS["navy"],
            fg="#E2E8F0",
            activebackground="#1E293B",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            font=("Segoe UI", 10, "bold"),
        )
        btn.pack(fill=tk.X, padx=10, pady=2)
        self.nav_buttons[key] = btn

    def show_page(self, key: str) -> None:
        if key not in self.pages:
            return
        for btn_key, btn in self.nav_buttons.items():
            if btn_key == key:
                btn.configure(bg=COLORS["blue"], fg="#FFFFFF")
            else:
                btn.configure(bg=COLORS["navy"], fg="#E2E8F0")
        self.pages[key].tkraise()
        self.active_page = key

    def refresh(self) -> None:
        page = self.pages.get(self.active_page)
        if page is None:
            return
        loader = getattr(page, "load_runs", None) or getattr(page, "load_data", None)
        if callable(loader):
            loader()

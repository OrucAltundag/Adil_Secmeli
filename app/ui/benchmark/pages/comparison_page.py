from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import BarChart, COLORS, DataTable, ErrorBanner, SectionHeader, run_async


class ComparisonPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.rows = list(mock_data.COMPARISON_ROWS)
        self._build()
        self.load_data()

    def _build(self) -> None:
        SectionHeader(self, "Algorithm Comparison", "Algoritmalari ayni dataset ve senaryo uzerinde metriklerle karsilastirin.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        filters = ttk.LabelFrame(self, text="Filtreler", padding=10)
        filters.pack(fill=tk.X, pady=(12, 10))
        for col in range(9):
            filters.columnconfigure(col, weight=1)

        ttk.Label(filters, text="Algoritma Grubu").grid(row=0, column=0, sticky="w")
        self.group_cb = ttk.Combobox(filters, state="readonly", values=["Tumu", "MCDM", "ML", "Clustering", "Allocation"])
        self.group_cb.set("Tumu")
        self.group_cb.grid(row=0, column=1, sticky="ew", padx=4)

        ttk.Label(filters, text="Metrik").grid(row=0, column=2, sticky="w")
        self.metric_cb = ttk.Combobox(
            filters,
            state="readonly",
            values=["accuracy", "f1", "roc_auc", "hit_at_10", "ndcg_at_10", "silhouette", "fairness", "latency_ms"],
        )
        self.metric_cb.set("accuracy")
        self.metric_cb.grid(row=0, column=3, sticky="ew", padx=4)

        ttk.Label(filters, text="K").grid(row=0, column=4, sticky="w")
        self.k_cb = ttk.Combobox(filters, state="readonly", values=["3", "5", "10"], width=6)
        self.k_cb.set("10")
        self.k_cb.grid(row=0, column=5, sticky="ew", padx=4)

        ttk.Label(filters, text="Gorunum").grid(row=0, column=6, sticky="w")
        self.view_cb = ttk.Combobox(filters, state="readonly", values=["Tablo", "Cubuk grafik", "Cizgi grafik"])
        self.view_cb.set("Tablo")
        self.view_cb.grid(row=0, column=7, sticky="ew", padx=4)

        ttk.Button(filters, text="Uygula", command=self.apply_filters).grid(row=0, column=8, sticky="e", padx=(8, 0))

        self.table = DataTable(
            self,
            ["algorithm", "group", "accuracy", "f1", "roc_auc", "hit_at_10", "ndcg_at_10", "silhouette", "fairness", "latency_ms", "runtime", "explanation"],
            height=10,
        )
        self.table.pack(fill=tk.BOTH, expand=True)

        chart_frame = ttk.LabelFrame(self, text="Secilen Metrik Grafigi", padding=8)
        chart_frame.pack(fill=tk.X, pady=(10, 0))
        self.chart = BarChart(chart_frame, height=180)
        self.chart.pack(fill=tk.X)

    def load_data(self) -> None:
        def worker():
            return self.api.get_runs()

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erisilemiyor, ornek karsilastirma verisi gosteriliyor.", level="warning")
            self.apply_filters()

        run_async(self, worker, success)

    def apply_filters(self) -> None:
        group = self.group_cb.get()
        rows = self.rows
        if group and group != "Tumu":
            rows = [row for row in rows if row.get("group") == group]
        metric = self.metric_cb.get()
        rows = sorted(rows, key=lambda r: float(r.get(metric) or 0), reverse=metric != "latency_ms")
        if rows:
            rows[0]["best"] = "best"
        self.table.set_rows(rows, best_key="best")
        self.chart.plot(rows, "algorithm", metric, color=COLORS["blue"])

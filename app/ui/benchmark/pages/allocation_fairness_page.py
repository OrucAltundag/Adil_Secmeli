from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import BarChart, COLORS, DataTable, ErrorBanner, MetricCard, SectionHeader, run_async


class AllocationFairnessPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self._build()

    def _build(self) -> None:
        SectionHeader(self, "Allocation Fairness", "Yerlestirme algoritmalarini, tercih memnuniyetini ve kontenjan adaletini izleyin.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        ttk.Button(self, text="Allocation Benchmark Calistir", command=self.run_allocation).pack(anchor="e", pady=(8, 4))

        metric_frame = ttk.Frame(self)
        metric_frame.pack(fill=tk.X, pady=(6, 10))
        first = mock_data.FAIRNESS_ROWS[0]
        cards = [
            ("Average Rank", first["average_rank"], COLORS["blue"]),
            ("Top-K Satisfaction", first["top_k_satisfaction"], COLORS["green"]),
            ("Envy Score", first["envy_score"], COLORS["orange"]),
            ("Seat Fill Rate", first["seat_fill_rate"], COLORS["cyan"]),
            ("Capacity Fill Rate", "98.7%", COLORS["green"]),
            ("Unassigned Student", first["unassigned"], COLORS["red"]),
        ]
        for idx, (title, value, color) in enumerate(cards):
            MetricCard(metric_frame, title, value, accent=color).grid(row=0, column=idx, sticky="nsew", padx=4)
            metric_frame.columnconfigure(idx, weight=1)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        comp_frame = ttk.LabelFrame(body, text="Algoritma Karsilastirmasi", padding=8)
        comp_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.fairness_table = DataTable(comp_frame, ["algorithm", "average_rank", "top_k_satisfaction", "envy_score", "seat_fill_rate", "assigned", "unassigned"], height=5)
        self.fairness_table.pack(fill=tk.X)
        self.fairness_table.set_rows(mock_data.FAIRNESS_ROWS)

        assign_frame = ttk.LabelFrame(body, text="Ogrenci - Atama Tablosu", padding=8)
        assign_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.assignment_table = DataTable(
            assign_frame,
            ["student_id", "student_name", "assigned_course", "assigned_course_id", "preference_rank_received", "satisfaction_score", "algorithm", "capacity_status"],
            height=8,
        )
        self.assignment_table.pack(fill=tk.BOTH, expand=True)
        self.assignment_table.set_rows(mock_data.ALLOCATION_ROWS)

        chart_frame = ttk.LabelFrame(body, text="Kontenjan ve Fairness Grafigi", padding=8)
        chart_frame.grid(row=1, column=1, sticky="nsew")
        self.chart = BarChart(chart_frame, height=220)
        self.chart.pack(fill=tk.BOTH, expand=True)
        self.chart.plot(mock_data.FAIRNESS_ROWS, "algorithm", "seat_fill_rate", color=COLORS["green"])

    def run_allocation(self) -> None:
        payload = {"scenario": "allocation_fairness", "algorithms": [row["algorithm"] for row in mock_data.FAIRNESS_ROWS], "top_k": 3}

        def worker():
            return self.api.execute_run(payload)

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erisilemiyor, allocation mock sonuclari gosteriliyor.", level="warning")
            self.fairness_table.set_rows(mock_data.FAIRNESS_ROWS)
            self.assignment_table.set_rows(mock_data.ALLOCATION_ROWS)

        run_async(self, worker, success)

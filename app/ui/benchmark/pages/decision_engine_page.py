from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    JsonPreviewWidget,
    MetricCard,
    SectionHeader,
    run_async,
)


class DecisionEnginePage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self._build()
        self.request_recommendation()

    def _build(self) -> None:
        SectionHeader(self, "Decision Engine", "Veri profili, senaryo ve benchmark gecmisine gore en uygun algoritmayi onerir.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        controls = ttk.LabelFrame(self, text="Oneri Girdileri", padding=10)
        controls.pack(fill=tk.X, pady=(12, 10))
        ttk.Label(controls, text="Problem Tipi").grid(row=0, column=0, sticky="w")
        self.problem_cb = ttk.Combobox(controls, state="readonly", values=["prediction", "ranking", "allocation", "clustering"], width=18)
        self.problem_cb.set("prediction")
        self.problem_cb.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(controls, text="Veri Boyutu").grid(row=0, column=2, sticky="w")
        self.size_entry = ttk.Entry(controls, width=12)
        self.size_entry.insert(0, "5000")
        self.size_entry.grid(row=0, column=3, sticky="w", padx=8)
        self.explain_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Aciklanabilirlik oncelikli", variable=self.explain_var).grid(row=0, column=4, sticky="w", padx=8)
        ttk.Button(controls, text="Oneri Uret", command=self.request_recommendation).grid(row=0, column=5, sticky="e")

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        rec_frame = ttk.LabelFrame(body, text="Sistemin Onerdigi Algoritma", padding=12)
        rec_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.algorithm_card = MetricCard(rec_frame, "Algoritma", "-", "Gerekce bekleniyor", accent=COLORS["blue"])
        self.algorithm_card.pack(fill=tk.X)
        self.confidence_card = MetricCard(rec_frame, "Guven Skoru", "-", "0-1 arasi", accent=COLORS["green"])
        self.confidence_card.pack(fill=tk.X, pady=(8, 0))
        self.reason_label = ttk.Label(rec_frame, text="-", wraplength=520, foreground=COLORS["muted"])
        self.reason_label.pack(fill=tk.X, pady=(8, 0))

        scenario_frame = ttk.LabelFrame(body, text="Senaryo Bazli Oneriler", padding=8)
        scenario_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self.scenario_table = DataTable(scenario_frame, ["Senaryo", "Oneri", "Gerekce"], height=5)
        self.scenario_table.pack(fill=tk.BOTH, expand=True)
        self.scenario_table.set_rows(
            [
                {"Senaryo": "Kucuk veri", "Oneri": "LogisticRegression / AHP", "Gerekce": "Yorumlanabilirlik"},
                {"Senaryo": "Buyuk veri", "Oneri": "RandomForest / XGBoostLike", "Gerekce": "Olcek ve dogruluk"},
                {"Senaryo": "Allocation", "Oneri": "GaleShapley", "Gerekce": "Stabil eslesme"},
                {"Senaryo": "Clustering", "Oneri": "KMeans", "Gerekce": "Olceklenebilir segmentasyon"},
            ]
        )

        flow_frame = ttk.LabelFrame(body, text="Oneri Akisi", padding=8)
        flow_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.flow_table = DataTable(flow_frame, ["Adim", "Aciklama"], height=7)
        self.flow_table.pack(fill=tk.BOTH, expand=True)
        self.flow_table.set_rows(
            [
                {"Adim": "1", "Aciklama": "Veri profili analizi"},
                {"Adim": "2", "Aciklama": "Aday algoritmalarin belirlenmesi"},
                {"Adim": "3", "Aciklama": "Benchmark gecmisinin incelenmesi"},
                {"Adim": "4", "Aciklama": "Metriklerin karsilastirilmasi"},
                {"Adim": "5", "Aciklama": "En iyi algoritmanin onerilmesi"},
            ]
        )

        json_frame = ttk.LabelFrame(body, text="Oneri Detayi (JSON)", padding=8)
        json_frame.grid(row=1, column=1, sticky="nsew")
        self.json_preview = JsonPreviewWidget(json_frame, height=10)
        self.json_preview.pack(fill=tk.BOTH, expand=True)

    def request_recommendation(self) -> None:
        try:
            size = int(self.size_entry.get() or "5000")
        except ValueError:
            size = 5000
        payload = {
            "problem_type": self.problem_cb.get(),
            "data_size": size,
            "explainability_priority": self.explain_var.get(),
            "use_history": True,
        }

        def worker():
            return self.api.get_recommendation(payload)

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erisilemiyor, mock karar motoru sonucu gosteriliyor.", level="warning")
            data = result.data
            self.algorithm_card.set_value(data.get("algorithm", "-"), data.get("source", "-"))
            self.confidence_card.set_value(data.get("confidence", "-"))
            self.reason_label.configure(text=data.get("reason", "-"))
            self.json_preview.set_json(data)

        run_async(self, worker, success)

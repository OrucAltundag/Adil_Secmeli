from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import DataTable, ErrorBanner, JsonPreviewWidget, SectionHeader, run_async


class RunHistoryPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.runs = []
        self._build()
        self.load_runs()

    def _build(self) -> None:
        SectionHeader(self, "Run History", "Gecmis benchmark calistirmalarini listeleyin, detaylarini goruntuleyin ve karsilastirmaya hazirlayin.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        filters = ttk.LabelFrame(self, text="Filtreler", padding=10)
        filters.pack(fill=tk.X, pady=(12, 10))
        ttk.Label(filters, text="Tarih Araligi").grid(row=0, column=0, sticky="w")
        self.date_entry = ttk.Entry(filters, width=20)
        self.date_entry.insert(0, "2024-05-01 - 2024-05-18")
        self.date_entry.grid(row=0, column=1, padx=4)
        ttk.Label(filters, text="Senaryo").grid(row=0, column=2, sticky="w")
        self.scenario_cb = ttk.Combobox(filters, state="readonly", values=["Tumu", "real_mcdm_recommendation", "real_ml_prediction", "allocation_fairness", "clustering_exploration"], width=26)
        self.scenario_cb.set("Tumu")
        self.scenario_cb.grid(row=0, column=3, padx=4)
        ttk.Label(filters, text="Durum").grid(row=0, column=4, sticky="w")
        self.status_cb = ttk.Combobox(filters, state="readonly", values=["Tumu", "completed", "running", "failed"], width=12)
        self.status_cb.set("Tumu")
        self.status_cb.grid(row=0, column=5, padx=4)
        ttk.Button(filters, text="Filtrele", command=self.apply_filters).grid(row=0, column=6, padx=4)
        ttk.Button(filters, text="Yenile", command=self.load_runs).grid(row=0, column=7, padx=4)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(body, text="Run Listesi", padding=8)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        top_actions = ttk.Frame(list_frame)
        top_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(top_actions, text="Detay Goruntule", command=self.show_detail).pack(side=tk.RIGHT, padx=3)
        ttk.Button(top_actions, text="Compare", command=self.compare_selected).pack(side=tk.RIGHT, padx=3)
        self.table = DataTable(
            list_frame,
            ["run_id", "date", "scenario", "dataset", "algorithms_count", "status", "duration", "accuracy", "f1", "roc_auc", "hit_at_k", "ndcg_at_k", "silhouette", "fairness", "latency"],
            height=12,
        )
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.tree.bind("<Double-1>", lambda _e: self.show_detail())

        detail_frame = ttk.LabelFrame(body, text="Genel Notlar / JSON Onizleme", padding=8)
        detail_frame.grid(row=0, column=1, sticky="nsew")
        self.json_preview = JsonPreviewWidget(detail_frame, height=18)
        self.json_preview.pack(fill=tk.BOTH, expand=True)

    def load_runs(self) -> None:
        def worker():
            return self.api.get_runs()

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erisilemiyor, mock run history gosteriliyor.", level="warning")
            self.runs = self._normalize_runs(result.data.get("runs", mock_data.RUNS))
            self.apply_filters()
            if self.runs:
                self.json_preview.set_json(self.runs[0])

        run_async(self, worker, success)

    def _normalize_runs(self, runs):
        normalized = []
        for item in runs:
            if "run_id" in item:
                normalized.append(item)
                continue
            run = item.get("run", item)
            normalized.append(
                {
                    "run_id": run.get("run_id", "-"),
                    "date": run.get("started_at", "-"),
                    "scenario": run.get("scenario_name", "-"),
                    "dataset": run.get("dataset_name", "-"),
                    "algorithms_count": len(run.get("algorithms", [])),
                    "status": run.get("status", "-"),
                    "duration": "-",
                    "accuracy": "",
                    "f1": "",
                    "roc_auc": "",
                    "hit_at_k": "",
                    "ndcg_at_k": "",
                    "silhouette": "",
                    "fairness": "",
                    "latency": "",
                }
            )
        return normalized

    def apply_filters(self) -> None:
        rows = self.runs or mock_data.RUNS
        scenario = self.scenario_cb.get()
        status = self.status_cb.get()
        if scenario != "Tumu":
            rows = [r for r in rows if r.get("scenario") == scenario]
        if status != "Tumu":
            rows = [r for r in rows if r.get("status") == status]
        self.table.set_rows(rows)

    def show_detail(self) -> None:
        values = self.table.selected_values()
        run_id = values[0] if values else (self.runs[0]["run_id"] if self.runs else mock_data.RUNS[0]["run_id"])

        def worker():
            return self.api.get_run_detail(run_id)

        def success(result):
            if result.used_mock:
                self.banner.show("Run detayi API'den alinamadi, mock JSON gosteriliyor.", level="warning")
            self.json_preview.set_json(result.data)

        run_async(self, worker, success)

    def compare_selected(self) -> None:
        selected = self.table.selected_values()
        run_id = selected[0] if selected else "secili run yok"
        self.banner.show(f"{run_id} karsilastirmaya eklendi. Algorithm Comparison ekraninda son run verileri kullanilabilir.", level="warning")

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import COLORS, DataTable, ErrorBanner, MetricCard, SectionHeader, StatusCard, run_async


class DashboardPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.algorithm_vars: dict[str, tk.BooleanVar] = {}
        self.metric_cards: dict[str, MetricCard] = {}
        self.status_cards: dict[str, MetricCard] = {}
        self._build()
        self.load_initial_data()

    def _build(self) -> None:
        SectionHeader(self, "Benchmark Dashboard", "Senaryo, dataset ve algoritmalari secerek benchmark deneylerini calistirin.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        controls = ttk.LabelFrame(self, text="Deney Ayarlari", padding=10)
        controls.pack(fill=tk.X, pady=(12, 8))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Senaryo").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.scenario_cb = ttk.Combobox(controls, state="readonly", values=[s["name"] for s in mock_data.SCENARIOS])
        self.scenario_cb.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        self.scenario_cb.set(mock_data.SCENARIOS[0]["name"])

        ttk.Label(controls, text="Dataset").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.dataset_cb = ttk.Combobox(controls, state="readonly", values=mock_data.DATASETS)
        self.dataset_cb.grid(row=0, column=3, sticky="ew", padx=(0, 14))
        self.dataset_cb.set("real_pref_2024_v2")

        btns = ttk.Frame(controls)
        btns.grid(row=0, column=4, sticky="e")
        self.run_btn = ttk.Button(btns, text="Calistir", style="Primary.TButton", command=self.run_benchmark)
        self.run_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Temizle", command=self.clear_selection).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Sonuclari Yenile", command=self.refresh_results).pack(side=tk.LEFT, padx=3)

        algo_frame = ttk.LabelFrame(self, text="Algoritma Secimi (Coklu Secim)", padding=10)
        algo_frame.pack(fill=tk.X, pady=(0, 10))
        self.algo_container = ttk.Frame(algo_frame)
        self.algo_container.pack(fill=tk.X)

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X, pady=(0, 10))
        for idx, (key, title, value) in enumerate(
            [
                ("last_run", "Son Calistirma", "10:42:31"),
                ("status", "Durum", "Hazir"),
                ("duration", "Sure", "00:00:00"),
                ("algo_count", "Secilen Algoritma", "0"),
                ("dataset_size", "Dataset Boyutu", "12.4K"),
                ("metric_count", "Metrik", "0"),
            ]
        ):
            card = StatusCard(cards, title, value, "success" if key == "status" else "info")
            card.grid(row=0, column=idx, sticky="nsew", padx=4)
            cards.columnconfigure(idx, weight=1)
            self.status_cards[key] = card

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        summary_frame = ttk.LabelFrame(body, text="Son Run Ozeti", padding=8)
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.summary_table = DataTable(summary_frame, ["Alan", "Deger"], height=8)
        self.summary_table.pack(fill=tk.BOTH, expand=True)

        metrics_frame = ttk.LabelFrame(body, text="Ozet Metrikler", padding=8)
        metrics_frame.grid(row=0, column=1, sticky="nsew")
        for idx, key in enumerate(["accuracy", "f1", "roc_auc", "hit_at_10", "ndcg_at_10", "silhouette", "fairness", "latency_ms"]):
            card = MetricCard(metrics_frame, key.upper().replace("_", "-"), "-", accent=COLORS["blue"])
            card.grid(row=idx // 4, column=idx % 4, sticky="nsew", padx=4, pady=4)
            metrics_frame.columnconfigure(idx % 4, weight=1)
            self.metric_cards[key] = card

    def load_initial_data(self) -> None:
        def worker():
            return self.api.get_algorithms(), self.api.get_scenarios()

        def success(result):
            algos_result, scenarios_result = result
            if algos_result.used_mock or scenarios_result.used_mock:
                self.banner.show("Backend API erisilemiyor, ornek veri gosteriliyor.", level="warning")
            algos = algos_result.data.get("algorithms", mock_data.ALGORITHMS)
            scenarios = scenarios_result.data.get("scenarios", mock_data.SCENARIOS)
            self.scenario_cb["values"] = [s.get("name", "") for s in scenarios]
            self._render_algorithm_checks(algos)
            self._update_from_run(mock_data.SAMPLE_RUN)

        run_async(self, worker, success)

    def _render_algorithm_checks(self, algorithms) -> None:
        for child in self.algo_container.winfo_children():
            child.destroy()
        self.algorithm_vars.clear()
        for idx, item in enumerate(algorithms):
            name = item.get("name") or str(item)
            var = tk.BooleanVar(value=name in {"AHP", "TOPSIS", "RandomForest", "GaleShapley"})
            self.algorithm_vars[name] = var
            cb = ttk.Checkbutton(self.algo_container, text=name, variable=var, command=self._sync_algo_count)
            cb.grid(row=idx // 5, column=idx % 5, sticky="w", padx=8, pady=3)
        self._sync_algo_count()

    def _sync_algo_count(self) -> None:
        count = len(self.selected_algorithms())
        self.status_cards["algo_count"].set_value(count, "Secili")

    def selected_algorithms(self) -> list[str]:
        return [name for name, var in self.algorithm_vars.items() if var.get()]

    def clear_selection(self) -> None:
        for var in self.algorithm_vars.values():
            var.set(False)
        self._sync_algo_count()
        self.banner.clear()

    def refresh_results(self) -> None:
        self._update_from_run(mock_data.SAMPLE_RUN)

    def run_benchmark(self) -> None:
        algorithms = self.selected_algorithms()
        if not algorithms:
            self.banner.show("Benchmark calistirmak icin en az bir algoritma secin.")
            return
        payload = {
            "scenario": self.scenario_cb.get(),
            "dataset": self.dataset_cb.get(),
            "algorithms": algorithms,
            "parameters": {"source": "desktop-ui"},
        }
        self.run_btn.configure(state=tk.DISABLED)
        self.status_cards["status"].set_value("Calisiyor", "Thread aktif")
        self.banner.clear()

        def worker():
            return self.api.execute_run(payload)

        def success(result):
            self.run_btn.configure(state=tk.NORMAL)
            if result.used_mock:
                self.banner.show("Benchmark calistirilamadi. Backend API yanit vermiyor. Ornek veri gosteriliyor.", level="warning")
            data = result.data
            run = data.get("details", {}).get("run") or mock_data.SAMPLE_RUN
            self._update_from_run(run)
            self.status_cards["status"].set_value("Tamamlandi", "Sonuc alindi")

        def error(exc):
            self.run_btn.configure(state=tk.NORMAL)
            self.banner.show(f"Benchmark calistirilamadi: {exc}")

        run_async(self, worker, success, error)

    def _update_from_run(self, run: dict) -> None:
        metrics = run.get("metrics", {})
        self.status_cards["last_run"].set_value(run.get("date", "-").split(" ")[-1], "Bugun")
        self.status_cards["status"].set_value(run.get("status", "-"), "Run durumu")
        self.status_cards["duration"].set_value(run.get("duration", "-"), "Dakika")
        self.status_cards["algo_count"].set_value(len(run.get("algorithms", [])), "Secili")
        self.status_cards["dataset_size"].set_value(run.get("dataset_size", "-"), "Kayit")
        self.status_cards["metric_count"].set_value(run.get("metric_count", len(metrics)), "Tamam")
        self.summary_table.set_rows(
            [
                {"Alan": "Run ID", "Deger": run.get("run_id", "-")},
                {"Alan": "Senaryo", "Deger": run.get("scenario", "-")},
                {"Alan": "Dataset", "Deger": run.get("dataset", "-")},
                {"Alan": "Algoritmalar", "Deger": ", ".join(run.get("algorithms", []))},
                {"Alan": "Baslatan", "Deger": run.get("started_by", "Admin")},
                {"Alan": "Tarih", "Deger": run.get("date", "-")},
                {"Alan": "Durum", "Deger": run.get("status", "-")},
                {"Alan": "Sure", "Deger": run.get("duration", "-")},
            ]
        )
        for key, card in self.metric_cards.items():
            value = metrics.get(key, "-")
            card.set_value(value)

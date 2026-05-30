from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    COLORS,
    BarChart,
    DataTable,
    ErrorBanner,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    run_async,
)


class ComparisonPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.rows = list(mock_data.COMPARISON_ROWS)
        self.loaded_run_ids: list[str] = []
        self._build()
        self.load_data()

    def _build(self) -> None:
        SectionHeader(self, "Algoritma Karşılaştırma", "Algoritmaları aynı veri seti ve senaryo üzerinde metriklerle kıyaslayın.").pack(fill=tk.X)
        PageInfoBox(
            self,
            "Aynı koşullarda çalışan algoritmaların başarı, hız ve uygunluk metriklerini karşılaştırır.",
            "Algoritma grubunu ve ana metriği seçin; tablo ve grafik seçilen metriğe göre sıralanır.",
            "Farklı problem tiplerinin metrikleri farklıdır; boş hücreler o metrik bu algoritma için geçerli değil demektir.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.pack(fill=tk.X, pady=(6, 0))
        self.banner = ErrorBanner(self)

        filters = ttk.LabelFrame(self, text="Filtreler", padding=10)
        filters.pack(fill=tk.X, pady=(12, 10))
        for col in range(9):
            filters.columnconfigure(col, weight=1)

        ttk.Label(filters, text="Algoritma Grubu").grid(row=0, column=0, sticky="w")
        self.group_cb = ttk.Combobox(filters, state="readonly", values=["Tümü", "MCDM", "ML", "Clustering", "Allocation"])
        self.group_cb.set("Tümü")
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

        ttk.Label(filters, text="Görünüm").grid(row=0, column=6, sticky="w")
        self.view_cb = ttk.Combobox(filters, state="readonly", values=["Tablo", "Çubuk grafik", "Çizgi grafik"])
        self.view_cb.set("Tablo")
        self.view_cb.grid(row=0, column=7, sticky="ew", padx=4)
        self.view_cb.bind("<<ComboboxSelected>>", lambda _e: self.apply_filters())

        ttk.Button(filters, text="Uygula", command=self.apply_filters).grid(row=0, column=8, sticky="e", padx=(8, 0))

        self.table = DataTable(
            self,
            [
                "algorithm",
                "group",
                "accuracy",
                "f1",
                "roc_auc",
                "hit_at_10",
                "ndcg_at_10",
                "silhouette",
                "fairness",
                "latency_ms",
                "baseline_diff",
                "confidence_interval",
                "significance",
                "runtime",
                "explanation",
            ],
            height=10,
            column_labels={
                "algorithm": "Algoritma",
                "group": "Grup",
                "accuracy": "Accuracy",
                "f1": "F1",
                "roc_auc": "ROC-AUC",
                "hit_at_10": "Hit@10",
                "ndcg_at_10": "NDCG@10",
                "silhouette": "Silhouette",
                "fairness": "Adalet",
                "latency_ms": "Gecikme (ms)",
                "baseline_diff": "Baseline Farkı",
                "confidence_interval": "CI",
                "significance": "Anlamlılık",
                "runtime": "Süre",
                "explanation": "Açıklama",
            },
        )
        self.table.pack(fill=tk.BOTH, expand=True)

        self.chart_frame = ttk.LabelFrame(self, text="Seçilen Metrik Grafiği", padding=8)
        self.chart_frame.pack(fill=tk.X, pady=(10, 0))
        self.chart = BarChart(self.chart_frame, height=180)
        self.chart.pack(fill=tk.X)

    def load_data(self) -> None:
        def worker():
            selected_runs = list(getattr(self.api, "selected_run_ids_for_comparison", []))
            if selected_runs:
                return {"selected_runs": selected_runs, "details": [self.api.get_run_detail(run_id) for run_id in selected_runs]}
            return {"selected_runs": [], "runs": self.api.get_runs()}

        def success(result):
            selected_runs = result.get("selected_runs", [])
            if selected_runs:
                detail_results = result.get("details") or []
                self.source_badge.set_source(any(detail_result.used_mock for detail_result in detail_results))
                self.rows = []
                for run_id, detail_result in zip(selected_runs, detail_results):
                    if detail_result.used_mock:
                        self.banner.show("Run detayı API'den alınamadı; örnek karşılaştırma verisi gösteriliyor.", level="warning")
                    self.rows.extend(_rows_from_run_detail(run_id, detail_result.data))
                self.loaded_run_ids = selected_runs
                self.banner.show(f"Karşılaştırma sepetindeki run sayısı: {len(selected_runs)} ({', '.join(selected_runs[:3])})", level="warning")
            else:
                runs_result = result.get("runs")
                self.source_badge.set_source(True, "Veri kaynağı: Örnek karşılaştırma tablosu")
                if runs_result and runs_result.used_mock:
                    self.banner.show("Backend API erişilemiyor; örnek karşılaştırma verisi gösteriliyor.", level="warning")
                self.rows = list(mock_data.COMPARISON_ROWS)
                self.loaded_run_ids = []
            self._sync_metric_options()
            self.apply_filters()

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            success(worker())
            return
        run_async(self, worker, success)

    def apply_filters(self) -> None:
        group = self.group_cb.get()
        rows = self.rows
        for row in self.rows:
            row.pop("best", None)
        if group and group != "Tümü":
            rows = [row for row in rows if row.get("group") == group]
        metric = self.metric_cb.get()
        rows = [_with_baseline_fields(row, rows, metric) for row in rows]
        rows = sorted(rows, key=lambda r: float(r.get(metric) or 0), reverse=metric != "latency_ms")
        if rows:
            rows[0]["best"] = "best"
        self.table.set_rows(rows, best_key="best")
        self._render_view(rows, metric)

    def _sync_metric_options(self) -> None:
        preferred = ["accuracy", "f1", "roc_auc", "hit_at_10", "ndcg_at_10", "silhouette", "fairness", "latency_ms"]
        available = []
        for metric in preferred:
            if any(row.get(metric) not in {"", None, "—"} for row in self.rows):
                available.append(metric)
        if not available:
            available = preferred
        self.metric_cb["values"] = available
        if self.metric_cb.get() not in available:
            self.metric_cb.set(available[0])

    def _render_view(self, rows: list[dict], metric: str) -> None:
        view = self.view_cb.get()
        if view == "Tablo":
            self.table.pack(fill=tk.BOTH, expand=True)
            self.chart_frame.pack_forget()
            return
        if not self.chart_frame.winfo_ismapped():
            self.chart_frame.pack(fill=tk.X, pady=(10, 0))
        if view == "Çizgi grafik":
            self.chart.plot_line(rows, "algorithm", metric, color=COLORS["blue"])
        else:
            self.chart.plot(rows, "algorithm", metric, color=COLORS["blue"])


def _rows_from_run_detail(run_id: str, detail: dict) -> list[dict]:
    rows = []
    for item in detail.get("comparison_table") or []:
        row = _normalize_comparison_row(item)
        row["run_id"] = run_id
        rows.append(row)
    return rows


def _normalize_comparison_row(item: dict) -> dict:
    algorithm = item.get("algorithm", "-")
    row = {
        "algorithm": algorithm,
        "group": _infer_group(algorithm),
        "accuracy": "",
        "f1": "",
        "roc_auc": "",
        "hit_at_10": "",
        "ndcg_at_10": "",
        "silhouette": "",
        "fairness": "",
        "latency_ms": "",
        "runtime": "",
        "explanation": "Gerçek run detayı",
    }
    metric_map = {
        "accuracy": "accuracy",
        "f1": "f1",
        "roc_auc": "roc_auc",
        "hit_at_k": "hit_at_10",
        "ndcg_at_k": "ndcg_at_10",
        "silhouette": "silhouette",
        "silhouette_score": "silhouette",
        "seat_fill_rate": "fairness",
        "latency_ms": "latency_ms",
    }
    for raw_key, value in item.items():
        metric_name = str(raw_key).split(".")[-1]
        target = metric_map.get(metric_name)
        if target:
            row[target] = value
    return row


def _infer_group(algorithm: str) -> str:
    name = str(algorithm or "").lower()
    if name in {"ahp", "topsis", "vikor", "promethee_ii"}:
        return "MCDM"
    if "allocation" in name or "gale" in name or "greedy" in name:
        return "Allocation"
    if "cluster" in name or "kmeans" in name or "dbscan" in name:
        return "Clustering"
    return "ML"


def _with_baseline_fields(row: dict, rows: list[dict], metric: str) -> dict:
    out = dict(row)
    baseline = _baseline_value(rows, metric)
    try:
        metric_value = float(out.get(metric))
    except (TypeError, ValueError):
        metric_value = None
    if baseline is not None and metric_value is not None:
        out["baseline_diff"] = metric_value - baseline
        out["significance"] = "Hesaplanmadı"
    else:
        out["baseline_diff"] = "—"
        out["significance"] = "—"
    out["confidence_interval"] = out.get("confidence_interval") or "—"
    return out


def _baseline_value(rows: list[dict], metric: str) -> float | None:
    baseline_names = ("baseline", "random", "majority", "dummy")
    for row in rows:
        algorithm = str(row.get("algorithm", "")).lower()
        if not any(token in algorithm for token in baseline_names):
            continue
        try:
            return float(row.get(metric))
        except (TypeError, ValueError):
            return None
    return None

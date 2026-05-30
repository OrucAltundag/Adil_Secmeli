from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from app.ui.benchmark.widgets import COLORS, ErrorBanner, JsonPreviewWidget, PageInfoBox, SourceBadge, run_async


class AlgorithmGovernancePage(ttk.Frame):
    """Algoritma yönetişimi ve istatistiksel değerlendirme paneli."""

    def __init__(self, parent, api_client):
        super().__init__(parent)
        self.api = api_client
        self._build()
        self.load_data()

    def _build(self) -> None:
        self.configure(style="BenchmarkRoot.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 8))
        tk.Label(
            header,
            text="Algoritma Yönetişimi",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Bu bölümdeki benchmark algoritmaları nihai müfredat kararını doğrudan üretmez. Nihai karar AHP/TOPSIS + kurallar + state machine hattıyla verilir.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))
        PageInfoBox(
            header,
            "Algoritmaların kullanım rolünü, görev eşleşmesini ve veri güvenlik kurallarını denetler.",
            "Rol matrisiyle algoritmanın final karara etkisini, problem eşleşmesiyle hangi işte kullanılabileceğini kontrol edin.",
            "Bu sayfa benchmark tarafındaki güvenlik bariyeridir; veri yetersizse algoritma çalışsa bile karar hattına alınmamalıdır.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(header)
        self.source_badge.pack(fill=tk.X, pady=(6, 0))
        self.banner = ErrorBanner(header)

        body = ttk.Notebook(self)
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 18))

        self.role_frame = ttk.Frame(body)
        self.task_frame = ttk.Frame(body)
        self.guard_frame = ttk.Frame(body)
        self.result_frame = ttk.Frame(body)
        body.add(self.role_frame, text="Rol Matrisi")
        body.add(self.task_frame, text="Problem Eşleşmesi")
        body.add(self.guard_frame, text="Veri Uygunluğu")
        body.add(self.result_frame, text="Benchmark Sonuçları")

        self._build_role_matrix()
        self._build_task_mapping()
        self._build_guard_panel()
        self._build_result_panel()

    def _build_role_matrix(self) -> None:
        card = ttk.LabelFrame(self.role_frame, text="Algoritma Rol Matrisi", padding=8)
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        columns = ("algorithm", "family", "task", "role", "final", "min_samples", "metrics", "warning")
        self.role_tree = ttk.Treeview(card, columns=columns, show="headings", height=16)
        headers = {
            "algorithm": "Algoritma",
            "family": "Aile",
            "task": "Görev",
            "role": "Kullanım rolü",
            "final": "Final karara etki",
            "min_samples": "Min veri",
            "metrics": "Önerilen metrikler",
            "warning": "Uyarı",
        }
        widths = {"algorithm": 150, "family": 90, "task": 110, "role": 140, "final": 110, "min_samples": 80, "metrics": 230, "warning": 260}
        for col in columns:
            self.role_tree.heading(col, text=headers[col])
            self.role_tree.column(col, width=widths[col], anchor="w")
        self.role_tree.pack(fill=tk.BOTH, expand=True)
        self.role_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_role_select())

    def _build_task_mapping(self) -> None:
        card = ttk.LabelFrame(self.task_frame, text="Problem-Algoritma Eşleşmesi", padding=8)
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        columns = ("task", "algorithm", "allowed_role", "recommended", "notes")
        self.task_tree = ttk.Treeview(card, columns=columns, show="headings", height=16)
        for col, label, width in [
            ("task", "Problem tipi", 210),
            ("algorithm", "Algoritma", 170),
            ("allowed_role", "İzinli rol", 140),
            ("recommended", "Önerilen", 90),
            ("notes", "Not", 360),
        ]:
            self.task_tree.heading(col, text=label)
            self.task_tree.column(col, width=width, anchor="w")
        self.task_tree.pack(fill=tk.BOTH, expand=True)

    def _build_guard_panel(self) -> None:
        card = ttk.LabelFrame(self.guard_frame, text="Veri Uygunluk Kontrolü", padding=8)
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.guard_text = tk.Text(card, height=12, wrap="word", bg="#FFFFFF", fg=COLORS["text"], relief="flat")
        self.guard_text.pack(fill=tk.BOTH, expand=True)

    def _build_result_panel(self) -> None:
        card = ttk.LabelFrame(self.result_frame, text="Governed Benchmark Sonuçları", padding=8)
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        controls = ttk.Frame(card)
        controls.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(controls, text="Görev").pack(side=tk.LEFT)
        self.governed_task_cb = ttk.Combobox(controls, state="readonly", values=["classification", "ranking", "clustering", "allocation"], width=16)
        self.governed_task_cb.set("classification")
        self.governed_task_cb.pack(side=tk.LEFT, padx=6)
        ttk.Label(controls, text="Algoritmalar").pack(side=tk.LEFT)
        self.governed_algorithms_entry = ttk.Entry(controls, width=32)
        self.governed_algorithms_entry.insert(0, "majority_class_predictor")
        self.governed_algorithms_entry.pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Governed Benchmark Çalıştır", command=self.execute_governed_run).pack(side=tk.LEFT, padx=6)
        columns = ("id", "task", "samples", "features", "status", "metric", "started")
        self.run_tree = ttk.Treeview(card, columns=columns, show="headings", height=7)
        for col, label, width in [
            ("id", "Run ID", 80),
            ("task", "Görev", 150),
            ("samples", "Örnek", 80),
            ("features", "Özellik", 80),
            ("status", "Durum", 110),
            ("metric", "Ana metrik", 140),
            ("started", "Başlangıç", 170),
        ]:
            self.run_tree.heading(col, text=label)
            self.run_tree.column(col, width=width, anchor="w")
        self.run_tree.pack(fill=tk.BOTH, expand=True)
        self.run_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_run_select())
        self.detail_tabs = ttk.Notebook(card)
        self.detail_tabs.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.detail_previews = {}
        for key, title in [
            ("metrics", "Metrikler"),
            ("validation", "Validation"),
            ("statistics", "Statistics"),
            ("diagnostics", "Diagnostics"),
            ("leakage", "Leakage"),
            ("clustering", "Clustering"),
        ]:
            frame = ttk.Frame(self.detail_tabs)
            self.detail_tabs.add(frame, text=title)
            preview = JsonPreviewWidget(frame, height=8)
            preview.pack(fill=tk.BOTH, expand=True)
            self.detail_previews[key] = preview

    def load_data(self) -> None:
        def worker():
            return {
                "governance": self.api.get_algorithm_governance(),
                "tasks": self.api.get_algorithm_tasks(),
                "runs": self.api.get_governed_runs(),
            }

        def success(result: dict[str, Any]) -> None:
            used_mock = any(item.used_mock for item in result.values())
            self.source_badge.set_source(used_mock)
            if used_mock:
                self.banner.show("Backend API erişilemiyor; örnek algoritma yönetişimi verisi gösteriliyor.", level="warning")
            governance = result["governance"]
            tasks = result["tasks"]
            runs = result["runs"]
            self._fill_roles(_extract_data(governance.data))
            self._fill_tasks(_extract_data(tasks.data))
            self._fill_runs(_extract_data(runs.data))
            self._fill_guard_text(_extract_data(governance.data))

        def error(exc: Exception) -> None:
            self.banner.show(f"Algoritma yönetişimi verisi alınamadı: {exc}")

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return

        run_async(self, worker, success, error)

    def _fill_roles(self, rows: list[dict[str, Any]]) -> None:
        self.role_tree.delete(*self.role_tree.get_children())
        for row in rows:
            metrics = row.get("recommended_metrics") or []
            self.role_tree.insert(
                "",
                "end",
                values=(
                    row.get("display_name") or row.get("algorithm_key"),
                    row.get("algorithm_family"),
                    row.get("task_type"),
                    _role_label(row.get("usage_role")),
                    "Evet" if row.get("can_affect_final_decision") else "Hayır",
                    row.get("minimum_sample_count"),
                    ", ".join(metrics[:4]),
                    row.get("user_facing_warning") or "",
                ),
            )

    def _fill_tasks(self, rows: list[dict[str, Any]]) -> None:
        self.task_tree.delete(*self.task_tree.get_children())
        for row in rows:
            self.task_tree.insert(
                "",
                "end",
                values=(
                    row.get("task_key"),
                    row.get("algorithm_key"),
                    _role_label(row.get("allowed_usage_role")),
                    "Evet" if row.get("is_recommended") else "Hayır",
                    row.get("notes") or "",
                ),
            )

    def _fill_runs(self, rows: list[dict[str, Any]]) -> None:
        self.run_tree.delete(*self.run_tree.get_children())
        for row in rows:
            self.run_tree.insert(
                "",
                "end",
                values=(
                    row.get("id"),
                    row.get("task_type"),
                    row.get("sample_count"),
                    row.get("feature_count"),
                    row.get("status"),
                    row.get("primary_metric_name"),
                    row.get("started_at"),
                ),
            )
        if self.run_tree.get_children():
            first = self.run_tree.get_children()[0]
            self.run_tree.selection_set(first)
            self._on_run_select()

    def _fill_guard_text(self, rows: list[dict[str, Any]]) -> None:
        blocked = [row for row in rows if row.get("usage_role") in {"benchmark_only", "experimental"}]
        text = [
            "Veri uygunluk kontrolü her benchmark çalıştırmasından önce registry kurallarına göre yapılır.",
            "",
            "Öne çıkan güvenlik kuralları:",
            "- Benchmark-only algoritmalar final kararı etkileyemez.",
            "- XGBoost/GradientBoosting minimum veri eşiği sağlanmadan production/advisory kullanıma açılmaz.",
            "- Classification görevlerinde tek sınıf veya yetersiz sınıf örneği engellenir.",
            "- Clustering sonuçları keşifsel analiz olarak raporlanır.",
            "",
            f"Benchmark/deneysel rolündeki algoritma sayısı: {len(blocked)}",
        ]
        self.guard_text.delete("1.0", tk.END)
        self.guard_text.insert("1.0", "\n".join(text))

    def _on_role_select(self) -> None:
        selection = self.role_tree.selection()
        if not selection:
            return
        values = self.role_tree.item(selection[0], "values")
        text = [
            f"Algoritma: {values[0]}",
            f"Aile: {values[1]}",
            f"Görev: {values[2]}",
            f"Kullanım rolü: {values[3]}",
            f"Final karara etki: {values[4]}",
            f"Minimum veri: {values[5]}",
            f"Önerilen metrikler: {values[6]}",
            "",
            "Canlı guard özeti:",
            "- Minimum veri eşiği sağlanmadan algoritma çalıştırması karar hattına alınmamalıdır.",
            "- Benchmark-only veya deneysel roller final kararı etkileyemez.",
        ]
        if values[7]:
            text.append(f"- Uyarı: {values[7]}")
        self.guard_text.delete("1.0", tk.END)
        self.guard_text.insert("1.0", "\n".join(text))

    def _on_run_select(self) -> None:
        selection = self.run_tree.selection()
        if not selection:
            return
        values = self.run_tree.item(selection[0], "values")
        run_id = values[0]
        self.load_run_detail(run_id)

    def load_run_detail(self, run_id: int | str) -> None:
        def worker():
            return {
                "metrics": self.api.get_governed_run_metrics(run_id),
                "validation": self.api.get_governed_run_validation(run_id),
                "statistics": self.api.get_governed_run_statistics(run_id),
                "diagnostics": self.api.get_governed_run_diagnostics(run_id),
                "leakage": self.api.get_governed_run_leakage(run_id),
                "clustering": self.api.get_governed_run_clustering(run_id),
            }

        def success(result: dict[str, Any]) -> None:
            if any(item.used_mock for item in result.values()):
                self.banner.show("Governed run detayı API'den alınamadı; örnek detay gösteriliyor.", level="warning")
            for key, api_result in result.items():
                self.detail_previews[key].set_json(_extract_data(api_result.data))

        def error(exc: Exception) -> None:
            self.banner.show(f"Governed run detayı alınamadı: {exc}")

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)

    def execute_governed_run(self) -> None:
        algorithms = [item.strip() for item in self.governed_algorithms_entry.get().split(",") if item.strip()]
        payload = {
            "task_type": self.governed_task_cb.get(),
            "task_key": "course_status_classification",
            "algorithms": algorithms or ["majority_class_predictor"],
            "dataset_name": "desktop_governed_sample",
            "X": [[0.1], [0.8], [0.4], [0.9]],
            "y_true": [0, 1, 0, 1],
            "feature_names": ["success_rate"],
            "target_column": "status",
            "created_by": "desktop-ui",
        }

        def worker():
            return self.api.execute_governed_run(payload)

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erişilemiyor; örnek governed benchmark sonucu gösteriliyor.", level="warning")
            else:
                self.banner.show("Governed benchmark çalıştırması tamamlandı.", level="warning")
            self.load_data()

        def error(exc):
            self.banner.show(f"Governed benchmark çalıştırılamadı: {exc}")

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)


def _extract_data(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("algorithms"), list):
            return data["algorithms"]
        if isinstance(data, list):
            return data
        for key in ("algorithms", "tasks", "runs"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return payload if isinstance(payload, list) else []


def _role_label(role: str | None) -> str:
    return {
        "production_decision": "Ana karar motoru",
        "advisory_ml": "Destekleyici ML",
        "benchmark_only": "Sadece benchmark",
        "experimental": "Deneysel",
        "baseline": "Baseline",
    }.get(str(role or ""), str(role or ""))

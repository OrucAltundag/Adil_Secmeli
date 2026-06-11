from __future__ import annotations

import csv
import json
from datetime import datetime, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    DataTable,
    ErrorBanner,
    JsonPreviewWidget,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    run_async,
)


class RunHistoryPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.runs = []
        self.filtered_runs = []
        self.last_detail: dict | None = None
        self._build()
        self.load_runs()

    def _build(self) -> None:
        SectionHeader(self, "Çalıştırma Geçmişi", "Geçmiş benchmark çalışmalarını listeleyin, detaylarını görüntüleyin ve karşılaştırmaya hazırlayın.").pack(fill=tk.X)
        PageInfoBox(
            self,
            "Daha önce yapılan benchmark deneylerinin kayıtlarını ve ayrıntılarını gösterir.",
            "Filtreleri kullanarak run listesini daraltın; Detay Görüntüle ile JSON çıktısını inceleyin.",
            "Run kayıtları deney hafızasıdır; veri seti ve algoritma versiyonu ile birlikte değerlendirilmelidir.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.pack(fill=tk.X, pady=(6, 0))
        self.banner = ErrorBanner(self)

        filters = ttk.LabelFrame(self, text="Filtreler", padding=10)
        filters.pack(fill=tk.X, pady=(12, 10))
        ttk.Label(filters, text="Tarih Aralığı").grid(row=0, column=0, sticky="w")
        self.date_entry = ttk.Entry(filters, width=20)
        self.date_entry.insert(0, "2024-05-01 - 2024-05-18")
        self.date_entry.grid(row=0, column=1, padx=4)
        ttk.Label(filters, text="Senaryo").grid(row=0, column=2, sticky="w")
        self.scenario_cb = ttk.Combobox(filters, state="readonly", values=["Tümü", "real_mcdm_recommendation", "real_ml_prediction", "allocation_fairness", "clustering_exploration"], width=26)
        self.scenario_cb.set("Tümü")
        self.scenario_cb.grid(row=0, column=3, padx=4)
        ttk.Label(filters, text="Durum").grid(row=0, column=4, sticky="w")
        self.status_cb = ttk.Combobox(filters, state="readonly", values=["Tümü", "completed", "running", "failed"], width=12)
        self.status_cb.set("Tümü")
        self.status_cb.grid(row=0, column=5, padx=4)
        ttk.Label(filters, text="Kaynak").grid(row=0, column=6, sticky="w")
        self.source_cb = ttk.Combobox(filters, state="readonly", values=["Tümü", "Classic JSON", "Governed DB"], width=14)
        self.source_cb.set("Tümü")
        self.source_cb.grid(row=0, column=7, padx=4)
        ttk.Button(filters, text="Filtrele", command=self.apply_filters).grid(row=0, column=8, padx=4)
        ttk.Button(filters, text="Yenile", command=self.load_runs).grid(row=0, column=9, padx=4)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(body, text="Çalıştırma Listesi", padding=8)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        top_actions = ttk.Frame(list_frame)
        top_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(top_actions, text="Detay Görüntüle", command=self.show_detail).pack(side=tk.RIGHT, padx=3)
        ttk.Button(top_actions, text="Karşılaştırmaya Ekle", command=self.compare_selected).pack(side=tk.RIGHT, padx=3)
        ttk.Button(top_actions, text="JSON Export", command=lambda: self.export_detail("json")).pack(side=tk.RIGHT, padx=3)
        ttk.Button(top_actions, text="CSV Export", command=lambda: self.export_detail("csv")).pack(side=tk.RIGHT, padx=3)
        self.table = DataTable(
            list_frame,
            ["run_id", "source", "date", "scenario", "dataset", "algorithms_count", "status", "duration", "accuracy", "f1", "roc_auc", "hit_at_k", "ndcg_at_k", "silhouette", "fairness", "latency"],
            height=12,
            column_labels={
                "run_id": "Run ID",
                "source": "Kaynak",
                "date": "Tarih",
                "scenario": "Senaryo",
                "dataset": "Veri Seti",
                "algorithms_count": "Algoritma",
                "status": "Durum",
                "duration": "Süre",
                "accuracy": "Accuracy",
                "f1": "F1",
                "roc_auc": "ROC-AUC",
                "hit_at_k": "Hit@K",
                "ndcg_at_k": "NDCG@K",
                "silhouette": "Silhouette",
                "fairness": "Adalet",
                "latency": "Gecikme",
            },
        )
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.tree.bind("<Double-1>", lambda _e: self.show_detail())

        detail_frame = ttk.LabelFrame(body, text="Run Detayı", padding=8)
        detail_frame.grid(row=0, column=1, sticky="nsew")
        self.detail_tabs = ttk.Notebook(detail_frame)
        self.detail_tabs.pack(fill=tk.BOTH, expand=True)
        self.summary_tab = ttk.Frame(self.detail_tabs)
        self.metrics_tab = ttk.Frame(self.detail_tabs)
        self.validation_tab = ttk.Frame(self.detail_tabs)
        self.diagnostics_tab = ttk.Frame(self.detail_tabs)
        self.leakage_tab = ttk.Frame(self.detail_tabs)
        self.raw_json_tab = ttk.Frame(self.detail_tabs)
        self.detail_tabs.add(self.summary_tab, text="Özet")
        self.detail_tabs.add(self.metrics_tab, text="Metrikler")
        self.detail_tabs.add(self.validation_tab, text="Validation")
        self.detail_tabs.add(self.diagnostics_tab, text="Diagnostics")
        self.detail_tabs.add(self.leakage_tab, text="Leakage")
        self.detail_tabs.add(self.raw_json_tab, text="Ham JSON")
        self.summary_table = DataTable(self.summary_tab, ["Alan", "Deger"], height=8, column_labels={"Alan": "Alan", "Deger": "Değer"})
        self.summary_table.pack(fill=tk.BOTH, expand=True)
        self.metrics_table = None
        self.validation_text = self._text_panel(self.validation_tab)
        self.diagnostics_text = self._text_panel(self.diagnostics_tab)
        self.leakage_text = self._text_panel(self.leakage_tab)
        self.json_preview = JsonPreviewWidget(self.raw_json_tab, height=18)
        self.json_preview.pack(fill=tk.BOTH, expand=True)

    def load_runs(self) -> None:
        def worker():
            result = {"classic": self.api.get_runs()}
            if hasattr(self.api, "get_governed_runs"):
                result["governed"] = self.api.get_governed_runs()
            return result

        def success(result):
            classic = result["classic"]
            governed = result.get("governed")
            used_mock = bool(classic.used_mock or (governed and governed.used_mock))
            self.source_badge.set_source(used_mock)
            if used_mock:
                self.banner.show("Backend API erişilemiyor; örnek çalıştırma geçmişi gösteriliyor.", level="warning")
            classic_rows = self._normalize_runs(classic.data.get("runs", mock_data.RUNS), source="Classic JSON")
            governed_rows = self._normalize_governed_runs(_extract_rows(governed.data) if governed else [])
            self.runs = classic_rows + governed_rows
            self.apply_filters()
            if self.runs:
                self._load_detail_tabs({"summary": self.runs[0]})

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            success(worker())
            return
        run_async(self, worker, success)

    def _normalize_runs(self, runs, source: str = "Classic JSON"):
        normalized = []
        for item in runs:
            if "run_id" in item:
                row = dict(item)
                row.setdefault("source", source)
                normalized.append(row)
                continue
            run = item.get("run", item)
            normalized.append(
                {
                    "run_id": run.get("run_id", "-"),
                    "source": source,
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

    def _normalize_governed_runs(self, rows):
        normalized = []
        for row in rows:
            run_id = row.get("id") or row.get("run_id")
            normalized.append(
                {
                    "run_id": f"governed:{run_id}",
                    "source": "Governed DB",
                    "date": row.get("started_at") or row.get("created_at") or "-",
                    "scenario": row.get("task_type") or row.get("task_key") or "-",
                    "dataset": row.get("dataset_name") or "governed_dataset",
                    "algorithms_count": len(row.get("algorithms") or []) if isinstance(row.get("algorithms"), list) else 1,
                    "status": row.get("status", "-"),
                    "duration": "-",
                    "accuracy": "",
                    "f1": "",
                    "roc_auc": "",
                    "hit_at_k": "",
                    "ndcg_at_k": "",
                    "silhouette": "",
                    "fairness": row.get("primary_metric_value", ""),
                    "latency": "",
                    "governed_id": run_id,
                }
            )
        return normalized

    def apply_filters(self) -> None:
        rows = self.runs or mock_data.RUNS
        scenario = self.scenario_cb.get()
        status = self.status_cb.get()
        source = self.source_cb.get()
        start_date, end_date = _parse_date_range(self.date_entry.get())
        if scenario != "Tümü":
            rows = [r for r in rows if r.get("scenario") == scenario]
        if status != "Tümü":
            rows = [r for r in rows if r.get("status") == status]
        if source != "Tümü":
            rows = [r for r in rows if r.get("source") == source]
        if start_date or end_date:
            rows = [r for r in rows if _date_in_range(_row_datetime(r), start_date, end_date)]
        self.filtered_runs = list(rows)
        self.table.set_rows(rows)

    def show_detail(self) -> None:
        values = self.table.selected_values()
        run_id = values[0] if values else (self.runs[0]["run_id"] if self.runs else mock_data.RUNS[0]["run_id"])
        selected_row = next((row for row in self.runs if str(row.get("run_id")) == str(run_id)), None)
        if selected_row and selected_row.get("source") == "Governed DB":
            governed_id = selected_row.get("governed_id") or run_id

            def gov_worker():
                return self.api.get_governed_run_leakage(governed_id)

            def gov_success(leakage_result):
                detail = {
                    "summary": selected_row,
                    "details": {
                        "diagnostics": "Governed run metrik/validation/diagnostics ayrıntıları Algoritma Yönetişimi sayfasındaki alt panellerde gösterilir.",
                        "validation": "Governed DB kaydı klasik JSON run değildir; kaynak filtresiyle birlikte tek geçmiş listesinde görünür.",
                        "leakage": _format_leakage(leakage_result.data),
                    },
                }
                self._load_detail_tabs(detail)

            if self.api.__class__.__name__ != "BenchmarkApiClient":
                gov_success(gov_worker())
            else:
                run_async(self, gov_worker, gov_success)
            return

        def worker():
            detail_result = self.api.get_run_detail(run_id)
            leakage_result = self.api.get_governed_run_leakage(run_id)
            return {"detail": detail_result, "leakage": leakage_result}

        def success(result):
            detail_result = result["detail"]
            leakage_result = result["leakage"]
            if detail_result.used_mock:
                self.banner.show("Run detayı API'den alınamadı; örnek JSON gösteriliyor.", level="warning")
            data = detail_result.data
            if not isinstance(data.get("details"), dict):
                data["details"] = {}
            if not data["details"].get("leakage"):
                data["details"]["leakage"] = _format_leakage(leakage_result.data)
            self.last_detail = data
            self._load_detail_tabs(data)

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            success(worker())
            return
        run_async(self, worker, success)

    def compare_selected(self) -> None:
        selected = self.table.selected_values()
        run_id = selected[0] if selected else "seçili run yok"
        if run_id == "seçili run yok":
            self.banner.show("Karşılaştırmaya eklemek için bir run seçin.", level="warning")
            return
        selected_row = next((row for row in self.runs if str(row.get("run_id")) == str(run_id)), None)
        if selected_row and selected_row.get("source") == "Governed DB":
            self.banner.show("Governed DB run'ları tek geçmişte görünür; klasik karşılaştırma sepetine sadece Classic JSON run'ları eklenir.", level="warning")
            return
        basket = getattr(self.api, "selected_run_ids_for_comparison", [])
        if run_id not in basket:
            basket.append(str(run_id))
        self.api.selected_run_ids_for_comparison = basket
        self.banner.show(f"{run_id} karşılaştırma sepetine eklendi. Algoritma Karşılaştırma ekranında seçili run bilgisi kullanılabilir.", level="warning")

    def export_detail(self, export_format: str) -> None:
        detail = self.last_detail or {"summary": self.filtered_runs[0] if self.filtered_runs else {}}
        run_id = (detail.get("summary") or {}).get("run_id") or "selected_run"
        out_dir = Path("reports/benchmark_exports")
        out_dir.mkdir(parents=True, exist_ok=True)
        if export_format == "csv":
            path = out_dir / f"{run_id}.csv"
            rows = detail.get("comparison_table") or []
            columns = sorted({key for row in rows if isinstance(row, dict) for key in row.keys()})
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns or ["message"])
                writer.writeheader()
                if rows:
                    writer.writerows(rows)
                else:
                    writer.writerow({"message": "Metrik satırı bulunamadı."})
        else:
            path = out_dir / f"{run_id}.json"
            path.write_text(json.dumps(detail, indent=2, ensure_ascii=False), encoding="utf-8")
        self.banner.show(f"Run detayı dışa aktarıldı: {path}", level="warning")

    def _load_detail_tabs(self, detail: dict) -> None:
        self.last_detail = detail
        summary = detail.get("summary") or {}
        self.summary_table.set_rows([{"Alan": key, "Deger": value} for key, value in summary.items()])
        self._set_metrics_rows(detail.get("comparison_table") or [])
        raw_details = detail.get("details")
        details: dict = raw_details if isinstance(raw_details, dict) else {}
        self._set_text(self.validation_text, details.get("validation") or "Validation detayı bu run kaydında bulunamadı.")
        self._set_text(self.diagnostics_text, details.get("diagnostics") or "Diagnostics detayı bu run kaydında bulunamadı.")
        self._set_text(self.leakage_text, details.get("leakage") or "Leakage detayı bu run kaydında bulunamadı.")
        self.json_preview.set_json(detail)

    def _set_metrics_rows(self, rows: list[dict]) -> None:
        if self.metrics_table is not None:
            self.metrics_table.destroy()
        columns = sorted({key for row in rows if isinstance(row, dict) for key in row.keys()})
        if not columns:
            columns = ["Bilgi"]
            rows = [{"Bilgi": "Metrik satırı bulunamadı."}]
        self.metrics_table = DataTable(self.metrics_tab, columns, height=10)
        self.metrics_table.pack(fill=tk.BOTH, expand=True)
        self.metrics_table.set_rows(rows)

    def _text_panel(self, parent) -> tk.Text:
        text = tk.Text(parent, height=12, wrap="word", bg="#F8FAFC", relief="solid", bd=1)
        text.pack(fill=tk.BOTH, expand=True)
        text.configure(state="disabled")
        return text

    def _set_text(self, widget: tk.Text, value) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False))
        widget.configure(state="disabled")


def _format_leakage(leakage_data: dict) -> str:
    if not leakage_data:
        return "Leakage verisi bulunamadı."
    items = leakage_data.get("data") or []
    if not items:
        return "Leakage kaydı yok."
    lines = []
    for item in items:
        algo = item.get("algorithm_key", "?")
        detected = item.get("leakage_detected", False)
        blocked = item.get("blocked", False)
        summary = item.get("summary_text", "")
        status = "⚠️ TESPİT EDİLDİ" if detected else "✓ Temiz"
        block_info = " [ENGELLENDİ]" if blocked else ""
        lines.append(f"{algo}: {status}{block_info}")
        if summary:
            lines.append(f"  {summary}")
    return "\n".join(lines)


def _parse_date_range(text: str) -> tuple[datetime | None, datetime | None]:
    raw = str(text or "").strip()
    if not raw:
        return None, None
    parts = [part.strip() for part in raw.split(" - ", 1)]
    if len(parts) == 1:
        return _parse_date(parts[0], end_of_day=False), _parse_date(parts[0], end_of_day=True)
    return _parse_date(parts[0], end_of_day=False), _parse_date(parts[1], end_of_day=True)


def _parse_date(value: str, *, end_of_day: bool) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(value[:19], fmt)
            if end_of_day and fmt in {"%Y-%m-%d", "%d.%m.%Y"}:
                return datetime.combine(parsed.date(), time.max)
            return parsed
        except ValueError:
            continue
    return None


def _row_datetime(row: dict) -> datetime | None:
    return _parse_date(str(row.get("date") or row.get("started_at") or ""), end_of_day=False)


def _date_in_range(value: datetime | None, start: datetime | None, end: datetime | None) -> bool:
    if value is None:
        return True
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True


def _extract_rows(payload) -> list[dict]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        for key in ("runs", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return payload if isinstance(payload, list) else []

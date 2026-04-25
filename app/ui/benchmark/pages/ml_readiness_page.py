from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark.widgets import COLORS, DataTable, ErrorBanner, JsonPreviewWidget, MetricCard, SectionHeader, run_async


class MLReadinessPage(ttk.Frame):
    """Benchmark Platformu içinde ML güvenilirlik ve hazırlık paneli."""

    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self._build()
        self.load_data()

    def _build(self) -> None:
        SectionHeader(
            self,
            "ML Güvenilirlik & Hazırlık",
            "ML çıktıları destekleyici/deneysel niteliktedir; nihai karar AHP/TOPSIS + kurallar + state machine tarafından verilir.",
        ).pack(fill=tk.X)
        self.banner = ErrorBanner(self)
        self.banner.show(
            "Mevcut veri miktarı düşük olduğunda ML modelleri nihai karar verici olarak kullanılmaz.",
            level="warning",
        )

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X, pady=(10, 8))
        self.sample_card = MetricCard(cards, "Eğitim Örneği", "-", "Ders-yıl kaydı", accent=COLORS["blue"])
        self.not_ready_card = MetricCard(cards, "Hazır Değil", "-", "Algoritma sayısı", accent=COLORS["orange"])
        self.production_card = MetricCard(cards, "Production-ready", "-", "Varsayılan etki: kapalı", accent=COLORS["green"])
        for idx, card in enumerate([self.sample_card, self.not_ready_card, self.production_card]):
            card.grid(row=0, column=idx, sticky="nsew", padx=4)
            cards.columnconfigure(idx, weight=1)

        body = ttk.PanedWindow(self, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True)

        top = ttk.LabelFrame(body, text="Algoritma Hazırlık Tablosu", padding=8)
        bottom = ttk.PanedWindow(body, orient=tk.HORIZONTAL)
        body.add(top, weight=3)
        body.add(bottom, weight=2)

        self.readiness_table = DataTable(
            top,
            ["Algoritma", "Rol", "Örnek", "Minimum", "Seviye", "Eğitilebilir", "Production-ready", "Uyarılar"],
            height=10,
        )
        self.readiness_table.pack(fill=tk.BOTH, expand=True)

        runs_frame = ttk.LabelFrame(bottom, text="Model Eğitim Çalışmaları", padding=8)
        preds_frame = ttk.LabelFrame(bottom, text="Tahminler ve Fallback", padding=8)
        bottom.add(runs_frame, weight=1)
        bottom.add(preds_frame, weight=1)

        self.runs_table = DataTable(runs_frame, ["ID", "Algoritma", "Versiyon", "Örnek", "Seviye", "Durum", "Skip Nedeni"], height=8)
        self.runs_table.pack(fill=tk.BOTH, expand=True)

        self.prediction_preview = JsonPreviewWidget(preds_frame, height=10)
        self.prediction_preview.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btns, text="Yenile", command=self.load_data).pack(side=tk.RIGHT)

    def load_data(self) -> None:
        def worker():
            return {
                "readiness": self.api.get_ml_readiness(),
                "runs": self.api.get_ml_model_runs(),
                "predictions": self.api.get_ml_predictions(),
            }

        def success(result):
            readiness_result = result["readiness"]
            if readiness_result.used_mock:
                self.banner.show("Backend API erişilemiyor; mock ML readiness verisi gösteriliyor.", level="warning")
            rows = readiness_result.data.get("data", readiness_result.data.get("algorithm_readiness", []))
            self._load_readiness(rows)
            self._load_runs(result["runs"].data.get("data", []))
            self.prediction_preview.set_json(result["predictions"].data.get("data", []))

        def error(exc):
            self.banner.show(f"ML hazırlık verisi alınamadı: {exc}")

        run_async(self, worker, success, error)

    def _load_readiness(self, rows: list[dict]) -> None:
        sample_count = max([int(row.get("sample_count") or 0) for row in rows] or [0])
        not_ready = len([row for row in rows if row.get("readiness_level") in {"not_ready", "low"}])
        production = len([row for row in rows if row.get("can_use_for_production_decision")])
        self.sample_card.set_value(sample_count)
        self.not_ready_card.set_value(not_ready)
        self.production_card.set_value(production)
        table_rows = []
        for row in rows:
            warnings = "; ".join((row.get("warnings") or row.get("blocking_reasons") or [])[:2])
            table_rows.append(
                {
                    "Algoritma": row.get("algorithm_key"),
                    "Rol": row.get("usage_role"),
                    "Örnek": row.get("sample_count"),
                    "Minimum": row.get("required_min_samples"),
                    "Seviye": row.get("readiness_level"),
                    "Eğitilebilir": "Evet" if row.get("can_train") else "Hayır",
                    "Production-ready": "Evet" if row.get("can_use_for_production_decision") else "Hayır",
                    "Uyarılar": warnings,
                }
            )
        self.readiness_table.set_rows(table_rows)

    def _load_runs(self, rows: list[dict]) -> None:
        table_rows = []
        for row in rows[:50]:
            table_rows.append(
                {
                    "ID": row.get("id"),
                    "Algoritma": row.get("algorithm_key"),
                    "Versiyon": row.get("model_version"),
                    "Örnek": row.get("training_sample_count"),
                    "Seviye": row.get("readiness_level"),
                    "Durum": row.get("status"),
                    "Skip Nedeni": row.get("skip_reason"),
                }
            )
        self.runs_table.set_rows(table_rows)

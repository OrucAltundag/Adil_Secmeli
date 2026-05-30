from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any

from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    JsonPreviewWidget,
    MetricCard,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    run_async,
)


def _yes_no(value: Any) -> str:
    return "Evet" if bool(value) else "Hayır"


def _short_reason(row: dict[str, Any]) -> str:
    reasons = row.get("uncertainty_reasons") or row.get("fallback_reasons") or []
    if isinstance(reasons, list) and reasons:
        return "; ".join(str(item) for item in reasons[:2])
    if isinstance(reasons, str) and reasons:
        return reasons
    return str(row.get("fallback_reason") or row.get("explanation") or "—")


def format_prediction_row(row: dict[str, Any]) -> dict[str, Any]:
    """Translate raw ML prediction governance flags into visible Turkish badges."""
    confidence = row.get("confidence_level", row.get("confidence_score", row.get("confidence")))
    return {
        "ID": row.get("id", "—"),
        "Algoritma": row.get("algorithm_key", "—"),
        "Fallback": _yes_no(row.get("fallback_used")),
        "Advisory": _yes_no(row.get("advisory_only")),
        "Karara Etki": _yes_no(row.get("should_influence_decision")),
        "Güven": confidence if confidence not in {None, ""} else "—",
        "Neden": _short_reason(row),
    }


class MLReadinessPage(ttk.Frame):
    """Benchmark Platformu içinde ML güvenilirlik ve hazırlık paneli."""

    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.readiness_rows: list[dict[str, Any]] = []
        self.report_rows: list[dict[str, Any]] = []
        self.feature_summary: dict[str, Any] = {}
        self._build()
        self.load_data()

    def _build(self) -> None:
        SectionHeader(
            self,
            "ML Güvenilirlik & Hazırlık",
            "ML çıktıları destekleyici/deneysel niteliktedir; nihai karar AHP/TOPSIS + kurallar + state machine tarafından verilir.",
        ).pack(fill=tk.X)
        PageInfoBox(
            self,
            "Makine öğrenmesi modellerinin veri açısından eğitilebilir ve güvenilir olup olmadığını gösterir.",
            "Hazırlık tablosunda örnek sayısı, minimum veri ihtiyacı, eğitilebilirlik ve production-ready durumunu kontrol edin.",
            "Veri yetersizse model çalıştırılmamalı veya sadece advisory/fallback sonucu olarak gösterilmelidir.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.pack(fill=tk.X, pady=(6, 0))
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
            column_labels={"Production-ready": "Üretim Kararına Hazır"},
        )
        self.readiness_table.pack(fill=tk.BOTH, expand=True)

        runs_frame = ttk.LabelFrame(bottom, text="Model Eğitim Çalışmaları", padding=8)
        preds_frame = ttk.LabelFrame(bottom, text="Tahminler ve Fallback", padding=8)
        bottom.add(runs_frame, weight=1)
        bottom.add(preds_frame, weight=1)

        self.runs_table = DataTable(
            runs_frame,
            ["ID", "Algoritma", "Versiyon", "Örnek", "Seviye", "Durum", "Skip Nedeni"],
            height=8,
            column_labels={"Skip Nedeni": "Atlama Nedeni"},
        )
        self.runs_table.pack(fill=tk.BOTH, expand=True)

        self.ml_tabs = ttk.Notebook(preds_frame)
        self.ml_tabs.pack(fill=tk.BOTH, expand=True)
        prediction_tab = ttk.Frame(self.ml_tabs, padding=6)
        reports_tab = ttk.Frame(self.ml_tabs, padding=6)
        feature_tab = ttk.Frame(self.ml_tabs, padding=6)
        self.ml_tabs.add(prediction_tab, text="Tahmin Rozetleri")
        self.ml_tabs.add(reports_tab, text="Rapor Geçmişi")
        self.ml_tabs.add(feature_tab, text="Feature Özeti")

        self.prediction_table = DataTable(
            prediction_tab,
            ["ID", "Algoritma", "Fallback", "Advisory", "Karara Etki", "Güven", "Neden"],
            height=7,
        )
        self.prediction_table.pack(fill=tk.BOTH, expand=True)
        self.reports_table = DataTable(reports_tab, ["ID", "Tarih", "Örnek", "Özet"], height=7)
        self.reports_table.pack(fill=tk.BOTH, expand=True)
        self.feature_preview = JsonPreviewWidget(feature_tab, height=8)
        self.feature_preview.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(self)
        btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btns, text="Feature Özeti", command=self.show_feature_summary).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text="Snapshot Üret", command=self.build_snapshot).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Model Train", command=self.train_model).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Readiness Raporu", command=self.create_report).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Rapor Export", command=self.export_report).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Yenile", command=self.load_data).pack(side=tk.RIGHT)

    def load_data(self) -> None:
        def worker():
            return {
                "readiness": self.api.get_ml_readiness(),
                "runs": self.api.get_ml_model_runs(),
                "predictions": self.api.get_ml_predictions(),
                "reports": self.api.get_ml_readiness_reports(),
            }

        def success(result):
            readiness_result = result["readiness"]
            self.source_badge.set_source(readiness_result.used_mock)
            if readiness_result.used_mock:
                self.banner.show("Backend API erişilemiyor; mock ML readiness verisi gösteriliyor.", level="warning")
            rows = readiness_result.data.get("data", readiness_result.data.get("algorithm_readiness", []))
            self._load_readiness(rows)
            self._load_runs(result["runs"].data.get("data", []))
            self._load_predictions(result["predictions"].data.get("data", []))
            self._load_reports(result["reports"].data.get("data", []))

        def error(exc):
            self.banner.show(f"ML hazırlık verisi alınamadı: {exc}")

        self._run_api_action(worker, success, error)

    def _load_readiness(self, rows: list[dict]) -> None:
        self.readiness_rows = rows if isinstance(rows, list) else []
        sample_count = max([int(row.get("sample_count") or 0) for row in self.readiness_rows] or [0])
        not_ready = len([row for row in self.readiness_rows if row.get("readiness_level") in {"not_ready", "low"}])
        production = len([row for row in self.readiness_rows if row.get("can_use_for_production_decision")])
        self.sample_card.set_value(sample_count)
        self.not_ready_card.set_value(not_ready)
        self.production_card.set_value(production)
        table_rows = []
        for row in self.readiness_rows:
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
        if not table_rows:
            table_rows.append(
                {
                    "Algoritma": "Kayıt yok",
                    "Rol": "—",
                    "Örnek": 0,
                    "Minimum": "—",
                    "Seviye": "Veri bulunamadı",
                    "Eğitilebilir": "Hayır",
                    "Production-ready": "Hayır",
                    "Uyarılar": "Backend veya veri kaydı yok.",
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
        if not table_rows:
            table_rows.append(
                {
                    "ID": "—",
                    "Algoritma": "Kayıt yok",
                    "Versiyon": "—",
                    "Örnek": "—",
                    "Seviye": "—",
                    "Durum": "Henüz model eğitimi yok",
                    "Skip Nedeni": "—",
                }
            )
        self.runs_table.set_rows(table_rows)

    def _load_predictions(self, rows: list[dict]) -> None:
        table_rows = [format_prediction_row(row) for row in rows[:50]]
        if not table_rows:
            table_rows.append(
                {
                    "ID": "—",
                    "Algoritma": "Kayıt yok",
                    "Fallback": "—",
                    "Advisory": "—",
                    "Karara Etki": "—",
                    "Güven": "—",
                    "Neden": "Henüz ML tahmin kaydı yok.",
                }
            )
        self.prediction_table.set_rows(table_rows)

    def _load_reports(self, rows: list[dict]) -> None:
        self.report_rows = rows if isinstance(rows, list) else []
        table_rows = []
        for row in self.report_rows[:50]:
            table_rows.append(
                {
                    "ID": row.get("id") or row.get("report_id"),
                    "Tarih": row.get("created_at") or "—",
                    "Örnek": row.get("sample_count", "—"),
                    "Özet": row.get("summary_text") or row.get("summary") or "—",
                }
            )
        if not table_rows:
            table_rows.append({"ID": "—", "Tarih": "—", "Örnek": "—", "Özet": "Henüz readiness raporu yok."})
        self.reports_table.set_rows(table_rows)

    def show_feature_summary(self) -> None:
        def worker():
            return self.api.get_ml_feature_summary()

        def success(result):
            self.feature_summary = result.data.get("data", result.data)
            self.feature_preview.set_json(self.feature_summary)
            if result.used_mock:
                self.banner.show("Backend API erişilemiyor; örnek feature özeti gösteriliyor.", level="warning")
            else:
                self.banner.show("Feature özeti üretildi.", level="warning")

        def error(exc):
            self.banner.show(f"Feature özeti alınamadı: {exc}")

        self._run_api_action(worker, success, error)

    def build_snapshot(self) -> None:
        def worker():
            return self.api.build_ml_feature_snapshot({"save_snapshot": True})

        def success(result):
            data = result.data.get("data", result.data)
            self.feature_preview.set_json(data)
            snapshot_id = data.get("snapshot_id", "—") if isinstance(data, dict) else "—"
            self.banner.show(f"Feature snapshot üretildi. Snapshot ID: {snapshot_id}", level="warning")
            self.load_data()

        def error(exc):
            self.banner.show(f"Feature snapshot üretilemedi: {exc}")

        self._run_api_action(worker, success, error)

    def train_model(self) -> None:
        row = self._selected_readiness_row()
        if not row:
            self.banner.show("Model eğitimi için önce hazırlık tablosundan bir algoritma seçin.")
            return
        if not row.get("can_train"):
            reasons = row.get("blocking_reasons") or row.get("warnings") or []
            reason_text = "; ".join(str(item) for item in reasons[:3]) if reasons else "Minimum eğitim örneği sağlanmıyor."
            self.banner.show(
                f"Model train engellendi: {row.get('algorithm_key')} için veri yeterli değil. {reason_text}"
            )
            return

        payload = {"algorithm_key": row.get("algorithm_key"), "created_by": "desktop-ui"}

        def worker():
            return self.api.train_ml_model(payload)

        def success(result):
            data = result.data.get("data", result.data)
            status = data.get("status", "tamamlandı") if isinstance(data, dict) else "tamamlandı"
            self.banner.show(f"Model train isteği tamamlandı. Durum: {status}", level="warning")
            self.load_data()

        def error(exc):
            self.banner.show(f"Model train çalıştırılamadı: {exc}")

        self._run_api_action(worker, success, error)

    def create_report(self) -> None:
        def worker():
            return self.api.create_ml_readiness_report({"save": True})

        def success(result):
            data = result.data.get("data", result.data)
            self.feature_preview.set_json(data)
            report_id = data.get("id") or data.get("report_id") if isinstance(data, dict) else "—"
            self.banner.show(f"ML readiness raporu üretildi. Rapor ID: {report_id}", level="warning")
            self.load_data()

        def error(exc):
            self.banner.show(f"ML readiness raporu üretilemedi: {exc}")

        self._run_api_action(worker, success, error)

    def export_report(self) -> None:
        export_dir = Path("reports") / "ml_readiness_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        target = export_dir / "latest_ml_readiness_report.json"
        payload = {
            "algorithm_readiness": self.readiness_rows,
            "reports": self.report_rows,
            "feature_summary": self.feature_summary,
        }
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.banner.show(f"ML readiness raporu dışa aktarıldı: {target}", level="warning")

    def _selected_readiness_row(self) -> dict[str, Any] | None:
        values = self.readiness_table.selected_values()
        selected_key = values[0] if values else None
        if selected_key:
            for row in self.readiness_rows:
                if str(row.get("algorithm_key")) == str(selected_key):
                    return row
        return self.readiness_rows[0] if self.readiness_rows else None

    def _run_api_action(self, worker, success, error) -> None:
        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)

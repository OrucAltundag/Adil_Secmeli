from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    MetricCard,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    StatusCard,
    run_async,
)


class DashboardPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.algorithm_vars: dict[str, tk.BooleanVar] = {}
        self.metric_cards: dict[str, MetricCard] = {}
        self.status_cards: dict[str, MetricCard] = {}
        self.readiness_cards: dict[str, MetricCard] = {}
        self.algorithms: list[dict] = []
        self.scenarios: list[dict] = list(mock_data.SCENARIOS)
        self.backend_ready = False
        self._build()
        self.load_initial_data()

    def _build(self) -> None:
        SectionHeader(self, "Benchmark Paneli", "Senaryo, veri seti ve algoritma seçerek deney çalıştırın.").pack(fill=tk.X)
        PageInfoBox(
            self,
            "Benchmark deneyini başlatır ve son çalıştırmanın özetini gösterir.",
            "Önce senaryo ve veri setini seçin, sonra bu senaryoya uygun algoritmaları işaretleyip Çalıştır düğmesine basın.",
            "Bu ekran analiz/lab amaçlıdır; sonuçlar nihai ders kararını otomatik değiştirmez.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.pack(fill=tk.X, pady=(8, 0))
        self.banner = ErrorBanner(self)

        controls = ttk.LabelFrame(self, text="Deney Ayarları", padding=10)
        controls.pack(fill=tk.X, pady=(12, 8))
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Senaryo").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.scenario_cb = ttk.Combobox(controls, state="readonly", values=[s["name"] for s in mock_data.SCENARIOS])
        self.scenario_cb.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        self.scenario_cb.set(mock_data.SCENARIOS[0]["name"])
        self.scenario_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_scenario_change())
        # display_name <-> name eslemesi (UI Turkce ad gosterir, backend ingilizce key bekler).
        self._scenario_label_to_key: dict[str, str] = {}

        ttk.Label(controls, text="Veri seti").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.dataset_cb = ttk.Combobox(controls, state="readonly", values=["Yüklü dataset yok"])
        self.dataset_cb.grid(row=0, column=3, sticky="ew", padx=(0, 14))
        self.dataset_cb.set("Yüklü dataset yok")

        btns = ttk.Frame(controls)
        btns.grid(row=0, column=4, sticky="e")
        self.run_btn = ttk.Button(btns, text="Çalıştır", style="Primary.TButton", command=self.run_benchmark)
        self.run_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Temizle", command=self.clear_selection).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="Sonuçları Yenile", command=self.refresh_results).pack(side=tk.LEFT, padx=3)
        # API'yi GUI thread'inden ayri bir thread'de baslat: kullanici CLI'ya
        # gitmek zorunda kalmadan benchmark'i gercek backend ile calistirsin.
        self.start_api_btn = ttk.Button(btns, text="API Başlat", command=self.start_api_background)
        self.start_api_btn.pack(side=tk.LEFT, padx=3)

        # Senaryo aciklama paneli: amac ve sisteme etkisi (Turkce).
        desc_frame = ttk.LabelFrame(controls, text="Senaryo Açıklaması", padding=6)
        desc_frame.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(8, 0))
        self.scenario_purpose_lbl = ttk.Label(
            desc_frame, text="Amaç: -", wraplength=900, justify=tk.LEFT,
        )
        self.scenario_purpose_lbl.pack(anchor="w")
        self.scenario_impact_lbl = ttk.Label(
            desc_frame, text="Sisteme etkisi: -", wraplength=900, justify=tk.LEFT,
            foreground="#0f5132",
        )
        self.scenario_impact_lbl.pack(anchor="w", pady=(4, 0))

        readiness_frame = ttk.LabelFrame(self, text="Benchmark Readiness", padding=10)
        readiness_frame.pack(fill=tk.X, pady=(0, 10))
        for idx, (key, title) in enumerate(
            [
                ("dataset", "Dataset"),
                ("scenario", "Senaryo"),
                ("algorithms", "Algoritma Uyumu"),
                ("backend", "Backend/API"),
            ]
        ):
            card = MetricCard(readiness_frame, title, "Kontrol", "Bekleniyor", accent=COLORS["orange"])
            card.grid(row=0, column=idx, sticky="nsew", padx=4)
            readiness_frame.columnconfigure(idx, weight=1)
            self.readiness_cards[key] = card

        algo_frame = ttk.LabelFrame(self, text="Algoritma Seçimi (çoklu seçim)", padding=10)
        algo_frame.pack(fill=tk.X, pady=(0, 10))
        self.algo_container = ttk.Frame(algo_frame)
        self.algo_container.pack(fill=tk.X)

        cards = ttk.Frame(self)
        cards.pack(fill=tk.X, pady=(0, 10))
        for idx, (key, title, value) in enumerate(
            [
                ("last_run", "Son Çalıştırma", "10:42:31"),
                ("status", "Durum", "Hazır"),
                ("duration", "Süre", "00:00:00"),
                ("algo_count", "Secilen Algoritma", "0"),
                ("dataset_size", "Veri Seti Boyutu", "12.4K"),
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

        summary_frame = ttk.LabelFrame(body, text="Son Çalıştırma Özeti", padding=8)
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.summary_table = DataTable(summary_frame, ["Alan", "Deger"], height=8, column_labels={"Alan": "Alan", "Deger": "Değer"})
        self.summary_table.pack(fill=tk.BOTH, expand=True)

        metrics_frame = ttk.LabelFrame(body, text="Özet Metrikler", padding=8)
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
            self.backend_ready = not (algos_result.used_mock or scenarios_result.used_mock)
            self.source_badge.set_source(not self.backend_ready)
            if algos_result.used_mock or scenarios_result.used_mock:
                self.banner.show(
                    "Backend API erişilemiyor (örnek veri gösteriliyor). "
                    "Çalıştırmak için terminalden: "
                    "python -m app.main --mode api --host 127.0.0.1 --port 8000",
                    level="warning",
                )
            self.algorithms = algos_result.data.get("algorithms", mock_data.ALGORITHMS)
            self.scenarios = scenarios_result.data.get("scenarios", mock_data.SCENARIOS)
            # display_name varsa onu goster, geri yola map'le; yoksa eski davranis.
            self._scenario_label_to_key = {
                (s.get("display_name") or s.get("name") or ""): (s.get("name") or "")
                for s in self.scenarios
            }
            self.scenario_cb["values"] = list(self._scenario_label_to_key.keys())
            current_label = self.scenario_cb.get()
            if (not current_label or current_label not in self._scenario_label_to_key) and self.scenarios:
                first_label = next(iter(self._scenario_label_to_key.keys()))
                self.scenario_cb.set(first_label)
            self._update_scenario_description()
            self._sync_dataset_choices()
            self._render_algorithm_checks(self.algorithms)
            self._update_from_run(mock_data.SAMPLE_RUN)
            self._sync_readiness()

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            success(worker())
            return
        run_async(self, worker, success)

    def _render_algorithm_checks(self, algorithms) -> None:
        for child in self.algo_container.winfo_children():
            child.destroy()
        self.algorithm_vars.clear()
        allowed = set(self._scenario_default_algorithms())
        visible = [item for item in algorithms if not allowed or (item.get("name") or str(item)) in allowed]
        for idx, item in enumerate(visible):
            name = item.get("name") or str(item)
            var = tk.BooleanVar(value=name in allowed)
            self.algorithm_vars[name] = var
            cb = ttk.Checkbutton(self.algo_container, text=name, variable=var, command=self._sync_algo_count)
            cb.grid(row=idx // 5, column=idx % 5, sticky="w", padx=8, pady=3)
        self._sync_algo_count()

    def _sync_algo_count(self) -> None:
        count = len(self.selected_algorithms())
        self.status_cards["algo_count"].set_value(count, "Seçili")
        self._sync_readiness()

    def selected_algorithms(self) -> list[str]:
        return [name for name, var in self.algorithm_vars.items() if var.get()]

    def clear_selection(self) -> None:
        for var in self.algorithm_vars.values():
            var.set(False)
        self._sync_algo_count()
        self.banner.clear()

    def refresh_results(self) -> None:
        self._sync_dataset_choices()
        self._sync_readiness()
        self._update_from_run(mock_data.SAMPLE_RUN)

    def start_api_background(self) -> None:
        """uvicorn ile arka planda FastAPI'yi baslatir.

        Tek seferlik: daha onceki bir tetikleme zaten calisiyorsa tekrar
        denemez. GUI thread'ini bloklamamak icin daemon thread'de calistirir.
        Baslatildiktan sonra ~2sn icinde load_initial_data() tetiklenir, badge
        ve banner gercek API durumunu yansitir.
        """
        if getattr(self, "_api_thread", None) and self._api_thread.is_alive():
            self.banner.show("API zaten çalışıyor.", level="info")
            return
        try:
            import uvicorn  # noqa: F401
        except ImportError:
            self.banner.show(
                "uvicorn yüklü değil. Terminalden: pip install -r requirements.txt",
                level="error",
            )
            return
        import threading
        import urllib.parse

        host = "127.0.0.1"
        port = 8000
        base = getattr(self.api, "base_url", "")
        if base:
            parsed = urllib.parse.urlparse(base)
            host = parsed.hostname or host
            port = parsed.port or port

        def _run():
            try:
                import uvicorn as _uv
                _uv.run("app.api.main:app", host=host, port=port, reload=False, log_level="warning")
            except Exception as exc:  # noqa: BLE001
                # GUI thread'ine geri donus yok; sadece log yaz.
                print(f"[Benchmark API] Baslatma hatasi: {exc}")

        self._api_thread = threading.Thread(target=_run, daemon=True, name="BenchmarkAPI")
        self._api_thread.start()
        self.banner.show(
            f"API başlatılıyor: http://{host}:{port}/docs ... 2-3 saniye sonra 'Sonuçları Yenile' deyin.",
            level="info",
        )
        self.start_api_btn.configure(state=tk.DISABLED, text="API çalışıyor")
        # Birkac saniye sonra otomatik dene.
        self.after(2500, self.load_initial_data)

    def _on_scenario_change(self) -> None:
        self._update_scenario_description()
        self._render_algorithm_checks(self.algorithms or mock_data.ALGORITHMS)
        self._sync_readiness()

    def _selected_scenario_key(self) -> str:
        """Combobox'taki gosterilen ada karsilik gelen backend key'i dondurur."""
        label = self.scenario_cb.get()
        if label in self._scenario_label_to_key:
            return self._scenario_label_to_key[label]
        # Eski mock veya elle yazilmis durumlar icin guvenli geri donus.
        return label

    def _selected_scenario(self) -> dict | None:
        key = self._selected_scenario_key()
        for scenario in self.scenarios:
            if scenario.get("name") == key:
                return scenario
        return None

    def _update_scenario_description(self) -> None:
        if not hasattr(self, "scenario_purpose_lbl"):
            return
        scenario = self._selected_scenario() or {}
        purpose = scenario.get("purpose_tr") or scenario.get("description") or "-"
        impact = scenario.get("system_impact_tr") or "Sisteme etkisi bilgisi yok."
        self.scenario_purpose_lbl.config(text=f"Amaç: {purpose}")
        self.scenario_impact_lbl.config(text=f"Sisteme etkisi: {impact}")

    def _scenario_default_algorithms(self) -> list[str]:
        scenario = self._selected_scenario()
        if scenario:
            return list(scenario.get("default_algorithms") or [])
        return []

    def _sync_dataset_choices(self) -> None:
        dataset_name = getattr(self.api, "last_dataset_name", None)
        if dataset_name:
            self.dataset_cb["values"] = [dataset_name]
            self.dataset_cb.set(dataset_name)
            return
        self.dataset_cb["values"] = ["Yüklü dataset yok"]
        self.dataset_cb.set("Yüklü dataset yok")

    def _readiness_state(self) -> dict[str, tuple[bool, str]]:
        selected = self.selected_algorithms()
        allowed = set(self._scenario_default_algorithms())
        dataset_ready = bool(getattr(self.api, "last_dataset_name", None)) and self.dataset_cb.get() != "Yüklü dataset yok"
        scenario_ready = self._selected_scenario_key() in {s.get("name") for s in self.scenarios}
        algorithms_ready = bool(selected) and (not allowed or all(name in allowed for name in selected))
        backend_ready = bool(self.backend_ready) and not bool(getattr(self.api, "last_dataset_used_mock", False))
        return {
            "dataset": (dataset_ready, self.dataset_cb.get() if dataset_ready else "Dataset Lab'de yükleyin"),
            "scenario": (scenario_ready, self.scenario_cb.get() if scenario_ready else "Geçersiz senaryo"),
            "algorithms": (algorithms_ready, f"{len(selected)} uyumlu" if algorithms_ready else "Uygun algoritma seçin"),
            "backend": (backend_ready, "Gerçek API" if backend_ready else "API yok/mock"),
        }

    def _sync_readiness(self) -> bool:
        if not self.readiness_cards:
            return False
        states = self._readiness_state()
        for key, (ready, subtitle) in states.items():
            card = self.readiness_cards[key]
            card.set_value("Hazır" if ready else "Eksik", subtitle)
            card.set_accent(COLORS["green"] if ready else COLORS["orange"])
        all_ready = all(ready for ready, _subtitle in states.values())
        if hasattr(self, "run_btn"):
            self.run_btn.configure(state=tk.NORMAL if all_ready else tk.DISABLED)
        return all_ready

    def run_benchmark(self) -> None:
        self._sync_dataset_choices()
        if not self._sync_readiness():
            self.banner.show("Benchmark çalıştırılamaz: dataset, senaryo, algoritma uyumu ve gerçek API durumu hazır olmalı.", level="warning")
            return
        algorithms = self.selected_algorithms()
        if not algorithms:
            self.banner.show("Benchmark çalıştırmak için en az bir algoritma seçin.")
            return
        payload = {
            # Backend ingilizce key bekler; combobox Turkce label gosterse de
            # _selected_scenario_key dogru key'i dondurur.
            "scenario": self._selected_scenario_key(),
            "dataset": self.dataset_cb.get(),
            "algorithms": algorithms,
            "parameters": {"source": "desktop-ui"},
        }
        self.run_btn.configure(state=tk.DISABLED)
        self.status_cards["status"].set_value("Çalışıyor", "Arka plan işlemi aktif")
        self.banner.clear()

        def worker():
            return self.api.execute_run(payload)

        def success(result):
            self.run_btn.configure(state=tk.NORMAL)
            if result.used_mock:
                self.source_badge.set_source(True)
                self.banner.show("Benchmark çalıştırılamadı. Backend API yanıt vermiyor; örnek veri gösteriliyor.", level="warning")
            else:
                self.source_badge.set_source(False)
            data = result.data
            run = self._run_from_response(data)
            self._update_from_run(run)
            self.status_cards["status"].set_value("Tamamlandı", "Sonuç alındı")

        def error(exc):
            self.run_btn.configure(state=tk.NORMAL)
            self.banner.show(f"Benchmark çalıştırılamadı: {_friendly_error(exc)}")

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)

    def _update_from_run(self, run: dict) -> None:
        metrics = run.get("metrics", {})
        self.status_cards["last_run"].set_value(run.get("date", "-").split(" ")[-1], "Bugün")
        self.status_cards["status"].set_value(run.get("status", "-"), "Run durumu")
        self.status_cards["duration"].set_value(run.get("duration", "-"), "Süre")
        self.status_cards["algo_count"].set_value(len(run.get("algorithms", [])), "Seçili")
        self.status_cards["dataset_size"].set_value(run.get("dataset_size", "-"), "Kayıt")
        self.status_cards["metric_count"].set_value(run.get("metric_count", len(metrics)), "Tamam")
        self.summary_table.set_rows(
            [
                {"Alan": "Run ID", "Deger": run.get("run_id", "-")},
                {"Alan": "Senaryo", "Deger": run.get("scenario", "-")},
                {"Alan": "Veri seti", "Deger": run.get("dataset", "-")},
                {"Alan": "Algoritmalar", "Deger": ", ".join(run.get("algorithms", []))},
                {"Alan": "Başlatan", "Deger": run.get("started_by", "Admin")},
                {"Alan": "Tarih", "Deger": run.get("date", "-")},
                {"Alan": "Durum", "Deger": run.get("status", "-")},
                {"Alan": "Süre", "Deger": run.get("duration", "-")},
            ]
        )
        for key, card in self.metric_cards.items():
            value = metrics.get(key, "-")
            card.set_value(value)

    def _run_from_response(self, data: dict) -> dict:
        raw_details = data.get("details")
        details_run = raw_details.get("run") if isinstance(raw_details, dict) else None
        raw_summary = data.get("summary")
        summary: dict = raw_summary if isinstance(raw_summary, dict) else {}
        run = dict(mock_data.SAMPLE_RUN)
        if isinstance(details_run, dict):
            run.update(
                {
                    "run_id": details_run.get("run_id") or summary.get("run_id") or run.get("run_id"),
                    "scenario": details_run.get("scenario_name") or summary.get("scenario_name") or self.scenario_cb.get(),
                    "dataset": details_run.get("dataset_name") or summary.get("dataset_name") or self.dataset_cb.get(),
                    "algorithms": details_run.get("algorithms") or summary.get("algorithms") or self.selected_algorithms(),
                    "date": details_run.get("started_at") or summary.get("started_at") or run.get("date"),
                    "status": details_run.get("status") or summary.get("status") or "completed",
                }
            )
        else:
            run.update(
                {
                    "run_id": summary.get("run_id") or run.get("run_id"),
                    "scenario": summary.get("scenario_name") or self.scenario_cb.get(),
                    "dataset": summary.get("dataset_name") or self.dataset_cb.get(),
                    "algorithms": summary.get("algorithms") or self.selected_algorithms(),
                    "date": summary.get("started_at") or run.get("date"),
                    "status": summary.get("status") or "completed",
                }
            )
        metrics = self._metrics_from_comparison(data.get("comparison_table") or [])
        if not metrics and isinstance(details_run, dict):
            metrics = details_run.get("metrics", {})
        run["metrics"] = metrics or run.get("metrics", {})
        run["metric_count"] = len(run["metrics"])
        quality = getattr(self.api, "last_dataset", {}) or {}
        row_count = (quality.get("quality_summary") or {}).get("row_count")
        if row_count:
            run["dataset_size"] = row_count
        return run

    def _metrics_from_comparison(self, rows: list[dict]) -> dict[str, float]:
        mapping = {
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
        out: dict[str, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            for raw_key, value in row.items():
                metric_name = str(raw_key).split(".")[-1]
                target_key = mapping.get(metric_name)
                if not target_key:
                    continue
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    continue
                current = out.get(target_key)
                if current is None:
                    out[target_key] = numeric_value
                elif target_key == "latency_ms":
                    out[target_key] = min(current, numeric_value)
                else:
                    out[target_key] = max(current, numeric_value)
        return out


def _friendly_error(exc: Exception) -> str:
    message = str(exc)
    if "No dataset loaded" in message:
        return "Önce Dataset Lab ekranında geçerli bir veri seti yükleyin."
    if "HTTP Error 400" in message:
        return "Benchmark isteği backend tarafından reddedildi. Dataset ve senaryo seçimini kontrol edin."
    if "HTTP Error 500" in message:
        return "Backend benchmark çalıştırırken hata verdi. Veri seti formatını ve algoritma uyumunu kontrol edin."
    return message

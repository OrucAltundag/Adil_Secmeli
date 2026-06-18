# -*- coding: utf-8 -*-
# =============================================================================
# app/main.py — Adil Seçmeli Ana Uygulama Giriş Noktası
# =============================================================================
# Bu dosya masaüstü Tkinter uygulamasını başlatır.
# İlgili modüller: app/db (veritabanı), app/ui/tabs (sekmeler), app/services (hesaplama)
# =============================================================================

import argparse
import json
import os
import sys
import warnings

# app/main.py doğrudan çalıştırılırsa proje kökünü önce path'e ekle.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.config import load_app_config
from app.core.logging_config import configure_logging
from app.core.permissions import UserContext, can
from app.db.session import init_database

warnings.filterwarnings("ignore", category=FutureWarning, module="seaborn")

# ---------- Headless (ekransız) ortam kontrolü ----------
def is_headless_environment() -> bool:
    """
    Tkinter gibi GUI araçları bir "display" ister.
    Codespaces / container gibi ortamlarda DISPLAY olmayabilir.
    """
    if os.name == "nt":
        return False
    return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

HEADLESS = is_headless_environment()


def _default_api_port() -> int:
    try:
        return int(os.environ.get("ADIL_SECMELI_API_PORT", load_app_config().api_port))
    except (TypeError, ValueError):
        return 8000


DEFAULT_API_HOST = os.environ.get("ADIL_SECMELI_API_HOST", load_app_config().api_host)
DEFAULT_API_PORT = _default_api_port()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.core.state import AppState

# ---------- Veritabanı ve temel bileşenler ----------
from app.db.sqlite_db import Database

# ---------- Servis katmanı (hesaplama, havuz kararı) ----------
from app.services.course_type import build_elective_predicate_from_columns


# =============================================================================
# BÖLÜM 1: Yapılandırma (config.json)
# =============================================================================
def load_config():
    app_cfg = load_app_config()
    default = app_cfg.as_legacy_dict()
    default.setdefault("charts", {"bins": 15})
    cfg_path = os.path.join(os.getcwd(), "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            default.update(data or {})
        except Exception:
            pass
    db_path = default.get("db_path")
    fallback_path = app_cfg.sqlite_db_path
    if db_path and fallback_path and not os.path.exists(str(db_path)) and os.path.exists(str(fallback_path)):
        default["db_path"] = fallback_path
        fallback_url_path = os.path.abspath(str(fallback_path)).replace(os.sep, "/")
        default["db_url"] = f"sqlite:///{fallback_url_path}"
    return default


def build_headless_message(host: str, port: int) -> str:
    return (
        "[GUI] Headless ortam algilandi (DISPLAY/WAYLAND_DISPLAY yok). "
        "Tkinter arayuzu burada acilamaz.\n\n"
        "[API] REST API modu otomatik baslatiliyor.\n"
        f"- Adres: http://{host}:{port}\n"
        f"- Dokumantasyon: http://{host}:{port}/docs\n\n"
        "Masaustu arayuz icin uygulamayi GUI olan bir ortamda "
        "`python -m app.main --mode gui` ile calistirin."
    )


def run_api_server(host: str, port: int) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            "[API] uvicorn bulunamadi. `pip install -r requirements.txt` komutunu calistirin."
        )
        return 1

    print(f"[API] Adil Secmeli API baslatiliyor: http://{host}:{port}/docs")
    uvicorn.run("app.api.main:app", host=host, port=port, reload=False)
    return 0


def run_gui() -> int:
    try:
        app = AdilSecmeliApp()
        app.mainloop()
        return 0
    except tk.TclError as e:
        print(
            "[GUI] Tkinter baslatilamadi. Muhtemelen display yok.\n"
            f"Hata: {e}\n\n"
            "GUI uygulamayi display olan bir ortamda calistirin."
        )
        return 1


def run_migrate() -> int:
    try:
        result = init_database()
        print(f"[MIGRATE] Schema compatibility tamamlandi: {result.get('db_path')}")
        return 0
    except Exception as exc:
        print(f"[MIGRATE] Hata: {exc}")
        return 1


def run_schema_check() -> int:
    try:
        from app.services.schema_health_service import generate_schema_health_report

        print(generate_schema_health_report(config=load_app_config()))
        return 0
    except Exception as exc:
        print(f"[SCHEMA-CHECK] Hata: {exc}")
        return 1


def _configure_health_output_encoding() -> None:
    """Windows konsol kodlaması Unicode rapor karakterlerinde CLI'ı düşürmesin."""

    try:
        reconfig = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfig):
            reconfig(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass


def run_health(mode: str) -> int:
    """CLI sağlık modları: health-check / -full / -repair / -audit."""

    try:
        _configure_health_output_encoding()
        from app.health.health_formatter import (
            format_algorithm_catalog,
            format_report,
        )
        from app.services.health_service import HealthService

        service = HealthService(config=load_app_config())
        runner = {
            "quick": service.run_quick_health_check,
            "full": service.run_full_health_check,
            "repair": service.run_auto_repair,
            "audit": service.run_audit_health_check,
        }[mode]
        report = runner()
        print(format_report(report, developer=True))
        if mode == "full":
            print(format_algorithm_catalog())
        # Çıkış kodu: KRİTİK ise 1, aksi halde 0 (CI entegrasyonu için).
        return 1 if report.overall_status in ("RİSKLİ", "KRİTİK") else 0
    except Exception as exc:  # noqa: BLE001
        print(f"[HEALTH:{mode}] Hata: {exc}")
        return 1


def run_benchmark_mode() -> int:
    print("[BENCHMARK] Benchmark paneli GUI icinde aciliyor.")
    return run_gui()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Adil Seçmeli giriş noktası (GUI veya headless API modu)."
    )
    parser.add_argument(
        "--mode",
        choices=(
            "auto",
            "gui",
            "api",
            "benchmark",
            "migrate",
            "schema-check",
            "health-check",
            "health-check-full",
            "health-repair",
            "health-audit",
        ),
        default="auto",
        help=(
            "auto: headless ise API, degilse GUI; "
            "gui/api/benchmark/migrate/schema-check ve "
            "health-check/health-check-full/health-repair/health-audit modlarini zorla"
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_API_HOST,
        help="API host adresi (headless veya --mode api icin).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_API_PORT,
        help="API portu (headless veya --mode api icin).",
    )
    args = parser.parse_args(argv)
    configure_logging(load_app_config())

    if args.mode == "api":
        return run_api_server(args.host, args.port)

    if args.mode == "gui":
        return run_gui()

    if args.mode == "benchmark":
        return run_benchmark_mode()

    if args.mode == "migrate":
        return run_migrate()

    if args.mode == "schema-check":
        return run_schema_check()

    if args.mode == "health-check":
        return run_health("quick")

    if args.mode == "health-check-full":
        return run_health("full")

    if args.mode == "health-repair":
        return run_health("repair")

    if args.mode == "health-audit":
        return run_health("audit")

    if HEADLESS:
        print(build_headless_message(args.host, args.port))
        return run_api_server(args.host, args.port)

    return run_gui()






# =============================================================================
# BÖLÜM 2: Ana Uygulama Sınıfı (AdilSecmeliApp)
# =============================================================================
class AdilSecmeliApp(tk.Tk):

    def __init__(self):
        super().__init__()
        from app.ui.style import apply_style
        from app.ui.tabs.ahp_weight_page import AHPWeightPage
        from app.ui.tabs.calc_tab import CalcTab
        from app.ui.tabs.data_management_page import DataManagementPage
        from app.ui.tabs.data_quality_page import DataQualityPage
        from app.ui.tabs.decision_center_page import DecisionCenterPage
        from app.ui.tabs.overview_page import OverviewPage
        from app.ui.tabs.semester_planning_page import SemesterPlanningPage
        from app.ui.tabs.system_health_page import SystemHealthPage
        from app.ui.tabs.topsis_decision_page import TopsisDecisionPage
        from app.ui.tabs.tools_tab import ToolsTab
        from app.ui.tabs.trend_visualization_page import TrendVisualizationPage
        from app.ui.tabs.view_tab import ViewTab

        apply_style(self)
        self.app_config = load_app_config()
        configure_logging(self.app_config)
        self.user_context = UserContext.demo_admin(self.app_config)
        self.config_data = load_config()
        self.show_benchmark_lab = bool(self.config_data.get("show_benchmark_lab", False))
        self.auto_algorithm_trigger_var = tk.BooleanVar(
            value=bool(self.config_data.get("auto_pipeline_enabled", False))
        )
        self._automatic_preview_in_progress = False
        self.db_path = self.config_data.get("db_path")
        if self.db_path:
            self.db_path = os.path.abspath(self.db_path)
        self.db_url = self.app_config.database_url
        self.db = Database(self.db_url if self.db_url else self.db_path)
        self.current_table = None

        self.state = AppState(db_path=self.db_path)


        # Grafik ve Cache değişkenleri
        self.chart_canvas = None
        self.ui_refs = {}
        self.results_cache = {}

        # Algoritma Listesi
        self.algorithms = [
            {"id": "mock",    "name": "Veri Üretimi (Mock)"},
            {"id": "trend",   "name": "2. Tarihsel Trend Analizi"},
            {"id": "ahp",     "name": "3. AHP (Ağırlıklar)"},
            {"id": "topsis",  "name": "4. TOPSIS (Sıralama)"},
            {"id": "lr",      "name": "Lineer Regresyon (Tahmin)"},
            {"id": "rf",      "name": "Random Forest (Sınıflandırma)"},
            {"id": "dt",      "name": "Decision Tree (Karar)"},
            {"id": "next_year", "name": "Sonraki Yil Mufredat Uretimi"}
        ]

        # ---- BÖLÜM 2.1: Üst çubuk (Header) ----
        topbar = ttk.Frame(self, padding=8)
        topbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(topbar, text="Adil Seçmeli • Masaüstü", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(topbar, text="Veritabanı Seç", command=self.cmd_open_db).pack(side=tk.RIGHT, padx=4)
        ttk.Button(topbar, text="Yenile", command=self.refresh_all).pack(side=tk.RIGHT, padx=4)
        ttk.Checkbutton(
            topbar,
            text="Otomatik Karar Tetiği",
            variable=self.auto_algorithm_trigger_var,
            command=self._toggle_auto_algorithm_trigger,
        ).pack(side=tk.RIGHT, padx=10)

        # ---- Ana Konteyner ----
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # ---- BÖLÜM 2.2: Sekmeler (Notebook) ----
        self.nb = ttk.Notebook(container)
        self.nb.pack(fill=tk.BOTH, expand=True)

        # 🔔 Dış notebook tab değişim event'i
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # ── GRUP 0: GENEL BAKIŞ (sistemin tek-bakışta özeti + algoritma rehberi)
        self.tab_overview = OverviewPage(self.nb, app=self)
        self.nb.add(self.tab_overview, text="🏠 Genel Bakış")

        # ── GRUP 1: SİSTEM ────────────────────────────────────────────
        _g_sistem = ttk.Frame(self.nb)
        self.nb.add(_g_sistem, text="🖥️ Sistem")
        self._nb_sistem = ttk.Notebook(_g_sistem)
        self._nb_sistem.pack(fill=tk.BOTH, expand=True)
        self._nb_sistem.bind("<<NotebookTabChanged>>",
                             lambda e: self._on_inner_tab_change(e, "sistem"))

        self.tab_system_health = SystemHealthPage(self._nb_sistem, app=self)
        self._nb_sistem.add(self.tab_system_health, text="🏥 Sistem Sağlığı")

        # §4: "Güvenlik & Hazırlık" sayfası arayüzden kaldırıldı (kullanıcı isteği).
        # Sınıf (SecurityReadinessPage) kod tabanında kalır; yalnız sekme oluşturulmaz.

        self.tab_view = ViewTab(self._nb_sistem, app=self)
        self._nb_sistem.add(self.tab_view, text="📂 Veritabanı Görüntüle")

        # ── GRUP 2: VERİ ──────────────────────────────────────────────
        _g_veri = ttk.Frame(self.nb)
        self.nb.add(_g_veri, text="📥 Veri")
        self._nb_veri = ttk.Notebook(_g_veri)
        self._nb_veri.pack(fill=tk.BOTH, expand=True)

        self.tab_data_management = DataManagementPage(self._nb_veri, app=self)
        self._nb_veri.add(self.tab_data_management, text="📥 Veri Yönetimi")

        self.tab_data_quality = DataQualityPage(self._nb_veri, app=self, db_path=self.db_path)
        self._nb_veri.add(self.tab_data_quality, text="✓ Veri Kalitesi")

        # Trend Kontrol Sayfası (Veri başlığı altında, canlı hesaplama).
        # TrendVisualizationPage yeniden kullanılır; Veri sekmesi için ayrı örnek.
        self.tab_data_trend = TrendVisualizationPage(self._nb_veri, app=self)
        self._nb_veri.add(self.tab_data_trend, text="📈 Trend")

        # ── GRUP 3: KARAR SÜRECİ ──────────────────────────────────────
        _g_karar = ttk.Frame(self.nb)
        self.nb.add(_g_karar, text="⚙️ Karar Süreci")
        self._nb_karar = ttk.Notebook(_g_karar)
        self._nb_karar.pack(fill=tk.BOTH, expand=True)
        self._nb_karar.bind("<<NotebookTabChanged>>",
                            lambda e: self._on_inner_tab_change(e, "karar"))

        self.tab_calc = CalcTab(self._nb_karar, app=self)
        self._nb_karar.add(self.tab_calc, text="🧮 Kriter & Havuz")

        self.tab_ahp_weight = AHPWeightPage(self._nb_karar, app=self)
        self._nb_karar.add(self.tab_ahp_weight, text="⚖️ AHP Ağırlık Yönetimi")

        self.tab_topsis_decision = TopsisDecisionPage(self._nb_karar, app=self)
        self._nb_karar.add(self.tab_topsis_decision, text="📐 TOPSIS Kararı")

        self.tab_decision_center = DecisionCenterPage(self._nb_karar, app=self)
        self._nb_karar.add(self.tab_decision_center, text="🎯 Karar Merkezi")

        self.tab_semester_planning = SemesterPlanningPage(self._nb_karar, app=self)
        self._nb_karar.add(self.tab_semester_planning, text="📅 Dönem Planlama")

        # ── GRUP 4: RAPORLAMA & ANALİZ ────────────────────────────────
        _g_rapor = ttk.Frame(self.nb)
        self.nb.add(_g_rapor, text="📊 Raporlama & Analiz")
        self._nb_rapor = ttk.Notebook(_g_rapor)
        self._nb_rapor.pack(fill=tk.BOTH, expand=True)
        self._nb_rapor.bind("<<NotebookTabChanged>>",
                            lambda e: self._on_inner_tab_change(e, "rapor"))

        self.tab_trend_vis = TrendVisualizationPage(self._nb_rapor, app=self)
        self._nb_rapor.add(self.tab_trend_vis, text="📈 Trend Görselleştirme")

        self.tab_tools = ToolsTab(self._nb_rapor, app=self)
        self._nb_rapor.add(self.tab_tools, text="📄 Rapor & Yükleme")

        # ── GRUP 5: BENCHMARK LAB ─────────────────────────────────────
        if self.show_benchmark_lab:
            from app.ui.benchmark import BenchmarkPanel

            _g_bench = ttk.Frame(self.nb)
            self.nb.add(_g_bench, text="🔬 Benchmark Lab")
            self.tab_benchmark = BenchmarkPanel(_g_bench, app=self)
            self.tab_benchmark.pack(fill=tk.BOTH, expand=True)

        # Otomatik Bağlan
        self.auto_connect()





    # ---- BÖLÜM 3: Veritabanı bağlantısı ve başlangıç -----

    def auto_connect(self):
        """
        Uygulama acilisinda otomatik veritabani baglantisi kurar.
                Sirasyla: DB baglan -> havuz seed -> (opsiyonel) sonraki yil uret -> UI yenile.

                Not:
                - Tum yillari kapsayan statu/yil zincirleme esitleme acilista otomatik
                    calistirilmaz. Bu islem sadece kullanici tetigiyle (ilgili butonlardan)
                    calistirilir.
        """
        db_path = self.db_path
        db_url = self.db_url
        if self.app_config.db_backend == "sqlite" and db_path and not os.path.exists(str(db_path)):
            fallback = os.path.abspath(str(self.app_config.sqlite_db_path))
            if os.path.exists(fallback):
                self.db_path = fallback
                self.db_url = f"sqlite:///{fallback.replace(os.sep, '/')}"
                db_path = self.db_path
                db_url = self.db_url

        try:
            # 1) Veritabani baglantisi
            self.db.connect(db_url or db_path)
            self.tab_view.fill_tables()

            # 2) Havuz seed (bossa)
            self.ensure_pool_initialized_once()

            # 3) Otomatik tetik yalniz gecici karar onizlemesi uretir; mufredati yazmaz.
            if self.auto_algorithm_trigger_var.get():
                self.after(500, self._run_automatic_decision_previews)

            # 4) UI yenileme
            try:
                self.tab_calc.refresh()
            except Exception:
                pass
            try:
                self.tab_tools.refresh()
            except Exception:
                pass
            try:
                self.tab_calc.page_pool.refresh()
            except Exception:
                pass
            try:
                self.tab_decision_center.refresh()
            except Exception:
                pass

        except FileNotFoundError:
            messagebox.showwarning(
                "Veritabani Bulunamadi",
                f"Veritabanı dosyası bulunamadı:\n{db_path}\n\n"
                "Lütfen geçerli bir SQLite veritabanı dosyası seçiniz."
            )
            self.cmd_open_db()

        except Exception as e:
            messagebox.showerror(
                "Baslangic Hatasi",
                f"Uygulama baslatilirken hata olustu:\\n\\n{e}"
            )


    def _persist_config_value(self, key, value):
        path = os.path.join(os.getcwd(), "config.json")
        data = {}
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle) or {}
        except Exception:
            data = {}
        data[str(key)] = value
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
        self.config_data[str(key)] = value

    def _toggle_auto_algorithm_trigger(self):
        enabled = bool(self.auto_algorithm_trigger_var.get())
        try:
            self._persist_config_value("auto_pipeline_enabled", enabled)
        except Exception as exc:
            self.auto_algorithm_trigger_var.set(not enabled)
            messagebox.showerror("Otomatik Karar Tetiği", f"Ayar kaydedilemedi: {exc}")
            return
        if enabled and messagebox.askyesno(
            "Otomatik Karar Tetiği",
            "Otomatik tetik açıldı. En güncel gerçek yıl için geçici kararlar şimdi hesaplansın mı?",
        ):
            self.after(50, self._run_automatic_decision_previews)

    def _run_automatic_decision_previews(self):
        if self._automatic_preview_in_progress or not self.auto_algorithm_trigger_var.get():
            return
        self._automatic_preview_in_progress = True
        created = 0
        skipped = 0
        errors = []
        try:
            from app.services.criteria_completion_service import can_run_algorithm
            from app.services.decision_run_service import record_decision_run_for_faculty_year

            conn = getattr(self.db, "conn", None)
            if conn is None:
                return
            cur = conn.cursor()
            cur.execute(
                """
                SELECT b.fakulte_id, b.bolum_id, MAX(m.akademik_yil)
                FROM mufredat m JOIN bolum b ON b.bolum_id=m.bolum_id
                GROUP BY b.fakulte_id, b.bolum_id
                ORDER BY b.fakulte_id, b.bolum_id
                """
            )
            scopes = [
                (int(row[0]), int(row[1]), int(row[2]))
                for row in cur.fetchall()
                if row[2] is not None
            ]
            for faculty_id, department_id, year in scopes:
                for semester in ("Guz", "Bahar"):
                    try:
                        gate = can_run_algorithm(
                            conn,
                            year=year,
                            faculty_id=faculty_id,
                            department_id=department_id,
                            semester=semester,
                            scope_type="department",
                            refresh=False,
                        )
                        if not gate.get("can_run"):
                            skipped += 1
                            continue
                        record_decision_run_for_faculty_year(
                            conn,
                            year=year,
                            faculty_id=faculty_id,
                            department_id=department_id,
                            semester=semester,
                            created_by="automatic-preview",
                        )
                        created += 1
                    except Exception as exc:
                        errors.append(str(exc))
            conn.commit()
            try:
                self.tab_decision_center.refresh()
            except Exception:
                pass
            messagebox.showinfo(
                "Otomatik Karar Tetiği",
                f"Geçici karar önizlemeleri tamamlandı. Oluşan: {created}, atlanan: {skipped}, hata: {len(errors)}.",
            )
        finally:
            self._automatic_preview_in_progress = False

    def cmd_open_db(self):
        """Kullanicidan yeni veritabani dosyasi secmesini ister ve baglantıyı yeniler."""
        if self.app_config.db_backend != "sqlite":
            messagebox.showinfo(
                "Veritabanı",
                "PostgreSQL modu etkin. Dosya seçimi yerine DATABASE_URL kullanılacak.",
            )
            return
        path = filedialog.askopenfilename(
            title="SQLite Veritabanı Seç",
            filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("Tümü", "*.*")]
        )
        if not path:
            return
        try:
            self.db.connect(path)
            self.db_path = os.path.abspath(path)
            self.db_url = f"sqlite:///{self.db_path.replace(os.sep, '/')}"
            self.state.set("db_path", path)

            try:
                db_url_path = os.path.abspath(path).replace(os.sep, "/")
                self._persist_config_value("db_path", path)
                self._persist_config_value("db_url", f"sqlite:///{db_url_path}")
            except Exception:
                pass

            self.tab_view.fill_tables()
            self.ensure_pool_initialized_once()
            if self.auto_algorithm_trigger_var.get():
                self.after(50, self._run_automatic_decision_previews)
            self.tab_calc.refresh()
            try:
                self.tab_tools.refresh()
            except Exception:
                pass
            try:
                self.tab_calc.page_pool.refresh()
            except Exception:
                pass
            try:
                self.tab_decision_center.refresh()
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror(
                "Veritabanı Bağlantı Hatası",
                f"Seçilen veritabanına bağlanılamadı:\n\n{e}",
            )


    # ---- BÖLÜM 4: Havuz tablosu doldurma -----

    def fill_pool_table_for_years(self):
        """
        Havuz tablosunu mevcut mufredat yillari icin doldurur.
        Sadece kayit yoksa INSERT yapar (ON CONFLICT DO NOTHING).
        skor alanini NULL birakir; yil bazli TOPSIS hesaplaninca doldurulur.
        """
        _, year_rows = self.db.run_sql(
            "SELECT DISTINCT akademik_yil FROM mufredat ORDER BY akademik_yil"
        )
        years = [int(r[0]) for r in (year_rows or []) if r and r[0] is not None]
        if not years:
            return

        dersler = []
        try:
            columns = self.db.get_columns("ders")
            elective_predicate = build_elective_predicate_from_columns(columns, alias="d")
            if elective_predicate != "0=1":
                _, dersler = self.db.run_sql(
                    f"""
                    SELECT d.ders_id, d.fakulte_id, d.bolum_id, d.ad
                    FROM ders d
                    WHERE {elective_predicate}
                    """
                )
        except Exception:
            dersler = []

        if not dersler:
            return

        insert_q = """
            INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
            VALUES (?, ?, ?, ?, 0, 0, NULL, ?)
            ON CONFLICT DO NOTHING
        """

        for ders_id, fakulte_id, bolum_id, ders_adi in dersler:
            for yil in years:
                self.db.run_sql(
                    insert_q,
                    (str(ders_id), yil, fakulte_id, bolum_id, str(ders_adi or "")),
                )
        print(f"[Pool] {len(dersler)} ders x {len(years)} yil = havuz seed tamamlandi.")


    def open_sql_runner(self):
        if not can(getattr(self, "user_context", None), "use_sql_console", config=getattr(self, "app_config", None)):
            messagebox.showwarning(
                "SQL Console",
                "SQL Console yalnızca geliştirici/yönetici modunda kullanılabilir.",
            )
            return
        win = tk.Toplevel(self)
        win.title("SQL Çalıştır")
        win.geometry("900x600")
        txt = tk.Text(win, height=10)
        txt.pack(fill=tk.BOTH, expand=False, padx=8, pady=8)
        if self.app_config.db_backend == "sqlite":
            txt.insert(tk.END, "SELECT name FROM sqlite_master WHERE type='table';")
        else:
            txt.insert(tk.END, "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema();")

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(frame, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        sx.pack(fill=tk.X)
        tree.configure(xscrollcommand=sx.set)

        def run():
            q = txt.get("1.0", tk.END).strip()
            if not q:
                return
            try:
                cols, rows = self.db.run_sql(q)
                if cols:
                    tree.delete(*tree.get_children())
                    tree["columns"] = cols
                    for c in cols:
                        tree.heading(c, text=c)
                        tree.column(c, width=150, anchor="center")
                    for r in rows:
                        if hasattr(r, "_mapping"):
                            tree.insert("", tk.END, values=[r._mapping.get(c) for c in cols])
                        else:
                            tree.insert("", tk.END, values=list(r))
                else:
                    messagebox.showinfo("Tamam", "Sorgu başarıyla çalıştı.")
            except Exception as e:
                messagebox.showerror("SQL Hatası", str(e))

        ttk.Button(win, text="Çalıştır", command=run).pack(pady=(0, 8))

    def refresh_all(self):
        try:
            self.tab_view.refresh()
            outer = self.nb.tab(self.nb.index("current"), "text")
            if "Sistem" in outer:
                inner = self._nb_sistem.tab(self._nb_sistem.index("current"), "text")
                if "Sağlık" in inner:
                    self.tab_system_health.refresh()
            elif "Karar Süreci" in outer:
                inner = self._nb_karar.tab(self._nb_karar.index("current"), "text")
                if "Kriter" in inner:
                    self.tab_calc.refresh()
                elif "AHP" in inner:
                    self.tab_ahp_weight.refresh()
                elif "TOPSIS" in inner:
                    self.tab_topsis_decision.refresh()
                elif "Karar Merkezi" in inner:
                    self.tab_decision_center.refresh()
                elif "Dönem" in inner:
                    self.tab_semester_planning.refresh()
            elif "Raporlama" in outer:
                inner = self._nb_rapor.tab(self._nb_rapor.index("current"), "text")
                if "Trend" in inner:
                    self.tab_trend_vis.refresh()
                elif "Rapor" in inner:
                    self.tab_tools.refresh()
            elif "Benchmark" in outer:
                self.tab_benchmark.refresh()
        except Exception as e:
            messagebox.showerror("Yenileme Hatası", str(e))




     # =========================================================

    #  ANALİZ & DASHBOARD FONKSİYONLARI (YENİ EKLENECEK KISIM)
    # =========================================================

    def on_tab_change(self, event):
        """Dış sekme değiştiğinde aktif iç sekmeyi yeniler."""
        selected = event.widget.tab(event.widget.index("current"), "text")
        try:
            if "Sistem" in selected:
                inner = self._nb_sistem.tab(self._nb_sistem.index("current"), "text")
                if "Sağlık" in inner:
                    self.tab_system_health.refresh()
            elif "Karar Süreci" in selected:
                inner = self._nb_karar.tab(self._nb_karar.index("current"), "text")
                if "Kriter" in inner:
                    self.tab_calc.refresh()
                elif "AHP" in inner:
                    self.tab_ahp_weight.refresh()
                elif "TOPSIS" in inner:
                    self.tab_topsis_decision.refresh()
                elif "Karar Merkezi" in inner:
                    self.tab_decision_center.refresh()
                elif "Dönem" in inner:
                    self.tab_semester_planning.refresh()
            elif "Raporlama" in selected:
                inner = self._nb_rapor.tab(self._nb_rapor.index("current"), "text")
                if "Trend" in inner:
                    self.tab_trend_vis.refresh()
                elif "Rapor" in inner:
                    self.tab_tools.refresh()
            elif "Benchmark" in selected:
                self.tab_benchmark.refresh()
        except Exception:
            pass

    def _on_inner_tab_change(self, event, group: str):
        """İç sekme değiştiğinde ilgili sayfanın refresh() metodunu çağırır."""
        try:
            selected = event.widget.tab(event.widget.index("current"), "text")
            if group == "sistem":
                if "Sağlık" in selected:
                    self.tab_system_health.refresh()
            elif group == "karar":
                if "Kriter" in selected:
                    self.tab_calc.refresh()
                elif "AHP" in selected:
                    self.tab_ahp_weight.refresh()
                elif "TOPSIS" in selected:
                    self.tab_topsis_decision.refresh()
                elif "Karar Merkezi" in selected:
                    self.tab_decision_center.refresh()
                elif "Dönem" in selected:
                    self.tab_semester_planning.refresh()
            elif group == "rapor":
                if "Trend" in selected:
                    self.tab_trend_vis.refresh()
                elif "Rapor" in selected:
                    self.tab_tools.refresh()
        except Exception:
            pass


    def ensure_pool_initialized_once(self):
        """Havuz tablosu bos ise ilk kez mufredat yillarindan seed olusturur."""
        res = self.db.run_sql("SELECT COUNT(*) FROM havuz;")
        cnt = res[1][0][0] if res[1] else 0
        if cnt == 0:
            self.fill_pool_table_for_years()


if __name__ == "__main__":
    raise SystemExit(main())

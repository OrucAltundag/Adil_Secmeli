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
from app.services.calculation import run_automatic_scoring
from app.services.course_type import build_elective_predicate_from_columns
from app.services.yearly_workflow import is_yearly_workflow_enabled


# =============================================================================
# BÖLÜM 1: Yapılandırma (config.json)
# =============================================================================
def load_config():
    default = load_app_config().as_legacy_dict()
    default.setdefault("charts", {"bins": 15})
    cfg_path = os.path.join(os.getcwd(), "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            default.update(data or {})
        except Exception:
            pass
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


def run_health(mode: str) -> int:
    """CLI sağlık modları: health-check / -full / -repair / -audit."""

    try:
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
        from app.ui.benchmark import BenchmarkPanel
        from app.ui.style import apply_style
        from app.ui.tabs.ahp_weight_page import AHPWeightPage
        from app.ui.tabs.analysis_tab import AnalysisTab
        from app.ui.tabs.calc_tab import CalcTab
        from app.ui.tabs.data_management_page import DataManagementPage
        from app.ui.tabs.data_quality_page import DataQualityPage
        from app.ui.tabs.decision_center_page import DecisionCenterPage
        from app.ui.tabs.security_readiness_page import SecurityReadinessPage
        from app.ui.tabs.semester_planning_page import SemesterPlanningPage
        from app.ui.tabs.system_health_page import SystemHealthPage
        from app.ui.tabs.tools_tab import ToolsTab
        from app.ui.tabs.view_tab import ViewTab

        apply_style(self)
        self.app_config = load_app_config()
        configure_logging(self.app_config)
        self.user_context = UserContext.demo_admin(self.app_config)
        self.config_data = load_config()
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

        # ---- Ana Konteyner ----
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # ---- BÖLÜM 2.2: Sekmeler (Notebook) ----
        self.nb = ttk.Notebook(container)
        self.nb.pack(fill=tk.BOTH, expand=True)

        # 🔔 Outer notebook tab değişim event'i
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # ── GRUP 1: SİSTEM ────────────────────────────────────────────
        _g_sistem = ttk.Frame(self.nb)
        self.nb.add(_g_sistem, text="🖥️ Sistem")
        self._nb_sistem = ttk.Notebook(_g_sistem)
        self._nb_sistem.pack(fill=tk.BOTH, expand=True)
        self._nb_sistem.bind("<<NotebookTabChanged>>",
                             lambda e: self._on_inner_tab_change(e, "sistem"))

        self.tab_system_health = SystemHealthPage(self._nb_sistem, app=self)
        self._nb_sistem.add(self.tab_system_health, text="🏥 Sistem Sağlığı")

        self.tab_security_readiness = SecurityReadinessPage(self._nb_sistem)
        self._nb_sistem.add(self.tab_security_readiness, text="🔐 Güvenlik & Hazırlık")

        self.tab_view = ViewTab(self._nb_sistem, app=self)
        self._nb_sistem.add(self.tab_view, text="📂 Veritabanı Görüntüle")

        # ── GRUP 2: VERİ ──────────────────────────────────────────────
        _g_veri = ttk.Frame(self.nb)
        self.nb.add(_g_veri, text="📥 Veri")
        self._nb_veri = ttk.Notebook(_g_veri)
        self._nb_veri.pack(fill=tk.BOTH, expand=True)
        self._nb_veri.bind("<<NotebookTabChanged>>",
                           lambda e: self._on_inner_tab_change(e, "veri"))

        self.tab_data_management = DataManagementPage(self._nb_veri, app=self)
        self._nb_veri.add(self.tab_data_management, text="📥 Veri Yönetimi")

        self.tab_data_quality = DataQualityPage(self._nb_veri, app=self, db_path=self.db_path)
        self._nb_veri.add(self.tab_data_quality, text="✓ Veri Kalitesi")

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

        self.tab_analysis = AnalysisTab(self._nb_rapor, app=self)
        self._nb_rapor.add(self.tab_analysis, text="📊 Analiz & Grafik")

        self.tab_tools = ToolsTab(self._nb_rapor, app=self)
        self._nb_rapor.add(self.tab_tools, text="📄 Rapor & Yükleme")

        # ── GRUP 5: BENCHMARK LAB ─────────────────────────────────────
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

        try:
            # 1) Veritabani baglantisi
            self.db.connect(db_url or db_path)
            self.tab_view.fill_tables()

            # 2) Havuz seed (bossa)
            self.ensure_pool_initialized_once()

            # 3) Otomatik sonraki yil uretimi (legacy mod)
            if is_yearly_workflow_enabled():
                print("[AUTO] ENABLE_YEARLY_CRITERIA_WORKFLOW=true -> otomatik algoritma tetigi kapali.")
            else:
                try:
                    if self.app_config.db_backend != "sqlite":
                        print("[AUTO] PostgreSQL modu etkin; legacy SQLite otomatik skor yolu atlandi.")
                    else:
                        print("[AUTO] Sonraki yil mufredat kontrolu basliyor...")
                        if isinstance(db_path, str):
                            auto_summary = run_automatic_scoring(db_path)
                        else:
                            auto_summary = run_automatic_scoring()
                        if isinstance(auto_summary, dict):
                            gen = auto_summary.get("generation") or {}
                            generated = gen.get("generated", []) or []
                            skipped = gen.get("skipped", []) or []
                            errors = gen.get("errors", []) or []
                            print(
                                f"[AUTO] Uretim ozeti | olusan: {len(generated)} | "
                                f"atlanan: {len(skipped)} | hata: {len(errors)}"
                            )
                            for err in errors[:5]:
                                print(f"[AUTO][HATA] {err}")
                            for sk in skipped[:5]:
                                print(f"[AUTO][ATLANAN] {sk}")
                except Exception as e:
                    print(f"[AUTO] Otomatik uretim hatasi: {e}")

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
                    f"Varsayilan veritabani yok:\n{db_path}\n\nLutfen config ayarlarini kontrol ediniz."
            )
            self.cmd_open_db()

        except Exception as e:
            messagebox.showerror(
                "Baslangic Hatasi",
                f"Uygulama baslatilirken hata olustu:\\n\\n{e}"
            )


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
            self.state.set("db_path", path)

            try:
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump({"db_path": path, "db_url": f"sqlite:///{os.path.abspath(path)}"}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            self.tab_view.fill_tables()
            self.ensure_pool_initialized_once()
            if not is_yearly_workflow_enabled():
                try:
                    run_automatic_scoring(path)
                except Exception:
                    pass
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
            messagebox.showerror("Hata", str(e))


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
                elif "Güvenlik" in inner:
                    self.tab_security_readiness.refresh_data()
            elif "Karar Süreci" in outer:
                inner = self._nb_karar.tab(self._nb_karar.index("current"), "text")
                if "Kriter" in inner:
                    self.tab_calc.refresh()
                elif "AHP" in inner:
                    self.tab_ahp_weight.refresh()
                elif "Karar Merkezi" in inner:
                    self.tab_decision_center.refresh()
                elif "Dönem" in inner:
                    self.tab_semester_planning.refresh()
            elif "Raporlama" in outer:
                inner = self._nb_rapor.tab(self._nb_rapor.index("current"), "text")
                if "Analiz" in inner:
                    self.tab_analysis.refresh()
                elif "Rapor" in inner:
                    self.tab_tools.refresh()
            elif "Benchmark" in outer:
                self.tab_benchmark.refresh()
        except Exception as e:
            messagebox.showerror("Hata", str(e))




     # =========================================================

    #  ANALİZ & DASHBOARD FONKSİYONLARI (YENİ EKLENECEK KISIM)
    # =========================================================

    def on_tab_change(self, event):
        """Dış sekme değiştiğinde aktif iç sekmeyi yeniler."""
        selected = event.widget.tab(event.widget.index("current"), "text")
        try:
            if "Sistem" in selected:
                idx = self._nb_sistem.index("current")
                inner = self._nb_sistem.tab(idx, "text")
                if "Sağlık" in inner:
                    self.tab_system_health.refresh()
                elif "Güvenlik" in inner:
                    self.tab_security_readiness.refresh_data()
            elif "Veri" in selected:
                pass
            elif "Karar Süreci" in selected:
                idx = self._nb_karar.index("current")
                inner = self._nb_karar.tab(idx, "text")
                if "Kriter" in inner:
                    self.tab_calc.refresh()
                elif "AHP" in inner:
                    self.tab_ahp_weight.refresh()
                elif "Karar Merkezi" in inner:
                    self.tab_decision_center.refresh()
                elif "Dönem" in inner:
                    self.tab_semester_planning.refresh()
            elif "Raporlama" in selected:
                idx = self._nb_rapor.index("current")
                inner = self._nb_rapor.tab(idx, "text")
                if "Analiz" in inner:
                    self.tab_analysis.refresh()
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
                elif "Güvenlik" in selected:
                    self.tab_security_readiness.refresh_data()
            elif group == "karar":
                if "Kriter" in selected:
                    self.tab_calc.refresh()
                elif "AHP" in selected:
                    self.tab_ahp_weight.refresh()
                elif "Karar Merkezi" in selected:
                    self.tab_decision_center.refresh()
                elif "Dönem" in selected:
                    self.tab_semester_planning.refresh()
            elif group == "rapor":
                if "Analiz" in selected:
                    self.tab_analysis.refresh()
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

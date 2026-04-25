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
        return int(os.environ.get("ADIL_SECMELI_API_PORT", "8000"))
    except (TypeError, ValueError):
        return 8000


DEFAULT_API_HOST = os.environ.get("ADIL_SECMELI_API_HOST", "0.0.0.0")
DEFAULT_API_PORT = _default_api_port()

# ---------- Proje kökünü Python path'e ekle ----------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# ---------- Veritabanı ve temel bileşenler ----------
from app.db.sqlite_db import Database
from app.core.state import AppState
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd


# ---------- Grafik kütüphaneleri (Tkinter uyumlu) ----------
import matplotlib
matplotlib.use("Agg" if HEADLESS else "TkAgg")
try:
    import seaborn as sns
except Exception:
    sns = None

# ---------- Servis katmanı (hesaplama, havuz kararı) ----------
from app.services.calculation import run_automatic_scoring
from app.services.course_type import build_elective_predicate
from app.services.yearly_workflow import is_yearly_workflow_enabled



# =============================================================================
# BÖLÜM 1: Yapılandırma (config.json)
# =============================================================================
def load_config():
    default = {
        "db_path": "./adil_secimli.db",
        "charts": {"bins": 15}
    }
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Adil Seçmeli giriş noktası (GUI veya headless API modu)."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "gui", "api"),
        default="auto",
        help="auto: headless ise API, degilse GUI; gui: masaustu arayuzu zorla; api: REST API baslat",
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

    if args.mode == "api":
        return run_api_server(args.host, args.port)

    if args.mode == "gui":
        return run_gui()

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
        from app.ui.tabs.view_tab import ViewTab
        from app.ui.tabs.analysis_tab import AnalysisTab
        from app.ui.tabs.calc_tab import CalcTab
        from app.ui.tabs.tools_tab import ToolsTab
        from app.ui.benchmark import BenchmarkPanel
        from app.ui.style import apply_style

        apply_style(self)
        self.config_data = load_config()
        self.db = Database()
        self.db_path = self.config_data.get("db_path")
        self.current_table = None

        self.state = AppState(db_path=self.config_data.get("db_path"))
        
        
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

        # 1. SEKME: Tablo Görüntüle (ViewTab)
        self.tab_view = ViewTab(self.nb, app=self)
        self.nb.add(self.tab_view, text="📂 Tablo Görüntüle")


        # 2. SEKME: Analiz & Grafik (AnalysisTab)
        self.tab_analysis = AnalysisTab(self.nb, app=self)
        self.nb.add(self.tab_analysis, text="📊 Analiz & Grafik")

        
        # 3. SEKME: Rapor & Yukleme (ToolsTab)
        self.tab_tools = ToolsTab(self.nb, app=self)
        self.nb.add(self.tab_tools, text="Rapor & Yukleme")


        # 🔔 Notebook tab değişim event’i
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 4. SEKME: Hesaplama & Test (CalcTab)
        self.tab_calc = CalcTab(self.nb, app=self)
        self.nb.add(self.tab_calc, text="🧮 Hesaplama & Test")

        # 5. SEKME: Benchmark Platformu
        self.tab_benchmark = BenchmarkPanel(self.nb, app=self)
        self.nb.add(self.tab_benchmark, text="Benchmark Platformu")


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
        db_path = self.config_data.get("db_path")

        if db_path:
            db_path = os.path.abspath(db_path)

        try:
            # 1) Veritabani baglantisi
            self.db.connect(db_path)
            self.tab_view.fill_tables()

            # 2) Havuz seed (bossa)
            self.ensure_pool_initialized_once()

            # 3) Otomatik sonraki yil uretimi (legacy mod)
            if is_yearly_workflow_enabled():
                print("[AUTO] ENABLE_YEARLY_CRITERIA_WORKFLOW=true -> otomatik algoritma tetigi kapali.")
            else:
                try:
                    print("[AUTO] Sonraki yil mufredat kontrolu basliyor...")
                    auto_summary = run_automatic_scoring(db_path)
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

        except FileNotFoundError:
            messagebox.showwarning(
                "Veritabani Bulunamadi",
                f"Varsayilan veritabani yok:\\n{db_path}\\n\\nLutfen dosya seciniz."
            )
            self.cmd_open_db()

        except Exception as e:
            messagebox.showerror(
                "Baslangic Hatasi",
                f"Uygulama baslatilirken hata olustu:\\n\\n{e}"
            )


    def cmd_open_db(self):
        """Kullanicidan yeni veritabani dosyasi secmesini ister ve baglantıyı yeniler."""
        path = filedialog.askopenfilename(
            title="SQLite Veritabanı Seç",
            filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("Tümü", "*.*")]
        )
        if not path:
            return
        try:
            self.db.connect(path)
            self.db_path = path
            self.state.set("db_path", path)
               # tek yerden güncelle

            try:
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump({"db_path": path}, f, ensure_ascii=False, indent=2)
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

        except Exception as e:
            messagebox.showerror("Hata", str(e))


    # ---- BÖLÜM 4: Havuz tablosu doldurma -----

    def fill_pool_table_for_years(self):
        """
        Havuz tablosunu mevcut mufredat yillari icin doldurur.
        Sadece kayit yoksa INSERT yapar (INSERT OR IGNORE).
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
            conn = getattr(self.db, "conn", None)
            if conn is not None:
                cur = conn.cursor()
                elective_predicate = build_elective_predicate(cur=cur, alias="d")
                if elective_predicate != "0=1":
                    cur.execute(
                        f"""
                        SELECT d.ders_id, d.fakulte_id, d.bolum_id, d.ad
                        FROM ders d
                        WHERE {elective_predicate}
                        """
                    )
                    dersler = cur.fetchall()
        except Exception:
            dersler = []

        if not dersler:
            return

        insert_q = """
            INSERT OR IGNORE INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
            VALUES (?, ?, ?, ?, 0, 0, NULL, ?)
        """

        cur = self.db.conn.cursor()
        for ders_id, fakulte_id, bolum_id, ders_adi in dersler:
            for yil in years:
                cur.execute(
                    insert_q,
                    (str(ders_id), yil, fakulte_id, bolum_id, str(ders_adi or "")),
                )

        self.db.conn.commit()
        print(f"[Pool] {len(dersler)} ders x {len(years)} yil = havuz seed tamamlandi.")


    def open_sql_runner(self):
        win = tk.Toplevel(self)
        win.title("SQL Çalıştır")
        win.geometry("900x600")
        txt = tk.Text(win, height=10)
        txt.pack(fill=tk.BOTH, expand=False, padx=8, pady=8)
        txt.insert(tk.END, f"SELECT name FROM sqlite_master WHERE type='table';")

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
                        if isinstance(r, sqlite3.Row):
                            tree.insert("", tk.END, values=[r[c] for c in cols])
                        else:
                            tree.insert("", tk.END, values=r)
                else:
                    messagebox.showinfo("Tamam", "Sorgu başarıyla çalıştı.")
            except Exception as e:
                messagebox.showerror("SQL Hatası", str(e))

        ttk.Button(win, text="Çalıştır", command=run).pack(pady=(0, 8))

    def refresh_all(self):
        try:
            self.tab_view.refresh()

            # Analiz sekmesi açıksa yenile
            current_tab_text = self.nb.tab(self.nb.index("current"), "text")
            if "Analiz" in current_tab_text:
                self.tab_analysis.refresh()

            if "Hesaplama" in current_tab_text:
                self.tab_calc.refresh()

            if "Rapor" in current_tab_text:
                self.tab_tools.refresh()

            if "Benchmark" in current_tab_text:
                self.tab_benchmark.refresh()


        except Exception as e:
            messagebox.showerror("Hata", str(e))

      


     # =========================================================
    
    #  ANALİZ & DASHBOARD FONKSİYONLARI (YENİ EKLENECEK KISIM)
    # =========================================================

    def on_tab_change(self, event):
        """Ana sekme degistiginde ilgili sekmenin refresh() metodunu cagırır."""
        selected_tab = event.widget.tab(event.widget.index("current"), "text")

        if "Analiz" in selected_tab:
            self.tab_analysis.refresh()

        if "Hesaplama" in selected_tab:
            self.tab_calc.refresh()

        if "Benchmark" in selected_tab:
            self.tab_benchmark.refresh()


    def ensure_pool_initialized_once(self):
        """Havuz tablosu bos ise ilk kez mufredat yillarindan seed olusturur."""
        res = self.db.run_sql("SELECT COUNT(*) FROM havuz;")
        cnt = res[1][0][0] if res[1] else 0
        if cnt == 0:
            self.fill_pool_table_for_years()


if __name__ == "__main__":
    raise SystemExit(main())

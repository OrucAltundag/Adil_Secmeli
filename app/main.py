# -*- coding: utf-8 -*-
# =============================================================================
# app/main.py — Adil Seçmeli Ana Uygulama Giriş Noktası
# =============================================================================
# Bu dosya masaüstü Tkinter uygulamasını başlatır.
# İlgili modüller: app/db (veritabanı), app/ui/tabs (sekmeler), app/services (hesaplama)
# =============================================================================

import json
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="seaborn")

# ---------- Proje kökünü Python path'e ekle ----------
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# ---------- Veritabanı ve UI bileşenleri ----------
from app.db.sqlite_db import Database
from app.ui.tabs.view_tab import ViewTab
from app.ui.tabs.analysis_tab import AnalysisTab
from app.ui.tabs.calc_tab import CalcTab
from app.ui.tabs.tools_tab import ToolsTab
from app.ui.style import apply_style
from app.core.state import AppState
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd


# ---------- Grafik kütüphaneleri (Tkinter uyumlu) ----------
import matplotlib
matplotlib.use("TkAgg")
try:
    import seaborn as sns
except Exception:
    sns = None

# ---------- Servis katmanı (hesaplama, havuz kararı) ----------
from app.services.calculation import run_automatic_scoring
from app.services.havuz_karar import muhendislik_mufredat_durumunu_esitle



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






# =============================================================================
# BÖLÜM 2: Ana Uygulama Sınıfı (AdilSecmeliApp)
# =============================================================================
class AdilSecmeliApp(tk.Tk):

    def __init__(self):
        super().__init__()
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

        
        # 3. SEKME: Rapor & Skor (ToolsTab)
        self.tab_tools = ToolsTab(self.nb, app=self)
        self.nb.add(self.tab_tools, text="⚙️ Rapor & Skor")


        # 🔔 Notebook tab değişim event’i
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 4. SEKME: Hesaplama & Test (CalcTab)
        self.tab_calc = CalcTab(self.nb, app=self)
        self.nb.add(self.tab_calc, text="🧮 Hesaplama & Test")


        # Otomatik Bağlan
        self.auto_connect()
    
   

    
    
    # ---- BÖLÜM 3: Veritabanı bağlantısı ve başlangıç -----

    def auto_connect(self):
        db_path = self.config_data.get("db_path")

        if db_path:
            db_path = os.path.abspath(db_path)

        try:
            # 1) Veritabani baglantisi
            self.db.connect(db_path)
            self.tab_view.fill_tables()

            # 2) Havuz seed (bossa)
            self.ensure_pool_initialized_once()

            # 3) Otomatik sonraki yil uretimi
            try:
                print("[AUTO] Sonraki yil mufredat kontrolu basliyor...")
                auto_summary = run_automatic_scoring(db_path)
                if isinstance(auto_summary, dict):
                    generated = auto_summary.get("generated", [])
                    skipped = auto_summary.get("skipped", [])
                    errors = auto_summary.get("errors", [])
                    print(
                        f"[AUTO] Uretim ozeti | olusan: {len(generated)} | "
                        f"atlanan: {len(skipped)} | hata: {len(errors)}"
                    )
                    for err in errors[:5]:
                        print(f"[AUTO][HATA] {err}")
            except Exception as e:
                print(f"[AUTO] Otomatik uretim hatasi: {e}")

            # 4) State-machine esitleme (dinamik yil araligi)
            try:
                _, yr = self.db.run_sql(
                    """
                    SELECT MIN(yil), MAX(yil) FROM (
                        SELECT yil as yil FROM havuz
                        UNION
                        SELECT akademik_yil as yil FROM mufredat
                    )
                    """
                )
                min_yil = int(yr[0][0]) if yr and yr[0][0] is not None else None
                max_yil = int(yr[0][1]) if yr and yr[0][1] is not None else None
                if min_yil is not None and max_yil is not None and max_yil >= min_yil:
                    print(f"[AUTO] Statu/yil esitleme: {min_yil} -> {max_yil}")
                    muhendislik_mufredat_durumunu_esitle(
                        db_path,
                        baslangic_yili=min_yil,
                        bitis_yili=max_yil,
                    )
            except Exception as e:
                print(f"[AUTO] Esitleme uyarisi: {e}")

            # 5) UI yenileme
            try:
                self.tab_calc.refresh()
            except Exception:
                pass
            try:
                self.tab_tools.refresh()
            except Exception:
                pass
            try:
                self.tab_pool.refresh()
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
                self.tab_pool.refresh()
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

        try:
            self.db.run_sql("SELECT 1 FROM ders WHERE DersTipi='Secmeli' LIMIT 1")
            col_tip = "DersTipi"
        except Exception:
            col_tip = "tip"

        q = (
            f"SELECT d.ders_id, d.fakulte_id, d.bolum_id, d.ad "
            f"FROM ders d WHERE COALESCE(d.{col_tip}, '') LIKE 'Se%'"
        )
        try:
            _, dersler = self.db.run_sql(q)
        except Exception:
            _, dersler = self.db.run_sql("SELECT ders_id, fakulte_id, bolum_id, ad FROM ders")

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


        except Exception as e:
            messagebox.showerror("Hata", str(e))

      


     # =========================================================
    
    #  ANALİZ & DASHBOARD FONKSİYONLARI (YENİ EKLENECEK KISIM)
    # =========================================================

    def on_tab_change(self, event):
        selected_tab = event.widget.tab(event.widget.index("current"), "text")

        if "Analiz" in selected_tab:
            self.tab_analysis.refresh()

        if "Hesaplama" in selected_tab:
            self.tab_calc.refresh()


    def ensure_pool_initialized_once(self):
        res = self.db.run_sql("SELECT COUNT(*) FROM havuz;")
        cnt = res[1][0][0] if res[1] else 0
        if cnt == 0:
            self.fill_pool_table_for_years()


if __name__ == "__main__":
    app = AdilSecmeliApp()
    app.mainloop()

import json
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="seaborn")

# --- BU BLOĞU EN ÜSTE EKLE ---
# Şu anki dosyanın (main.py) yolunu al
current_dir = os.path.dirname(os.path.abspath(__file__))
# Bir üst klasöre çık (Adil_Secmeli_Python klasörü)
parent_dir = os.path.dirname(current_dir)
# Bunu Python'un arama yollarına ekle
sys.path.append(parent_dir)
# -----------------------------


from app.db.sqlite_db import Database
from app.ui.tabs.view_tab import ViewTab
from app.ui.tabs.analysis_tab import AnalysisTab
from app.ui.tabs.calc_tab import CalcTab
from app.ui.tabs.tools_tab import ToolsTab
from app.ui.style import apply_style
from app.core.state import AppState
from app.ui.tabs.criteria_page import CriteriaPage 



import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd


# main.py - En üst kısım
import matplotlib
matplotlib.use("TkAgg") # Tkinter ile uyumlu backend

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
try:
    import seaborn as sns
except Exception:
    sns = None
 # Grafikleri güzelleştirmek için (opsiyonel ama şık durur)

# app/main.py en üst kısımlar
from app.services.calculation import KararMotoru, run_automatic_scoring  

from app.services.havuz_karar import muhendislik_mufredat_durumunu_esitle



# =============== Yapılandırma ==================
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






# =============== Uygulama ==================
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
            {"id": "dt",      "name": "Decision Tree (Karar)"}
        ]

        # ---- Üst çubuk (Header) ----
        topbar = ttk.Frame(self, padding=8)
        topbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(topbar, text="Adil Seçmeli • Masaüstü", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(topbar, text="Veritabanı Seç", command=self.cmd_open_db).pack(side=tk.RIGHT, padx=4)
        ttk.Button(topbar, text="Yenile", command=self.refresh_all).pack(side=tk.RIGHT, padx=4)

        # ---- Ana Konteyner ----
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # =========================================================
        # =========================================================
        # Notebook (Sekmeler)
        # =========================================================
        # =========================================================
        self.nb = ttk.Notebook(container)
        self.nb.pack(fill=tk.BOTH, expand=True)

        # =========================================================
        # 1. SEKME: TABLO GÖRÜNTÜLE (Sidebar Burada)
        # =========================================================
        # 1. SEKME: TABLO GÖRÜNTÜLE
        self.tab_view = ViewTab(self.nb, app=self)
        self.nb.add(self.tab_view, text="📂 Tablo Görüntüle")


        # =========================================================
        # 2. SEKME: ANALİZ & GRAFİK
        # =========================================================
        self.tab_analysis = AnalysisTab(self.nb, app=self)
        self.nb.add(self.tab_analysis, text="📊 Analiz & Grafik")

        
        # =========================================================
        # 3. SEKME: RAPOR & SKOR
        # =========================================================
        self.tab_tools = ToolsTab(self.nb, app=self)
        self.nb.add(self.tab_tools, text="⚙️ Rapor & Skor")


        # 🔔 Notebook tab değişim event’i
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # =========================================================
        # 4. SEKME: HESAPLAMA & TEST (EKSİK OLAN KISIM BURASIYDI)
        # =========================================================
        self.tab_calc = CalcTab(self.nb, app=self)
        self.nb.add(self.tab_calc, text="🧮 Hesaplama & Test")


        # Otomatik Bağlan
        self.auto_connect()
    
   

    
    
    # ---------- Bağlantı ----------

    def auto_connect(self):
        db_path = self.config_data.get("db_path")
        
        # Dosya yolunu garantiye al (Mutlak yol kullan)
        if db_path:
            db_path = os.path.abspath(db_path)

        try:
            # 1. Veritabanı Bağlantısı
            self.db.connect(db_path)
            self.tab_view.fill_tables()

            # 2. Havuz Başlangıç Kontrolü (Tablo boşsa ilk kayıtları atar)
            self.ensure_pool_initialized_once()

            # 3. YENİ: Otomatik Puanlama ve 2023 Seçimi (Calculation.py)
            # Bu fonksiyon: AHP/TOPSIS hesaplar, puanları basar ve 2023 müfredatına en iyi 5 dersi ekler.
            try:
                print(f"⚙️ [AUTO] Otomatik Puanlama ve Simülasyon Çalıştırılıyor...")
                run_automatic_scoring(db_path) 
            except Exception as e:
                print(f"⚠️ Otomatik puanlama hatası: {e}")

            # 4. YENİ: Statü ve Renk Eşitleme (HavuzKarar.py)
            # Bu fonksiyon: Müfredat tablosuna bakar; seçilenleri 'Yeşil' (1), düşenleri 'Kırmızı' (-1) yapar.
            try:
                print("⚙️ [AUTO] Statü ve Yıl Eşitlemesi yapılıyor...")
                muhendislik_mufredat_durumunu_esitle(db_path, baslangic_yili=2022, bitis_yili=2025)
            except Exception as e:
                print(f"⚠️ Eşitleme uyarısı: {e}")

            # 5. UI Yenileme (Hesaplama sekmesindeki verileri güncelle)
            self.tab_calc.refresh()

        except FileNotFoundError:
            messagebox.showwarning(
                "Veritabanı Bulunamadı",
                f"Varsayılan veritabanı yok:\n{db_path}\n\nLütfen dosya seçiniz."
            )
            self.cmd_open_db()

        except Exception as e:
            messagebox.showerror(
                "Başlangıç Hatası",
                f"Uygulama başlatılırken hata oluştu:\n\n{e}"
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
            self.tab_calc.refresh()  # ✅ önemli

        except Exception as e:
            messagebox.showerror("Hata", str(e))


    # ---------- Havuz Tablosu Doldurma  ----------
   
    def fill_pool_table_for_years(self):
        years = [2022, 2023, 2024, 2025]

        # Seçmeli dersleri fakülte ile birlikte al
        q = """
            SELECT d.ders_id, d.ad, d.fakulte_id
            FROM ders d
            WHERE d.DersTipi = 'Seçmeli'
        """
        _, dersler = self.db.run_sql(q)
        if not dersler:
            return

        insert_q = """
            INSERT OR IGNORE INTO havuz (ders_id, ders_adi, fakulte_id, yil, skor, sayac, statu)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        cur = self.db.conn.cursor()  # Database sınıfında conn varsa
        for ders_id, ders_adi, fakulte_id in dersler:
            for yil in years:
                cur.execute(insert_q, (ders_id, ders_adi, fakulte_id, yil, 0.5, 0, 0))

        self.db.conn.commit()

    # Bu fonksiyon çağrıldığında, her yıl için fakülteye ait dersler havuza eklenecek.
   
   
    # ---------- Tablo listesi / görüntüleme ----------

    # def fill_tables(self):
    #     self.lst_tables.delete(0, tk.END)
    #     tables = self.db.tables()
    #     for t in tables:
    #         self.lst_tables.insert(tk.END, t)
    #     if tables:
    #         self.lst_tables.selection_clear(0, tk.END)
    #         self.lst_tables.selection_set(0)
    #         self.on_table_select()

    # def on_table_select(self, _evt=None):
    #     sel = self.lst_tables.curselection()
    #     if not sel:
    #         return
    #     table = self.lst_tables.get(sel[0])
    #     self.current_table = table

    #     cols, rows = self.db.head(table, limit=2000)

    #     # Treeview başlıkları
    #     self.tree.delete(*self.tree.get_children())
    #     self.tree["columns"] = cols
    #     for c in cols:
    #         self.tree.heading(c, text=c, command=lambda col=c: self.sort_by(col, False))
    #         self.tree.column(c, width=140, anchor="center")
    #     # satırlar
    #     for r in rows:
    #         self.tree.insert("", tk.END, values=[r[c] for c in cols])

    # def sort_by(self, col, descending):
    #     data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
    #     try:
    #         data.sort(key=lambda t: float(t[0]), reverse=descending)
    #     except Exception:
    #         data.sort(key=lambda t: t[0], reverse=descending)
    #     for index, item in enumerate(data):
    #         self.tree.move(item[1], "", index)
    #     self.tree.heading(col, command=lambda: self.sort_by(col, not descending))

    # def apply_filter(self):
    #     if not self.current_table:
    #         return
    #     q = self.search_var.get().strip()
    #     if not q:
    #         self.on_table_select()
    #         return
    #     cols, _ = self.db.head(self.current_table, limit=1)
    #     like_cols = " OR ".join([f"CAST({c} AS TEXT) LIKE :kw" for c in cols])
    #     query = f"SELECT * FROM {self.current_table} WHERE {like_cols} LIMIT 2000;"
    #     df = self.db.read_df(query.replace(":kw", f"'%{q.replace('%','') }%'"))
        
    #     self.tree.delete(*self.tree.get_children())
    #     self.tree["columns"] = list(df.columns)
    #     for c in df.columns:
    #         self.tree.heading(c, text=c)
    #         self.tree.column(c, width=140, anchor="center")
    #     for _, row in df.iterrows():
    #         self.tree.insert("", tk.END, values=list(row.values))

    # ---------- SQL Çalıştırıcı ----------

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
        res = self.db.run_sql("SELECT COUNT(*) FROM havuz WHERE yil BETWEEN 2022 AND 2025;")
        cnt = res[1][0][0] if res[1] else 0
        if cnt == 0:
            self.fill_pool_table_for_years()



if __name__ == "__main__":
    app = AdilSecmeliApp()
    app.mainloop()
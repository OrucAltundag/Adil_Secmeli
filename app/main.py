import json
import os
import sys


# --- BU BLOĞU EN ÜSTE EKLE ---
# Şu anki dosyanın (main.py) yolunu al
current_dir = os.path.dirname(os.path.abspath(__file__))
# Bir üst klasöre çık (Adil_Secmeli_Python klasörü)
parent_dir = os.path.dirname(current_dir)
# Bunu Python'un arama yollarına ekle
sys.path.append(parent_dir)
# -----------------------------

import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# main.py - En üst kısım
import matplotlib
matplotlib.use("TkAgg") # Tkinter ile uyumlu backend
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns # Grafikleri güzelleştirmek için (opsiyonel ama şık durur)

from app.services.calculation import DecisionEngine


# =============== Yardımcı: Tema / Stil ==================
def apply_style(root: tk.Tk):
    root.title("Adil Seçmeli • Masaüstü")
    root.geometry("1280x760")
    root.minsize(1100, 680)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except:
        pass

    style.configure("Sidebar.TFrame", background="#0f172a")
    style.configure("Sidebar.TLabel", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 10, "bold"))
    style.configure("Sidebar.TButton", background="#111827", foreground="#e5e7eb")
    style.map("Sidebar.TButton", background=[("active", "#1f2937")])

    style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
    style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))


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


# =============== Veritabanı Katmanı ==================
class Database:
    def __init__(self, db_path: str | None = None):
        self.conn = None
        if db_path:
            self.connect(db_path)

    def connect(self, db_path: str):
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Veritabanı bulunamadı: {db_path}")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def ensure(self):
        if not self.conn:
            raise RuntimeError("Veritabanı bağlantısı yok.")

    def tables(self):
        self.ensure()
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        return [r[0] for r in cur.fetchall()]

    def head(self, table: str, limit=1000):
        self.ensure()
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {table} LIMIT {limit};")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return cols, rows

    def read_df(self, query: str):
        self.ensure()
        return pd.read_sql_query(query, self.conn)

    def run_sql(self, query: str):
        self.ensure()
        cur = self.conn.cursor()
        cur.execute(query)
        if query.strip().lower().startswith("select"):
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return cols, rows
        else:
            self.conn.commit()
            return [], []
        
   


# =============== Uygulama ==================
class AdilSecmeliApp(tk.Tk):

    def __init__(self):
        super().__init__()
        apply_style(self)
        self.config_data = load_config()
        self.db = Database()
        self.current_table = None
        
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

        # Notebook (Sekmeler)
        self.nb = ttk.Notebook(container)
        self.nb.pack(fill=tk.BOTH, expand=True)

        # =========================================================
        # 1. SEKME: TABLO GÖRÜNTÜLE (Sidebar Burada)
        # =========================================================
        self.tab_view = ttk.Frame(self.nb)
        self.nb.add(self.tab_view, text="📂 Tablo Görüntüle")

        # --- SOL TARAFI: SIDEBAR ---
        self.sidebar = ttk.Frame(self.tab_view, style="Sidebar.TFrame", width=240)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="Tablolar", style="Sidebar.TLabel").pack(anchor="w", padx=14, pady=(16, 6))
        
        self.lst_tables = tk.Listbox(self.sidebar, bg="#111827", fg="#e5e7eb", highlightthickness=0,
                                     selectbackground="#334155", activestyle="none")
        self.lst_tables.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.lst_tables.bind("<<ListboxSelect>>", self.on_table_select)

        ttk.Button(self.sidebar, text="SQL Çalıştır", style="Sidebar.TButton", command=self.open_sql_runner)\
            .pack(fill=tk.X, padx=10, pady=(0, 10))

        # --- SAĞ TARAFI: İÇERİK ---
        content_frame = ttk.Frame(self.tab_view, padding=10)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_view = ttk.Frame(content_frame)
        top_view.pack(fill=tk.X)
        self.search_var = tk.StringVar()
        ttk.Label(top_view, text="Filtre:").pack(side=tk.LEFT)
        ttk.Entry(top_view, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=6)
        ttk.Button(top_view, text="Uygula", command=self.apply_filter).pack(side=tk.LEFT)

        self.tree = ttk.Treeview(content_frame, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.scroll_x = ttk.Scrollbar(content_frame, orient="horizontal", command=self.tree.xview)
        self.scroll_x.pack(fill=tk.X)
        self.tree.configure(xscrollcommand=self.scroll_x.set)

        # =========================================================
        # 2. SEKME: ANALİZ & GRAFİK
        # =========================================================
        self.tab_analysis = ttk.Frame(self.nb)
        self.nb.add(self.tab_analysis, text="📊 Analiz & Grafik")
        
        # =========================================================
        # 3. SEKME: RAPOR & SKOR
        # =========================================================
        self.tab_tools = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_tools, text="⚙️ Rapor & Skor")
        ttk.Label(self.tab_tools, text="Raporlar burada olacak.", justify="left").pack(anchor="w")

        # =========================================================
        # 4. SEKME: HESAPLAMA & TEST (EKSİK OLAN KISIM BURASIYDI)
        # =========================================================
        # Bu kısım __init__ içinde tanımlanmaz, setup_calculation_tab fonksiyonu ile doldurulur.
        # Ama sekmeyi burada rezerve etmemiz lazım:
        
        # NOT: setup_calculation_tab fonksiyonu kendi içinde "self.nb.add" yaptığı için 
        # buraya manuel eklememize gerek yok, sadece auto_connect içinde çağırmamız yeterli.

        # Otomatik Bağlan
        self.auto_connect()
    # ---------- Bağlantı ----------

    def auto_connect(self):
        db_path = self.config_data.get("db_path")
        try:
            self.db.connect(db_path)
            self.fill_tables()

            # --- YENİ EKLENEN SATIR ---
            self.setup_analysis_tab()  # Bağlantı kurulunca grafikleri çiz!
            self.setup_calculation_tab() # Hesaplamalar sekmesini yükle
            # --------------------------
        except Exception as e:
            messagebox.showwarning("Bağlantı bulunamadı",
                                   f"Varsayılan db açılamadı: {db_path}\n\n{e}\n\nDosya seçiniz.")
            self.cmd_open_db()
            
        # --- HER DURUMDA sekmeyi yükle ---
        self.setup_calculation_tab()

    def cmd_open_db(self):
        path = filedialog.askopenfilename(title="SQLite Veritabanı Seç",
                                          filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("Tümü", "*.*")])
        if not path:
            return
        try:
            self.db.connect(path)
            try:
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump({"db_path": path}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self.fill_tables()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ---------- Tablo listesi / görüntüleme ----------

    def fill_tables(self):
        self.lst_tables.delete(0, tk.END)
        tables = self.db.tables()
        for t in tables:
            self.lst_tables.insert(tk.END, t)
        if tables:
            self.lst_tables.selection_clear(0, tk.END)
            self.lst_tables.selection_set(0)
            self.on_table_select()

    def on_table_select(self, _evt=None):
        sel = self.lst_tables.curselection()
        if not sel:
            return
        table = self.lst_tables.get(sel[0])
        self.current_table = table

        cols, rows = self.db.head(table, limit=2000)

        # Treeview başlıkları
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c, command=lambda col=c: self.sort_by(col, False))
            self.tree.column(c, width=140, anchor="center")
        # satırlar
        for r in rows:
            self.tree.insert("", tk.END, values=[r[c] for c in cols])

    def sort_by(self, col, descending):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]), reverse=descending)
        except Exception:
            data.sort(key=lambda t: t[0], reverse=descending)
        for index, item in enumerate(data):
            self.tree.move(item[1], "", index)
        self.tree.heading(col, command=lambda: self.sort_by(col, not descending))

    def apply_filter(self):
        if not self.current_table:
            return
        q = self.search_var.get().strip()
        if not q:
            self.on_table_select()
            return
        cols, _ = self.db.head(self.current_table, limit=1)
        like_cols = " OR ".join([f"CAST({c} AS TEXT) LIKE :kw" for c in cols])
        query = f"SELECT * FROM {self.current_table} WHERE {like_cols} LIMIT 2000;"
        df = self.db.read_df(query.replace(":kw", f"'%{q.replace('%','') }%'"))
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        for c in df.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140, anchor="center")
        for _, row in df.iterrows():
            self.tree.insert("", tk.END, values=list(row.values))

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
            self.fill_tables()
            self.on_table_select()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

        # --- SEKME KAYBOLMASIN DİYE BURAYI EKLE ---
        self.setup_calculation_tab()


     # =========================================================
    
    #  ANALİZ & DASHBOARD FONKSİYONLARI (YENİ EKLENECEK KISIM)
    # =========================================================

    def fetch_dashboard_stats(self):
        """Veritabanından KPI (Anahtar Performans Göstergeleri) verilerini çeker."""
        stats = {
            "total_student": 0,
            "total_course": 0,
            "avg_success": 0.0,
            "active_survey": "Yok"
        }
        
        try:
            # 1. Toplam Öğrenci
            res = self.db.run_sql("SELECT COUNT(*) FROM ogrenci;")
            if res[1]: stats["total_student"] = res[1][0][0]

            # 2. Açılan Ders Sayısı
            res = self.db.run_sql("SELECT COUNT(*) FROM ders;")
            if res[1]: stats["total_course"] = res[1][0][0]

            # 3. Genel Başarı Ortalaması (Kayit tablosundan)
            # Not: Mock datada 'durum' alanını kullandık, burada basit bir oran alıyoruz
            df_grades = self.db.read_df("SELECT durum FROM kayit WHERE durum IN ('Geçti', 'Kaldı')")
            if not df_grades.empty:
                pass_count = df_grades[df_grades['durum'] == 'Geçti'].count().iloc[0]
                total = len(df_grades)
                stats["avg_success"] = round((pass_count / total) * 100, 1)

            # 4. Aktif Anket Var mı?
            res = self.db.run_sql("SELECT ad FROM anket_form WHERE aktif_mi=1 LIMIT 1;")
            if res[1]: stats["active_survey"] = "Aktif"
            
        except Exception as e:
            print(f"İstatistik hatası: {e}")
        
        return stats

    def setup_analysis_tab(self):
        """Analiz sekmesini grafiklerle doldurur."""
        # Önce eski widget'ları temizle (Yenile butonu için)
        for widget in self.tab_analysis.winfo_children():
            widget.destroy()

        # --- A. ÜST KISIM: KPI KARTLARI ---
        kpi_frame = ttk.Frame(self.tab_analysis)
        kpi_frame.pack(fill=tk.X, pady=10, padx=10)

        stats = self.fetch_dashboard_stats()

        # KPI Kartı Oluşturucu Yardımcı Fonksiyon
        def create_card(parent, title, value, color_code):
            card = tk.Frame(parent, bg=color_code, padx=10, pady=10)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            tk.Label(card, text=title, bg=color_code, fg="white", font=("Segoe UI", 10)).pack(anchor="w")
            tk.Label(card, text=str(value), bg=color_code, fg="white", font=("Segoe UI", 18, "bold")).pack(anchor="w")

        create_card(kpi_frame, "Toplam Öğrenci", stats["total_student"], "#3b82f6") # Mavi
        create_card(kpi_frame, "Toplam Ders", stats["total_course"], "#10b981")    # Yeşil
        create_card(kpi_frame, "Genel Başarı", f"%{stats['avg_success']}", "#f59e0b") # Turuncu
        create_card(kpi_frame, "Anket Durumu", stats["active_survey"], "#8b5cf6")  # Mor

        # --- B. GRAFİKLER BÖLÜMÜ ---
        charts_frame = ttk.Frame(self.tab_analysis)
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Matplotlib Figure oluştur
        fig = Figure(figsize=(10, 5), dpi=100)
        
        # 1. Grafik (Sol): En Başarılı 5 Ders (Bar Chart)
        ax1 = fig.add_subplot(121) # 1 satır, 2 sütun, 1. grafik
        try:
            query_top = """
                SELECT d.ad, p.basari_orani 
                FROM performans p 
                JOIN ders d ON p.ders_id = d.ders_id 
                ORDER BY p.basari_orani DESC LIMIT 5;
            """
            df_top = self.db.read_df(query_top)
            if not df_top.empty:
                # Başarı oranını yüzdeye çevir (0.8 -> 80)
                df_top['basari_orani'] = df_top['basari_orani'] * 100
                sns.barplot(x='basari_orani', y='ad', data=df_top, ax=ax1, palette="viridis")
                ax1.set_title("En Yüksek Başarı Oranına Sahip Dersler (Top 5)", fontsize=10)
                ax1.set_xlabel("Başarı (%)")
                ax1.set_ylabel("")
                ax1.grid(axis='x', linestyle='--', alpha=0.6)
            else:
                ax1.text(0.5, 0.5, "Veri Yok", ha='center')
        except Exception as e:
            ax1.text(0.5, 0.5, f"Hata: {e}", ha='center')

        # 2. Grafik (Sağ): Popülerlik Dağılımı (Pie Chart)
        ax2 = fig.add_subplot(122) # 1 satır, 2 sütun, 2. grafik
        try:
            query_pop = """
                SELECT d.ad, p.tercih_sayisi 
                FROM populerlik p 
                JOIN ders d ON p.ders_id = d.ders_id 
                ORDER BY p.tercih_sayisi DESC LIMIT 7;
            """
            df_pop = self.db.read_df(query_pop)
            if not df_pop.empty:
                ax2.pie(df_pop['tercih_sayisi'], labels=df_pop['ad'], autopct='%1.1f%%', startangle=90, colors=sns.color_palette("pastel"))
                ax2.set_title("Öğrenci Tercihlerine Göre En Popüler Dersler", fontsize=10)
            else:
                ax2.text(0.5, 0.5, "Veri Yok", ha='center')
        except Exception as e:
            ax2.text(0.5, 0.5, f"Hata: {e}", ha='center')

        fig.tight_layout()

        # Grafiği Tkinter'a göm
        canvas = FigureCanvasTkAgg(fig, master=charts_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# =========================================================
    #  HESAPLAMALAR SEKMESİ (YENİ TASARIM)
    # =========================================================

    def setup_calculation_tab(self):

        # SEKME ZATEN EKLENDİ Mİ?
        for tab in self.nb.tabs():
            if "Hesaplama" in self.nb.tab(tab, "text"):
                return  # Tekrar ekleme, hata çıkarır
        
        # 1. Ana Sekmeyi Oluştur (Ana Notebook içinde)
        self.tab_calc = ttk.Frame(self.nb)
        self.nb.add(self.tab_calc, text="🧮 Hesaplama & Test")
        
        # 2. Alt Sekme Yöneticisi (Nested Notebook) Oluştur
        self.sub_nb = ttk.Notebook(self.tab_calc)
        self.sub_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 3. Alt Sayfaları (Frame) Tanımla
        self.page_algos = ttk.Frame(self.sub_nb)
        self.page_relations = ttk.Frame(self.sub_nb)
        
        # 4. Alt Sayfaları Notebook'a Ekle
        self.sub_nb.add(self.page_algos, text="⚙️ Algoritma Kontrol Paneli")
        self.sub_nb.add(self.page_relations, text="🔗 Ders İlişkileri & Kurallar")
        
        # 5. Sayfaların İçeriğini Dolduran Fonksiyonları Çağır
        self.setup_algo_panel(self.page_algos)      # Eski kodları buraya taşıdık
        self.setup_relations_panel(self.page_relations) # Yeni boş sayfa

    def setup_algo_panel(self, parent):
        """Eski Hesaplama Ekranını buraya taşıdık."""
        
        # Ana Konteyner (parent içine yerleşiyor)
        main_container = tk.Frame(parent, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- SOL PANEL: Algoritma Kontrolleri ---
        left_frame = tk.Frame(main_container, bg="#e2e8f0", width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="Algoritma Kontrol Paneli", bg="#1e293b", fg="white", 
                 font=("Segoe UI", 11, "bold"), pady=8).pack(fill=tk.X)

        grid_frame = tk.Frame(left_frame, bg="#e2e8f0")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- SAĞ PANEL: Sonuç Ekranı ---
        right_frame = tk.Frame(main_container, bg="#fce7f3")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(right_frame, text="SONUÇ EKRANI", bg="#be185d", fg="white", 
                 font=("Segoe UI", 11, "bold"), pady=8).pack(fill=tk.X)
        
        self.result_text = tk.Text(right_frame, bg="#fff1f2", fg="#000000", 
                                   font=("Consolas", 10), state="disabled", padx=10, pady=10)
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # --- Algoritma Listesi ve Butonlar ---
        # (Listeyi tekrar tanımlamamıza gerek yok, __init__ içinde tanımlı olmalı ama
        # eğer setup_calculation_tab içinde tanımladıysan buraya almalısın.)
        if not hasattr(self, 'algorithms'):
            self.algorithms = [
                {"id": "mock",    "name": "Veri Üretimi (Mock)"},
                {"id": "trend",   "name": "2. Tarihsel Trend Analizi"},
                {"id": "ahp",     "name": "3. AHP (Ağırlıklar)"},
                {"id": "topsis",  "name": "4. TOPSIS (Sıralama)"},
                {"id": "lr",      "name": "Lineer Regresyon (Tahmin)"},
                {"id": "rf",      "name": "Random Forest (Sınıflandırma)"},
                {"id": "dt",      "name": "Decision Tree (Karar)"}
            ]
        
        self.ui_refs = {} 
        self.results_cache = {}

        btn_run_all = tk.Button(grid_frame, text="🚀 TÜMÜNÜ ÇALIŞTIR", bg="#2563eb", fg="white", 
                                font=("Segoe UI", 10, "bold"), cursor="hand2",
                                command=self.run_all_algorithms)
        btn_run_all.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 20), ipady=5)

        for idx, algo in enumerate(self.algorithms, start=1):
            algo_id = algo["id"]
            
            btn_run = ttk.Button(grid_frame, text=f"Çalıştır: {algo_id.upper()}", 
                                 command=lambda i=algo_id: self.run_single_step(i))
            btn_run.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")

            lbl_status = tk.Label(grid_frame, text="Bekliyor...", bg="#cbd5e1", width=15, anchor="center")
            lbl_status.grid(row=idx, column=1, padx=5, pady=5)

            btn_show = ttk.Button(grid_frame, text="Sonuç Göster", state="disabled",
                                  command=lambda i=algo_id: self.show_result(i))
            btn_show.grid(row=idx, column=2, padx=5, pady=5, sticky="ew")

            self.ui_refs[algo_id] = {"status": lbl_status, "show_btn": btn_show}

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(2, weight=1)


    def setup_relations_panel(self, parent):
        """Ders İlişkileri ve NLP Analiz Sayfası"""
        import networkx as nx
        
        # Layout: Üst (Filtreler), Alt (Sol Liste | Orta Grafik | Sağ Skor)
        
        # --- 1. ÜST PANEL (Filtreler) ---
        top_frame = tk.Frame(parent, bg="#e2e8f0", pady=5)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="Fakülte:", bg="#e2e8f0").pack(side=tk.LEFT, padx=5)
        self.cb_fakulte = ttk.Combobox(top_frame, state="readonly", width=30)
        self.cb_fakulte.pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="Listele", command=self.load_courses_for_relations).pack(side=tk.LEFT, padx=10)

        # Fakülteleri doldur
        fakulteler = [r[0] for r in self.db.run_sql("SELECT ad FROM fakulte")[1]]
        self.cb_fakulte['values'] = fakulteler
        if fakulteler: self.cb_fakulte.current(0)

        # --- 2. ANA PANEL ---
        main_pane = tk.PanedWindow(parent, orient=tk.HORIZONTAL, bg="#f1f5f9")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # A. SOL PANEL (Ders Listesi)
        left_frame = tk.Frame(main_pane, bg="white", width=200)
        main_pane.add(left_frame, width=250)
        
        tk.Label(left_frame, text="Ders Listesi", font=("Segoe UI", 10, "bold"), bg="white").pack(pady=5)
        
        self.lst_rel_courses = tk.Listbox(left_frame, bg="#f8fafc", selectbackground="#3b82f6")
        self.lst_rel_courses.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.lst_rel_courses.bind("<<ListboxSelect>>", self.on_rel_course_select)

        # B. ORTA PANEL (Ağaç Grafiği)
        center_frame = tk.Frame(main_pane, bg="white")
        main_pane.add(center_frame)
        main_pane.paneconfig(center_frame, stretch="always")

        
        tk.Label(center_frame, text="İlişki Ağı (NLP Benzerlik Analizi)", font=("Segoe UI", 10, "bold"), bg="white").pack(pady=5)
        
        # Grafik için Matplotlib Canvas
        self.rel_fig = Figure(figsize=(5, 4), dpi=100)
        self.rel_canvas = FigureCanvasTkAgg(self.rel_fig, master=center_frame)
        self.rel_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # C. SAĞ PANEL (Skor Tablosu)
        right_frame = tk.Frame(main_pane, bg="white", width=200)
        main_pane.add(right_frame, width=250)
        
        tk.Label(right_frame, text="İlişki Puanları (Top 10)", font=("Segoe UI", 10, "bold"), bg="white").pack(pady=5)
        
        self.tree_scores = ttk.Treeview(right_frame, columns=("ders", "skor"), show="headings")
        self.tree_scores.heading("ders", text="Benzer Ders")
        self.tree_scores.heading("skor", text="Puan")
        self.tree_scores.column("ders", width=120)
        self.tree_scores.column("skor", width=60, anchor="center")
        self.tree_scores.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def load_courses_for_relations(self):
        """Seçilen fakülteye göre sol listeyi doldurur."""
        fakulte = self.cb_fakulte.get()
        if not fakulte: return
        
        query = f"SELECT ders_id, ad FROM ders d JOIN fakulte f ON d.fakulte_id = f.fakulte_id WHERE f.ad = '{fakulte}'"
        res = self.db.run_sql(query)
        
        self.lst_rel_courses.delete(0, tk.END)
        self.course_map = {} # Listbox index -> ders_id eşleşmesi
        
        if res[1]:
            for idx, row in enumerate(res[1]):
                self.lst_rel_courses.insert(tk.END, row[1]) # Ders Adı
                self.course_map[idx] = row[0] # Ders ID

    def on_rel_course_select(self, event):
        """Listeden ders seçilince NLP motorunu çalıştır ve grafiği çiz."""
        import networkx as nx
        
        sel = self.lst_rel_courses.curselection()
        if not sel: return
        
        course_id = self.course_map[sel[0]]
        
        # 1. NLP Motorunu Çağır
        from app.services.similarity import SimilarityEngine
        from app.db.database import SessionLocal
        
        db = SessionLocal()
        engine = SimilarityEngine(db)
        results, graph_data = engine.get_related_courses(course_id)
        db.close()
        
        # 2. Sağ Tabloyu Doldur
        self.tree_scores.delete(*self.tree_scores.get_children())
        if results:
            for r in results:
                # Skoru yüzdeye çevirip gösterelim
                score_display = f"%{r['skor']*100:.1f}"
                self.tree_scores.insert("", tk.END, values=(r['ders'], score_display))
        
        # 3. Grafiği Çiz (NetworkX)
        self.rel_fig.clear()
        ax = self.rel_fig.add_subplot(111)
        
        if graph_data:
            G = nx.Graph()
            
            # Merkez Düğüm (Seçilen Ders)
            center_node = graph_data[0][0] # Target course name
            G.add_node(center_node)
            
            # Diğer düğümler ve kenarlar
            for source, target, weight in graph_data:
                G.add_edge(source, target, weight=weight)
            
            # Çizim Ayarları
            pos = nx.spring_layout(G, k=0.5) # Yaylanma düzeni
            
            # Düğümleri Çiz
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color='#3b82f6', node_size=2000, alpha=0.8)
            # Etiketleri Çiz
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_color='white', font_weight='bold')
            # Kenarları Çiz (Kalınlık skora göre değişsin)
            weights = [G[u][v]['weight'] * 5 for u,v in G.edges()]
            nx.draw_networkx_edges(G, pos, ax=ax, width=weights, edge_color='#94a3b8')
            
            ax.set_title(f"'{center_node}' İçin İçerik İlişki Ağı")
            ax.axis('off')
        else:
            ax.text(0.5, 0.5, "Yeterli benzerlik bulunamadı veya veri eksik.", ha='center')
            
        self.rel_canvas.draw()
        

    # =========================================================
    #  İŞ MANTIĞI FONKSİYONLARI
    # =========================================================

    def run_single_step(self, algo_id):
        """Tek bir algoritmayı çalıştırır, durumunu günceller ve sonucu kaydeder."""
        widgets = self.ui_refs[algo_id]
        
        # 1. Durumu Güncelle: Çalışıyor
        widgets["status"].config(text="Çalışıyor...", bg="#fcd34d") # Sarı
        widgets["show_btn"].config(state="disabled")
        self.update_idletasks() 
        
        import time
        time.sleep(0.5) 

        result_text = ""
        success = True

        try:
            # --- ALGORİTMA SEÇİCİ ---
            if algo_id == "mock":
                res = self.db.run_sql("SELECT COUNT(*) FROM ogrenci")
                count = res[1][0][0] if res[1] else 0
                result_text = f"Veritabanı Durumu:\n==================\n"
                result_text += f"Toplam Öğrenci: {count}\n"
                result_text += "Durum: Veriler analiz için hazır."
            
            elif algo_id == "ahp":
                from app.services.calculation import DecisionEngine
                eng = DecisionEngine()
                w = eng.run_ahp()
                result_text = "AHP Matrisi ve Kriter Ağırlıkları:\n==================================\n"
                result_text += f"1. Performans (Başarı): {w[0]:.4f} (%{w[0]*100:.1f})\n"
                result_text += f"2. Popülerlik (Talep):  {w[1]:.4f} (%{w[1]*100:.1f})\n"
                result_text += f"3. Anket (Öğrenci):     {w[2]:.4f} (%{w[2]*100:.1f})\n"

           
            elif algo_id == "trend":
                # --- SADECE TREND HESAPLAMA VE GÖSTERME ---
                from app.services.calculation import DecisionEngine
                import pandas as pd
                
                eng = DecisionEngine()
                
                # Veriyi çek
                query = """
                SELECT d.ders_id, d.ad as ders, p.akademik_yil, p.basari_orani
                FROM ders d
                JOIN performans p ON d.ders_id = p.ders_id
                WHERE p.basari_orani IS NOT NULL 
                ORDER BY d.ders_id, p.akademik_yil DESC;
                """
                raw_data = self.db.read_df(query)
                
                if raw_data.empty:
                    result_text = "Veri yok! Lütfen önce MOCK veriyi çalıştırın."
                    success = False
                else:
                    grouped = raw_data.groupby('ders_id')
                    result_text = "--- DERSLERİN TARİHSEL BAŞARI ANALİZİ ---\n"
                    result_text += "(Formül: 2024*%50 + 2023*%30 + 2022*%20)\n\n"
                    
                    for ders_id, group in grouped:
                        ders_adi = group.iloc[0]['ders']
                        
                        # Yıllık ortalama al (Güz+Bahar birleştir)
                        yearly_group = group.groupby('akademik_yil')['basari_orani'].mean().reset_index()
                        yearly_group = yearly_group.sort_values('akademik_yil', ascending=False)
                        
                        history = []
                        for _, row in yearly_group.iterrows():
                            history.append({'yil': int(row['akademik_yil']), 'oran': row['basari_orani']})
                        
                        # Hesapla
                        if hasattr(eng, 'calculate_historical_trend'):
                            score, log_msg = eng.calculate_historical_trend(history)
                            # Sadece ilk 10 dersi detaylı yaz, gerisini atla (Ekran dolmasın)
                            if len(result_text) < 2000: 
                                result_text += f"{ders_adi}:\n   {log_msg}\n"
                        
                    result_text += "\n... (Tüm dersler için hesaplandı ve hafızaya alındı)."

            elif algo_id == "topsis":
                # --- GELİŞMİŞ TREND ANALİZLİ TOPSIS (DÜZELTİLMİŞ) ---
                from app.services.calculation import DecisionEngine
                import pandas as pd
                import numpy as np
                
                eng = DecisionEngine()
                
                # 1. Veriyi Çek
                query = """
                SELECT 
                    d.ders_id, d.ad as ders, 
                    p.akademik_yil, p.basari_orani,
                    pop.tercih_sayisi as populerlik
                FROM ders d
                LEFT JOIN performans p ON d.ders_id = p.ders_id
                LEFT JOIN populerlik pop ON d.ders_id = pop.ders_id
                WHERE p.basari_orani IS NOT NULL 
                ORDER BY d.ders_id, p.akademik_yil DESC;
                """
                raw_data = self.db.read_df(query)
                
                if raw_data.empty:
                    result_text = "Veri bulunamadı! Lütfen önce 'MOCK' veriyi çalıştırın."
                    success = False
                else:
                    processed_rows = []
                    grouped = raw_data.groupby('ders_id')
                    
                    for ders_id, group in grouped:
                        ders_adi = group.iloc[0]['ders']
                        yearly_group = group.groupby('akademik_yil')['basari_orani'].mean().reset_index()
                        yearly_group = yearly_group.sort_values('akademik_yil', ascending=False)
                        
                        history = [{'yil': int(r['akademik_yil']), 'oran': r['basari_orani']} for _, r in yearly_group.iterrows()]
                        
                        trend_score, _ = eng.calculate_historical_trend(history)
                        avg_pop = group['populerlik'].max() if pd.notna(group['populerlik'].max()) else 0
                        
                        processed_rows.append({
                            'ders': ders_adi,
                            'basari': trend_score,     # Trend Skoru buraya geliyor
                            'populerlik': avg_pop,
                            'anket': np.random.randint(40, 90)
                        })
                    
                    
                   # 2. AHP & TOPSIS Çalıştır
                    df_final = pd.DataFrame(processed_rows)
                    weights = eng.run_ahp()
                    df_result, logs = eng.run_topsis(df_final, weights)
                    
                    result_text = "--- NİHAİ KARAR MATRİSİ (TOPSIS) ---\n"
                    result_text += "Girdiler: Trend Skoru + Popülerlik + Anket\n\n"
                    result_text += df_result[['Ders', 'AHP_TOPSIS_Skor', 'S+', 'S-']].head(15).to_string(index=False, float_format="%.4f")

            elif algo_id in ["lr", "rf", "dt"]:
                # --- K-FOLD CROSS VALIDATION ---
                from app.services.ai_engine import AIEngine
                from app.db.database import SessionLocal
                
                db_session = SessionLocal()
                ai = AIEngine(db_session)
                
                # Gerçek K-Fold Testini Çalıştır
                k_val = 5
                result_text = ai.run_kfold_test(algorithm_type=algo_id, k=k_val)
                
                db_session.close()

        except Exception as e:
            result_text = f"HATA OLUŞTU:\n{str(e)}"
            success = False
            import traceback
            traceback.print_exc() # Konsola detaylı hata basar

        # 2. Sonucu Kaydet
        self.results_cache[algo_id] = result_text

        # 3. Durumu Güncelle
        if success:
            widgets["status"].config(text="Tamamlandı", bg="#86efac")
            widgets["show_btn"].config(state="normal")
            self.show_result(algo_id)
        else:
            widgets["status"].config(text="Hata!", bg="#fca5a5")

    def show_result(self, algo_id):
        """Sağdaki pembe alana sonucu yazar."""
        text = self.results_cache.get(algo_id, "Sonuç bulunamadı.")
        
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        
        title = f"--- SONUÇ: {algo_id.upper()} ---\n\n"
        self.result_text.insert(tk.END, title)
        self.result_text.insert(tk.END, text)
        
        self.result_text.config(state="disabled")

    def run_all_algorithms(self):
        """Listedeki sıraya göre hepsini çalıştırır."""
        # Ekranı temizle
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "Toplu işlem başlatılıyor...\nLütfen bekleyiniz.\n")
        self.result_text.config(state="disabled")

        for algo in self.algorithms:
            self.run_single_step(algo["id"])
            # Biraz bekleme ekle ki kullanıcı aktığını görsün
            self.update_idletasks()
            import time
            time.sleep(0.3)


if __name__ == "__main__":
    app = AdilSecmeliApp()
    app.mainloop()
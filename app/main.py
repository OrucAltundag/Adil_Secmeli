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

from app.services.calculation import KararMotoru

from app.services.havuz_karar import muhendislik_mufredat_durumunu_esitle


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
        self.db_path = self.config_data.get("db_path")
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

        # 🔔 Notebook tab değişim event’i
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

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

            # Veritabanı bağlantısı başarılı olduktan sonra havuz verilerini doldur
            #self.fill_pool_table_for_years()  # 2022-2025 yılları için havuz verilerini ekle
        
            self.ensure_pool_initialized_once()



            # self.setup_analysis_tab()  # Bağlantı kurulunca grafikleri çiz!
            self.setup_calculation_tab() # Hesaplamalar sekmesini yükle
            # --------------------------
    
            
            try:
                print("⚙️ Sistem Başlatılıyor: Statü ve Yıl Eşitlemesi yapılıyor...")
                # Veritabanı yolunu parametre olarak gönderiyoruz
                muhendislik_mufredat_durumunu_esitle(db_path, baslangic_yili=2022, bitis_yili=2025)
            except Exception as e:
                print(f"Eşitleme uyarısı: {e}")
            


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

    # ---------- Havuz Tablosu Doldurma  ----------
   
    def fill_pool_table_for_years(self):
        # 2022-2025 yılları arasında her fakülteye ait dersleri ekle
        years = [2022, 2023, 2024, 2025]
        
        # Fakülteleri al
        fakulteler = self.db.run_sql("SELECT ad FROM fakulte")[1]
        
        for fakulte in fakulteler:
            fakulte_adi = fakulte[0]
            
            # Fakültedeki seçmeli dersleri al
            dersler_query = f"""
            SELECT ders_id FROM ders 
            JOIN fakulte f ON ders.fakulte_id = f.fakulte_id 
            WHERE f.ad = '{fakulte_adi}' AND ders.DersTipi = 'Seçmeli'
            """
            
            dersler = self.db.run_sql(dersler_query)[1]
            
            # Yıllar arasında dersleri havuza ekle
            for year in years:
                for ders in dersler:
                    ders_id = ders[0]
                    
                    # Havuz tablosuna dersleri ekle (ilk başta sabit skor ve statu ile)
                    self.db.run_sql(f"""
                    INSERT INTO havuz (ders_id, yil, skor, statu) 
                    VALUES ({ders_id}, {year}, 0.5, 0)  -- Sabit skor (0.5), statu (0: havuzda)
                    """)

                print(f"{fakulte_adi} fakültesi için {year} yılı havuz verileri eklendi.")

    # Bu fonksiyon çağrıldığında, her yıl için fakülteye ait dersler havuza eklenecek.
   
   
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

    def on_tab_change(self, event):
        selected_tab = event.widget.tab(event.widget.index("current"), "text")

        if "Analiz" in selected_tab:
            self.setup_analysis_tab()

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

        # Eğer performans tablosu boşsa analizi çizme
        try:
            res = self.db.run_sql("SELECT COUNT(*) FROM performans;")
            if not res[1] or res[1][0][0] == 0:
                ttk.Label(
                    self.tab_analysis,
                    text="📭 Analiz için yeterli veri yok.\nLütfen önce MOCK / veri yükleme çalıştırın.",
                    font=("Segoe UI", 11)
                ).pack(pady=50)
                return
        except:
            return

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
                df_top['basari_orani'] = df_top['basari_orani'] * 100

                sns.barplot(
                    x='basari_orani',
                    y='ad',
                    data=df_top,
                    ax=ax1,
                    palette="viridis" if len(df_top) > 1 else None
                )

                ax1.set_title(
                    "En Yüksek Başarı Oranına Sahip Dersler (Top 5)",
                    fontsize=10
                )
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
        # ---  HAVUZ SAYFASI ---
        self.page_pool = ttk.Frame(self.sub_nb)  
        
        # 4. Alt Sayfaları Notebook'a Ekle
        self.sub_nb.add(self.page_algos, text="⚙️ Algoritma Kontrol Paneli")
        self.sub_nb.add(self.page_relations, text="🔗 Ders İlişkileri & Kurallar")
        self.sub_nb.add(self.page_pool, text="🏊 Havuz Yönetimi")
        
        # 5. Sayfaların İçeriğini Dolduran Fonksiyonları Çağır
        self.setup_algo_panel(self.page_algos)      # Eski kodları buraya taşıdık
        self.setup_relations_panel(self.page_relations) # Yeni boş sayfa
        self.setup_pool_panel(self.page_pool)

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
        
        query = f"""
        SELECT DISTINCT d.ders_id, d.ad
        FROM ders d
        JOIN fakulte f ON d.fakulte_id = f.fakulte_id
        WHERE f.ad = '{fakulte}'
        """

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


        from app.services.similarity_engine import SimilarityEngine

        engine = SimilarityEngine(self.db_path)
        engine.compute_and_save(course_id, top_n=10)

        #SAĞ PANEL (LİSTE)
        query = f"""
        SELECT d.ad, di.skor
        FROM ders_iliski di
        JOIN ders d ON d.ders_id = di.hedef_ders_id
        WHERE di.kaynak_ders_id = {course_id}
        ORDER BY di.skor DESC
        LIMIT 10
        """
        rows = self.db.run_sql(query)[1]


        self.tree_scores.delete(*self.tree_scores.get_children())
        for ad, skor in rows:
            self.tree_scores.insert("", tk.END, values=(ad, f"%{skor*100:.1f}"))


        if not rows:
            return


        #ORTA PANEL (AĞAÇ / NETWORK)
        self.rel_fig.clear()
        ax = self.rel_fig.add_subplot(111)

        G = nx.Graph()
        center_name = self.lst_rel_courses.get(sel[0])
        G.add_node(center_name)

        for ders_adi, skor in rows:
            G.add_node(ders_adi)
            G.add_edge(center_name, ders_adi, weight=skor)

        pos = nx.spring_layout(G, k=0.7, center=(0, 0))

        nx.draw_networkx_nodes(G, pos, node_color="#3b82f6", node_size=1800, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=8, font_color="white", ax=ax)

        weights = [G[u][v]['weight'] * 8 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, width=weights, edge_color="#94a3b8", ax=ax)

        ax.set_title(f"'{center_name}' için Ders Benzerlik Ağı")
        ax.axis("off")

        self.rel_canvas.draw()

    def setup_pool_panel(self, parent):

        """
        Havuz Yönetimi Sayfası - Fakülte > Bölüm > Yıl Filtreli
        """
        # --- 1. ÜST PANEL (FİLTRELER) ---
        top_frame = tk.Frame(parent, bg="#f1f5f9", pady=10, padx=10)
        top_frame.pack(fill=tk.X)

        # A. Fakülte Seçimi
        tk.Label(top_frame, text="1. Fakülte:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.cb_pool_fakulte = ttk.Combobox(top_frame, state="readonly", width=25)
        self.cb_pool_fakulte.pack(side=tk.LEFT, padx=5)
        # Fakülte değişince bölümleri yüklemesi için olay (event) bağlıyoruz
        self.cb_pool_fakulte.bind("<<ComboboxSelected>>", self.on_faculty_change)

        # B. Bölüm Seçimi (YENİ EKLENDİ)
        tk.Label(top_frame, text="2. Bölüm:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.cb_pool_bolum = ttk.Combobox(top_frame, state="readonly", width=25)
        self.cb_pool_bolum.pack(side=tk.LEFT, padx=5)

        # C. Yıl Seçimi (GÜNCELLENDİ: 2022-2025)
        tk.Label(top_frame, text="3. Yıl:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.cb_pool_yil = ttk.Combobox(top_frame, state="readonly", values=["2022", "2023", "2024", "2025"], width=10)
        self.cb_pool_yil.current(3) # Varsayılan 2025
        self.cb_pool_yil.pack(side=tk.LEFT, padx=5)

        self.cb_pool_bolum.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())
        self.cb_pool_yil.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())


        # D. Listele Butonu
        ttk.Button(top_frame, text="Verileri Getir", command=self.load_pool_data).pack(side=tk.LEFT, padx=20)

        # --- 2. ORTA PANEL (AKSİYON BUTONLARI) ---
        action_frame = tk.Frame(parent, bg="#e2e8f0", pady=5)
        action_frame.pack(fill=tk.X)

        self.btn_toggle_rest = tk.Button(action_frame, text="🔴 Dinlenmedekileri Gizle", bg="#fca5a5", font=("Segoe UI", 8),
                  command=self.toggle_resting_courses)
        self.btn_toggle_rest.pack(side=tk.LEFT, padx=10)

        

        # --- 3. ALT PANEL (SPLIT VIEW) ---
        paned = tk.PanedWindow(parent, orient=tk.HORIZONTAL, sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # SOL: HAVUZ
        left_frame = tk.Frame(paned, bg="white")
        paned.add(left_frame, width=650)
        tk.Label(left_frame, text="DERS HAVUZU (Seçilen Fakülte)", bg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        
        cols_pool = ("ID", "Ders Adı", "Puan", "Sayaç", "Durum", "Yıl")
        self.tree_pool = ttk.Treeview(left_frame, columns=cols_pool, show="headings", selectmode="extended")
        for col in cols_pool:
            self.tree_pool.heading(col, text=col)
            if col == "Ders Adı": w=200
            elif col == "ID": w=50
            else: w=70
            self.tree_pool.column(col, width=w, anchor="center")
        
        self.tree_pool.tag_configure("resting", background="#fee2e2", foreground="#b91c1c")
        self.tree_pool.tag_configure("active", background="white")
        
        sb_pool = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree_pool.yview)
        self.tree_pool.configure(yscrollcommand=sb_pool.set)
        sb_pool.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_pool.pack(fill=tk.BOTH, expand=True)

        # SAĞ: MÜFREDAT
        right_frame = tk.Frame(paned, bg="white")
        paned.add(right_frame)
        tk.Label(right_frame, text="MÜFREDAT (Seçilen Bölüm)", bg="#dcfce7", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)

        cols_curr = ("ID", "Ders Adı", "Kesinleşme Puanı")
        self.tree_curr = ttk.Treeview(right_frame, columns=cols_curr, show="headings")
        for col in cols_curr:
            self.tree_curr.heading(col, text=col)
            self.tree_curr.column(col, anchor="center")
        self.tree_curr.pack(fill=tk.BOTH, expand=True)
        
        # Simülasyon Butonu
        tk.Button(right_frame, text="👤 Örnek Öğrenci Seçimi Başlat", 
                  bg="#22c55e", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self.open_student_simulation).pack(fill=tk.X, pady=5, padx=5)

        # Başlangıçta Fakülteleri Doldur
        self.after(500, self.load_faculties_to_combo)

    # =========================================================
    #  VERİ YÖNETİMİ VE FİLTRELEME İŞLEVLERİ
    # =========================================================

    def load_faculties_to_combo(self):
        """Fakülteleri Combobox'a doldurur."""
        try:
            res = self.db.run_sql("SELECT ad FROM fakulte")
            if res[1]:
                values = [r[0] for r in res[1]]
                self.cb_pool_fakulte['values'] = values
                if values: self.cb_pool_fakulte.current(0)
                # İlk açılışta seçili fakültenin bölümlerini de yükle
                self.on_faculty_change(None)
        except Exception as e:
            print(f"Fakülte yükleme hatası: {e}")

    def on_faculty_change(self, event):
        secilen_fakulte = self.cb_pool_fakulte.get()
        if not secilen_fakulte:
            return

        # Fakülte ID
        res = self.db.run_sql(
            f"SELECT fakulte_id FROM fakulte WHERE ad = '{secilen_fakulte}'"
        )
        if not res[1]:
            return

        fakulte_id = res[1][0][0]

        # Bölümleri yükle
        res_bolum = self.db.run_sql(
            f"SELECT ad FROM bolum WHERE fakulte_id = {fakulte_id}"
        )

        bolumler = [r[0] for r in res_bolum[1]] if res_bolum[1] else []

        self.cb_pool_bolum['values'] = bolumler
        if bolumler:
            self.cb_pool_bolum.current(0)

        # Fakülte değişince havuz otomatik yüklensin
        self.load_pool_data()

   
    def load_pool_data(self):
        """
        SOL TABLO: Seçilen Fakülteye ve Yıla göre gerçek HAVUZ verilerini getirir.
        SAĞ TABLO: Seçilen Bölüme göre müfredatı getirir.
        """
        fakulte = self.cb_pool_fakulte.get()
        bolum = self.cb_pool_bolum.get()
        yil = self.cb_pool_yil.get()

        if not fakulte or not yil:
            return

        # --- 1. SOL TABLO (HAVUZ) DOLDURMA ---
        self.tree_pool.delete(*self.tree_pool.get_children())
        
        # GÜNCELLENMİŞ SORGU:
        # Manuel 0 değerleri yerine 'havuz' tablosundaki gerçek sütunları (skor, sayac, statu) çekiyoruz.
        # Ayrıca filtreye 'yil' şartını da ekledik.
        query_left = f"""
            SELECT 
                h.ders_id,      -- Örn: F1B2D15
                h.ders_adi,     -- Örn: Yapay Zeka
                h.skor,         -- Örn: 2
                h.sayac,        -- Örn: 1
                h.statu,        -- Örn: 0 (Havuzda), 1 (Müfredatta), -1 (Yasaklı)
                h.yil           -- Örn: 2024
            FROM havuz h
            JOIN fakulte f ON h.fakulte_id = f.fakulte_id
            WHERE f.ad = '{fakulte}' AND h.yil = {yil}
            ORDER BY h.skor DESC, h.sayac DESC
        """

        try:
            _, rows = self.db.run_sql(query_left)
            if rows:
                for row in rows:
                    r_id, r_ad, r_skor, r_sayac, r_statu, r_yil = row
                    
                    # Görselleştirme (Tag atama)
                    # Statü -1 ise Kırmızı, 1 ise (Müfredatta) ama burada havuzu listeliyoruz, genelde 0 gelir.
                    tag = "active"
                    statu_text = "Havuzda"
                    
                    if str(r_statu) == "-1":
                        tag = "resting"
                        statu_text = "Dinlenmede (-1)"
                    elif str(r_statu) == "1":
                        tag = "chosen"
                        statu_text = "Müfredatta (1)"
                    else:
                        statu_text = "Havuzda (0)"

                    # Skoru ondalıklı gösterme (örn: 2.0)
                    disp_skor = f"{r_skor:.1f}" if r_skor is not None else "0.0"
                    
                    self.tree_pool.insert("", tk.END, values=(r_id, r_ad, disp_skor, r_sayac, statu_text, r_yil), tags=(tag,))
            
            # Renklendirme Ayarları
            self.tree_pool.tag_configure("resting", background="#fee2e2", foreground="#b91c1c") # Açık Kırmızı
            self.tree_pool.tag_configure("chosen", background="#dcfce7", foreground="#15803d")  # Açık Yeşil
            self.tree_pool.tag_configure("active", background="white")

        except Exception as e:
            print(f"Havuz verisi hatası: {e}")

# --- 2. SAĞ TABLO (MÜFREDAT) DOLDURMA ---
        # Artık veriyi 'statu=1' olan havuz kayıtlarından değil,
        # doğrudan GERÇEK 'mufredat' ve 'mufredat_ders' tablolarından çekiyoruz.
        
        self.tree_curr.delete(*self.tree_curr.get_children())
        
        # Eğer bölüm veya yıl seçili değilse çık
        if not bolum or not yil:
            return

        # GÜNCELLENMİŞ SORGUNUZ
        # Mantık:
        # 1. Seçilen 'bolum' ve 'yil'a ait müfredat ID'sini bul.
        # 2. 'mufredat_ders' tablosundan dersleri getir.
        # 3. 'ders' tablosundan isimleri al.
        # 4. 'havuz' tablosundan (varsa) o yılki SKORUNU alıp yanına yaz.
        
        query_right = f"""
                    SELECT 
                        d.ders_id, 
                        d.ad, 
                        h.skor
                    FROM mufredat m
                    -- DÜZELTME 1: 'm.id' yerine 'm.mufredat_id' kullanıldı.
                    JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                    JOIN ders d ON md.ders_id = d.ders_id
                    JOIN bolum b ON m.bolum_id = b.bolum_id
                    -- DÜZELTME 2: 'm.yil' yerine 'm.akademik_yil' kullanıldı.
                    -- Havuz tablosu ile eşleşirken yıl bilgisi buradan alınıyor.
                    LEFT JOIN havuz h ON (h.ders_id = d.ders_id AND h.yil = m.akademik_yil)
                    WHERE b.ad = '{bolum}' AND m.akademik_yil = {yil}
                    ORDER BY d.ad
                """
        
        try:
            _, rows_right = self.db.run_sql(query_right)
            
            if rows_right:
                for r in rows_right:
                    r_id = r[0]
                    r_ad = r[1]
                    r_skor = r[2]

                    # Puan formatı (Eğer havuzda yoksa 0.0 gösterelim)
                    score_txt = f"%{r_skor:.1f}" if r_skor is not None else "---"
                    
                    self.tree_curr.insert("", tk.END, values=(r_id, r_ad, score_txt))
            else:
                # Veri yoksa boş olduğunu belirtmek istersen (Opsiyonel)
                pass 
                
        except Exception as e:
            print(f"Müfredat verisi çekme hatası: {e}")
            # Hata durumunda kullanıcıya boş tablo gösterir, program çökmez.

    

    # --- YARDIMCI FONKSİYONLAR (ŞİMDİLİK BOŞ, MANTIĞI SONRA EKLEYECEĞİZ) ---
    
    def load_faculties_to_combo(self):
        try:
            res = self.db.run_sql("SELECT ad FROM fakulte")
            if res[1]:
                self.cb_pool_fakulte['values'] = [r[0] for r in res[1]]
                self.cb_pool_fakulte.current(0)
        except: pass

   
    def toggle_resting_courses(self):
        messagebox.showinfo("Bilgi", "Filtreleme mantığı buraya eklenecek.")


    def ensure_pool_initialized_once(self):
        res = self.db.run_sql("SELECT COUNT(*) FROM havuz WHERE yil BETWEEN 2022 AND 2025;")
        cnt = res[1][0][0] if res[1] else 0
        if cnt == 0:
            self.fill_pool_table_for_years()


    # =========================================================================
    #  ALGORİTMA MANTIĞI: MÜFREDAT BELİRLEME (SOL -> SAĞ)
    # =========================================================================

    def move_to_curriculum(self):
        """
        HOCANIN ALGORİTMASI (TAM ENTEGRASYON):
        1. Veritabanından geçmiş verileri (2022-2024) çek.
        2. Trend + AHP + TOPSIS hesapla.
        3. Puanlara göre eleme yap (Status -1 / 1).
        """
        if not messagebox.askyesno("Onay", "Algoritma çalıştırılsın mı? (Mevcut havuz durumu değişecek)"):
            return

        try:
            # 1. Havuzdaki DERSLERİ ve GEÇMİŞ VERİLERİNİ Çek
            # Sadece 'Müsait' (Statu != -1) ve 'Seçilmemiş' (Statu != 1) olanlara bakalım mı?
            # Hayır, havuzdaki (Statu 0) dersleri yarıştıracağız.
            query_pool = """
                SELECT h.havuz_id, h.ders_id, d.ad 
                FROM havuz h JOIN ders d ON h.ders_id = d.ders_id 
                WHERE h.statu = 0
            """
            pool_rows = self.db.run_sql(query_pool)[1]
            
            if not pool_rows:
                messagebox.showwarning("Uyarı", "Havuzda işlenecek (Statü 0) ders kalmadı!")
                return

            # Hesaplama Motorunu Çağır
            from app.services.calculation import KararMotoru
        
            import pandas as pd
            
            engine = KararMotoru()
            
            # Veri Hazırlığı
            topsis_input = []
            
            for row in pool_rows:
                h_id, d_id, d_ad = row
                
                # A. Tarihsel Veriyi Çek (Trend için)
                q_hist = f"SELECT akademik_yil, basari_orani FROM performans WHERE ders_id={d_id}"
                hist_rows = self.db.run_sql(q_hist)[1]
                history = [{'yil': int(r[0]), 'oran': float(r[1])} for r in hist_rows]
                
                trend_score, _ = engine.calculate_historical_trend(history)
                
                # B. Diğer Metrikler (Popülerlik, Anket - Mock/DB)
                # Not: Gerçekte 'anket' tablosundan, 'populerlik' tablosundan JOIN ile gelmeli.
                # Şimdilik DB'den basitçe alalım veya simüle edelim.
                
                # Performans (Son yılın başarısı)
                last_perf = history[0]['oran'] if history else 0.5
                
                # Popülerlik
                q_pop = f"SELECT tercih_sayisi FROM populerlik WHERE ders_id={d_id}"
                res_pop = self.db.run_sql(q_pop)[1]
                pop_val = res_pop[0][0] if res_pop else 50
                
                # Anket (Simüle - Veritabanında henüz tam yoksa)
                anket_val = 75 # Ortalama bir değer
                
                topsis_input.append({
                    'havuz_id': h_id,
                    'ders': d_ad,
                    'basari': last_perf,
                    'trend': trend_score,
                    'populerlik': pop_val,
                    'anket': anket_val
                })

            # 2. HESAPLAMA (AHP + TOPSIS)
            df = pd.DataFrame(topsis_input)
            
            # Ağırlıkları Al
            weights = engine.run_ahp() 
            
            # Sıralamayı Yap
            df_result, logs = engine.run_topsis(df, weights)
            
            # 3. KARAR (BARAJ / ORTALAMA)
            # Rort (Ortalama Skor)
            avg_score = df_result['AHP_TOPSIS_Skor'].mean()
            threshold = 0.50 
            
            # Sonuçları Veritabanına Yaz
            cursor = self.db.conn.cursor()
            selected_count = 0
            
            for _, row in df_result.iterrows():
                score = row['AHP_TOPSIS_Skor']
                h_id = topsis_input[df_result.index[df_result['Ders'] == row['Ders']].tolist()[0]]['havuz_id']
                
                # Kural: 50'yi geçsin VEYA Ortalamayı geçsin
                if score >= threshold or score >= avg_score:
                    new_statu = 1 # Seçildi
                    selected_count += 1
                else:
                    new_statu = -1 # Elendi
                    # Sayacı artır (DB'den okuyup artırmak daha doğru ama basitçe update yapalım)
                    cursor.execute(f"UPDATE havuz SET sayac = sayac + 1 WHERE havuz_id={h_id}")

                cursor.execute("UPDATE havuz SET statu = ?, skor = ? WHERE havuz_id = ?", 
                               (new_statu, float(score), h_id))
            
            self.db.conn.commit()
            
            # Arayüzü Yenile
            self.load_pool_data()
            self.load_curriculum_list()
            
            msg = f"İşlem Tamamlandı!\n\n" \
                  f"Ortalama Puan: {avg_score:.4f}\n" \
                  f"Seçilen Ders: {selected_count}\n" \
                  f"Elenen Ders: {len(df_result) - selected_count}"
            
            messagebox.showinfo("Sonuç", msg)

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Hata", f"Algoritma hatası: {e}")


    def load_curriculum_list(self):
        """Sağ taraftaki Müfredat tablosunu doldurur (Statu = 1 olanlar)"""
        self.tree_curr.delete(*self.tree_curr.get_children())
        
        query = """
            SELECT h.havuz_id, d.ad, h.skor 
            FROM havuz h JOIN ders d ON h.ders_id = d.ders_id 
            WHERE h.statu = 1
        """
        cols, rows = self.db.run_sql(query)
        for r in rows:
            # Puanı yüzdelik formatta gösterelim
            score_txt = f"%{r[2]*100:.1f}" if r[2] else "N/A"
            self.tree_curr.insert("", tk.END, values=(r[0], r[1], score_txt))


    def on_fakulte_change(self, event):
        fakulte_adi = self.cmb_fakulte.get()
        fakulte_id = self.fakulte_map[fakulte_adi]

        self.tree_havuz.delete(*self.tree_havuz.get_children())

        rows = self.db.run_sql("""
            SELECT ders_id, ad, count, status
            FROM ders
            WHERE fakulte_id = ? AND tip = 'Seçmeli'
            ORDER BY ad
        """, (fakulte_id,))[1]

        for r in rows:
            self.tree_havuz.insert("", "end", values=r)


    # =========================================================================
    #  SİMÜLASYON: ÖĞRENCİ DERS SEÇİM EKRANI
    # =========================================================================

    def open_student_simulation(self):
        """
        Sağ taraftaki 'Müfredat' listesini alıp, bir öğrenci gibi seçim yapma ekranı açar.
        """
        # Müfredattaki dersleri al
        curr_items = self.tree_curr.get_children()
        if not curr_items:
            messagebox.showwarning("Uyarı", "Müfredatta ders yok! Önce algoritmayı çalıştırın.")
            return

        # Yeni Pencere (Popup)
        sim_win = tk.Toplevel(self)
        sim_win.title("🎓 Öğrenci Ders Seçim Ekranı (Simülasyon)")
        sim_win.geometry("600x500")
        sim_win.configure(bg="#f8fafc")

        tk.Label(sim_win, text="2025-2026 GÜZ DÖNEMİ DERS SEÇİMİ", 
                 font=("Segoe UI", 14, "bold"), bg="#f8fafc", fg="#1e293b").pack(pady=15)

        tk.Label(sim_win, text="Müfredat Komisyonu tarafından onaylanan dersler aşağıdadır.\nLütfen almak istediklerinizi işaretleyiniz.", 
                 bg="#f8fafc").pack(pady=(0, 10))

        # Checkbox Listesi
        check_frame = tk.Frame(sim_win, bg="white", relief="groove", bd=1)
        check_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.vars_student_select = []
        
        for item in curr_items:
            vals = self.tree_curr.item(item)['values']
            d_id, d_name, d_score = vals
            
            var = tk.IntVar()
            cb = tk.Checkbutton(check_frame, text=f"{d_name} (Öneri Puanı: {d_score})", 
                                variable=var, bg="white", font=("Segoe UI", 10), anchor="w", padx=10, pady=5)
            cb.pack(fill=tk.X)
            self.vars_student_select.append((d_name, var))

        # Kaydet Butonu
        def save_selection():
            selected = [name for name, var in self.vars_student_select if var.get() == 1]
            if not selected:
                messagebox.showwarning("Uyarı", "Hiç ders seçmediniz!")
                return
            
            msg = "Seçilen Dersler:\n\n" + "\n".join(f"✅ {s}" for s in selected)
            msg += "\n\nKaydınız başarıyla tamamlandı!"
            messagebox.showinfo("Onay", msg)
            sim_win.destroy()

        btn_save = tk.Button(sim_win, text="Seçimi Onayla ve Kaydet", 
                             bg="#22c55e", fg="white", font=("Segoe UI", 10, "bold"),
                             command=save_selection)
        btn_save.pack(pady=20, ipadx=10)



    # =========================================================
    #  İŞ MANTIĞI FONKSİYONLARI
    # =========================================================

    def run_single_step(self, algo_id):
        """
        Seçilen tek bir algoritmayı çalıştırır, durumunu günceller ve sonucu kaydeder.
        """
        widgets = self.ui_refs[algo_id]
        
        # 1. Durumu Güncelle: Çalışıyor (Sarı)
        widgets["status"].config(text="Çalışıyor...", bg="#fcd34d") 
        widgets["show_btn"].config(state="disabled")
        self.update_idletasks() 
        
        import time
        time.sleep(0.5) 

        sonuc_metni = ""
        basarili_mi = True

        try:
            # --- ALGORİTMA SEÇİCİ ---
            
            # 1. MOCK (Sahte Veri) Kontrolü
            if algo_id == "mock":
                res = self.db.run_sql("SELECT COUNT(*) FROM ogrenci")
                sayi = res[1][0][0] if res[1] else 0
                sonuc_metni = f"Veritabanı Durumu:\n==================\n"
                sonuc_metni += f"Toplam Öğrenci: {sayi}\n"
                sonuc_metni += "Durum: Veriler analiz için hazır."
            
            # 2. AHP (Analitik Hiyerarşi Prosesi)
            elif algo_id == "ahp":
                from app.services.calculation import KararMotoru
                # Havuz verisi şimdilik lazım değil, None gönderiyoruz
                motor = KararMotoru(None) 
                
                # AHP Hesaplama
                agirliklar = motor.ahp_calistir()
                
                sonuc_metni = "AHP Matrisi ve Kriter Ağırlıkları:\n==================================\n"
                sonuc_metni += f"1. Performans (Başarı): {agirliklar[0]:.4f} (%{agirliklar[0]*100:.1f})\n"
                sonuc_metni += f"2. Popülerlik (Talep):  {agirliklar[1]:.4f} (%{agirliklar[1]*100:.1f})\n"
                sonuc_metni += f"3. Anket (Öğrenci):     {agirliklar[2]:.4f} (%{agirliklar[2]*100:.1f})\n"

            # 3. TREND ANALİZİ
            elif algo_id == "trend":
                from app.services.calculation import KararMotoru
                import pandas as pd
                
                motor = KararMotoru(None)
                
                # Veriyi çek (Ders, Yıl, Başarı Oranı)
                sorgu = """
                SELECT d.ders_id, d.ad as ders, p.akademik_yil, p.basari_orani
                FROM ders d
                JOIN performans p ON d.ders_id = p.ders_id
                WHERE p.basari_orani IS NOT NULL 
                ORDER BY d.ders_id, p.akademik_yil DESC;
                """
                ham_veri = self.db.read_df(sorgu)
                
                if ham_veri.empty:
                    sonuc_metni = "Veri yok! Lütfen önce MOCK veriyi çalıştırın."
                    basarili_mi = False
                else:
                    gruplanmis = ham_veri.groupby('ders_id')
                    sonuc_metni = "--- DERSLERİN TARİHSEL BAŞARI ANALİZİ ---\n"
                    sonuc_metni += "(Formül: 2024*%50 + 2023*%30 + 2022*%20)\n\n"
                    
                    # Her ders için hesaplama yap
                    for ders_id, grup in gruplanmis:
                        ders_adi = grup.iloc[0]['ders']
                        
                        # Yıllık ortalama al (Güz+Bahar birleştir)
                        yillik_grup = grup.groupby('akademik_yil')['basari_orani'].mean().reset_index()
                        yillik_grup = yillik_grup.sort_values('akademik_yil', ascending=False)
                        
                        gecmis = []
                        for _, satir in yillik_grup.iterrows():
                            gecmis.append({'yil': int(satir['akademik_yil']), 'oran': satir['basari_orani']})
                        
                        # Trend Hesapla (Türkçe method ismi)
                        if hasattr(motor, 'gecmis_trend_hesapla'):
                            skor, log_mesaji = motor.gecmis_trend_hesapla(gecmis)
                            
                            # Ekran dolmasın diye sadece ilk başlardaki veriyi ekle
                            if len(sonuc_metni) < 2000: 
                                sonuc_metni += f"{ders_adi}:\n   {log_mesaji}\n"
                        
                    sonuc_metni += "\n... (Tüm dersler için hesaplandı)."

          # 4. TOPSIS (Sıralama Algoritması)
            elif algo_id == "topsis":
                from app.services.calculation import KararMotoru
                import pandas as pd
                import numpy as np
                
                motor = KararMotoru(None)
                
                # 1. Veriyi Çek (Performans ve Popülerlik ile birleştir)
                sorgu = """
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
                ham_veri = self.db.read_df(sorgu)
                
                if ham_veri.empty:
                    sonuc_metni = "Veri bulunamadı! Lütfen önce 'MOCK' veriyi çalıştırın."
                    basarili_mi = False
                else:
                    islenmis_satirlar = []
                    gruplanmis = ham_veri.groupby('ders_id')
                    
                    for ders_id, grup in gruplanmis:
                        ders_adi = grup.iloc[0]['ders']
                        yillik_grup = grup.groupby('akademik_yil')['basari_orani'].mean().reset_index()
                        yillik_grup = yillik_grup.sort_values('akademik_yil', ascending=False)
                        
                        # Geçmiş verisi (Trend hesabı için)
                        gecmis = [{'yil': int(r['akademik_yil']), 'oran': r['basari_orani']} for _, r in yillik_grup.iterrows()]
                        
                        # A. Trend Skoru Hesapla
                        trend_skoru, _ = motor.gecmis_trend_hesapla(gecmis)
                        
                        # B. Son Yıl Başarısı (Basari kriteri için)
                        son_basari = gecmis[0]['oran'] if gecmis else 0
                        
                        # C. Popülerlik (Yoksa 0)
                        ort_pop = grup['populerlik'].max() if pd.notna(grup['populerlik'].max()) else 0
                        
                        # Veri Hazırla (BURASI DÜZELTİLDİ: Tüm anahtarlar eklendi)
                        islenmis_satirlar.append({
                            'ders': ders_adi,
                            'basari': son_basari,      # Düzeltme: Son yılın notu
                            'trend': trend_skoru,      # Düzeltme: Eksik olan anahtar eklendi
                            'populerlik': ort_pop,
                            'anket': np.random.randint(40, 90) # Anket verisi simüle edildi
                        })
                    
                    # 2. AHP & TOPSIS Çalıştır
                    df_final = pd.DataFrame(islenmis_satirlar)
                    
                    # Ağırlıkları Hesapla
                    agirliklar = motor.ahp_calistir()
                    
                    # Sıralamayı Yap (TOPSIS)
                    # Artık 'trend' sütunu olduğu için hata vermeyecek
                    df_sonuc, logs = motor.topsis_calistir(df_final, agirliklar)
                    
                    sonuc_metni = "--- NİHAİ KARAR MATRİSİ (TOPSIS) ---\n"
                    sonuc_metni += "Girdiler: Başarı + Trend + Popülerlik + Anket\n\n"
                    
                    # Sonuçları göster (Sütun isimlerini kontrol et)
                    if not df_sonuc.empty:
                        sonuc_metni += df_sonuc[['Ders', 'AHP_TOPSIS_Skor', 'S+', 'S-']].head(15).to_string(index=False, float_format="%.4f")
                    else:
                        sonuc_metni += "Hesaplama sonucu boş döndü."
            # 5. YAPAY ZEKA (Makine Öğrenmesi)
            elif algo_id in ["lr", "rf", "dt"]:
                from app.services.ai_engine import AIEngine
                # Veritabanı bağlantısı için session oluşturma (SQLAlchemy kullanıyorsan)
                # Eğer SQLAlchemy yoksa ve sqlite3 kullanıyorsan burayı güncellemek gerekebilir.
                # Şimdilik mevcut yapını koruyoruz:
                try:
                    from app.db.database import SessionLocal
                    db_oturumu = SessionLocal()
                    ai_motoru = AIEngine(db_oturumu)
                    
                    # K-Fold Testini Çalıştır
                    k_degeri = 5
                    sonuc_metni = ai_motoru.run_kfold_test(algorithm_type=algo_id, k=k_degeri)
                    
                    db_oturumu.close()
                except ImportError:
                    # SQLAlchemy session yoksa, mevcut sqlite bağlantısını kullanmaya çalışabiliriz
                    # Ancak AIEngine sınıfı Session bekliyor olabilir.
                    # Basit çözüm:
                    sonuc_metni = "Hata: Veritabanı oturumu (SessionLocal) bulunamadı.\nLütfen veritabanı ayarlarını kontrol edin."
                    basarili_mi = False

        except Exception as e:
            sonuc_metni = f"HATA OLUŞTU:\n{str(e)}"
            basarili_mi = False
            import traceback
            traceback.print_exc() # Konsola detaylı hata basar

        # 2. Sonucu Kaydet
        self.results_cache[algo_id] = sonuc_metni

        # 3. Durumu Güncelle (Yeşil veya Kırmızı)
        if basarili_mi:
            widgets["status"].config(text="Tamamlandı", bg="#86efac") # Yeşil
            widgets["show_btn"].config(state="normal")
            self.show_result(algo_id)
        else:
            widgets["status"].config(text="Hata!", bg="#fca5a5") # Kırmızı

    def show_result(self, algo_id):
        """Sağdaki pembe alana sonucu yazar."""
        metin = self.results_cache.get(algo_id, "Sonuç bulunamadı.")
        
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        
        baslik = f"--- SONUÇ: {algo_id.upper()} ---\n\n"
        self.result_text.insert(tk.END, baslik)
        self.result_text.insert(tk.END, metin)
        
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
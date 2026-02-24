# app/ui/tabs/analysis_tab.py
import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# seaborn kullanmak istersen açık kalsın:
import seaborn as sns


class AnalysisTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app          # AdilSecmeliApp referansı
        self.db = app.db        # Database (sqlite_db.Database)
        self.canvas = None

        # İlk açılışta boş placeholder
        self._placeholder = ttk.Label(
            self,
            text="📊 Analiz sekmesi hazır.\nTab'a girince grafikler yüklenecek.",
            font=("Segoe UI", 11),
            justify="center"
        )
        self._placeholder.pack(expand=True, pady=40)

    # ----------------------------
    # Public API
    # ----------------------------
    def refresh(self):
        """Sekmeyi (yeniden) çiz."""
        # önce temizle
        for w in self.winfo_children():
            w.destroy()

        # veri var mı?
        if not self._has_table("performans"):
            ttk.Label(
                self,
                text="📭 'performans' tablosu yok.\nAnaliz için tablo/Mock veri gerekiyor.",
                font=("Segoe UI", 11),
                justify="center"
            ).pack(expand=True, pady=50)
            return

        try:
            res = self.db.run_sql("SELECT COUNT(*) FROM performans;")
            count_perf = (res[1][0][0] if res and res[1] else 0)
            if count_perf == 0:
                ttk.Label(
                    self,
                    text="📭 Analiz için yeterli veri yok.\nLütfen önce MOCK / veri yükleme çalıştırın.",
                    font=("Segoe UI", 11),
                    justify="center"
                ).pack(expand=True, pady=50)
                return
        except Exception:
            ttk.Label(
                self,
                text="⚠️ Analiz verisi okunamadı.\nVeritabanı bağlantısını kontrol et.",
                font=("Segoe UI", 11),
                justify="center"
            ).pack(expand=True, pady=50)
            return

        # --- KPI KARTLARI ---
        kpi_frame = ttk.Frame(self)
        kpi_frame.pack(fill=tk.X, pady=10, padx=10)

        stats = self._fetch_dashboard_stats()

        self._create_card(kpi_frame, "Toplam Öğrenci", stats["total_student"], "#3b82f6")
        self._create_card(kpi_frame, "Toplam Ders", stats["total_course"], "#10b981")
        self._create_card(kpi_frame, "Genel Başarı", f"%{stats['avg_success']}", "#f59e0b")
        self._create_card(kpi_frame, "Anket Durumu", stats["active_survey"], "#8b5cf6")

        # --- GRAFİKLER ---
        charts_frame = ttk.Frame(self)
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        fig = Figure(figsize=(10, 5), dpi=100)

        ax1 = fig.add_subplot(121)
        self._plot_top_success(ax1)

        ax2 = fig.add_subplot(122)
        self._plot_top_popularity(ax2)

        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=charts_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ----------------------------
    # Internals
    # ----------------------------
    def _has_table(self, table_name: str) -> bool:
        try:
            tables = self.db.tables()
            return table_name in tables
        except Exception:
            return False

    def _create_card(self, parent, title, value, color_code):
        card = tk.Frame(parent, bg=color_code, padx=10, pady=10)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(card, text=title, bg=color_code, fg="white", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(card, text=str(value), bg=color_code, fg="white", font=("Segoe UI", 18, "bold")).pack(anchor="w")

    def _fetch_dashboard_stats(self):
        stats = {
            "total_student": 0,
            "total_course": 0,
            "avg_success": 0.0,
            "active_survey": "Yok"
        }

        try:
            # 1) Toplam öğrenci
            if self._has_table("ogrenci"):
                res = self.db.run_sql("SELECT COUNT(*) FROM ogrenci;")
                if res[1]:
                    stats["total_student"] = res[1][0][0]

            # 2) Toplam ders
            if self._has_table("ders"):
                res = self.db.run_sql("SELECT COUNT(*) FROM ders;")
                if res[1]:
                    stats["total_course"] = res[1][0][0]

            # 3) Genel başarı (kayit tablosu varsa)
            if self._has_table("kayit"):
                df_grades = self.db.read_df(
                    "SELECT durum FROM kayit WHERE durum IN ('Geçti', 'Kaldı')"
                )
                if not df_grades.empty:
                    pass_count = (df_grades['durum'] == 'Geçti').sum()
                    total = len(df_grades)
                    if total > 0:
                        stats["avg_success"] = round((pass_count / total) * 100, 1)

            # 4) Aktif anket var mı?
            if self._has_table("anket_form"):
                res = self.db.run_sql("SELECT ad FROM anket_form WHERE aktif_mi=1 LIMIT 1;")
                if res[1]:
                    stats["active_survey"] = "Aktif"

        except Exception as e:
            print(f"İstatistik hatası: {e}")

        return stats

    def _plot_top_success(self, ax):
        ax.set_title("En Yüksek Başarı Oranı (Top 5)", fontsize=10)

        if not (self._has_table("performans") and self._has_table("ders")):
            ax.text(0.5, 0.5, "Tablolar eksik", ha="center", va="center")
            ax.axis("off")
            return

        try:
            query_top = """
                SELECT d.ad, p.basari_orani 
                FROM performans p 
                JOIN ders d ON p.ders_id = d.ders_id 
                ORDER BY p.basari_orani DESC LIMIT 5;
            """
            df_top = self.db.read_df(query_top)

            if df_top.empty:
                ax.text(0.5, 0.5, "Veri Yok", ha="center", va="center")
                ax.axis("off")
                return

            df_top["basari_orani"] = df_top["basari_orani"] * 100

            sns.barplot(
                x="basari_orani",
                y="ad",
                hue="ad",
                data=df_top,
                ax=ax,
                palette="viridis" if len(df_top) > 1 else None,
                legend=False
            )

            ax.set_xlabel("Başarı (%)")
            ax.set_ylabel("")
            ax.grid(axis="x", linestyle="--", alpha=0.6)

        except Exception as e:
            ax.text(0.5, 0.5, f"Hata: {e}", ha="center", va="center")
            ax.axis("off")

    def _plot_top_popularity(self, ax):
        ax.set_title("En Popüler Dersler (Top 7)", fontsize=10)

        if not (self._has_table("populerlik") and self._has_table("ders")):
            ax.text(0.5, 0.5, "Tablolar eksik", ha="center", va="center")
            ax.axis("off")
            return

        try:
            query_pop = """
                SELECT d.ad, p.talep_sayisi 
                FROM populerlik p 
                JOIN ders d ON p.ders_id = d.ders_id 
                ORDER BY p.talep_sayisi DESC LIMIT 7;
            """
            df_pop = self.db.read_df(query_pop)

            if df_pop.empty:
                ax.text(0.5, 0.5, "Veri Yok", ha="center", va="center")
                ax.axis("off")
                return

            ax.pie(
                df_pop["talep_sayisi"],
                labels=df_pop["ad"],
                autopct="%1.1f%%",
                startangle=90,
                colors=sns.color_palette("pastel")
            )

        except Exception as e:
            ax.text(0.5, 0.5, f"Hata: {e}", ha="center", va="center")
            ax.axis("off")

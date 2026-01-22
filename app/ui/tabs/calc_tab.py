# app/ui/tabs/calc_tab.py
import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd

from app.ui.tabs.pool_tab import PoolTab

from app.ui.tabs.relations_tab import RelationsTab




class CalcTab(ttk.Frame):
    """
    🧮 Hesaplama & Test sekmesi:
    - Algoritma kontrol paneli (mock/trend/ahp/topsis/lr/rf/dt)
    - Ders ilişkileri (NLP benzerlik grafiği)
    - Havuz yönetimi (Fakülte/Bölüm/Yıl filtreli)
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.db_path = getattr(app, "db_path", None)

        # state/cache
        self.ui_refs = {}
        self.results_cache = {}


        # ---- Nested Notebook ----
        self.sub_nb = ttk.Notebook(self)
        self.sub_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 1) Algo tab
        self.page_algos = ttk.Frame(self.sub_nb)
        self.sub_nb.add(self.page_algos, text="⚙️ Algoritma Kontrol Paneli")
        self.setup_algo_panel(self.page_algos)

        # 2) Relations tab (ayrı sınıf)
        self.page_relations = RelationsTab(self.sub_nb, app=self.app)
        self.sub_nb.add(self.page_relations, text="🔗 Ders İlişkileri & Kurallar")

        # 3) Pool tab (ayrı sınıf)
        self.page_pool = PoolTab(self.sub_nb, app=self.app)
        self.sub_nb.add(self.page_pool, text="🏊 Havuz Yönetimi")


    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self):
        # DB path güncel kalsın
        self.db_path = getattr(self.app, "db_path", self.db_path)

        # Relations yenile (fakülteleri kendi içinde dolduruyor)
        try:
            self.page_relations.refresh()
        except Exception:
            pass

        # PoolTab yenile
        try:
            self.page_pool.db_path = self.db_path
            self.page_pool.refresh()
        except Exception:
            pass



    # =========================================================
    #  1) ALGO PANEL
    # =========================================================
    def setup_algo_panel(self, parent):
        main_container = tk.Frame(parent, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # SOL
        left_frame = tk.Frame(main_container, bg="#e2e8f0", width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame,
            text="Algoritma Kontrol Paneli",
            bg="#1e293b",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            pady=8
        ).pack(fill=tk.X)

        grid_frame = tk.Frame(left_frame, bg="#e2e8f0")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # SAĞ
        right_frame = tk.Frame(main_container, bg="#fce7f3")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(
            right_frame,
            text="SONUÇ EKRANI",
            bg="#be185d",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            pady=8
        ).pack(fill=tk.X)

        self.result_text = tk.Text(
            right_frame,
            bg="#fff1f2",
            fg="#000000",
            font=("Consolas", 10),
            state="disabled",
            padx=10,
            pady=10
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Algoritma listesi (app'ten al, yoksa default)
        algos = getattr(self.app, "algorithms", None)
        if not algos:
            algos = [
                {"id": "mock", "name": "Veri Üretimi (Mock)"},
                {"id": "trend", "name": "Tarihsel Trend Analizi"},
                {"id": "ahp", "name": "AHP (Ağırlıklar)"},
                {"id": "topsis", "name": "TOPSIS (Sıralama)"},
                {"id": "lr", "name": "Lineer Regresyon (Tahmin)"},
                {"id": "rf", "name": "Random Forest (Sınıflandırma)"},
                {"id": "dt", "name": "Decision Tree (Karar)"},
            ]

        self.ui_refs = {}
        self.results_cache = {}

        btn_run_all = tk.Button(
            grid_frame,
            text="🚀 TÜMÜNÜ ÇALIŞTIR",
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            command=self.run_all_algorithms
        )
        btn_run_all.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 20), ipady=5)

        for idx, algo in enumerate(algos, start=1):
            algo_id = algo["id"]

            btn_run = ttk.Button(
                grid_frame,
                text=f"Çalıştır: {algo_id.upper()}",
                command=lambda i=algo_id: self.run_single_step(i)
            )
            btn_run.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")

            lbl_status = tk.Label(grid_frame, text="Bekliyor...", bg="#cbd5e1", width=15, anchor="center")
            lbl_status.grid(row=idx, column=1, padx=5, pady=5)

            btn_show = ttk.Button(
                grid_frame,
                text="Sonuç Göster",
                state="disabled",
                command=lambda i=algo_id: self.show_result(i)
            )
            btn_show.grid(row=idx, column=2, padx=5, pady=5, sticky="ew")

            self.ui_refs[algo_id] = {"status": lbl_status, "show_btn": btn_show}

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(2, weight=1)

    def run_all_algorithms(self):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "Toplu işlem başlatılıyor...\nLütfen bekleyiniz.\n")
        self.result_text.config(state="disabled")

        algos = getattr(self.app, "algorithms", None) or [{"id": k} for k in self.ui_refs.keys()]
        for algo in algos:
            self.run_single_step(algo["id"])
            self.update_idletasks()

    def run_single_step(self, algo_id: str):
        if algo_id not in self.ui_refs:
            return

        widgets = self.ui_refs[algo_id]
        widgets["status"].config(text="Çalışıyor...", bg="#fcd34d")
        widgets["show_btn"].config(state="disabled")
        self.update_idletasks()

        sonuc_metni = ""
        basarili_mi = True

        try:
            # 1) MOCK kontrol
            if algo_id == "mock":
                res = self.db.run_sql("SELECT COUNT(*) FROM ogrenci")
                sayi = res[1][0][0] if res[1] else 0
                sonuc_metni = (
                    "Veritabanı Durumu:\n"
                    "==================\n"
                    f"Toplam Öğrenci: {sayi}\n"
                    "Durum: Veriler analiz için hazır."
                )

            # 2) AHP
            elif algo_id == "ahp":
                from app.services.calculation import KararMotoru
                motor = KararMotoru(None)
                agirliklar = motor.ahp_calistir()

                sonuc_metni = "AHP Matrisi ve Kriter Ağırlıkları:\n==================================\n"
                sonuc_metni += f"1. Performans (Başarı): {agirliklar[0]:.4f} (%{agirliklar[0]*100:.1f})\n"
                sonuc_metni += f"2. Popülerlik (Talep):  {agirliklar[1]:.4f} (%{agirliklar[1]*100:.1f})\n"
                sonuc_metni += f"3. Anket (Öğrenci):     {agirliklar[2]:.4f} (%{agirliklar[2]*100:.1f})\n"

            # 3) TREND
            elif algo_id == "trend":
                from app.services.calculation import KararMotoru
                motor = KararMotoru(None)

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
                    gruplanmis = ham_veri.groupby("ders_id")
                    sonuc_metni = (
                        "--- DERSLERİN TARİHSEL BAŞARI ANALİZİ ---\n"
                        "(Formül: 2024*%50 + 2023*%30 + 2022*%20)\n\n"
                    )

                    for _, grup in gruplanmis:
                        ders_adi = grup.iloc[0]["ders"]
                        yillik = grup.groupby("akademik_yil")["basari_orani"].mean().reset_index()
                        yillik = yillik.sort_values("akademik_yil", ascending=False)

                        gecmis = [{"yil": int(r["akademik_yil"]), "oran": float(r["basari_orani"])} for _, r in yillik.iterrows()]

                        if hasattr(motor, "gecmis_trend_hesapla"):
                            _, log_mesaji = motor.gecmis_trend_hesapla(gecmis)
                            if len(sonuc_metni) < 2500:
                                sonuc_metni += f"{ders_adi}:\n   {log_mesaji}\n"

                    sonuc_metni += "\n... (Tüm dersler için hesaplandı)."

            # 4) TOPSIS
            elif algo_id == "topsis":
                from app.services.calculation import KararMotoru
                import numpy as np

                motor = KararMotoru(None)

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
                    islenmis = []
                    for _, grup in ham_veri.groupby("ders_id"):
                        ders_adi = grup.iloc[0]["ders"]
                        yillik = grup.groupby("akademik_yil")["basari_orani"].mean().reset_index()
                        yillik = yillik.sort_values("akademik_yil", ascending=False)
                        gecmis = [{"yil": int(r["akademik_yil"]), "oran": float(r["basari_orani"])} for _, r in yillik.iterrows()]

                        trend_skoru, _ = motor.gecmis_trend_hesapla(gecmis) if hasattr(motor, "gecmis_trend_hesapla") else (0, "")
                        son_basari = gecmis[0]["oran"] if gecmis else 0.0

                        ort_pop = grup["populerlik"].max()
                        ort_pop = float(ort_pop) if pd.notna(ort_pop) else 0.0

                        islenmis.append({
                            "ders": ders_adi,
                            "basari": son_basari,
                            "trend": trend_skoru,
                            "populerlik": ort_pop,
                            "anket": float(np.random.randint(40, 90))
                        })

                    df_final = pd.DataFrame(islenmis)
                    agirliklar = motor.ahp_calistir()
                    df_sonuc, _ = motor.topsis_calistir(df_final, agirliklar)

                    sonuc_metni = "--- NİHAİ KARAR MATRİSİ (TOPSIS) ---\n"
                    sonuc_metni += "Girdiler: Başarı + Trend + Popülerlik + Anket\n\n"
                    if not df_sonuc.empty:
                        # Sütun isimleri projene göre değişebilir; burada en sık kullanılanı baz aldım.
                        cols = [c for c in ["Ders", "AHP_TOPSIS_Skor", "S+", "S-"] if c in df_sonuc.columns]
                        sonuc_metni += df_sonuc[cols].head(15).to_string(index=False, float_format="%.4f")
                    else:
                        sonuc_metni += "Hesaplama sonucu boş döndü."

            # 5) ML
            elif algo_id in ["lr", "rf", "dt"]:
                from app.services.ai_engine import AIEngine
                try:
                    from app.db.database import SessionLocal
                    db_oturumu = SessionLocal()
                    ai_motoru = AIEngine(db_oturumu)
                    sonuc_metni = ai_motoru.run_kfold_test(algorithm_type=algo_id, k=5)
                    db_oturumu.close()
                except Exception:
                    sonuc_metni = (
                        "Hata: Veritabanı oturumu (SessionLocal) bulunamadı veya AIEngine hata verdi.\n"
                        "Not: AIEngine SQLAlchemy Session bekliyorsa app/db/database.py ayarlı olmalı."
                    )
                    basarili_mi = False

            else:
                sonuc_metni = f"Bu algo_id desteklenmiyor: {algo_id}"
                basarili_mi = False

        except Exception as e:
            basarili_mi = False
            sonuc_metni = f"HATA OLUŞTU:\n{e}"

        self.results_cache[algo_id] = sonuc_metni

        if basarili_mi:
            widgets["status"].config(text="Tamamlandı", bg="#86efac")
            widgets["show_btn"].config(state="normal")
            self.show_result(algo_id)
        else:
            widgets["status"].config(text="Hata!", bg="#fca5a5")

    def show_result(self, algo_id: str):
        metin = self.results_cache.get(algo_id, "Sonuç bulunamadı.")

        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)

        baslik = f"--- SONUÇ: {algo_id.upper()} ---\n\n"
        self.result_text.insert(tk.END, baslik)
        self.result_text.insert(tk.END, metin)

        self.result_text.config(state="disabled")


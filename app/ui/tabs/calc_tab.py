# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs/calc_tab.py — Hesaplama & Test Ana Sekmesi
# =============================================================================
# Bu dosya dort alt sekme icerir:
#   1. Kriter Girdi Islemleri (CriteriaPage)
#   2. Algoritma Kontrol & Ders Lab (genel AHP/TOPSIS/LR/RF/DT + tek ders analizi)
#   3. Ders Iliskileri & Kurallar (NLP benzerlik grafi)
#   4. Havuz Yonetimi (PoolTab — fakulte/yil/donem bazli havuz gorunumu)
#
# "Sonraki Yil Mufredat Uret" butonu secili yil icin manuel algoritma calistirir.
# "Tam Ekran" butonu PanedWindow'dan ust paneli gizleyerek analiz labini buyutur.
# =============================================================================
import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd

from app.ui.tabs.pool_tab import PoolTab
from app.ui.tabs.relations_tab import RelationsTab
from app.ui.tabs.criteria_page import CriteriaPage
from app.ui.tabs.course_analysis_tab import CourseAnalysisTab



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
        self.cb_algo_year = None


        # ---- Nested Notebook ----
        self.sub_nb = ttk.Notebook(self)
        self.sub_nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 0) Kriter Sayfası
        self.page_criteria = ttk.Frame(self.sub_nb)
        self.sub_nb.add(self.page_criteria, text="📝 Kriter Girdi İşlemleri")
        self.criteria_view = CriteriaPage(self.page_criteria, self.db, app=self.app)

        # 1) Algoritma Kontrol + Ders Laboratuvari (Birlesik Kokpit)
        self.page_algos = ttk.Frame(self.sub_nb)
        self.sub_nb.add(self.page_algos, text="Algoritma Kontrol & Ders Lab")
        self.setup_algo_panel(self.page_algos)

        # 2) Relations tab
        self.page_relations = RelationsTab(self.sub_nb, app=self.app)
        self.sub_nb.add(self.page_relations, text="Ders Iliskileri & Kurallar")

        # 3) Pool tab
        self.page_pool = PoolTab(self.sub_nb, app=self.app)
        self.sub_nb.add(self.page_pool, text="Havuz Yonetimi")

        # Alt sekme degisince Ders Lab'i yenile (Combobox degerleri gosterilmeden set edilirse bos kalabilir)
        self.sub_nb.bind("<<NotebookTabChanged>>", self._on_sub_tab_changed)

    def _on_sub_tab_changed(self, event=None):
        """
        Alt sekme degistiginde sadece ilk acilista yukle; sonrasinda
        mevcut filtre durumlarini koru.
        """
        try:
            idx = self.sub_nb.index(self.sub_nb.select())
            if idx == 1 and not getattr(self, "_lab_initialized", False):
                self.page_lab.refresh()
                self._lab_initialized = True
            elif idx == 3 and not getattr(self, "_pool_initialized", False):
                self.page_pool.refresh()
                self._pool_initialized = True
        except Exception:
            pass

    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self, force_reload=False):
        """
        DB path guncelle. force_reload=True olmadikca mevcut filtre
        durumlarini korur; sadece combobox values'lari gunceller.
        """
        self.db_path = getattr(self.app, "db_path", self.db_path)

        try:
            self.page_relations.refresh()
        except Exception:
            pass

        try:
            self.page_pool.db_path = self.db_path
            if force_reload or not getattr(self, "_pool_initialized", False):
                self.page_pool.refresh()
                self._pool_initialized = True
        except Exception:
            pass

        try:
            if force_reload or not getattr(self, "_lab_initialized", False):
                self.page_lab.refresh()
                self._lab_initialized = True
        except Exception:
            pass

        try:
            if hasattr(self.criteria_view, "load_faculties"):
                self.criteria_view.load_faculties(preserve_selection=True)
        except Exception as e:
            print(f"[CalcTab] load_faculties hatasi: {e}")
        try:
            if hasattr(self.criteria_view, "load_courses"):
                restore_id = getattr(self.criteria_view, "selected_course_id", None)
                self.criteria_view.load_courses(restore_course_id=restore_id)
        except Exception as e:
            print(f"[CalcTab] load_courses hatasi: {e}")
        try:
            self._refresh_algo_year_options()
        except Exception:
            pass

    def _refresh_algo_year_options(self):
        if not self.cb_algo_year:
            return
        previous = self.cb_algo_year.get()
        years = []
        try:
            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT yil FROM (
                    SELECT yil as yil FROM havuz
                    UNION
                    SELECT akademik_yil as yil FROM mufredat
                )
                WHERE yil IS NOT NULL
                ORDER BY yil
                """
            )
            years = [str(r[0]) for r in (rows or []) if r and r[0] is not None]
        except Exception:
            years = []

        if years:
            self.cb_algo_year["values"] = years
            if previous in years:
                self.cb_algo_year.set(previous)
            else:
                self.cb_algo_year.set(years[-1])



    # =========================================================
    #  1) ALGO PANEL
    # =========================================================
    def setup_algo_panel(self, parent):
        """Algoritma kontrol panelini olusturur: ust barda sonraki yil uretim + tumunu calistir butonlari, sol tarafta her algoritma icin calistir/goster butonlari, sag tarafta log/sonuc alani, altta ders analiz laboratuvari."""
        # Dikey bolum: Ust = Genel Kontrol, Alt = Ders Laboratuvari
        paned = tk.PanedWindow(parent, orient=tk.VERTICAL, sashwidth=6, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # UST: Genel Algoritma Kontrolu
        top_container = tk.Frame(paned, bg="#f0f0f0")
        paned.add(top_container, minsize=200)

        # --- Next Year butonu: sabit ust bar ---
        next_year_bar = tk.Frame(top_container, bg="#0f172a", pady=6, padx=10)
        next_year_bar.pack(fill=tk.X, side=tk.TOP)

        self._btn_next_year = tk.Button(
            next_year_bar,
            text="Sonraki Yil Mufredat Uret",
            bg="#16a34a", fg="white", activebackground="#15803d", activeforeground="white",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            relief="flat", bd=0,
            padx=24, pady=6,
            command=lambda: self.run_single_step("next_year"),
        )
        self._btn_next_year.pack(side=tk.LEFT, padx=(0, 16))

        self._lbl_next_year_status = tk.Label(
            next_year_bar, text="", bg="#0f172a", fg="#86efac",
            font=("Segoe UI", 9),
        )
        self._lbl_next_year_status.pack(side=tk.LEFT, padx=4)

        tk.Label(
            next_year_bar,
            text="Yil:",
            bg="#0f172a",
            fg="#cbd5e1",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(16, 4))
        self.cb_algo_year = ttk.Combobox(next_year_bar, state="readonly", width=8)
        self.cb_algo_year.pack(side=tk.LEFT, padx=(0, 8))
        self._refresh_algo_year_options()

        btn_run_all_top = tk.Button(
            next_year_bar,
            text="Tumunu Calistir",
            bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            relief="flat", bd=0,
            padx=16, pady=4,
            command=self.run_all_algorithms,
        )
        btn_run_all_top.pack(side=tk.RIGHT)

        # --- Ana icerik: Sol (butonlar) + Sag (log) ---
        main_container = tk.Frame(top_container, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_container, bg="#e2e8f0", width=430)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame,
            text="Algoritma Kontrol",
            bg="#1e293b", fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=6,
        ).pack(fill=tk.X)

        grid_frame = tk.Frame(left_frame, bg="#e2e8f0")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        right_frame = tk.Frame(main_container, bg="#fce7f3")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(
            right_frame,
            text="Sonuc / Log",
            bg="#be185d", fg="white",
            font=("Segoe UI", 10, "bold"),
            pady=6,
        ).pack(fill=tk.X)

        self.result_text = tk.Text(
            right_frame,
            bg="#fff1f2", fg="#000000",
            font=("Consolas", 9),
            state="disabled",
            padx=8, pady=8,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # ALT: Ders Analiz Laboratuvari
        bottom_container = tk.Frame(paned, bg="white")
        paned.add(bottom_container, minsize=220)

        lab_header = tk.Frame(bottom_container, bg="#0f172a", pady=3, padx=8)
        lab_header.pack(fill=tk.X)
        tk.Label(lab_header, text="Ders Analiz Laboratuvari",
                 bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self._btn_fullscreen = tk.Button(
            lab_header, text="Tam Ekran",
            bg="#334155", fg="white", font=("Segoe UI", 8, "bold"),
            relief="flat", cursor="hand2", padx=10,
            command=self._toggle_fullscreen,
        )
        self._btn_fullscreen.pack(side=tk.RIGHT)

        self.page_lab = CourseAnalysisTab(bottom_container, app=self.app)
        self.page_lab.pack(fill=tk.BOTH, expand=True)

        self._paned = paned
        self._top_container = top_container
        self._bottom_container = bottom_container
        self._is_fullscreen = False

        # Algoritma listesi (next_year haric — o ayri buton olarak ust barda)
        algos = getattr(self.app, "algorithms", None)
        if not algos:
            algos = [
                {"id": "mock", "name": "Veri Uretimi (Mock)"},
                {"id": "trend", "name": "Tarihsel Trend Analizi"},
                {"id": "ahp", "name": "AHP (Agirliklar)"},
                {"id": "topsis", "name": "TOPSIS (Siralama)"},
                {"id": "lr", "name": "Lineer Regresyon (Tahmin)"},
                {"id": "rf", "name": "Random Forest (Siniflandirma)"},
                {"id": "dt", "name": "Decision Tree (Karar)"},
                {"id": "next_year", "name": "Sonraki Yil Mufredat Uretimi"},
            ]

        self.ui_refs = {}
        self.results_cache = {}

        row_idx = 0
        for algo in algos:
            algo_id = algo["id"]
            if algo_id == "next_year":
                lbl_status = self._lbl_next_year_status
                self.ui_refs[algo_id] = {"status": lbl_status, "show_btn": None}
                continue

            btn_run = ttk.Button(
                grid_frame,
                text=f"Calistir: {algo_id.upper()}",
                command=lambda i=algo_id: self.run_single_step(i),
            )
            btn_run.grid(row=row_idx, column=0, padx=4, pady=3, sticky="ew")

            lbl_status = tk.Label(
                grid_frame, text="Bekliyor...", bg="#cbd5e1",
                width=14, anchor="center", font=("Segoe UI", 8),
            )
            lbl_status.grid(row=row_idx, column=1, padx=4, pady=3)

            btn_show = ttk.Button(
                grid_frame,
                text="Sonuc Goster",
                state="disabled",
                command=lambda i=algo_id: self.show_result(i),
            )
            btn_show.grid(row=row_idx, column=2, padx=4, pady=3, sticky="ew")

            self.ui_refs[algo_id] = {"status": lbl_status, "show_btn": btn_show}
            row_idx += 1

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(2, weight=1)

    def run_all_algorithms(self):
        """Algoritma kontrol merkezi: secili yil icin toplu hesaplama calistir."""
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(
            tk.END,
            "Toplu hesaplama baslatiliyor...\nLutfen bekleyiniz.\n",
        )
        self.result_text.config(state="disabled")
        self.run_single_step("next_year")
        self.update_idletasks()

    def run_single_step(self, algo_id: str):
        """Tek bir algoritma adimini calistirir. Sonucu results_cache'e kaydeder ve UI status etiketini gunceller."""
        if algo_id not in self.ui_refs:
            return

        widgets = self.ui_refs[algo_id]
        if algo_id == "next_year":
            widgets["status"].config(text="Calisiyor...", fg="#fcd34d")
            self._btn_next_year.config(state="disabled", bg="#6b7280", text="Calisiyor...")
        else:
            widgets["status"].config(text="Calisiyor...", bg="#fcd34d")
            if widgets.get("show_btn"):
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
                motor = KararMotoru()
                agirliklar = motor.ahp_calistir()
                cr, gecerli, lambda_max = motor.ahp_tutarlilik_kontrolu(agirliklar=agirliklar)

                sonuc_metni = "AHP Matrisi ve Kriter Ağırlıkları:\n==================================\n"
                sonuc_metni += f"1. Performans (Başarı): {agirliklar[0]:.4f} (%{agirliklar[0]*100:.1f})\n"
                sonuc_metni += f"2. Trend:               {agirliklar[1]:.4f} (%{agirliklar[1]*100:.1f})\n"
                sonuc_metni += f"3. Popülerlik:          {agirliklar[2]:.4f} (%{agirliklar[2]*100:.1f})\n"
                sonuc_metni += f"4. Anket:               {agirliklar[3]:.4f} (%{agirliklar[3]*100:.1f})\n\n"
                sonuc_metni += f"Tutarlılık Oranı (CR): {cr:.4f} (λmax={lambda_max:.2f})\n"
                sonuc_metni += f"CR < 0.10: {'✅ Geçerli' if gecerli else '⚠️ Dikkat: Matris tutarsız olabilir'}\n"

            # 3) TREND
            elif algo_id == "trend":
                from app.services.calculation import KararMotoru
                motor = KararMotoru()

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

                motor = KararMotoru()

                sorgu = """
                    SELECT
                        d.ders_id, d.ad as ders,
                        p.akademik_yil, p.basari_orani,
                        pop.doluluk_orani as populerlik,
                        pop.kontenjan, pop.talep_sayisi
                    FROM ders d
                    LEFT JOIN performans p ON d.ders_id = p.ders_id
                    LEFT JOIN populerlik pop ON d.ders_id = pop.ders_id
                        AND pop.akademik_yil = p.akademik_yil
                    WHERE p.basari_orani IS NOT NULL
                    ORDER BY d.ders_id, p.akademik_yil DESC;
                """
                ham_veri = self.db.read_df(sorgu)
                if ham_veri.empty:
                    sonuc_metni = "Veri bulunamadı! Lütfen önce 'MOCK' veriyi çalıştırın."
                    basarili_mi = False
                else:
                    anket_map = {}
                    try:
                        _, anket_rows = self.db.run_sql(
                            """SELECT ders_id,
                                      CASE WHEN anket_katilimci > 0
                                           THEN MIN(1.0, MAX(0.0, CAST(anket_dersi_secen AS REAL) / anket_katilimci))
                                           ELSE 0.5 END as anket_orani
                               FROM ders_kriterleri
                               WHERE anket_katilimci > 0
                               GROUP BY ders_id
                               ORDER BY yil DESC"""
                        )
                        for r in (anket_rows or []):
                            did = int(r[0])
                            if did not in anket_map:
                                anket_map[did] = float(r[1])
                    except Exception:
                        pass

                    islenmis = []
                    for _, grup in ham_veri.groupby("ders_id"):
                        ders_adi = grup.iloc[0]["ders"]
                        yillik = grup.groupby("akademik_yil")["basari_orani"].mean().reset_index()
                        yillik = yillik.sort_values("akademik_yil", ascending=False)
                        gecmis = [{"yil": int(r["akademik_yil"]), "oran": float(r["basari_orani"])} for _, r in yillik.iterrows()]

                        trend_skoru, _ = motor.gecmis_trend_hesapla(gecmis) if hasattr(motor, "gecmis_trend_hesapla") else (0, "")
                        son_basari = gecmis[0]["oran"] if gecmis else 0.0

                        pop_val = grup["populerlik"].dropna()
                        pop_norm = float(pop_val.iloc[0]) if len(pop_val) > 0 else 0.5
                        pop_norm = max(0.0, min(1.0, pop_norm))

                        ders_id_val = int(grup["ders_id"].iloc[0])
                        anket_val = anket_map.get(ders_id_val, 0.5)

                        islenmis.append({
                            "ders_id": ders_id_val,
                            "ders": ders_adi,
                            "basari": son_basari,
                            "trend": trend_skoru,
                            "populerlik": pop_norm,
                            "anket": anket_val,
                        })

                    df_final = pd.DataFrame(islenmis)
                    if "ders_id" not in df_final.columns and len(islenmis) > 0:
                        df_final["ders_id"] = [r["ders_id"] for r in islenmis]
                    agirliklar = motor.ahp_calistir()
                    df_sonuc, meta = motor.topsis_calistir(df_final, agirliklar)

                    sonuc_metni = "--- NİHAİ KARAR MATRİSİ (TOPSIS) ---\n"
                    sonuc_metni += "Girdiler: Başarı + Trend + Popülerlik + Anket\n\n"
                    if not df_sonuc.empty:
                        cols = [c for c in ["Ders", "AHP_TOPSIS_Skor", "Kesinlesme_Puani", "S+", "S-"] if c in df_sonuc.columns]
                        sonuc_metni += df_sonuc[cols].head(20).to_string(index=False, float_format="%.4f")
                    else:
                        sonuc_metni += "Hesaplama sonucu boş döndü."

            # 5) Sonraki yil mufredat uretimi (manuel, yil bazli)
            elif algo_id == "next_year":
                from app.services.calculation import run_all_algorithms_for_year
                import os

                db_path = getattr(self.app, "db_path", None) or self.db_path
                if not db_path:
                    raise ValueError("Veritabani yolu bulunamadi.")
                db_path = os.path.abspath(db_path)

                secili_yil = None
                if self.cb_algo_year and self.cb_algo_year.get():
                    try:
                        secili_yil = int(self.cb_algo_year.get())
                    except Exception:
                        secili_yil = None
                if secili_yil is None:
                    try:
                        _, rows = self.db.run_sql("SELECT MAX(akademik_yil) FROM mufredat")
                        secili_yil = int(rows[0][0]) if rows and rows[0][0] is not None else 2022
                    except Exception:
                        secili_yil = 2022

                summary = run_all_algorithms_for_year(
                    yil=int(secili_yil),
                    db_path=db_path,
                    donem="G",
                )

                processed = summary.get("processed", []) or []
                skipped = summary.get("skipped", []) or []
                errors = summary.get("errors", []) or []

                lines = []
                lines.append(f"Algoritma kontrol merkezi: {int(secili_yil)} yili calistirildi.")
                lines.append(
                    f"Ozet: islenen_fakulte={len(processed)} | atlanan_fakulte={len(skipped)} | hata={len(errors)}"
                )
                lines.append("")

                if processed:
                    lines.append("Islenen fakulteler:")
                    for item in processed:
                        lines.append(f"- {item.get('message', '')}")
                        for bol in item.get("departments", []) or []:
                            lines.append(
                                f"  * {bol.get('bolum', '?')} | dis_bolum_dersi={bol.get('dis_bolum_ders_sayisi', 0)}"
                            )
                    lines.append("")

                if skipped:
                    lines.append("Atlanan fakulteler:")
                    for item in skipped:
                        lines.append(f"- {item.get('reason')}")
                        missing_criteria = item.get("missing_criteria", []) or []
                        for mk in missing_criteria[:8]:
                            lines.append(
                                f"  * Eksik: {mk.get('bolum')} | {mk.get('ders')} (ID:{mk.get('ders_id')})"
                            )
                        if len(missing_criteria) > 8:
                            lines.append(f"  * ... +{len(missing_criteria) - 8} ders daha")
                    lines.append("")

                if errors:
                    lines.append("Hatalar:")
                    for item in errors:
                        lines.append(
                            f"- {item.get('fakulte')} | yil={item.get('year')} -> {item.get('error')}"
                        )

                if not processed and not skipped and not errors:
                    lines.append("Calistirilacak uygun fakulte bulunamadi.")

                sonuc_metni = "\n".join(lines)
                basarili_mi = bool(summary.get("ok", True)) and len(errors) == 0

                try:
                    self._refresh_algo_year_options()
                except Exception:
                    pass
                try:
                    self.page_pool.refresh(select_latest_year=True)
                except Exception:
                    pass
                try:
                    self.page_lab.refresh()
                except Exception:
                    pass
                try:
                    self.app.refresh_all()
                except Exception:
                    pass

            # 6) ML
            elif algo_id in ["lr", "rf", "dt"]:
                from app.services.ai_engine import HavuzAIEngine
                try:
                    from app.db.database import get_session
                    db_oturumu = get_session()
                    havuz_ai = HavuzAIEngine(db_oturumu)

                    kfold_txt = havuz_ai.run_kfold(algorithm_type=algo_id, k=5)
                    sonuc_metni = kfold_txt + "\n"

                    pred_df = havuz_ai.predict_all_courses()
                    if not pred_df.empty:
                        ders_names = {}
                        try:
                            _, d_rows = self.db.run_sql("SELECT ders_id, ad FROM ders")
                            ders_names = {int(r[0]): str(r[1]) for r in (d_rows or [])}
                        except Exception:
                            pass

                        pred_df["ders_ad"] = pred_df["ders_id"].apply(
                            lambda x: ders_names.get(int(x), f"#{x}")
                        )

                        if algo_id == "lr":
                            sonuc_metni += "\n--- Ders Bazli LR Tahminleri ---\n"
                            show = pred_df[["ders_ad", "basari_orani", "lr_tahmin"]].copy()
                            show.columns = ["Ders", "Gercek(%)", "LR_Tahmin(%)"]
                            show["Gercek(%)"] = (show["Gercek(%)"] * 100).round(1)
                            show = show.sort_values("LR_Tahmin(%)", ascending=False)
                            sonuc_metni += show.head(25).to_string(index=False, float_format="%.1f")
                        elif algo_id == "rf":
                            sonuc_metni += "\n--- Ders Bazli RF Tahminleri ---\n"
                            show = pred_df[["ders_ad", "skor", "rf_tahmin"]].copy()
                            show.columns = ["Ders", "Gercek_Skor", "RF_Tahmin"]
                            show = show.sort_values("RF_Tahmin", ascending=False)
                            sonuc_metni += show.head(25).to_string(index=False, float_format="%.1f")
                        elif algo_id == "dt":
                            statu_map = {1: "Mufredat", 0: "Havuz", -1: "Dinlenme", -2: "Iptal"}
                            sonuc_metni += "\n--- Ders Bazli DT Tahminleri ---\n"
                            show = pred_df[["ders_ad", "statu", "dt_tahmin"]].copy()
                            show.columns = ["Ders", "Gercek", "DT_Tahmin"]
                            show["Gercek_Lbl"] = show["Gercek"].map(statu_map).fillna("?")
                            show["Tahmin_Lbl"] = show["DT_Tahmin"].map(statu_map).fillna("?")
                            show["Eslesme"] = show["Gercek"] == show["DT_Tahmin"]
                            acc = show["Eslesme"].mean() * 100
                            sonuc_metni += f"Tahmin dogrulugu: %{acc:.1f}\n\n"
                            display = show[["Ders", "Gercek_Lbl", "Tahmin_Lbl", "Eslesme"]]
                            sonuc_metni += display.head(25).to_string(index=False)

                    db_oturumu.close()
                except Exception as ml_exc:
                    import traceback
                    sonuc_metni = (
                        f"ML Hata: {ml_exc}\n\n{traceback.format_exc()}"
                    )
                    basarili_mi = False

            else:
                sonuc_metni = f"Bu algo_id desteklenmiyor: {algo_id}"
                basarili_mi = False

        except Exception as e:
            import traceback
            basarili_mi = False
            sonuc_metni = f"HATA OLUŞTU:\n{e}\n\nDetay:\n{traceback.format_exc()}"
            print(f"[Algoritma {algo_id}] Hata: {e}")
            traceback.print_exc()

        self.results_cache[algo_id] = sonuc_metni

        if algo_id == "next_year":
            if basarili_mi:
                widgets["status"].config(text="Tamamlandi", fg="#86efac")
                self._btn_next_year.config(
                    state="normal", bg="#16a34a",
                    text="Sonraki Yil Mufredat Uret",
                )
            else:
                widgets["status"].config(text="Hata!", fg="#fca5a5")
                self._btn_next_year.config(
                    state="normal", bg="#dc2626",
                    text="Sonraki Yil (Hata!)",
                )
            self.show_result(algo_id)
        else:
            if basarili_mi:
                widgets["status"].config(text="Tamamlandi", bg="#86efac")
            else:
                widgets["status"].config(text="Hata!", bg="#fca5a5")
            if widgets.get("show_btn"):
                widgets["show_btn"].config(state="normal")
            self.show_result(algo_id)

    def show_result(self, algo_id: str):
        """Secilen algoritmanin cache'deki sonucunu log panelinde gosterir."""
        metin = self.results_cache.get(algo_id, "Sonuç bulunamadı.")

        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)

        baslik = f"--- SONUÇ: {algo_id.upper()} ---\n\n"
        self.result_text.insert(tk.END, baslik)
        self.result_text.insert(tk.END, metin)

        self.result_text.config(state="disabled")

    def _toggle_fullscreen(self):
        """Ders analiz panelini tam ekran yapar veya eski haline dondurur."""
        if self._is_fullscreen:
            self._paned.add(self._top_container, before=self._bottom_container, minsize=200)
            self._btn_fullscreen.config(text="Tam Ekran")
            self._is_fullscreen = False
        else:
            self._paned.forget(self._top_container)
            self._btn_fullscreen.config(text="Normal Gorunum")
            self._is_fullscreen = True



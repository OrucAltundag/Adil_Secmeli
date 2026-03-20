# -*- coding: utf-8 -*-
# app/ui/tabs/calc_tab.py
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
        """Algoritma Kontrol & Ders Lab sekmesi acildiginda ders listesini yukle."""
        try:
            idx = self.sub_nb.index(self.sub_nb.select())
            if idx == 1:  # Algoritma Kontrol & Ders Lab
                self.page_lab.refresh()
        except Exception:
            pass

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

        # Ders Analiz Lab yenile
        try:
            self.page_lab.refresh()
        except Exception:
            pass

        # Kriter sayfasını yenile (fakülteler + ders listesi)
        try:
            if hasattr(self.criteria_view, "load_faculties"):
                self.criteria_view.load_faculties()
        except Exception as e:
            print(f"[CalcTab] load_faculties hatası: {e}")
        try:
            if hasattr(self.criteria_view, "load_courses"):
                self.criteria_view.load_courses()
        except Exception as e:
            print(f"[CalcTab] load_courses hatası: {e}")



    # =========================================================
    #  1) ALGO PANEL
    # =========================================================
    def setup_algo_panel(self, parent):
        # Dikey bolum: Ust = Genel Kontrol, Alt = Ders Laboratuvari
        paned = tk.PanedWindow(parent, orient=tk.VERTICAL, sashwidth=6, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # UST: Genel Algoritma Kontrolu
        top_container = tk.Frame(paned, bg="#f0f0f0")
        paned.add(top_container, minsize=180)

        main_container = tk.Frame(top_container, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_container, bg="#e2e8f0", width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        tk.Label(
            left_frame,
            text="Genel Kontrol",
            bg="#1e293b",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            pady=8
        ).pack(fill=tk.X)

        grid_frame = tk.Frame(left_frame, bg="#e2e8f0")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        right_frame = tk.Frame(main_container, bg="#fce7f3")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(
            right_frame,
            text="Sonuc / Log",
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

        # ALT: Ders Analiz Laboratuvari
        bottom_container = tk.Frame(paned, bg="white")
        paned.add(bottom_container, minsize=220)
        self.page_lab = CourseAnalysisTab(bottom_container, app=self.app)
        self.page_lab.pack(fill=tk.BOTH, expand=True)

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
                {"id": "next_year", "name": "Sonraki Yıl Müfredat Üretimi"},
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

            # 5) Sonraki yil mufredat uretimi (okul geneli zincirli pipeline)
            elif algo_id == "next_year":
                from app.services.calculation import rebuild_school_curricula
                import os

                db_path = getattr(self.app, "db_path", None) or self.db_path
                if not db_path:
                    raise ValueError("Veritabani yolu bulunamadi.")
                db_path = os.path.abspath(db_path)

                pipeline = rebuild_school_curricula(
                    db_path=db_path,
                    base_year=2022,
                    donem="G",
                    max_rounds=8,
                )

                reset = pipeline.get("reset") or {}
                gen = pipeline.get("generation") or {}
                generated = gen.get("generated", []) or []
                skipped = gen.get("skipped", []) or []
                errors = gen.get("errors", []) or []
                rounds = gen.get("rounds", []) or []

                lines = []
                lines.append("Okul geneli mufredat yeniden olusturma pipeline'i calisti.")
                lines.append("1) 2022 disi mufredat temizlendi")
                lines.append("2) Kriterleri tamam olan yillar zincirleme yeniden uretildi")
                lines.append("")

                lines.append(
                    f"Temizlik: mufredat={reset.get('deleted_mufredat', 0)} | "
                    f"mufredat_ders={reset.get('deleted_mufredat_ders', 0)} | "
                    f"havuz={reset.get('deleted_havuz', 0)}"
                )
                lines.append(f"Legacy duzeltme kaydi: {reset.get('normalized_curricula', 0)}")
                lines.append(
                    f"Uretim ozeti: round={len(rounds)} | olusan={len(generated)} | "
                    f"atlanan={len(skipped)} | hata={len(errors)}"
                )
                lines.append("")

                for item in generated:
                    lines.append(
                        f"[{item.get('fakulte')}] {item.get('year_from')} -> {item.get('year_to')} "
                        f"(havuz upsert={item.get('pool_rows_upserted', 0)})"
                    )
                    for bol in item.get("departments", []):
                        b_ad = bol.get("bolum", "?")
                        if bol.get("tasindi_mi"):
                            lines.append(f"- {b_ad}: Degisiklik yok, mufredat tasindi.")
                            continue
                        dusen = bol.get("dusenler", []) or []
                        eklenen = bol.get("eklenenler", []) or []
                        if dusen:
                            lines.append(f"- {b_ad} | Cikanlar:")
                            for d in dusen:
                                rs = " + ".join(d.get("reasons", []) or ["Kural geregi"])
                                lines.append(
                                    f"  * {d.get('ders')} (Skor:{d.get('score', 0):.1f}, "
                                    f"Ort:{d.get('average_grade', 0):.1f}) -> {rs}"
                                )
                        if eklenen:
                            lines.append(f"- {b_ad} | Girenler:")
                            for e in eklenen:
                                rs = " + ".join(e.get("reasons", []) or ["Yuksek kesinlesme puani"])
                                lines.append(
                                    f"  * {e.get('ders')} (Skor:{e.get('score', 0):.1f}) -> {rs}"
                                )
                    lines.append("")

                if skipped:
                    lines.append("Atlanan fakulteler/yillar:")
                    for item in skipped[:30]:
                        ytxt = f" | yil={item.get('year')}" if item.get("year") is not None else ""
                        lines.append(f"- {item.get('fakulte')} {ytxt} -> {item.get('reason')}")
                        missing_criteria = item.get("missing_criteria", []) or []
                        if missing_criteria:
                            lines.append("  Eksik kriter girisleri:")
                            for mk in missing_criteria[:8]:
                                lines.append(
                                    f"    * {mk.get('bolum')} | {mk.get('ders')} (ID:{mk.get('ders_id')})"
                                )
                            if len(missing_criteria) > 8:
                                lines.append(f"    * ... +{len(missing_criteria)-8} ders daha")

                        missing_curricula = item.get("missing_curricula", []) or []
                        if missing_curricula:
                            lines.append("  Eksik mufredat bolumleri:")
                            for mm in missing_curricula[:8]:
                                lines.append(f"    * {mm.get('bolum')} (bolum_id={mm.get('bolum_id')})")
                            if len(missing_curricula) > 8:
                                lines.append(f"    * ... +{len(missing_curricula)-8} bolum daha")
                    lines.append("")

                if errors:
                    lines.append("Hatalar:")
                    for item in errors[:20]:
                        ytxt = f" | yil={item.get('year')}" if item.get("year") is not None else ""
                        lines.append(f"- {item.get('fakulte')} {ytxt} -> {item.get('error')}")

                if not generated and not errors:
                    lines.append("Yeni yil uretimi yapilmadi. (Kriterler eksik olabilir veya sistem zaten guncel.)")

                sonuc_metni = "\n".join(lines)
                basarili_mi = bool(pipeline.get("ok", False)) and len(errors) == 0

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

        if basarili_mi:
            widgets["status"].config(text="Tamamlandi", bg="#86efac")
            widgets["show_btn"].config(state="normal")
            self.show_result(algo_id)
        else:
            widgets["status"].config(text="Hata!", bg="#fca5a5")
            widgets["show_btn"].config(state="normal")
            self.show_result(algo_id)

    def show_result(self, algo_id: str):
        metin = self.results_cache.get(algo_id, "Sonuç bulunamadı.")

        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)

        baslik = f"--- SONUÇ: {algo_id.upper()} ---\n\n"
        self.result_text.insert(tk.END, baslik)
        self.result_text.insert(tk.END, metin)

        self.result_text.config(state="disabled")


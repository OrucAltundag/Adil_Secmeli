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
# "Sonraki Yil Mufredat Uret" butonu secili fakulte ve yil icin:
#   - Fakulte bazli kriter tamlık kontrolu yapar
#   - Eksik varsa uyari verir
#   - Tamam ise algoritmalari calistirir ve sonraki yil mufredatini uretir
# =============================================================================
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd

from app.services.yearly_workflow import (
    get_missing_criteria,
    get_years_eligible_for_algorithm,
    is_faculty_criteria_complete,
)
from app.ui.tabs.course_analysis_tab import CourseAnalysisTab
from app.ui.tabs.criteria_page import CriteriaPage
from app.ui.tabs.pool_tab import PoolTab
from app.ui.utils.validation import validate_combobox_selection

# Kullanici mesaji (tam metin — spesifikasyon)
_MSG_CRITERIA_BLOCK = (
    "Bu fakültede bütün bölümlerin bu yıl özelinde kriter giriş işlemleri tamamlanmadı. "
    "Yeni yıl müfredatı oluşturulamaz."
)

_NEXT_YEAR_BATCH_ALGOS = ("mock", "trend", "ahp", "topsis", "lr", "rf", "dt")



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
        self.cb_algo_fakulte = None  # Fakülte combobox'ı
        self._fakulte_map = {}  # ad -> id eşlemesi
        self._algo_buttons = {}


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

        # NOT: "Ders İlişkileri & Kurallar" sekmesi kullanıcı talebiyle arayüzden
        # kaldırıldı (RelationsTab sınıfı/dosyası ileride yeniden kullanılabilmesi
        # için korunmaktadır; yalnızca notebook'a eklenmiyor).

        # 2) Pool tab
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
            elif idx == 2 and not getattr(self, "_pool_initialized", False):
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
                self.criteria_view.load_courses(
                    restore_course_id=restore_id,
                    show_warnings=False,
                )
        except Exception as e:
            print(f"[CalcTab] load_courses hatasi: {e}")
        try:
            self._refresh_algo_faculty_options()
            self._refresh_algo_year_options()
            self._sync_algo_controls()
        except Exception:
            pass

    def _refresh_algo_faculty_options(self):
        """Algoritma paneli için fakülte listesini yükler."""
        if not self.cb_algo_fakulte:
            return
        previous = self.cb_algo_fakulte.get()
        try:
            _, rows = self.db.run_sql("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
            faculties = [str(r[1]) for r in (rows or []) if r and r[1]]
            self._fakulte_map = {str(r[1]): int(r[0]) for r in (rows or []) if r and r[1]}
            self.cb_algo_fakulte["values"] = faculties
            if faculties:
                if previous in faculties:
                    self.cb_algo_fakulte.set(previous)
                else:
                    self.cb_algo_fakulte.set(faculties[0])
        except Exception as e:
            print(f"[CalcTab] Fakulte listesi yuklenemedi: {e}")

    def _on_algo_faculty_change(self, event=None):
        """Fakülte değişince yıl listesini o fakülteye göre güncelle."""
        self._refresh_algo_year_options()
        self._sync_algo_controls()

    def _update_button_state(self):
        """Update Next Year button state based on form validity."""
        ready = self._algo_scope_ready()
        next_state = tk.NORMAL if ready else tk.DISABLED
        if getattr(self, "_btn_next_year", None) is not None:
            self._btn_next_year.config(state=next_state, bg="#16a34a" if ready else "#6b7280")
        for button in self._algo_buttons.values():
            button.config(state=next_state)

    def _sync_algo_controls(self):
        self._update_button_state()

    def _refresh_algo_year_options(self):
        """
        Algoritma paneli yil listesi: secili fakultede tum bolumlerin kriter girisi
        tamamlanmis akademik yillar (sabit aralik / havuz copu yil yok).
        """
        if not self.cb_algo_year:
            return
        previous = self.cb_algo_year.get()
        years: list[str] = []

        fakulte_name = self.cb_algo_fakulte.get() if self.cb_algo_fakulte else ""
        fakulte_id = self._fakulte_map.get(fakulte_name) if fakulte_name else None

        try:
            conn = getattr(self.db, "conn", None)
            if conn and fakulte_id:
                years_int = get_years_eligible_for_algorithm(conn, int(fakulte_id))
                years = [str(y) for y in years_int]
        except Exception as e:
            print(f"[CalcTab] Algoritma yil listesi: {e}")

        if years:
            self.cb_algo_year["values"] = years
            if previous in years:
                self.cb_algo_year.set(previous)
            else:
                self.cb_algo_year.set(years[-1])
        else:
            self.cb_algo_year["values"] = []
            self.cb_algo_year.set("")
        self._sync_algo_controls()
        self._update_button_state()

    def _algo_scope_ready(self) -> bool:
        if not self.cb_algo_fakulte or not self.cb_algo_year:
            return False
        return bool((self.cb_algo_fakulte.get() or "").strip()) and bool((self.cb_algo_year.get() or "").strip())

    @staticmethod
    def _friendly_ui_error() -> str:
        return "İşlem tamamlanamadı. Detay alanındaki hata kaydını kontrol edin."

    def _missing_algo_scope_message(self) -> str:
        missing = []
        if not self.cb_algo_fakulte or not (self.cb_algo_fakulte.get() or "").strip():
            missing.append("Fakülte")
        if not self.cb_algo_year or not (self.cb_algo_year.get() or "").strip():
            missing.append("Akademik yıl")
        if not missing:
            return "Algoritma çalıştırmak için fakülte ve yıl seçiniz."
        return (
            "Algoritma çalıştırmak için önce seçimleri tamamlayınız.\n\n"
            f"Eksik alan: {', '.join(missing)}"
        )

    def _algo_scope(self) -> tuple[int, str, int]:
        """Algoritma paneli: (fakulte_id, fakulte_ad, akademik_yil)."""
        name = self.cb_algo_fakulte.get() if self.cb_algo_fakulte else ""
        fid = self._fakulte_map.get(name)
        if not fid:
            raise ValueError("Lutfen bir fakulte seciniz.")
        ystr = (self.cb_algo_year.get() or "").strip() if self.cb_algo_year else ""
        if not ystr:
            raise ValueError("Lutfen bir yil seciniz.")
        return int(fid), name, int(ystr)



    # =========================================================
    #  1) ALGO PANEL
    # =========================================================
    def setup_algo_panel(self, parent):
        """
        Algoritma kontrol panelini olusturur:
        - Ust bar: Fakulte ve Yil secimi + Sonraki Yil Mufredat Uret butonu
        - Sol: Her algoritma icin calistir/goster butonlari
        - Sag: Log/sonuc alani
        - Alt: Ders analiz laboratuvari

        NOT: "Tumunu Calistir" butonu kaldirildi - islevi "Sonraki Yil Mufredat Uret"
        butonuna tasindi. Bu buton artik fakulte bazli kriter tamlık kontrolu yapar.
        """
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
            text="Sonraki Yıl Kararını Hesapla",
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

        # Fakülte seçimi - yıl listesi fakülteye göre güncellenir
        tk.Label(
            next_year_bar,
            text="Fakulte:",
            bg="#0f172a",
            fg="#cbd5e1",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(16, 4))
        self.cb_algo_fakulte = ttk.Combobox(next_year_bar, state="readonly", width=28)
        self.cb_algo_fakulte.pack(side=tk.LEFT, padx=(0, 8))
        self.cb_algo_fakulte.bind("<<ComboboxSelected>>", self._on_algo_faculty_change)

        tk.Label(
            next_year_bar,
            text="Yil:",
            bg="#0f172a",
            fg="#cbd5e1",
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(8, 4))
        self.cb_algo_year = ttk.Combobox(next_year_bar, state="readonly", width=8)
        self.cb_algo_year.pack(side=tk.LEFT, padx=(0, 8))
        self.cb_algo_year.bind("<<ComboboxSelected>>", lambda e: self._update_button_state())

        # --- Otomatik mod + Excel: kullanici "kriter girdileri tamamlandiginda
        # sistem otomatik mufredat/oneri uretip Excel paylassin" istedi. ---
        try:
            from app.services.auto_pipeline_service import is_auto_pipeline_enabled

            self._auto_mode_var = tk.BooleanVar(value=is_auto_pipeline_enabled())
        except Exception:
            self._auto_mode_var = tk.BooleanVar(value=False)
        self._chk_auto_mode = tk.Checkbutton(
            next_year_bar,
            text="Otomatik Mod",
            variable=self._auto_mode_var,
            command=self._toggle_auto_mode,
            bg="#0f172a", fg="#cbd5e1", selectcolor="#0f172a",
            activebackground="#0f172a", activeforeground="white",
            font=("Segoe UI", 9, "bold"),
        )
        self._chk_auto_mode.pack(side=tk.LEFT, padx=(16, 4))

        # Açılışta otomatik algoritma/müfredat üretimi (yearly_workflow bayrağı).
        # Konsoldaki "[AUTO] ... otomatik algoritma tetigi kapali" mesajını kontrol eder.
        try:
            from app.services.yearly_workflow import is_startup_auto_scoring_enabled
            self._startup_auto_var = tk.BooleanVar(value=is_startup_auto_scoring_enabled())
        except Exception:
            self._startup_auto_var = tk.BooleanVar(value=False)
        self._chk_startup_auto = tk.Checkbutton(
            next_year_bar,
            text="Açılışta Otomatik Üretim",
            variable=self._startup_auto_var,
            command=self._toggle_startup_auto,
            bg="#0f172a", fg="#cbd5e1", selectcolor="#0f172a",
            activebackground="#0f172a", activeforeground="white",
            font=("Segoe UI", 9, "bold"),
        )
        self._chk_startup_auto.pack(side=tk.LEFT, padx=(8, 4))

        self._btn_export_excel = tk.Button(
            next_year_bar,
            text="Ders Önerisi Excel'e Aktar",
            bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
            font=("Segoe UI", 9, "bold"), cursor="hand2", relief="flat", bd=0, padx=12, pady=4,
            command=self._export_recommendation_excel,
        )
        self._btn_export_excel.pack(side=tk.LEFT, padx=(8, 0))

        # Fakülte ve yıl combobox'larını doldur
        self._refresh_algo_faculty_options()
        self._refresh_algo_year_options()

        # İlk durumda button disabled olsun
        self._btn_next_year.config(state="disabled", bg="#6b7280")

        # "Tumunu Calistir" butonu KALDIRILDI - islevi "Sonraki Yil Mufredat Uret"
        # butonuna tasindi. Tek buton hem kriter tamlık kontrolu yapar hem de
        # tum algoritmalari calistirip sonraki yil mufredatini uretir.

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
            self._algo_buttons[algo_id] = btn_run

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
        self._sync_algo_controls()

    # run_all_algorithms metodu KALDIRILDI - islevi run_single_step("next_year") icine tasindi
    # Eski kod: Algoritma kontrol merkezi: secili yil icin toplu hesaplama calistir
    # Yeni davranis: "Sonraki Yil Mufredat Uret" butonu artik hem kriter tamlık kontrolu
    # yapar hem de tum algoritmalari calistirip sonraki yil mufredatini uretir.

    def _run_full_algorithm_batch_for_next_year(self):
        """
        Eski 'Tumunu Calistir' davranisini korur.
        Next-year akisi once gorunur algoritmalari tek tek calistirir, sonra
        mufredat uretim hattina gecer.
        """
        batch_results = []
        for batch_algo_id in _NEXT_YEAR_BATCH_ALGOS:
            if batch_algo_id not in self.ui_refs:
                continue
            self.run_single_step(batch_algo_id)

            status_text = ""
            status_widget = self.ui_refs.get(batch_algo_id, {}).get("status")
            if status_widget is not None:
                try:
                    status_text = str(status_widget.cget("text") or "")
                except Exception:
                    status_text = ""

            batch_results.append(
                {
                    "id": batch_algo_id,
                    "status": status_text or "Bilinmiyor",
                    "ok": status_text == "Tamamlandi",
                }
            )
        return batch_results

    def _toggle_auto_mode(self):
        """Otomatik modu config.json'a yazar; kullanıcıya kısa bilgi verir."""
        try:
            from app.services.auto_pipeline_service import set_auto_pipeline_enabled

            enabled = bool(self._auto_mode_var.get())
            set_auto_pipeline_enabled(enabled)
            if enabled:
                messagebox.showinfo(
                    "Otomatik Mod",
                    "Otomatik mod açıldı.\n\nKriter girdileri tamamlandığında (kriter "
                    "importu sonrası) sistem ilgili fakülte için yeni yıl müfredatını "
                    "üretip ders önerisi Excel'ini exports/ klasörüne yazacak.",
                )
            else:
                messagebox.showinfo("Otomatik Mod", "Otomatik mod kapatıldı (manuel çalışma).")
        except Exception:
            messagebox.showerror("Otomatik Mod", self._friendly_ui_error())

    def _toggle_startup_auto(self):
        """Açılışta otomatik üretimi config.json'a yazar (yearly_workflow bayrağı)."""
        try:
            from app.services.yearly_workflow import (
                set_startup_auto_scoring_enabled,
                yearly_workflow_env_override,
            )

            enabled = bool(self._startup_auto_var.get())
            set_startup_auto_scoring_enabled(enabled)
            if yearly_workflow_env_override():
                messagebox.showwarning(
                    "Açılışta Otomatik Üretim",
                    "Ayar kaydedildi ANCAK ENABLE_YEARLY_CRITERIA_WORKFLOW ortam değişkeni "
                    "ayarlı olduğu için config'i geçersiz kılar. Etki etmesi için ortam "
                    "değişkenini kaldırın.",
                )
                return
            durum = "AÇIK" if enabled else "KAPALI"
            messagebox.showinfo(
                "Açılışta Otomatik Üretim",
                f"Açılışta otomatik algoritma/müfredat üretimi: {durum}.\n\n"
                "Değişiklik bir sonraki uygulama açılışında geçerli olur. "
                "(KAPALI iken üretimi 'Sonraki Yıl Müfredat Üret' ile elle yaparsınız.)",
            )
        except Exception:
            messagebox.showerror("Açılışta Otomatik Üretim", self._friendly_ui_error())

    def _export_recommendation_excel(self):
        """Seçili fakülte/yıl için ders önerisi Excel'ini elle üretir."""
        try:
            import os

            from app.services.auto_pipeline_service import export_recommendations_excel

            db_path = getattr(self.app, "db_path", None) or getattr(self, "db_path", None)
            if not db_path:
                messagebox.showerror("Excel", "Veritabanı yolu bulunamadı.")
                return
            year = None
            if self.cb_algo_year and self.cb_algo_year.get():
                try:
                    year = int(self.cb_algo_year.get())
                except ValueError:
                    year = None
            if year is None:
                messagebox.showwarning("Excel", "Önce yıl seçin.")
                return
            fac_id = None
            if self.cb_algo_fakulte and self.cb_algo_fakulte.get():
                fac_id = self._fakulte_map.get(self.cb_algo_fakulte.get())
            # Seçili yıl kaynak yıl ise üretilen yıl = year+1; ama kullanıcı doğrudan
            # mevcut yılın önerisini de isteyebilir. Burada seçili yılın raporunu üretiriz.
            faculty_ids = [int(fac_id)] if fac_id is not None else None
            path = export_recommendations_excel(
                db_path=os.path.abspath(db_path),
                year=int(year),
                faculty_ids=faculty_ids,
            )
            messagebox.showinfo("Excel", f"Ders önerisi Excel oluşturuldu:\n{path}")
        except Exception:
            messagebox.showerror("Excel", self._friendly_ui_error())

    def run_single_step(self, algo_id: str):
        """
        Tek bir algoritma adimini calistirir. Sonucu results_cache'e kaydeder ve UI status etiketini gunceller.

        "next_year" icin ozel davranis:
        - Secili fakulte icin kriter tamlık kontrolu yapar
        - Eksik kriter varsa hata mesaji gosterir ve islemi durdurur
        - Tamam ise tum algoritmalari calistirip sonraki yil mufredatini uretir
        """
        if algo_id not in self.ui_refs:
            return
        if not self._algo_scope_ready():
            messagebox.showwarning(
                "Eksik Seçim",
                self._missing_algo_scope_message(),
            )
            self._sync_algo_controls()
            return

        # FORM VALIDATION: UI tarafı validasyon
        # Kullanıcı seçimi yoksa backend'e gitmemesi için
        if algo_id in ("mock", "ahp", "topsis", "trend", "lr", "rf", "dt", "next_year"):
            if not validate_combobox_selection(
                self.cb_algo_fakulte,
                "Fakülte",
                error_title="Eksik Seçim"
            ):
                return
            
            if not validate_combobox_selection(
                self.cb_algo_year,
                "Akademik Yıl",
                error_title="Eksik Seçim"
            ):
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
                fid, fac_name, yctx = self._algo_scope()
                res = self.db.run_sql(
                    "SELECT COUNT(*) FROM ogrenci WHERE fakulte_id = ?",
                    (fid,),
                )
                sayi = res[1][0][0] if res[1] else 0
                sonuc_metni = (
                    f"Kapsam: {fac_name} | yil {yctx}\n"
                    "==================\n"
                    "Veritabanı Durumu:\n"
                    f"Bu fakultedeki ogrenci sayisi: {sayi}\n"
                    "Durum: Veriler analiz için hazır."
                )

            # 2) AHP
            elif algo_id == "ahp":
                fid, fac_name, yctx = self._algo_scope()
                from app.services.calculation import KararMotoru
                from app.services.ahp_profile_service import (
                    DEFAULT_CRITERIA_KEYS,
                    resolve_ahp_profile,
                )

                conn = getattr(self.db, "conn", None)
                if conn is None:
                    raise ValueError("Veritabani baglantisi yok.")

                profile = resolve_ahp_profile(
                    conn,
                    faculty_id=fid,
                    department_id=None,
                    year=yctx,
                )
                weights_dict = dict(profile.get("weights") or {})
                agirliklar = [float(weights_dict.get(key, 0.0)) for key in DEFAULT_CRITERIA_KEYS]
                total = sum(agirliklar) or 1.0
                agirliklar = [value / total for value in agirliklar]

                motor = KararMotoru()
                cr = float(profile.get("consistency_ratio") or 0.0)
                gecerli = bool(profile.get("is_consistent", True))
                lambda_max = 0.0
                matrix = profile.get("pairwise_matrix") or None
                if matrix:
                    try:
                        cr, gecerli, lambda_max = motor.ahp_tutarlilik_kontrolu(
                            matris=matrix,
                            agirliklar=agirliklar,
                        )
                    except Exception:
                        lambda_max = 0.0

                sonuc_metni = f"Kapsam: {fac_name} | yil {yctx}\n\n"
                sonuc_metni += (
                    "Aktif AHP Profili:\n"
                    "==================\n"
                    f"ID: {profile.get('id')} | Ad: {profile.get('name') or profile.get('profile_name')} | "
                    f"Versiyon: {profile.get('version')} | Kapsam: {profile.get('scope_type')}\n\n"
                )
                sonuc_metni += "AHP Matrisi ve Kriter Ağırlıkları:\n==================================\n"
                sonuc_metni += f"1. Performans (Başarı): {agirliklar[0]:.6f} (%{agirliklar[0]*100:.3f})\n"
                sonuc_metni += f"2. Trend:               {agirliklar[1]:.6f} (%{agirliklar[1]*100:.3f})\n"
                sonuc_metni += f"3. Popülerlik:          {agirliklar[2]:.6f} (%{agirliklar[2]*100:.3f})\n"
                sonuc_metni += f"4. Anket:               {agirliklar[3]:.6f} (%{agirliklar[3]*100:.3f})\n\n"
                sonuc_metni += f"Tutarlılık Oranı (CR): {cr:.6f} (λmax={lambda_max:.6f})\n"
                sonuc_metni += f"CR < 0.10: {'✅ Geçerli' if gecerli else '⚠️ Dikkat: Matris tutarsız olabilir'}\n"

            # 3) TREND
            elif algo_id == "trend":
                fid, fac_name, yctx = self._algo_scope()
                from app.services.calculation import KararMotoru
                motor = KararMotoru()

                sorgu = """
                    SELECT d.ders_id, d.ad as ders, p.akademik_yil, p.basari_orani
                    FROM ders d
                    JOIN performans p ON d.ders_id = p.ders_id
                    WHERE p.basari_orani IS NOT NULL
                      AND EXISTS (
                          SELECT 1 FROM mufredat_ders md
                          JOIN mufredat m ON md.mufredat_id = m.mufredat_id
                          JOIN bolum b ON m.bolum_id = b.bolum_id
                          WHERE md.ders_id = d.ders_id AND b.fakulte_id = ?
                            AND m.akademik_yil = ?
                      )
                    ORDER BY d.ders_id, p.akademik_yil DESC;
                """
                ham_veri = self.db.read_df(sorgu, params=(fid, yctx))
                if ham_veri.empty:
                    sonuc_metni = (
                        f"Kapsam: {fac_name} | yil {yctx}\n"
                        "Secili fakulte icin performans verisi yok.\n"
                        "Kriter / performans kayitlarini kontrol edin."
                    )
                    basarili_mi = False
                else:
                    gruplanmis = ham_veri.groupby("ders_id")
                    sonuc_metni = (
                        f"Kapsam: {fac_name} | referans yil {yctx}\n"
                        "--- DERSLERİN TARİHSEL BAŞARI ANALİZİ ---\n"
                        "(Agirlikli gecmis yil formulu — motor)\n\n"
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
                fid, fac_name, yctx = self._algo_scope()
                from app.services.calculation import get_faculty_year_topsis_results

                conn = getattr(self.db, "conn", None)
                if conn is None:
                    raise ValueError("Veritabani baglantisi yok.")

                pack = get_faculty_year_topsis_results(
                    cur=conn.cursor(),
                    fakulte_id=fid,
                    akademik_yil=yctx,
                    donem="G",
                    strict_ahp=True,
                )
                if not pack.get("ok"):
                    sonuc_metni = (
                        f"Kapsam: {fac_name} | yil {yctx}\n"
                        f"TOPSIS hesaplanamadi: {pack.get('error')}\n"
                    )
                    basarili_mi = False
                else:
                    profile = pack.get("ahp_profile") or {}
                    meta = pack.get("meta") or {}
                    sonuc_metni = f"Kapsam: {fac_name} | yil {yctx}\n"
                    sonuc_metni += "--- NİHAİ KARAR MATRİSİ (AHP + TOPSIS) ---\n"
                    sonuc_metni += "Girdiler: Başarı + Trend + Popülerlik + Anket\n"
                    sonuc_metni += (
                        f"AHP profili: #{profile.get('id', '—')} "
                        f"{profile.get('name') or profile.get('profile_name') or ''} "
                        f"v{profile.get('version', '—')}\n"
                    )
                    if meta.get("agirliklar"):
                        sonuc_metni += "Ağırlıklar: " + ", ".join(
                            f"{key}={float(value):.6f}"
                            for key, value in zip(meta.get("sutunlar", []), meta.get("agirliklar", []))
                        ) + "\n"
                    sonuc_metni += "\n"

                    df_sonuc = pack.get("df_sonuc")
                    if df_sonuc is not None and not df_sonuc.empty:
                        cols = [
                            c for c in ["Ders", "AHP_TOPSIS_Skor", "Kesinlesme_Puani", "S+", "S-"]
                            if c in df_sonuc.columns
                        ]
                        sonuc_metni += df_sonuc[cols].head(20).to_string(index=False, float_format="%.6f")
                    else:
                        scores = sorted(
                            dict(pack.get("scores") or {}).items(),
                            key=lambda item: float(item[1]),
                            reverse=True,
                        )
                        if scores:
                            sonuc_metni += "TOPSIS evreni boş; havuz/anket skorlari:\n"
                            for ders_id, score in scores[:20]:
                                sonuc_metni += f"- Ders {ders_id}: {float(score):.6f}\n"
                        else:
                            sonuc_metni += "Hesaplama sonucu boş döndü."

            # 5) Sonraki yil mufredat uretimi (fakulte bazli, kriter tamlık kontrolu ile)
            elif algo_id == "next_year":
                # Seçili fakülte ID'sini al
                secili_fakulte_id = None
                secili_fakulte_ad = None
                if self.cb_algo_fakulte and self.cb_algo_fakulte.get():
                    secili_fakulte_ad = self.cb_algo_fakulte.get()
                    secili_fakulte_id = self._fakulte_map.get(secili_fakulte_ad)

                if not secili_fakulte_id:
                    raise ValueError("Lutfen bir fakulte seciniz.")

                secili_yil = None
                if self.cb_algo_year and self.cb_algo_year.get():
                    try:
                        secili_yil = int(self.cb_algo_year.get())
                    except Exception:
                        secili_yil = None
                if secili_yil is None:
                    try:
                        _, rows = self.db.run_sql(
                            """
                            SELECT MAX(m.akademik_yil)
                            FROM mufredat m
                            JOIN bolum b ON b.bolum_id = m.bolum_id
                            WHERE b.fakulte_id = ?
                            """,
                            (secili_fakulte_id,),
                        )
                        secili_yil = int(rows[0][0]) if rows and rows[0][0] is not None else None
                    except Exception:
                        secili_yil = None
                if secili_yil is None:
                    raise ValueError(
                        "Secili fakulte icin akademik yil yok. Yil listesinden secin veya once mufredat yukleyin."
                    )

                # FAKÜLTE BAZLI KRİTER TAMLIK KONTROLÜ
                # Seçili fakültedeki tüm bölümlerin seçili yıl için kriter girişleri tamamlanmış olmalı
                conn = getattr(self.db, "conn", None)
                if conn:
                    kriter_tamam = is_faculty_criteria_complete(conn, secili_yil, secili_fakulte_id, refresh=True)

                    if not kriter_tamam:
                        # Eksik kriterleri listele
                        eksik_kriterler = get_missing_criteria(conn, secili_yil, fakulte_id=secili_fakulte_id)

                        # Eksik bölümleri bul
                        eksik_bolumler = set()
                        for ek in eksik_kriterler:
                            eksik_bolumler.add(ek.get("bolum", "?"))

                        hata_mesaji = _MSG_CRITERIA_BLOCK + "\n\n"
                        hata_mesaji += (
                            f"Fakulte: {secili_fakulte_ad}\n"
                            f"Yil: {secili_yil}\n\n"
                            f"Eksik kriter girisi olan bolumler:\n"
                        )
                        for bol in sorted(eksik_bolumler):
                            hata_mesaji += f"  - {bol}\n"

                        if eksik_kriterler:
                            hata_mesaji += f"\nToplam eksik ders sayisi: {len(eksik_kriterler)}\n"
                            hata_mesaji += "\nIlk 10 eksik ders:\n"
                            for ek in eksik_kriterler[:10]:
                                hata_mesaji += f"  * {ek.get('bolum')} | {ek.get('ders')} (ID:{ek.get('ders_id')})\n"
                            if len(eksik_kriterler) > 10:
                                hata_mesaji += f"  ... +{len(eksik_kriterler) - 10} ders daha\n"

                        sonuc_metni = hata_mesaji
                        basarili_mi = False

                        # UI'ı güncelle ve erken çık
                        widgets["status"].config(text="Kriter Eksik!", fg="#ef4444")
                        self._btn_next_year.config(
                            state="normal", bg="#16a34a", text="Sonraki Yıl Kararını Hesapla"
                        )
                        self.results_cache[algo_id] = sonuc_metni
                        self.result_text.config(state="normal")
                        self.result_text.delete("1.0", tk.END)
                        self.result_text.insert(tk.END, sonuc_metni)
                        self.result_text.config(state="disabled")

                        # Kullanıcıya messagebox ile de uyarı ver
                        messagebox.showwarning(
                            "Kriter Girisleri Eksik",
                            hata_mesaji,
                        )
                        return

                # Kriter kontrolü geçildi: Güz+Bahar için yalnız GEÇİCİ karar
                # çalıştırmaları oluşturulur. Müfredat/havuz burada değiştirilmez.
                from app.services.decision_run_service import record_decision_run_for_faculty_year

                conn = getattr(self.db, "conn", None)
                if conn is None:
                    raise ValueError("Veritabanı bağlantısı bulunamadı.")
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT DISTINCT b.bolum_id, b.ad
                    FROM mufredat m
                    JOIN bolum b ON b.bolum_id=m.bolum_id
                    WHERE b.fakulte_id=? AND m.akademik_yil=?
                    ORDER BY b.ad, b.bolum_id
                    """,
                    (int(secili_fakulte_id), int(secili_yil)),
                )
                departments = [(int(row[0]), str(row[1] or row[0])) for row in cur.fetchall()]
                if not departments:
                    raise ValueError("Seçili fakülte/yıl için karar üretilecek bölüm bulunamadı.")
                results = []
                for department_id, department_name in departments:
                    for term in ("Guz", "Bahar"):
                        try:
                            result = record_decision_run_for_faculty_year(
                                conn,
                                year=int(secili_yil),
                                faculty_id=int(secili_fakulte_id),
                                department_id=int(department_id),
                                semester=term,
                                created_by="calc-tab",
                            )
                            results.append((department_name, term, result, None))
                        except Exception as exc:
                            results.append((department_name, term, None, str(exc)))
                conn.commit()

                lines = [
                    f"{secili_fakulte_ad} / {secili_yil} için geçici müfredat kararları hesaplandı.",
                    "Müfredat ve havuz kayıtları değiştirilmedi.",
                    "",
                ]
                for department_name, term, result, error in results:
                    if error:
                        lines.append(f"{department_name} / {term}: oluşturulamadı — {error}")
                    else:
                        summary = (result or {}).get("summary") or {}
                        lines.append(
                            f"{department_name} / {term}: karar #{(result or {}).get('decision_run_id')} | "
                            f"ders={summary.get('course_count', 0)} | "
                            f"PROMETHEE öneri={((summary.get('candidate_recommendations') or {}).get('selected_count', 0))}"
                        )
                sonuc_metni = "\n".join(lines)
                basarili_mi = any(result and result.get("ok") for _, _, result, _ in results)
                if basarili_mi:
                    try:
                        self.app._nb_karar.select(self.app.tab_decision_center)
                        self.app.tab_decision_center.refresh()
                    except Exception:
                        pass
                try:
                    self.app.refresh_all()
                except Exception:
                    pass

            # 6) ML
            elif algo_id in ["lr", "rf", "dt"]:
                fid_ml, fac_ml, y_ml = self._algo_scope()
                from app.services.ai_engine import HavuzAIEngine
                db_oturumu = None
                try:
                    from app.db.database import get_session
                    db_oturumu = get_session()
                    havuz_ai = HavuzAIEngine(db_oturumu)

                    kfold_txt = havuz_ai.run_kfold(
                        algorithm_type=algo_id,
                        k=5,
                        fakulte_id=fid_ml,
                        yil=y_ml,
                        curriculum_only=True,
                    )
                    sonuc_metni = f"Kapsam: {fac_ml} | yil {y_ml}\n\n"
                    sonuc_metni += kfold_txt + "\n"

                    pred_df = havuz_ai.predict_all_courses(
                        fakulte_id=fid_ml,
                        yil=y_ml,
                        curriculum_only=True,
                    )
                    train_meta = havuz_ai.get_last_training_meta()
                    if train_meta.get("fallback_used"):
                        sonuc_metni += (
                            "\nNot: Mufredat kapsaminda yeterli egitim verisi olmadigi icin "
                            f"ML egitimi fakulte geneli havuz verisiyle genisletildi "
                            f"({train_meta.get('target_rows')} -> {train_meta.get('fit_rows')} satir).\n"
                        )
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
                            show = pred_df[["ders_ad", "basari_orani", "lr_tahmin"]].rename(  # type: ignore[call-overload]
                                columns={"ders_ad": "Ders", "basari_orani": "Gercek(%)", "lr_tahmin": "LR_Tahmin(%)"}
                            )
                            show["Gercek(%)"] = (show["Gercek(%)"] * 100).round(1)
                            show = show.sort_values(by="LR_Tahmin(%)", ascending=False)
                            sonuc_metni += show.head(25).to_string(index=False, float_format="%.1f")
                        elif algo_id == "rf":
                            sonuc_metni += "\n--- Ders Bazli RF Tahminleri ---\n"
                            show = pred_df[["ders_ad", "skor", "rf_tahmin"]].rename(  # type: ignore[call-overload]
                                columns={"ders_ad": "Ders", "skor": "Gercek_Skor", "rf_tahmin": "RF_Tahmin"}
                            )
                            show = show.sort_values(by="RF_Tahmin", ascending=False)
                            sonuc_metni += show.head(25).to_string(index=False, float_format="%.1f")
                        elif algo_id == "dt":
                            statu_map = {1: "Mufredat", 0: "Havuz", -1: "Dinlenme", -2: "Iptal"}
                            sonuc_metni += "\n--- Ders Bazli DT Tahminleri ---\n"
                            show = pred_df[["ders_ad", "statu", "dt_tahmin"]].rename(  # type: ignore[call-overload]
                                columns={"ders_ad": "Ders", "statu": "Gercek", "dt_tahmin": "DT_Tahmin"}
                            )
                            show["Gercek_Lbl"] = show["Gercek"].map(statu_map).fillna("?")  # type: ignore[arg-type]
                            show["Tahmin_Lbl"] = show["DT_Tahmin"].map(statu_map).fillna("?")  # type: ignore[arg-type]
                            show["Eslesme"] = show["Gercek"] == show["DT_Tahmin"]
                            acc = show["Eslesme"].mean() * 100
                            sonuc_metni += f"Tahmin dogrulugu: %{acc:.1f}\n\n"
                            display = show[["Ders", "Gercek_Lbl", "Tahmin_Lbl", "Eslesme"]]
                            sonuc_metni += display.head(25).to_string(index=False)
                    else:
                        sonuc_metni += "\nBu fakulte ve yil kapsami icin ML tahmin verisi bulunamadi."
                except Exception as ml_exc:
                    import traceback
                    print(f"[CalcTab] ML hata: {ml_exc}")
                    sonuc_metni = self._friendly_ui_error() + f"\n\nDetay kaydı:\n{traceback.format_exc()}"
                    basarili_mi = False
                finally:
                    try:
                        if db_oturumu is not None:
                            db_oturumu.close()
                    except Exception:
                        pass

            else:
                sonuc_metni = f"Bu algo_id desteklenmiyor: {algo_id}"
                basarili_mi = False

        except Exception as e:
            import traceback
            basarili_mi = False
            print(f"[Algoritma {algo_id}] Hata: {e}")
            traceback.print_exc()
            sonuc_metni = self._friendly_ui_error()

        self.results_cache[algo_id] = sonuc_metni

        if algo_id == "next_year":
            if basarili_mi:
                widgets["status"].config(text="Tamamlandi", fg="#86efac")
                self._btn_next_year.config(
                    state="normal", bg="#16a34a",
                    text="Sonraki Yıl Kararını Hesapla",
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

        self._sync_algo_controls()

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

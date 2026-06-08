# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs/criteria_page.py — Kriter Girdi Sayfası
# =============================================================================
# Ders bazlı kriter verisi girişi: toplam_ogrenci, gecen_ogrenci, ortalama,
# kontenjan, kayitli. Kaydetme: ders_kriterleri + performans + populerlik tablolarına
# yazar. Algoritmalar (calculation.py) performans/popülerlik'ten okur.
# =============================================================================

import csv
import logging
import os
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from app.db.schema_compat import ensure_reporting_schema
from app.services.criteria_completion_service import get_completion_summary
from app.services.criteria_import_service import (
    FACULTY_SCOPE_LABEL,
    format_criteria_import_summary,
    get_active_criteria_import,
    get_criteria_import_by_id,
)
from app.services.criteria_import_service import (
    import_criteria_excel as run_criteria_import,
)
from app.services.criteria_import_service import (
    normalize_department_scope_name,
)
from app.services.criteria_override_service import list_overrides, request_override
from app.services.criteria_task_service import generate_tasks_for_missing_criteria
from app.services.yearly_workflow import mark_criteria_status

logger = logging.getLogger(__name__)


class CriteriaPage:
    """
    Kriter Girdi Sayfasi.

    Sol panel: Fakulte/Bolum/Yil filtreleriyle ders listesi (kriter durumu ile).
    Sag panel: Secilen ders icin akademik performans, kontenjan/populerlik
    ve anket tercih verilerinin giris formu.

    Kaydet isleminde:
      1. ders_kriterleri tablosuna INSERT/UPDATE
      2. performans tablosuna ortalama_not + basari_orani yazilir
      3. populerlik tablosuna talep + kontenjan + doluluk_orani yazilir
      4. kriter tamamlama durumu bolum/fakulte bazinda guncellenir
    """

    def __init__(self, parent, db, app=None):
        self.parent = parent
        self.db = db
        self.app = app
        self.selected_course_id = None
        self._survey_locked = False
        self._current_survey_record = None
        self._current_criteria_import_summary = None
        self._student_dataset_path = None  # Secilen ogrenci veri seti yolu

        self._ensure_table()

        # Arayüzü Kur
        self.setup_ui()

    def _ensure_table(self):
        """Kriter ve raporlama semalarini migration-safe sekilde hazirlar."""
        if not getattr(self.db, "conn", None):
            return
        try:
            ensure_reporting_schema(self.db.conn)
        except Exception as e:
            print(f"ders_kriterleri tablo oluşturma hatası: {e}")

    def _refresh_related_views(self, restore_course_id=None):
        """
        Kriter kaydı sonrası ilgili ekranları yeniler.
        Bu metod tüm bağlı sekmeler için refresh tetikler.
        """
        if not self.app:
            return
        try:
            # CalcTab (Havuz Yönetimi dahil) yenile
            if hasattr(self.app, "tab_calc"):
                self.app.tab_calc.refresh(force_reload=True)
        except Exception as exc:
            print(f"[CriteriaPage] tab_calc refresh hatasi: {exc}")
        try:
            # Rapor & Yükleme sekmesini yenile
            if hasattr(self.app, "tab_tools"):
                self.app.tab_tools.refresh()
        except Exception as exc:
            print(f"[CriteriaPage] tab_tools refresh hatasi: {exc}")
        try:
            # Veri Görüntüleme sekmesini yenile
            if hasattr(self.app, "tab_view"):
                self.app.tab_view.refresh()
        except Exception as exc:
            print(f"[CriteriaPage] tab_view refresh hatasi: {exc}")
        try:
            # Kriter listesini restore et
            if restore_course_id is not None:
                self.load_courses(restore_course_id=restore_course_id)
        except Exception as exc:
            print(f"[CriteriaPage] load_courses refresh hatasi: {exc}")

    def setup_ui(self):
        # --- ANA DÜZEN: Üst (Filtre), Sol (Liste), Sağ (Form) ---

        # 1. ÜST PANEL: FİLTRELER
        top_frame = tk.Frame(self.parent, bg="#f1f5f9", pady=10, padx=10)
        top_frame.pack(fill=tk.X)

        # Filtre Bileşenleri
        self.create_filter_ui(top_frame)

        # 2. ALT PANEL: İÇERİK (PanedWindow ile bölünebilir yapı)
        paned = tk.PanedWindow(self.parent, orient=tk.HORIZONTAL, sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # A. SOL PANEL: DERS LİSTESİ
        left_frame = tk.Frame(paned, bg="white", width=400)
        paned.add(left_frame)

        tk.Label(left_frame, text="DERS LİSTESİ", bg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)

        # Treeview
        cols = ("ID", "Ders Adı", "Kriter Durumu")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Ders Adı", text="Ders Adı")
        self.tree.heading("Kriter Durumu", text="Veri Var mı?")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Ders Adı", width=250)
        self.tree.column("Kriter Durumu", width=100, anchor="center")

        sb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Seçim Olayı
        self.tree.bind("<<TreeviewSelect>>", self.on_course_select)

        # B. SAĞ PANEL: VERİ GİRİŞ FORMU
        right_frame = tk.Frame(paned, bg="#f8fafc", width=500)
        paned.add(right_frame)

        self.create_form_ui(right_frame)
        self.create_completion_panel()

        # Fakülte listesi uygulama veritabani baglantisi kurulduktan sonra
        # refresh() veya ilk veri yuklemesinde doldurulur.
        if getattr(self.db, "conn", None):
            self.load_faculties()

    def create_filter_ui(self, parent):
        # Stil
        lbl_style = {"bg": "#f1f5f9", "font": ("Segoe UI", 9, "bold")}

        # Fakülte
        tk.Label(parent, text="Fakülte:", **lbl_style).pack(side=tk.LEFT, padx=5)
        self.cb_fakulte = ttk.Combobox(parent, state="readonly", width=25)
        self.cb_fakulte.pack(side=tk.LEFT, padx=5)
        self.cb_fakulte.bind("<<ComboboxSelected>>", self.on_faculty_change)

        # Bölüm
        tk.Label(parent, text="Bölüm:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_bolum = ttk.Combobox(parent, state="readonly", width=25)
        self.cb_bolum.pack(side=tk.LEFT, padx=5)
        # Bölüm değişince yıl listesini güncelle
        self.cb_bolum.bind("<<ComboboxSelected>>", self._on_department_change)

        # Yıl - artık hard-coded değil, veritabanından dinamik yükleniyor
        tk.Label(parent, text="Yıl:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_yil = ttk.Combobox(parent, state="readonly", width=10, values=[])
        self.cb_yil.pack(side=tk.LEFT, padx=5)

        # Dönem
        tk.Label(parent, text="Dönem:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_donem = ttk.Combobox(parent, state="readonly", width=10, values=["Güz", "Bahar"])
        self.cb_donem.current(0)
        self.cb_donem.pack(side=tk.LEFT, padx=5)

        # Kriter durumu filtresi
        tk.Label(parent, text="Kriter:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_kriter_filtre = ttk.Combobox(parent, state="readonly", width=12,
                                            values=["Tümü", "Girildi", "Girilmedi"])
        self.cb_kriter_filtre.current(0)
        self.cb_kriter_filtre.pack(side=tk.LEFT, padx=5)

        # Müfredat filtresi
        tk.Label(parent, text="Müfredat:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_mufredat_filtre = ttk.Combobox(parent, state="readonly", width=14,
                                              values=["Tümü", "Müfredattakiler"])
        self.cb_mufredat_filtre.current(0)
        self.cb_mufredat_filtre.pack(side=tk.LEFT, padx=5)

        # Listele Butonu
        tk.Button(parent, text="Dersleri Getir", bg="#3b82f6", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self.load_courses).pack(side=tk.LEFT, padx=20)

        # Kriter Excel İçe Aktar (fonksiyon vardı ama butonu yoktu → erişilemiyordu)
        tk.Button(parent, text="📥 Kriter Excel İçe Aktar", bg="#f97316", fg="white",
                  font=("Segoe UI", 9, "bold"),
                  command=self.import_kriterler_excel).pack(side=tk.LEFT, padx=5)

        # Öğrenci Veri Seti seçici
        tk.Button(parent, text="📂 Öğrenci Veri Seti", bg="#059669", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self._select_student_dataset).pack(side=tk.LEFT, padx=(10, 2))
        self.lbl_dataset_name = tk.Label(
            parent,
            text="seçilmedi",
            bg="#f1f5f9",
            fg="#64748b",
            font=("Segoe UI", 8, "italic"),
            width=22,
            anchor="w",
        )
        self.lbl_dataset_name.pack(side=tk.LEFT, padx=(0, 10))

        # Otomatik kriter üretimi (seçilen veri setini kullanır)
        tk.Button(parent, text="🎓 Otomatik Kriter Girdi İşlemleri",
                  bg="#7c3aed", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self.auto_generate_from_dataset).pack(side=tk.LEFT, padx=5)

    def create_form_ui(self, parent):
        tk.Label(parent, text="KRİTER VERİ GİRİŞİ", bg="#1e293b", fg="white",
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill=tk.X)

        self.form_frame = tk.Frame(parent, bg="#f8fafc", padx=20, pady=20)
        self.form_frame.pack(fill=tk.BOTH, expand=True)

        # Ders Başlığı
        self.lbl_selected_course = tk.Label(self.form_frame, text="Lütfen soldan bir ders seçiniz.",
                                            bg="#f8fafc", fg="#334155", font=("Segoe UI", 12, "bold"))
        self.lbl_selected_course.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        self.lbl_criteria_source_info = tk.Label(
            self.form_frame,
            text="Aktif kriter dosyasi: -",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 9, "italic"),
            wraplength=360,
            justify="left",
        )
        self.lbl_criteria_source_info.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # --- GİRİŞ ALANLARI ---

        # 1. Akademik Başarı Verileri
        self.create_section_header(2, "1. Akademik Performans")
        self.ent_toplam_ogrenci = self.create_input_row(3, "Dersi Alan Toplam Öğrenci:", "0")
        self.ent_gecen_ogrenci = self.create_input_row(4, "Dersi Geçen Öğrenci:", "0")
        self.ent_ortalama = self.create_input_row(5, "Ders Not Ortalaması (0-100):", "0.0")

        # Otomatik Hesaplanan: Başarı Oranı
        tk.Label(self.form_frame, text="Başarı Oranı (%):", bg="#f8fafc", font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="w", pady=5)
        self.lbl_basari_sonuc = tk.Label(self.form_frame, text="-", bg="#e2e8f0", width=10)
        self.lbl_basari_sonuc.grid(row=6, column=1, sticky="w")

        # 2. Kontenjan ve İlgi
        self.create_section_header(7, "2. Kontenjan ve Popülerlik")
        self.ent_kontenjan = self.create_input_row(8, "Ders Kontenjanı:", "0")
        self.ent_kayitli = self.create_input_row(9, "Kayıtlı Öğrenci (otomatik):", "0")

        # Otomatik Hesaplanan: Doluluk
        tk.Label(self.form_frame, text="Doluluk Oranı (%):", bg="#f8fafc", font=("Segoe UI", 9, "bold")).grid(row=10, column=0, sticky="w", pady=5)
        self.lbl_doluluk_sonuc = tk.Label(self.form_frame, text="-", bg="#e2e8f0", width=10)
        self.lbl_doluluk_sonuc.grid(row=10, column=1, sticky="w")

        # 3. Anket Tercihi
        self.create_section_header(11, "3. Anket Tercihi")
        self.ent_anket_katilimci = self.create_input_row(12, "Ankete Katılan Toplam Öğrenci (otomatik):", "0")
        self.ent_anket_katilimci.config(state="disabled")
        self.ent_anket_dersi_secen = self.create_input_row(13, "Bu Dersi Seçen Öğrenci:", "0")
        tk.Label(self.form_frame, text="Anket Tercih Oranı (%):", bg="#f8fafc", font=("Segoe UI", 9, "bold")).grid(row=14, column=0, sticky="w", pady=5)
        self.lbl_anket_sonuc = tk.Label(self.form_frame, text="-", bg="#e2e8f0", width=10)
        self.lbl_anket_sonuc.grid(row=14, column=1, sticky="w")
        self.lbl_anket_kaynak_info = tk.Label(
            self.form_frame,
            text="Anket verisi manuel girise acik.",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 9, "italic"),
            wraplength=280,
            justify="left",
        )
        self.lbl_anket_kaynak_info.grid(row=15, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # KAYDET BUTONU
        btn_save = tk.Button(self.form_frame, text="💾 VERİLERİ KAYDET VE GÜNCELLE",
                             bg="#16a34a", fg="white", font=("Segoe UI", 10, "bold"),
                             command=self.save_data, cursor="hand2")
        btn_save.grid(row=16, column=0, columnspan=2, sticky="ew", pady=30, ipady=5)

    def create_completion_panel(self):
        panel = ttk.LabelFrame(self.parent, text="Gelişmiş Tamlık Paneli", padding=8)
        panel.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))

        actions = ttk.Frame(panel)
        actions.pack(fill=tk.X, pady=(0, 6))
        self.lbl_completion_summary = ttk.Label(
            actions,
            text="Tamlık bilgisi için fakülte, yıl ve dönem seçip yenileyin.",
        )
        self.lbl_completion_summary.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(actions, text="Yenile", command=self.refresh_completion_panel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(actions, text="Eksiklerden Görev Oluştur", command=self._generate_completion_tasks).pack(side=tk.RIGHT, padx=4)
        ttk.Button(actions, text="Override Talep Et", command=self._request_completion_override).pack(side=tk.RIGHT, padx=4)
        ttk.Button(actions, text="CSV Dışa Aktar", command=self._export_completion_matrix).pack(side=tk.RIGHT, padx=4)

        nb = ttk.Notebook(panel)
        nb.pack(fill=tk.BOTH, expand=True)

        matrix_frame = ttk.Frame(nb)
        nb.add(matrix_frame, text="Eksik Kriter Matrisi")
        columns = ("ders", "başarı", "ortalama", "kontenjan", "kayıtlı", "anket", "trend", "durum")
        self.tree_completion_matrix = ttk.Treeview(matrix_frame, columns=columns, show="headings", height=6)
        for col in columns:
            self.tree_completion_matrix.heading(col, text=col.title())
            self.tree_completion_matrix.column(col, width=120, anchor=tk.W)
        matrix_y = ttk.Scrollbar(matrix_frame, orient=tk.VERTICAL, command=self.tree_completion_matrix.yview)
        matrix_x = ttk.Scrollbar(matrix_frame, orient=tk.HORIZONTAL, command=self.tree_completion_matrix.xview)
        self.tree_completion_matrix.configure(yscrollcommand=matrix_y.set, xscrollcommand=matrix_x.set)
        self.tree_completion_matrix.grid(row=0, column=0, sticky="nsew")
        matrix_y.grid(row=0, column=1, sticky="ns")
        matrix_x.grid(row=1, column=0, sticky="ew")
        matrix_frame.columnconfigure(0, weight=1)
        matrix_frame.rowconfigure(0, weight=1)

        issues_frame = ttk.Frame(nb)
        nb.add(issues_frame, text="Validation Issues")
        issue_cols = ("ders", "alan", "seviye", "tip", "mesaj", "öneri")
        self.tree_completion_issues = ttk.Treeview(issues_frame, columns=issue_cols, show="headings", height=6)
        for col in issue_cols:
            self.tree_completion_issues.heading(col, text=col.title())
            self.tree_completion_issues.column(col, width=150, anchor=tk.W)
        issue_y = ttk.Scrollbar(issues_frame, orient=tk.VERTICAL, command=self.tree_completion_issues.yview)
        issue_x = ttk.Scrollbar(issues_frame, orient=tk.HORIZONTAL, command=self.tree_completion_issues.xview)
        self.tree_completion_issues.configure(yscrollcommand=issue_y.set, xscrollcommand=issue_x.set)
        self.tree_completion_issues.grid(row=0, column=0, sticky="nsew")
        issue_y.grid(row=0, column=1, sticky="ns")
        issue_x.grid(row=1, column=0, sticky="ew")
        issues_frame.columnconfigure(0, weight=1)
        issues_frame.rowconfigure(0, weight=1)

        self._last_completion_summary = None

    def create_section_header(self, row, text):
        tk.Label(self.form_frame, text=text, bg="#f8fafc", fg="#2563eb",
                 font=("Segoe UI", 10, "bold", "underline")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 5))

    def create_input_row(self, row, label_text, default_val):
        tk.Label(self.form_frame, text=label_text, bg="#f8fafc").grid(row=row, column=0, sticky="w", pady=5)
        var = tk.StringVar(value=default_val)
        entry = tk.Entry(self.form_frame, textvariable=var, width=15)
        entry.grid(row=row, column=1, sticky="w", padx=10)
        # Her tuşa basıldığında hesaplama yap
        entry.bind("<KeyRelease>", self.update_calculations)
        return entry

    def _selected_faculty_id(self) -> int | None:
        faculty_name = self.cb_fakulte.get()
        if not faculty_name or not getattr(self.db, "conn", None):
            return None
        try:
            _, rows = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad=? LIMIT 1", (faculty_name,))
            if not rows:
                return None
            return int(rows[0][0])
        except Exception:
            return None

    def _selected_department_name(self) -> str | None:
        return normalize_department_scope_name(self.cb_bolum.get())

    def _selected_department_id(self) -> int | None:
        faculty_id = self._selected_faculty_id()
        department_name = self._selected_department_name()
        if faculty_id is None or not department_name:
            return None
        try:
            _, rows = self.db.run_sql(
                "SELECT bolum_id FROM bolum WHERE fakulte_id=? AND ad=? LIMIT 1",
                (int(faculty_id), department_name),
            )
            if not rows:
                return None
            return int(rows[0][0])
        except Exception:
            return None

    def _selected_completion_scope(self) -> tuple[str, int | None, int | None, int | None, str | None]:
        faculty_id = self._selected_faculty_id()
        department_id = self._selected_department_id()
        year_raw = self.cb_yil.get()
        year = int(year_raw) if str(year_raw or "").strip().isdigit() else None
        semester = self.cb_donem.get() or "Güz"
        scope_type = "department" if department_id is not None else "faculty"
        return scope_type, faculty_id, department_id, year, semester

    def _matrix_display_value(self, row: dict[str, Any]) -> str:
        if row.get("missing_reason") and "istisna" in str(row.get("missing_reason")).lower():
            return "Yeni ders istisnası"
        if row.get("is_present") and row.get("is_valid"):
            return "Var"
        if row.get("is_present") and not row.get("is_valid"):
            return "Geçersiz"
        if not row.get("is_required"):
            return "Opsiyonel"
        return "Eksik"

    def refresh_completion_panel(self):
        if not getattr(self.db, "conn", None):
            return
        for tree_name in ("tree_completion_matrix", "tree_completion_issues"):
            tree = getattr(self, tree_name, None)
            if tree:
                tree.delete(*tree.get_children())
        try:
            scope_type, faculty_id, department_id, year, semester = self._selected_completion_scope()
            if faculty_id is None or year is None:
                self.lbl_completion_summary.config(text="Fakülte, yıl ve dönem seçimi bekleniyor.")
                return
            summary = get_completion_summary(
                self.db.conn,
                scope_type=scope_type,
                year=int(year),
                faculty_id=int(faculty_id),
                department_id=int(department_id) if department_id is not None else None,
                semester=semester,
                refresh=True,
            )
            self._last_completion_summary = summary
            risk = summary.get("missing_data_risk") or {}
            # Bekleyen (pending) override talepleri — override_active yalnızca onaylı override'ı yansıtır.
            try:
                pending = list_overrides(
                    self.db.conn,
                    scope_type=scope_type,
                    year=int(year),
                    faculty_id=int(faculty_id),
                    department_id=int(department_id) if department_id is not None else None,
                    semester=semester,
                    approval_status="pending",
                )
            except Exception:
                logger.exception("Bekleyen override sorgusu başarısız")
                pending = []
            if summary.get("override_active") and summary.get("can_run_algorithm"):
                durum = "Override ile hazır"
            elif pending:
                durum = "Override onayı bekliyor"
            elif summary.get("can_run_algorithm"):
                durum = "Hazır"
            else:
                durum = "Engellendi"
            self.lbl_completion_summary.config(
                text=(
                    f"Tamlık: %{float(summary.get('completion_ratio') or 0) * 100:.1f} | "
                    f"Seviye: {summary.get('completion_level')} | "
                    f"Algoritma: {durum} | "
                    f"Eksik zorunlu: {summary.get('missing_required_fields')} | "
                    f"Geçersiz: {summary.get('invalid_required_fields')} | "
                    f"Risk: {risk.get('risk_level', 'low')}"
                )
            )
            by_course: dict[int, dict[str, Any]] = {}
            for row in summary.get("matrix") or []:
                cid = int(row.get("course_id"))
                item = by_course.setdefault(
                    cid,
                    {
                        "name": row.get("course_code") or row.get("course_name") or str(cid),
                        "fields": {},
                        "status": "Tamam",
                    },
                )
                item["fields"][row.get("criterion_key")] = self._matrix_display_value(row)
                if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid")):
                    item["status"] = "Eksik/Geçersiz"
            for item in by_course.values():
                fields = item["fields"]
                self.tree_completion_matrix.insert(
                    "",
                    tk.END,
                    values=(
                        item["name"],
                        fields.get("passed_students") or fields.get("total_students") or "-",
                        fields.get("average_grade") or "-",
                        fields.get("capacity") or "-",
                        fields.get("enrolled_students") or "-",
                        fields.get("survey_count") or "-",
                        fields.get("trend") or "-",
                        item["status"],
                    ),
                )
            course_names = {
                int(row.get("course_id")): row.get("course_code") or row.get("course_name") or str(row.get("course_id"))
                for row in summary.get("matrix") or []
                if row.get("course_id") is not None
            }
            for issue in summary.get("validation_issues") or []:
                self.tree_completion_issues.insert(
                    "",
                    tk.END,
                    values=(
                        course_names.get(int(issue.get("course_id") or 0), issue.get("course_id") or ""),
                        issue.get("field_name") or issue.get("criterion_key") or "",
                        issue.get("severity") or "",
                        issue.get("issue_type") or "",
                        issue.get("message") or "",
                        issue.get("suggestion") or "",
                    ),
                )
        except Exception:
            logger.exception("Tamlık paneli yüklenemedi")
            self.lbl_completion_summary.config(text="Tamlık bilgisi yüklenemedi.")

    def _generate_completion_tasks(self):
        try:
            if not self._last_completion_summary:
                self.refresh_completion_panel()
            summary = self._last_completion_summary
            if not summary:
                return
            created = generate_tasks_for_missing_criteria(self.db.conn, summary)
            self.db.conn.commit()
            messagebox.showinfo("Görevler", f"{len(created)} yeni tamlık görevi oluşturuldu.")
        except Exception as exc:
            messagebox.showerror("Görevler", f"Görev oluşturulamadı:\n{exc}")

    def _current_username(self, default: str) -> str:
        active_user = getattr(self.app, "current_user", None) if self.app else None
        return getattr(active_user, "username", None) or default

    def _request_completion_override(self):
        try:
            if not self._last_completion_summary:
                self.refresh_completion_panel()
            summary = self._last_completion_summary
            if not summary:
                return
            # Hazırlık zaten uygunsa override gereksiz.
            if summary.get("can_run_algorithm") and not summary.get("blocking_reason"):
                messagebox.showinfo("Override", "Hazırlık zaten uygun; override talebine gerek yok.")
                return
            missing_fields = sorted(
                {
                    str(row.get("criterion_key"))
                    for row in summary.get("matrix") or []
                    if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
                }
            )
            if not missing_fields:
                messagebox.showinfo("Override", "Override gerektiren eksik/geçersiz zorunlu alan bulunmuyor.")
                return
            reason = simpledialog.askstring("Override Talebi", "Override gerekçesi:")
            if not reason or not reason.strip():
                return
            override = request_override(
                self.db.conn,
                scope_type=str(summary.get("scope_type") or "faculty"),
                year=int(summary.get("year") or 0),
                faculty_id=summary.get("faculty_id"),
                department_id=summary.get("department_id"),
                semester=summary.get("semester"),
                missing_fields=missing_fields,
                validation_issues=summary.get("validation_issues") or [],
                reason=reason.strip(),
                requested_by=self._current_username("ui"),
            )
            self.db.conn.commit()
            status = (override or {}).get("approval_status")
            if status == "pending":
                messagebox.showinfo(
                    "Override",
                    "Override talebi kaydedildi; ancak algoritma hâlâ çalıştırılamaz. "
                    "Bu kapsam için yetkili onayı gerekiyor (onay Karar Merkezi'nden verilebilir).",
                )
            elif status == "approved":
                messagebox.showinfo(
                    "Override",
                    "Override aktif edildi (politika onay gerektirmiyor). Algoritma override ile çalıştırılabilir.",
                )
            else:
                messagebox.showinfo("Override", f"Override talebi kaydedildi. Durum: {status}")
            self.refresh_completion_panel()
        except Exception as exc:
            logger.exception("Override talebi oluşturulamadı")
            messagebox.showerror("Override", f"Override talebi oluşturulamadı:\n{exc}")

    def _export_completion_matrix(self):
        if not self._last_completion_summary:
            self.refresh_completion_panel()
        summary = self._last_completion_summary
        if not summary:
            return
        path = filedialog.asksaveasfilename(
            title="Tamlık Matrisi CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Tümü", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "course_id",
                        "course_code",
                        "course_name",
                        "criterion_key",
                        "is_required",
                        "is_present",
                        "is_valid",
                        "missing_reason",
                        "invalid_reason",
                        "source_type",
                    ],
                )
                writer.writeheader()
                for row in summary.get("matrix") or []:
                    writer.writerow({key: row.get(key) for key in writer.fieldnames})
            messagebox.showinfo("Dışa Aktar", "Tamlık matrisi CSV olarak dışa aktarıldı.")
        except Exception as exc:
            messagebox.showerror("Dışa Aktar", f"CSV oluşturulamadı:\n{exc}")

    def _now_utc(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Sistem şu anda işlem yapamıyor. Lütfen daha sonra tekrar deneyin."

    # --- VERİ İŞLEMLERİ ---

    def _select_student_dataset(self):
        """Ogrenci not veri seti Excel dosyasini sec ve etiket ile goster."""
        path = filedialog.askopenfilename(
            title="Öğrenci Veri Seti Seç",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Tümü", "*.*")],
        )
        if not path:
            return
        self._student_dataset_path = path
        filename = os.path.basename(path)
        lbl = getattr(self, "lbl_dataset_name", None)
        if lbl:
            lbl.config(text=filename, fg="#15803d")

    def auto_generate_from_dataset(self):
        """Secilen (veya varsayilan) ogrenci not veri setinden
        butun derslerin kriterlerini OTOMATIK uretir.
        Manuel girisin yerine gecer; mevcut yilki kriterler yenilenir."""
        from tkinter import messagebox as _mb

        # Seçili yıl zorunlu: üretim hangi akademik yıla yazılacaksa o seçilmeli
        # (eski sürüm yılı 2022'ye hard-code ediyordu; seçilen yıldan bağımsız yazıyordu).
        year_raw = self.cb_yil.get()
        if not str(year_raw or "").strip().isdigit():
            _mb.showwarning("Eksik Kapsam", "Lütfen önce filtre alanından hedef akademik yılı seçiniz.")
            return
        target_year = int(year_raw)

        # Hangi dosya kullanilacak?
        excel_path = self._student_dataset_path  # kullanici sectiyse
        from pathlib import Path as _Path
        _varsayilan = (
            _Path(__file__).parent.parent.parent.parent / "data"
            / "2022_ogrenci_not_veri_seti.xlsx"
        )
        if not excel_path:
            excel_path = str(_varsayilan)

        import os as _os
        dosya_adi = _os.path.basename(str(excel_path))

        if not _mb.askyesno(
            "Otomatik Kriter Uretimi",
            f"Hedef akademik yil: {target_year}\n"
            f"Secilen veri seti: {dosya_adi}\n\n"
            "Bu dosyadan TUM ders kriterleri OTOMATIK uretilecek.\n"
            "Secili yildaki mevcut kriterleri (varsa) SILINIP yeniden yazilacak.\n\n"
            "Devam edilsin mi?",
        ):
            return
        try:
            from app.services.student_dataset_criteria_service import (
                auto_generate_criteria_from_student_dataset,
            )

            conn = getattr(self.db, "conn", None)
            if conn is None:
                _mb.showerror("Hata", "Veritabani baglantisi yok.")
                return
            sonuc = auto_generate_criteria_from_student_dataset(
                conn, excel_path=excel_path, year=target_year, replace=True
            )
            mesaj = (
                f"OTOMATIK URETIM TAMAMLANDI\n\n"
                f"  Kaynak dosya: {_os.path.basename(sonuc['excel_path'])}\n"
                f"  Eklenen kriter satiri: {sonuc['eklenen']}\n"
                f"  Veri setindeki toplam ders: {sonuc['toplam']}\n"
                f"  Eslesmeyen ders kodu: {len(sonuc['eslesmeyen'])}\n"
            )
            if sonuc["eslesmeyen"]:
                mesaj += (
                    f"  (Eslesmeyenler: "
                    f"{', '.join(sonuc['eslesmeyen'][:5])}"
                    f"{'...' if len(sonuc['eslesmeyen']) > 5 else ''})\n"
                )
            _mb.showinfo("Otomatik Uretim", mesaj)
            try:
                self.load_courses()
            except Exception:
                pass
            try:
                self.refresh_completion_panel()
            except Exception:
                pass
        except Exception as exc:
            _mb.showerror("Otomatik Uretim Hatasi", str(exc))

    def import_kriterler_excel(self):
        """Secili kapsam icin kriter dosyasini uygular."""
        path = filedialog.askopenfilename(
            title="Kriter Excel Seç",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Tümü", "*.*")]
        )
        if not path:
            return
        db_path = getattr(self.app, "db_path", None) if self.app else None
        if not db_path or not os.path.exists(db_path):
            messagebox.showwarning("Uyarı", "Veritabanı bağlantısı yok.")
            return
        faculty_id = self._selected_faculty_id()
        department_id = self._selected_department_id()  # eksik tanım eklendi (NameError giderildi)
        year_raw = self.cb_yil.get()
        term = self.cb_donem.get() or "Güz"
        if faculty_id is None or not year_raw:
            messagebox.showwarning("Uyarı", "Lütfen önce fakülte, yıl ve dönem seçiniz.")
            return
        try:
            result = run_criteria_import(
                db_path=db_path,
                excel_path=path,
                faculty_id=int(faculty_id),
                year=int(year_raw),
                term=term,
                department_id=int(department_id) if department_id is not None else None,
                source_filename=os.path.basename(path),
            )
            if result.get("ok"):
                messagebox.showinfo("Tamam", result.get("message", "Kriter dosyasi yuklendi."))
                self.load_courses()
                self._refresh_related_views()
            else:
                messagebox.showerror("Hata", result.get("message", "Kriter dosyasi yuklenemedi."))
        except Exception as e:
            print(f"[CriteriaPage] Import hatası: {e}")
            messagebox.showerror("Hata", self._friendly_backend_error())

    def load_faculties(self, preserve_selection=False):
        if not getattr(self.db, "conn", None):
            return
        prev_fakulte = self.cb_fakulte.get() if preserve_selection else None
        prev_bolum = self.cb_bolum.get() if preserve_selection else None
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte")
            if rows:
                values = [str(r[0]) for r in rows]
                self.cb_fakulte["values"] = values
                if prev_fakulte and prev_fakulte in values:
                    self.cb_fakulte.set(prev_fakulte)
                    self.on_faculty_change(None, _preserve_bolum=prev_bolum)
                else:
                    self.cb_fakulte.current(0)
                    self.on_faculty_change(None)
        except Exception as e:
            print(f"Fakülte yükleme hatası: {e}")

    def on_faculty_change(self, event, _preserve_bolum=None):
        fakulte = self.cb_fakulte.get()
        if not fakulte or not getattr(self.db, "conn", None):
            return
        try:
            _, res = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad=?", (fakulte,))
            if not res:
                return
            fid = res[0][0]
            self._current_fakulte_id = int(fid)  # Fakülte ID'sini sakla
            _, res_bolum = self.db.run_sql("SELECT ad FROM bolum WHERE fakulte_id=?", (fid,))
            vals = [FACULTY_SCOPE_LABEL]
            if res_bolum:
                vals.extend(str(r[0]) for r in res_bolum)
            self.cb_bolum["values"] = vals
            if _preserve_bolum and _preserve_bolum in vals:
                self.cb_bolum.set(_preserve_bolum)
            elif vals:
                self.cb_bolum.set(FACULTY_SCOPE_LABEL)
            # Bölüm değişince yıl listesini de güncelle
            self._refresh_years_for_selection()
        except Exception as e:
            print(f"Bölüm yükleme hatası: {e}")

    def _on_department_change(self, event=None):
        """Bölüm değiştiğinde yıl listesini günceller."""
        self._refresh_years_for_selection()

    def _refresh_years_for_selection(self):
        """
        Seçili fakülte/bölüm için müfredatı olan yılları yükler.
        Hard-coded yıl listesi kaldırıldı - sadece gerçek müfredat verisi kullanılıyor.
        """
        fakulte = self.cb_fakulte.get()
        bolum = self._selected_department_name()

        if not fakulte:
            self.cb_yil["values"] = []
            return

        try:
            # Fakülte ID'sini al
            _, res = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad=?", (fakulte,))
            if not res:
                self.cb_yil["values"] = []
                return
            fid = int(res[0][0])

            # Bölüm ID'sini al (varsa)
            bid = None
            if bolum:
                _, res_bol = self.db.run_sql(
                    "SELECT bolum_id FROM bolum WHERE fakulte_id=? AND ad=?",
                    (fid, bolum)
                )
                if res_bol:
                    bid = int(res_bol[0][0])

            # Müfredatı olan yılları sorgula (fakülte + bölüm bazlı)
            if bid:
                # Belirli bir bölüm için müfredat yılları
                _, rows = self.db.run_sql(
                    """
                    SELECT DISTINCT m.akademik_yil
                    FROM mufredat m
                    WHERE m.bolum_id = ?
                    ORDER BY m.akademik_yil
                    """,
                    (bid,)
                )
            else:
                # Fakültenin tüm bölümleri için müfredat yılları
                _, rows = self.db.run_sql(
                    """
                    SELECT DISTINCT m.akademik_yil
                    FROM mufredat m
                    JOIN bolum b ON b.bolum_id = m.bolum_id
                    WHERE b.fakulte_id = ?
                    ORDER BY m.akademik_yil
                    """,
                    (fid,)
                )

            years = [str(int(r[0])) for r in (rows or []) if r and r[0] is not None]

            # Mevcut seçimi koru veya en son yılı seç
            prev_year = self.cb_yil.get()
            self.cb_yil["values"] = years

            if years:
                if prev_year in years:
                    self.cb_yil.set(prev_year)
                else:
                    self.cb_yil.set(years[-1])  # En son yılı seç
            else:
                self.cb_yil.set("")

        except Exception as e:
            print(f"Yıl listesi yükleme hatası: {e}")
            self.cb_yil["values"] = []


    def load_courses(self, restore_course_id=None, show_warnings=True):
        """Fakültedeki seçmeli dersleri listeler; Güz/Bahar ve kriter filtresine göre."""
        self.tree.delete(*self.tree.get_children())

        fakulte = self.cb_fakulte.get()
        bolum = self._selected_department_name()
        yil = self.cb_yil.get()
        donem = self.cb_donem.get()
        kriter_filtre = self.cb_kriter_filtre.get()
        mufredat_filtre = getattr(self, "cb_mufredat_filtre", None)
        muf_val = (mufredat_filtre.get() or "").strip() if mufredat_filtre else ""
        sadece_mufredat = muf_val in ("Müfredattakiler", "Müfredattaki")

        if not (fakulte and yil and donem):
            if show_warnings:
                messagebox.showwarning("Eksik", "Lütfen Fakülte, Yıl ve Dönem seçiniz.")
            else:
                self.tree.insert("", tk.END, values=("", "Fakülte/Yıl/Dönem seçimi bekleniyor.", ""))
            return

        if not getattr(self.db, "conn", None):
            self.tree.insert("", tk.END, values=("", "Veritabanı bağlantısı yok.", ""))
            return

        try:
            col_tip = self._ders_tip_kolonu()
            donem_norm = "Güz" if donem == "Güz" else "Bahar"
            bolum_filter = bolum or ""

            if sadece_mufredat:
                # Mufredattaki TUM dersler (secimli + zorunlu). Eski filtre sadece secimli
                # gosterdiginden mufredatta olup DersTipi=Zorunlu kayitli dersler listede yoktu.
                query = """
                    SELECT DISTINCT d.ders_id, d.ad,
                           CASE WHEN dk.id IS NOT NULL THEN 'Girildi' ELSE 'Bos' END as durum
                    FROM mufredat m
                    JOIN bolum b ON b.bolum_id = m.bolum_id
                    JOIN fakulte f ON f.fakulte_id = b.fakulte_id
                    JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                    JOIN ders d ON d.ders_id = md.ders_id
                    LEFT JOIN ders_kriterleri dk ON (dk.ders_id = d.ders_id AND dk.yil = ?
                        AND (
                            LOWER(SUBSTR(TRIM(COALESCE(dk.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                            OR dk.donem IS NULL
                            OR dk.donem = ''
                        ))
                    WHERE f.ad = ?
                      AND (? = '' OR b.ad = ?)
                      AND m.akademik_yil = ?
                      AND LOWER(SUBSTR(TRIM(COALESCE(m.donem,'')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                    ORDER BY d.ad
                """
                _, rows = self.db.run_sql(
                    query,
                    (
                        int(yil),
                        donem_norm,
                        fakulte,
                        bolum_filter,
                        bolum_filter,
                        int(yil),
                        donem_norm,
                    ),
                )
            else:
                query = f"""
                    SELECT d.ders_id, d.ad,
                           CASE WHEN dk.id IS NOT NULL THEN 'Girildi' ELSE 'Bos' END as durum
                    FROM ders d
                    JOIN fakulte f ON d.fakulte_id = f.fakulte_id
                    LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
                    LEFT JOIN ders_kriterleri dk ON (dk.ders_id = d.ders_id AND dk.yil = ?
                        AND (
                            LOWER(SUBSTR(TRIM(COALESCE(dk.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                            OR dk.donem IS NULL
                            OR dk.donem = ''
                        ))
                    WHERE f.ad = ?
                      AND (? = '' OR b.ad = ?)
                      AND (LOWER(COALESCE(d.{col_tip},'')) LIKE '%seçmeli%'
                           OR LOWER(COALESCE(d.{col_tip},'')) LIKE '%secmeli%')
                    ORDER BY d.ad
                """
                _, rows = self.db.run_sql(
                    query,
                    (
                        int(yil),
                        donem_norm,
                        fakulte,
                        bolum_filter,
                        bolum_filter,
                    ),
                )

            # Kriter filtresi uygula
            if kriter_filtre == "Girildi":
                rows = [r for r in (rows or []) if str(r[2]) == "Girildi"]
            elif kriter_filtre == "Girilmedi":
                rows = [r for r in (rows or []) if str(r[2]) != "Girildi"]

            if not rows:
                self.tree.insert("", tk.END, values=("", "Bu kriterlere uygun ders bulunamadı.", ""))
            else:
                for r in rows:
                    vals = (int(r[0]), str(r[1]), str(r[2]))
                    self.tree.insert("", tk.END, values=vals)

            if restore_course_id is not None:
                for item_id in self.tree.get_children():
                    item_vals = self.tree.item(item_id, "values")
                    if item_vals and str(item_vals[0]) == str(restore_course_id):
                        self.tree.selection_set(item_id)
                        self.tree.see(item_id)
                        break
            try:
                self.refresh_completion_panel()
            except Exception:
                pass

        except Exception as e:
            import traceback
            print(f"[Kriter load_courses] Hata: {e}")
            traceback.print_exc()
            messagebox.showerror("Hata", f"Dersler yüklenirken hata oluştu:\n{str(e)}")

    def _has_col(self, table, col):
        try:
            cur = self.db.conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            return any(r[1] == col for r in cur.fetchall())
        except Exception:
            return False

    def _ders_tip_kolonu(self):
        """Ders tablosundaki seçmeli/zorunlu sütun adını döner (DersTipi, tip veya tur)."""
        for col in ("DersTipi", "tip", "tur"):
            if self._has_col("ders", col):
                return col
        return "DersTipi"

    def _check_in_mufredat(self, yil: int, donem: str) -> bool:
        """Ders bu yıl/dönem/bölüm müfredatında mı?"""
        bolum = self._selected_department_name()
        faculty_id = self._selected_faculty_id()
        try:
            params: list[Any] = [self.selected_course_id, int(yil), str(donem).strip()]
            department_clause = ""
            if bolum:
                department_clause = "AND b.ad = ?"
                params.append(bolum)
            elif faculty_id is not None:
                department_clause = "AND b.fakulte_id = ?"
                params.append(int(faculty_id))
            _, rows = self.db.run_sql(f"""
                SELECT 1 FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                JOIN bolum b ON m.bolum_id = b.bolum_id
                WHERE md.ders_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem,'Güz')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                  {department_clause}
                LIMIT 1
            """, tuple(params))
            return bool(rows)
        except Exception:
            return False

    def _update_form_readonly(self):
        """1 ve 2. kriterler filtreye göre açık/kilitli olur."""
          # Müfredattakiler filtresi veya ders müfredattaysa → 1 ve 2 açık
        readonly = not getattr(self, "_course_in_mufredat", True)
        state = "disabled" if readonly else "normal"
        for w in (self.ent_toplam_ogrenci, self.ent_gecen_ogrenci, self.ent_ortalama,
                  self.ent_kontenjan, self.ent_kayitli):
            w.config(state=state)

    def _set_entry_value(self, entry, value, state="normal"):
        previous_state = None
        try:
            previous_state = entry.cget("state")
        except Exception:
            previous_state = None
        try:
            entry.config(state=state)
        except Exception:
            pass
        entry.delete(0, tk.END)
        entry.insert(0, str(value))
        if previous_state is not None:
            try:
                entry.config(state=previous_state)
            except Exception:
                pass

    def _survey_record_locked(self, record: dict[str, Any] | None) -> bool:
        if not record:
            return False
        source = str(record.get("anket_veri_kaynagi") or "").strip().lower()
        locked = int(record.get("anket_manual_locked") or 0)
        return locked == 1 or source == "survey_import"

    def _apply_survey_lock_state(self, locked: bool, source_text: str | None = None):
        self._survey_locked = bool(locked)
        if locked:
            if getattr(self, "ent_anket_dersi_secen", None):
                self.ent_anket_dersi_secen.config(state="disabled")
            if getattr(self, "lbl_anket_kaynak_info", None):
                self.lbl_anket_kaynak_info.config(
                    text=source_text or "Bu alanlar belge ile dolduruldugu icin manuel duzenlemeye kapali.",
                    fg="#b45309",
                )
        else:
            if getattr(self, "ent_anket_dersi_secen", None):
                self.ent_anket_dersi_secen.config(state="normal")
            if getattr(self, "lbl_anket_kaynak_info", None):
                self.lbl_anket_kaynak_info.config(
                    text=source_text or "Anket verisi manuel girise acik.",
                    fg="#475569",
                )

    def _update_criteria_source_info(self, record: dict[str, Any] | None = None):
        if not getattr(self, "lbl_criteria_source_info", None):
            return

        summary = None
        if record and record.get("criteria_import_id") is not None:
            try:
                summary = get_criteria_import_by_id(self.db.conn, int(record.get("criteria_import_id") or 0))
            except Exception:
                summary = None
        if summary is None:
            faculty_id = self._selected_faculty_id()
            year_text = self.cb_yil.get()
            term = self.cb_donem.get() or "Güz"
            department_id = self._selected_department_id()
            if faculty_id is not None and year_text:
                try:
                    summary = get_active_criteria_import(
                        self.db.conn,
                        faculty_id=int(faculty_id),
                        year=int(year_text),
                        term=term,
                        department_id=int(department_id) if department_id is not None else None,
                    )
                except Exception:
                    summary = None

        self._current_criteria_import_summary = summary
        text = f"Aktif kriter dosyasi: {format_criteria_import_summary(summary)}"
        if record and int(record.get("criteria_manual_override") or 0) == 1:
            text += " | Bu ders icin manuel override aktif."
        elif record and str(record.get("criteria_veri_kaynagi") or "").strip().lower() == "manual":
            text += " | Bu ders manuel kriter verisi kullaniyor."
        self.lbl_criteria_source_info.config(text=text)

    def _fetch_saved_criteria_record(self, ders_id, yil, donem):
        """ders_kriterleri kaydini acik kolon adlariyla dondurur."""
        columns = [
            "donem",
            "toplam_ogrenci",
            "gecen_ogrenci",
            "basari_ortalamasi",
            "kontenjan",
            "kayitli_ogrenci",
            "anket_katilimci",
            "anket_dersi_secen",
            "anket_veri_kaynagi",
            "anket_manual_locked",
            "anket_import_id",
            "anket_imported_at",
            "criteria_import_id",
            "criteria_veri_kaynagi",
            "criteria_manual_override",
            "criteria_updated_at",
        ]
        select_parts = [
            "donem",
            "toplam_ogrenci",
            "gecen_ogrenci",
            "basari_ortalamasi",
            "kontenjan",
            "kayitli_ogrenci",
            "anket_katilimci",
            "anket_dersi_secen",
            "COALESCE(anket_veri_kaynagi, 'manual') AS anket_veri_kaynagi"
            if self._has_col("ders_kriterleri", "anket_veri_kaynagi")
            else "'manual' AS anket_veri_kaynagi",
            "COALESCE(anket_manual_locked, 0) AS anket_manual_locked"
            if self._has_col("ders_kriterleri", "anket_manual_locked")
            else "0 AS anket_manual_locked",
            "anket_import_id" if self._has_col("ders_kriterleri", "anket_import_id") else "NULL AS anket_import_id",
            "anket_imported_at"
            if self._has_col("ders_kriterleri", "anket_imported_at")
            else "NULL AS anket_imported_at",
            "criteria_import_id" if self._has_col("ders_kriterleri", "criteria_import_id") else "NULL AS criteria_import_id",
            "COALESCE(criteria_veri_kaynagi, 'manual') AS criteria_veri_kaynagi"
            if self._has_col("ders_kriterleri", "criteria_veri_kaynagi")
            else "'manual' AS criteria_veri_kaynagi",
            "COALESCE(criteria_manual_override, 0) AS criteria_manual_override"
            if self._has_col("ders_kriterleri", "criteria_manual_override")
            else "0 AS criteria_manual_override",
            "criteria_updated_at"
            if self._has_col("ders_kriterleri", "criteria_updated_at")
            else "NULL AS criteria_updated_at",
        ]
        base_query = f"""
            SELECT {", ".join(select_parts)}
            FROM ders_kriterleri
            WHERE ders_id=? AND yil=?
        """
        queries = [
            (
                base_query + " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) ORDER BY id DESC LIMIT 1",
                (int(ders_id), int(yil), str(donem).strip()),
            ),
            (
                base_query + " ORDER BY id DESC LIMIT 1",
                (int(ders_id), int(yil)),
            ),
        ]
        for query, params in queries:
            _, rows = self.db.run_sql(query, params)
            if rows:
                row = rows[0]
                return {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
        return None

    def _fetch_saved_criteria(self, ders_id, yil, donem):
        """ders_kriterleri kaydini sabit kolon sirasiyla dondurur."""
        record = self._fetch_saved_criteria_record(ders_id, yil, donem)
        if not record:
            return None
        return (
            record.get("donem"),
            record.get("toplam_ogrenci"),
            record.get("gecen_ogrenci"),
            record.get("basari_ortalamasi"),
            record.get("kontenjan"),
            record.get("kayitli_ogrenci"),
            record.get("anket_katilimci"),
            record.get("anket_dersi_secen"),
        )


    def on_course_select(self, event):
        sel = self.tree.selection()
        if not sel: return

        item = self.tree.item(sel[0])
        values = item['values']

        # GÜVENLİK KONTROLÜ 1: Değerler boş mu?
        if not values or values[0] == "":
            return  # ID yoksa veya boş satırsa işlem yapma

        try:
            # GÜVENLİK KONTROLÜ 2: ID gerçekten sayı mı?
            self.selected_course_id = int(values[0])
            course_name = values[1]
        except (ValueError, IndexError):
            # Eğer ID sayıya çevrilemiyorsa (örn: "Ders Bulunamadı" yazısıysa) çık
            self.selected_course_id = None
            self.lbl_selected_course.config(text="Geçersiz seçim.", fg="red")
            return

        yil = self.cb_yil.get()
        # Yıl seçili değilse hata vermesin, varsayılanı korusun
        if not yil:
            messagebox.showwarning("Uyarı", "Lütfen bir yıl seçiniz.")
            return

        donem = self.cb_donem.get() or "Güz"
        self.lbl_selected_course.config(text=f"Seçilen: {course_name} ({yil} {donem})", fg="#0f172a")

        # Müfredattakiler filtresi seçiliyse liste zaten müfredat dersleri → 1 ve 2 açık
        # Değilse sadece bu ders müfredattaysa 1 ve 2 açık.
        muf_filtre = getattr(self, "cb_mufredat_filtre", None)
        muf_val = (muf_filtre.get() or "").strip() if muf_filtre else ""
        if muf_val in ("Müfredattakiler", "Müfredattaki"):
            self._course_in_mufredat = True  # Listelenen dersler müfredatta
        else:
            self._course_in_mufredat = self._check_in_mufredat(int(yil), donem)
        self._update_form_readonly()

        # Mevcut veriyi çek: ders_kriterleri (donem eşleşmeli; NULL/boş eski kayıtlar her iki dönemde)
        try:
            saved_record = self._fetch_saved_criteria_record(self.selected_course_id, int(yil), donem)
            self._current_survey_record = saved_record
            self._update_criteria_source_info(saved_record)

            if saved_record:
                self.cb_donem.set("Bahar" if str(saved_record.get("donem") or "").lower().startswith("b") else "Güz")
                self.ent_toplam_ogrenci.delete(0, tk.END)
                self.ent_toplam_ogrenci.insert(0, str(saved_record.get("toplam_ogrenci") or 0))
                self.ent_gecen_ogrenci.delete(0, tk.END)
                self.ent_gecen_ogrenci.insert(0, str(saved_record.get("gecen_ogrenci") or 0))
                self.ent_ortalama.delete(0, tk.END)
                self.ent_ortalama.insert(0, str(saved_record.get("basari_ortalamasi") or 0.0))
                self.ent_kontenjan.delete(0, tk.END)
                self.ent_kontenjan.insert(0, str(saved_record.get("kontenjan") or 0))
                self.ent_kayitli.delete(0, tk.END)
                self.ent_kayitli.insert(0, str(saved_record.get("kayitli_ogrenci") or 0))
                self._set_entry_value(self.ent_anket_katilimci, saved_record.get("anket_katilimci") or 0, state="normal")
                self.ent_anket_katilimci.config(state="disabled")
                self._set_entry_value(self.ent_anket_dersi_secen, saved_record.get("anket_dersi_secen") or 0, state="normal")

                if self._survey_record_locked(saved_record):
                    imported_at = saved_record.get("anket_imported_at")
                    import_message = "Bu alanlar belge ile dolduruldugu icin manuel duzenlemeye kapali."
                    if imported_at:
                        import_message += f" Son yukleme: {imported_at}."
                    self._apply_survey_lock_state(True, import_message)
                else:
                    self._apply_survey_lock_state(False)
            else:
                self._current_survey_record = None
                self._update_criteria_source_info(None)
                # ders_kriterleri yoksa performans+populerlikten doldur
                _, pr = self.db.run_sql(
                    "SELECT ortalama_not, basari_orani FROM performans WHERE ders_id=? AND akademik_yil=? LIMIT 1",
                    (self.selected_course_id, int(yil))
                )
                _, po = self.db.run_sql(
                    "SELECT talep_sayisi, kontenjan FROM populerlik WHERE ders_id=? AND akademik_yil=? LIMIT 1",
                    (self.selected_course_id, int(yil))
                )
                if pr and po:
                    ort = float(pr[0][0] or 0)
                    basari = float(pr[0][1] or 0)
                    talep = int(po[0][0] or 0)
                    kont = int(po[0][1] or 50)
                    top_ogr = max(talep, int(talep / (basari or 0.01)) if basari else talep)
                    gecen = int(top_ogr * basari) if basari else 0
                    self.ent_toplam_ogrenci.delete(0, tk.END)
                    self.ent_toplam_ogrenci.insert(0, str(top_ogr))
                    self.ent_gecen_ogrenci.delete(0, tk.END)
                    self.ent_gecen_ogrenci.insert(0, str(gecen))
                    self.ent_ortalama.delete(0, tk.END)
                    self.ent_ortalama.insert(0, f"{ort:.1f}")
                    self.ent_kontenjan.delete(0, tk.END)
                    self.ent_kontenjan.insert(0, str(kont))
                    self.ent_kayitli.delete(0, tk.END)
                    self.ent_kayitli.insert(0, str(top_ogr))
                    self._set_entry_value(self.ent_anket_katilimci, top_ogr, state="normal")
                    self.ent_anket_katilimci.config(state="disabled")
                    self.ent_anket_dersi_secen.delete(0, tk.END)
                    self.ent_anket_dersi_secen.insert(0, "0")
                else:
                    self.clear_form_inputs()

                    # Kayıtlı öğrenci sayısı ve anket katılımcı sayısı toplama eşit tutulur.
                    self.ent_kayitli.delete(0, tk.END)
                    self.ent_kayitli.insert(0, self.ent_toplam_ogrenci.get().strip() or "0")
                    self._set_entry_value(self.ent_anket_katilimci, self.ent_toplam_ogrenci.get().strip() or "0", state="normal")
                    self.ent_anket_katilimci.config(state="disabled")
                self._apply_survey_lock_state(False)

            self.update_calculations()

        except Exception as e:
            import traceback
            print(f"[Kriter on_course_select] Veri çekme hatası: {e}")
            traceback.print_exc()
            messagebox.showerror("Hata", f"Veri okunurken hata oluştu: {e}")

    def clear_form_inputs(self):
        """Formu güvenli şekilde temizler"""
        self._current_survey_record = None
        self._current_criteria_import_summary = None
        self.ent_toplam_ogrenci.delete(0, tk.END); self.ent_toplam_ogrenci.insert(0, "0")
        self.ent_gecen_ogrenci.delete(0, tk.END); self.ent_gecen_ogrenci.insert(0, "0")
        self.ent_ortalama.delete(0, tk.END); self.ent_ortalama.insert(0, "0.0")
        self.ent_kontenjan.delete(0, tk.END); self.ent_kontenjan.insert(0, "0")
        self.ent_kayitli.delete(0, tk.END); self.ent_kayitli.insert(0, "0")
        self._set_entry_value(self.ent_anket_katilimci, "0", state="normal")
        self.ent_anket_katilimci.config(state="disabled")
        self.ent_anket_dersi_secen.delete(0, tk.END); self.ent_anket_dersi_secen.insert(0, "0")
        self.lbl_anket_sonuc.config(text="-")
        if getattr(self, "lbl_criteria_source_info", None):
            self.lbl_criteria_source_info.config(text="Aktif kriter dosyasi: -")
        self._apply_survey_lock_state(False)

    def update_calculations(self, event=None):
        """Kullanıcı sayı girdikçe oranları anlık gösterir."""
        try:
            toplam = float(self.ent_toplam_ogrenci.get())
            kayitli = toplam
            kayitli_text = str(int(kayitli) if kayitli.is_integer() else kayitli)
            self._set_entry_value(self.ent_kayitli, kayitli_text, state="normal")
            if not self._survey_locked:
                self._set_entry_value(self.ent_anket_katilimci, kayitli_text, state="normal")
                self.ent_anket_katilimci.config(state="disabled")

            gecen = float(self.ent_gecen_ogrenci.get())
            if toplam > 0:
                basari = (gecen / toplam) * 100
                self.lbl_basari_sonuc.config(text=f"%{basari:.1f}", fg="green")
            else:
                self.lbl_basari_sonuc.config(text="-")

            kontenjan = float(self.ent_kontenjan.get())
            if kontenjan > 0:
                doluluk = (kayitli / kontenjan) * 100
                self.lbl_doluluk_sonuc.config(text=f"%{doluluk:.1f}", fg="blue")
            else:
                self.lbl_doluluk_sonuc.config(text="-")

            anket_kat = float(self.ent_anket_katilimci.get() or 0)
            anket_secen = float(self.ent_anket_dersi_secen.get() or 0)
            if anket_kat > 0:
                oran = min(100.0, (anket_secen / anket_kat) * 100)
                self.lbl_anket_sonuc.config(text=f"%{oran:.1f}", fg="#7c3aed")
            else:
                self.lbl_anket_sonuc.config(text="-")
        except ValueError:
            pass

    def save_data(self):
        # UI Form Validation
        if not self.selected_course_id:
            messagebox.showwarning("Uyarı", "Lütfen önce listeden işlem yapılacak dersi seçiniz.")
            return

        if not self.cb_yil.get():
            messagebox.showerror("Eksik Alan", "Lütfen akademik yıl seçiniz.")
            self.cb_yil.focus()
            return

        if not self.cb_donem.get():
            messagebox.showerror("Eksik Alan", "Lütfen dönem seçiniz.")
            self.cb_donem.focus()
            return

        if not self._selected_faculty_id():
            messagebox.showerror("Eksik Alan", "Lütfen fakülte seçiniz.")
            self.cb_fakulte.focus()
            return

        yil = int(self.cb_yil.get())
        donem = (self.cb_donem.get() or "Güz").strip()
        donem_db = "Bahar" if str(donem).lower().startswith("b") else "Güz"
        in_mufredat = getattr(self, "_course_in_mufredat", True)

        try:
            c_id = int(self.selected_course_id)
            existing_record = self._fetch_saved_criteria_record(c_id, yil, donem)
            survey_locked = self._survey_record_locked(existing_record)
            top_ogr = gecen = ort = kont = kayit = 0
            if in_mufredat:
                top_ogr = int(self.ent_toplam_ogrenci.get().strip() or 0)
                gecen = int(self.ent_gecen_ogrenci.get().strip() or 0)
                ort = float(self.ent_ortalama.get().strip() or 0.0)
                kont = int(self.ent_kontenjan.get().strip() or 0)
                kayit = top_ogr
                # Kayıt öncesi temel iş kuralı doğrulaması (hatalı veri kaydını baştan engelle).
                if top_ogr < 0 or gecen < 0 or kont < 0:
                    messagebox.showerror("Geçersiz Veri", "Öğrenci ve kontenjan sayıları negatif olamaz.")
                    return
                if gecen > top_ogr:
                    messagebox.showerror(
                        "Geçersiz Veri",
                        "Dersi geçen öğrenci sayısı, dersi alan toplam öğrenciden fazla olamaz.",
                    )
                    return
                if not (0.0 <= ort <= 100.0):
                    messagebox.showerror("Geçersiz Veri", "Ders not ortalaması 0-100 aralığında olmalıdır.")
                    return

            if survey_locked and existing_record:
                ank_kat = int(existing_record.get("anket_katilimci") or 0)
                ank_sec = int(existing_record.get("anket_dersi_secen") or 0)
                anket_veri_kaynagi = str(existing_record.get("anket_veri_kaynagi") or "survey_import")
                anket_manual_locked = int(existing_record.get("anket_manual_locked") or 1)
                anket_import_id = existing_record.get("anket_import_id")
                anket_imported_at = existing_record.get("anket_imported_at")
            else:
                ank_kat = int(self.ent_anket_katilimci.get().strip() or 0)
                ank_sec = int(self.ent_anket_dersi_secen.get().strip() or 0)
                anket_veri_kaynagi = "manual"
                anket_manual_locked = 0
                anket_import_id = None
                anket_imported_at = None

            if existing_record and existing_record.get("criteria_import_id") is not None:
                criteria_import_id = existing_record.get("criteria_import_id")
                criteria_veri_kaynagi = "manual_override"
                criteria_manual_override = 1
            else:
                criteria_import_id = None
                criteria_veri_kaynagi = "manual"
                criteria_manual_override = 0
            criteria_updated_at = self._now_utc()

            basari_orani = (gecen / top_ogr) if top_ogr > 0 else 0.0
            doluluk_orani = min(kayit / kont, 1.0) if kont > 0 else 0.0

            cur = self.db.conn.cursor()

            # ── 1. ders_kriterleri ──
            cur.execute(
                """
                SELECT id
                FROM ders_kriterleri
                WHERE ders_id = ?
                  AND yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY id DESC
                LIMIT 1
                """,
                (c_id, yil, donem_db),
            )
            existing_row = cur.fetchone()
            if existing_row:
                cur.execute(
                    """
                    UPDATE ders_kriterleri
                    SET donem = ?,
                        toplam_ogrenci = ?,
                        gecen_ogrenci = ?,
                        basari_ortalamasi = ?,
                        kontenjan = ?,
                        kayitli_ogrenci = ?,
                        anket_katilimci = ?,
                        anket_dersi_secen = ?,
                        anket_veri_kaynagi = ?,
                        anket_manual_locked = ?,
                        anket_import_id = ?,
                        anket_imported_at = ?,
                        criteria_import_id = ?,
                        criteria_veri_kaynagi = ?,
                        criteria_manual_override = ?,
                        criteria_updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        donem_db,
                        top_ogr,
                        gecen,
                        ort,
                        kont,
                        kayit,
                        ank_kat,
                        ank_sec,
                        anket_veri_kaynagi,
                        anket_manual_locked,
                        anket_import_id,
                        anket_imported_at,
                        criteria_import_id,
                        criteria_veri_kaynagi,
                        criteria_manual_override,
                        criteria_updated_at,
                        int(existing_row[0]),
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO ders_kriterleri
                        (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
                         basari_ortalamasi, kontenjan, kayitli_ogrenci,
                         anket_katilimci, anket_dersi_secen, anket_veri_kaynagi,
                         anket_manual_locked, anket_import_id, anket_imported_at,
                         criteria_import_id, criteria_veri_kaynagi, criteria_manual_override, criteria_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        c_id,
                        yil,
                        donem_db,
                        top_ogr,
                        gecen,
                        ort,
                        kont,
                        kayit,
                        ank_kat,
                        ank_sec,
                        anket_veri_kaynagi,
                        anket_manual_locked,
                        anket_import_id,
                        anket_imported_at,
                        criteria_import_id,
                        criteria_veri_kaynagi,
                        criteria_manual_override,
                        criteria_updated_at,
                    ),
                )
            # performans + populerlik HER durumda (update VEYA insert) güncellenir.
            # Eski sürümde bu yazımlar yalnızca insert dalındaydı; mevcut bir kaydı
            # güncellerken algoritmanın okuduğu performans/populerlik tabloları eski
            # kalıyor, karar motoru güncel olmayan veriyle çalışabiliyordu.
            cur.execute(
                "DELETE FROM performans WHERE ders_id=? AND akademik_yil=? AND donem=?",
                (c_id, yil, donem_db),
            )
            cur.execute(
                """
                INSERT INTO performans
                    (ders_id, akademik_yil, donem, ortalama_not, basari_orani)
                VALUES (?, ?, ?, ?, ?)
                """,
                (c_id, yil, donem_db, ort, basari_orani),
            )
            cur.execute(
                "DELETE FROM populerlik WHERE ders_id=? AND akademik_yil=? AND donem=?",
                (c_id, yil, donem_db),
            )
            cur.execute(
                """
                INSERT INTO populerlik
                    (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (c_id, yil, donem_db, kayit, kont, doluluk_orani),
            )

            self.db.conn.commit()
            try:
                from app.utils.logger import log_operation
                log_operation("Kriter kaydedildi", f"ders_id={c_id} yil={yil}", success=True)
            except Exception:
                pass

            status_messages = []
            try:
                faculty_id = self._selected_faculty_id()
                department_id = self._selected_department_id()
                if faculty_id is not None:
                    status_result = mark_criteria_status(
                        conn=self.db.conn,
                        yil=int(yil),
                        fakulte_id=int(faculty_id),
                        bolum_id=int(department_id) if department_id is not None else None,
                    )
                    status_messages = [
                        str(msg)
                        for msg in (status_result.get("messages") or [])
                        if msg
                    ]
            except Exception as status_exc:
                status_messages = [f"Kriter durum guncelleme uyarisi: {status_exc}"]

            msg = "Veriler kaydedildi."
            if in_mufredat:
                msg += f"\nBaşarı oranı: %{basari_orani*100:.1f}  |  Doluluk: %{doluluk_orani*100:.1f}"
            else:
                msg += "\n(Müfredatta olmayan ders – yalnızca temel kriterler kaydedildi.)"
            if survey_locked:
                msg += "\nAnket alanlari belge ile dolduruldugu icin mevcut anket verisi korunarak kaydedildi."
            if int(criteria_manual_override or 0) == 1:
                msg += "\nBu ders icin kriter dosyasi uzerine manuel override kaydedildi."
            if status_messages:
                msg += "\n\n" + "\n".join(status_messages)
            messagebox.showinfo("Başarılı", msg)
            self.load_courses(restore_course_id=c_id)
            # Tüm ilgili sekmeleri yenile (tab_view dahil)
            self._refresh_related_views(restore_course_id=c_id)

        except ValueError:
            messagebox.showerror("Hata", "Lütfen sayısal alanlara sadece rakam giriniz!")
        except Exception as e:
            import traceback
            print(f"[Kriter Kaydet] SQL Hatası: {e}")
            traceback.print_exc()
            messagebox.showerror("Kritik Hata", f"Veritabanına yazılamadı:\n{e}")

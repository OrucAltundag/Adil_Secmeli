# -*- coding: utf-8 -*-
"""Tkinter Decision Center page."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app.services.ahp_profile_service import (
    activate_ahp_profile,
    create_ahp_profile,
    list_ahp_profiles,
)
from app.services.calculation import run_all_algorithms_for_year
from app.services.criteria_completion_service import can_run_algorithm
from app.services.criteria_override_service import request_override
from app.services.decision_policy_service import (
    activate_decision_policy,
    create_decision_policy,
    list_decision_policies,
)
from app.services.decision_run_service import list_course_decisions, list_decision_runs
from app.services.ml_prediction_service import get_predictions_for_course
from app.services.pool_state_machine_service import (
    approve_state_approval,
    get_course_state_history,
    get_pool_lifecycle_summary,
    list_pending_approvals,
    list_state_transitions,
    reject_state_approval,
)
from app.services.service_factory import get_service_factory

def _status_text(status: int | None) -> str:
    labels = {1: "Müfredatta", 0: "Havuzda", -1: "Dinlenmede", -2: "Kalıcı iptal"}
    try:
        return labels.get(int(status), "Belirsiz")
    except (TypeError, ValueError):
        return "Belirsiz"


def _lifecycle_text(label: str | None) -> str:
    labels = {
        "curriculum": "Müfredat",
        "pool": "Havuz",
        "resting": "Dinlenmede",
        "cancel_candidate": "İptal adayı",
        "permanently_cancelled": "Kalıcı iptal",
        "under_review": "İncelemede",
        "protected": "Korumalı",
        "reactivation_candidate": "Yeniden açılma adayı",
    }
    return labels.get(str(label or ""), str(label or "Belirsiz"))


class DecisionCenterPage(ttk.Frame):
    """Karar Merkezi: AHP, policy, runs, course decisions and reports."""

    def __init__(self, parent, app, service_factory=None):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.service_factory = service_factory or get_service_factory(
            conn=getattr(self.db, "conn", None),
            db_path=getattr(app, "db_path", None),
            config=getattr(app, "app_config", None),
        )
        self._faculty_map: dict[str, int] = {}
        self._department_map: dict[str, int] = {}
        self._run_ids: dict[str, int] = {}
        self._decision_ids: dict[str, int] = {}
        self._pool_transition_rows: dict[str, dict] = {}
        self._pool_approval_ids: dict[str, int] = {}
        self._action_buttons: list[ttk.Button] = []

        self._build_filters()
        self.sub_nb = ttk.Notebook(self)
        self.sub_nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self._build_readiness_tab()
        self._build_ahp_tab()
        self._build_policy_tab()
        self._build_runs_tab()
        self._build_course_tab()
        self._build_pool_lifecycle_tab()
        self._build_sensitivity_tab()
        self._build_approvals_tab()
        self._build_fairness_tab()

    def _conn(self):
        conn = getattr(self.db, "conn", None)
        if conn is None:
            raise RuntimeError(self._friendly_backend_error())
        return conn

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Sistem şu anda işlem yapamıyor. Lütfen daha sonra tekrar deneyin."

    def _tab_info(self, parent, baslik, ne_ise_yarar, veri_kaynagi, ne_yapmali, renk="#1565C0"):
        """Her sekmenin üstüne; amaç, veri kaynağı ve yapılacak işi açıklayan bilgi kutusu."""
        box = tk.Frame(parent, bg=renk)
        box.pack(fill=tk.X, pady=(0, 8))
        inner = tk.Frame(box, bg="#F4F8FE")
        inner.pack(fill=tk.X, padx=2, pady=2)

        tk.Label(
            inner, text=baslik, bg="#F4F8FE", fg=renk,
            font=("Segoe UI", 10, "bold"), anchor=tk.W,
        ).pack(fill=tk.X, padx=10, pady=(6, 3))

        tk.Label(
            inner, text="Ne işe yarar:  " + ne_ise_yarar,
            bg="#F4F8FE", fg="#2A2A2A", font=("Segoe UI", 8),
            anchor=tk.W, justify=tk.LEFT, wraplength=1180,
        ).pack(fill=tk.X, padx=10, pady=1)

        tk.Label(
            inner, text="Veri kaynağı:  " + veri_kaynagi,
            bg="#FFF6DF", fg="#6B4E00", font=("Segoe UI", 8, "bold"),
            anchor=tk.W, justify=tk.LEFT, wraplength=1180,
        ).pack(fill=tk.X, padx=10, pady=3, ipady=2)

        tk.Label(
            inner, text="Ne yapmalısınız:  " + ne_yapmali,
            bg="#F4F8FE", fg="#1B5E20", font=("Segoe UI", 8),
            anchor=tk.W, justify=tk.LEFT, wraplength=1180,
        ).pack(fill=tk.X, padx=10, pady=(1, 6))

    def _build_filters(self):
        bar = ttk.LabelFrame(self, text="Filtreler", padding=8)
        bar.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(bar, text="Yıl").pack(side=tk.LEFT)
        self.cb_year = ttk.Combobox(bar, width=8, state="readonly")
        self.cb_year.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(bar, text="Fakülte").pack(side=tk.LEFT)
        self.cb_faculty = ttk.Combobox(bar, width=26, state="readonly")
        self.cb_faculty.pack(side=tk.LEFT, padx=(4, 12))
        self.cb_faculty.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(bar, text="Bölüm").pack(side=tk.LEFT)
        self.cb_department = ttk.Combobox(bar, width=26, state="readonly")
        self.cb_department.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(bar, text="Dönem").pack(side=tk.LEFT)
        self.cb_semester = ttk.Combobox(bar, width=10, state="readonly", values=["Guz", "Bahar"])
        self.cb_semester.set("Guz")
        self.cb_semester.pack(side=tk.LEFT, padx=(4, 12))
        self.cb_semester.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(bar, text="Run").pack(side=tk.LEFT)
        self.cb_run = ttk.Combobox(bar, width=34, state="readonly")
        self.cb_run.pack(side=tk.LEFT, padx=(4, 12))
        self.cb_run.bind("<<ComboboxSelected>>", lambda _e: self._load_run_related())
        self.cb_year.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Button(bar, text="Yenile", command=self.refresh).pack(side=tk.RIGHT)

    def _build_ahp_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="AHP Profilleri")
        self._tab_info(
            frame,
            "AHP Profilleri — Kriter Ağırlıkları",
            "Karar algoritmasının her kritere (başarı, trend, popülerlik, anket) ne kadar "
            "önem vereceğini belirleyen ağırlık profillerini listeler. Karar çalıştırılmadan "
            "önce mutlaka tutarlı (CR ≤ 0.10) ve AKTİF bir profil olmalıdır.",
            "ahp_weight_profiles tablosu. Profiller 'AHP Ağırlık Yönetimi' ana sekmesinde "
            "ikili karşılaştırma matrisi ile oluşturulur; buradan yalnızca listelenir ve aktif yapılır.",
            "Listede tutarlı bir profil yoksa 'Yeni Varsayılan Profil' ile oluşturun, "
            "ardından 'Seçileni Aktif Yap' butonuna basın.",
        )
        columns = ("id", "ad", "kapsam", "yil", "agirliklar", "cr", "tutarlı", "aktif")
        self.tree_ahp = self._tree(frame, columns)
        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=6)
        ttk.Button(actions, text="Yeni Varsayılan Profil", command=self._create_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Seçileni Aktif Yap", command=self._activate_profile).pack(side=tk.LEFT, padx=4)
        self.lbl_ahp_warning = ttk.Label(actions, text="")
        self.lbl_ahp_warning.pack(side=tk.LEFT, padx=12)

    def _build_readiness_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="Hazırlık Kontrolü")
        self._tab_info(
            frame,
            "Hazırlık Kontrolü — Algoritma Çalışmaya Hazır mı?",
            "Seçili yıl/fakülte/dönem için kriter verilerinin yeterince dolu ve geçerli olup "
            "olmadığını denetler. Tamlık oranı eşiğin altındaysa karar algoritması ÇALIŞTIRILAMAZ. "
            "Bu sekme, hatalı/eksik veriyle yanlış karar üretilmesini engelleyen güvenlik kapısıdır.",
            "criteria_completion_matrix, criteria_validation_issues, criteria_missing_data_risks "
            "tabloları. Bu veriler 'Veri Yönetimi' sekmesinden kriter Excel'i içe aktarılarak doldurulur.",
            "Yıl ve Fakülte seçip 'Hazırlığı Yenile' deyin. 'Engellendi' görüyorsanız eksik "
            "kriterleri içe aktarın veya geçerli gerekçeyle 'Override Talep Et' kullanın.",
            renk="#E65100",
        )
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(top, text="Hazırlığı Yenile", command=self._load_readiness).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Override Talep Et", command=self._request_readiness_override).pack(side=tk.LEFT, padx=4)
        self.lbl_readiness = ttk.Label(top, text="")
        self.lbl_readiness.pack(side=tk.LEFT, padx=12)
        self.txt_readiness = tk.Text(frame, height=18, wrap=tk.WORD)
        self.txt_readiness.pack(fill=tk.BOTH, expand=True)

    def _build_policy_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="Karar Politikaları")
        self._tab_info(
            frame,
            "Karar Politikaları — Eşik Değerleri ve Kurallar",
            "Bir dersin TOPSIS skoruna göre hangi statüye geçeceğini belirleyen eşikleri tutar: "
            "müfredatta kalma eşiği, havuza düşme, dinlenmeye alma, iptal adayı eşiği ve "
            "iptal için manuel onay gerekip gerekmediği. Karar çalıştırmadan önce AKTİF bir politika olmalıdır.",
            "decision_policies tablosu. Politikalar bu sekmede oluşturulur (içe aktarma gerekmez); "
            "değerler kurum kurallarınıza göre belirlenir.",
            "Aktif politika yoksa 'Yeni Varsayılan Politika' oluşturun ve 'Seçileni Aktif Yap' deyin. "
            "Eşikleri kurumunuzun kurallarına göre düzenleyin.",
            renk="#6A1B9A",
        )
        columns = ("id", "ad", "kapsam", "yil", "mod", "müfredat", "havuz", "dinlenme", "iptal", "onay", "aktif")
        self.tree_policy = self._tree(frame, columns)
        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=6)
        ttk.Button(actions, text="Yeni Varsayılan Politika", command=self._create_policy).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Seçileni Aktif Yap", command=self._activate_policy).pack(side=tk.LEFT, padx=4)

    def _build_runs_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="Çalıştırmalar")
        self._tab_info(
            frame,
            "Çalıştırmalar — Karar Motorunun Çalıştırılması",
            "Bu sekme tüm Karar Merkezi'nin KALBİDİR. 'Yeni Karar Çalıştır' butonu; AHP ağırlıkları "
            "+ aktif politika + kriter verilerini kullanarak TOPSIS algoritmasını çalıştırır ve her ders "
            "için karar üretir. Üretilen kayıtlar diğer 6 sekmeyi (Ders Kararları, Havuz, Hassas, "
            "Akademik Onay, Adalet) besler.",
            "decision_runs tablosu. Bu tablo yalnızca 'Yeni Karar Çalıştır' butonuyla dolar — "
            "önkoşul: hazırlık 'Hazır' + aktif AHP profili + aktif politika + müfredat/ders verisi.",
            "Üstten Yıl/Fakülte/Dönem seçin, 'Yeni Karar Çalıştır' deyin. Çalıştırma tamamlanınca "
            "satıra tıklayıp diğer sekmelerde sonuçları inceleyin.",
            renk="#1B5E20",
        )
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 6))
        self.btn_execute_run = ttk.Button(top, text="Yeni Karar Çalıştır", command=self._execute_run)
        self.btn_execute_run.pack(side=tk.LEFT)
        self._action_buttons.append(self.btn_execute_run)
        self.tree_runs = self._tree(
            frame,
            ("id", "yil", "fakülte", "dönem", "durum", "ahp", "politika", "başlangıç"),
        )
        self.tree_runs.bind("<<TreeviewSelect>>", lambda _e: self._select_run_from_tree())

    def _build_course_tab(self):
        frame = ttk.PanedWindow(self.sub_nb, orient=tk.VERTICAL)
        self.sub_nb.add(frame, text="Ders Kararları")
        top = ttk.Frame(frame, padding=8)
        bottom = ttk.LabelFrame(frame, text="Ders Detayı ve Açıklama", padding=8)
        frame.add(top, weight=3)
        frame.add(bottom, weight=2)
        self._tab_info(
            top,
            "Ders Kararları — Her Ders İçin Üretilen Karar",
            "Seçili karar çalıştırması için ders ders sonuçları gösterir: eski statü, algoritmanın "
            "önerdiği statü, final statü, TOPSIS skoru, trend, veri güveni ve gerekçe. Bir satıra "
            "tıklayınca altta kriter kırılımı, ML destekleyici tahmin ve insan-okur açıklama görünür.",
            "course_decisions + course_score_breakdowns + course_trend_analysis + "
            "course_decision_explanations tabloları. Hepsi 'Çalıştırmalar' sekmesindeki karar "
            "çalıştırması ile otomatik üretilir — ayrı içe aktarma gerekmez.",
            "Üstteki 'Run' filtresinden bir çalıştırma seçin. Boşsa önce 'Çalıştırmalar' "
            "sekmesinde karar çalıştırın.",
            renk="#00838F",
        )
        self.tree_courses = self._tree(
            top,
            ("id", "kod", "ders", "eski", "öneri", "final", "skor", "trend", "güven", "stabilite", "onay", "gerekçe"),
        )
        self.tree_courses.bind("<<TreeviewSelect>>", lambda _e: self._show_course_detail())
        self.txt_course_detail = tk.Text(bottom, height=10, wrap=tk.WORD)
        self.txt_course_detail.pack(fill=tk.BOTH, expand=True)

    def _build_pool_lifecycle_tab(self):
        frame = ttk.PanedWindow(self.sub_nb, orient=tk.VERTICAL)
        self.sub_nb.add(frame, text="Havuz Yaşam Döngüsü")

        top = ttk.Frame(frame, padding=8)
        bottom = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        frame.add(top, weight=3)
        frame.add(bottom, weight=2)

        self._tab_info(
            top,
            "Havuz Yaşam Döngüsü — Derslerin Statü Geçiş Geçmişi",
            "Derslerin müfredat ↔ havuz ↔ dinlenme ↔ iptal arasındaki geçişlerini, hangi kuralın "
            "uygulandığını ve sayaç değişimlerini gösterir. Sağ altta manuel onay bekleyen kritik "
            "kararlar (ör. kalıcı iptal) listelenir ve buradan onaylanıp reddedilebilir.",
            "course_state_transitions + course_state_approvals tabloları. Karar çalıştırması + "
            "havuz durum makinesi (pool_state_policies) tarafından otomatik üretilir.",
            "Yıl/Fakülte/Dönem seçip 'Yaşam Döngüsünü Yenile' deyin. Onay bekleyen kaydı seçip "
            "'Onayla' / 'Reddet' butonlarıyla karara bağlayın.",
            renk="#AD1457",
        )
        actions = ttk.Frame(top)
        actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(actions, text="Yaşam Döngüsünü Yenile", command=self._load_pool_lifecycle).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Havuzdan Öner", command=self._havuzdan_oner).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Otomatik Karar Önerisi", command=self._otomatik_karar).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="ML Analiz (p-value/SHAP/LIME)", command=self._ml_analiz).pack(side=tk.LEFT, padx=4)
        self.lbl_pool_lifecycle = ttk.Label(actions, text="")
        self.lbl_pool_lifecycle.pack(side=tk.LEFT, padx=12)
        self.tree_pool_lifecycle = self._tree(
            top,
            ("id", "kod", "ders", "eski", "öneri", "final", "etiket", "skor", "trend", "güven", "onay", "gerekçe"),
        )
        self.tree_pool_lifecycle.bind("<<TreeviewSelect>>", lambda _e: self._show_pool_lifecycle_detail())

        detail = ttk.LabelFrame(bottom, text="Durum Geçmişi ve Gerekçe", padding=8)
        approvals = ttk.LabelFrame(bottom, text="Onay Bekleyen Kararlar", padding=8)
        bottom.add(detail, weight=2)
        bottom.add(approvals, weight=2)

        self.txt_pool_lifecycle_detail = tk.Text(detail, height=10, wrap=tk.WORD)
        self.txt_pool_lifecycle_detail.pack(fill=tk.BOTH, expand=True)

        self.tree_pool_approvals = self._tree(
            approvals,
            ("id", "kod", "ders", "istenen", "mevcut", "tip", "durum", "gerekçe"),
        )
        approval_buttons = ttk.Frame(approvals)
        approval_buttons.pack(fill=tk.X, pady=6)
        ttk.Button(approval_buttons, text="Onayla", command=self._approve_pool_state).pack(side=tk.LEFT, padx=4)
        ttk.Button(approval_buttons, text="Reddet", command=self._reject_pool_state).pack(side=tk.LEFT, padx=4)

    def _build_sensitivity_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="Hassas Kararlar")
        self._tab_info(
            frame,
            "Hassas Kararlar — Riske Açık / Kırılgan Sonuçlar",
            "Ağırlıklar biraz değişse kararı değişebilecek 'sınırda' dersleri gösterir. "
            "Düşük stabilite = küçük veri/ağırlık oynamasında karar tersine dönebilir; bu dersler "
            "ekstra incelenmelidir. min/max skor ve aralık genişliği duyarlılığı ölçer.",
            "decision_sensitivity_results tablosu. 'Çalıştırmalar' sekmesindeki karar çalıştırması "
            "sırasında duyarlılık analizi ile otomatik üretilir.",
            "Üstteki 'Run' filtresinden çalıştırma seçin. 'low' stabiliteli dersleri öncelikli "
            "olarak Akademik Onay'a yönlendirin.",
            renk="#C62828",
        )
        self.tree_sensitivity = self._tree(
            frame,
            ("ders", "skor", "min", "max", "aralık", "stabilite", "açıklama"),
        )

    def _build_approvals_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="Akademik Onay")
        self._tab_info(
            frame,
            "Akademik Onay — Manuel Karar Gerektiren Dersler",
            "Algoritmanın kendi başına karara bağlamadığı, insan onayı isteyen dersleri listeler "
            "(düşük veri güveni, kritik statü değişimi veya politika gereği). Bunlar akademik "
            "kurul tarafından gözden geçirilmelidir.",
            "course_decisions tablosunda approval_required = 1 olan kayıtlar. Karar çalıştırması "
            "ile otomatik işaretlenir.",
            "Üstteki 'Run' filtresinden çalıştırma seçin. Düşük güvenli kararları kurulda "
            "değerlendirip nihai statüyü 'Havuz Yaşam Döngüsü' sekmesinden onaylayın.",
            renk="#E65100",
        )
        self.tree_approvals = self._tree(
            frame,
            ("kod", "ders", "öneri", "final", "güven", "durum", "gerekçe"),
        )

    def _build_fairness_tab(self):
        frame = ttk.Frame(self.sub_nb, padding=8)
        self.sub_nb.add(frame, text="Adalet Raporu")
        self._tab_info(
            frame,
            "Adalet Raporu — Kararların Yanlılık Denetimi",
            "Üretilen kararların belirli grupları (fakülte, bölüm, ders türü) sistematik olarak "
            "kayırıp kayırmadığını ölçer. Şeffaflık ve hesap verebilirlik için; kararların "
            "savunulabilir ve dengeli olduğunu kanıtlayan rapordur.",
            "decision_fairness_reports tablosu. Her karar çalıştırması sonunda otomatik üretilir.",
            "Üstteki 'Run' filtresinden bir çalıştırma seçin; rapor otomatik yüklenir. "
            "Dengesizlik uyarısı varsa AHP ağırlıklarını gözden geçirin.",
            renk="#283593",
        )
        self.txt_fairness = tk.Text(frame, height=18, wrap=tk.WORD)
        self.txt_fairness.pack(fill=tk.BOTH, expand=True)

    def _tree(self, parent, columns):
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(wrapper, columns=columns, show="headings", height=10)
        vsb = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=tree.yview)
        hsb = ttk.Scrollbar(wrapper, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        wrapper.columnconfigure(0, weight=1)
        wrapper.rowconfigure(0, weight=1)
        for column in columns:
            tree.heading(column, text=column.title())
            tree.column(column, width=130, anchor=tk.W)
        return tree

    def refresh(self, force_reload: bool = False):
        try:
            self._load_filters()
            self._sync_action_buttons()
            self._load_ahp()
            self._load_policies()
            self._load_runs()
            self._load_readiness()
            self._load_pool_lifecycle()
            self._load_run_related()
        except Exception:
            if getattr(self, "txt_readiness", None):
                self.txt_readiness.delete("1.0", tk.END)
                self.txt_readiness.insert(tk.END, self._friendly_backend_error())

    def _load_filters(self):
        conn = self._conn()
        course_service = get_service_factory(
            conn=conn,
            db_path=getattr(self.app, "db_path", None),
            config=getattr(self.app, "app_config", None),
        ).get_course_service()
        years = [str(year) for year in course_service.list_curriculum_years().unwrap()]
        self.cb_year["values"] = years
        if years and self.cb_year.get() not in years:
            self.cb_year.set(years[-1])

        faculty_rows = course_service.list_faculties().unwrap()
        self._faculty_map = {str(row.get("ad")): int(row.get("fakulte_id")) for row in faculty_rows}
        faculty_names = list(self._faculty_map.keys())
        self.cb_faculty["values"] = faculty_names
        if faculty_names and self.cb_faculty.get() not in faculty_names:
            self.cb_faculty.set(faculty_names[0])
        self._load_departments()
        self._sync_action_buttons()

    def _on_filter_change(self, _event=None):
        self._load_departments()
        self._sync_action_buttons()

    def _selection_ready(self) -> bool:
        return bool((self.cb_year.get() or "").strip()) and bool(self._faculty_map.get(self.cb_faculty.get()))

    def _sync_action_buttons(self):
        state = tk.NORMAL if self._selection_ready() else tk.DISABLED
        for button in getattr(self, "_action_buttons", []):
            try:
                button.configure(state=state)
            except Exception:
                pass

    def _load_departments(self):
        try:
            conn = self._conn()
            fid = self._faculty_map.get(self.cb_faculty.get())
            course_service = get_service_factory(
                conn=conn,
                db_path=getattr(self.app, "db_path", None),
                config=getattr(self.app, "app_config", None),
            ).get_course_service()
            rows = course_service.list_departments(int(fid) if fid else None).unwrap()
            self._department_map = {"Tümü": None}
            self._department_map.update({str(row.get("ad")): int(row.get("bolum_id")) for row in rows})
            values = list(self._department_map.keys())
            self.cb_department["values"] = values
            if self.cb_department.get() not in values:
                self.cb_department.set("Tümü")
            self._sync_action_buttons()
        except Exception:
            pass

    def _load_ahp(self):
        self._clear(self.tree_ahp)
        rows = list_ahp_profiles(self._conn())
        inconsistent = []
        for p in rows:
            weights = ", ".join(f"{k}:{v:.2f}" for k, v in p["weights"].items())
            self.tree_ahp.insert(
                "",
                tk.END,
                iid=str(p["id"]),
                values=(
                    p["id"], p["name"], p["scope_type"], p.get("year") or "",
                    weights, f"{float(p.get('consistency_ratio') or 0):.3f}",
                    "Evet" if p.get("is_consistent") else "Hayır",
                    "Evet" if p.get("is_active") else "Hayır",
                ),
            )
            if not p.get("is_consistent"):
                inconsistent.append(p["name"])
        self.lbl_ahp_warning.config(
            text=("Tutarsız profil: " + ", ".join(inconsistent[:3])) if inconsistent else "Aktif profiller tutarlı."
        )

    def _load_policies(self):
        self._clear(self.tree_policy)
        for p in list_decision_policies(self._conn()):
            self.tree_policy.insert(
                "",
                tk.END,
                iid=str(p["id"]),
                values=(
                    p["id"], p["name"], p["scope_type"], p.get("year") or "",
                    p["mode"], p["curriculum_keep_threshold"], p["pool_threshold"],
                    p["rest_threshold"], p.get("cancel_candidate_threshold") or "",
                    "Evet" if p.get("require_manual_approval_for_cancel") else "Hayır",
                    "Evet" if p.get("is_active") else "Hayır",
                ),
            )

    def _load_runs(self):
        self._clear(self.tree_runs)
        self._run_ids.clear()
        run_values = []
        for run in list_decision_runs(self._conn(), limit=200):
            label = f"#{run['id']} | {run.get('year')} | {run.get('status')}"
            self._run_ids[label] = int(run["id"])
            run_values.append(label)
            self.tree_runs.insert(
                "",
                tk.END,
                iid=str(run["id"]),
                values=(
                    run["id"], run.get("year"), run.get("faculty_id") or "",
                    run.get("semester") or "", run.get("status") or "",
                    run.get("ahp_profile_name") or run.get("ahp_profile_id") or "",
                    run.get("decision_policy_name") or run.get("decision_policy_id") or "",
                    run.get("started_at") or "",
                ),
            )
        self.cb_run["values"] = run_values
        if run_values and self.cb_run.get() not in run_values:
            self.cb_run.set(run_values[0])

    def _load_run_related(self):
        run_id = self._selected_run_id()
        self._load_course_decisions(run_id)
        self._load_sensitivity(run_id)
        self._load_approvals(run_id)
        self._load_fairness(run_id)
        self._load_pool_lifecycle()

    def _load_readiness(self):
        if not getattr(self, "txt_readiness", None):
            return
        self.txt_readiness.delete("1.0", tk.END)
        try:
            year = int(self.cb_year.get())
            faculty_id = self._faculty_map.get(self.cb_faculty.get())
            department_id = self._department_map.get(self.cb_department.get())
            if not faculty_id:
                self.lbl_readiness.config(text="Fakülte seçimi bekleniyor.")
                self.txt_readiness.insert(tk.END, "Hazırlık kontrolü için fakülte ve yıl seçiniz.")
                return
            gate = can_run_algorithm(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id),
                department_id=int(department_id) if department_id is not None else None,
                semester=self.cb_semester.get() or "Guz",
                scope_type="department" if department_id is not None else "faculty",
            )
            summary = gate.get("summary") or {}
            risk = gate.get("risk") or {}
            durum = "Hazır" if gate.get("can_run") else "Engellendi"
            if gate.get("override_active"):
                durum = "Override ile hazır" if gate.get("can_run") else "Override bekliyor"
            self.lbl_readiness.config(
                text=(
                    f"{durum} | Tamlık %{float(gate.get('completion_ratio') or 0) * 100:.1f} | "
                    f"Risk {risk.get('risk_level', 'low')}"
                )
            )
            lines = [
                f"Algoritma çalıştırılabilir mi: {'Evet' if gate.get('can_run') else 'Hayır'}",
                f"Tamlık oranı: %{float(gate.get('completion_ratio') or 0) * 100:.1f}",
                f"Minimum oran: %{float(gate.get('required_completion_ratio') or 0) * 100:.1f}",
                f"Seviye: {gate.get('completion_level')}",
                f"Eksik zorunlu alan: {gate.get('missing_required_fields')}",
                f"Geçersiz zorunlu alan: {gate.get('invalid_required_fields')}",
                f"Kritik/geçersiz issue: {gate.get('blocking_issue_count')}",
                f"Risk: {risk.get('risk_level', 'low')} ({risk.get('risk_score', 0)})",
                f"Aktif override: {'Evet' if gate.get('override_active') else 'Hayır'}",
                "",
                gate.get("blocking_reason") or summary.get("warning_reason") or "Hazırlık kontrolünde engelleyici bulgu yok.",
                "",
                "Kriter bazlı özet:",
            ]
            for key, item in (summary.get("criterion_summary") or {}).items():
                lines.append(
                    f"- {key}: %{float(item.get('required_completion_ratio', item.get('completion_ratio', 0))) * 100:.1f}"
                )
            self.txt_readiness.insert(tk.END, "\n".join(lines))
            self._last_readiness_gate = gate
        except Exception:
            self.lbl_readiness.config(text="Hazırlık kontrolü yüklenemedi.")
            self.txt_readiness.insert(tk.END, self._friendly_backend_error())

    def _request_readiness_override(self):
        try:
            if not getattr(self, "_last_readiness_gate", None):
                self._load_readiness()
            gate = getattr(self, "_last_readiness_gate", None)
            summary = (gate or {}).get("summary") or {}
            if not summary:
                return
            reason = simpledialog.askstring("Override Talebi", "Override gerekçesi:")
            if not reason:
                return
            missing_fields = sorted(
                {
                    str(row.get("criterion_key"))
                    for row in summary.get("matrix") or []
                    if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
                }
            )
            request_override(
                self._conn(),
                scope_type=str(summary.get("scope_type") or "faculty"),
                year=int(summary.get("year")),
                faculty_id=summary.get("faculty_id"),
                department_id=summary.get("department_id"),
                semester=summary.get("semester"),
                missing_fields=missing_fields,
                validation_issues=summary.get("validation_issues") or [],
                reason=reason,
                requested_by="decision_center",
            )
            self._conn().commit()
            messagebox.showinfo("Override", "Override talebi kaydedildi.")
            self._load_readiness()
        except Exception:
            messagebox.showerror("Override", self._friendly_backend_error())

    def _load_course_decisions(self, run_id):
        self._clear(self.tree_courses)
        self._decision_ids.clear()
        self.txt_course_detail.delete("1.0", tk.END)
        if not run_id:
            self.txt_course_detail.insert(tk.END, "Henüz karar çalıştırması bulunmuyor.")
            return
        for row in list_course_decisions(self._conn(), int(run_id)):
            iid = str(row["id"])
            self._decision_ids[iid] = int(row["id"])
            self.tree_courses.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    row["id"], row.get("course_code") or "", row.get("course_name") or row.get("course_id"),
                    _status_text(row.get("old_status")), _status_text(row.get("recommended_status")),
                    _status_text(row.get("final_status")), f"{float(row.get('topsis_score') or 0):.1f}",
                    row.get("trend_label") or "", f"{float(row.get('data_confidence_score') or 0):.2f}",
                    row.get("decision_stability") or "", "Evet" if row.get("approval_required") else "Hayır",
                    row.get("main_reason") or "",
                ),
            )

    def _havuzdan_oner(self):
        """Havuzdaki secmeli dersleri AKTIF AHP agirliklariyla puanlayip
        acilmasi onerilenleri listeler (Havuzdan Oner)."""
        try:
            from app.services.pool_recommendation_service import recommend_from_pool

            year = int(self.cb_year.get())
            faculty_id = self._faculty_map.get(self.cb_faculty.get())
            department_id = self._department_map.get(self.cb_department.get())
            semester = self.cb_semester.get() or None
            rapor = recommend_from_pool(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id) if faculty_id else None,
                department_id=int(department_id) if department_id is not None else None,
                semester=semester,
                top_n=25,
            )
            self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
            ag = rapor["agirliklar"]
            lines = [
                "HAVUZDAN ONERI (aktif AHP agirliklariyla puanlama)",
                "=" * 58,
                "Agirliklar: "
                + ", ".join(f"{k}=%{v*100:.0f}" for k, v in ag.items()),
                f"Esik: {rapor['esik']:.0f}  |  Toplam aday: {rapor['toplam_aday']}"
                f"  |  Kriter verisi yok: {rapor['veri_yok']}",
                "-" * 58,
                f"{'Sira':>4} {'Kod':<10} {'Ders':<26} {'Skor':>6}  Oneri",
                "-" * 58,
            ]
            for o in rapor["oneriler"]:
                isaret = "AC ✓" if o["oneri"] == "AC" else "havuz"
                lines.append(
                    f"{o['sira']:>4} {o['kod']:<10} {o['ad'][:26]:<26} "
                    f"{o['skor']:>6.1f}  {isaret}"
                )
            ac_sayisi = sum(1 for o in rapor["oneriler"] if o["oneri"] == "AC")
            lines += [
                "-" * 58,
                f"ONERI: {ac_sayisi} ders acilmasi onerilir "
                f"(skor >= {rapor['esik']:.0f}).",
                "",
                "Not: Kriter verisi olmayan dersler siralanmaz "
                "(once 'Veri Yonetimi'nden kriter ice aktarin).",
            ]
            self.txt_pool_lifecycle_detail.insert(tk.END, "\n".join(lines))
            self.lbl_pool_lifecycle.config(
                text=f"Havuzdan oneri: {ac_sayisi} ders aciliabilir "
                f"({len(rapor['oneriler'])} siralandi)"
            )
        except Exception as exc:
            messagebox.showerror("Havuzdan Öner", self._friendly_backend_error())
            try:
                self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
                self.txt_pool_lifecycle_detail.insert(tk.END, f"Hata: {exc}")
            except Exception:
                pass

    def _ml_analiz(self):
        """Faz 2+3 ML yeteneklerini (p-value, SHAP/LIME, pruning/MLP)
        kriter verisinden uretip raporlar."""
        try:
            from app.services.ml_analysis_service import run_ml_analysis

            year = int(self.cb_year.get())
            faculty_id = self._faculty_map.get(self.cb_faculty.get())
            self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
            self.txt_pool_lifecycle_detail.insert(
                tk.END, "ML analizi calisiyor (p-value + SHAP/LIME + model "
                "egitimi)... birkac saniye surebilir.\n"
            )
            self.txt_pool_lifecycle_detail.update_idletasks()

            bloklar = []
            for mk, baslik in (("adaptive", "ADAPTIF (Pruning) [Faz2-D]"),
                               ("mlp", "MLP DERIN OGRENME [Faz3-H]")):
                r = run_ml_analysis(
                    self._conn(), year=year,
                    faculty_id=int(faculty_id) if faculty_id else None,
                    model_key=mk,
                )
                bloklar.append(f">>> {baslik}\n" + r["rapor"])

            self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
            self.txt_pool_lifecycle_detail.insert(
                tk.END, "\n\n".join(bloklar)
            )
            self.lbl_pool_lifecycle.config(
                text="ML analiz: p-value + SHAP/LIME + pruning/MLP raporu hazir"
            )
        except Exception as exc:
            messagebox.showerror("ML Analiz", self._friendly_backend_error())
            try:
                self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
                self.txt_pool_lifecycle_detail.insert(tk.END, f"Hata: {exc}")
            except Exception:
                pass

    def _otomatik_karar(self):
        """AHP skoru + (varsa) ML sinyalini birlestirip otomatik
        aç/havuzda tut/iptal adayi onerisi uretir (Otomatik Karar Destek)."""
        try:
            from app.services.auto_decision_support_service import (
                auto_decision_support,
            )

            year = int(self.cb_year.get())
            faculty_id = self._faculty_map.get(self.cb_faculty.get())
            department_id = self._department_map.get(self.cb_department.get())
            semester = self.cb_semester.get() or None
            r = auto_decision_support(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id) if faculty_id else None,
                department_id=int(department_id) if department_id is not None else None,
                semester=semester,
            )
            oz = r["ozet"]
            es = r["esikler"]
            lines = [
                "OTOMATIK KARAR DESTEK ONERISI",
                "=" * 58,
                "Yontem: AHP-agirlikli havuz skoru"
                + (" + ML sinyali" if oz["ml_kullanildi"] else "")
                + f"  (esik AC>={es['ac']:.0f}, iptal<{es['iptal']:.0f})",
                "-" * 58,
                f"  AÇ önerilen          : {oz['ac']}",
                f"  Havuzda tut          : {oz['havuzda_tut']}",
                f"  İptal adayı          : {oz['iptal_adayi']}",
                f"  Toplam degerlendirilen: {oz['toplam']}"
                f"  (kriter verisi yok: {oz['veri_yok']})",
                "-" * 58,
                f"{'Kod':<10} {'Ders':<24} {'Skor':>5} {'ML':>5} "
                f"{'Nihai':>6} {'Guven':>6}  Karar",
                "-" * 58,
            ]
            for k in r["kararlar"][:30]:
                lines.append(
                    f"{k['kod']:<10} {k['ad'][:24]:<24} {k['skor']:>5.0f} "
                    f"{k['ml_sinyal']:>+5.2f} {k['nihai_skor']:>6.1f} "
                    f"{k['guven']:>6.2f}  {k['karar']}"
                )
            lines += [
                "-" * 58,
                "NOT: Bu modul kararlari OTOMATIK UYGULAMAZ; karar "
                "vericiye destek amaclidir. Nihai onay 'Akademik Onay' "
                "ve 'Havuz Yasam Dongusu' uzerinden verilir.",
            ]
            self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
            self.txt_pool_lifecycle_detail.insert(tk.END, "\n".join(lines))
            self.lbl_pool_lifecycle.config(
                text=f"Otomatik karar: {oz['ac']} aç / "
                f"{oz['havuzda_tut']} tut / {oz['iptal_adayi']} iptal adayı"
            )
        except Exception as exc:
            messagebox.showerror("Otomatik Karar", self._friendly_backend_error())
            try:
                self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
                self.txt_pool_lifecycle_detail.insert(tk.END, f"Hata: {exc}")
            except Exception:
                pass

    def _load_pool_lifecycle(self):
        if not getattr(self, "tree_pool_lifecycle", None):
            return
        self._clear(self.tree_pool_lifecycle)
        self._clear(self.tree_pool_approvals)
        self._pool_transition_rows.clear()
        self._pool_approval_ids.clear()
        self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
        try:
            year = int(self.cb_year.get())
            faculty_id = self._faculty_map.get(self.cb_faculty.get())
            department_id = self._department_map.get(self.cb_department.get())
            semester = self.cb_semester.get() or "Guz"
            summary = get_pool_lifecycle_summary(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id) if faculty_id is not None else None,
                department_id=int(department_id) if department_id is not None else None,
                semester=semester,
            )
            self.lbl_pool_lifecycle.config(
                text=(
                    f"Müfredat {summary.get('curriculum_count', 0)} | "
                    f"Havuz {summary.get('pool_count', 0)} | "
                    f"Dinlenme {summary.get('resting_count', 0)} | "
                    f"Kalıcı iptal {summary.get('cancelled_count', 0)} | "
                    f"İptal adayı {summary.get('cancel_candidate_count', 0)} | "
                    f"Onay bekleyen {summary.get('pending_approval_count', 0)}"
                )
            )

            rows = list_state_transitions(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id) if faculty_id is not None else None,
                department_id=int(department_id) if department_id is not None else None,
                limit=500,
            )
            if not rows:
                self.txt_pool_lifecycle_detail.insert(tk.END, "Henüz havuz yaşam döngüsü kaydı bulunmuyor.")
            for row in rows:
                iid = str(row.get("id"))
                self._pool_transition_rows[iid] = row
                self.tree_pool_lifecycle.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(
                        row.get("id"),
                        row.get("course_code") or "",
                        row.get("course_name") or row.get("course_id"),
                        _status_text(row.get("old_status")),
                        _status_text(row.get("recommended_status")),
                        _status_text(row.get("final_status")),
                        _lifecycle_text(row.get("lifecycle_label")),
                        f"{float(row.get('topsis_score') or 0):.1f}",
                        row.get("trend_label") or "",
                        f"{float(row.get('data_confidence_score') or 0):.2f}",
                        "Evet" if row.get("approval_required") else "Hayır",
                        row.get("explanation") or "",
                    ),
                )

            approvals = list_pending_approvals(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id) if faculty_id is not None else None,
                department_id=int(department_id) if department_id is not None else None,
                status="pending",
            )
            for item in approvals:
                iid = str(item.get("id"))
                self._pool_approval_ids[iid] = int(item.get("id"))
                self.tree_pool_approvals.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(
                        item.get("id"),
                        item.get("course_code") or "",
                        item.get("course_name") or item.get("course_id"),
                        _status_text(item.get("requested_status")),
                        _status_text(item.get("current_status")),
                        item.get("approval_type") or "",
                        item.get("approval_status") or "",
                        item.get("approval_reason") or "",
                    ),
                )
        except Exception as exc:
            self.lbl_pool_lifecycle.config(text="Havuz yaşam döngüsü yüklenemedi.")
            self.txt_pool_lifecycle_detail.insert(tk.END, str(exc))

    def _show_pool_lifecycle_detail(self):
        selected = self.tree_pool_lifecycle.selection()
        if not selected:
            return
        row = self._pool_transition_rows.get(str(selected[0]), {})
        self.txt_pool_lifecycle_detail.delete("1.0", tk.END)
        if not row:
            return
        lines = [
            f"{row.get('course_code') or ''} {row.get('course_name') or row.get('course_id')}",
            f"Eski statü: {_status_text(row.get('old_status'))}",
            f"Önerilen statü: {_status_text(row.get('recommended_status'))}",
            f"Final statü: {_status_text(row.get('final_status'))}",
            f"Yaşam döngüsü etiketi: {_lifecycle_text(row.get('lifecycle_label'))}",
            f"Kural: {row.get('rule_applied') or ''}",
            f"Skor / trend / veri güveni: {float(row.get('topsis_score') or 0):.1f} / {row.get('trend_label') or ''} / {float(row.get('data_confidence_score') or 0):.2f}",
            f"Sayaç: {row.get('counter_before')} -> {row.get('counter_after')}",
            f"Onay: {row.get('approval_status') or 'not_required'}",
            "",
            row.get("explanation") or "",
            "",
            "Uyarılar:",
        ]
        for warning in row.get("warnings") or []:
            lines.append(f"- {warning}")
        try:
            history = get_course_state_history(self._conn(), int(row.get("course_id")))
            lines.extend(["", "Son durum geçmişi:"])
            for hist in history[:8]:
                lines.append(
                    f"- {hist.get('created_at') or ''}: "
                    f"{_status_text(hist.get('old_status'))} -> {_status_text(hist.get('final_status'))} "
                    f"({_lifecycle_text(hist.get('lifecycle_label'))})"
                )
        except Exception:
            pass
        self.txt_pool_lifecycle_detail.insert(tk.END, "\n".join(lines))

    def _approve_pool_state(self):
        selected = self.tree_pool_approvals.selection()
        if not selected:
            messagebox.showwarning("Havuz Onayı", "Lütfen bir onay kaydı seçin.")
            return
        note = simpledialog.askstring("Havuz Onayı", "İnceleme notu:")
        try:
            approve_state_approval(self._conn(), int(selected[0]), reviewed_by="decision_center", review_note=note)
            self._conn().commit()
            self._load_pool_lifecycle()
        except Exception:
            messagebox.showerror("Havuz Onayı", self._friendly_backend_error())

    def _reject_pool_state(self):
        selected = self.tree_pool_approvals.selection()
        if not selected:
            messagebox.showwarning("Havuz Onayı", "Lütfen bir onay kaydı seçin.")
            return
        note = simpledialog.askstring("Havuz Reddi", "Red notu:")
        try:
            reject_state_approval(self._conn(), int(selected[0]), reviewed_by="decision_center", review_note=note)
            self._conn().commit()
            self._load_pool_lifecycle()
        except Exception:
            messagebox.showerror("Havuz Reddi", self._friendly_backend_error())

    def _load_sensitivity(self, run_id):
        self._clear(self.tree_sensitivity)
        if not run_id:
            return
        cur = self._conn().cursor()
        cur.execute(
            """
            SELECT d.kod, d.ad, s.base_score, s.min_score, s.max_score,
                   s.score_range, s.stability_level, s.explanation
            FROM decision_sensitivity_results s
            LEFT JOIN ders d ON d.ders_id = s.course_id
            WHERE s.decision_run_id = ?
            ORDER BY CASE s.stability_level WHEN 'low' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END
            """,
            (int(run_id),),
        )
        for row in cur.fetchall():
            self.tree_sensitivity.insert("", tk.END, values=(row[0] or row[1], f"{row[2] or 0:.1f}", f"{row[3] or 0:.1f}", f"{row[4] or 0:.1f}", f"{row[5] or 0:.1f}", row[6], row[7]))

    def _load_approvals(self, run_id):
        self._clear(self.tree_approvals)
        if not run_id:
            return
        cur = self._conn().cursor()
        cur.execute(
            """
            SELECT d.kod, d.ad, cd.recommended_status, cd.final_status,
                   cd.data_confidence_score, cd.approval_status, cd.approval_reason
            FROM course_decisions cd
            LEFT JOIN ders d ON d.ders_id = cd.course_id
            WHERE cd.decision_run_id = ? AND cd.approval_required = 1
            ORDER BY cd.data_confidence_score ASC, d.ad
            """,
            (int(run_id),),
        )
        for row in cur.fetchall():
            self.tree_approvals.insert("", tk.END, values=(row[0] or "", row[1] or "", _status_text(row[2]), _status_text(row[3]), f"{row[4] or 0:.2f}", row[5] or "pending", row[6] or ""))

    def _load_fairness(self, run_id):
        self.txt_fairness.delete("1.0", tk.END)
        if not run_id:
            self.txt_fairness.insert(tk.END, "Henüz adalet raporu bulunmuyor.")
            return
        cur = self._conn().cursor()

        # 1) Kayıtlı adalet raporu (varsa)
        cur.execute(
            """
            SELECT summary_text, report_json
            FROM decision_fairness_reports
            WHERE decision_run_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(run_id),),
        )
        row = cur.fetchone()
        if row:
            self.txt_fairness.insert(tk.END, str(row[0] or "") + "\n\n")
            try:
                report = json.loads(row[1] or "{}")
            except Exception:
                report = {}
            for key, value in report.items():
                self.txt_fairness.insert(tk.END, f"{key}: {value}\n")
        else:
            self.txt_fairness.insert(
                tk.END, "Bu çalıştırma için kayıtlı adalet raporu yok.\n"
            )

        # 2) Objektif metrikler — her zaman course_decisions'tan hesaplanır
        try:
            self._append_objective_metrics(cur, int(run_id))
        except Exception as exc:
            self.txt_fairness.insert(
                tk.END, f"\n[Objektif metrikler hesaplanamadı: {exc}]\n"
            )

    def _append_objective_metrics(self, cur, run_id: int):
        """Karar çalıştırmasının ham sonuçlarından objektif kalite metrikleri."""
        cur.execute(
            """
            SELECT final_status, topsis_score, data_confidence_score,
                   approval_required, decision_stability, department_id
            FROM course_decisions
            WHERE decision_run_id = ?
            """,
            (run_id,),
        )
        rows = cur.fetchall()
        if not rows:
            self.txt_fairness.insert(
                tk.END, "\nObjektif metrik için ders kararı bulunamadı.\n"
            )
            return

        n = len(rows)
        skorlar = [float(r[1] or 0) for r in rows]
        guven = [float(r[2] or 0) for r in rows]
        onay_gerek = sum(1 for r in rows if r[3])
        mufredat = [float(r[1] or 0) for r in rows if r[0] == 1]
        havuz = [float(r[1] or 0) for r in rows if r[0] is not None and r[0] <= 0]

        def ort(x):
            return sum(x) / len(x) if x else 0.0

        def std(x):
            if len(x) < 2:
                return 0.0
            m = ort(x)
            return (sum((v - m) ** 2 for v in x) / len(x)) ** 0.5

        # Statü dağılımı
        dagilim = {}
        stabilite = {}
        bolumler = set()
        for r in rows:
            s = _status_text(r[0])
            dagilim[s] = dagilim.get(s, 0) + 1
            st = str(r[4] or "bilinmiyor")
            stabilite[st] = stabilite.get(st, 0) + 1
            if r[5] is not None:
                bolumler.add(r[5])

        ayrim = ort(mufredat) - ort(havuz)  # separation: yüksek = iyi ayrışma

        lines = [
            "",
            "=" * 58,
            "OBJEKTIF KALITE METRIKLERI (ham karar verisinden)",
            "=" * 58,
            f"Toplam ders karari        : {n}",
            f"Kapsanan bolum sayisi     : {len(bolumler)}",
            "",
            "Karar dagilimi:",
        ]
        for s, c in sorted(dagilim.items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {s:<14}: {c:>4}  (%{c / n * 100:.1f})")
        lines += [
            "",
            f"Ortalama TOPSIS skoru     : {ort(skorlar):.2f}  (std {std(skorlar):.2f})",
            f"  Mufredatta kalan ort.   : {ort(mufredat):.2f}  (n={len(mufredat)})",
            f"  Havuz/dinlenme ort.     : {ort(havuz):.2f}  (n={len(havuz)})",
            f"  >> Skor ayrimi (separation): {ayrim:.2f}  "
            f"({'iyi ayrisma' if ayrim >= 10 else 'zayif ayrisma — esikleri gozden gecirin'})",
            "",
            f"Ortalama veri guveni      : {ort(guven):.3f}  "
            f"({'yeterli' if ort(guven) >= 0.6 else 'dusuk — veri tamlamayi artirin'})",
            f"Manuel onay yuku          : {onay_gerek}/{n}  "
            f"(%{onay_gerek / n * 100:.1f})",
            "",
            "Karar kararliligi (stability) dagilimi:",
        ]
        for st, c in sorted(stabilite.items(), key=lambda kv: -kv[1]):
            lines.append(f"  - {st:<10}: {c:>4}  (%{c / n * 100:.1f})")
        lines += [
            "",
            "Yorum: Skor ayrimi yuksek + veri guveni >=0.60 + dusuk onay yuku",
            "       => karar motoru saglikli ve guvenilir calisiyor demektir.",
            "",
        ]
        self.txt_fairness.insert(tk.END, "\n".join(lines))

    def _show_course_detail(self):
        selected = self.tree_courses.selection()
        if not selected:
            return
        decision_id = int(selected[0])
        cur = self._conn().cursor()
        cur.execute(
            """
            SELECT cd.*, d.kod, d.ad, e.human_readable_text,
                   c.explanation AS confidence_explanation,
                   t.explanation AS trend_explanation,
                   b.raw_values_json, b.weights_json, b.contribution_json,
                   b.positive_distance, b.negative_distance
            FROM course_decisions cd
            LEFT JOIN ders d ON d.ders_id = cd.course_id
            LEFT JOIN course_decision_explanations e ON e.course_decision_id = cd.id
            LEFT JOIN course_data_confidence c ON c.decision_run_id = cd.decision_run_id AND c.course_id = cd.course_id
            LEFT JOIN course_trend_analysis t ON t.decision_run_id = cd.decision_run_id AND t.course_id = cd.course_id
            LEFT JOIN course_score_breakdowns b ON b.decision_run_id = cd.decision_run_id AND b.course_id = cd.course_id
            WHERE cd.id = ?
            LIMIT 1
            """,
            (decision_id,),
        )
        row = cur.fetchone()
        self.txt_course_detail.delete("1.0", tk.END)
        if not row:
            return
        raw = json.loads(row["raw_values_json"] or "{}") if row["raw_values_json"] else {}
        weights = json.loads(row["weights_json"] or "{}") if row["weights_json"] else {}
        contrib = json.loads(row["contribution_json"] or "{}") if row["contribution_json"] else {}
        lines = [
            f"{row['kod'] or ''} {row['ad'] or ''}",
            f"TOPSIS skoru: {float(row['topsis_score'] or 0):.1f}",
            f"Trend: {row['trend_label'] or ''} ({float(row['trend_score'] or 0):.2f})",
            f"Veri güveni: {float(row['data_confidence_score'] or 0):.2f}",
            f"Kararlılık: {row['decision_stability'] or ''}",
            f"Pozitif/negatif ideale uzaklık: {float(row['positive_distance'] or 0):.4f} / {float(row['negative_distance'] or 0):.4f}",
            "",
            "Kriter değerleri:",
        ]
        for key in sorted(raw):
            lines.append(f"- {key}: değer={raw.get(key):.3f}, ağırlık={float(weights.get(key, 0)):.3f}, katkı={float(contrib.get(key, 0)):.3f}")
        lines.extend(["", str(row["trend_explanation"] or ""), str(row["confidence_explanation"] or ""), "", str(row["human_readable_text"] or row["main_reason"] or "")])
        try:
            ml_predictions = get_predictions_for_course(self._conn(), int(row["course_id"]), int(row["year"]))
        except Exception:
            ml_predictions = []
        lines.extend(["", "ML Destekleyici Tahmin:"])
        if not ml_predictions:
            lines.append("Bu ders için kayıtlı ML destekleyici tahmin bulunmuyor.")
        else:
            for pred in ml_predictions[:3]:
                lines.append(
                    f"- {pred.get('algorithm_key')}: tahmin={pred.get('predicted_value_text')}; "
                    f"güven={float(pred.get('confidence_score') or 0):.2f}/{pred.get('confidence_level') or 'low'}; "
                    f"fallback={'evet' if pred.get('fallback_used') else 'hayır'}; "
                    f"karara etkisi={'evet' if pred.get('should_influence_decision') else 'hayır'}."
                )
                if pred.get("explanation"):
                    lines.append(f"  {pred.get('explanation')}")
        self.txt_course_detail.insert(tk.END, "\n".join(lines))

    def _selected_run_id(self):
        label = self.cb_run.get()
        if label in self._run_ids:
            return self._run_ids[label]
        selected = self.tree_runs.selection()
        return int(selected[0]) if selected else None

    def _select_run_from_tree(self):
        selected = self.tree_runs.selection()
        if not selected:
            return
        run_id = int(selected[0])
        for label, label_run_id in self._run_ids.items():
            if label_run_id == run_id:
                self.cb_run.set(label)
                break
        self._load_run_related()

    def _create_profile(self):
        name = simpledialog.askstring("AHP Profili", "Profil adı:")
        if not name:
            return
        try:
            create_ahp_profile(self._conn(), name=name, scope_type="global", activate=True)
            self._load_ahp()
        except Exception:
            messagebox.showerror("AHP Profili", self._friendly_backend_error())

    def _activate_profile(self):
        selected = self.tree_ahp.selection()
        if not selected:
            messagebox.showwarning("AHP Profili", "Lütfen bir profil seçin.")
            return
        try:
            activate_ahp_profile(self._conn(), int(selected[0]))
            self._load_ahp()
        except Exception:
            messagebox.showerror("AHP Profili", self._friendly_backend_error())

    def _create_policy(self):
        name = simpledialog.askstring("Karar Politikası", "Politika adı:")
        if not name:
            return
        try:
            create_decision_policy(self._conn(), name=name, scope_type="global", activate=True)
            self._load_policies()
        except Exception:
            messagebox.showerror("Karar Politikası", self._friendly_backend_error())

    def _activate_policy(self):
        selected = self.tree_policy.selection()
        if not selected:
            messagebox.showwarning("Karar Politikası", "Lütfen bir politika seçin.")
            return
        try:
            activate_decision_policy(self._conn(), int(selected[0]))
            self._load_policies()
        except Exception:
            messagebox.showerror("Karar Politikası", self._friendly_backend_error())

    def _execute_run(self):
        if not self._selection_ready():
            messagebox.showwarning("Karar Çalıştır", "Karar çalıştırmak için önce yıl ve fakülte seçiniz.")
            self._sync_action_buttons()
            return
        try:
            year = int(self.cb_year.get())
            faculty_id = self._faculty_map.get(self.cb_faculty.get())
            gate = can_run_algorithm(
                self._conn(),
                year=year,
                faculty_id=int(faculty_id),
                semester=self.cb_semester.get() or "Guz",
                scope_type="faculty",
            )
            if not gate.get("can_run"):
                messagebox.showwarning(
                    "Hazırlık Kontrolü",
                    gate.get("blocking_reason") or "Kriter tamlığı yeterli olmadığı için algoritma çalıştırılamaz.",
                )
                self._load_readiness()
                return
            result = run_all_algorithms_for_year(
                yil=year,
                db_path=getattr(self.app, "db_path", None) or "data/adil_secmeli.db",
                donem=self.cb_semester.get() or "Guz",
                fakulte_id=int(faculty_id),
            )
            if not result.get("ok"):
                messagebox.showwarning("Karar Çalıştır", self._friendly_backend_error())
            self.refresh()
        except Exception:
            messagebox.showerror("Karar Çalıştır", self._friendly_backend_error())

    def _clear(self, tree):
        for item in tree.get_children():
            tree.delete(item)

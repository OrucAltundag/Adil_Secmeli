# -*- coding: utf-8 -*-
"""AHP Agirlik Yonetimi - Gelismis Tkinter paneli (v2)."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app.services.ahp_calculation_service import calculate_weights_from_pairwise_matrix
from app.services.ahp_impact_explanation_service import explain_weight_profile
from app.services.ahp_profile_service import (
    activate_profile,
    approve_profile,
    archive_profile,
    clone_profile,
    create_profile,
    get_profile,
    list_ahp_profiles,
    reject_profile,
    submit_for_approval,
    validate_profile,
)
from app.services.criteria_definition_service import list_active_criteria

# ─── Kriter meta verileri ────────────────────────────────────────────────────
KRITER_ETIKET: dict[str, str] = {
    "basari": "Basari",
    "trend": "Trend",
    "populerlik": "Populerlik",
    "anket": "Anket / Tercih",
    "katilim": "Katilim",
    "ders_zorluk": "Ders Zorlugu",
    "kredi": "Kredi",
    "kariyer": "Kariyer Katkisi",
}

KRITER_RENK: dict[str, str] = {
    "basari": "#1565C0",
    "trend": "#E65100",
    "populerlik": "#2E7D32",
    "anket": "#6A1B9A",
    "katilim": "#00838F",
    "ders_zorluk": "#AD1457",
    "kredi": "#4E342E",
    "kariyer": "#F57F17",
}

KRITER_ACIKLAMA: dict[str, str] = {
    "basari": (
        "Ogrencilerin ders sonu ortalama not basarisini olcer. "
        "Yuksek agirlik; akademik basariyi secmeli ders puanlamasinin merkezine koyar."
    ),
    "trend": (
        "Dersin iceriginin guncel teknoloji ve is dunyasi trendleriyle "
        "uyumunu olcer. Yuksek agirlik, rekabetci ve guncel dersleri one cikarir."
    ),
    "populerlik": (
        "Dersin onceki donemlerdeki tercih sayisi ve doluluk oranina gore belirlenir. "
        "Talep goren dersler daha yuksek puan alir."
    ),
    "anket": (
        "Ogrenci anket sonuclarina dayali memnuniyet ve tavsiye puanidir. "
        "Yuksek agirlik, ogrenci geri bildirimini onceliklendirir."
    ),
    "katilim": (
        "Derse devam ve aktif katilim oranini olcer. "
        "Yuksek agirlik, duzenli devam eden ogrencileri odullendirir."
    ),
    "ders_zorluk": (
        "Gecme orani ve harf dagilimi uzerinden hesaplanan gucluk endeksidir. "
        "Kolay dersler bu kriterde dusuk puan alabilir."
    ),
    "kredi": (
        "Dersin AKTS / kredi degerini yansitir. "
        "Yuksek kredili dersler daha agir basan secenekler olarak degerlendirilebilir."
    ),
    "kariyer": (
        "Dersin is bulma ve kariyer gelisimine olan katkisini olcer. "
        "Sektorel iliskiler ve mezun geri bildirimleri kaynak alinir."
    ),
}

DURUM_RENK: dict[str, str] = {
    "active": "#C8E6C9",
    "approved": "#B3E5FC",
    "pending_approval": "#FFE0B2",
    "validated": "#E3F2FD",
    "draft": "#F5F5F5",
    "archived": "#EEEEEE",
    "rejected": "#FFCDD2",
}

DURUM_ETIKET: dict[str, str] = {
    "active": "* AKTIF",
    "approved": "v Onaylandi",
    "pending_approval": "~ Onay Bekliyor",
    "validated": "? Dogrulandi",
    "draft": "- Taslak",
    "archived": "# Arsivlendi",
    "rejected": "x Reddedildi",
}

SAATY_ETIKETLER: list[str] = [
    "1/9 -- A kesinlikle daha az onemli",
    "1/7 -- A cok guclu daha az onemli",
    "1/5 -- A guclu daha az onemli",
    "1/3 -- A biraz daha az onemli",
    "1   -- Esit onemli",
    "3   -- A biraz daha onemli",
    "5   -- A guclu daha onemli",
    "7   -- A cok guclu daha onemli",
    "9   -- A kesinlikle daha onemli",
]

SAATY_DEGERLER: list[float] = [1 / 9, 1 / 7, 1 / 5, 1 / 3, 1.0, 3.0, 5.0, 7.0, 9.0]


class AHPWeightPage(ttk.Frame):
    """
    AHP Agirlik Yonetimi sayfasi - uc sekme:

    1. Profil Listesi      : Renkli durum tablosu, sag detay paneli (CR + agirlik
                             cubukları), aksiyon butonlari, renk aciklamasi.
    2. Ikili Karsilastirma : Gorsel NxN giris matrisi, otomatik karsit-hucre
                             guncelleme, canli CR gostergesi, agirlik cubukları.
    3. Etki & Analiz       : Renkli kriter kartlari, ASCII agirlik cubukları,
                             aciklama metinleri.

    Bu sayfa, AHP (Analytic Hierarchy Process) yontemiyle kriter agirliklarini
    yonetmenizi saglar. Dogruluk kriteri: CR <= 0.10 (tutarli matris).
    """

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._profile_rows: dict[str, int] = {}
        self._criterion_keys: list[str] = []
        self._matrix_entries: list[list] = []   # StringVar (off-diag) | None (diag)
        self._current_weights: dict[str, float] = {}
        self._current_cr: float | None = None
        self._build_ui()

    # ─── Veritabani ──────────────────────────────────────────────────────────
    def _conn(self):
        conn = getattr(getattr(self.app, "db", None), "conn", None)
        if conn is None:
            raise RuntimeError(self._friendly_backend_error())
        return conn

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Sistem şu an meşgul, daha sonra tekrar deneyin."

    def _format_error(self, exc: Exception) -> str:
        text = str(exc)
        markers = ("Veritabani", "Veritaban", "database", "sqlite", "connection", "baglanti")
        if any(marker.lower() in text.lower() for marker in markers):
            return self._friendly_backend_error()
        return text

    # ─── Ana UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        header = ttk.Frame(self, padding=(8, 6))
        header.pack(fill=tk.X)
        ttk.Label(
            header, text="AHP Agirlik Yonetimi", style="Header.TLabel"
        ).pack(side=tk.LEFT)
        ttk.Button(header, text="Yenile", command=self.refresh).pack(side=tk.RIGHT, padx=2)
        ttk.Button(header, text="+ Yeni Profil", command=self.create_default_profile).pack(
            side=tk.RIGHT, padx=2
        )

        # Aktif profil banner
        self.banner_var = tk.StringVar(value="Henuz aktif profil yok")
        banner = tk.Frame(self, bg="#1B5E20", pady=2)
        banner.pack(fill=tk.X, padx=8, pady=(0, 2))
        tk.Label(
            banner,
            textvariable=self.banner_var,
            bg="#1B5E20",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            pady=4,
        ).pack()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 8))
        self._build_tab1()
        self._build_tab2()
        self._build_tab3()

    # ─── Tab 1: Profil Listesi ────────────────────────────────────────────────
    def _build_tab1(self):
        frame = ttk.Frame(self.nb, padding=6)
        self.nb.add(frame, text="Profil Listesi")

        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Sol: Treeview
        left = ttk.Frame(paned)
        paned.add(left, weight=3)

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("profil", "scope", "year", "version", "cr", "status", "active")
        self.profile_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=16
        )
        headings = {
            "profil": "Profil Adi",
            "scope": "Kapsam",
            "year": "Yil",
            "version": "Versiyon",
            "cr": "CR",
            "status": "Durum",
            "active": "Aktif",
        }
        widths = {
            "profil": 180, "scope": 100, "year": 44,
            "version": 68, "cr": 52, "status": 120, "active": 44,
        }
        for col, text in headings.items():
            self.profile_tree.heading(col, text=text)
            self.profile_tree.column(col, width=widths[col], minwidth=40, anchor=tk.W)

        for status, color in DURUM_RENK.items():
            self.profile_tree.tag_configure(status, background=color)

        # Secili satir, durum rengi ne olursa olsun belirgin (koyu mavi) gorunsun
        try:
            style = ttk.Style()
            style.map(
                "Treeview",
                background=[("selected", "#1565C0")],
                foreground=[("selected", "white")],
            )
        except Exception:
            pass

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.profile_tree.yview)
        self.profile_tree.configure(yscrollcommand=scroll_y.set)
        self.profile_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.profile_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_profile_select())

        # Sag: Detay paneli
        right = ttk.LabelFrame(paned, text="  Profil Detayi  ", padding=8)
        paned.add(right, weight=2)

        self.detail_name = ttk.Label(
            right, text="---", font=("Segoe UI", 10, "bold"), wraplength=210, anchor=tk.W
        )
        self.detail_name.pack(fill=tk.X, pady=(0, 2))

        self.detail_status = ttk.Label(right, text="", font=("Segoe UI", 9))
        self.detail_status.pack(anchor=tk.W)

        self.detail_cr = ttk.Label(right, text="")
        self.detail_cr.pack(anchor=tk.W, pady=(2, 0))

        ttk.Label(right, text="Notlar:", font=("Segoe UI", 8, "italic")).pack(
            anchor=tk.W, pady=(6, 0)
        )
        self.detail_notes = tk.Text(
            right, height=3, wrap=tk.WORD, state=tk.DISABLED,
            font=("Segoe UI", 8), relief=tk.FLAT, bg="#F9F9F9",
        )
        self.detail_notes.pack(fill=tk.X, pady=(2, 4))

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(right, text="Kriter Agirliklari", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.weight_canvas_tab1 = tk.Canvas(
            right, height=120, bg="white",
            highlightthickness=1, highlightbackground="#BDBDBD",
        )
        self.weight_canvas_tab1.pack(fill=tk.X, pady=(4, 0))

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(8, 4))
        ttk.Label(right, text="Ikili Karsilastirma Matrisi", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.detail_matrix_text = tk.Text(
            right, height=8, wrap=tk.NONE,
            font=("Consolas", 8), state=tk.DISABLED,
            bg="#F8F9FA", relief=tk.FLAT,
        )
        mat_sb_x = ttk.Scrollbar(right, orient=tk.HORIZONTAL, command=self.detail_matrix_text.xview)
        self.detail_matrix_text.configure(xscrollcommand=mat_sb_x.set)
        self.detail_matrix_text.pack(fill=tk.X, pady=(2, 0))
        mat_sb_x.pack(fill=tk.X)

        # Aksiyon butonlari --- 2 sira
        action_frame = ttk.Frame(frame, padding=(0, 6, 0, 0))
        action_frame.pack(fill=tk.X)

        row1 = ttk.Frame(action_frame)
        row1.pack(fill=tk.X, pady=(0, 2))
        for text, cmd in [
            ("Dogrula", self.validate_selected),
            ("Onaya Gonder", self.submit_selected),
            ("Onayla", self.approve_selected),
            ("Reddet", self.reject_selected),
        ]:
            ttk.Button(row1, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(action_frame)
        row2.pack(fill=tk.X)
        for text, cmd in [
            ("Aktif Yap", self.activate_selected),
            ("Klonla", self.clone_selected),
            ("Arsivle", self.archive_selected),
            ("Matrisi Duzenle", self._edit_selected_in_tab2),
        ]:
            ttk.Button(row2, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        # Durum renk aciklamasi
        legend = ttk.Frame(frame)
        legend.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(legend, text="Durum renkleri:", font=("Segoe UI", 7, "italic")).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        for status in ("active", "approved", "pending_approval", "validated", "draft", "archived", "rejected"):
            color = DURUM_RENK[status]
            tk.Label(
                legend,
                text=DURUM_ETIKET[status],
                bg=color, padx=5, pady=1,
                font=("Segoe UI", 7), relief=tk.GROOVE, bd=1,
            ).pack(side=tk.LEFT, padx=2)

        # Yasam dongusu + TOPSIS akis aciklamasi
        akis = tk.Frame(frame, bg="#F4F8FE")
        akis.pack(fill=tk.X, pady=(8, 0))
        tk.Label(
            akis,
            text="Profil yasam dongusu ve TOPSIS'e aktarim",
            bg="#F4F8FE", fg="#1565C0",
            font=("Segoe UI", 8, "bold"), anchor=tk.W,
        ).pack(fill=tk.X, padx=8, pady=(4, 1))
        tk.Label(
            akis,
            text=(
                "Adimlar:  1) Yeni Profil (ad girilir)  ->  2) Ikili Karsilastirma "
                "sekmesinde matris doldurulur  ->  3) Dogrula  ->  4) Onaya Gonder  "
                "->  5) Onayla  ->  6) Aktif Yap.\n"
                "Onayla: profil 'approved' olur (gecerli ama henuz kullanilmaz).  "
                "Reddet: profil 'rejected' olur (kullanilamaz, gerekce sorulur).  "
                "Aktif Yap: profil 'active' olur ve ESKI aktif profil otomatik pasige duser.\n"
                "TOPSIS baglantisi: Yalnizca AKTIF profilin agirliklari kullanilir. "
                "Karar Merkezi -> Calistirmalar -> 'Yeni Karar Calistir' dediginizde "
                "aktif AHP profilinin agirliklari TOPSIS'e otomatik aktarilir. "
                "Kontrol: Karar Merkezi -> Calistirmalar sekmesindeki 'ahp' sutunu "
                "hangi profilin kullanildigini gosterir."
            ),
            bg="#F4F8FE", fg="#37474F",
            font=("Segoe UI", 7), anchor=tk.W,
            justify=tk.LEFT, wraplength=1050,
        ).pack(fill=tk.X, padx=8, pady=(0, 5))

    # ─── Tab 2: Ikili Karsilastirma ───────────────────────────────────────────
    def _build_tab2(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Ikili Karsilastirma")

        # Profil bilgi cubugu
        topbar = ttk.Frame(frame)
        topbar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(topbar, text="Duzenlenen Profil:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.profile_label_tab2 = ttk.Label(
            topbar,
            text="--- (Tab 1'den profil secip 'Matrisi Duzenle' tiklayin)",
            font=("Segoe UI", 9, "bold"),
            foreground="#1565C0",
        )
        self.profile_label_tab2.pack(side=tk.LEFT, padx=6)

        # Hizli karsilastirma yardimcisi
        helper = ttk.LabelFrame(frame, text="  Hizli Karsilastirma Yardimcisi  ", padding=6)
        helper.pack(fill=tk.X, pady=(0, 6))
        hrow = ttk.Frame(helper)
        hrow.pack(fill=tk.X)

        ttk.Label(hrow, text="Kriter A:").pack(side=tk.LEFT)
        self.cb_left = ttk.Combobox(hrow, width=16, state="readonly")
        self.cb_left.pack(side=tk.LEFT, padx=4)

        ttk.Label(hrow, text="Kriter B:").pack(side=tk.LEFT)
        self.cb_right = ttk.Combobox(hrow, width=16, state="readonly")
        self.cb_right.pack(side=tk.LEFT, padx=4)

        ttk.Label(hrow, text="Onem:").pack(side=tk.LEFT)
        self.cb_saaty = ttk.Combobox(
            hrow, width=36, state="readonly", values=SAATY_ETIKETLER
        )
        self.cb_saaty.set(SAATY_ETIKETLER[4])
        self.cb_saaty.pack(side=tk.LEFT, padx=4)
        ttk.Button(hrow, text="Uygula ->", command=self.apply_pairwise_value).pack(
            side=tk.LEFT, padx=4
        )

        # Ana icerik: Matris (sol) | CR + Agirliklar (sag)
        content = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True)

        # ── Sol: Matris ──
        mat_outer = ttk.LabelFrame(
            content,
            text="  Karsilastirma Matrisi  (hucreleri dogrudan duzenleyebilirsiniz)  ",
            padding=6,
        )
        content.add(mat_outer, weight=3)

        self.matrix_canvas = tk.Canvas(mat_outer, bg="white", highlightthickness=0)
        mx_sby = ttk.Scrollbar(mat_outer, orient=tk.VERTICAL, command=self.matrix_canvas.yview)
        mx_sbx = ttk.Scrollbar(mat_outer, orient=tk.HORIZONTAL, command=self.matrix_canvas.xview)
        self.matrix_canvas.configure(
            yscrollcommand=mx_sby.set, xscrollcommand=mx_sbx.set
        )
        mx_sby.pack(side=tk.RIGHT, fill=tk.Y)
        mx_sbx.pack(side=tk.BOTTOM, fill=tk.X)
        self.matrix_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.matrix_inner = ttk.Frame(self.matrix_canvas)
        self.matrix_canvas.create_window((0, 0), window=self.matrix_inner, anchor="nw")
        self.matrix_inner.bind(
            "<Configure>",
            lambda _e: self.matrix_canvas.configure(
                scrollregion=self.matrix_canvas.bbox("all")
            ),
        )

        mat_btns = ttk.Frame(mat_outer)
        mat_btns.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(mat_btns, text="Sifirla (1)", command=self._reset_matrix).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(mat_btns, text="JSON Kopyala", command=self._copy_matrix_json).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(mat_btns, text="Profile Kaydet", command=self.save_matrix_to_selected).pack(
            side=tk.RIGHT, padx=2
        )

        # ── Sag: CR + Agirliklar ──
        right = ttk.Frame(content, padding=4)
        content.add(right, weight=2)

        cr_frame = ttk.LabelFrame(right, text="  Tutarlilik Orani (CR)  ", padding=8)
        cr_frame.pack(fill=tk.X, pady=(0, 8))

        self.cr_value_label = ttk.Label(
            cr_frame, text="---", font=("Segoe UI", 24, "bold"), anchor=tk.CENTER
        )
        self.cr_value_label.pack(fill=tk.X)
        self.cr_status_label = ttk.Label(
            cr_frame, text="Henuz hesaplanmadi", anchor=tk.CENTER, font=("Segoe UI", 8)
        )
        self.cr_status_label.pack(fill=tk.X, pady=(2, 0))
        self.cr_bar = tk.Canvas(cr_frame, height=14, bg="#E0E0E0", highlightthickness=0)
        self.cr_bar.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(
            cr_frame,
            text="CR <= 0.10  Tutarli   |   CR > 0.10  Duzeltilmeli",
            font=("Segoe UI", 7),
            foreground="#757575",
        ).pack()

        # CR <= 0.10 esiginin detayli aciklamasi
        aciklama_kutu = tk.Frame(cr_frame, bg="#FFF6DF")
        aciklama_kutu.pack(fill=tk.X, pady=(6, 0))
        tk.Label(
            aciklama_kutu,
            text="CR (Tutarlilik Orani) nedir ve neden 0.10?",
            bg="#FFF6DF", fg="#6B4E00",
            font=("Segoe UI", 8, "bold"), anchor=tk.W,
        ).pack(fill=tk.X, padx=6, pady=(4, 1))
        tk.Label(
            aciklama_kutu,
            text=(
                "CR = CI / RI.  CI = (lambda_max - n) / (n - 1)  tutarsizlik indeksi, "
                "RI ise n boyutlu rastgele matrisin beklenen indeksidir (Saaty tablosu: "
                "n=4 icin 0.90).  Ikili karsilastirmalar mukemmel tutarli olsaydi CR=0 olurdu.\n\n"
                "Saaty'nin kurali: %10'a kadar tutarsizlik insan yargisinda normaldir. "
                "Bu yuzden esik CR <= 0.10 secilmistir.\n\n"
                "CR > 0.10 ise: yargilariniz celiskili (or. A>B, B>C ama C>A). "
                "Bu durumda hesaplanan agirliklar guvenilmezdir; karsilastirmalari "
                "gozden gecirip duzeltmeniz gerekir. Sistem tutarsiz profili AKTIF "
                "yapmaniza izin vermez."
            ),
            bg="#FFF6DF", fg="#5D4037",
            font=("Segoe UI", 7), anchor=tk.W,
            justify=tk.LEFT, wraplength=300,
        ).pack(fill=tk.X, padx=6, pady=(0, 5))

        ttk.Button(
            right, text="Agirliklari Hesapla", command=self.calculate_current_matrix
        ).pack(fill=tk.X, pady=(0, 6))

        wf = ttk.LabelFrame(right, text="  Hesaplanan Agirliklar  ", padding=6)
        wf.pack(fill=tk.BOTH, expand=True)
        self.weight_canvas_tab2 = tk.Canvas(wf, bg="white", highlightthickness=0)
        self.weight_canvas_tab2.pack(fill=tk.BOTH, expand=True)

    # ─── Tab 3: Etki & Analiz ─────────────────────────────────────────────────
    def _build_tab3(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Etki ve Analiz")

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            top,
            text="Secili profilin kriter agirliklari ve hassasiyet analizi:",
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT)
        ttk.Button(top, text="Analizi Yukle", command=self.load_impact).pack(side=tk.RIGHT)

        # Kriter kartlari (dinamik)
        cards_outer = ttk.LabelFrame(frame, text="  Kriter Agirlik Kartlari  ", padding=4)
        cards_outer.pack(fill=tk.X, pady=(0, 6))
        self.cards_frame = ttk.Frame(cards_outer)
        self.cards_frame.pack(fill=tk.X)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)

        ttk.Label(frame, text="Detayli Rapor:", font=("Segoe UI", 9, "bold")).pack(
            anchor=tk.W, pady=(0, 2)
        )

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self.impact_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
            bg="#FAFAFA",
        )
        impact_sb = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=self.impact_text.yview
        )
        self.impact_text.configure(yscrollcommand=impact_sb.set)
        self.impact_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        impact_sb.pack(side=tk.RIGHT, fill=tk.Y)

    # ─── Yenile ──────────────────────────────────────────────────────────────
    def refresh(self):
        try:
            conn = self._conn()
            profiles = list_ahp_profiles(conn)
            criteria = list_active_criteria(conn)
            conn.commit()

            self._criterion_keys = [row["criterion_key"] for row in criteria]
            self.cb_left["values"] = self._criterion_keys
            self.cb_right["values"] = self._criterion_keys
            if self._criterion_keys:
                self.cb_left.set(self._criterion_keys[0])
                self.cb_right.set(
                    self._criterion_keys[min(1, len(self._criterion_keys) - 1)]
                )

            for item in self.profile_tree.get_children():
                self.profile_tree.delete(item)
            self._profile_rows.clear()

            active_profile = None
            for profile in profiles:
                status = profile.get("status", "draft")
                is_active = bool(profile.get("is_active"))
                if is_active:
                    active_profile = profile
                cr = profile.get("consistency_ratio")
                cr_text = "" if cr is None else f"{float(cr):.3f}"
                # profile_name veya name alanından al; ikisi de bos ise "(isimsiz)"
                pname = (
                    profile.get("profile_name")
                    or profile.get("name")
                    or "(isimsiz)"
                )
                # Bytes gelirse guvvenli str'e cevir
                if isinstance(pname, bytes):
                    pname = pname.decode("utf-8", errors="replace")
                pname = str(pname).strip() or "(isimsiz)"

                item = self.profile_tree.insert(
                    "",
                    tk.END,
                    values=(
                        pname,
                        self._scope_text(profile),
                        profile.get("year") or "",
                        profile.get("version") or "1",
                        cr_text,
                        DURUM_ETIKET.get(status, status),
                        "Evet" if is_active else "",
                    ),
                    tags=(status,),
                )
                self._profile_rows[item] = int(profile["id"])

            if active_profile:
                cr = active_profile.get("consistency_ratio")
                cr_str = f"   |   CR: {float(cr):.3f}" if cr is not None else ""
                self.banner_var.set(
                    f"* Aktif Profil: {active_profile.get('profile_name')}"
                    f"   (v{active_profile.get('version')}){cr_str}"
                )
            else:
                self.banner_var.set(
                    "Aktif profil yok --- bir profili secip 'Aktif Yap' ile etkinlestirin."
                )

            self._rebuild_matrix_grid()

            # Refresh sonrasi panel bos kalmasin: aktif profili (yoksa ilk
            # satiri) otomatik sec ve detayini goster.
            children = self.profile_tree.get_children()
            if children:
                hedef = None
                if active_profile:
                    for item, pid in self._profile_rows.items():
                        if int(pid) == int(active_profile["id"]):
                            hedef = item
                            break
                hedef = hedef or children[0]
                self.profile_tree.selection_set(hedef)
                self.profile_tree.focus(hedef)
                self._on_profile_select()
        except Exception as exc:
            messagebox.showerror("AHP Agirlik Yonetimi", self._format_error(exc))

    # ─── Matris Grid ─────────────────────────────────────────────────────────
    def _rebuild_matrix_grid(self, matrix: list[list] | None = None):
        """NxN Entry widget matrisini olusturur / yeniler."""
        for widget in self.matrix_inner.winfo_children():
            widget.destroy()
        self._matrix_entries = []

        keys = self._criterion_keys
        n = len(keys)
        if n == 0:
            ttk.Label(
                self.matrix_inner,
                text="Aktif kriter bulunamadi. Lutfen 'Yenile' butonuna basin.",
                padding=16,
            ).pack()
            return

        CELL_W = 7
        HEADER_W = 12

        # Baslik satiri --- kose bos
        tk.Label(
            self.matrix_inner, text="", width=HEADER_W, bg="#ECEFF1", relief=tk.FLAT
        ).grid(row=0, column=0, padx=1, pady=1, sticky="nsew")

        for j, key in enumerate(keys):
            label = KRITER_ETIKET.get(key, key)
            color = KRITER_RENK.get(key, "#546E7A")
            tk.Label(
                self.matrix_inner,
                text=label,
                width=CELL_W,
                bg=color,
                fg="white",
                font=("Segoe UI", 8, "bold"),
                anchor=tk.CENTER,
                pady=4,
            ).grid(row=0, column=j + 1, padx=1, pady=1, sticky="nsew")

        for i, key_i in enumerate(keys):
            label_i = KRITER_ETIKET.get(key_i, key_i)
            color_i = KRITER_RENK.get(key_i, "#546E7A")
            tk.Label(
                self.matrix_inner,
                text=label_i,
                width=HEADER_W,
                bg=color_i,
                fg="white",
                font=("Segoe UI", 8, "bold"),
                anchor=tk.W,
                padx=4,
            ).grid(row=i + 1, column=0, padx=1, pady=1, sticky="nsew")

            row_vars: list[tk.StringVar | None] = []
            for j in range(n):
                if i == j:
                    # Diagonal: kilitli "1"
                    tk.Label(
                        self.matrix_inner,
                        text="1",
                        width=CELL_W,
                        bg="#ECEFF1",
                        fg="#455A64",
                        font=("Segoe UI", 9, "bold"),
                        anchor=tk.CENTER,
                        relief=tk.SUNKEN,
                        bd=1,
                    ).grid(row=i + 1, column=j + 1, padx=1, pady=1, sticky="nsew")
                    row_vars.append(None)
                else:
                    try:
                        init_val = self._fmt(float(matrix[i][j])) if matrix else "1"
                    except Exception:
                        init_val = "1"
                    var = tk.StringVar(value=init_val)
                    entry = ttk.Entry(
                        self.matrix_inner,
                        textvariable=var,
                        width=CELL_W,
                        justify=tk.CENTER,
                    )
                    entry.grid(row=i + 1, column=j + 1, padx=1, pady=1, sticky="nsew")
                    entry.bind(
                        "<FocusOut>", lambda _e, ii=i, jj=j: self._on_cell_edit(ii, jj)
                    )
                    entry.bind(
                        "<Return>", lambda _e, ii=i, jj=j: self._on_cell_edit(ii, jj)
                    )
                    row_vars.append(var)
            self._matrix_entries.append(row_vars)

        self.matrix_inner.update_idletasks()
        self.matrix_canvas.configure(scrollregion=self.matrix_canvas.bbox("all"))

    def _on_cell_edit(self, i: int, j: int):
        """Hucre duzenlendikten sonra karsit hucreyi (j,i) = 1/v olarak gunceller."""
        try:
            n = len(self._criterion_keys)
            if i >= n or j >= n or i >= len(self._matrix_entries):
                return
            var_ij = self._matrix_entries[i][j]
            if var_ij is None:
                return
            value = self._parse_val(var_ij.get())
            if value <= 0:
                raise ValueError("Deger sifirdan buyuk olmalidir.")
            var_ij.set(self._fmt(value))
            var_ji = self._matrix_entries[j][i]
            if var_ji is not None:
                var_ji.set(self._fmt(1.0 / value))
        except (ValueError, ZeroDivisionError) as exc:
            messagebox.showwarning(
                "Matris Girisi",
                f"Gecersiz deger: {exc}\n"
                "Gecerli degerler: 1/9, 1/7, 1/5, 1/3, 1, 2, 3, 5, 7, 9",
            )

    # ─── Hesaplama ────────────────────────────────────────────────────────────
    def calculate_current_matrix(self):
        try:
            keys = self._criterion_keys
            if not keys:
                messagebox.showwarning("AHP", "Kriter listesi bos. 'Yenile' butonuna basin.")
                return
            matrix = self._get_matrix_values()
            result = calculate_weights_from_pairwise_matrix(keys, matrix)

            weights = (
                result.weights
                if hasattr(result, "weights")
                else result.to_dict().get("weights", {})
            )
            cr = (
                result.consistency_ratio
                if hasattr(result, "consistency_ratio")
                else None
            )
            self._current_weights = weights
            self._current_cr = cr

            # CR gostergesi guncelle
            if cr is not None:
                self.cr_value_label.config(text=f"{cr:.4f}")
                if cr <= 0.10:
                    cr_color, cr_msg = "#2E7D32", "Tutarli --- matris kabul edilebilir"
                elif cr <= 0.15:
                    cr_color, cr_msg = "#F57C00", "Sinirda --- inceleme onerilir"
                else:
                    cr_color, cr_msg = "#C62828", "Tutarsiz --- karsilastirmalari duzeltiniz"
                self.cr_value_label.config(foreground=cr_color)
                self.cr_status_label.config(text=cr_msg, foreground=cr_color)
                self._draw_cr_bar(cr)
            else:
                self.cr_value_label.config(text="---", foreground="#333")
                self.cr_status_label.config(text="CR hesaplanamadi", foreground="#757575")

            self._draw_weight_bars(self.weight_canvas_tab2, keys, weights)
        except Exception as exc:
            messagebox.showerror("AHP Hesaplama", self._format_error(exc))

    def _draw_cr_bar(self, cr: float):
        self.cr_bar.update_idletasks()
        w = max(self.cr_bar.winfo_width(), 200)
        ratio = min(cr / 0.20, 1.0)
        bar_w = int(w * ratio)
        color = "#4CAF50" if cr <= 0.10 else ("#FF9800" if cr <= 0.15 else "#F44336")
        self.cr_bar.delete("all")
        self.cr_bar.create_rectangle(0, 0, bar_w, 14, fill=color, outline="")
        self.cr_bar.create_rectangle(bar_w, 0, w, 14, fill="#E0E0E0", outline="")
        txt_color = "white" if ratio > 0.25 else "#555"
        self.cr_bar.create_text(
            w // 2, 7, text=f"CR = {cr:.3f}", font=("Segoe UI", 7), fill=txt_color
        )

    # ─── Agirlik Cubuklari ────────────────────────────────────────────────────
    def _draw_weight_bars(self, canvas: tk.Canvas, keys: list, weights: dict):
        canvas.delete("all")
        if not keys or not weights:
            canvas.create_text(
                10, 20, text="Agirlik verisi yok",
                anchor=tk.W, font=("Segoe UI", 8), fill="#9E9E9E",
            )
            return

        canvas.update_idletasks()
        cw = max(canvas.winfo_width(), 200)
        row_h = 26
        total_h = len(keys) * row_h + 12
        canvas.config(height=max(total_h, 80))

        bar_start = 88
        bar_end = cw - 54
        bar_width = max(bar_end - bar_start, 20)

        for idx, key in enumerate(keys):
            y = 6 + idx * row_h
            label = KRITER_ETIKET.get(key, key)
            w_val = float(weights.get(key, 0.0))
            color = KRITER_RENK.get(key, "#607D8B")
            bar_len = int(bar_width * w_val)

            canvas.create_text(
                bar_start - 4, y + 10,
                text=label, anchor=tk.E,
                font=("Segoe UI", 8), fill="#424242",
            )
            canvas.create_rectangle(
                bar_start, y + 4, bar_start + bar_width, y + 20,
                fill="#F5F5F5", outline="#E0E0E0",
            )
            if bar_len > 0:
                canvas.create_rectangle(
                    bar_start, y + 4, bar_start + bar_len, y + 20,
                    fill=color, outline="",
                )
            canvas.create_text(
                bar_start + bar_width + 4, y + 10,
                text=f"{w_val * 100:.1f}%", anchor=tk.W,
                font=("Segoe UI", 8, "bold"), fill=color,
            )

    # ─── Profil Secim Olayi ──────────────────────────────────────────────────
    def _on_profile_select(self):
        try:
            profile = self._selected_profile()
            if not profile:
                return

            name = (
                profile.get("profile_name")
                or profile.get("name")
                or "(isimsiz)"
            )
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            name = str(name).strip() or "(isimsiz)"

            status = profile.get("status", "draft")
            cr = profile.get("consistency_ratio")
            notes = profile.get("notes") or ""

            self.detail_name.config(text=name)

            status_fg = {
                "active": "#2E7D32",
                "approved": "#1565C0",
                "rejected": "#C62828",
                "pending_approval": "#E65100",
                "archived": "#757575",
            }.get(status, "#333333")
            self.detail_status.config(
                text=DURUM_ETIKET.get(status, status), foreground=status_fg
            )

            if cr is not None:
                cr_f = float(cr)
                cr_color = "#2E7D32" if cr_f <= 0.10 else "#C62828"
                self.detail_cr.config(
                    text=f"CR: {cr_f:.4f}  {'Tutarli' if cr_f <= 0.10 else 'Tutarsiz'}",
                    foreground=cr_color,
                )
            else:
                self.detail_cr.config(text="CR: Hesaplanmamis", foreground="#9E9E9E")

            self.detail_notes.config(state=tk.NORMAL)
            self.detail_notes.delete("1.0", tk.END)
            self.detail_notes.insert(tk.END, notes)
            self.detail_notes.config(state=tk.DISABLED)

            # Agirlik cubukları
            weights = profile.get("weights") or {}
            keys = (
                profile.get("criteria_keys")
                or list(weights.keys())
                or self._criterion_keys
            )
            self._draw_weight_bars(self.weight_canvas_tab1, keys, weights)

            # Matris gorunumu
            self._show_detail_matrix(profile, keys)

        except Exception as exc:
            # Sessiz cokme yerine detay panelinde goster
            try:
                self.detail_name.config(text=f"Hata: {exc}")
            except Exception:
                pass

    def _show_detail_matrix(self, profile: dict, keys: list):
        """Detay panelindeki salt-okunur matris widget'ini gunceller."""
        matrix = profile.get("pairwise_matrix") or []
        self.detail_matrix_text.config(state=tk.NORMAL)
        self.detail_matrix_text.delete("1.0", tk.END)

        if not matrix or not keys:
            self.detail_matrix_text.insert(tk.END, "(matris verisi yok)")
            self.detail_matrix_text.config(state=tk.DISABLED)
            return

        n = len(keys)
        col_w = 7  # her hucre genisligi

        # Baslik satiri
        header = " " * 12
        for k in keys:
            lbl = KRITER_ETIKET.get(k, k)[:col_w]
            header += f"{lbl:>{col_w}} "
        self.detail_matrix_text.insert(tk.END, header + "\n")
        self.detail_matrix_text.insert(tk.END, "-" * len(header) + "\n")

        # Deger satirlari
        for i, ki in enumerate(keys):
            row_lbl = KRITER_ETIKET.get(ki, ki)[:11]
            line = f"{row_lbl:<11} |"
            for j in range(min(n, len(matrix[i]) if i < len(matrix) else 0)):
                try:
                    v = float(matrix[i][j])
                    cell = self._fmt(v)[:col_w]
                    line += f" {cell:>{col_w}}"
                except Exception:
                    line += f" {'?':>{col_w}}"
            self.detail_matrix_text.insert(tk.END, line + "\n")

        self.detail_matrix_text.config(state=tk.DISABLED)

    def _edit_selected_in_tab2(self):
        """Secili profil matrisini Tab 2'ye yukleyip o sekmeyi acar."""
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", "Once bir profil secin.")
            return
        matrix = profile.get("pairwise_matrix") or None
        self.profile_label_tab2.config(text=profile.get("profile_name", "---"))
        self._rebuild_matrix_grid(matrix)
        self.nb.select(1)

    # ─── Ikili Karsilastirma ──────────────────────────────────────────────────
    def apply_pairwise_value(self):
        """Hizli karsilastirma yardimcisindan secilen degeri matrise uygular."""
        keys = self._criterion_keys
        if not keys:
            messagebox.showwarning("AHP", "Kriter yok. 'Yenile' butonuna basin.")
            return
        left = self.cb_left.get()
        right = self.cb_right.get()
        if left == right:
            messagebox.showwarning(
                "AHP", "Ayni kriter icin karsilastirma yapilmaz (diagonal daima 1)."
            )
            return
        if left not in keys or right not in keys:
            return
        try:
            idx = SAATY_ETIKETLER.index(self.cb_saaty.get())
        except ValueError:
            idx = 4
        value = SAATY_DEGERLER[idx]
        i, j = keys.index(left), keys.index(right)
        if i < len(self._matrix_entries):
            var_ij = self._matrix_entries[i][j]
            var_ji = self._matrix_entries[j][i]
            if var_ij is not None:
                var_ij.set(self._fmt(value))
            if var_ji is not None:
                var_ji.set(self._fmt(1.0 / value))

    def save_matrix_to_selected(self):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning(
                "AHP",
                "Profil secili degil.\n"
                "Tab 1'den profil secin --> 'Matrisi Duzenle' --> duzenleyin --> buradan kaydedin.",
            )
            return
        try:
            keys = profile.get("criteria_keys") or self._criterion_keys
            matrix = self._get_matrix_values()
            from app.services.ahp_profile_service import update_profile

            conn = self._conn()
            update_profile(conn, int(profile["id"]), criteria_keys=keys, pairwise_matrix=matrix)
            conn.commit()
            self.refresh()
            messagebox.showinfo("AHP", "Matris profile kaydedildi.")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    # ─── Etki & Analiz ───────────────────────────────────────────────────────
    def load_impact(self):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", "Once Tab 1'den bir profil secin.")
            return
        try:
            report = explain_weight_profile(self._conn(), int(profile["id"]))

            # Kriter kartlarini yeniden ciz
            for w in self.cards_frame.winfo_children():
                w.destroy()

            weight_table = report.get("weight_table", [])
            for row in weight_table:
                key = row.get("criterion_key", "")
                pct = float(row.get("percent", 0))
                color = KRITER_RENK.get(key, "#607D8B")
                label = KRITER_ETIKET.get(key, key)
                desc = KRITER_ACIKLAMA.get(key, "")

                card = tk.Frame(
                    self.cards_frame, bg=color, padx=10, pady=6, relief=tk.RAISED, bd=1
                )
                card.pack(side=tk.LEFT, padx=4, pady=2)
                tk.Label(
                    card, text=label, bg=color, fg="white",
                    font=("Segoe UI", 8, "bold"),
                ).pack(anchor=tk.W)
                tk.Label(
                    card, text=f"%{pct:.1f}", bg=color, fg="white",
                    font=("Segoe UI", 18, "bold"),
                ).pack()
                if desc:
                    tk.Label(
                        card,
                        text=desc[:58] + ("..." if len(desc) > 58 else ""),
                        bg=color, fg="#E8F5E9",
                        font=("Segoe UI", 7), wraplength=130, justify=tk.LEFT,
                    ).pack(anchor=tk.W)

            # Rapor metni
            self.impact_text.config(state=tk.NORMAL)
            self.impact_text.delete("1.0", tk.END)
            summary = report.get("summary_text", "")
            if summary:
                self.impact_text.insert(tk.END, summary + "\n\n")
            self.impact_text.insert(tk.END, "=" * 64 + "\n")
            self.impact_text.insert(tk.END, "KRITER AGIRLIKLARI\n")
            self.impact_text.insert(tk.END, "-" * 64 + "\n")
            for row in weight_table:
                key = row.get("criterion_key", "")
                label = KRITER_ETIKET.get(key, key)
                pct = float(row.get("percent", 0))
                filled = "#" * int(pct / 2.5)
                empty = "." * (40 - len(filled))
                self.impact_text.insert(
                    tk.END, f"{label:<18} {filled}{empty}  %{pct:.1f}\n"
                )
            self.impact_text.insert(tk.END, "\n" + "=" * 64 + "\n")
            self.impact_text.insert(tk.END, "KRITER ACIKLAMALARI\n")
            self.impact_text.insert(tk.END, "-" * 64 + "\n\n")
            for row in weight_table:
                key = row.get("criterion_key", "")
                label = KRITER_ETIKET.get(key, key)
                desc = KRITER_ACIKLAMA.get(key, "")
                if desc:
                    self.impact_text.insert(tk.END, f"> {label}\n  {desc}\n\n")
            self.impact_text.config(state=tk.DISABLED)

        except Exception as exc:
            messagebox.showerror("AHP Etki", self._format_error(exc))

    # ─── Profil CRUD ─────────────────────────────────────────────────────────
    def create_default_profile(self):
        # Profil adini kullanici elle girer
        ad = simpledialog.askstring(
            "Yeni AHP Profili",
            "Profil adi (zorunlu):",
            parent=self,
        )
        if ad is None:
            return  # iptal
        ad = ad.strip()
        if not ad:
            messagebox.showwarning("AHP", "Profil adi bos olamaz.")
            return
        notlar = simpledialog.askstring(
            "Yeni AHP Profili",
            "Aciklama / not (istege bagli):",
            parent=self,
        ) or "UI uzerinden olusturuldu."
        try:
            conn = self._conn()
            profile = create_profile(
                conn,
                profile_name=ad,
                name=ad,
                criteria_keys=self._criterion_keys or None,
                source="manual",
                status="draft",
                notes=notlar,
            )
            conn.commit()
            self.refresh()
            # Yeni olusturulan profili otomatik sec
            self._select_profile_by_id(int(profile["id"]))
            messagebox.showinfo(
                "AHP",
                f"Profil olusturuldu: #{profile['id']} — '{ad}'\n\n"
                "Sonraki adimlar:\n"
                "1) 'Ikili Karsilastirma' sekmesinde matrisi doldurun\n"
                "2) Dogrula -> Onaya Gonder -> Onayla\n"
                "3) 'Aktif Yap' ile TOPSIS'in kullanacagi profil yapin",
            )
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def _select_profile_by_id(self, profile_id: int):
        """Verilen profile_id'ye sahip treeview satirini sec ve detayini goster."""
        for item, pid in self._profile_rows.items():
            if int(pid) == int(profile_id):
                self.profile_tree.selection_set(item)
                self.profile_tree.focus(item)
                self.profile_tree.see(item)
                self._on_profile_select()
                return

    def validate_selected(self):
        self._profile_action(
            lambda conn, pid: validate_profile(conn, pid), "Profil dogrulandi."
        )

    def submit_selected(self):
        self._profile_action(
            lambda conn, pid: submit_for_approval(conn, pid), "Profil onaya gonderildi."
        )

    def approve_selected(self):
        self._profile_action(
            lambda conn, pid: approve_profile(conn, pid, approved_by="ui"),
            "Profil onaylandi.",
        )

    def reject_selected(self):
        reason = simpledialog.askstring("AHP Reddet", "Red gerekcesinizi yazin:")
        if not reason:
            return
        self._profile_action(
            lambda conn, pid: reject_profile(conn, pid, reason, rejected_by="ui"),
            "Profil reddedildi.",
        )

    def activate_selected(self):
        self._profile_action(
            lambda conn, pid: activate_profile(conn, pid, actor="ui"),
            "Profil aktif yapildi.",
        )

    def clone_selected(self):
        self._profile_action(
            lambda conn, pid: clone_profile(conn, pid, actor="ui"), "Profil klonlandi."
        )

    def archive_selected(self):
        self._profile_action(
            lambda conn, pid: archive_profile(conn, pid, actor="ui"), "Profil arsivlendi."
        )

    # ─── Yardimci ────────────────────────────────────────────────────────────
    def _profile_action(self, action, message: str):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", "Once bir profil secin.")
            return
        try:
            conn = self._conn()
            action(conn, int(profile["id"]))
            conn.commit()
            self.refresh()
            messagebox.showinfo("AHP", message)
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def _selected_profile(self):
        selected = self.profile_tree.selection()
        if not selected:
            return None
        profile_id = self._profile_rows.get(selected[0])
        return get_profile(self._conn(), int(profile_id)) if profile_id else None

    def _get_matrix_values(self) -> list[list[float]]:
        """Entry widget'lardan NxN matris degerlerini okur."""
        keys = self._criterion_keys
        n = len(keys)
        matrix = [[1.0] * n for _ in range(n)]
        for i in range(min(n, len(self._matrix_entries))):
            for j in range(min(n, len(self._matrix_entries[i]))):
                if i == j:
                    continue
                var = self._matrix_entries[i][j]
                if var is not None:
                    try:
                        matrix[i][j] = self._parse_val(var.get())
                    except Exception:
                        matrix[i][j] = 1.0
        return matrix

    def _reset_matrix(self):
        """Tum off-diagonal hucreleri 1 olarak sifirlar."""
        for row in self._matrix_entries:
            for var in row:
                if var is not None:
                    var.set("1")

    def _copy_matrix_json(self):
        """Mevcut matris degerlerini JSON olarak panoya kopyalar."""
        try:
            matrix = self._get_matrix_values()
            json_str = json.dumps(matrix, ensure_ascii=False, indent=2)
            self.clipboard_clear()
            self.clipboard_append(json_str)
            messagebox.showinfo("AHP", "Matris JSON olarak panoya kopyalandi.")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    @staticmethod
    def _fmt(v: float) -> str:
        """Float -> okunabilir string: 0.333->1/3, 3.0->3"""
        for num, den, text in [
            (1, 9, "1/9"), (1, 7, "1/7"), (1, 5, "1/5"), (1, 3, "1/3"),
            (1, 2, "1/2"), (1, 1, "1"), (2, 1, "2"), (3, 1, "3"),
            (4, 1, "4"), (5, 1, "5"), (6, 1, "6"), (7, 1, "7"),
            (8, 1, "8"), (9, 1, "9"),
        ]:
            if abs(v - num / den) < 1e-6:
                return text
        return f"{v:.3f}".rstrip("0").rstrip(".")

    @staticmethod
    def _parse_val(s: str) -> float:
        """'1/3' veya '3' veya '3.5' -> float."""
        s = s.strip()
        if not s:
            return 1.0
        if "/" in s:
            parts = s.split("/", 1)
            return float(parts[0]) / float(parts[1])
        return float(s)

    @staticmethod
    def _scope_text(profile) -> str:
        parts = [str(profile.get("scope_type") or "global")]
        if profile.get("faculty_id"):
            parts.append(f"F:{profile['faculty_id']}")
        if profile.get("department_id"):
            parts.append(f"B:{profile['department_id']}")
        if profile.get("semester"):
            parts.append(str(profile["semester"]))
        return " / ".join(parts)

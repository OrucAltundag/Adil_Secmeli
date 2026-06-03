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
    delete_profile,
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


class _NewProfileDialog(tk.Toplevel):
    """Yeni AHP profili oluşturmak için tek pencerede tüm alanları toplayan modal dialog."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self.title("Yeni AHP Profili Oluştur")
        self.resizable(False, False)
        self.result: dict | None = None
        self._build()
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        px = parent.winfo_rootx() + max((parent.winfo_width() - w) // 2, 0)
        py = parent.winfo_rooty() + max((parent.winfo_height() - h) // 2, 0)
        self.geometry(f"{w}x{h}+{px}+{py}")
        self.transient(parent)
        self.grab_set()
        self._name_entry.focus_set()
        self.wait_window(self)

    def _build(self) -> None:
        # Renkli başlık şeridi
        hdr = tk.Frame(self, bg="#1B5E20")
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="Yeni AHP Profili Oluştur",
            bg="#1B5E20", fg="white",
            font=("Segoe UI", 12, "bold"),
            pady=14, padx=18, anchor="w",
        ).pack(fill=tk.X)

        body = ttk.Frame(self, padding=18)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)

        # ─ Profil Adı ─
        ttk.Label(body, text="Profil Adı  *", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 3)
        )
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(
            body, textvariable=self._name_var, width=42, font=("Segoe UI", 10)
        )
        self._name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # ─ Notlar ─
        ttk.Label(body, text="Notlar / Açıklama  (isteğe bağlı)", font=("Segoe UI", 9)).grid(
            row=2, column=0, sticky="w", pady=(0, 3)
        )
        self._notes = tk.Text(
            body, height=5, width=42,
            font=("Segoe UI", 9), wrap=tk.WORD,
            relief=tk.FLAT, bd=1,
            highlightthickness=1, highlightbackground="#BDBDBD",
            bg="#F9F9F9",
        )
        self._notes.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        # ─ Kapsam + Yıl ─
        meta = ttk.Frame(body)
        meta.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        ttk.Label(meta, text="Kapsam:").pack(side=tk.LEFT)
        self._scope_var = tk.StringVar(value="global")
        ttk.Combobox(
            meta, textvariable=self._scope_var,
            values=["global", "faculty", "department"],
            state="readonly", width=14,
        ).pack(side=tk.LEFT, padx=(4, 20))
        ttk.Label(meta, text="Yıl:").pack(side=tk.LEFT)
        self._year_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self._year_var, width=8).pack(side=tk.LEFT, padx=4)

        # ─ Butonlar ─
        ttk.Separator(body, orient=tk.HORIZONTAL).grid(
            row=5, column=0, sticky="ew", pady=(0, 12)
        )
        btn_row = ttk.Frame(body)
        btn_row.grid(row=6, column=0, sticky="e")
        ttk.Button(btn_row, text="İptal", command=self.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_row, text="  Oluştur  ", command=self._ok).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _ok(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Yeni Profil", "Profil adı boş olamaz.", parent=self)
            self._name_entry.focus_set()
            return
        notes = self._notes.get("1.0", tk.END).strip() or "UI üzerinden oluşturuldu."
        year_s = self._year_var.get().strip()
        self.result = {
            "name": name,
            "notes": notes,
            "scope_type": self._scope_var.get(),
            "year": int(year_s) if year_s.isdigit() else None,
        }
        self.destroy()


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
        self._profile_list_ids: list[int] = []
        self._profile_options: dict[str, int] = {}
        self._profile_cache: dict[int, dict] = {}
        self._selected_profile_id: int | None = None
        self._criterion_keys: list[str] = []
        self._matrix_entries: list[list] = []   # StringVar (off-diag) | None (diag)
        self._current_weights: dict[str, float] = {}
        self._current_cr: float | None = None
        # Tab2'de duzenlenen profilin id'si (Tab1 secimi degisse de korunur)
        self._editing_profile_id: int | None = None
        self._build_ui()

    _TR_ASCII = {
        "ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
        "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
        "\xef": "i", "�": "i",
    }

    @classmethod
    def _ascii_safe(cls, s: str) -> str:
        """Tkinter'in render edemedigi karakterleri ASCII'ye indir
        (DB cagrisi yok; '(isimsiz)' sorununu kalici onler)."""
        if not s:
            return s
        out = "".join(cls._TR_ASCII.get(ch, ch) for ch in s)
        try:
            out.encode("ascii")
            return out
        except UnicodeEncodeError:
            return out.encode("ascii", "ignore").decode("ascii") or s

    @classmethod
    def _profile_display_name(cls, profile: dict) -> str:
        raw = profile.get("profile_name") or profile.get("name") or ""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        name = cls._ascii_safe(str(raw).strip())
        if name.lower() in {"", "(isimsiz)", "isimsiz", "none", "null", "---"}:
            return f"AHP Profili #{profile.get('id') or '?'}"
        return name

    @classmethod
    def _profile_option_label(cls, profile: dict) -> str:
        name = cls._profile_display_name(profile)
        status = DURUM_ETIKET.get(str(profile.get("status") or "draft"), str(profile.get("status") or "draft"))
        active = " | AKTIF" if profile.get("is_active") else ""
        return f"#{profile.get('id')} - {name} | {status}{active}"

    @classmethod
    def _profile_list_line(cls, profile: dict) -> str:
        name = cls._profile_display_name(profile)
        scope = str(profile.get("scope_type") or "global")
        version = str(profile.get("version") or "1")
        status = DURUM_ETIKET.get(str(profile.get("status") or "draft"), str(profile.get("status") or "draft"))
        active = " | AKTIF" if profile.get("is_active") else ""
        return f"#{profile.get('id')}  {name}  |  {scope}  |  v{version}  |  {status}{active}"

    # ─── Veritabani ──────────────────────────────────────────────────────────
    def _conn(self):
        conn = getattr(getattr(self.app, "db", None), "conn", None)
        if conn is None:
            raise RuntimeError(self._friendly_backend_error())
        return conn

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Veritabanı bağlantısı kurulamadı. Geçerli veritabanı dosyasını seçip yeniden deneyin."

    @staticmethod
    def _profile_required_message() -> str:
        return "Profil listesinden bir profil seçin. Liste boşsa '+ Yeni Profil' ile profil oluşturun."

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
        ttk.Button(header, text="Tümünü Temizle", command=self.delete_all_profiles).pack(side=tk.RIGHT, padx=2)
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

        # Sol: tablo yerine acik secim paneli
        left = ttk.LabelFrame(paned, text="  Profil Secimi  ", padding=8)
        paned.add(left, weight=2)

        self.selected_profile_var = tk.StringVar(value="Secili profil yok")
        tk.Label(
            left,
            textvariable=self.selected_profile_var,
            bg="#E8F5E9",
            fg="#1B5E20",
            font=("Segoe UI", 9, "bold"),
            anchor=tk.W,
            padx=8,
            pady=6,
            relief=tk.GROOVE,
            bd=1,
        ).pack(fill=tk.X, pady=(0, 8))

        picker = ttk.Frame(left)
        picker.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(picker, text="Profil:").pack(side=tk.LEFT)
        self.profile_picker_var = tk.StringVar()
        self.profile_picker = ttk.Combobox(
            picker,
            textvariable=self.profile_picker_var,
            state="readonly",
            width=46,
        )
        self.profile_picker.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.profile_picker.bind("<<ComboboxSelected>>", self._select_profile_from_picker)
        ttk.Button(picker, text="Profili Sec", command=self._select_profile_from_picker).pack(side=tk.LEFT)

        ttk.Label(
            left,
            text="Tek tikla profil secin. Cift tik: matrisi duzenle.",
            foreground="#455A64",
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 4))

        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.profile_listbox = tk.Listbox(
            list_frame,
            activestyle="dotbox",
            exportselection=False,
            font=("Segoe UI", 9),
            height=18,
            selectmode=tk.SINGLE,
        )
        # Backwards-compatibility alias: some code/tests reference `profile_tree`.
        # Map it to the listbox so selection APIs remain available.
        self.profile_tree = self.profile_listbox
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.profile_listbox.yview)
        self.profile_listbox.configure(yscrollcommand=list_scroll.set)
        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_list_select)
        self.profile_listbox.bind(
            "<Double-Button-1>",
            lambda _e: (self._on_profile_list_select(), self._edit_selected_in_tab2()),
        )

        quick_actions = ttk.Frame(left)
        quick_actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(quick_actions, text="Aktif Yap", command=self.activate_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_actions, text="Matrisi Duzenle", command=self._edit_selected_in_tab2).pack(side=tk.LEFT, padx=2)

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

        # ─ Aksiyon butonlari ─
        action_frame = ttk.Frame(frame, padding=(0, 8, 0, 0))
        action_frame.pack(fill=tk.X)

        lc = ttk.LabelFrame(action_frame, text=" Yaşam Döngüsü ", padding=(8, 4))
        lc.pack(side=tk.LEFT, padx=(0, 10))
        for text, cmd in [
            ("Doğrula", self.validate_selected),
            ("Onaya Gönder", self.submit_selected),
            ("Onayla", self.approve_selected),
            ("Reddet", self.reject_selected),
        ]:
            ttk.Button(lc, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        mgmt = ttk.LabelFrame(action_frame, text=" Yönetim ", padding=(8, 4))
        mgmt.pack(side=tk.LEFT, padx=(0, 10))
        for text, cmd in [
            ("Aktif Yap", self.activate_selected),
            ("Yeniden Adlandır", self.rename_selected),
            ("Klonla", self.clone_selected),
            ("Arşivle", self.archive_selected),
            ("Sil", self.delete_selected),
        ]:
            ttk.Button(mgmt, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            action_frame, text="Matrisi Düzenle →",
            command=self._edit_selected_in_tab2,
        ).pack(side=tk.LEFT)

        # Durum renk aciklamasi
        legend = ttk.Frame(frame)
        legend.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(legend, text="Durum:", font=("Segoe UI", 7, "italic")).pack(side=tk.LEFT, padx=(0, 4))
        for status in ("active", "approved", "pending_approval", "validated", "draft", "archived", "rejected"):
            tk.Label(
                legend,
                text=DURUM_ETIKET[status],
                bg=DURUM_RENK[status], padx=4, pady=1,
                font=("Segoe UI", 7), relief=tk.GROOVE, bd=1,
            ).pack(side=tk.LEFT, padx=2)

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
            text="--- (Profil listesinden seçim yapıp 'Matrisi Duzenle' tiklayin)",
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
        ttk.Button(
            mat_btns, text="Kaydet ve Onayla (AKTIF yap)",
            command=self.save_and_approve_matrix,
        ).pack(side=tk.RIGHT, padx=2)
        ttk.Button(
            mat_btns, text="Sadece Kaydet",
            command=lambda: self.save_matrix_to_selected(False),
        ).pack(side=tk.RIGHT, padx=2)

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
            requested_profile_id = self._selected_profile_id

            self._criterion_keys = [row["criterion_key"] for row in criteria]
            self.cb_left["values"] = self._criterion_keys
            self.cb_right["values"] = self._criterion_keys
            if self._criterion_keys:
                self.cb_left.set(self._criterion_keys[0])
                self.cb_right.set(
                    self._criterion_keys[min(1, len(self._criterion_keys) - 1)]
                )

            self._profile_list_ids.clear()
            self._profile_options.clear()
            self._profile_cache.clear()
            self.profile_listbox.delete(0, tk.END)

            active_profile = None
            for profile in profiles:
                # Performans: list_ahp_profiles zaten tam veriyi donuyor;
                # per-satir get_profile cagrisi (ensure_schema DDL dahil)
                # cok yavaslatiyordu — kaldirildi.
                status = profile.get("status") or "draft"
                is_active = bool(profile.get("is_active"))
                if is_active:
                    active_profile = profile
                profile_id = int(profile["id"])
                self._profile_cache[profile_id] = profile
                option_label = self._profile_option_label(profile)
                self._profile_options[option_label] = profile_id
                self._profile_list_ids.append(profile_id)
                self.profile_listbox.insert(tk.END, self._profile_list_line(profile))
                row_index = self.profile_listbox.size() - 1
                try:
                    self.profile_listbox.itemconfig(
                        row_index,
                        background=DURUM_RENK.get(status, "#FFFFFF"),
                    )
                except Exception:
                    pass

            self.profile_picker["values"] = list(self._profile_options.keys())

            if active_profile:
                cr = active_profile.get("consistency_ratio")
                cr_str = f"   |   CR: {float(cr):.3f}" if cr is not None else ""
                self.banner_var.set(
                    f"* Aktif Profil: {self._profile_display_name(active_profile)}"
                    f"   (v{active_profile.get('version')}){cr_str}"
                )
            else:
                self.banner_var.set(
                    "Aktif profil yok --- bir profili secip 'Aktif Yap' ile etkinlestirin."
                )

            self._rebuild_matrix_grid()

            # Refresh sonrasi panel bos kalmasin: aktif profili (yoksa ilk
            # satiri) otomatik sec ve detayini goster.
            if self._profile_list_ids:
                target_id = None
                if requested_profile_id and int(requested_profile_id) in self._profile_cache:
                    target_id = int(requested_profile_id)
                elif active_profile:
                    target_id = int(active_profile["id"])
                else:
                    target_id = self._profile_list_ids[0]
                self._select_profile_by_id(target_id)
                self._on_profile_select()
            else:
                self._selected_profile_id = None
                self.selected_profile_var.set("Secili profil yok")
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
                text="Aktif kriter bulunamadi. Kriterleri yenileyin veya kriter girişlerini kontrol edin.",
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
                "Gecerli ornekler: 1/9, 1/7, 1/5, 1/3, 1, 3, 5, 7, 9 veya pozitif sayi",
            )

    # ─── Hesaplama ────────────────────────────────────────────────────────────
    def calculate_current_matrix(self):
        try:
            keys = self._criterion_keys
            if not keys:
                messagebox.showwarning("AHP", "Kriter listesi bos. Kriterleri yenileyin veya kriter girişlerini kontrol edin.")
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
    def _on_profile_list_select(self, _event=None):
        selected = self.profile_listbox.curselection()
        if not selected:
            return
        index = int(selected[0])
        if index >= len(self._profile_list_ids):
            return
        self._set_selected_profile_id(self._profile_list_ids[index])
        self._on_profile_select()

    def _select_profile_from_picker(self, _event=None):
        label = self.profile_picker_var.get()
        profile_id = self._profile_options.get(label)
        if not profile_id:
            return
        self._set_selected_profile_id(profile_id)
        self._on_profile_select()

    def _set_selected_profile_id(self, profile_id: int):
        self._selected_profile_id = int(profile_id)
        if int(profile_id) in self._profile_list_ids:
            index = self._profile_list_ids.index(int(profile_id))
            self.profile_listbox.selection_clear(0, tk.END)
            self.profile_listbox.selection_set(index)
            self.profile_listbox.activate(index)
            self.profile_listbox.see(index)
        for label, pid in self._profile_options.items():
            if int(pid) == int(profile_id):
                self.profile_picker_var.set(label)
                break
        profile = self._profile_cache.get(int(profile_id))
        if profile:
            self.selected_profile_var.set(
                f"SECILI: #{profile_id} - {self._profile_display_name(profile)}"
            )
        self._update_selection_marks()

    def _update_selection_marks(self):
        # Listbox'un secili satir rengi ve ustteki "SECILI" etiketi secimi gosterir.
        return

    def _on_profile_select(self):
        try:
            profile = self._selected_profile()
            if not profile:
                return

            name = self._profile_display_name(profile)

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
            messagebox.showerror("AHP", f"Profil detayı yüklenemedi: {self._format_error(exc)}")

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
        """Secili profilin matrisini Tab 2'ye yukle (AYNI profil duzenlenir,
        yeni profil OLUSTURULMAZ). Profil id'si sabitlenir."""
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", self._profile_required_message())
            return
        self._editing_profile_id = int(profile["id"])
        matrix = profile.get("pairwise_matrix") or None
        ad = self._profile_display_name(profile)
        self.profile_label_tab2.config(
            text=f"#{profile['id']} — {ad}  (bu profil duzenleniyor)"
        )
        self._rebuild_matrix_grid(matrix)
        self.nb.select(1)

    # ─── Ikili Karsilastirma ──────────────────────────────────────────────────
    def apply_pairwise_value(self):
        """Hizli karsilastirma yardimcisindan secilen degeri matrise uygular."""
        keys = self._criterion_keys
        if not keys:
            messagebox.showwarning("AHP", "Kriter yok. Kriterleri yenileyin veya kriter girişlerini kontrol edin.")
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

    def _editing_profile(self):
        """Tab2'de duzenlenen profili dondur. Oncelik sirasi:
        1) acik 'Matrisi Duzenle' id'si  2) Tab1 secimi
        3) AKTIF profil  4) listedeki ilk profil.
        Asla gecersiz (0/None) id ile cagrilmaz."""
        conn = self._conn()

        # 1) Acikca duzenlenen profil
        pid = self._editing_profile_id
        if pid and int(pid) > 0:
            try:
                p = get_profile(conn, int(pid))
                if p:
                    return p
            except Exception:
                pass

        # 2) Tab1 secimi
        sel = self._selected_profile()
        if sel and int(sel.get("id") or 0) > 0:
            self._editing_profile_id = int(sel["id"])
            return sel

        # 3) Aktif profil / 4) ilk profil
        try:
            profiles = list_ahp_profiles(conn)
        except Exception:
            profiles = []
        if profiles:
            aktif = next(
                (p for p in profiles if p.get("is_active")), profiles[0]
            )
            self._editing_profile_id = int(aktif["id"])
            return get_profile(conn, int(aktif["id"])) or aktif
        return None

    def save_matrix_to_selected(self, then_approve: bool = False):
        profile = self._editing_profile()
        if not profile:
            messagebox.showwarning(
                "AHP",
                "Duzenlenecek profil belirsiz.\n"
                "Profil listesinden profil secip 'Matrisi Duzenle' butonuna basin.",
            )
            return
        try:
            from app.services.ahp_profile_service import update_profile

            pid = int(profile["id"])
            keys = profile.get("criteria_keys") or self._criterion_keys
            matrix = self._get_matrix_values()
            conn = self._conn()
            # AYNI profil yerinde guncellenir (yeni profil olusmaz)
            update_profile(conn, pid, criteria_keys=keys, pairwise_matrix=matrix)
            approval_error: tuple[str, Exception] | None = None
            if then_approve:
                # Dogrula -> onaya gonder -> onayla -> aktif yap zincirini
                # tek tusla calistir (hata olursa o adimda durur)
                for step_name, fn in (
                    ("Dogrula", lambda: validate_profile(conn, pid)),
                    ("Onaya Gonder", lambda: submit_for_approval(conn, pid)),
                    ("Onayla", lambda: approve_profile(conn, pid, approved_by="ui")),
                    ("Aktif Yap", lambda: activate_profile(conn, pid, actor="ui")),
                ):
                    try:
                        fn()
                    except Exception as step_exc:
                        approval_error = (step_name, step_exc)
                        break
            conn.commit()
            self.refresh()
            self._select_profile_by_id(pid)
            if then_approve:
                if approval_error:
                    step_name, step_exc = approval_error
                    messagebox.showwarning(
                        "AHP",
                        "Matris kaydedildi ancak profil onay/aktivasyon akışı tamamlanmadı.\n"
                        f"Duran adım: {step_name}\n"
                        f"Neden: {self._format_error(step_exc)}",
                    )
                else:
                    messagebox.showinfo(
                        "AHP",
                        "Matris kaydedildi, profil onaylandi ve AKTIF yapildi.\n"
                        "Artik Karar Merkezi -> Calistirmalar'da TOPSIS bu profili kullanir.",
                    )
            else:
                messagebox.showinfo("AHP", "Matris ayni profile kaydedildi (yeni profil olusmadi).")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def save_and_approve_matrix(self):
        if not messagebox.askyesno(
            "Kaydet ve Onayla",
            "Matris kaydedilip profil otomatik olarak Dogrula -> Onayla -> "
            "AKTIF yapilacak. Devam edilsin mi?",
        ):
            return
        self.save_matrix_to_selected(then_approve=True)

    # ─── Etki & Analiz ───────────────────────────────────────────────────────
    def load_impact(self):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", self._profile_required_message())
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
        dlg = _NewProfileDialog(self)
        if dlg.result is None:
            return
        data = dlg.result
        try:
            conn = self._conn()
            profile = create_profile(
                conn,
                profile_name=data["name"],
                name=data["name"],
                criteria_keys=self._criterion_keys or None,
                source="manual",
                status="draft",
                notes=data["notes"],
                scope_type=data["scope_type"],
                year=data["year"],
            )
            conn.commit()
            self.refresh()
            self._select_profile_by_id(int(profile["id"]))
            messagebox.showinfo(
                "AHP",
                f"Profil oluşturuldu: #{profile['id']} — '{data['name']}'\n\n"
                "Sıradaki adım: 'İkili Karşılaştırma' sekmesinde matrisi doldurup\n"
                "Kaydet ve Onayla (AKTİF Yap) butonuna basın.",
            )
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def _select_profile_by_id(self, profile_id: int):
        """Verilen profile_id'ye sahip profil satirini sec ve detayini goster."""
        self._set_selected_profile_id(int(profile_id))
        self._on_profile_select()

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
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", self._profile_required_message())
            return
        reason = simpledialog.askstring("AHP Reddet", "Red gerekcesinizi yazin:")
        if not reason:
            return
        # Kullanici istegi: reddedilen profil ayni zamanda SILINIR.
        if not messagebox.askyesno(
            "AHP Reddet + Sil",
            f"'{self._profile_display_name(profile)}' profili "
            f"reddedilip KALICI olarak silinecek. Onayliyor musunuz?",
        ):
            return
        try:
            conn = self._conn()
            pid = int(profile["id"])
            try:
                reject_profile(conn, pid, reason, rejected_by="ui")
            except Exception:
                pass  # reddetme basarisiz olsa bile silmeyi dene
            delete_profile(conn, pid)
            conn.commit()
            self._selected_profile_id = None
            self.refresh()
            messagebox.showinfo("AHP", "Profil reddedildi ve silindi.")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def delete_selected(self):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", self._profile_required_message())
            return
        ad = self._profile_display_name(profile)
        if not messagebox.askyesno(
            "Profil Sil",
            f"'{ad}' profili KALICI olarak silinecek. Onayliyor musunuz?\n"
            "(Aktif profil silinemez.)",
        ):
            return
        try:
            conn = self._conn()
            delete_profile(conn, int(profile["id"]))
            conn.commit()
            self._selected_profile_id = None
            self.refresh()
            messagebox.showinfo("AHP", f"Profil silindi: '{ad}'")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def rename_selected(self):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", self._profile_required_message())
            return
        eski = self._profile_display_name(profile)
        yeni = simpledialog.askstring(
            "Profil Adi Degistir", "Yeni profil adi:",
            initialvalue=str(eski), parent=self,
        )
        if yeni is None:
            return
        yeni = yeni.strip()
        if not yeni:
            messagebox.showwarning("AHP", "Profil adi bos olamaz.")
            return
        try:
            from app.services.ahp_profile_service import update_profile

            conn = self._conn()
            pid = int(profile["id"])
            update_profile(conn, pid, profile_name=yeni, name=yeni)
            conn.commit()
            self.refresh()
            self._select_profile_by_id(pid)
            messagebox.showinfo("AHP", f"Profil adi degistirildi: '{yeni}'")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

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

    def delete_all_profiles(self):
        if not messagebox.askyesno(
            "Tüm Profilleri Sil",
            "Tüm AHP profilleri kalıcı olarak silinecek.\n"
            "Bu işlem geri alınamaz. Emin misiniz?",
        ):
            return
        try:
            conn = self._conn()
            profiles = list_ahp_profiles(conn)
            for p in profiles:
                try:
                    delete_profile(conn, int(p["id"]))
                except Exception:
                    pass
            conn.commit()
            self.refresh()
            messagebox.showinfo("AHP", "Tüm profiller silindi.")
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    # ─── Yardimci ────────────────────────────────────────────────────────────
    def _profile_action(self, action, message: str):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", self._profile_required_message())
            return
        try:
            conn = self._conn()
            pid = int(profile["id"])
            action(conn, pid)
            conn.commit()
            self.refresh()
            self._select_profile_by_id(pid)
            messagebox.showinfo("AHP", message)
        except Exception as exc:
            messagebox.showerror("AHP", self._format_error(exc))

    def _selected_profile(self):
        # Prefer tree selection (newer UI) but fall back to listbox for compatibility.
        tree = getattr(self, "profile_tree", None)
        if tree is not None:
            try:
                selected = tree.selection()
                if selected:
                    profile_id = self._profile_rows.get(selected[0])
                    if profile_id:
                        return get_profile(self._conn(), int(profile_id))
            except Exception as exc:
                messagebox.showerror("AHP", f"Profil yüklenemedi: {self._format_error(exc)}")
                return None

        # Fallback to older listbox-based selection for backward compatibility
        listbox = getattr(self, "profile_listbox", None)
        selected = listbox.curselection() if listbox is not None else ()
        if selected:
            index = int(selected[0])
            if index < len(self._profile_list_ids):
                self._selected_profile_id = int(self._profile_list_ids[index])
        if not self._selected_profile_id:
            if self._profile_list_ids:
                self._set_selected_profile_id(self._profile_list_ids[0])
            else:
                return None
        profile = get_profile(self._conn(), int(self._selected_profile_id))
        if not profile:
            self._selected_profile_id = None
            self._update_selection_marks()
        return profile

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

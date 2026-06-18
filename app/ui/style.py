# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/style.py — Uygulama Gorsel Tema Yonetimi
# =============================================================================
# Tum ttk widget'lari icin merkezi stil tanimlari.
# Renk paleti (COLORS), font tanimlari (FONTS) ve apply_style() fonksiyonu.
# Tema: clam (platformlar arasi tutarli gorunum).
# =============================================================================
import tkinter as tk
from tkinter import ttk

# İstersen sabitleri burada tut
COLORS = {
    # Yeni karar ekranlarının kullandığı uyumluluk renkleri. Bunlar eski
    # uygulama temasını global olarak değiştirmez; yalnız yerel kartlarda
    # sabit renk anahtarları sağlar.
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "text": "#172033",
    "muted": "#64748b",
    "success": "#15803d",
    "success_soft": "#dcfce7",
    "warning_soft": "#fef3c7",
    "sidebar_bg": "#0f172a",
    "sidebar_fg": "#e2e8f0",
    "btn_bg": "#111827",
    "btn_bg_active": "#1f2937",
}


def style_text_widget(widget: tk.Text, *, mono: bool = False) -> None:
    """Yeni ekranlardaki metin alanlarını eski, sade temayla uyumlu tut."""

    widget.configure(
        bg="#ffffff",
        fg="#172033",
        insertbackground="#172033",
        selectbackground="#dbeafe",
        selectforeground="#172033",
        relief=tk.SUNKEN,
        borderwidth=1,
        padx=6,
        pady=6,
        font=("Consolas", 9) if mono else ("Segoe UI", 9),
    )

FONTS = {
    "header": ("Segoe UI", 12, "bold"),
    "sidebar": ("Segoe UI", 10, "bold"),
    "tree": ("Segoe UI", 9),
    "tree_head": ("Segoe UI", 9, "bold"),
}


def apply_style(root: tk.Tk):
    """Uygulama genel teması (tek yerden yönet)."""
    root.title("Adil Seçmeli • Masaüstü")
    root.geometry("1280x760")
    root.minsize(1100, 680)

    style = ttk.Style()

    # theme seç (bazı platformlarda farklı olabilir)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Sidebar
    style.configure(
        "Sidebar.TFrame",
        background=COLORS["sidebar_bg"]
    )
    style.configure(
        "Sidebar.TLabel",
        background=COLORS["sidebar_bg"],
        foreground=COLORS["sidebar_fg"],
        font=FONTS["sidebar"]
    )
    style.configure(
        "Sidebar.TButton",
        background=COLORS["btn_bg"],
        foreground="#e5e7eb",
        padding=(10, 6)
    )
    style.map(
        "Sidebar.TButton",
        background=[("active", COLORS["btn_bg_active"])]
    )

    # Header
    style.configure(
        "Header.TLabel",
        font=FONTS["header"]
    )

    # Treeview
    style.configure(
        "Treeview",
        rowheight=26,
        font=FONTS["tree"]
    )
    style.configure(
        "Treeview.Heading",
        font=FONTS["tree_head"]
    )

    # İstersen genel buton stili de tanımlayabilirsin
    style.configure(
        "Primary.TButton",
        padding=(10, 6)
    )

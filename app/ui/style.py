# app/ui/style.py
import tkinter as tk
from tkinter import ttk

# İstersen sabitleri burada tut
COLORS = {
    "sidebar_bg": "#0f172a",
    "sidebar_fg": "#e2e8f0",
    "btn_bg": "#111827",
    "btn_bg_active": "#1f2937",
}

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

# -*- coding: utf-8 -*-
"""Genel Bakış / Algoritma Rehberi sayfası — kurulum smoke testi."""

from __future__ import annotations

import pytest


def test_overview_page_constructs_without_db():
    """Sayfa DB bağımlılığı olmadan (app=None) çökmeden kurulmalı."""
    try:
        import tkinter as tk
    except Exception:  # pragma: no cover
        pytest.skip("tkinter yok.")

    from app.ui.tabs.overview_page import ALGORITMALAR, PIPELINE, OverviewPage

    # İçerik bütünlüğü: boru hattı 7 adım, her algoritma 4 alan dolu.
    assert len(PIPELINE) == 7
    assert len(ALGORITMALAR) >= 6
    for ad, neden, formul, nerede in ALGORITMALAR:
        assert ad and neden and formul and nerede

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok.")
    try:
        root.withdraw()
        page = OverviewPage(root, app=None)
        page.pack()
        root.update_idletasks()
        assert page.winfo_children()
        # refresh() statik içerikte güvenli no-op olmalı.
        page.refresh()
    finally:
        root.destroy()

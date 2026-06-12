# -*- coding: utf-8 -*-
"""Tablo kataloğu (DB görüntüleyici Türkçe ad + bilgi) testleri."""

from __future__ import annotations

from app.ui.table_catalog import (
    TABLE_CATALOG,
    display_name,
    get_table_info,
    physical_from_display,
)

# Görüntüleyicide görülen çekirdek tablolar — katalogda olmalı.
CEKIRDEK = [
    "ders", "fakulte", "bolum", "mufredat", "mufredat_ders",
    "ders_kriterleri", "performans", "populerlik", "skor",
    "decision_runs", "course_decisions", "ahp_weight_profiles",
    "semester_plan_runs", "havuz", "anket_sonuclari",
]


def test_core_tables_have_full_metadata():
    for t in CEKIRDEK:
        assert t in TABLE_CATALOG, f"Katalogda eksik: {t}"
        info = get_table_info(t)
        assert info["tr"] and info["desc"] and info["usage"] and info["grup"]


def test_display_physical_roundtrip():
    for t in list(TABLE_CATALOG)[:30] + ["bilinmeyen_tablo_xyz"]:
        label = display_name(t)
        assert physical_from_display(label) == t


def test_unknown_table_has_safe_fallback():
    info = get_table_info("hic_olmayan_tablo")
    assert info["tr"]  # boş değil
    assert "hic_olmayan_tablo" in info["usage"]
    assert info["grup"]


def test_turkish_names_are_distinct_for_core():
    adlar = [get_table_info(t)["tr"] for t in CEKIRDEK]
    assert len(set(adlar)) == len(adlar)  # çekirdek adlar benzersiz

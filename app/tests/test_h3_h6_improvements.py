# -*- coding: utf-8 -*-
"""H3-H6 iyilestirmeleri regresyon testleri (2026-06-15).

H3: TOPSIS dejenere kriter tespiti (varyansi 0 olan sutunlar isaretlenir).
H4: Ham basari yeterliyse gocereli sifirlanma korumasi (dusme onerilmez).
H5: Mantiksiz anket verisi (secen > katilimci) -> notr 0.5.
H6: Dual wrapper varsayilan strict_ahp=True.

bkz. docs/MATEMATIKSEL_INCELEME_RAPORU_2026-06-15.md
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pandas as pd
import pytest

from app.services.calculation import (
    MIN_RAW_SUCCESS_FLOOR,
    KararMotoru,
    _read_course_metrics,
    evaluate_drop_reasons,
    should_drop_course,
)


# -----------------------------
# H3: Dejenere kriter tespiti
# -----------------------------


def test_h3_topsis_marks_degenerate_criteria():
    """Tum dersler ayni populerlik degerine sahipse o kriter dejenere isaretlenir."""
    motor = KararMotoru()
    df = pd.DataFrame([
        {"ders_id": 1, "ders": "A", "basari": 0.9, "trend": 0.5, "populerlik": 0.8, "anket": 0.5},
        {"ders_id": 2, "ders": "B", "basari": 0.7, "trend": 0.5, "populerlik": 0.8, "anket": 0.5},
        {"ders_id": 3, "ders": "C", "basari": 0.5, "trend": 0.5, "populerlik": 0.8, "anket": 0.5},
    ])
    weights = [0.4, 0.2, 0.2, 0.2]
    _, meta = motor.topsis_calistir(df, weights, criteria_keys=["basari", "trend", "populerlik", "anket"])
    degenerate = meta.get("degenerate_criteria", [])
    # trend, populerlik, anket sabit -> dejenere
    assert set(degenerate) == {"trend", "populerlik", "anket"}, (
        f"Beklenen 3 dejenere kriter; alinan: {degenerate}"
    )


def test_h3_topsis_no_degenerate_when_all_vary():
    """Tum kriterlerde varyans varsa dejenere liste bos olmali."""
    motor = KararMotoru()
    df = pd.DataFrame([
        {"ders_id": 1, "ders": "A", "basari": 0.9, "trend": 0.7, "populerlik": 0.8, "anket": 0.6},
        {"ders_id": 2, "ders": "B", "basari": 0.7, "trend": 0.5, "populerlik": 0.6, "anket": 0.8},
        {"ders_id": 3, "ders": "C", "basari": 0.5, "trend": 0.3, "populerlik": 0.4, "anket": 0.9},
    ])
    _, meta = motor.topsis_calistir(df, [0.4, 0.2, 0.2, 0.2])
    assert meta.get("degenerate_criteria") == []


# -----------------------------
# H4: Gocereli sifirlanma korumasi
# -----------------------------


def test_h4_low_score_protected_when_raw_success_high():
    """KP duusuk ama ham basari 0.70+ ise dusme onerisi olmamali."""
    flag, reasons = should_drop_course(
        score_100=0.0,           # gocereli C=0
        average_grade=79.0,      # not yeterli
        raw_basari_ratio=0.84,   # ham basari %84 -> KORUMALI
    )
    assert flag is False
    assert reasons == []


def test_h4_low_score_NOT_protected_when_raw_success_low():
    """KP duusuk VE ham basari 0.70 alti -> dusme onerisi devam etmeli."""
    flag, reasons = should_drop_course(
        score_100=0.0,
        average_grade=79.0,
        raw_basari_ratio=0.50,
    )
    assert flag is True
    assert any("Kesinlesme" in r for r in reasons)


def test_h4_average_grade_still_drops_regardless_of_raw_basari():
    """Ham basari yuksek olsa bile ortalama not 45 alti -> hala duser (ortalama bagimsiz)."""
    flag, reasons = should_drop_course(
        score_100=85,
        average_grade=30,        # not cok dusuk
        raw_basari_ratio=0.90,
    )
    assert flag is True
    assert any("Gecme not" in r for r in reasons)


def test_h4_backward_compat_when_raw_basari_none():
    """raw_basari_ratio=None verilince ESKI davranis korunmali."""
    flag_eski, reasons_eski = should_drop_course(score_100=0.0, average_grade=79.0)
    flag_yeni_korumasiz, reasons_yeni_korumasiz = should_drop_course(
        score_100=0.0, average_grade=79.0, raw_basari_ratio=None
    )
    assert flag_eski == flag_yeni_korumasiz == True
    assert reasons_eski == reasons_yeni_korumasiz


def test_h4_evaluate_drop_reasons_returns_protected_list():
    """evaluate_drop_reasons korumali durumda BOS liste donmeli."""
    reasons = evaluate_drop_reasons(
        score_100=0.0, average_grade=79.0, raw_basari_ratio=0.85,
    )
    assert reasons == []


def test_h4_threshold_constant_is_documented():
    """MIN_RAW_SUCCESS_FLOOR sabit ve mantikli olmali."""
    assert 0.0 < MIN_RAW_SUCCESS_FLOOR < 1.0
    assert MIN_RAW_SUCCESS_FLOOR == 0.70  # docs ile uyumlu


# -----------------------------
# H5: Mantiksiz anket verisi
# -----------------------------


def _build_db_with_anket(secen: int, katilim: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, yil INTEGER, donem TEXT,
            toplam_ogrenci INTEGER, gecen_ogrenci INTEGER,
            basari_ortalamasi REAL, kontenjan INTEGER, kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER, anket_dersi_secen INTEGER
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER,
            ortalama_not REAL, basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, doluluk_orani REAL
        );
    """)
    cur.execute(
        "INSERT INTO ders_kriterleri "
        "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, "
        " kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen) "
        "VALUES (1, 2022, 'Guz', 50, 45, 80, 60, 50, ?, ?)",
        (katilim, secen),
    )
    cur.execute(
        "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) "
        "VALUES (1, 2022, 80, 0.90)"
    )
    conn.commit()
    conn.close()
    return path


def test_h5_invalid_anket_returns_neutral():
    """anket_secen (50) > anket_katilimci (44) mantiksiz -> anket=0.5 notr."""
    path = _build_db_with_anket(secen=50, katilim=44)
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
    try:
        motor = KararMotoru()
        m = _read_course_metrics(conn.cursor(), 1, 2022, "Guz", motor)
        assert m["anket"] == pytest.approx(0.5, abs=1e-6), (
            f"Mantiksiz anket -> notr 0.5 bekleniyor; alinan: {m['anket']}"
        )
    finally:
        conn.close()
        os.unlink(path)


def test_h5_valid_anket_passes_through():
    """anket_secen (30) <= anket_katilimci (40) gecerli -> 30/40 = 0.75."""
    path = _build_db_with_anket(secen=30, katilim=40)
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
    try:
        motor = KararMotoru()
        m = _read_course_metrics(conn.cursor(), 1, 2022, "Guz", motor)
        assert m["anket"] == pytest.approx(0.75, abs=1e-3)
    finally:
        conn.close()
        os.unlink(path)


def test_h5_edge_case_equal_secen_and_katilim():
    """anket_secen == anket_katilimci -> 1.0 (sınırda, mantiksiz değil)."""
    path = _build_db_with_anket(secen=44, katilim=44)
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
    try:
        motor = KararMotoru()
        m = _read_course_metrics(conn.cursor(), 1, 2022, "Guz", motor)
        assert m["anket"] == pytest.approx(1.0, abs=1e-3)
    finally:
        conn.close()
        os.unlink(path)


# -----------------------------
# H6: Strict AHP varsayilan
# -----------------------------


def test_h6_dual_wrapper_default_is_strict():
    """run_all_algorithms_for_year_dual varsayilan olarak strict_ahp=True olmali."""
    import inspect

    from app.services.calculation import run_all_algorithms_for_year_dual

    sig = inspect.signature(run_all_algorithms_for_year_dual)
    param = sig.parameters.get("strict_ahp")
    assert param is not None, "strict_ahp parametresi tanimli olmali"
    assert param.default is True, (
        f"Dual wrapper varsayilan strict_ahp=True olmali; alinan: {param.default}"
    )


def test_h6_dual_wrapper_passes_strict_to_subcalls():
    """Dual wrapper, strict_ahp degerini alt run_all_algorithms_for_year cagrilarina iletmeli."""
    from unittest.mock import patch

    from app.services.calculation import run_all_algorithms_for_year_dual

    captured_strict = []

    def stub(yil, db_path=None, donem="G", fakulte_id=None, strict_ahp=False):
        captured_strict.append(strict_ahp)
        return {"ok": True, "year": yil, "processed": [{"x": 1}], "skipped": [], "errors": [], "messages": []}

    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=stub):
        run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1)  # default

    assert all(s is True for s in captured_strict), (
        f"Default strict_ahp=True alt cagrilara iletilmeli; alinan: {captured_strict}"
    )

    # Opt-out: strict_ahp=False acikca verince False iletilmeli
    captured_strict.clear()
    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=stub):
        run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1, strict_ahp=False)
    assert all(s is False for s in captured_strict)

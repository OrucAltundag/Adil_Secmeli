# -*- coding: utf-8 -*-
"""Faz C regresyon testleri: Toplu Kesinlesme Puanlari modu.

Spec madde 4/6/7/8/23/26 kosullari:
- Filtreler yil/fakulte/donem/durum dogru calismali.
- Eski/yeni puan karsilastirmasi spec madde 6 etiketleriyle.
- Karar esikleri spec madde 23 (80/60/40/0) ile uyumlu.
- Eski veri karismamali (yeni sorgu her cagrida).
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import types

import pytest

from app.ui.tabs.course_analysis_tab import CourseAnalysisTab


def _build_mini_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY, bolum_id INTEGER, fakulte_id INTEGER,
            ad TEXT, kod TEXT, kontenjan INTEGER, kredi INTEGER, akts INTEGER, DersTipi TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY, fakulte_id INTEGER, akademik_yil INTEGER,
            bolum_id INTEGER, donem TEXT, durum TEXT, versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT, mufredat_id INTEGER, ders_id INTEGER
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id TEXT, yil INTEGER,
            fakulte_id INTEGER, bolum_id INTEGER, donem TEXT, statu INTEGER,
            sayac INTEGER, skor REAL, ders_adi TEXT
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER,
            akademik_yil INTEGER, ortalama_not REAL, basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER,
            akademik_yil INTEGER, doluluk_orani REAL
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, yil INTEGER, donem TEXT,
            toplam_ogrenci INTEGER, gecen_ogrenci INTEGER,
            basari_ortalamasi REAL, kontenjan INTEGER, kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER, anket_dersi_secen INTEGER
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER,
            akademik_yil INTEGER, donem TEXT, skor_top REAL
        );
        """
    )
    # 1 fakulte, 1 bolum, 3 ders (2 mufredatta, 1 havuzda)
    cur.execute("INSERT INTO fakulte VALUES (1, 'Test Fakultesi')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Test Bolumu')")
    for cid, ad, basari in ((101, "Yuksek Basari", 0.95), (102, "Orta Basari", 0.75), (103, "Havuz Dersi", 0.60)):
        cur.execute(
            "INSERT INTO ders VALUES (?, 10, 1, ?, ?, 50, 3, 5, 'Secmeli')",
            (cid, ad, f"D{cid}"),
        )
        cur.execute(
            "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) "
            "VALUES (?, 2022, ?, ?)",
            (cid, 70 + basari * 20, basari),
        )
        cur.execute(
            "INSERT INTO populerlik (ders_id, akademik_yil, doluluk_orani) VALUES (?, 2022, 0.8)",
            (cid,),
        )
        cur.execute(
            "INSERT INTO ders_kriterleri "
            "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, "
            " kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen) "
            "VALUES (?, 2022, 'Guz', 50, ?, 75, 60, 50, 40, 35)",
            (cid, int(basari * 50)),
        )
    # Mufredat: 101 ve 102 mufredatta (Guz), 103 yalniz havuzda
    cur.execute(
        "INSERT INTO mufredat VALUES (1, 1, 2022, 10, 'Guz', 'Resmi', 1)"
    )
    cur.executemany(
        "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
        [(1, 101), (1, 102)],
    )
    # Havuz: 3 ders Guz havuzunda; 101'in saklanan skoru var (eski KP), digerleri yok
    for cid, eski_kp in ((101, 88.0), (102, None), (103, None)):
        cur.execute(
            "INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi) "
            "VALUES (?, 2022, 1, 10, 'Guz', 1, 0, ?, ?)",
            (str(cid), eski_kp, f"Ders-{cid}"),
        )
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def tab():
    """CourseAnalysisTab bare instance (UI'siz, Tk root yok)."""
    path = _build_mini_db()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    fake_db = types.SimpleNamespace(conn=conn)
    instance = CourseAnalysisTab.__new__(CourseAnalysisTab)
    instance.db = fake_db
    yield instance
    conn.close()
    try:
        os.unlink(path)
    except OSError:
        pass


# -----------------------------
# Helper testleri (spec madde 6/23)
# -----------------------------


def test_change_label_arrti():
    label, tag = CourseAnalysisTab._compute_change(50.0, 60.0)
    assert "Artt" in label and "+10.00" in label
    assert tag == "artti"


def test_change_label_azaldi():
    label, tag = CourseAnalysisTab._compute_change(80.0, 60.0)
    assert "Azald" in label
    assert tag == "azaldi"


def test_change_label_ilk_kez():
    label, tag = CourseAnalysisTab._compute_change(None, 75.0)
    assert "lk kez" in label
    assert tag == "ilk_kez"


def test_change_label_degismedi():
    label, tag = CourseAnalysisTab._compute_change(50.0, 50.005)
    # Tag dogru olmali; etiket metni dilden bagimsiz olarak diff icermeli
    assert tag == ""
    assert "50.0" in label


def test_decision_thresholds():
    # Spec madde 23: 80/60/40/0
    assert CourseAnalysisTab._compute_decision(85) == "Müfredata güçlü öneri"
    assert CourseAnalysisTab._compute_decision(80) == "Müfredata güçlü öneri"
    assert CourseAnalysisTab._compute_decision(79.9) == "Müfredatta kalabilir"
    assert CourseAnalysisTab._compute_decision(60) == "Müfredatta kalabilir"
    assert CourseAnalysisTab._compute_decision(50) == "Manuel inceleme"
    assert CourseAnalysisTab._compute_decision(40) == "Manuel inceleme"
    assert CourseAnalysisTab._compute_decision(39.9) == "Düşme önerisi"
    assert CourseAnalysisTab._compute_decision(0) == "Düşme önerisi"


# -----------------------------
# Veri toplama testleri (spec madde 4/7/8)
# -----------------------------


def test_collect_returns_all_courses_for_year(tab):
    rows = tab._collect_bulk_rows(2022, "Hepsi", "Güz", "Hepsi")
    # 2 TOPSIS (101, 102) + 1 havuz (103) = 3 ders
    assert len(rows) >= 3
    ders_ids = {r["ders_id"] for r in rows}
    assert {101, 102, 103} <= ders_ids


def test_collect_separates_topsis_vs_pool(tab):
    rows = tab._collect_bulk_rows(2022, "Hepsi", "Güz", "Hepsi")
    topsis = [r for r in rows if r["yontem"] == "topsis"]
    pool = [r for r in rows if r["yontem"] == "pool_anket_only"]
    assert len(topsis) == 2  # 101, 102 mufredatta
    assert len(pool) == 1    # 103 yalniz havuzda
    # Mufredatta olanlarin durumu dogru olmali
    assert all(r["durum"] == "Müfredatta" for r in topsis)
    assert all(r["durum"] == "Havuzda" for r in pool)


def test_status_filter_works(tab):
    only_mufredat = tab._collect_bulk_rows(2022, "Hepsi", "Güz", "Müfredatta")
    only_havuz = tab._collect_bulk_rows(2022, "Hepsi", "Güz", "Havuzda")
    assert all(r["durum"] == "Müfredatta" for r in only_mufredat)
    assert all(r["durum"] == "Havuzda" for r in only_havuz)


def test_donem_filter_works(tab):
    rows_guz = tab._collect_bulk_rows(2022, "Hepsi", "Güz", "Hepsi")
    rows_bahar = tab._collect_bulk_rows(2022, "Hepsi", "Bahar", "Hepsi")
    # Mini DB'de yalniz Guz mufredati var; ama havuzda her donem icin sorgu acilir.
    # Donem filtresi en azindan Guz/Bahar ayriminda dogru calismali.
    if rows_guz:
        assert all(r["donem"] == "Güz" for r in rows_guz)
    if rows_bahar:
        assert all(r["donem"] == "Bahar" for r in rows_bahar)


def test_eski_kp_vs_yeni_kp_change_label(tab):
    """101 dersinin eski_kp=88; yeni_kp canli hesap. Degisim etiketi dogru olmali."""
    rows = tab._collect_bulk_rows(2022, "Hepsi", "Güz", "Müfredatta")
    by_id = {r["ders_id"]: r for r in rows}
    assert 101 in by_id
    r = by_id[101]
    assert r["eski_kp"] != "—", "Eski KP saklanan deger olmali"
    # 102'nin eski_kp'si NULL idi -> 'ilk kez hesaplandı'
    if 102 in by_id:
        assert by_id[102]["eski_kp"] == "—"
        assert by_id[102]["_tag"] == "ilk_kez"


def test_fakulte_filter_returns_only_selected(tab):
    rows_all = tab._collect_bulk_rows(2022, "Hepsi", "Hepsi", "Hepsi")
    rows_test = tab._collect_bulk_rows(2022, "Test Fakultesi", "Hepsi", "Hepsi")
    assert len(rows_test) > 0
    assert all(r["fakulte"] == "Test Fakultesi" for r in rows_test)
    assert len(rows_test) == len(rows_all)  # tek fakulte var

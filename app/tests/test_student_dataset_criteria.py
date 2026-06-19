# -*- coding: utf-8 -*-
"""Otomatik kriter üretimi — ders_kriterleri + performans + popülerlik yazmalı.

Regresyon: eski sürüm yalnızca ders_kriterleri yazıyordu; bu yüzden Veri
Kalitesi'nde Kriter %100 ama Performans/Popülerlik %0 görünüyordu.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import openpyxl

from app.services.student_dataset_criteria_service import (
    auto_generate_criteria_from_student_dataset,
)


def _excel(path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ders Analizi"
    ws.append(["ders_kodu", "donem", "kayit_sayisi", "gecme_orani_%", "ort_agirlikli", "ort_katilim_yuzde"])
    ws.append(["TIP102S", "Guz", 50, 96.0, 82.25, 80.0])
    ws.append(["TIP101S", "Bahar", 40, 80.0, 70.0, 75.0])
    wb.save(path)
    wb.close()


def _db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE ders(ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT);
        CREATE TABLE ders_kriterleri(id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INT, yil INT, donem TEXT,
            toplam_ogrenci INT, gecen_ogrenci INT, basari_ortalamasi REAL, kontenjan INT, kayitli_ogrenci INT,
            anket_katilimci INT, anket_dersi_secen INT, anket_veri_kaynagi TEXT, criteria_veri_kaynagi TEXT,
            criteria_updated_at TEXT, is_active INT);
        CREATE TABLE performans(id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INT, akademik_yil INT, donem TEXT,
            ortalama_not REAL, basari_orani REAL);
        CREATE TABLE populerlik(id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INT, akademik_yil INT, donem TEXT,
            talep_sayisi INT, kontenjan INT, doluluk_orani REAL);
        """
    )
    conn.execute("INSERT INTO ders VALUES (769,'TIP102S','Tibbi Etik')")
    conn.execute("INSERT INTO ders VALUES (768,'TIP101S','Klinik Anatomi')")
    conn.commit()
    return conn


def test_auto_generate_writes_all_three_tables():
    fd, xp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    _excel(xp)
    conn = _db()
    try:
        r = auto_generate_criteria_from_student_dataset(conn, excel_path=xp, year=2022, replace=True)
        assert r["eklenen"] == 2
        assert r["performans_yazilan"] == 2
        assert r["populerlik_yazilan"] == 2

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ders_kriterleri WHERE yil=2022")
        assert cur.fetchone()[0] == 2
        # performans: basari_orani = gecen/kayit = 48/50 = 0.96
        cur.execute("SELECT ortalama_not, basari_orani FROM performans WHERE ders_id=769")
        ort, basari = cur.fetchone()
        assert ort == 82.25
        assert abs(basari - 0.96) < 1e-6
        # populerlik: doluluk = 50/60
        cur.execute(
            "SELECT talep_sayisi, kontenjan, doluluk_orani, ilgi_orani, ham_puan "
            "FROM populerlik WHERE ders_id=769"
        )
        talep, kont, dol, ilgi, populerlik = cur.fetchone()
        assert talep == 50 and kont == 60
        assert abs(dol - 50 / 60) < 1e-6
        assert abs(ilgi - 0.80) < 1e-6
        assert abs(populerlik - ((50 / 60 * 0.60 + 0.80 * 0.15) / 0.75)) < 1e-6
    finally:
        conn.close()
        os.unlink(xp)


def test_replace_clears_year_before_regenerate():
    fd, xp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    _excel(xp)
    conn = _db()
    try:
        auto_generate_criteria_from_student_dataset(conn, excel_path=xp, year=2022, replace=True)
        auto_generate_criteria_from_student_dataset(conn, excel_path=xp, year=2022, replace=True)
        cur = conn.cursor()
        # Tekrar çalıştırınca kopya satır birikmemeli.
        cur.execute("SELECT COUNT(*) FROM performans WHERE akademik_yil=2022")
        assert cur.fetchone()[0] == 2
        cur.execute("SELECT COUNT(*) FROM populerlik WHERE akademik_yil=2022")
        assert cur.fetchone()[0] == 2
    finally:
        conn.close()
        os.unlink(xp)

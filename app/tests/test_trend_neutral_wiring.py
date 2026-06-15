# -*- coding: utf-8 -*-
"""H1 regresyon testleri: trend notr-skoru asil kesinlesme yoluna bagli olmali.

bkz. docs/MATEMATIKSEL_INCELEME_RAPORU_2026-06-15.md (H1, H2)

Onceki davranis (HATA): _read_course_metrics legacy gecmis_trend_hesapla'yi
cagiriyordu; tek yil verisi olan ders icin trend = basari (collinear) veya 0.0
donuyordu. Bu test, notr-farkinda analyze_course_trend yolunun kullanildigini
ve tek-yil verisinde trend = 0.5 (notr) dondugunu kilitler.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.services.calculation import KararMotoru, _read_course_metrics


def _build_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY, ad TEXT, bolum_id INTEGER, fakulte_id INTEGER
        );
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
        """
    )
    # Tek-yil dersi (101): yalniz 2022 verisi -> trend notr (0.5) bekleniyor
    cur.execute("INSERT INTO ders VALUES (101, 'Tek Yil Ders', 1, 1)")
    cur.execute(
        "INSERT INTO ders_kriterleri "
        "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, "
        " kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen) "
        "VALUES (101, 2022, 'Guz', 50, 48, 82.0, 60, 50, 44, 40)"
    )
    cur.execute(
        "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) "
        "VALUES (101, 2022, 82.0, 0.96)"
    )
    cur.execute(
        "INSERT INTO populerlik (ders_id, akademik_yil, doluluk_orani) VALUES (101, 2022, 0.83)"
    )

    # Cok-yil dersi (102): 2020, 2021, 2022 verisi -> trend bagimsiz hesaplanmali
    cur.execute("INSERT INTO ders VALUES (102, 'Cok Yil Ders', 1, 1)")
    for yil, basari in ((2020, 0.60), (2021, 0.70), (2022, 0.80)):
        cur.execute(
            "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) "
            "VALUES (102, ?, 75.0, ?)",
            (yil, basari),
        )
        cur.execute(
            "INSERT INTO populerlik (ders_id, akademik_yil, doluluk_orani) VALUES (102, ?, 0.80)",
            (yil,),
        )
        cur.execute(
            "INSERT INTO ders_kriterleri "
            "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, "
            " kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen) "
            "VALUES (102, ?, 'Guz', 50, ?, 75.0, 60, 50, 40, 35)",
            (yil, int(basari * 50)),
        )

    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def cur():
    path = _build_db()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn.cursor()
    conn.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_single_year_course_gets_neutral_trend(cur):
    """Tek-yil verisi olan ders icin trend NOTR (0.5) olmali.

    Bu, H1 kilit regresyonu: trend basari'nin kopyasi olamaz.
    """
    motor = KararMotoru()
    metrics = _read_course_metrics(cur, ders_id=101, yil=2022, donem="G", motor=motor)
    assert metrics["basari"] == pytest.approx(0.96, abs=1e-3)
    assert metrics["trend"] == pytest.approx(0.5, abs=1e-3), (
        "Tek yil verisi olan ders icin trend = 0.5 (notr) olmali; "
        f"alinan: {metrics['trend']}. _read_course_metrics legacy "
        "gecmis_trend_hesapla yerine analyze_course_trend kullanmali."
    )
    # trend != basari olmali (collinearity bug'i geri donmemeli)
    assert abs(metrics["trend"] - metrics["basari"]) > 0.4


def test_multi_year_course_gets_real_trend(cur):
    """Cok-yil verisi olan ders icin trend bagimsiz hesaplanmali (0.5 degil)."""
    motor = KararMotoru()
    metrics = _read_course_metrics(cur, ders_id=102, yil=2022, donem="G", motor=motor)
    # Yukselen trend (0.60->0.70->0.80) -> agirlikli ortalama ~0.72
    assert metrics["trend"] > 0.6
    assert metrics["trend"] < 0.85
    # Tek-yil notr varsayilanindan farkli olmali
    assert metrics["trend"] != pytest.approx(0.5, abs=0.05)


def test_trend_value_clamped_to_unit_range(cur):
    """Trend [0,1] araliginda kalmali, tasma olmamali."""
    motor = KararMotoru()
    for did in (101, 102):
        t = _read_course_metrics(cur, did, 2022, "G", motor)["trend"]
        assert 0.0 <= t <= 1.0

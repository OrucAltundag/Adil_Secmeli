# -*- coding: utf-8 -*-
"""Faz 5: Uçtan uca karar destek hattı entegrasyon testi.

Zincir: kriter verisi → karar çalıştırma (decision_runs + açılabilirlik)
→ Önerilen Dersler (list_recommended_courses) → Dönem Planı (semester_plan_runs,
açılabilirlik aday skoru) → CSV dışa aktarım.

Bu test, dört fazda kurulan parçaların gerçekten birbirine bağlı çalıştığını
tek bir geçici DB üzerinde kanıtlar.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

from app.services.acilabilirlik_service import list_recommended_courses
from app.services.decision_run_service import record_decision_run_for_faculty_year
from app.services.semester_planning_engine import (
    _latest_acilabilirlik_scores,
    generate_semester_plan,
)
from app.services.semester_planning_reporting_service import export_semester_plan

YEAR = 2025


def _build_pipeline_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT,
            fakulte_id INTEGER, bolum_id INTEGER, DersTipi TEXT, kontenjan INTEGER
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER, bolum_id INTEGER, akademik_yil INTEGER,
            donem TEXT, durum TEXT, versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mufredat_id INTEGER, ders_id INTEGER
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, yil INTEGER, donem TEXT,
            toplam_ogrenci INTEGER, gecen_ogrenci INTEGER, basari_ortalamasi REAL,
            kontenjan INTEGER, kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER, anket_dersi_secen INTEGER
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, donem TEXT,
            ortalama_not REAL, basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, donem TEXT,
            talep_sayisi INTEGER, kontenjan INTEGER, doluluk_orani REAL
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id TEXT, yil INTEGER, fakulte_id INTEGER, bolum_id INTEGER,
            donem TEXT, statu INTEGER, sayac INTEGER, skor REAL, ders_adi TEXT
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, donem TEXT, skor_top REAL
        );
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    cur.execute(
        "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon) "
        "VALUES (1, 10, ?, 'Guz', 'Resmi', 1)",
        (YEAR,),
    )
    mufredat_id = int(cur.lastrowid)

    # Uc secmeli ders; farkli basari/talep -> farkli skor/acilabilirlik.
    courses = [
        # (id, kod, ad, toplam, gecen, ort, kontenjan, kayitli, anket_kat, anket_secen, doluluk)
        (101, "BLM101", "Algoritmalar", 100, 88, 85.0, 50, 48, 30, 27, 0.96),
        (102, "BLM102", "Veri Tabani", 100, 70, 70.0, 50, 38, 30, 20, 0.76),
        (103, "BLM103", "Eski Konu", 100, 45, 50.0, 50, 18, 30, 8, 0.36),
    ]
    for (cid, kod, ad, toplam, gecen, ort, kont, kayitli, akat, asecen, dol) in courses:
        cur.execute(
            "INSERT INTO ders VALUES (?, ?, ?, 1, 10, 'Secmeli', ?)",
            (cid, kod, ad, kont),
        )
        cur.execute("INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)", (mufredat_id, cid))
        cur.executemany(
            "INSERT INTO performans (ders_id, akademik_yil, donem, ortalama_not, basari_orani) "
            "VALUES (?, ?, 'Guz', ?, ?)",
            [
                (cid, YEAR - 1, ort - 5, (gecen - 5) / toplam),
                (cid, YEAR, ort, gecen / toplam),
            ],
        )
        cur.execute(
            "INSERT INTO populerlik (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani) "
            "VALUES (?, ?, 'Guz', ?, ?, ?)",
            (cid, YEAR, kayitli, kont, dol),
        )
        cur.execute(
            "INSERT INTO ders_kriterleri "
            "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, "
            "kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen) "
            "VALUES (?, ?, 'Guz', ?, ?, ?, ?, ?, ?, ?)",
            (cid, YEAR, toplam, gecen, ort, kont, kayitli, akat, asecen),
        )
        cur.execute(
            "INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi) "
            "VALUES (?, ?, 1, 10, 'Guz', 1, 0, ?, ?)",
            (str(cid), YEAR, ort, ad),
        )
    conn.commit()
    return path, conn


def test_full_pipeline_decision_to_plan_export():
    path, conn = _build_pipeline_db()
    try:
        # 1) KARAR ÇALIŞTIRMA — decision_runs + course_decisions (+ açılabilirlik)
        result = record_decision_run_for_faculty_year(conn, year=YEAR, faculty_id=1, semester="Guz")
        conn.commit()
        assert result["ok"] is True
        run_id = result["decision_run_id"]

        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), COUNT(acilabilirlik_score) FROM course_decisions WHERE decision_run_id = ?",
            (run_id,),
        )
        total, with_acil = cur.fetchone()
        assert total >= 1
        # Her ders kararı açılabilirlik skoruyla yazılmış olmalı (Faz 3).
        assert with_acil == total

        # 2) ÖNERİLEN DERSLER — açılabilirliğe göre sıralı, kategorili (Faz 3)
        recommended = list_recommended_courses(conn, run_id)
        assert recommended
        assert all("oneri_kategori" in r for r in recommended)
        skorlar = [r["acilabilirlik"] for r in recommended]
        assert skorlar == sorted(skorlar, reverse=True)  # azalan sıralı

        # 3) PLANLAMA — açılabilirlik aday skorunu beslemeli (Faz 4)
        acil_map = _latest_acilabilirlik_scores(conn, YEAR, faculty_id=1)
        assert acil_map  # karar çalıştırmasından dolu gelmeli

        plan = generate_semester_plan(conn, year=YEAR, faculty_id=1, persist=True, created_by="e2e")
        conn.commit()
        assert plan["ok"] is True
        plan_id = plan["plan_id"]
        assert plan_id is not None

        # Plana giren derslerin skoru açılabilirlikten gelmeli.
        selected = (plan.get("fall_courses") or []) + (plan.get("spring_courses") or [])
        assert selected
        assert any(c.get("score_source") == "acilabilirlik" for c in selected)

        # 4) DIŞA AKTARIM — CSV üretilebilmeli ve ders kodu içermeli (Faz 5)
        csv_text = export_semester_plan(conn, plan_id, format="csv")
        assert "course_code" in csv_text
        assert "BLM101" in csv_text

        # semester_plan_runs gerçekten yazıldı.
        cur.execute("SELECT COUNT(*) FROM semester_plan_runs WHERE id = ?", (plan_id,))
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()
        os.unlink(path)

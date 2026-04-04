import os
import sqlite3
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.ai_engine import HavuzAIEngine


def _build_ai_test_db(total_rows: int, curriculum_rows: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE bolum (
            bolum_id INTEGER PRIMARY KEY,
            fakulte_id INTEGER,
            ad TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY,
            fakulte_id INTEGER,
            akademik_yil INTEGER,
            bolum_id INTEGER,
            donem TEXT
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY,
            mufredat_id INTEGER,
            ders_id INTEGER
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id TEXT,
            yil INTEGER,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            donem TEXT,
            statu INTEGER,
            sayac INTEGER,
            skor REAL,
            ders_adi TEXT
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            ortalama_not REAL,
            basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            talep_sayisi INTEGER,
            kontenjan INTEGER,
            doluluk_orani REAL
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER,
            gecen_ogrenci INTEGER,
            basari_ortalamasi REAL,
            kontenjan INTEGER,
            kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER,
            anket_dersi_secen INTEGER
        );
        """
    )
    cur.execute("INSERT INTO bolum VALUES (40, 4, 'Gastronomi')")
    cur.execute("INSERT INTO mufredat VALUES (1, 4, 2022, 40, 'Guz')")

    for idx in range(total_rows):
        ders_id = 1001 + idx
        statu = 1 if idx < curriculum_rows else 0
        skor = 40.0 + (idx * 3)
        basari = 0.60 + (idx * 0.01)
        ortalama = 60.0 + idx
        doluluk = min(0.50 + (idx * 0.02), 0.95)

        cur.execute(
            """
            INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
            VALUES (?, 2022, 4, 40, 'Guz', ?, 0, ?, ?)
            """,
            (str(ders_id), statu, skor, f"Ders-{ders_id}"),
        )
        cur.execute(
            """
            INSERT INTO performans (ders_id, akademik_yil, donem, ortalama_not, basari_orani)
            VALUES (?, 2022, 'Guz', ?, ?)
            """,
            (ders_id, ortalama, basari),
        )
        cur.execute(
            """
            INSERT INTO populerlik (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
            VALUES (?, 2022, 'Guz', 50, 60, ?)
            """,
            (ders_id, doluluk),
        )
        cur.execute(
            """
            INSERT INTO ders_kriterleri
                (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                 kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen)
            VALUES (?, 2022, 'Guz', 100, 70, ?, 60, 50, 100, ?)
            """,
            (ders_id, ortalama, 20 + idx),
        )

        if idx < curriculum_rows:
            cur.execute(
                "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (?, 1, ?)",
                (idx + 1, ders_id),
            )

    conn.commit()
    conn.close()
    return path


def test_predict_all_courses_falls_back_to_faculty_training_scope_when_curriculum_too_small():
    db_path = _build_ai_test_db(total_rows=12, curriculum_rows=4)
    session = None
    try:
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        ai = HavuzAIEngine(session)

        df = ai.predict_all_courses(fakulte_id=4, yil=2022, curriculum_only=True)
        meta = ai.get_last_training_meta()

        assert len(df) == 4
        assert {"lr_tahmin", "rf_tahmin", "dt_tahmin"}.issubset(df.columns)
        assert meta["fallback_used"] is True
        assert meta["target_rows"] == 4
        assert meta["fit_rows"] == 12
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_predict_all_courses_returns_fallback_columns_when_training_still_insufficient():
    db_path = _build_ai_test_db(total_rows=4, curriculum_rows=2)
    session = None
    try:
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        ai = HavuzAIEngine(session)

        df = ai.predict_all_courses(fakulte_id=4, yil=2022, curriculum_only=True)

        assert len(df) == 2
        assert {"lr_tahmin", "rf_tahmin", "dt_tahmin", "prediction_mode"}.issubset(df.columns)
        assert set(df["prediction_mode"].tolist()) == {"fallback"}
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass

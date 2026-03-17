# -*- coding: utf-8 -*-
# =============================================================================
# app/etl/import_kriterler_excel.py — Ders Kriterleri Toplu Excel İçe Aktarma
# =============================================================================
# Excel'den ders kriterlerini (toplam öğrenci, geçen, kontenjan, kayıtlı vb.)
# toplu olarak ders_kriterleri, performans ve populerlik tablolarına yazar.
#
# Gerekli kolonlar: DersAdı (veya DersID/Kod), Yıl
# Opsiyonel: Dönem, ToplamÖğrenci, GeçenÖğrenci, Ortalama, Kontenjan, KayıtlıÖğrenci
#            AnketKatılımcı, AnketDersiSeçen
# =============================================================================

import os
import re
import sqlite3
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_CANDIDATES = [
    os.path.join(DATA_DIR, "adil_secmeli.db"),
    os.path.join(PROJECT_ROOT, "adil_secmeli.db"),
]
DEFAULT_DB = next((p for p in DB_CANDIDATES if os.path.exists(p)), None)


def _normalize_col(s: str) -> str:
    return str(s).strip().lower().replace("ı", "i").replace("ğ", "g").replace("ş", "s").replace("ö", "o").replace("ü", "u").replace("ç", "c")


def _find_col(df: pd.DataFrame, *names):
    norm_map = {_normalize_col(c): c for c in df.columns}
    for n in names:
        key = _normalize_col(n)
        if key in norm_map:
            return norm_map[key]
    return None


def _safe_int(val, default=0):
    try:
        if pd.isna(val):
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _find_ders_id(cur, ders_adi: str = None, ders_id: int = None, kod: str = None):
    """Ders adı, ID veya kod ile ders_id bulur."""
    if ders_id is not None and ders_id > 0:
        cur.execute("SELECT ders_id FROM ders WHERE ders_id = ?", (ders_id,))
        r = cur.fetchone()
        return r[0] if r else None
    if kod and str(kod).strip():
        cur.execute("SELECT ders_id FROM ders WHERE trim(kod) = trim(?)", (str(kod).strip(),))
        r = cur.fetchone()
        return r[0] if r else None
    if ders_adi and str(ders_adi).strip():
        d = str(ders_adi).strip()
        cur.execute("SELECT ders_id FROM ders WHERE lower(trim(ad)) = lower(trim(?))", (d,))
        r = cur.fetchone()
        if r:
            return r[0]
        cur.execute("SELECT ders_id FROM ders WHERE lower(ad) LIKE lower(?)", (f"%{d}%",))
        r = cur.fetchone()
        return r[0] if r else None
    return None


def _clean_year(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    m = re.search(r"(19|20)\d{2}", s)
    return int(m.group()) if m else None


def run_import(excel_path: str, db_path: str = None):
    """
    Excel'den ders kriterlerini toplu yükler.
    Returns: (ok: bool, msg: str, counts: dict)
    """
    db = db_path or DEFAULT_DB
    result = {"eklenen": 0, "guncellenen": 0, "atlanan": 0, "hata": 0}

    if not db or not os.path.exists(db):
        return False, "Veritabanı bulunamadı.", result
    if not excel_path or not os.path.exists(excel_path):
        return False, "Excel dosyası bulunamadı.", result

    df = pd.read_excel(excel_path)
    df.columns = [str(c).strip() for c in df.columns]

    col_ders = _find_col(df, "DersAdı", "DersAdi", "Ders Adı", "ders_adi", "DersAd")
    col_id = _find_col(df, "DersID", "ders_id", "Ders Id")
    col_kod = _find_col(df, "Kod", "DersKod", "ders_kod")
    col_yil = _find_col(df, "Yıl", "Yil", "Akademik Yıl", "akademik_yil", "year")
    col_donem = _find_col(df, "Dönem", "Donem", "donem", "term")
    col_toplam = _find_col(df, "ToplamÖğrenci", "ToplamOgrenci", "toplam_ogrenci")
    col_gecen = _find_col(df, "GeçenÖğrenci", "GecenOgrenci", "gecen_ogrenci")
    col_ortalama = _find_col(df, "Ortalama", "ortalama_not", "OrtalamaNot")
    col_kontenjan = _find_col(df, "Kontenjan", "kontenjan")
    col_kayitli = _find_col(df, "KayıtlıÖğrenci", "KayitliOgrenci", "kayitli_ogrenci", "talep_sayisi")
    col_anket_kat = _find_col(df, "AnketKatılımcı", "AnketKatilimci", "anket_katilimci")
    col_anket_sec = _find_col(df, "AnketDersiSeçen", "AnketDersiSecen", "anket_dersi_secen")

    if not col_yil:
        return False, "Gerekli kolon bulunamadı: Yıl", result
    if not (col_ders or col_id or col_kod):
        return False, "Ders tanımlayıcı gerekli: DersAdı, DersID veya Kod", result

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # ders_kriterleri tablosu yoksa oluştur
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            donem TEXT DEFAULT 'Güz',
            toplam_ogrenci INTEGER DEFAULT 0,
            gecen_ogrenci INTEGER DEFAULT 0,
            basari_ortalamasi REAL DEFAULT 0.0,
            kontenjan INTEGER DEFAULT 0,
            kayitli_ogrenci INTEGER DEFAULT 0,
            anket_katilimci INTEGER DEFAULT 0,
            anket_dersi_secen INTEGER DEFAULT 0,
            UNIQUE(ders_id, yil),
            FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
        )
    """)
    for col in ("anket_katilimci", "anket_dersi_secen"):
        try:
            cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col} INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    try:
        for idx, row in df.iterrows():
            ders_id = _find_ders_id(
                cur,
                ders_adi=row.get(col_ders) if col_ders else None,
                ders_id=_safe_int(row.get(col_id), 0) if col_id else 0 or None,
                kod=row.get(col_kod) if col_kod else None,
            )
            if not ders_id:
                result["atlanan"] += 1
                continue

            yil = _clean_year(row.get(col_yil))
            if not yil:
                result["atlanan"] += 1
                continue

            donem = str(row.get(col_donem) if col_donem else "Güz").strip() or "Güz"
            donem_norm = "Güz" if donem.lower() in ("güz", "guz") else "Bahar"

            toplam = _safe_int(row.get(col_toplam), 0)
            gecen = _safe_int(row.get(col_gecen), 0)
            ort = _safe_float(row.get(col_ortalama), 0.0)
            kont = _safe_int(row.get(col_kontenjan), 0)
            kayit = _safe_int(row.get(col_kayitli), 0)
            ank_kat = _safe_int(row.get(col_anket_kat), 0)
            ank_sec = _safe_int(row.get(col_anket_sec), 0)

            basari_orani = (gecen / toplam) if toplam > 0 else 0.0
            doluluk_orani = min(kayit / kont, 1.0) if kont > 0 else 0.0

            try:
                cur.execute("DELETE FROM ders_kriterleri WHERE ders_id=? AND yil=?", (ders_id, yil))
                cur.execute("""
                    INSERT INTO ders_kriterleri
                        (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
                         basari_ortalamasi, kontenjan, kayitli_ogrenci,
                         anket_katilimci, anket_dersi_secen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ders_id, yil, donem, toplam, gecen, ort, kont, kayit, ank_kat, ank_sec))

                cur.execute(
                    "DELETE FROM performans WHERE ders_id=? AND akademik_yil=? AND donem=?",
                    (ders_id, yil, donem_norm),
                )
                cur.execute("""
                    INSERT INTO performans
                        (ders_id, akademik_yil, donem, ortalama_not, basari_orani)
                    VALUES (?, ?, ?, ?, ?)
                """, (ders_id, yil, donem_norm, ort, basari_orani))

                cur.execute(
                    "DELETE FROM populerlik WHERE ders_id=? AND akademik_yil=? AND donem=?",
                    (ders_id, yil, donem_norm),
                )
                cur.execute("""
                    INSERT INTO populerlik
                        (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ders_id, yil, donem_norm, kayit, kont, doluluk_orani))

                result["eklenen"] += 1
            except Exception as e:
                result["hata"] += 1

        conn.commit()
        try:
            from app.utils.logger import log_operation
            log_operation("Kriter Excel import", f"eklenen={result['eklenen']} atlanan={result['atlanan']}", success=True)
        except Exception:
            pass
        msg = f"Kriter aktarımı tamamlandı. Eklenen/Güncellenen: {result['eklenen']}, Atlanan: {result['atlanan']}"
        if result["hata"]:
            msg += f", Hata: {result['hata']}"
        return True, msg, result
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Kullanım: python -m app.etl.import_kriterler_excel <excel_dosyasi.xlsx>")
        sys.exit(1)
    ok, msg, counts = run_import(path)
    print(msg)
    sys.exit(0 if ok else 1)

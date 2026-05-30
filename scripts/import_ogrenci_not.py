"""Import `Ana Veri` Excel sheet into `ogrenci_not` SQLite table.

Usage:
    python scripts/import_ogrenci_not.py --excel data/2022_ogrenci_not_veri_seti.xlsx --db data/adil_secmeli.db
"""
from pathlib import Path
import argparse
import sqlite3
import pandas as pd
import datetime


EXPECTED_COLS = [
    "ogrenci_no", "ad", "soyad", "cinsiyet", "dogum_yili", "sinif",
    "burslu_mu", "bolum_id", "bolum_adi", "fakulte_adi",
    "akademik_yil", "donem", "ders_id", "ders_kodu", "ders_adi", "kredi",
    "vize_notu", "proje_notu", "final_notu", "agirlikli_not",
    "gecme_esigi", "harf_notu", "gano_katkisi_4luk",
    "katilim_sayisi", "toplam_hafta", "katilim_yuzdesi",
    "devamsiz_mi", "gecti_mi", "basari_durumu",
    "begen_puani_1_5", "zorluk_alg_1_5", "kariyer_katkisi_1_5",
    "ilgi_alani_uyumu_1_5", "tekrar_alacak_mi", "yeniden_alir_mi",
    "not_tutarsizlik_flag",
]


CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS ogrenci_not (
    ogrenci_no TEXT,
    ad TEXT,
    soyad TEXT,
    cinsiyet TEXT,
    dogum_yili INTEGER,
    sinif INTEGER,
    burslu_mu TEXT,
    bolum_id INTEGER,
    bolum_adi TEXT,
    fakulte_adi TEXT,
    akademik_yil TEXT,
    donem TEXT,
    ders_id TEXT,
    ders_kodu TEXT,
    ders_adi TEXT,
    kredi INTEGER,
    vize_notu REAL,
    proje_notu REAL,
    final_notu REAL,
    agirlikli_not REAL,
    gecme_esigi REAL,
    harf_notu TEXT,
    gano_katkisi_4luk REAL,
    katilim_sayisi INTEGER,
    toplam_hafta INTEGER,
    katilim_yuzdesi REAL,
    devamsiz_mi TEXT,
    gecti_mi TEXT,
    basari_durumu TEXT,
    begen_puani_1_5 INTEGER,
    zorluk_alg_1_5 INTEGER,
    kariyer_katkisi_1_5 INTEGER,
    ilgi_alani_uyumu_1_5 INTEGER,
    tekrar_alacak_mi TEXT,
    yeniden_alir_mi TEXT,
    not_tutarsizlik_flag TEXT,
    imported_at TEXT,
    UNIQUE(ogrenci_no, ders_kodu, akademik_yil, donem)
);
'''


INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_ogrenci_not_year ON ogrenci_not(akademik_yil);",
    "CREATE INDEX IF NOT EXISTS idx_ogrenci_not_ders ON ogrenci_not(ders_kodu);",
    "CREATE INDEX IF NOT EXISTS idx_ogrenci_not_bolum ON ogrenci_not(bolum_id);",
]


def import_excel_to_db(excel_path: Path, db_path: Path, sheet_name: str = "Ana Veri") -> tuple[int, int]:
    if not excel_path.exists():
        raise FileNotFoundError(excel_path)
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    # Normalize columns
    df.columns = [c if isinstance(c, str) else str(c) for c in df.columns]
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = None

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    for s in INDEX_SQL:
        cur.execute(s)
    conn.commit()

    cols = EXPECTED_COLS + ["imported_at"]
    placeholders = ",".join(["?"] * len(cols))
    insert_sql = f"INSERT OR REPLACE INTO ogrenci_not ({', '.join(cols)}) VALUES ({placeholders})"

    rows = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for _, r in df[EXPECTED_COLS].iterrows():
        vals = []
        for c in EXPECTED_COLS:
            v = r[c]
            if pd.isna(v):
                vals.append(None)
            else:
                if c in ('dogum_yili','sinif','bolum_id','kredi','katilim_sayisi','toplam_hafta',
                         'begen_puani_1_5','zorluk_alg_1_5','kariyer_katkisi_1_5','ilgi_alani_uyumu_1_5'):
                    try:
                        vals.append(int(v))
                    except Exception:
                        try:
                            vals.append(int(float(v)))
                        except Exception:
                            vals.append(None)
                elif c in ('vize_notu','proje_notu','final_notu','agirlikli_not','gecme_esigi','gano_katkisi_4luk','katilim_yuzdesi'):
                    try:
                        vals.append(float(v))
                    except Exception:
                        vals.append(None)
                else:
                    vals.append(str(v))
        vals.append(now)
        rows.append(tuple(vals))

    cur.executemany(insert_sql, rows)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM ogrenci_not WHERE akademik_yil LIKE ?;", (f"{df['akademik_yil'].iloc[0]}%",))
    count_year = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ogrenci_not;")
    count_total = cur.fetchone()[0]
    conn.close()
    return count_year, count_total


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--excel", required=True)
    p.add_argument("--db", required=True)
    args = p.parse_args()
    excel = Path(args.excel)
    db = Path(args.db)
    y, t = import_excel_to_db(excel, db)
    print(f"Imported/updated {y} rows for year from {excel} into {db}; total in table: {t}")


if __name__ == "__main__":
    main()

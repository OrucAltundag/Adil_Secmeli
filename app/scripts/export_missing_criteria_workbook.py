# -*- coding: utf-8 -*-
"""
Mufredatta olup next-year kriterleri eksik dersleri Excel + CSV olarak export eder.

Kullanim:
  python app/scripts/export_missing_criteria_workbook.py
  python app/scripts/export_missing_criteria_workbook.py --yil 2022 --donem G

Cikti: exports/missing_criteria_YYYYMMDD.xlsx ve .csv
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
DEFAULT_DB = os.path.join(ROOT, "data", "adil_secmeli.db")
EXPORT_DIR = os.path.join(ROOT, "exports")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--yil", type=int, default=2022)
    ap.add_argument("--donem", default="G", help="G veya Guz / Bahar ilk harf")
    ap.add_argument("--out-dir", default=EXPORT_DIR)
    args = ap.parse_args()
    donem = str(args.donem or "G").strip()
    if not os.path.exists(args.db):
        print("DB yok:", args.db)
        return 1

    from app.services.calculation import _has_generation_criteria

    os.makedirs(args.out_dir, exist_ok=True)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    rows_out = []
    cur.execute(
        """
        SELECT DISTINCT f.ad, b.ad, d.ders_id, d.ad, m.akademik_yil, COALESCE(m.donem,'')
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN fakulte f ON f.fakulte_id = b.fakulte_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        JOIN ders d ON d.ders_id = md.ders_id
        WHERE m.akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(m.donem,'')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
        ORDER BY f.ad, b.ad, d.ad
        """,
        (int(args.yil), donem),
    )
    for fak, bol, did, dad, yil, mdon in cur.fetchall():
        if _has_generation_criteria(cur, int(did), int(yil), donem):
            continue
        rows_out.append(
            {
                "fakulte": fak or "",
                "bolum": bol or "",
                "ders_id": int(did),
                "ders_adi": dad or "",
                "yil": int(yil),
                "donem": mdon or "Güz",
                "mufredatta_mi": True,
                "toplam_ogrenci": 100,
                "gecen_ogrenci": 75,
                "kontenjan": 50,
                "kayitli_ogrenci": 40,
                "ortalama": 70.0,
                "basari_orani": 0.75,
                "trend": 0.72,
                "populerlik": 0.80,
                "anket_katilimci": 0,
                "anket_dersi_secen": 0,
                "not_aciklama": "ORNEK SEED — Excel’i gercek degerlerle guncelleyin; dry-run ile kontrol edin.",
            }
        )
    conn.close()

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = os.path.join(args.out_dir, f"missing_criteria_{args.yil}_{stamp}")

    import pandas as pd

    df = pd.DataFrame(rows_out)
    if df.empty:
        print("Eksik kriter kaydi yok (tum mufredat dersleri tam).")
        df.to_excel(base + "_bos.xlsx", index=False)
        return 0
    df.to_excel(base + ".xlsx", index=False)
    df.to_csv(base + ".csv", index=False, encoding="utf-8-sig")
    print(f"Yazildi: {base}.xlsx ({len(df)} satir), {base}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

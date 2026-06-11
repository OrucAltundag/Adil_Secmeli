# -*- coding: utf-8 -*-
"""
Excel/CSV'den ders_kriterleri + performans + populerlik yukler.

Varsayilan: dry-run ( --apply yoksa DB yazilmaz ).
  python app/scripts/seed_criteria_from_workbook.py exports/missing_criteria.xlsx
  python app/scripts/seed_criteria_from_workbook.py exports/missing_criteria.xlsx --apply
  python app/scripts/seed_criteria_from_workbook.py exports/missing_criteria.xlsx --apply --force
"""
from __future__ import annotations

import argparse
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB = os.path.join(ROOT, "data", "adil_secmeli.db")


def _norm(s):
    return str(s).strip().lower().replace("ı", "i")


def _col(df, *names):
    m = {_norm(c): c for c in df.columns}
    for n in names:
        k = _norm(n)
        if k in m:
            return m[k]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Excel veya CSV")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--apply", action="store_true", help="DB'ye yaz")
    ap.add_argument("--force", action="store_true", help="Mevcut ders+yil uzerine yaz")
    args = ap.parse_args()
    dry = not args.apply

    if not os.path.exists(args.input):
        print("Dosya yok:", args.input)
        return 1
    if not os.path.exists(args.db):
        print("DB yok:", args.db)
        return 1

    import pandas as pd

    path = args.input
    df = pd.read_csv(path, encoding="utf-8-sig") if path.lower().endswith(".csv") else pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]

    c_id = _col(df, "ders_id", "DersID")
    c_yil = _col(df, "yil", "Yil", "Yıl")
    if not c_id or not c_yil:
        print("Gerekli sutun: ders_id, yil")
        return 1

    c_top = _col(df, "toplam_ogrenci", "ToplamOgrenci")
    c_gec = _col(df, "gecen_ogrenci", "GecenOgrenci")
    c_ort = _col(df, "ortalama", "Ortalama")
    c_kon = _col(df, "kontenjan", "Kontenjan")
    c_kay = _col(df, "kayitli_ogrenci", "KayitliOgrenci")
    c_don = _col(df, "donem", "Dönem")
    c_ank_k = _col(df, "anket_katilimci", "AnketKatilimci")
    c_ank_s = _col(df, "anket_dersi_secen", "AnketDersiSecen")

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    plan = []

    for i, row in df.iterrows():
        try:
            did = int(float(row[c_id]))
            yil = int(float(row[c_yil]))
        except (ValueError, TypeError):
            plan.append({"satir": int(i), "aksiyon": "ATLA", "neden": "ders_id/yil"})  # type: ignore[arg-type]
            continue
        cur.execute("SELECT id FROM ders_kriterleri WHERE ders_id=? AND yil=?", (did, yil))
        if cur.fetchone() and not args.force:
            plan.append({"satir": int(i), "ders_id": did, "yil": yil, "aksiyon": "ATLA", "neden": "mevcut kayit"})  # type: ignore[arg-type]
            continue

        def gi(col, default):
            if not col or pd.isna(row.get(col)):
                return default
            try:
                return int(float(row[col]))
            except (ValueError, TypeError):
                return default

        def gf(col, default):
            if not col or pd.isna(row.get(col)):
                return default
            try:
                return float(row[col])
            except (ValueError, TypeError):
                return default

        toplam = gi(c_top, 100)
        gecen = gi(c_gec, int(toplam * 0.75))
        ort = gf(c_ort, 70.0)
        kont = gi(c_kon, 50)
        kayit = gi(c_kay, 40)
        donem = str(row[c_don]) if c_don and pd.notna(row.get(c_don)) else "Güz"
        donem_norm = "Güz" if "bahar" not in donem.lower() else "Bahar"
        ank_k = gi(c_ank_k, 0)
        ank_s = gi(c_ank_s, 0)
        basari = (gecen / toplam) if toplam > 0 else 0.0
        doluluk = min(kayit / kont, 1.0) if kont > 0 else 0.0
        plan.append(
            {
                "satir": int(i),  # type: ignore[arg-type]
                "ders_id": did,
                "yil": yil,
                "aksiyon": "YAZ",
                "donem_norm": donem_norm,
                "toplam": toplam,
                "gecen": gecen,
                "ortalama": ort,
                "kontenjan": kont,
                "kayitli": kayit,
                "anket_katilimci": ank_k,
                "anket_dersi_secen": ank_s,
                "basari_orani": basari,
                "doluluk_orani": doluluk,
            }
        )

    yaz = [p for p in plan if p.get("aksiyon") == "YAZ"]
    atl = [p for p in plan if p.get("aksiyon") == "ATLA"]
    print("=== Dry-run ozeti ===" if dry else "=== Apply ===")
    print(f"Yazilacak: {len(yaz)}, Atlanacak: {len(atl)}")
    for p in yaz[:25]:
        print(f"  YAZ ders_id={p['ders_id']} yil={p['yil']}")
    for p in atl[:15]:
        print(f"  ATLA {p}")
    if len(yaz) > 25:
        print(f"  ... +{len(yaz)-25} yazim")

    if dry:
        print("\nDB degismedi. Uygulamak: --apply")
        conn.close()
        return 0

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL, yil INTEGER NOT NULL, donem TEXT DEFAULT 'Güz',
            toplam_ogrenci INTEGER, gecen_ogrenci INTEGER, basari_ortalamasi REAL,
            kontenjan INTEGER, kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER DEFAULT 0, anket_dersi_secen INTEGER DEFAULT 0,
            UNIQUE(ders_id, yil)
        )
        """
    )
    for col in ("anket_katilimci", "anket_dersi_secen"):
        try:
            cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

    for p in yaz:
        did, yil = p["ders_id"], p["yil"]
        dn = p["donem_norm"]
        cur.execute("DELETE FROM ders_kriterleri WHERE ders_id=? AND yil=?", (did, yil))
        cur.execute(
            """
            INSERT INTO ders_kriterleri
            (ders_id,yil,donem,toplam_ogrenci,gecen_ogrenci,basari_ortalamasi,kontenjan,kayitli_ogrenci,anket_katilimci,anket_dersi_secen)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                did,
                yil,
                dn,
                p["toplam"],
                p["gecen"],
                p["ortalama"],
                p["kontenjan"],
                p["kayitli"],
                p["anket_katilimci"],
                p["anket_dersi_secen"],
            ),
        )
        cur.execute(
            "DELETE FROM performans WHERE ders_id=? AND akademik_yil=? AND donem=?",
            (did, yil, dn),
        )
        cur.execute(
            "INSERT INTO performans (ders_id,akademik_yil,donem,ortalama_not,basari_orani) VALUES (?,?,?,?,?)",
            (did, yil, dn, p["ortalama"], p["basari_orani"]),
        )
        cur.execute(
            "DELETE FROM populerlik WHERE ders_id=? AND akademik_yil=? AND donem=?",
            (did, yil, dn),
        )
        cur.execute(
            "INSERT INTO populerlik (ders_id,akademik_yil,donem,talep_sayisi,kontenjan,doluluk_orani) VALUES (?,?,?,?,?,?)",
            (did, yil, dn, p["kayitli"], p["kontenjan"], p["doluluk_orani"]),
        )

    conn.commit()
    conn.close()
    print(f"Tamam: {len(yaz)} kayit yazildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

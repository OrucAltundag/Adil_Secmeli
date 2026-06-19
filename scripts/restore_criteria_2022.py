# -*- coding: utf-8 -*-
"""
2022 ders_kriterleri'ni ogrenci veri setinden YENIDEN uret.
Sadece ders_kriterleri'ne dokunur (mufredat/havuz/ders korunur).
Eslesme ders.kod ile yapilir.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import openpyxl

KOK = Path(__file__).parent.parent
DB = KOK / "data" / "adil_secmeli.db"
OGR = KOK / "data" / "2022_ogrenci_not_veri_seti.xlsx"
YIL = 2022


def main():
    wb = openpyxl.load_workbook(OGR, read_only=True)
    ws = wb["Ders Analizi"]
    it = ws.iter_rows(min_row=1, values_only=True)
    h = list(next(it))
    j = {k: i for i, k in enumerate(h)}
    stat = []
    for r in it:
        stat.append({
            "kod": str(r[j["ders_kodu"]]).strip(),
            "donem": str(r[j["donem"]]).strip(),
            "kayit": int(r[j["kayit_sayisi"]] or 0),  # type: ignore[arg-type]  # openpyxl cell.value Optional
            "gecme": float(r[j["gecme_orani_%"]] or 0),  # type: ignore[arg-type]
            "agir": float(r[j["ort_agirlikli"]] or 0),  # type: ignore[arg-type]
            "katilim": float(r[j["ort_katilim_yuzde"]] or 0),  # type: ignore[arg-type]
        })
    wb.close()

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cur.execute("DELETE FROM ders_kriterleri WHERE yil=?", (YIL,))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n = 0
    eksik = 0
    for s in stat:
        cur.execute("SELECT ders_id FROM ders WHERE kod=?", (s["kod"],))
        row = cur.fetchone()
        if not row:
            eksik += 1
            continue
        did = int(row[0])
        gecen = round(s["kayit"] * s["gecme"] / 100.0)
        katilim_yuzde = round(s.get("katilim", 0.0), 1)
        katilim_sayisi = round(s["kayit"] * katilim_yuzde / 100.0)
        # Ders_kriterleri tablo mevcut schema'sı katilim_yuzdesi/katilim_sayisi sütunlarını
        # içermiyor; anket_katilimci alanına katilim_sayisi yazarak katılım bilgisini koruyalım.
        anket_kat = katilim_sayisi
        cur.execute(
            "INSERT INTO ders_kriterleri "
            "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, "
            "basari_ortalamasi, kontenjan, kayitli_ogrenci, anket_katilimci, "
            "anket_dersi_secen, anket_veri_kaynagi, criteria_veri_kaynagi, "
            "criteria_updated_at, is_active) "
            "VALUES (?,?,?,?,?,?,?,?,?,?, 'ogrenci_veri_seti_2022', "
            "'ogrenci_veri_seti_2022', ?, 1)",
            (did, YIL, s["donem"], s["kayit"], gecen, round(s["agir"], 2),
             60, s["kayit"], anket_kat, s["kayit"], now),
        )
        n += 1
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM ders_kriterleri WHERE yil=?", (YIL,))
    print(f"ders_kriterleri 2022 yeniden uretildi: {n} satir "
          f"({eksik} ders DB'de bulunamadi). Toplam: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()

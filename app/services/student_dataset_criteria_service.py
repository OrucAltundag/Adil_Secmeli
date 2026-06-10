# -*- coding: utf-8 -*-
"""
Ogrenci not veri setinden ders_kriterleri'ne OTOMATIK kriter uretici.

Kaynak: data/2022_ogrenci_not_veri_seti.xlsx -> 'Ders Analizi' sekmesi
Hedef: ders_kriterleri (ders.kod ile eslesir; yoksa ders olusturulmaz)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

VARSAYILAN_EXCEL = (
    Path(__file__).parent.parent.parent / "data"
    / "2022_ogrenci_not_veri_seti.xlsx"
)
YIL = 2022


def auto_generate_criteria_from_student_dataset(
    conn: sqlite3.Connection,
    *,
    excel_path: str | Path | None = None,
    year: int = YIL,
    replace: bool = True,
) -> dict[str, Any]:
    """
    Ogrenci veri setinin 'Ders Analizi' sekmesinden ders_kriterleri uretir.

    Args:
        conn: sqlite baglantisi
        excel_path: Excel yolu (yoksa varsayilan)
        year: hedef yil (varsayilan 2022)
        replace: True ise once o yilin satirlarini siler

    Returns:
        {'eklenen': int, 'eslesmeyen': list[str], 'toplam': int,
         'excel_path': str, 'replace': bool}
    """
    yol = Path(excel_path) if excel_path else VARSAYILAN_EXCEL
    if not yol.exists():
        raise FileNotFoundError(f"Ogrenci veri seti bulunamadi: {yol}")

    wb = openpyxl.load_workbook(str(yol), read_only=True)
    if "Ders Analizi" not in wb.sheetnames:
        wb.close()
        raise ValueError(
            "Excel dosyasinda 'Ders Analizi' sekmesi yok."
        )
    ws = wb["Ders Analizi"]
    it = ws.iter_rows(min_row=1, values_only=True)
    hdr = list(next(it))
    j = {k: i for i, k in enumerate(hdr)}
    gerekli = {"ders_kodu", "donem", "kayit_sayisi", "gecme_orani_%",
               "ort_agirlikli", "ort_katilim_yuzde"}
    # openpyxl cell value tipi cok genis (Decimal, datetime, formula vb.);
    # set diff'i str-onlu yapacak şekilde normalize edelim.
    hdr_str = {str(h) for h in hdr}
    if not gerekli.issubset(hdr_str):
        wb.close()
        raise ValueError(
            "Excel 'Ders Analizi' sekmesinde gerekli sutunlar eksik: "
            f"{gerekli - hdr_str}"
        )

    kayitlar = []
    for r in it:
        kayitlar.append({
            "kod": str(r[j["ders_kodu"]]).strip(),
            "donem": str(r[j["donem"]]).strip(),
            "kayit": int(r[j["kayit_sayisi"]] or 0),  # type: ignore[arg-type]
            "gecme": float(r[j["gecme_orani_%"]] or 0),  # type: ignore[arg-type]
            "agir": float(r[j["ort_agirlikli"]] or 0),  # type: ignore[arg-type]
            "katilim": float(r[j["ort_katilim_yuzde"]] or 0),  # type: ignore[arg-type]
        })
    wb.close()

    cur = conn.cursor()
    if replace:
        cur.execute("DELETE FROM ders_kriterleri WHERE yil = ?", (int(year),))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    eklenen, eslesmeyen = 0, []
    for s in kayitlar:
        cur.execute("SELECT ders_id FROM ders WHERE kod = ?", (s["kod"],))
        row = cur.fetchone()
        if not row:
            eslesmeyen.append(s["kod"])
            continue
        did = int(row[0])
        gecen = round(s["kayit"] * s["gecme"] / 100.0)
        anket_kat = round(s["kayit"] * s["katilim"] / 100.0)
        cur.execute(
            "INSERT INTO ders_kriterleri "
            "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, "
            "basari_ortalamasi, kontenjan, kayitli_ogrenci, anket_katilimci, "
            "anket_dersi_secen, anket_veri_kaynagi, criteria_veri_kaynagi, "
            "criteria_updated_at, is_active) "
            "VALUES (?,?,?,?,?,?,?,?,?,?, 'ogrenci_veri_seti', "
            "'ogrenci_veri_seti', ?, 1)",
            (did, int(year), s["donem"], s["kayit"], gecen,
             round(s["agir"], 2), 60, s["kayit"], anket_kat, s["kayit"], now),
        )
        eklenen += 1
    conn.commit()
    return {
        "eklenen": eklenen,
        "eslesmeyen": eslesmeyen,
        "toplam": len(kayitlar),
        "excel_path": str(yol),
        "replace": replace,
    }

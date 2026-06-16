# -*- coding: utf-8 -*-
"""
Ogrenci not veri setinden OTOMATIK kriter uretici.

Kaynak: data/<yil>_ogrenci_not_veri_seti.xlsx -> 'Ders Analizi' sekmesi
Hedef (manuel kayit ile AYNI uc tablo):
  - ders_kriterleri
  - performans   (ortalama_not, basari_orani)
  - populerlik   (talep_sayisi, kontenjan, doluluk_orani)

Dersler `ders.kod` ile eslesir; eslesmeyen ders icin yeni ders olusturulmaz.
Manuel "Verileri Kaydet" islemi zaten bu uc tabloyu birden yazar; bu fonksiyon
da tutarlilik icin ayni uc tabloyu doldurur (aksi halde Veri Kalitesi'nde
performans/populerlik %0 gorunur).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl

DATA_DIR = Path(__file__).parent.parent.parent / "data"
YIL = 2022
VARSAYILAN_EXCEL = DATA_DIR / f"{YIL}_ogrenci_not_veri_seti.xlsx"


def _dataset_for_year(year: int) -> Path:
    """Yila uygun not veri seti dosyasini doner (data/<yil>_...xlsx)."""
    return DATA_DIR / f"{int(year)}_ogrenci_not_veri_seti.xlsx"


def auto_generate_criteria_from_student_dataset(
    conn: sqlite3.Connection,
    *,
    excel_path: str | Path | None = None,
    year: int = YIL,
    replace: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Ogrenci veri setinin 'Ders Analizi' sekmesinden ders_kriterleri uretir.

    Args:
        conn: sqlite baglantisi
        excel_path: Excel yolu (yoksa varsayilan)
        year: hedef yil (varsayilan 2022)
        replace: True ise once o yilin satirlarini siler
        dry_run: True ise HICBIR yazma yapmaz (DELETE/INSERT/commit yok); yalniz
            eslesme/onizleme hesaplar. UI onay diyalogunda kullanilir.

    Returns:
        {'eklenen': int, 'eslesmeyen': list[str], 'toplam': int,
         'excel_path': str, 'replace': bool, 'preview_rows': list[dict]}
    """
    yol = Path(excel_path) if excel_path else _dataset_for_year(year)
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
    if replace and not dry_run:
        # Manuel kayit ile tutarli: yilin uc tablosunu da temizle.
        cur.execute("DELETE FROM ders_kriterleri WHERE yil = ?", (int(year),))
        cur.execute("DELETE FROM performans WHERE akademik_yil = ?", (int(year),))
        cur.execute("DELETE FROM populerlik WHERE akademik_yil = ?", (int(year),))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    KONTENJAN = 60  # veri setinde kontenjan yok; manuel kayitla ayni varsayilan
    eklenen, perf_yazilan, pop_yazilan, eslesmeyen = 0, 0, 0, []
    yazilan_ders_ids: list[int] = []
    preview_rows: list[dict[str, Any]] = []
    for s in kayitlar:
        if not s["kod"]:
            continue
        cur.execute("SELECT ders_id FROM ders WHERE kod = ?", (s["kod"],))
        row = cur.fetchone()
        if not row:
            eslesmeyen.append(s["kod"])
            continue
        did = int(row[0])
        yazilan_ders_ids.append(did)
        donem = s["donem"]
        gecen = round(s["kayit"] * s["gecme"] / 100.0)
        anket_kat = round(s["kayit"] * s["katilim"] / 100.0)
        # Turetilen olcumler (manuel kayit save_data ile ayni mantik):
        basari_orani = (gecen / s["kayit"]) if s["kayit"] > 0 else 0.0
        doluluk_orani = min(s["kayit"] / KONTENJAN, 1.0) if KONTENJAN > 0 else 0.0

        # Onizleme satiri (UI onay diyalogu icin) — yazma olsun olmasin doldurulur.
        preview_rows.append({
            "kod": s["kod"],
            "donem": donem,
            "kayit": s["kayit"],
            "basari_orani": round(basari_orani, 3),
            "ortalama_not": round(s["agir"], 2),
            "doluluk_orani": round(doluluk_orani, 3),
        })
        eklenen += 1

        if dry_run:
            # Yazma yok: yalniz eslesme ve onizleme sayilari hesaplanir.
            perf_yazilan += 1
            pop_yazilan += 1
            continue

        cur.execute(
            "INSERT INTO ders_kriterleri "
            "(ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, "
            "basari_ortalamasi, kontenjan, kayitli_ogrenci, anket_katilimci, "
            "anket_dersi_secen, anket_veri_kaynagi, criteria_veri_kaynagi, "
            "criteria_updated_at, is_active) "
            "VALUES (?,?,?,?,?,?,?,?,?,?, 'ogrenci_veri_seti', "
            "'ogrenci_veri_seti', ?, 1)",
            (did, int(year), donem, s["kayit"], gecen,
             round(s["agir"], 2), KONTENJAN, s["kayit"], anket_kat, s["kayit"], now),
        )

        # performans — TOPSIS 'basari' kriterinin okudugu tablo
        cur.execute(
            "DELETE FROM performans WHERE ders_id=? AND akademik_yil=? AND donem=?",
            (did, int(year), donem),
        )
        cur.execute(
            "INSERT INTO performans (ders_id, akademik_yil, donem, ortalama_not, basari_orani) "
            "VALUES (?,?,?,?,?)",
            (did, int(year), donem, round(s["agir"], 2), basari_orani),
        )
        perf_yazilan += 1

        # populerlik — TOPSIS 'populerlik' kriteri + acilabilirlik talep skoru
        cur.execute(
            "DELETE FROM populerlik WHERE ders_id=? AND akademik_yil=? AND donem=?",
            (did, int(year), donem),
        )
        cur.execute(
            "INSERT INTO populerlik (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani) "
            "VALUES (?,?,?,?,?,?)",
            (did, int(year), donem, s["kayit"], KONTENJAN, doluluk_orani),
        )
        pop_yazilan += 1

    # Kriter yazilan dersler artik DOLU; bu derslere ait BAYAT "zorunlu alan
    # bos" kritik dogrulama uyarilarini temizle (olgunluk skorunu haksizca
    # dusurmesin). Tablo yoksa sessizce gec. (dry_run'da yazma yok.)
    if yazilan_ders_ids and not dry_run:
        try:
            ph = ",".join("?" for _ in yazilan_ders_ids)
            cur.execute(
                f"DELETE FROM criteria_validation_issues "
                f"WHERE year = ? AND course_id IN ({ph})",
                (int(year), *[int(i) for i in yazilan_ders_ids]),
            )
        except sqlite3.OperationalError:
            pass
    if not dry_run:
        conn.commit()
    return {
        "eklenen": eklenen,
        "performans_yazilan": perf_yazilan,
        "populerlik_yazilan": pop_yazilan,
        "eslesmeyen": eslesmeyen,
        "toplam": len(kayitlar),
        "excel_path": str(yol),
        "replace": replace,
        "dry_run": dry_run,
        "preview_rows": preview_rows,
    }

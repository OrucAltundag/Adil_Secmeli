# -*- coding: utf-8 -*-
"""
Havuzdan Oner Servisi
=====================

Havuzdaki (ve mufredattaki) secmeli dersleri, ders_kriterleri verisi +
AKTIF AHP profilinin agirliklari ile puanlayip "acilmasi onerilen"
dersleri siralar.

Kriter turetme (ders_kriterleri -> 4 AHP kriteri):
  - basari      = basari_ortalamasi (0-100)
  - populerlik  = kayitli_ogrenci / kontenjan  (doluluk, 0-1 -> %)
  - trend       = gecen_ogrenci / toplam_ogrenci (gecme orani proxy)
  - anket       = anket_katilimci / kayitli_ogrenci (katilim/memnuniyet proxy)

Her kriter aday kume icinde min-max normalize edilir, AKTIF AHP
agirliklariyla agirlikli toplam alinir (0-100 skor). Esik ustu -> ONER.
"""
from __future__ import annotations

import sqlite3
from typing import Any

VARSAYILAN_AGIRLIK = {
    "basari": 0.40, "trend": 0.25, "populerlik": 0.20, "anket": 0.15,
}


def _aktif_agirliklar(conn: sqlite3.Connection) -> dict[str, float]:
    try:
        from app.services.ahp_profile_service import list_ahp_profiles

        for p in list_ahp_profiles(conn):
            if p.get("is_active") and p.get("weights"):
                w = {str(k): float(v) for k, v in p["weights"].items()}
                s = sum(w.values()) or 1.0
                return {k: v / s for k, v in w.items()}
    except Exception:
        pass
    return dict(VARSAYILAN_AGIRLIK)


def _ham_kriterler(row: dict) -> dict[str, float]:
    basari = float(row.get("basari_ortalamasi") or 0.0)
    toplam = float(row.get("toplam_ogrenci") or 0.0)
    gecen = float(row.get("gecen_ogrenci") or 0.0)
    kont = float(row.get("kontenjan") or 0.0)
    kayit = float(row.get("kayitli_ogrenci") or 0.0)
    anket = float(row.get("anket_katilimci") or 0.0)
    return {
        "basari": basari,
        "trend": (gecen / toplam * 100.0) if toplam > 0 else 0.0,
        "populerlik": (kayit / kont * 100.0) if kont > 0 else 0.0,
        "anket": (anket / kayit * 100.0) if kayit > 0 else 0.0,
    }


def _minmax(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    return (lo, hi) if hi > lo else (lo, lo + 1.0)


def recommend_from_pool(
    conn: sqlite3.Connection,
    *,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    top_n: int = 10,
    oner_esigi: float = 60.0,
) -> dict[str, Any]:
    """
    Havuzdaki secmeli dersleri puanlayip onerir.

    Returns:
        {
          "agirliklar": {...}, "esik": float, "toplam_aday": int,
          "veri_yok": int,
          "oneriler": [ {ders_id, kod, ad, statu, skor, kriterler,
                         oneri, gerekce, sira}, ... ]   # skor desc
        }
    """
    cur = conn.cursor()
    kosul = ["h.yil = ?"]
    params: list[Any] = [int(year)]
    if faculty_id:
        kosul.append("h.fakulte_id = ?")
        params.append(int(faculty_id))
    if department_id:
        kosul.append("d.bolum_id = ?")
        params.append(int(department_id))
    if semester:
        kosul.append(
            "LOWER(SUBSTR(TRIM(COALESCE(h.donem,'')),1,1)) = "
            "LOWER(SUBSTR(TRIM(?),1,1))"
        )
        params.append(str(semester))

    sql = f"""
        SELECT d.ders_id, COALESCE(d.kod,'') AS kod, COALESCE(d.ad,'') AS ad,
               h.statu AS statu,
               dk.basari_ortalamasi, dk.toplam_ogrenci, dk.gecen_ogrenci,
               dk.kontenjan, dk.kayitli_ogrenci, dk.anket_katilimci
        FROM havuz h
        JOIN ders d ON d.ders_id = CAST(h.ders_id AS INTEGER)
        LEFT JOIN ders_kriterleri dk
               ON dk.ders_id = d.ders_id AND dk.yil = ?
        WHERE {' AND '.join(kosul)}
        GROUP BY d.ders_id
    """
    cur.execute(sql, [int(year)] + params)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    agirlik = _aktif_agirliklar(conn)
    kriter_anahtarlari = ["basari", "trend", "populerlik", "anket"]

    veri_olan, veri_yok = [], 0
    for r in rows:
        if r.get("basari_ortalamasi") is None and r.get("kayitli_ogrenci") is None:
            veri_yok += 1
            continue
        r["_ham"] = _ham_kriterler(r)
        veri_olan.append(r)

    # Min-max normalizasyon araliklari
    aralik = {
        k: _minmax([r["_ham"][k] for r in veri_olan])
        for k in kriter_anahtarlari
    }

    for r in veri_olan:
        norm = {}
        skor = 0.0
        for k in kriter_anahtarlari:
            lo, hi = aralik[k]
            n = (r["_ham"][k] - lo) / (hi - lo) if hi > lo else 0.0
            norm[k] = round(n, 4)
            skor += float(agirlik.get(k, 0.0)) * n
        r["skor"] = round(skor * 100.0, 2)
        r["kriterler"] = {
            k: round(r["_ham"][k], 2) for k in kriter_anahtarlari
        }
        r["kriter_norm"] = norm

    veri_olan.sort(key=lambda x: x["skor"], reverse=True)

    oneriler = []
    for i, r in enumerate(veri_olan, 1):
        oner = r["skor"] >= oner_esigi
        en_guclu = max(r["kriter_norm"].items(), key=lambda kv: kv[1])[0]
        gerekce = (
            f"Skor {r['skor']:.1f} (esik {oner_esigi:.0f}). "
            f"En guclu kriter: {en_guclu}. "
            + ("ACILMASI ONERILIR." if oner else
               "Havuzda beklemesi onerilir (skor dusuk).")
        )
        oneriler.append({
            "sira": i,
            "ders_id": int(r["ders_id"]),
            "kod": r["kod"],
            "ad": r["ad"],
            "statu": int(r["statu"]) if r["statu"] is not None else 0,
            "skor": r["skor"],
            "kriterler": r["kriterler"],
            "oneri": "AC" if oner else "HAVUZDA_TUT",
            "gerekce": gerekce,
        })

    return {
        "agirliklar": agirlik,
        "esik": float(oner_esigi),
        "toplam_aday": len(rows),
        "veri_yok": veri_yok,
        "oneriler": oneriler[: int(top_n)] if top_n else oneriler,
        "tum_siralama": oneriler,
    }

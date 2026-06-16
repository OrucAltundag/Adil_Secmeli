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

# Cosine benzerlik boost katsayisi (0-1 arasi skor uzerine eklenir, max 5 puan)
_COSINE_BOOST = 5.0


def _cosine_benzerlik_boost(
    conn: sqlite3.Connection,
    aday_ids: list[int],
    aktif_statu: int = 1,
) -> dict[int, float]:
    """
    Her aday ders icin, aktif (statu=aktif_statu) derslerin isimleriyle
    TF-IDF + cosine benzerligine gore [0, _COSINE_BOOST] araliginda boost hesaplar.

    Fikir: Onceden mufredatta basarili olmus (acik) derslere isim benzerligine gore
    aday derslere kucuk bir ek puan verilir; benzer icerikli ders acilmasi tarihsel
    olarak desteklenmistir.

    Returns: {ders_id: boost_puan}  (boost 0 ise sozlukte yok)
    """
    if not aday_ids:
        return {}
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        cur = conn.cursor()
        # Aktif (mufredatta) derslerin adlari
        placeholders = ",".join("?" * len(aday_ids))
        cur.execute(
            f"""
            SELECT d.ders_id, COALESCE(d.ad,'') || ' ' || COALESCE(d.kod,'') AS metin
            FROM havuz h
            JOIN ders d ON d.ders_id = CAST(h.ders_id AS INTEGER)
            WHERE h.statu = ? AND d.ders_id NOT IN ({placeholders})
            """,
            [aktif_statu] + aday_ids,
        )
        aktif_rows = cur.fetchall()
        if not aktif_rows:
            return {}

        # Aday ders metinleri
        cur.execute(
            f"""
            SELECT ders_id, COALESCE(ad,'') || ' ' || COALESCE(kod,'') AS metin
            FROM ders WHERE ders_id IN ({placeholders})
            """,
            aday_ids,
        )
        aday_rows = cur.fetchall()
        if not aday_rows:
            return {}

        aktif_metni = [str(r[1]) for r in aktif_rows]
        aday_id_lst = [int(r[0]) for r in aday_rows]
        aday_metni  = [str(r[1]) for r in aday_rows]

        tum_metinler = aktif_metni + aday_metni
        vektorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 4), min_df=1,
        )
        tfidf = vektorizer.fit_transform(tum_metinler)

        n_aktif = len(aktif_metni)
        aktif_vek = tfidf[:n_aktif]  # type: ignore[index]  # scipy sparse matrix slicing destekler
        aday_vek  = tfidf[n_aktif:]   # type: ignore[index]

        # Her aday icin en yuksek aktif benzerligini al
        sim_matrix = cosine_similarity(aday_vek, aktif_vek)
        max_sim = np.max(sim_matrix, axis=1)  # shape: (n_aday,)

        result: dict[int, float] = {}
        for idx, did in enumerate(aday_id_lst):
            sim = float(max_sim[idx])
            if sim > 0.05:  # cok dusuk benzerlik ihmal et
                result[did] = round(sim * _COSINE_BOOST, 3)
        return result
    except Exception:
        return {}


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


def _havuz_giris_sayilari(
    conn: sqlite3.Connection,
    ders_ids: list[int],
) -> dict[int, int]:
    """
    Her ders icin havuz tablosunda kac kayit oldugunu sayar
    (tum yillar, tum statu'lar).  Bu degere 'havuz_count' denir;
    dersin kac farkli yil/donem diliminde havuzda izlendigini gosterir.
    """
    if not ders_ids:
        return {}
    placeholders = ",".join("?" * len(ders_ids))
    cur = conn.cursor()
    cur.execute(
        f"SELECT CAST(ders_id AS INTEGER), COUNT(*) FROM havuz "
        f"WHERE CAST(ders_id AS INTEGER) IN ({placeholders}) "
        f"GROUP BY CAST(ders_id AS INTEGER)",
        ders_ids,
    )
    return {int(r[0]): int(r[1]) for r in cur.fetchall()}


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

    # ── Havuz geçmiş count (bu ders kac yil/donem havuzda gorundu) ──
    tum_aday_ids = [int(r["ders_id"]) for r in veri_olan]
    havuz_counts = _havuz_giris_sayilari(conn, tum_aday_ids)

    # ── Cosine benzerlik boost (aktif derslerle isim/kod benzerligi) ──
    aday_ids = tum_aday_ids
    cosine_boost = _cosine_benzerlik_boost(conn, aday_ids)

    for r in veri_olan:
        norm = {}
        skor = 0.0
        for k in kriter_anahtarlari:
            lo, hi = aralik[k]
            n = (r["_ham"][k] - lo) / (hi - lo) if hi > lo else 0.0
            norm[k] = round(n, 4)
            skor += float(agirlik.get(k, 0.0)) * n
        base_skor = round(skor * 100.0, 2)
        boost     = cosine_boost.get(int(r["ders_id"]), 0.0)
        r["skor"]         = round(base_skor + boost, 2)
        r["skor_base"]    = base_skor
        r["cosine_boost"] = boost
        r["kriterler"] = {
            k: round(r["_ham"][k], 2) for k in kriter_anahtarlari
        }
        r["kriter_norm"] = norm

    veri_olan.sort(key=lambda x: x["skor"], reverse=True)

    oneriler = []
    for i, r in enumerate(veri_olan, 1):
        oner = r["skor"] >= oner_esigi
        en_guclu = max(r["kriter_norm"].items(), key=lambda kv: kv[1])[0]
        boost_acik = (
            f" Cosine benzerlik boost: +{r['cosine_boost']:.2f}."
            if r["cosine_boost"] > 0 else ""
        )
        gerekce = (
            f"Skor {r['skor']:.1f} (baz={r['skor_base']:.1f}{boost_acik}) "
            f"(esik {oner_esigi:.0f}). "
            f"En guclu kriter: {en_guclu}. "
            + ("ACILMASI ONERILIR." if oner else
               "Havuzda beklemesi onerilir (skor dusuk).")
        )
        hcount = havuz_counts.get(int(r["ders_id"]), 0)
        oneriler.append({
            "sira": i,
            "ders_id": int(r["ders_id"]),
            "kod": r["kod"],
            "ad": r["ad"],
            "statu": int(r["statu"]) if r["statu"] is not None else 0,
            "havuz_count": hcount,          # kac yil/donem havuzda goruldu
            "skor": r["skor"],
            "skor_base": r["skor_base"],
            "cosine_boost": r["cosine_boost"],
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

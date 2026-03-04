# =============================================================================
# app/api/routes.py — REST API Endpoint Tanımları
# =============================================================================
# Üniversite OBS / kayıt sistemi entegrasyonu için endpoint'ler.
# Ders listesi, skor, havuz, müfredat verilerine GET erişimi sağlar.
# =============================================================================

import json
import os
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _get_db_path() -> str:
    """config.json'dan veya varsayılandan veritabanı yolunu al."""
    default = "./adil_secimli.db"
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("db_path", default)
        except Exception:
            pass
    return default


def _run_query(query: str, params: tuple = ()):
    """Parametreli sorgu çalıştırır, (cols, rows) döner."""
    path = _get_db_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail="Veritabanı bulunamadı")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return cols, [list(r) for r in rows]


# ---------- Dersler ----------
@router.get("/dersler")
def ders_listesi(fakulte_id: Optional[int] = None, secmeli_only: bool = False):
    """Tüm dersleri veya fakülteye göre filtreler."""
    if secmeli_only:
        q = """
            SELECT d.ders_id, d.kod, d.ad, d.kredi, d.akts, d.fakulte_id
            FROM ders d
            WHERE (LOWER(COALESCE(d.DersTipi, d.tip, d.tur, '')) LIKE '%seçmeli%'
               OR LOWER(COALESCE(d.DersTipi, d.tip, d.tur, '')) LIKE '%secmeli%')
        """
        params = []
        if fakulte_id is not None:
            q += " AND d.fakulte_id = ?"
            params.append(fakulte_id)
        q += " ORDER BY d.ad"
    else:
        q = "SELECT ders_id, kod, ad, kredi, akts, fakulte_id FROM ders"
        params = []
        if fakulte_id is not None:
            q += " WHERE fakulte_id = ?"
            params.append(fakulte_id)
        q += " ORDER BY ad"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


# ---------- Skorlar ----------
@router.get("/skorlar")
def skor_listesi(akademik_yil: Optional[int] = None, donem: Optional[str] = None):
    """Ders skorlarını getirir (AHP/TOPSIS çıktıları)."""
    q = """
        SELECT s.ders_id, d.ad, s.akademik_yil, s.donem,
               s.b_norm, s.p_norm, s.a_norm, s.g_norm, s.skor_top
        FROM skor s
        JOIN ders d ON s.ders_id = d.ders_id
        WHERE 1=1
    """
    params = []
    if akademik_yil:
        q += " AND s.akademik_yil = ?"
        params.append(akademik_yil)
    if donem:
        q += " AND s.donem = ?"
        params.append(donem)
    q += " ORDER BY s.skor_top DESC"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


# ---------- Havuz ----------
@router.get("/havuz")
def havuz_listesi(yil: int, fakulte_id: Optional[int] = None):
    """Seçmeli ders havuzunu getirir."""
    q = """
        SELECT h.ders_id, d.ad, h.yil, h.fakulte_id, h.statu, h.sayac, h.skor
        FROM havuz h
        JOIN ders d ON h.ders_id = d.ders_id
        WHERE h.yil = ?
    """
    params = [yil]
    if fakulte_id is not None:
        q += " AND h.fakulte_id = ?"
        params.append(fakulte_id)
    q += " ORDER BY h.skor DESC"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


# ---------- Müfredat ----------
@router.get("/mufredat")
def mufredat_listesi(akademik_yil: int, bolum_id: Optional[int] = None):
    """Müfredattaki dersleri getirir."""
    q = """
        SELECT md.mders_id, m.akademik_yil, m.bolum_id, md.ders_id, d.ad
        FROM mufredat m
        JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
        JOIN ders d ON md.ders_id = d.ders_id
        WHERE m.akademik_yil = ?
    """
    params = [akademik_yil]
    if bolum_id is not None:
        q += " AND m.bolum_id = ?"
        params.append(bolum_id)
    q += " ORDER BY d.ad"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


# ---------- Fakülteler ----------
@router.get("/fakulteler")
def fakulte_listesi():
    """Fakülte listesi."""
    cols, rows = _run_query("SELECT fakulte_id, ad, kampus FROM fakulte ORDER BY ad")
    return {"columns": cols, "data": rows}

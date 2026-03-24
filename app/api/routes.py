# =============================================================================
# app/api/routes.py - REST API Endpoint Tanimlari
# =============================================================================

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.settings import load_settings
from app.db.schema_compat import ensure_reporting_schema
from app.services.curriculum_import_service import import_curriculum_excel

router = APIRouter()


def _normalize_donem(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("b"):
        return "Bahar"
    return "Guz"


def _donem_key(value: str | None) -> str:
    return "b" if _normalize_donem(value) == "Bahar" else "g"


def _get_db_path() -> str:
    settings = load_settings(config_path="config.json")
    return settings.db_path


def _open_connection() -> sqlite3.Connection:
    path = _get_db_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail="Veritabani bulunamadi")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_reporting_schema(conn)
    return conn


def _run_query(query: str, params: tuple = ()) -> tuple[list[str], list[list]]:
    conn = _open_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [list(r) for r in rows]
    finally:
        conn.close()


def _havuz_has_donem(conn: sqlite3.Connection) -> bool:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(havuz)")
    return "donem" in {str(row[1]) for row in cur.fetchall()}


@router.get("/dersler")
def ders_listesi(fakulte_id: Optional[int] = None, secmeli_only: bool = False):
    if secmeli_only:
        q = """
            SELECT d.ders_id, d.kod, d.ad, d.kredi, d.akts, d.fakulte_id
            FROM ders d
            WHERE (
                LOWER(COALESCE(d.DersTipi, d.tip, d.tur, '')) LIKE '%secmeli%'
                OR LOWER(COALESCE(d.DersTipi, d.tip, d.tur, '')) LIKE '%seçmeli%'
            )
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


@router.get("/skorlar")
def skor_listesi(akademik_yil: Optional[int] = None, donem: Optional[str] = None):
    q = """
        SELECT s.ders_id, d.ad, s.akademik_yil, s.donem,
               s.b_norm, s.p_norm, s.a_norm, s.g_norm, s.skor_top
        FROM skor s
        JOIN ders d ON s.ders_id = d.ders_id
        WHERE 1=1
    """
    params: list = []
    if akademik_yil:
        q += " AND s.akademik_yil = ?"
        params.append(int(akademik_yil))
    if donem:
        q += " AND LOWER(SUBSTR(TRIM(COALESCE(s.donem, '')), 1, 1)) = ?"
        params.append(_donem_key(donem))
    q += " ORDER BY s.skor_top DESC"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


@router.get("/havuz")
def havuz_listesi(yil: int, fakulte_id: Optional[int] = None, donem: Optional[str] = None):
    conn = _open_connection()
    try:
        use_term = bool(donem) and _havuz_has_donem(conn)
        q = """
            SELECT h.ders_id, d.ad, h.yil, h.fakulte_id, h.donem, h.statu, h.sayac, h.skor
            FROM havuz h
            LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
            WHERE h.yil = ?
        """
        params: list = [int(yil)]
        if fakulte_id is not None:
            q += " AND h.fakulte_id = ?"
            params.append(int(fakulte_id))
        if use_term:
            q += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
            params.append(_donem_key(donem))
        q += " ORDER BY h.skor DESC"

        cur = conn.cursor()
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return {"columns": cols, "data": [list(r) for r in rows]}
    finally:
        conn.close()


@router.get("/mufredat")
def mufredat_listesi(akademik_yil: int, bolum_id: Optional[int] = None, donem: Optional[str] = None):
    q = """
        SELECT md.mders_id, m.akademik_yil, m.bolum_id, m.donem, md.ders_id, d.ad
        FROM mufredat m
        JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
        JOIN ders d ON md.ders_id = d.ders_id
        WHERE m.akademik_yil = ?
    """
    params: list = [int(akademik_yil)]
    if bolum_id is not None:
        q += " AND m.bolum_id = ?"
        params.append(int(bolum_id))
    if donem:
        q += " AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?"
        params.append(_donem_key(donem))
    q += " ORDER BY d.ad"
    cols, rows = _run_query(q, tuple(params))
    return {"columns": cols, "data": rows}


@router.get("/akademik-plan")
def akademik_plan(fakulte_id: int, yil: int):
    conn = _open_connection()
    try:
        cur = conn.cursor()
        out = {"fakulte_id": int(fakulte_id), "yil": int(yil), "guz": [], "bahar": [], "overlap_count": 0}
        for term in ("g", "b"):
            cur.execute(
                """
                SELECT DISTINCT md.ders_id, d.ad
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                JOIN ders d ON d.ders_id = md.ders_id
                WHERE b.fakulte_id = ?
                  AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
                ORDER BY d.ad
                """,
                (int(fakulte_id), int(yil), term),
            )
            rows = [{"ders_id": int(r[0]), "ders_adi": str(r[1] or "")} for r in cur.fetchall()]
            if term == "g":
                out["guz"] = rows
            else:
                out["bahar"] = rows

        guz_ids = {int(item["ders_id"]) for item in out["guz"]}
        bahar_ids = {int(item["ders_id"]) for item in out["bahar"]}
        out["overlap_count"] = len(guz_ids & bahar_ids)
        out["guz_count"] = len(guz_ids)
        out["bahar_count"] = len(bahar_ids)
        out["balanced_4_plus_4"] = out["guz_count"] == 4 and out["bahar_count"] == 4 and out["overlap_count"] == 0
        return out
    finally:
        conn.close()


@router.get("/fakulteler")
def fakulte_listesi():
    cols, rows = _run_query("SELECT fakulte_id, ad, kampus FROM fakulte ORDER BY ad")
    return {"columns": cols, "data": rows}


@router.post("/mufredat/yukle")
async def mufredat_yukle(file: UploadFile = File(...), hedef_yil: int = 2022):
    filename = str(file.filename or "")
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Sadece .xlsx dosyasi desteklenir")

    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Veritabani bulunamadi")

    import tempfile

    fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        content = await file.read()
        with open(temp_path, "wb") as fh:
            fh.write(content)
        result = import_curriculum_excel(
            db_path=db_path,
            excel_path=temp_path,
            target_year=int(hedef_yil),
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

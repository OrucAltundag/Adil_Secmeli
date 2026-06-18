# -*- coding: utf-8 -*-
"""Seçmeli dersleri verilen yıl için havuza ekleyen servis.

Sıfırlama sonrası ya da yeni bir akademik yıl başlatıldığında, sistemin
``ders`` kataloğundaki **seçmeli** dersleri (``DersTipi = 'Seçmeli'``)
havuza tohumlamak için kullanılır.

- Yalnız VAR OLAN ders kayıtlarını ekler (yeni ders üretmez).
- Aynı (ders_id, yıl) kombinasyonu zaten havuzdaysa ATLANIR (idempotent).
- Skor / sayaç / statü VARSAYILAN değerlerle eklenir; gerçek puanlar daha sonra
  algoritma çalıştırıldığında oluşur.
- Fakülte/bölüm bilgisi ``ders``'ten okunur.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.course_type import build_elective_predicate


def _existing_havuz_ids(cur: sqlite3.Cursor, year: int, faculty_id: int | None) -> set[int]:
    where = "WHERE yil = ?"
    params: list[Any] = [int(year)]
    if faculty_id is not None:
        where += " AND fakulte_id = ?"
        params.append(int(faculty_id))
    cur.execute(f"SELECT DISTINCT CAST(ders_id AS INTEGER) FROM havuz {where}", params)
    return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}


def preview_seed(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
) -> dict[str, Any]:
    """Eklenecek seçmeli ders sayısını döndürür (UI önizleme için)."""
    cur = conn.cursor()
    fac_where = " AND d.fakulte_id = ?" if faculty_id is not None else ""
    params: list[Any] = [int(faculty_id)] if faculty_id is not None else []
    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    cur.execute(
        f"""
        SELECT d.ders_id FROM ders d
        WHERE {elective_predicate}
        {fac_where}
        """,
        params,
    )
    elective_ids = {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
    existing = _existing_havuz_ids(cur, year, faculty_id)
    new_ids = elective_ids - existing
    return {
        "elective_total": len(elective_ids),
        "already_in_pool": len(elective_ids & existing),
        "to_be_added": len(new_ids),
        "year": int(year),
        "faculty_id": faculty_id,
    }


def seed_havuz_from_electives(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    default_score: float | None = None,
) -> dict[str, Any]:
    """Seçmeli dersleri havuza ekler (idempotent). Caller commit eder.

    Yeni eklenen satırların ``statu = 0`` (havuzda), ``sayac = 0``, ``skor = None``
    (varsayılan: hesaplanmamış). UI'da "Veri yok" rengiyle görünür ve algoritma
    çalıştığında skoru oluşur.
    """
    cur = conn.cursor()
    fac_where = " AND d.fakulte_id = ?" if faculty_id is not None else ""
    params: list[Any] = [int(faculty_id)] if faculty_id is not None else []
    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    cur.execute(
        f"""
        SELECT d.ders_id, d.ad, d.fakulte_id, d.bolum_id
        FROM ders d
        WHERE {elective_predicate}
        {fac_where}
        ORDER BY d.ders_id
        """,
        params,
    )
    candidates = cur.fetchall()
    existing = _existing_havuz_ids(cur, year, faculty_id)

    added = 0
    skipped_existing = 0
    skipped_no_scope = 0
    for ders_id, ad, fac_id, bol_id in candidates:
        if ders_id is None:
            continue
        cid = int(ders_id)
        if cid in existing:
            skipped_existing += 1
            continue
        if fac_id is None:
            skipped_no_scope += 1
            continue
        cur.execute(
            """
            INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
            VALUES (?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (cid, int(year), int(fac_id), int(bol_id) if bol_id is not None else None,
             default_score, str(ad or "")),
        )
        added += 1
    return {
        "ok": True,
        "added": added,
        "skipped_existing": skipped_existing,
        "skipped_no_scope": skipped_no_scope,
        "year": int(year),
        "faculty_id": faculty_id,
        "message": (
            f"{added} seçmeli ders havuza eklendi. "
            f"({skipped_existing} zaten havuzdaydı, {skipped_no_scope} dersin fakülte bilgisi yok.)"
        ),
    }

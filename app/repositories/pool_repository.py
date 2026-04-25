# -*- coding: utf-8 -*-
"""Havuz verisi için repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class PoolRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_pool_rows(
        self,
        year: int,
        faculty_id: int | None = None,
        department_id: int | None = None,
        semester: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT h.*, d.kod AS course_code, d.ad AS course_name
            FROM havuz h
            LEFT JOIN ders d ON d.ders_id = CAST(h.ders_id AS INTEGER)
            WHERE h.yil = ?
        """
        params: list[Any] = [int(year)]
        if faculty_id is not None:
            query += " AND h.fakulte_id = ?"
            params.append(int(faculty_id))
        if department_id is not None:
            query += " AND COALESCE(d.bolum_id, h.bolum_id) = ?"
            params.append(int(department_id))
        if semester:
            key = "b" if str(semester).lower().startswith("b") else "g"
            query += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
            params.append(key)
        query += " ORDER BY h.statu DESC, h.skor DESC, d.ad"
        cur = self.conn.cursor()
        cur.execute(query, tuple(params))
        return fetch_all_dicts(cur)

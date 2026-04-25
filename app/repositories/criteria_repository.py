# -*- coding: utf-8 -*-
"""Kriter verisi için repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class CriteriaRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def find_by_scope(
        self,
        year: int,
        faculty_id: int | None = None,
        department_id: int | None = None,
        semester: str | None = None,
    ) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        query = """
            SELECT dk.*, d.kod AS course_code, d.ad AS course_name,
                   d.fakulte_id, d.bolum_id
            FROM ders_kriterleri dk
            LEFT JOIN ders d ON d.ders_id = dk.ders_id
            WHERE dk.yil = ?
        """
        params: list[Any] = [int(year)]
        if faculty_id is not None:
            query += " AND d.fakulte_id = ?"
            params.append(int(faculty_id))
        if department_id is not None:
            query += " AND d.bolum_id = ?"
            params.append(int(department_id))
        if semester:
            key = "b" if str(semester).lower().startswith("b") else "g"
            query += " AND LOWER(SUBSTR(TRIM(COALESCE(dk.donem, '')), 1, 1)) = ?"
            params.append(key)
        query += " ORDER BY d.ad"
        cur.execute(query, tuple(params))
        return fetch_all_dicts(cur)

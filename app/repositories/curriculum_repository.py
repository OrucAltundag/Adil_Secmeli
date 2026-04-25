# -*- coding: utf-8 -*-
"""Müfredat verisi için repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class CurriculumRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_curricula(self, year: int | None = None, department_id: int | None = None, semester: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM mufredat WHERE 1=1"
        params: list[Any] = []
        if year is not None:
            query += " AND akademik_yil = ?"
            params.append(int(year))
        if department_id is not None:
            query += " AND bolum_id = ?"
            params.append(int(department_id))
        if semester:
            key = "b" if str(semester).lower().startswith("b") else "g"
            query += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
            params.append(key)
        query += " ORDER BY akademik_yil DESC, bolum_id"
        cur = self.conn.cursor()
        cur.execute(query, tuple(params))
        return fetch_all_dicts(cur)

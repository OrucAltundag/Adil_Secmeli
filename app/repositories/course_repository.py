# -*- coding: utf-8 -*-
"""Ders/fakülte/bölüm okuma repository'si."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class CourseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_courses(self, faculty_id: int | None = None, elective_only: bool = False) -> list[dict[str, Any]]:
        from app.services.course_type import build_elective_predicate

        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(ders)")
        cols = {str(row[1]) for row in cur.fetchall()}
        type_parts = [col for col in ("DersTipi", "tip") if col in cols]
        type_expr = "COALESCE(" + ", ".join(f"d.{col}" for col in type_parts) + ", '')" if type_parts else "''"
        query = """
            SELECT d.ders_id, d.kod, d.ad, d.kredi, d.akts, d.fakulte_id, d.bolum_id,
                   {type_expr} AS course_type
            FROM ders d
        """.format(type_expr=type_expr)
        where: list[str] = []
        params: list[Any] = []
        if elective_only:
            where.append(build_elective_predicate(cur=cur, alias="d"))
        if faculty_id is not None:
            where.append("d.fakulte_id = ?")
            params.append(int(faculty_id))
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY d.ad"
        cur.execute(query, tuple(params))
        return fetch_all_dicts(cur)

    def list_faculties(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        # 'kampus' sutunu bazi semalarda bulunmayabilir; dinamik kontrol
        cur.execute("PRAGMA table_info(fakulte)")
        cols = {str(row[1]) for row in cur.fetchall()}
        select_cols = ["fakulte_id", "ad"]
        if "kampus" in cols:
            select_cols.append("kampus")
        cur.execute(
            f"SELECT {', '.join(select_cols)} FROM fakulte ORDER BY ad"
        )
        rows = fetch_all_dicts(cur)
        if "kampus" not in cols:
            for row in rows:
                row.setdefault("kampus", None)
        return rows

    def list_departments(self, faculty_id: int | None = None) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        if faculty_id is None:
            cur.execute("SELECT bolum_id, fakulte_id, ad FROM bolum ORDER BY ad")
        else:
            cur.execute("SELECT bolum_id, fakulte_id, ad FROM bolum WHERE fakulte_id = ? ORDER BY ad", (int(faculty_id),))
        return fetch_all_dicts(cur)

    def list_curriculum_years(self) -> list[int]:
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT akademik_yil FROM mufredat ORDER BY akademik_yil")
        return [int(row[0]) for row in cur.fetchall() if row and row[0] is not None]

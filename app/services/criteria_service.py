# -*- coding: utf-8 -*-
"""Kriter application service facade."""

from __future__ import annotations

import sqlite3

from app.core.result import ServiceResult
from app.db.session import db_session
from app.repositories.criteria_repository import CriteriaRepository
from app.services.criteria_completion_service import get_completion_summary


class CriteriaService:
    def __init__(self, conn: sqlite3.Connection | None = None, db_path: str | None = None):
        self.conn = conn
        self.db_path = db_path

    def list_criteria(self, year: int, faculty_id: int | None = None, department_id: int | None = None, semester: str | None = None) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(CriteriaRepository(self.conn).find_by_scope(year, faculty_id, department_id, semester))
        with db_session(self.db_path) as conn:
            return ServiceResult.ok(CriteriaRepository(conn).find_by_scope(year, faculty_id, department_id, semester))

    def completion_summary(self, scope_type: str, year: int, faculty_id: int | None = None, department_id: int | None = None, semester: str | None = None) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(get_completion_summary(self.conn, scope_type, year, faculty_id=faculty_id, department_id=department_id, semester=semester))
        with db_session(self.db_path) as conn:
            return ServiceResult.ok(get_completion_summary(conn, scope_type, year, faculty_id=faculty_id, department_id=department_id, semester=semester))

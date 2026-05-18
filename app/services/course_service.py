# -*- coding: utf-8 -*-
"""Ders/fakülte/bölüm application service."""

from __future__ import annotations

import sqlite3

from app.core.result import ServiceResult
from app.db.session import db_session
from app.repositories.course_repository import CourseRepository


class CourseService:
    def __init__(self, conn: sqlite3.Connection | None = None, db_path: str | None = None):
        self.conn = conn
        self.db_path = db_path

    def _repo(self, conn: sqlite3.Connection) -> CourseRepository:
        return CourseRepository(conn)

    def list_courses(self, faculty_id: int | None = None, elective_only: bool = False) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(self._repo(self.conn).list_courses(faculty_id=faculty_id, elective_only=elective_only))
        with db_session(self.db_path) as conn:
            return ServiceResult.ok(self._repo(conn).list_courses(faculty_id=faculty_id, elective_only=elective_only))

    def list_faculties(self) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(self._repo(self.conn).list_faculties())
        with db_session(self.db_path) as conn:
            return ServiceResult.ok(self._repo(conn).list_faculties())

    def list_departments(self, faculty_id: int | None = None) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(self._repo(self.conn).list_departments(faculty_id=faculty_id))
        with db_session(self.db_path) as conn:
            return ServiceResult.ok(self._repo(conn).list_departments(faculty_id=faculty_id))

    def list_curriculum_years(self) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(self._repo(self.conn).list_curriculum_years())
        with db_session(self.db_path) as conn:
            return ServiceResult.ok(self._repo(conn).list_curriculum_years())

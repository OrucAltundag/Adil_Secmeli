# -*- coding: utf-8 -*-
"""UI/API için servis factory."""

from __future__ import annotations

import sqlite3

from app.core.config import AppConfig, load_app_config
from app.services.course_service import CourseService
from app.services.criteria_service import CriteriaService
from app.services.health_service import HealthService
from app.services.report_table_service import ReportTableService
from app.services.system_service import SystemService


class ServiceFactory:
    def __init__(self, conn: sqlite3.Connection | None = None, db_path: str | None = None, config: AppConfig | None = None):
        self.conn = conn
        self.config = config or load_app_config()
        self.db_path = db_path or self.config.sqlite_db_path

    def get_course_service(self) -> CourseService:
        return CourseService(conn=self.conn, db_path=self.db_path)

    def get_criteria_service(self) -> CriteriaService:
        return CriteriaService(conn=self.conn, db_path=self.db_path)

    def get_reporting_table_service(self) -> ReportTableService:
        if self.conn is None:
            raise RuntimeError("ReportTableService için açık sqlite bağlantısı gerekir.")
        return ReportTableService(self.conn)

    def get_system_service(self) -> SystemService:
        return SystemService(conn=self.conn, db_path=self.db_path, config=self.config)

    def get_health_service(self, user_context=None) -> HealthService:
        return HealthService(
            db_path=self.db_path, config=self.config, user_context=user_context
        )


def get_service_factory(conn: sqlite3.Connection | None = None, db_path: str | None = None, config: AppConfig | None = None) -> ServiceFactory:
    return ServiceFactory(conn=conn, db_path=db_path, config=config)


def get_course_service(conn: sqlite3.Connection | None = None, db_path: str | None = None) -> CourseService:
    return get_service_factory(conn=conn, db_path=db_path).get_course_service()


def get_criteria_service(conn: sqlite3.Connection | None = None, db_path: str | None = None) -> CriteriaService:
    return get_service_factory(conn=conn, db_path=db_path).get_criteria_service()


def get_reporting_service(conn: sqlite3.Connection | None = None, db_path: str | None = None) -> ReportTableService:
    return get_service_factory(conn=conn, db_path=db_path).get_reporting_table_service()


def get_system_service(conn: sqlite3.Connection | None = None, db_path: str | None = None, config: AppConfig | None = None) -> SystemService:
    return get_service_factory(conn=conn, db_path=db_path, config=config).get_system_service()


def get_health_service(db_path: str | None = None, config: AppConfig | None = None, user_context=None) -> HealthService:
    return get_service_factory(db_path=db_path, config=config).get_health_service(user_context=user_context)


def get_curriculum_service(*args, **kwargs):
    return get_service_factory(*args, **kwargs)


def get_pool_service(*args, **kwargs):
    return get_service_factory(*args, **kwargs)


def get_decision_service(*args, **kwargs):
    return get_service_factory(*args, **kwargs)


def get_import_service(*args, **kwargs):
    return get_service_factory(*args, **kwargs)

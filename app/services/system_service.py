# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false
# NOT: SQLAlchemy bagimliliklari (Engine/Connection Optional, text() ↔ str)
# Pylance stubs'larinda asiri korumacidir; runtime'da sorunsuz calisir.
"""Sistem sağlığı ve mimari denetim servisi."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from app.core.config import AppConfig, load_app_config
from app.core.database_policy import database_policy_summary
from app.core.permissions import UserContext, can
from app.core.result import ServiceResult
from app.db.backend import is_sqlite_connection, is_sqlite_url
from app.db.schema_compat import ensure_reporting_schema
from app.db.session import db_session
from app.repositories.system_repository import SystemRepository
from app.services.architecture_audit_service import generate_architecture_audit_report
from app.services.schema_health_service import check_schema_health
from app.viewmodels.system_health import SystemHealthViewModel

LEGACY_DB_ACCESS_ALLOWLIST = {
    "view_tab.py": "Admin tablo görüntüleyici ve SQL Console",
    "data_management_page.py": "Import governance için aşamalı geçişte doğrudan servis bağlantısı",
}


def _unwrap_sqlite_connection(conn: Any) -> Any:
    if is_sqlite_connection(conn):
        return conn
    for attr in ("driver_connection", "dbapi_connection", "connection"):
        try:
            candidate = getattr(conn, attr, None)
        except Exception:
            candidate = None
        if is_sqlite_connection(candidate):
            return candidate
    return conn


class SystemService:
    def __init__(self, conn: sqlite3.Connection | None = None, db_path: str | None = None, config: AppConfig | None = None):
        self.conn = conn
        self.db_path = db_path
        self.config = config or load_app_config()

    def health(self) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(self._health_with_conn(self.conn))
        if not is_sqlite_url(self.config.database_url):
            return ServiceResult.ok(self._postgresql_health())
        with db_session(self.db_path or self.config.sqlite_db_path) as conn:
            return ServiceResult.ok(self._health_with_conn(conn))

    def _health_with_conn(self, conn: sqlite3.Connection) -> dict[str, Any]:
        conn = _unwrap_sqlite_connection(conn)
        if is_sqlite_connection(conn):
            schema = ensure_reporting_schema(conn)
            repo = SystemRepository(conn)
            info = repo.database_info(self.db_path or self.config.sqlite_db_path)
        else:
            schema = {"postgresql": {"runtime_schema_compat": "disabled"}}
            schema_health_probe = check_schema_health(conn=conn, db_path=self.db_path or self.config.sqlite_db_path, config=self.config)
            info = {
                "db_path": None,
                "database_url": self.config.database_url,
                "exists": True,
                "table_count": int((schema_health_probe.get("required_tables") or {}).get("existing_count") or 0),
                "connection_ok": True,
            }
        schema_health = check_schema_health(conn=conn, db_path=self.db_path or self.config.sqlite_db_path, config=self.config)
        return {
            "app_version": self.config.version,
            "mode": self.config.app_mode,
            "environment": self.config.environment,
            "db": info,
            "schema_ok": bool(schema_health.get("schema_ok")),
            "schema": schema,
            "schema_health": schema_health,
            "debug_tools_enabled": self.config.enable_developer_tools,
            "sql_console_enabled": self.config.enable_sql_console,
            "runtime_schema_mutation_allowed": bool(
                (schema_health.get("schema_compat") or {}).get("runtime_mutation_allowed")
            ),
        }

    def _postgresql_health(self) -> dict[str, Any]:
        from app.db.database import get_engine

        with get_engine().connect() as conn:
            conn.exec_driver_sql("SELECT 1")
            return self._health_with_conn(conn)

    def view_model(self, user_context: UserContext | None = None) -> SystemHealthViewModel:
        data = self.health().unwrap()
        return SystemHealthViewModel(
            app_mode=str(data.get("mode")),
            environment=str(data.get("environment")),
            db_path=str((data.get("db") or {}).get("db_path") or ""),
            db_connection_ok=bool((data.get("db") or {}).get("connection_ok")),
            schema_ok=bool(data.get("schema_ok")),
            debug_tools_enabled=bool(data.get("debug_tools_enabled")),
            sql_console_enabled=bool(data.get("sql_console_enabled")),
            sql_console_allowed=can(user_context, "use_sql_console", config=self.config),
            table_count=int((data.get("db") or {}).get("table_count") or 0),
            runtime_schema_mutation_allowed=bool(data.get("runtime_schema_mutation_allowed")),
        )

    def architecture_findings(self, ui_dir: str = "app/ui/tabs") -> ServiceResult:
        report = generate_architecture_audit_report()
        findings = [
            item
            for items in (report.get("groups") or {}).values()
            for item in items
            if item.get("layer") == "ui"
        ]
        return ServiceResult.ok(findings)

    def schema_health(self) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(
                check_schema_health(conn=self.conn, db_path=self.db_path or self.config.sqlite_db_path, config=self.config)
            )
        with db_session(self.db_path or self.config.sqlite_db_path) as conn:
            return ServiceResult.ok(
                check_schema_health(conn=conn, db_path=self.db_path or self.config.sqlite_db_path, config=self.config)
            )

    def architecture_audit(self) -> ServiceResult:
        return ServiceResult.ok(generate_architecture_audit_report())

    def config_summary(self) -> ServiceResult:
        return ServiceResult.ok(
            {
                "app_mode": self.config.app_mode,
                "environment": self.config.environment,
                "debug": self.config.debug,
                "database_url": self.config.database_url,
                "sqlite_db_path": self.config.sqlite_db_path,
                "enable_schema_compat": self.config.enable_schema_compat,
                "allow_runtime_schema_mutation": self.config.allow_runtime_schema_mutation,
                "allow_runtime_schema_mutation_in_production": self.config.allow_runtime_schema_mutation_in_production,
                "enable_sql_console": self.config.enable_sql_console,
                "enable_developer_tools": self.config.enable_developer_tools,
                "database_policy": database_policy_summary(self.config),
            }
        )

    def sql_console_audit_logs(self, limit: int = 50) -> ServiceResult:
        if self.conn is not None:
            return ServiceResult.ok(SystemRepository(self.conn).latest_sql_console_audit_logs(limit=limit))
        with db_session(self.db_path or self.config.sqlite_db_path) as conn:
            return ServiceResult.ok(SystemRepository(conn).latest_sql_console_audit_logs(limit=limit))

    def backup_database(self, target_path: str, source_path: str | None = None) -> ServiceResult:
        from app.db.sqlite_connection import connect_sqlite

        source_path = os.path.abspath(source_path or self.db_path or self.config.sqlite_db_path)
        target_path = os.path.abspath(target_path)
        if not os.path.exists(source_path):
            return ServiceResult.fail("Yedeklenecek veritabanı bulunamadı.", errors=[{"path": source_path}])
        source = connect_sqlite(source_path)
        target = connect_sqlite(target_path)
        try:
            source.backup(target)
            return ServiceResult.ok({"source": source_path, "target": target_path}, message="Yedek alındı.")
        finally:
            target.close()
            source.close()

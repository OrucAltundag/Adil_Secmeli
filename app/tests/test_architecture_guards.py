# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.api import routes
from app.core.config import AppConfig
from app.core.database_policy import (
    database_policy_summary,
    runtime_schema_mutation_allowed,
)
from app.core.permissions import UserContext, can
from app.db.schema_compat import ensure_reporting_schema
from app.services.architecture_audit_service import generate_architecture_audit_report
from app.services.schema_health_service import check_schema_health

ROOT = Path(__file__).resolve().parents[2]


def _minimal_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
            CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
            CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ders_adi TEXT, ad TEXT);
            CREATE TABLE havuz (id INTEGER PRIMARY KEY, ders_id INTEGER, yil INTEGER, durum INTEGER);
            CREATE TABLE skor (id INTEGER PRIMARY KEY, ders_id INTEGER, akademik_yil INTEGER);
            CREATE TABLE ders_kriterleri (id INTEGER PRIMARY KEY, ders_id INTEGER, yil INTEGER, donem TEXT);
            """
        )
        ensure_reporting_schema(conn)
    finally:
        conn.close()


def test_database_policy_production_defaults_are_safe():
    cfg = AppConfig(
        environment="production",
        enable_schema_compat=True,
        allow_runtime_schema_mutation=False,
        allow_runtime_schema_mutation_in_production=False,
        enable_sql_console=True,
        enable_developer_tools=True,
    )
    assert runtime_schema_mutation_allowed(cfg) is False
    assert can(UserContext(role="admin", is_admin=True), "use_sql_console", config=cfg) is False
    summary = database_policy_summary(cfg)
    assert summary["official_db_access"] == "repository"
    assert summary["sqlite_allowed_in_ui"] is False


def test_schema_compat_creates_audit_tables_and_logs(tmp_path):
    db_path = tmp_path / "compat.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
            CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
            CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ad TEXT);
            CREATE TABLE havuz (id INTEGER PRIMARY KEY, ders_id INTEGER, yil INTEGER, durum INTEGER);
            CREATE TABLE skor (id INTEGER PRIMARY KEY, ders_id INTEGER, akademik_yil INTEGER);
            CREATE TABLE ders_kriterleri (id INTEGER PRIMARY KEY, ders_id INTEGER, yil INTEGER);
            """
        )
        result = ensure_reporting_schema(conn)
        assert "architecture" in result
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='schema_compat_logs'"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sql_console_audit_logs'"
        ).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM schema_compat_logs").fetchone()[0] > 0
    finally:
        conn.close()


def test_schema_health_reports_required_tables(tmp_path):
    db_path = tmp_path / "health.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ders_adi TEXT)")
        health = check_schema_health(conn=conn, db_path=str(db_path), config=AppConfig(sqlite_db_path=str(db_path)))
        assert health["schema_ok"] is False
        assert "fakulte" in health["required_tables"]["missing_tables"]
    finally:
        conn.close()


def test_architecture_audit_service_reports_layers():
    report = generate_architecture_audit_report()
    assert "ui_direct_db_access" in report["groups"]
    assert "api_raw_sql" in report["groups"]
    assert "service_sqlite_usage" in report["groups"]
    assert isinstance(report["violation_count"], int)


def test_ui_direct_sqlite_connect_guard_allowlist():
    allowlist = {
        "app/ui/tabs/view_tab.py",
        "app/ui/tabs/data_management_page.py",
    }
    offenders: list[str] = []
    for path in (ROOT / "app" / "ui").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "sqlite3.connect" in text and rel not in allowlist:
            offenders.append(rel)
    assert offenders == []


def test_repository_layer_contains_required_modules():
    required = [
        "course_repository.py",
        "criteria_repository.py",
        "curriculum_repository.py",
        "pool_repository.py",
        "decision_repository.py",
        "report_repository.py",
        "benchmark_repository.py",
        "system_repository.py",
    ]
    missing = [name for name in required if not (ROOT / "app" / "repositories" / name).exists()]
    assert missing == []


def test_system_api_smoke_endpoints(monkeypatch, tmp_path):
    db_path = tmp_path / "api.db"
    _minimal_db(db_path)
    monkeypatch.setattr(routes, "_get_db_path", lambda: str(db_path))
    schema = routes.system_schema_health()
    audit = routes.system_architecture_audit()
    config = routes.system_config_summary()
    logs = routes.system_sql_console_audit_logs()
    assert schema["success"] is True
    assert audit["success"] is True
    assert config["success"] is True
    assert logs["success"] is True

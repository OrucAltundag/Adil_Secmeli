# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.api import routes
from app.core.config import load_app_config
from app.core.errors import BusinessRuleAppError, ValidationAppError
from app.core.permissions import UserContext, can
from app.core.result import ServiceResult
from app.db.session import db_session, init_database, open_sqlite_connection
from app.repositories.course_repository import CourseRepository
from app.services.course_service import CourseService
from app.services.import_validation_service import validate_import_request
from app.services.pool_state_validation_service import validate_pool_transition_context
from app.services.system_service import SystemService


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT, kampus TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            kod TEXT,
            ad TEXT,
            kredi REAL,
            akts REAL,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            DersTipi TEXT,
            tip TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            durum TEXT,
            versiyon INTEGER
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            skor_top REAL
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT
        );
        """
    )
    conn.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik', 'Merkez')")
    conn.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    conn.execute("INSERT INTO ders VALUES (101, 'BLM101', 'Algoritma', 3, 5, 1, 10, 'Secmeli', 'Secmeli')")
    conn.execute("INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon) VALUES (1, 10, 2026, 'Guz', 'Resmi', 1)")
    conn.commit()
    conn.close()
    init_database(path)
    return path


def test_config_defaults_and_production_sql_console(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ENABLE_SQL_CONSOLE", raising=False)
    cfg = load_app_config()
    assert cfg.app_mode == "auto"
    assert cfg.enable_sql_console is False


def test_postgresql_config_blocks_legacy_sqlite_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/adil_test")
    cfg = load_app_config()
    assert cfg.db_backend == "postgresql"
    with pytest.raises(RuntimeError):
        open_sqlite_connection()


def test_service_result_and_app_error_formats():
    ok = ServiceResult.ok(data={"x": 1}, message="Tamam")
    assert ok.to_api()["success"] is True
    fail = ServiceResult.fail("Hata", errors=[{"code": "X"}])
    assert fail.to_api()["success"] is False

    err = ValidationAppError("Alan hatalı", code="BAD_FIELD", suggestion="Alanı düzeltin.")
    assert err.to_api_response()["error"]["code"] == "BAD_FIELD"
    business = BusinessRuleAppError("Kural ihlali", suggestion="Yetkili onayı alın.")
    assert "Öneri" in business.to_user_message()


def test_db_session_commit_and_rollback():
    path = _tmp_db()
    try:
        with db_session(path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS tx_test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO tx_test (name) VALUES ('committed')")
        check = sqlite3.connect(path)
        try:
            assert check.execute("SELECT COUNT(*) FROM tx_test").fetchone()[0] == 1
        finally:
            check.close()

        with pytest.raises(RuntimeError):
            with db_session(path) as conn:
                conn.execute("INSERT INTO tx_test (name) VALUES ('rolled_back')")
                raise RuntimeError("rollback")
        check = sqlite3.connect(path)
        try:
            assert check.execute("SELECT COUNT(*) FROM tx_test").fetchone()[0] == 1
        finally:
            check.close()
    finally:
        os.unlink(path)


def test_repository_and_service_reuse():
    path = _tmp_db()
    try:
        with db_session(path) as conn:
            repo_rows = CourseRepository(conn).list_courses(faculty_id=1, elective_only=False)
            assert repo_rows and repo_rows[0]["ders_id"] == 101
            service_rows = CourseService(conn).list_courses(faculty_id=1).unwrap()
            assert service_rows == repo_rows
    finally:
        os.unlink(path)


def test_shared_validation_services():
    bad_import = validate_import_request("bad", "veri.txt")
    assert bad_import.is_valid is False
    bad_pool = validate_pool_transition_context({"year": 2026, "current_status": 99})
    assert bad_pool.is_valid is False


def test_permission_rules(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ENABLE_DEVELOPER_TOOLS", "true")
    monkeypatch.setenv("ENABLE_SQL_CONSOLE", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    cfg = load_app_config()
    assert can(UserContext(role="admin", is_admin=True), "use_sql_console", config=cfg) is True
    assert can(UserContext(role="viewer"), "use_sql_console", config=cfg) is False
    assert can(UserContext(role="faculty_coordinator"), "approve_import", config=cfg) is True
    assert can(UserContext(role="viewer"), "approve_cancel", config=cfg) is False


def test_api_health_and_system_service(monkeypatch):
    path = _tmp_db()
    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    try:
        response = routes.health()
        assert response["success"] is True
        assert response["data"]["db"]["connection_ok"] is True
        with db_session(path) as conn:
            vm = SystemService(conn=conn, db_path=path).view_model(UserContext(role="viewer"))
            assert vm.db_connection_ok is True
    finally:
        os.unlink(path)


def test_ui_imports_and_architecture_scan():
    from app.ui.tabs.system_health_page import SystemHealthPage
    from app.ui.tabs.view_tab import ViewTab

    assert SystemHealthPage is not None
    assert ViewTab is not None
    findings = SystemService(config=load_app_config()).architecture_findings().unwrap()
    assert isinstance(findings, list)
    system_health_source = open("app/ui/tabs/system_health_page.py", encoding="utf-8").read()
    assert "sqlite3.connect" not in system_health_source

# -*- coding: utf-8 -*-
"""Veritabanı sağlık kontrolleri testleri (geçici SQLite)."""

from __future__ import annotations

import sqlite3

import pytest

from app.health.checks.base_check import HealthContext
from app.health.checks.database_check import (
    SQLiteConnectionCheck,
    SQLiteIntegrityCheck,
    SQLiteTableCountCheck,
    SQLiteWritePermissionCheck,
)
from app.health.models import HealthStatus

pytestmark = pytest.mark.db


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "dbhealth.db")
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE a (id INTEGER PRIMARY KEY);"
        "CREATE TABLE b (id INTEGER PRIMARY KEY);"
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def ctx(db_path):
    return HealthContext.build(db_path=db_path, mode="full")


def test_connection_check_ok(ctx):
    res = SQLiteConnectionCheck().safe_run(ctx)
    assert res.status == HealthStatus.OK.value
    assert res.duration_ms >= 0
    assert res.source == "SQLiteConnectionCheck"


def test_connection_check_missing_file(tmp_path):
    ctx = HealthContext.build(
        db_path=str(tmp_path / "yok.db"), mode="quick"
    )
    res = SQLiteConnectionCheck().safe_run(ctx)
    assert res.status == HealthStatus.CRITICAL.value
    assert "bulunamadı" in res.detail


def test_integrity_check_ok(ctx):
    res = SQLiteIntegrityCheck().safe_run(ctx)
    assert res.status == HealthStatus.OK.value


def test_table_count_check(ctx):
    res = SQLiteTableCountCheck().safe_run(ctx)
    # 2 tablo var; min eşik altında olduğu için WARNING beklenir (çökmez).
    assert res.status in {
        HealthStatus.OK.value,
        HealthStatus.WARNING.value,
    }
    assert res.metadata.get("table_count") == 2


def test_write_permission_uses_temp_and_rolls_back(ctx, db_path):
    res = SQLiteWritePermissionCheck().safe_run(ctx)
    assert res.status == HealthStatus.OK.value
    # Gerçek veri bozulmamalı: yalnızca beklenen 2 tablo kalmalı.
    conn = sqlite3.connect(db_path)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert tables == {"a", "b"}


def test_safe_run_never_raises(ctx):
    # Bilinçli olarak bozuk bir context ile bile safe_run patlamamalı.
    broken = HealthContext.build(db_path="??invalid::path??", mode="quick")
    res = SQLiteIntegrityCheck().safe_run(broken)
    assert res.status in {
        HealthStatus.FAILED.value,
        HealthStatus.CRITICAL.value,
        HealthStatus.SKIPPED.value,
        HealthStatus.OK.value,
    }

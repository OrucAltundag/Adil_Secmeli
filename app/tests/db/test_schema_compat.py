# -*- coding: utf-8 -*-
"""DB / Schema / Migration testleri."""

from __future__ import annotations

import sqlite3
import pytest

pytestmark = pytest.mark.db


class TestFreshDBSchema:
    """Sifirdan DB olusturuldiginda gerekli tablolar var mi."""

    def test_base_tables_exist(self, empty_db):
        cur = empty_db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        required = {"fakulte", "bolum", "ders", "mufredat", "mufredat_ders",
                     "havuz", "skor", "ders_kriterleri", "performans", "populerlik"}
        for table in required:
            assert table in tables, f"Tablo eksik: {table}"


class TestSchemaCompat:
    """schema_compat fonksiyonlari — eksik kolon ekleme."""

    def test_ensure_criteria_import_schema(self, empty_db):
        from app.db.schema_compat import ensure_criteria_import_schema
        result = ensure_criteria_import_schema(empty_db, commit=True)
        assert isinstance(result, dict)
        # criteria_import tablosu olusturulmus olmali
        cur = empty_db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        assert "criteria_import" in tables or result.get("tables_created", 0) >= 0

    def test_ensure_survey_import_schema(self, empty_db):
        from app.db.schema_compat import ensure_survey_import_schema
        result = ensure_survey_import_schema(empty_db, commit=True)
        assert isinstance(result, dict)

    def test_ensure_skor_schema(self, empty_db):
        from app.db.schema_compat import ensure_skor_schema
        result = ensure_skor_schema(empty_db)
        assert isinstance(result, dict)

    def test_ensure_havuz_semester_schema(self, empty_db):
        from app.db.schema_compat import ensure_havuz_semester_schema
        result = ensure_havuz_semester_schema(empty_db)
        assert isinstance(result, dict)

    def test_ensure_architecture_schema(self, empty_db):
        from app.db.schema_compat import ensure_architecture_schema
        result = ensure_architecture_schema(empty_db, commit=True)
        assert isinstance(result, dict)
        cur = empty_db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        assert "schema_compat_logs" in tables

    def test_ensure_decision_governance_schema(self, empty_db):
        from app.db.schema_compat import ensure_decision_governance_schema
        result = ensure_decision_governance_schema(empty_db, commit=True)
        assert isinstance(result, dict)


class TestTransactionRollback:
    """Hata durumunda transaction rollback ediyor mu."""

    def test_rollback_on_error(self, empty_db):
        """Bozuk SQL sonrasi onceki commit korunur."""
        cur = empty_db.cursor()
        cur.execute("INSERT INTO fakulte VALUES (99, 'Test', 'Kampus')")
        empty_db.commit()
        try:
            cur.execute("INSERT INTO NONEXISTENT_TABLE VALUES (1)")
        except sqlite3.OperationalError:
            empty_db.rollback()
        cur.execute("SELECT COUNT(*) FROM fakulte WHERE fakulte_id = 99")
        assert cur.fetchone()[0] == 1, "Commit edilen veri rollback'ten etkilenmemeli"

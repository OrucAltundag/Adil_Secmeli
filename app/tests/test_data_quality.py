# -*- coding: utf-8 -*-
"""
Veri kalitesi testleri (PHASE 4)

Test sütunları:
- Veri kapsama hesaplaması
- Veri olgunluğu değerlendirmesi
- Eksik veri tespiti
- Doğrulama sorunları kaydı
- Karar güven skoru
- Decision engine entegrasyonu
"""

import sqlite3
from datetime import datetime, timezone

import pytest

from app.services.data_quality_integration_service import (
    assess_data_readiness_cursor,
    generate_coverage_report_cursor,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture
def test_db_memory():
    """In-memory SQLite veritabanı oluştur"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Temel tablolar
    cur.execute("""
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            kod TEXT,
            ad TEXT,
            fakulte_id INTEGER,
            bolum_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER,
            gecen_ogrenci INTEGER,
            basari_ortalamasi REAL,
            kontenjan INTEGER,
            kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            akademik_yil INTEGER,
            ortalama_not REAL,
            basari_orani REAL
        )
    """)

    cur.execute("""
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            akademik_yil INTEGER,
            doluluk_orani REAL,
            kontenjan INTEGER,
            talep_sayisi INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE anket_sonuclari (
            sonuc_id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            oy_sayisi INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE data_validation_issues (
            id INTEGER PRIMARY KEY,
            course_id INTEGER,
            issue_type TEXT,
            severity TEXT,
            message TEXT,
            is_resolved INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE missing_data_items (
            id INTEGER PRIMARY KEY,
            course_id INTEGER,
            year INTEGER,
            semester TEXT,
            missing_field TEXT,
            severity TEXT,
            message TEXT,
            detected_at TEXT,
            is_resolved INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    yield conn
    conn.close()


class TestDataCoverage:
    """Veri kapsama hesaplama testleri"""

    def test_empty_database(self, test_db_memory):
        """Boş veritabanında kapsama hesapla"""
        cur = test_db_memory.cursor()
        report = generate_coverage_report_cursor(cur, year=2024)

        assert report["total_courses"] == 0
        assert report["coverage_percentage"] == 0.0

    def test_coverage_with_partial_data(self, test_db_memory):
        """Kısmi verilerle kapsama hesapla"""
        cur = test_db_memory.cursor()

        # 5 ders ekle
        for i in range(1, 6):
            cur.execute(
                "INSERT INTO ders (ders_id, ad, fakulte_id) VALUES (?, ?, ?)",
                (i, f"Ders {i}", 1)
            )

        # 3 tanesine kriter verisi ekle
        for i in range(1, 4):
            cur.execute(
                "INSERT INTO ders_kriterleri (ders_id, yil, toplam_ogrenci, gecen_ogrenci) VALUES (?, ?, ?, ?)",
                (i, 2024, 50, 40)
            )

        # 2 tanesine performans verisi ekle
        for i in range(1, 3):
            cur.execute(
                "INSERT INTO performans (ders_id, akademik_yil, basari_orani) VALUES (?, ?, ?)",
                (i, 2024, 0.8)
            )

        test_db_memory.commit()

        report = generate_coverage_report_cursor(cur, year=2024)

        assert report["total_courses"] == 5
        assert report["courses_with_criteria"] == 3
        assert report["courses_with_performance"] == 2
        assert report["coverage_percentage"] > 0

    def test_department_scope_does_not_union_other_departments_via_legacy_path(self):
        conn = sqlite3.connect(":memory:")
        try:
            cur = conn.cursor()
            cur.executescript(
                """
                CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
                CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
                CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ad TEXT, fakulte_id INTEGER, bolum_id INTEGER);
                CREATE TABLE mufredat (
                    mufredat_id INTEGER PRIMARY KEY, fakulte_id INTEGER, bolum_id INTEGER,
                    akademik_yil INTEGER, donem TEXT
                );
                CREATE TABLE mufredat_ders (mufredat_id INTEGER, ders_id INTEGER);
                CREATE TABLE ders_kriterleri (
                    ders_id INTEGER, yil INTEGER, anket_dersi_secen INTEGER
                );
                CREATE TABLE performans (ders_id INTEGER, akademik_yil INTEGER, basari_orani REAL);
                CREATE TABLE populerlik (ders_id INTEGER, akademik_yil INTEGER, doluluk_orani REAL);
                INSERT INTO fakulte VALUES (1, 'Fakulte');
                INSERT INTO bolum VALUES (10, 1, 'Bolum A');
                INSERT INTO bolum VALUES (20, 1, 'Bolum B');
                INSERT INTO ders VALUES (101, 'A Dersi', 1, 10);
                INSERT INTO ders VALUES (201, 'B Dersi', 1, 20);
                INSERT INTO mufredat VALUES (1, 1, 10, 2026, 'Guz');
                INSERT INTO mufredat VALUES (2, 1, 20, 2026, 'Guz');
                INSERT INTO mufredat_ders VALUES (1, 101);
                INSERT INTO mufredat_ders VALUES (2, 201);
                INSERT INTO ders_kriterleri VALUES (101, 2026, 1);
                INSERT INTO performans VALUES (101, 2026, 0.8);
                INSERT INTO populerlik VALUES (101, 2026, 0.8);
                """
            )
            report_a = generate_coverage_report_cursor(
                cur, year=2026, faculty_id=1, department_id=10
            )
            report_b = generate_coverage_report_cursor(
                cur, year=2026, faculty_id=1, department_id=20
            )

            assert report_a["total_courses"] == 1
            assert report_a["courses_with_criteria"] == 1
            assert report_b["total_courses"] == 1
            assert report_b["courses_with_criteria"] == 0
        finally:
            conn.close()


class TestDataReadiness:
    """Veri olgunluğu değerlendirme testleri"""

    def test_readiness_not_ready(self, test_db_memory):
        """Hazır olmayan veri için seviye kontrolü"""
        cur = test_db_memory.cursor()

        # 10 ders ekle, 1 tanesi hariç hiç veri yok
        for i in range(1, 11):
            cur.execute(
                "INSERT INTO ders (ders_id, ad, fakulte_id) VALUES (?, ?, ?)",
                (i, f"Ders {i}", 1)
            )

        test_db_memory.commit()

        readiness = assess_data_readiness_cursor(cur, year=2024)

        assert readiness["readiness_score"] < 50
        assert readiness["readiness_level"] in ["not_ready", "low"]

    def test_readiness_decision_ready(self, test_db_memory):
        """Karar almaya hazır veri için seviye kontrolü"""
        cur = test_db_memory.cursor()

        # 5 ders ekle, hepsi tam veri ile
        for i in range(1, 6):
            cur.execute(
                "INSERT INTO ders (ders_id, ad, fakulte_id) VALUES (?, ?, ?)",
                (i, f"Ders {i}", 1)
            )

            # Kriter
            cur.execute(
                "INSERT INTO ders_kriterleri (ders_id, yil, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (i, 2024, 50, 40, 70.0, 40, 35)
            )

            # Performans
            cur.execute(
                "INSERT INTO performans (ders_id, akademik_yil, basari_orani, ortalama_not) VALUES (?, ?, ?, ?)",
                (i, 2024, 0.8, 75.0)
            )

            # Populerlik
            cur.execute(
                "INSERT INTO populerlik (ders_id, akademik_yil, doluluk_orani, kontenjan) VALUES (?, ?, ?, ?)",
                (i, 2024, 0.85, 40)
            )

            # Anket
            cur.execute(
                "INSERT INTO anket_sonuclari (ders_id, oy_sayisi) VALUES (?, ?)",
                (i, 35)
            )

        test_db_memory.commit()

        readiness = assess_data_readiness_cursor(cur, year=2024)

        assert readiness["readiness_score"] > 70
        assert readiness["readiness_level"] in ["good", "decision_ready"]


class TestMissingDataDetection:
    """Eksik veri tespiti testleri"""

    def test_detect_missing_criteria(self, test_db_memory):
        """Eksik kriter verisi tespiti"""
        cur = test_db_memory.cursor()

        # Veri ekle
        cur.execute(
            "INSERT INTO ders (ders_id, ad, fakulte_id) VALUES (1, 'Test Dersi', 1)"
        )
        cur.execute(
            "INSERT INTO performans (ders_id, akademik_yil, basari_orani) VALUES (1, 2024, 0.8)"
        )
        test_db_memory.commit()

        # Kriter verisi yok, performans var
        cur.execute(
            "SELECT COUNT(*) FROM ders_kriterleri WHERE ders_id = 1 AND yil = 2024"
        )
        criteria_count = cur.fetchone()[0]
        assert criteria_count == 0

    def test_insert_missing_data_item(self, test_db_memory):
        """Eksik veri öğesi kayıt"""
        cur = test_db_memory.cursor()

        cur.execute(
            """
            INSERT INTO missing_data_items
            (course_id, year, semester, missing_field, severity, message, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 2024, "Güz", "kriter_verisi", "warning", "Kriter verisi eksik", _now())
        )
        test_db_memory.commit()

        cur.execute("SELECT COUNT(*) FROM missing_data_items WHERE course_id = 1")
        count = cur.fetchone()[0]
        assert count == 1


class TestValidationIssues:
    """Doğrulama sorunları testleri"""

    def test_record_validation_issue(self, test_db_memory):
        """Doğrulama sorununu kaydet"""
        cur = test_db_memory.cursor()

        cur.execute(
            """
            INSERT INTO data_validation_issues
            (course_id, issue_type, severity, message, is_resolved, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, "invalid_score", "critical", "Skor hesaplanamadı", 0, _now())
        )
        test_db_memory.commit()

        cur.execute(
            "SELECT COUNT(*) FROM data_validation_issues WHERE severity = 'critical'"
        )
        critical_count = cur.fetchone()[0]
        assert critical_count == 1

    def test_resolve_validation_issue(self, test_db_memory):
        """Doğrulama sorununu çöz"""
        cur = test_db_memory.cursor()

        # Sorun ekle
        cur.execute(
            """
            INSERT INTO data_validation_issues
            (course_id, issue_type, severity, message, is_resolved, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (1, "invalid_score", "critical", "Skor hesaplanamadı", 0, _now())
        )
        test_db_memory.commit()
        issue_id = cur.lastrowid

        # Çöz
        cur.execute(
            "UPDATE data_validation_issues SET is_resolved = 1 WHERE id = ?",
            (issue_id,)
        )
        test_db_memory.commit()

        # Kontrol
        cur.execute("SELECT is_resolved FROM data_validation_issues WHERE id = ?", (issue_id,))
        is_resolved = cur.fetchone()[0]
        assert is_resolved == 1


class TestCoverageReportPersistence:
    """Kapsama raporu kalıcılığı testleri"""

    def test_save_coverage_report(self, test_db_memory):
        """Kapsama raporunu kaydet"""
        cur = test_db_memory.cursor()

        # Tablo oluştur
        cur.execute("""
            CREATE TABLE IF NOT EXISTS data_coverage_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER,
                total_courses INTEGER,
                coverage_percentage REAL,
                generated_at TEXT
            )
        """)

        # Rapor kaydet
        report = {
            "total_courses": 10,
            "coverage_percentage": 75.5,
        }

        cur.execute(
            """
            INSERT INTO data_coverage_reports
            (year, total_courses, coverage_percentage, generated_at)
            VALUES (?, ?, ?, ?)
            """,
            (2024, report["total_courses"], report["coverage_percentage"], _now())
        )
        test_db_memory.commit()

        report_id = cur.lastrowid

        # Kontrol
        cur.execute("SELECT * FROM data_coverage_reports WHERE id = ?", (report_id,))
        row = cur.fetchone()
        assert row[2] == 10  # total_courses
        assert row[3] == 75.5  # coverage_percentage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import json
import os
import sqlite3
import tempfile

from app.api import routes
from app.db.schema_compat import ensure_reporting_schema
from app.services.criteria_import_service import import_criteria_excel
from app.services.import_audit_service import (
    calculate_file_hash,
    create_import_batch,
    get_import_batch,
    record_import_issue,
)
from app.services.import_diff_service import recalculate_import_diff
from app.services.import_lineage_service import (
    apply_manual_override,
    list_value_sources,
    record_value_source,
)
from app.services.import_quality_service import (
    evaluate_import_quality,
)
from app.services.import_rollback_service import get_rollback_plan, rollback_import
from app.tests.test_criteria_import_service import _build_db as _criteria_import_db
from app.tests.test_criteria_import_service import _write_criteria_excel


def _db() -> tuple[str, sqlite3.Connection]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT, fakulte_id INTEGER, bolum_id INTEGER);
        CREATE TABLE havuz (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id TEXT, fakulte_id INTEGER, yil INTEGER, donem TEXT);
        CREATE TABLE skor (skor_id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER, akademik_yil INTEGER, donem TEXT);
        """
    )
    conn.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    conn.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    conn.executemany(
        "INSERT INTO ders VALUES (?, ?, ?, 1, 10)",
        [(101, "BLM101", "Algoritmalar"), (102, "BLM102", "Veri Yapilari")],
    )
    ensure_reporting_schema(conn)
    conn.commit()
    return path, conn


def _insert_criteria_row(conn, batch_id, row_no, course_id, code, value):
    payload = {
        "row_no": row_no,
        "ders_kodu": code,
        "ders_adi": code,
        "toplam_ogrenci": value,
        "matched_ders_id": course_id,
    }
    conn.execute(
        """
        INSERT INTO criteria_import_rows (
            import_batch_id, import_id, row_no, ders_kodu, ders_adi, toplam_ogrenci,
            gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci,
            matched_ders_id, row_status, normalized_row_json, row_hash
        )
        VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'matched', ?, ?)
        """,
        (
            batch_id,
            row_no,
            code,
            code,
            value,
            value,
            float(value),
            40,
            30,
            course_id,
            json.dumps(payload, sort_keys=True),
            calculate_file_hash(json.dumps(payload, sort_keys=True).encode("utf-8")),
        ),
    )


def test_file_hash_same_content_same_hash():
    assert calculate_file_hash(b"abc") == calculate_file_hash(b"abc")
    assert calculate_file_hash(b"abc") != calculate_file_hash(b"abcd")


def test_duplicate_import_same_scope_detected():
    _path, conn = _db()
    try:
        first = create_import_batch(conn, "criteria", file_bytes=b"same", faculty_id=1, year=2026)
        second = create_import_batch(conn, "criteria", file_bytes=b"same", faculty_id=1, year=2026)
        assert first["duplicate"] is False
        assert second["duplicate"] is True
        assert second["duplicate_of_import_batch_id"] == first["id"]
    finally:
        conn.close()


def test_import_quality_high_and_low():
    _path, conn = _db()
    try:
        high = create_import_batch(conn, "criteria", row_count=2, faculty_id=1, year=2026)
        _insert_criteria_row(conn, high["id"], 2, 101, "BLM101", 90)
        _insert_criteria_row(conn, high["id"], 3, 102, "BLM102", 85)
        quality = evaluate_import_quality(conn, high["id"])
        assert quality.quality_level == "high"
        assert quality.quality_score >= 0.80

        low = create_import_batch(conn, "criteria", row_count=2, faculty_id=1, year=2026)
        record_import_issue(
            conn,
            import_batch_id=low["id"],
            row_number=1,
            severity="critical",
            issue_type="missing_required_column",
            message="Gerekli kolon bulunamadi: toplam_ogrenci",
            suggestion="Sablondaki zorunlu kolonlari ekleyin.",
        )
        low_quality = evaluate_import_quality(conn, low["id"])
        assert low_quality.quality_level == "low"
    finally:
        conn.close()


def test_row_issue_classification_has_user_friendly_suggestion():
    _path, conn = _db()
    try:
        batch = create_import_batch(conn, "criteria", faculty_id=1, year=2026)
        issue = record_import_issue(
            conn,
            batch["id"],
            row_number=12,
            message="ValueError: could not convert string to float",
            field_name="ortalama_not",
        )
        assert issue["issue_type"] == "invalid_numeric_value"
        assert issue["suggestion"]
    finally:
        conn.close()


def test_import_diff_added_removed_changed_unchanged():
    _path, conn = _db()
    try:
        previous = create_import_batch(conn, "criteria", faculty_id=1, year=2026, status="active")
        current = create_import_batch(conn, "criteria", faculty_id=1, year=2026, status="validated")
        _insert_criteria_row(conn, previous["id"], 2, 101, "BLM101", 70)
        _insert_criteria_row(conn, previous["id"], 3, 102, "BLM102", 80)
        _insert_criteria_row(conn, current["id"], 2, 101, "BLM101", 75)
        _insert_criteria_row(conn, current["id"], 4, 103, "BLM103", 90)
        diff = recalculate_import_diff(conn, current["id"], compared_to_import_batch_id=previous["id"])
        assert diff["added_count"] == 1
        assert diff["removed_count"] == 1
        assert diff["changed_count"] == 1
        assert any(item.get("field_name") == "toplam_ogrenci" for item in diff["items"])
    finally:
        conn.close()


def test_rollback_reactivates_previous_and_logs():
    _path, conn = _db()
    try:
        previous = create_import_batch(conn, "criteria", faculty_id=1, year=2026, status="active")
        current = create_import_batch(conn, "criteria", faculty_id=1, year=2026, status="active")
        conn.execute(
            "UPDATE import_batches SET previous_import_batch_id = ? WHERE id = ?",
            (previous["id"], current["id"]),
        )
        record_value_source(conn, 101, 2026, "basari_ortalamasi", 85, "criteria_import", source_import_batch_id=current["id"])
        plan = get_rollback_plan(conn, current["id"])
        assert plan["can_rollback"] is True
        result = rollback_import(conn, current["id"], reason="Yanlis dosya")
        assert result["ok"] is True
        assert get_import_batch(conn, current["id"])["status"] == "rolled_back"
        assert get_import_batch(conn, previous["id"])["status"] == "active"
        assert conn.execute("SELECT COUNT(*) FROM import_rollback_logs").fetchone()[0] >= 1
    finally:
        conn.close()


def test_value_source_manual_override_deactivates_previous():
    _path, conn = _db()
    try:
        source_id = record_value_source(conn, 101, 2026, "basari_ortalamasi", 70, "criteria_import")
        result = apply_manual_override(conn, 101, 2026, "basari_ortalamasi", 88, "Kurul karari", user="tester")
        assert result["previous_source_id"] == source_id
        sources = list_value_sources(conn, course_id=101, year=2026, field_name="basari_ortalamasi")
        assert len(sources) == 1
        assert sources[0]["source_type"] == "override"
        assert float(sources[0]["value_numeric"]) == 88.0
    finally:
        conn.close()


def test_import_api_smoke(monkeypatch):
    path, conn = _db()
    try:
        batch = create_import_batch(conn, "criteria", row_count=1, faculty_id=1, year=2026)
        _insert_criteria_row(conn, batch["id"], 2, 101, "BLM101", 90)
        evaluate_import_quality(conn, batch["id"])
        recalculate_import_diff(conn, batch["id"])
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    history = routes.import_history()
    assert history["data"]
    quality_response = routes.import_quality(batch["id"])
    assert quality_response["quality_level"] == "high"
    diff_response = routes.import_diff(batch["id"])
    assert diff_response["import_batch_id"] == batch["id"]


def test_real_criteria_import_creates_audit_batch():
    db_path = _criteria_import_db()
    excel_path = _write_criteria_excel(
        [
            {
                "ders_kodu": "C101",
                "ders_adi": "Algoritmalar",
                "toplam_ogrenci": 40,
                "gecen_ogrenci": 35,
                "basari_ortalamasi": 82,
                "kontenjan": 50,
                "kayitli_ogrenci": 45,
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
            }
        ],
        meta_department="Bilgisayar",
    )
    try:
        result = import_criteria_excel(db_path, excel_path, faculty_id=1, department_id=10, year=2024, term="Guz")
        assert result["ok"] is True
        assert result["import_batch_id"]
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT status, file_hash_sha256, quality_level FROM import_batches WHERE id = ?", (result["import_batch_id"],))
        row = cur.fetchone()
        conn.close()
        assert row[0] == "active"
        assert row[1]
        assert row[2] in {"high", "medium"}
    finally:
        for path in (db_path, excel_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def test_data_management_page_importable():
    from app.ui.tabs.data_management_page import DataManagementPage

    assert DataManagementPage is not None

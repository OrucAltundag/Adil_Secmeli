import os
import sqlite3

from app.db.schema_compat import ensure_reporting_schema
from app.services.data_management_center_service import (
    execute_import_request,
    get_dashboard_context,
    get_import_bundle,
    write_import_template,
)
from app.services.import_audit_service import create_import_batch


def _db(tmp_path):
    db_path = tmp_path / "data_management_center.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT, fakulte_id INTEGER, bolum_id INTEGER);
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, basari_orani REAL, ortalama_not REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, doluluk_orani REAL, kontenjan INTEGER
        );
        CREATE TABLE anket_sonuclari (sonuc_id INTEGER PRIMARY KEY, ders_id INTEGER, oy_sayisi INTEGER);
        INSERT INTO fakulte VALUES (1, 'Muhendislik');
        INSERT INTO bolum VALUES (10, 1, 'Bilgisayar');
        INSERT INTO ders VALUES (101, 'BLM101', 'Algoritmalar', 1, 10);
        INSERT INTO ders VALUES (102, 'BLM102', 'Veri Yapilari', 1, 10);
        """
    )
    ensure_reporting_schema(conn)
    conn.execute(
        """
        INSERT INTO ders_kriterleri
            (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci)
        VALUES (101, 2026, 'Guz', 40, 35, 82.0, 45, 40)
        """
    )
    conn.execute("INSERT INTO performans (ders_id, akademik_yil, basari_orani, ortalama_not) VALUES (101, 2026, 0.87, 82.0)")
    conn.execute("INSERT INTO populerlik (ders_id, akademik_yil, doluluk_orani, kontenjan) VALUES (101, 2026, 0.88, 45)")
    conn.execute("INSERT INTO anket_sonuclari (sonuc_id, ders_id, oy_sayisi) VALUES (1, 101, 32)")
    batch = create_import_batch(conn, "criteria", original_filename="kriter.xlsx", row_count=1, faculty_id=1, year=2026)
    conn.commit()
    conn.close()
    return str(db_path), int(batch["id"])


def test_dashboard_context_summarizes_missing_data(tmp_path):
    db_path, _batch_id = _db(tmp_path)

    context = get_dashboard_context(db_path, year=2026, faculty_id=1)

    assert context["coverage"]["total_courses"] == 2
    assert context["coverage"]["courses_with_criteria"] == 1
    assert context["missing"]["criteria"] == 1
    assert context["missing"]["survey"] == 1
    assert context["latest_imports"][0]["original_filename"] == "kriter.xlsx"


def test_import_bundle_returns_batch_details(tmp_path):
    db_path, batch_id = _db(tmp_path)

    bundle = get_import_bundle(db_path, batch_id)

    assert bundle["batch"]["id"] == batch_id
    assert bundle["quality"]["import_batch_id"] == batch_id
    assert "rollback" in bundle


def test_execute_import_request_validates_required_scope(tmp_path):
    db_path, _batch_id = _db(tmp_path)
    excel_path = tmp_path / "empty.xlsx"
    excel_path.write_bytes(b"not parsed because faculty is missing")

    result = execute_import_request(
        db_path=db_path,
        import_type="criteria",
        excel_path=str(excel_path),
        year=2026,
        faculty_id=None,
    )

    assert result["ok"] is False
    assert "Fakülte" in result["errors"][0]
    assert os.path.exists(excel_path)


def test_write_import_template_creates_excel_file(tmp_path):
    db_path, _batch_id = _db(tmp_path)
    target = tmp_path / "survey_template.xlsx"

    result = write_import_template(
        db_path=db_path,
        import_type="survey",
        target_path=str(target),
        year=2026,
        faculty_id=None,
    )

    assert result["ok"] is True
    assert target.exists()

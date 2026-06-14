# -*- coding: utf-8 -*-
"""Backend helpers for the desktop Data Management Center."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.db.session import open_sqlite_connection
from app.services.criteria_import_service import import_criteria_excel, write_criteria_template_excel
from app.services.curriculum_import_service import import_curriculum_excel
from app.services.data_quality_integration_service import (
    assess_data_readiness_cursor,
    generate_coverage_report_cursor,
)
from app.services.import_audit_service import (
    get_import_batch,
    list_import_batches,
    list_import_issues,
    list_import_rows,
)
from app.services.import_diff_service import get_import_diff, recalculate_import_diff
from app.services.import_impact_service import get_import_impact, recalculate_import_impact
from app.services.import_quality_service import summarize_quality
from app.services.import_rollback_service import get_rollback_plan
from app.services.survey_import_service import import_survey_excel, write_survey_template_excel


@dataclass(frozen=True)
class ImportTypeSpec:
    key: str
    label: str
    description: str
    required_scope: str
    expected_columns: tuple[str, ...]


IMPORT_TYPE_SPECS: dict[str, ImportTypeSpec] = {
    "criteria": ImportTypeSpec(
        key="criteria",
        label="Kriter / Performans / Populerlik",
        description="Ders bazlı başarı, kontenjan ve doluluk sinyallerini yükler.",
        required_scope="Fakülte, yıl ve dönem zorunlu; bölüm opsiyonel.",
        expected_columns=(
            "ders_kodu veya ders_adi",
            "toplam_ogrenci",
            "gecen_ogrenci",
            "basari_ortalamasi",
            "kontenjan",
            "kayitli_ogrenci",
        ),
    ),
    "survey": ImportTypeSpec(
        key="survey",
        label="Anket / Tercih",
        description="Öğrenci tercih sayılarını ve anket sinyalini yükler.",
        required_scope="Fakülte ve yıl zorunlu.",
        expected_columns=("ders_kodu veya ders_adi", "tercih_sayisi veya oy_sayisi"),
    ),
    "curriculum": ImportTypeSpec(
        key="curriculum",
        label="Mufredat",
        description="Yıl, fakülte, bölüm, dönem ve ders-müfredat ilişkisini yükler.",
        required_scope="Hedef yıl zorunlu; fakülte/bölüm bilgisi dosyadan okunur.",
        expected_columns=("fakulte", "bolum", "yil", "donem", "ders_kodu veya ders_adi"),
    ),
}


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def connect_data_management(db_path: str) -> sqlite3.Connection:
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError("Veritabani yolu bulunamadi.")
    return open_sqlite_connection(os.path.abspath(db_path), row_factory=True)


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return bool(cur.fetchone())


def _fetch_years(cur: sqlite3.Cursor) -> list[int]:
    years: set[int] = set()
    sources = (
        ("performans", "akademik_yil"),
        ("populerlik", "akademik_yil"),
        ("ders_kriterleri", "yil"),
        ("import_batches", "year"),
        ("mufredat", "yil"),
    )
    for table, column in sources:
        if not _table_exists(cur, table):
            continue
        try:
            cur.execute(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL")
            for row in cur.fetchall():
                try:
                    years.add(int(row[0]))
                except (TypeError, ValueError):
                    continue
        except sqlite3.DatabaseError:
            continue
    return sorted(years, reverse=True)


def _fetch_faculties(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    if not _table_exists(cur, "fakulte"):
        return []
    cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
    return [{"id": int(row[0]), "name": str(row[1])} for row in cur.fetchall()]


def _fetch_departments(cur: sqlite3.Cursor, faculty_id: int | None = None) -> list[dict[str, Any]]:
    if not _table_exists(cur, "bolum"):
        return []
    if faculty_id is None:
        cur.execute("SELECT bolum_id, fakulte_id, ad FROM bolum ORDER BY ad")
    else:
        cur.execute("SELECT bolum_id, fakulte_id, ad FROM bolum WHERE fakulte_id=? ORDER BY ad", (int(faculty_id),))
    return [
        {"id": int(row[0]), "faculty_id": int(row[1]) if row[1] is not None else None, "name": str(row[2])}
        for row in cur.fetchall()
    ]


def _count_trend_ready(cur: sqlite3.Cursor, faculty_id: int | None, department_id: int | None) -> int:
    fac = "AND d.fakulte_id = ?" if faculty_id is not None else ""
    dept = "AND d.bolum_id = ?" if department_id is not None else ""
    params: list[Any] = []
    if faculty_id is not None:
        params.append(int(faculty_id))
    if department_id is not None:
        params.append(int(department_id))
    try:
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT p.ders_id
                FROM performans p
                JOIN ders d ON d.ders_id = p.ders_id
                WHERE 1=1 {fac} {dept}
                GROUP BY p.ders_id
                HAVING COUNT(DISTINCT p.akademik_yil) >= 2
            ) t
            """,
            tuple(params),
        )
        return int(cur.fetchone()[0] or 0)
    except sqlite3.DatabaseError:
        return 0


def _latest_import_counts(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.cursor()
    if not _table_exists(cur, "import_batches"):
        return {}
    cur.execute("SELECT status, COUNT(*) FROM import_batches GROUP BY status")
    return {str(row[0] or "unknown"): int(row[1] or 0) for row in cur.fetchall()}


def _missing_counts(coverage: dict[str, Any], trend_ready: int) -> dict[str, int]:
    total = int(coverage.get("total_courses") or 0)
    return {
        "criteria": max(0, total - int(coverage.get("courses_with_criteria") or 0)),
        "performance": max(0, total - int(coverage.get("courses_with_performance") or 0)),
        "popularity": max(0, total - int(coverage.get("courses_with_popularity") or 0)),
        "survey": max(0, total - int(coverage.get("courses_with_survey") or 0)),
        "trend": max(0, total - int(trend_ready or 0)),
    }


def _next_actions(coverage: dict[str, Any], readiness: dict[str, Any], missing: dict[str, int]) -> list[str]:
    total = int(coverage.get("total_courses") or 0)
    if total == 0:
        return ["Önce müfredat veya ders master verisini yükleyin."]

    actions: list[str] = []
    if missing.get("criteria", 0) > 0:
        actions.append(f"{missing['criteria']} ders için kriter/performans dosyası yükleyin.")
    if missing.get("survey", 0) > 0:
        actions.append(f"{missing['survey']} ders için anket/tercih dosyası yükleyin.")
    if float(readiness.get("validation_score") or 0) < 100:
        actions.append("Doğrulama sorunlarındaki kritik kayıtları düzeltin.")
    if not actions and float(coverage.get("coverage_percentage") or 0) >= 85:
        actions.append("Veri kapsamı karar çalıştırmak için yeterli görünüyor.")
    elif not actions:
        actions.append("Kapsamı yükseltmek için eksik veri matrisini kontrol edin.")
    return actions[:4]


def get_import_type_specs() -> list[dict[str, Any]]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "description": item.description,
            "required_scope": item.required_scope,
            "expected_columns": list(item.expected_columns),
        }
        for item in IMPORT_TYPE_SPECS.values()
    ]


def get_dashboard_context(
    db_path: str,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    with connect_data_management(db_path) as conn:
        cur = conn.cursor()
        years = _fetch_years(cur)
        selected_year = int(year if year is not None else (years[0] if years else 2022))
        faculties = _fetch_faculties(cur)
        departments = _fetch_departments(cur, faculty_id=faculty_id)
        coverage = generate_coverage_report_cursor(cur, selected_year, faculty_id, department_id)
        readiness = assess_data_readiness_cursor(cur, selected_year, faculty_id, department_id)
        trend_ready = _count_trend_ready(cur, faculty_id, department_id)
        missing = _missing_counts(coverage, trend_ready)
        latest = list_import_batches(conn, limit=8)
        status_counts = _latest_import_counts(conn)
        return {
            "years": years or [selected_year],
            "selected_year": selected_year,
            "faculties": faculties,
            "departments": departments,
            "coverage": coverage,
            "readiness": readiness,
            "missing": missing,
            "trend_ready": trend_ready,
            "latest_imports": latest,
            "import_status_counts": status_counts,
            "next_actions": _next_actions(coverage, readiness, missing),
            "import_types": get_import_type_specs(),
        }


def _maybe_run_auto_pipeline(
    db_path: str,
    year: int,
    faculty_id: int,
    result: dict[str, Any],
) -> None:
    """Otomatik mod açıksa kriter importu sonrası üretim hattını best-effort tetikler.

    Sonucu ana import sonucuna `auto_pipeline` anahtarıyla iliştirir; herhangi bir
    hata import akışını bozmaz (sessizce yutulur).
    """
    try:
        from app.services.auto_pipeline_service import (
            is_auto_pipeline_enabled,
            run_auto_pipeline,
        )

        if not is_auto_pipeline_enabled():
            return
        auto_summary = run_auto_pipeline(
            db_path=db_path,
            source_year=int(year),
            faculty_id=int(faculty_id),
            trigger="criteria_import",
        )
        result["auto_pipeline"] = auto_summary
    except Exception as exc:  # noqa: BLE001
        result["auto_pipeline"] = {"ok": False, "error": str(exc)}


def execute_import_request(
    db_path: str,
    import_type: str,
    excel_path: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    term: str | None = None,
    auto_activate: bool = True,
    uploaded_by: str | None = None,
) -> dict[str, Any]:
    import_type = str(import_type or "").strip().lower()
    if import_type not in IMPORT_TYPE_SPECS:
        return {"ok": False, "message": "Geçersiz import türü.", "errors": ["Geçersiz import türü."]}
    if not excel_path or not os.path.exists(excel_path):
        return {"ok": False, "message": "Excel dosyası bulunamadı.", "errors": ["Excel dosyası bulunamadı."]}

    if import_type == "criteria":
        if faculty_id is None:
            return {"ok": False, "message": "Kriter importu için fakülte seçin.", "errors": ["Fakülte zorunlu."]}
        criteria_result = import_criteria_excel(
            db_path=db_path,
            excel_path=excel_path,
            faculty_id=int(faculty_id),
            department_id=int(department_id) if department_id is not None else None,
            year=int(year),
            term=term or "Guz",
            source_filename=os.path.basename(excel_path),
            auto_activate=auto_activate,
            uploaded_by=uploaded_by,
        )
        # OTOMATIK MOD: kriter importu basariliysa ve otomatik mod aciksa, ilgili
        # fakulte icin sonraki yil mufredatini uretip ders onerisi Excel'ini yaz.
        # Kriter kapisi (cift-donem) generate icinde uygulandigi icin eksik donemde
        # uretim sessizce atlanir; hata olusursa ana import sonucu etkilenmez.
        if criteria_result.get("ok"):
            _maybe_run_auto_pipeline(db_path, year=int(year), faculty_id=int(faculty_id), result=criteria_result)
        return criteria_result

    if import_type == "survey":
        # Fakulte = None ("Tumu") => belgedeki tum fakulteler tek tek import edilir.
        return import_survey_excel(
            db_path=db_path,
            excel_path=excel_path,
            faculty_id=int(faculty_id) if faculty_id is not None else None,
            year=int(year),
            source_filename=os.path.basename(excel_path),
            auto_activate=auto_activate,
            uploaded_by=uploaded_by,
        )

    return import_curriculum_excel(
        db_path=db_path,
        excel_path=excel_path,
        target_year=int(year),
        auto_activate=auto_activate,
        uploaded_by=uploaded_by,
    )


def write_import_template(
    db_path: str,
    import_type: str,
    target_path: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    import_type = str(import_type or "").strip().lower()
    if import_type not in IMPORT_TYPE_SPECS:
        return {"ok": False, "message": "Geçersiz şablon türü.", "errors": ["Geçersiz şablon türü."]}
    if not target_path:
        return {"ok": False, "message": "Şablon dosya yolu seçilmedi.", "errors": ["Dosya yolu zorunlu."]}

    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    try:
        if import_type == "criteria":
            try:
                written = write_criteria_template_excel(
                    target_path=target_path,
                    db_path=db_path if faculty_id is not None else None,
                    faculty_id=int(faculty_id) if faculty_id is not None else None,
                    department_id=int(department_id) if department_id is not None else None,
                    year=int(year),
                    term=term or "Guz",
                )
            except Exception:
                written = write_criteria_template_excel(target_path=target_path, year=int(year), term=term or "Guz")
            return {"ok": True, "message": "Kriter şablonu oluşturuldu.", "path": written}

        if import_type == "survey":
            # faculty_id None ('Tumu') => tum fakulteler tek dosyada; db_path her durumda iletilir.
            try:
                written = write_survey_template_excel(
                    target_path=target_path,
                    db_path=db_path,
                    faculty_id=int(faculty_id) if faculty_id is not None else None,
                    year=int(year),
                )
            except Exception:
                written = write_survey_template_excel(target_path=target_path, year=int(year))
            scope_msg = "Anket şablonu oluşturuldu." if faculty_id is not None else "Anket şablonu (tüm fakülteler) oluşturuldu."
            return {"ok": True, "message": scope_msg, "path": written}

        rows = [
            {
                "Fakulte": "Örnek Fakültesi",
                "Bolum": "Örnek Bölüm",
                "Yil": int(year),
                "Donem": term or "Guz",
                "Ders Kodu": "SEC101",
                "Ders Adi": "Örnek Seçmeli Ders",
            }
        ]
        with pd.ExcelWriter(target_path, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Mufredat", index=False)
        return {"ok": True, "message": "Müfredat şablonu oluşturuldu.", "path": target_path}
    except Exception as exc:
        return {"ok": False, "message": f"Şablon oluşturulamadı: {exc}", "errors": [str(exc)]}


def get_import_bundle(db_path: str, import_batch_id: int) -> dict[str, Any]:
    with connect_data_management(db_path) as conn:
        batch = get_import_batch(conn, int(import_batch_id)) or {}
        quality = summarize_quality(conn, int(import_batch_id)) if batch else {}
        rows = list_import_rows(conn, int(import_batch_id), limit=500) if batch else []
        issues = list_import_issues(conn, int(import_batch_id), limit=500) if batch else []
        diff = get_import_diff(conn, int(import_batch_id)) if batch else None
        rollback = get_rollback_plan(conn, int(import_batch_id)) if batch else {}
        impact = get_import_impact(conn, int(import_batch_id)) if batch else None
        if batch.get("validation_summary_json"):
            batch["validation_summary"] = _json_loads(batch.get("validation_summary_json"), {})
        return {
            "batch": batch,
            "quality": quality,
            "rows": rows,
            "issues": issues,
            "diff": diff,
            "rollback": rollback,
            "impact": impact,
        }


def recalculate_import_artifact(db_path: str, import_batch_id: int, artifact: str) -> dict[str, Any]:
    with connect_data_management(db_path) as conn:
        if artifact == "diff":
            result = recalculate_import_diff(conn, int(import_batch_id))
        elif artifact == "impact":
            result = recalculate_import_impact(conn, int(import_batch_id))
        else:
            raise ValueError("Geçersiz hesaplama türü.")
        conn.commit()
        return result

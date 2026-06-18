# -*- coding: utf-8 -*-
"""Sistem sıfırlama servisi — müfredatla en baştan başlamak için.

Kullanıcı isteği: müfredat / yıl / girilen kriter / "kriter girildi" işaretleri ve
sistemin diğer üretilmiş/işlenmiş kayıtları temizlensin; sisteme müfredat yükleyerek
sıfırdan başlanabilsin.

**SİLİNEN (operasyonel/üretilmiş/governance/import):** müfredat, kriter, performans,
popülerlik, havuz, skor, karar çalışmaları, kriter tamamlama durumları, dönem planları,
üretim logları ve import geçmişi.

**KORUNAN (master + ham kaynak):** fakülte / bölüm / ders kataloğu ile öğrenci /
kayıt / anket ham verisi. AHP ve karar politikaları silinir; uygulama varsayılan
profilleri yeniden oluşturur.

İşlem TEK transaction içinde yapılır; caller commit eder. Yalnız VAR OLAN tablolar
silinir (şema kayması güvenli).
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.havuz_seed_service import seed_havuz_from_electives

# Sıfırlamada içeriği TAMAMEN silinecek operasyonel/üretilmiş tablolar.
WIPE_TABLES: tuple[str, ...] = (
    # Müfredat
    "mufredat_ders",
    "mufredat",
    # Kriter / performans / popülerlik (üretilmiş kriter verisi)
    "ders_kriterleri",
    "performans",
    "populerlik",
    # Havuz / skor (hesaplanmış)
    "havuz",
    "skor",
    # Karar çalışmaları ve türevleri
    "decision_run_import_sources",
    "course_decision_explanations",
    "course_score_breakdowns",
    "course_trend_analysis",
    "course_data_confidence",
    "decision_sensitivity_results",
    "course_state_transitions",
    "course_state_approvals",
    "course_state_overrides",
    "decision_staleness_flags",
    "low_confidence_decision_flags",
    "post_decision_outcomes",
    "course_decisions",
    "candidate_course_recommendations",
    "curriculum_decision_reviews",
    "decision_run_override_requests",
    "decision_runs",
    "data_coverage_reports",
    "decision_fairness_reports",
    "fairness_metric_items",
    # Kriter tamamlama durumları / "kriter girildi" işaretleri
    "criteria_completion_matrix",
    "criteria_completion_history",
    "criteria_department_status",
    "criteria_faculty_status",
    "criteria_missing_data_risks",
    "criteria_validation_issues",
    "criteria_value_sources",
    "data_validation_issues",
    "missing_data_items",
    "data_collection_priorities",
    "data_readiness_assessments",
    # AHP duyarlılık çalışma çıktıları (profil/politika değil)
    "ahp_course_sensitivity_items",
    "ahp_sensitivity_results",
    "ahp_profile_approval_logs",
    "ahp_profile_policies",
    "ahp_weight_profiles",
    "decision_policies",
    "criteria_completion_policies",
    "pool_state_policies",
    "semester_planning_policies",
    # Dönem planları (üretilmiş)
    "semester_plan_constraint_violations",
    "semester_plan_scenarios",
    "semester_plan_course_assignments",
    "semester_plan_runs",
    # Üretim logları / audit
    "curriculum_generation_log",
    "curriculum_generation_audit",
    "cross_department_curriculum_usage",
    # Import geçmişi / staging
    "import_diff_items",
    "import_diffs",
    "import_impact_reports",
    "import_quality_checks",
    "import_rollback_logs",
    "import_row_issues",
    "import_staging_rows",
    "import_staging_payloads",
    "criteria_import_rows",
    "criteria_import",
    "survey_import_rows",
    "survey_import",
    "secure_import_job_rows",
    "secure_import_jobs",
    "import_batches_archive",
    "import_batches",
)

# Bilgi amaçlı: korunan ana tablolar (silinmez).
KEEP_TABLES: tuple[str, ...] = (
    "fakulte", "bolum", "ders", "ders_iliski", "okul",
    "ogrenci", "ogrenci_not", "ogrenci_engel", "kayit",
    "anket_form", "anket_cevap", "anket_sonuclari",
)


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
    return bool(cur.fetchone())


def _count(cur: sqlite3.Cursor, table: str) -> int:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return int(cur.fetchone()[0] or 0)
    except sqlite3.OperationalError:
        return 0


def _pool_scopes_to_restore(cur: sqlite3.Cursor) -> list[tuple[int, int]]:
    """Temizlikten sonra yeniden kurulacak ``(yıl, fakülte)`` kapsamları."""
    scopes: set[tuple[int, int]] = set()
    queries = (
        ("havuz", "SELECT DISTINCT yil, fakulte_id FROM havuz"),
        ("mufredat", "SELECT DISTINCT akademik_yil, fakulte_id FROM mufredat"),
    )
    for table, query in queries:
        if not _table_exists(cur, table):
            continue
        try:
            cur.execute(query)
        except sqlite3.OperationalError:
            continue
        for year, faculty_id in cur.fetchall():
            if year is None or faculty_id is None:
                continue
            scopes.add((int(year), int(faculty_id)))
    return sorted(scopes)


def preview_reset(conn: sqlite3.Connection) -> dict[str, Any]:
    """Sıfırlamada silinecek tablo/satır sayıları (onay diyaloğu için)."""
    cur = conn.cursor()
    per_table: dict[str, int] = {}
    total = 0
    for table in WIPE_TABLES:
        if not _table_exists(cur, table):
            continue
        n = _count(cur, table)
        if n:
            per_table[table] = n
            total += n
    return {"per_table": per_table, "total_rows": total, "table_count": len(per_table)}


def reset_system(conn: sqlite3.Connection, user: str | None = None) -> dict[str, Any]:
    """Operasyonel/üretilmiş verileri siler. Caller commit eder.

    Ana katalog (fakülte/bölüm/ders) ve ham öğrenci/anket verisi korunur.
    """
    cur = conn.cursor()
    # FK kısıtları silmeyi engellemesin (çoğu bağlantıda zaten kapalı).
    try:
        cur.execute("PRAGMA foreign_keys = OFF")
    except sqlite3.Error:
        pass

    # Müfredat ve havuz silinince yıl filtreleri de kaybolmasın. Temizlikten
    # sonra aynı yıl/fakülte kapsamlarında seçmeli katalog havuzu yeniden kurulur.
    pool_scopes = _pool_scopes_to_restore(cur)

    deleted: dict[str, int] = {}
    total = 0
    for table in WIPE_TABLES:
        if not _table_exists(cur, table):
            continue
        before = _count(cur, table)
        if before == 0:
            continue
        cur.execute(f'DELETE FROM "{table}"')
        deleted[table] = before
        total += before
        # AUTOINCREMENT sayaçlarını da sıfırla (varsa).
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        except sqlite3.OperationalError:
            pass

    restored_pool_rows = 0
    restored_pool_scopes = 0
    if _table_exists(cur, "havuz") and _table_exists(cur, "ders"):
        for year, faculty_id in pool_scopes:
            result = seed_havuz_from_electives(
                conn,
                year,
                faculty_id=faculty_id,
                default_score=None,
            )
            restored_pool_rows += int(result.get("added", 0))
            restored_pool_scopes += 1

    return {
        "ok": True,
        "deleted": deleted,
        "total_rows": total,
        "table_count": len(deleted),
        "restored_pool_rows": restored_pool_rows,
        "restored_pool_scopes": restored_pool_scopes,
        "message": (
            f"Sıfırlama tamamlandı. {len(deleted)} tablodan toplam {total} kayıt silindi. "
            "Ana katalog (fakülte/bölüm/ders) ile öğrenci/anket ham verisi korundu. "
            f"{restored_pool_scopes} yıl/fakülte kapsamında {restored_pool_rows} seçmeli ders "
            "havuza yeniden eklendi. "
            "AHP ve karar politikaları varsayılan olarak yeniden oluşturulacaktır. "
            "Artık sisteme müfredat yükleyerek baştan başlayabilirsiniz."
        ),
    }

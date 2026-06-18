# -*- coding: utf-8 -*-
"""Rapor & Yükleme sayfası için şablon üretimi ve rapor dışa aktarımı (§12–§16).

İki sorumluluk:
- **TemplateGenerationService** (``write_template``): sistemin GERÇEKTEN yeniden
  içe aktarabileceği (§14) şablon Excel'leri üretir. Tek akademik yıl + ``donem``
  kolonu ile güz/bahar birlikte (§15). Kriter/Anket/Müfredat için mevcut, test
  edilmiş ``write_import_template`` akışına delege eder; diğerleri (havuz/öğrenci/
  ders/yıllık) burada doğrudan üretilir.
- **ReportExportService** (``export_report``): seçili kapsam için raporu
  indirilebilir Excel'e yazar (güz+bahar ayrı sayfalar, aynı dosya — §15).

UI doğrudan DB'ye bağlanmaz; bu servis ``db_path`` ile çalışır ve mevcut
repository/servis katmanını kullanır.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

from app.services.data_management_center_service import (
    export_student_criteria_dataset,
    write_import_template,
)

# template_type -> (sheet_name, kolonlar, örnek satır(lar))
# §14: kolon adları import doğrulamasıyla uyumlu; §15: 'donem' kolonu güz/bahar.
_TEMPLATES: dict[str, dict[str, Any]] = {
    "havuz": {
        "sheet": "Havuz",
        "rows": [
            {
                "fakulte": "Örnek Fakültesi", "bolum": "Örnek Bölüm", "akademik_yil": 2023,
                "donem": "Guz", "ders_kodu": "SEC101", "ders_adi": "Örnek Seçmeli",
                "havuz_durumu": "Havuzda", "oneri_durumu": "Yeni öneri",
            },
            {
                "fakulte": "Örnek Fakültesi", "bolum": "Örnek Bölüm", "akademik_yil": 2023,
                "donem": "Bahar", "ders_kodu": "SEC102", "ders_adi": "Örnek Seçmeli 2",
                "havuz_durumu": "Müfredatta", "oneri_durumu": "Korunuyor",
            },
        ],
    },
    "ogrenci": {
        "sheet": "Ders Analizi",
        "columns": [
            "ders_kodu", "donem", "kayit_sayisi", "gecme_orani_%",
            "ort_agirlikli", "ort_katilim_yuzde",
        ],
        "rows": [],
    },
    "ders": {
        "sheet": "Ders",
        "rows": [
            {
                "ders_kodu": "SEC101", "ders_adi": "Örnek Seçmeli", "fakulte": "Örnek Fakültesi",
                "bolum": "Örnek Bölüm", "kredi": 3, "akts": 5,
            },
        ],
    },
    "yillik_mufredat": {
        "sheet": "Mufredat",
        "columns": ["Fakulte", "Bolum", "Yil", "Donem", "Ders Kodu", "Ders Adi"],
        "rows": [],
    },
}

# UI'da gösterilecek dostça etiketler
TEMPLATE_LABELS: dict[str, str] = {
    "yillik_mufredat": "Güz+Bahar Yıllık Müfredat Şablonu",
    "criteria": "Kriter Şablonu",
    "survey": "Anket / Tercih Şablonu",
    "ogrenci": "Öğrenci Veri Seti Şablonu",
}


def list_template_types() -> list[tuple[str, str]]:
    """(template_type, label) listesi — UI buton üretimi için."""
    return list(TEMPLATE_LABELS.items())


def write_template(
    template_type: str,
    target_path: str,
    *,
    db_path: str | None = None,
    year: int = 2023,
    faculty_id: int | None = None,
    department_id: int | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    """§13/§14: Sistemin yeniden içe aktarabileceği şablon Excel'i üretir."""
    template_type = str(template_type or "").strip().lower()
    if not target_path:
        return {"ok": False, "message": "Hedef dosya yolu seçilmedi."}

    # Kriter/Anket/Müfredat: mevcut import şablon üreticisine delege (re-importable).
    if template_type in ("criteria", "survey", "curriculum"):
        return write_import_template(
            db_path=db_path or "",
            import_type=template_type,
            target_path=target_path,
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
            term=term,
        )

    spec = _TEMPLATES.get(template_type)
    if not spec:
        return {"ok": False, "message": f"Bilinmeyen şablon türü: {template_type}"}

    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        rows = list(spec["rows"])
        # Örnek satırlardaki yıl alanını seçili yıla uyarla.
        for r in rows:
            for ycol in ("akademik_yil", "yil"):
                if ycol in r:
                    r[ycol] = int(year)
        with pd.ExcelWriter(target_path, engine="openpyxl") as writer:
            pd.DataFrame(rows, columns=spec.get("columns")).to_excel(
                writer, sheet_name=spec["sheet"], index=False
            )
            # Açıklama sayfası (§14: zorunlu kolonlar + veri tipi beklentisi)
            note = pd.DataFrame(
                {
                    "Açıklama": [
                        "Bu şablon sistem tarafından yeniden içe aktarılabilir.",
                        "Kolon adlarını DEĞİŞTİRMEYİN.",
                        "Güz/Bahar ayrımı 'donem' kolonuyla yapılır (tek akademik yıl).",
                        "Verileri başlık satırının altına ekleyin.",
                    ]
                }
            )
            note.to_excel(writer, sheet_name="Aciklama", index=False)
        return {
            "ok": True,
            "message": f"{TEMPLATE_LABELS.get(template_type, template_type)} oluşturuldu (boş veri şablonu).",
            "path": target_path,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Şablon oluşturulamadı: {exc}"}


def write_student_criteria_dataset(excel_path: str, year: int, target_path: str) -> dict[str, Any]:
    """§3 köprüsü: öğrenci veri setinden indirilebilir kriter veri seti üretir."""
    return export_student_criteria_dataset(excel_path=excel_path, year=int(year), target_path=target_path)


# ---------------------------------------------------------------------------
# Rapor dışa aktarımı (§13 Rapor İndirme alanı) — indirilebilir Excel
# ---------------------------------------------------------------------------
REPORT_LABELS: dict[str, str] = {
    "mufredat": "Müfredat Raporu",
    "yillik_mufredat": "Güz+Bahar Yıllık Müfredat Raporu",
    "havuz": "Havuz Raporu",
    "kesinlesme": "Kesinleşme Puanları Raporu",
    "ahp_topsis": "AHP/TOPSIS Sonuç Raporu",
    "trend": "Trend Raporu",
    "donemsel_planlama": "Dönemsel Planlama Raporu",
    "import_hata": "Import Hata Raporu",
}

REPORT_SOURCES: dict[str, tuple[str, str]] = {
    "mufredat": ("Dönem Planlama / Müfredat", "mufredat, mufredat_ders, ders"),
    "yillik_mufredat": ("Dönem Planlama / Müfredat", "mufredat, mufredat_ders, ders"),
    "havuz": ("Karar Süreci / Fakülte Havuzu", "havuz, ders"),
    "kesinlesme": ("Karar Merkezi / Kesinleşme Puanları", "havuz, ders"),
    "ahp_topsis": ("Karar Süreci / AHP ve TOPSIS", "skor, ders"),
    "trend": ("Kriter ve Performans Verileri", "performans, ders"),
    "donemsel_planlama": ("Dönem Planlama", "semester_plan_runs, semester_plan_course_assignments, ders"),
    "import_hata": ("Veri Yönetimi / Import Geçmişi", "import_row_issues"),
}


def list_report_types() -> list[tuple[str, str]]:
    return list(REPORT_LABELS.items())


def _scope_and(*, col_fac: str, col_dep: str, faculty_id: int | None, department_id: int | None) -> tuple[str, list[Any]]:
    if department_id is not None:
        return f" AND {col_dep} = ?", [int(department_id)]
    if faculty_id is not None:
        return f" AND {col_fac} = ?", [int(faculty_id)]
    return "", []


def export_report(
    report_type: str,
    target_path: str,
    *,
    db_path: str,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """§13/§15: Seçili kapsam için raporu indirilebilir Excel'e yazar.

    Güz+bahar birlikte (``donem`` kolonu). Veri yoksa ``ok=False`` ile anlaşılır
    mesaj döner; sistem donmaz. UI doğrudan DB'ye bağlanmaz — bu servis bağlanır.
    """
    import sqlite3

    report_type = str(report_type or "").strip().lower()
    if report_type not in REPORT_LABELS:
        return {"ok": False, "message": f"Bilinmeyen rapor türü: {report_type}"}
    if not target_path:
        return {"ok": False, "message": "Hedef dosya yolu seçilmedi."}
    if not db_path or not os.path.exists(db_path):
        return {"ok": False, "message": "Veritabanı bulunamadı."}

    yr = int(year) if year is not None else None
    conn = sqlite3.connect(db_path)
    try:
        if report_type in ("mufredat", "yillik_mufredat"):
            scope, params = _scope_and(col_fac="m.fakulte_id", col_dep="m.bolum_id",
                                       faculty_id=faculty_id, department_id=department_id)
            sql = (
                "SELECT d.kod AS ders_kodu, d.ad AS ders_adi, m.donem, m.akademik_yil AS yil, "
                "f.ad AS fakulte, b.ad AS bolum, m.durum "
                "FROM mufredat m JOIN mufredat_ders md ON md.mufredat_id=m.mufredat_id "
                "JOIN ders d ON d.ders_id=md.ders_id "
                "LEFT JOIN fakulte f ON f.fakulte_id=m.fakulte_id "
                "LEFT JOIN bolum b ON b.bolum_id=m.bolum_id "
                "WHERE 1=1" + (" AND m.akademik_yil=?" if yr is not None else "") + scope +
                " ORDER BY m.donem, d.kod"
            )
            p = ([yr] if yr is not None else []) + params
        elif report_type == "havuz":
            scope, params = _scope_and(col_fac="h.fakulte_id", col_dep="h.bolum_id",
                                       faculty_id=faculty_id, department_id=department_id)
            sql = (
                "SELECT h.ders_id, COALESCE(d.kod,'') AS ders_kodu, COALESCE(d.ad,h.ders_adi) AS ders_adi, "
                "h.donem, h.yil, h.skor, h.statu, h.final_status "
                "FROM havuz h LEFT JOIN ders d ON d.ders_id=h.ders_id "
                "WHERE 1=1" + (" AND h.yil=?" if yr is not None else "") + scope +
                " ORDER BY h.donem, h.skor DESC"
            )
            p = ([yr] if yr is not None else []) + params
        elif report_type == "kesinlesme":
            scope, params = _scope_and(col_fac="h.fakulte_id", col_dep="h.bolum_id",
                                       faculty_id=faculty_id, department_id=department_id)
            sql = (
                "SELECT COALESCE(d.kod,'') AS ders_kodu, COALESCE(d.ad,h.ders_adi) AS ders_adi, "
                "h.donem, h.yil, h.skor AS kesinlesme_puani "
                "FROM havuz h LEFT JOIN ders d ON d.ders_id=h.ders_id "
                "WHERE h.skor IS NOT NULL" + (" AND h.yil=?" if yr is not None else "") + scope +
                " ORDER BY h.donem, h.skor DESC"
            )
            p = ([yr] if yr is not None else []) + params
        elif report_type == "ahp_topsis":
            scope, params = _scope_and(col_fac="d.fakulte_id", col_dep="d.bolum_id",
                                       faculty_id=faculty_id, department_id=department_id)
            sql = (
                "SELECT COALESCE(d.kod,'') AS ders_kodu, COALESCE(d.ad,'') AS ders_adi, s.donem, "
                "s.akademik_yil AS yil, s.skor_top AS topsis_skor, s.b_norm AS basari, "
                "s.p_norm AS populerlik, s.t_norm AS trend, s.a_norm AS anket, s.ahp_profile_id "
                "FROM skor s LEFT JOIN ders d ON d.ders_id=s.ders_id "
                "WHERE 1=1" + (" AND s.akademik_yil=?" if yr is not None else "") + scope +
                " ORDER BY s.donem, s.skor_top DESC"
            )
            p = ([yr] if yr is not None else []) + params
        elif report_type == "trend":
            scope, params = _scope_and(col_fac="d.fakulte_id", col_dep="d.bolum_id",
                                       faculty_id=faculty_id, department_id=department_id)
            sql = (
                "SELECT COALESCE(d.kod,'') AS ders_kodu, COALESCE(d.ad,'') AS ders_adi, "
                "p.akademik_yil AS yil, p.donem, p.basari_orani, p.ortalama_not "
                "FROM performans p LEFT JOIN ders d ON d.ders_id=p.ders_id "
                "WHERE 1=1" + scope + " ORDER BY ders_kodu, p.akademik_yil, p.donem"
            )
            p = params
        elif report_type == "donemsel_planlama":
            scope, params = _scope_and(col_fac="r.faculty_id", col_dep="r.department_id",
                                       faculty_id=faculty_id, department_id=department_id)
            sql = (
                "SELECT r.id AS run_id, r.year AS yil, r.run_name, r.faculty_id, r.department_id, "
                "a.assigned_semester AS donem, d.kod AS ders_kodu, d.ad AS ders_adi, "
                "a.assignment_type, a.course_score, a.expected_demand, a.expected_capacity, "
                "a.constraint_status, a.explanation, r.plan_score, r.status, r.created_at "
                "FROM semester_plan_runs r "
                "LEFT JOIN semester_plan_course_assignments a ON a.plan_run_id=r.id "
                "LEFT JOIN ders d ON d.ders_id=a.course_id "
                "WHERE 1=1" + (" AND r.year=?" if yr is not None else "") + scope +
                " ORDER BY r.id DESC, a.assigned_semester, d.kod"
            )
            p = ([yr] if yr is not None else []) + params
        else:  # import_hata
            sql = (
                "SELECT import_batch_id, row_number AS satir, issue_type AS sorun_turu, "
                "severity AS siddet, message AS mesaj "
                "FROM import_row_issues ORDER BY import_batch_id DESC, id LIMIT 5000"
            )
            p = []

        try:
            df = pd.read_sql_query(sql, conn, params=p or None)
        except Exception as exc:  # noqa: BLE001 - tablo/kolon yoksa anlaşılır mesaj
            return {"ok": False, "message": f"Rapor verisi okunamadı (tablo/kolon eksik olabilir): {exc}"}
    finally:
        conn.close()

    if df is None or df.empty:
        return {"ok": False, "message": "Seçili kapsam için rapor verisi bulunamadı."}

    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        with pd.ExcelWriter(target_path, engine="openpyxl") as writer:
            if "donem" in df.columns:
                # §15: Güz ve Bahar ayrı sayfalar (aynı dosya).
                wrote_any = False
                for label, key in (("Guz", "g"), ("Bahar", "b")):
                    part = df[df["donem"].astype(str).str.lower().str.startswith(key)]
                    if not part.empty:
                        part.to_excel(writer, sheet_name=label, index=False)
                        wrote_any = True
                if not wrote_any:
                    df.to_excel(writer, sheet_name="Rapor", index=False)
            else:
                df.to_excel(writer, sheet_name="Rapor", index=False)
            page_name, tables = REPORT_SOURCES[report_type]
            pd.DataFrame(
                [
                    {"Alan": "Rapor", "Deger": REPORT_LABELS[report_type]},
                    {"Alan": "Sistem sayfasi", "Deger": page_name},
                    {"Alan": "Canli veri kaynagi", "Deger": tables},
                    {"Alan": "Akademik yil", "Deger": yr if yr is not None else "Tum yillar"},
                    {"Alan": "Fakulte ID", "Deger": faculty_id if faculty_id is not None else "Tumu"},
                    {"Alan": "Bolum ID", "Deger": department_id if department_id is not None else "Tumu"},
                ]
            ).to_excel(writer, sheet_name="Kaynak Bilgisi", index=False)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Rapor dosyaya yazılamadı: {exc}"}

    return {
        "ok": True,
        "message": f"{REPORT_LABELS[report_type]} oluşturuldu ({len(df)} satır).",
        "path": target_path,
        "row_count": int(len(df)),
    }

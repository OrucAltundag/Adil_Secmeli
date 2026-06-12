# -*- coding: utf-8 -*-
"""
Hesaplanan / sentetik verileri TEMIZLE — tam temiz sayfa.

Kullanici istegi:
- Sistemin hesaplama yaparak doldurdugu tablolardaki eski verileri sil.
- Kriter sayfasinda her dersin FARKLI varsayilan degeri gorunmesin; temizlik
  sonrasi her ders SABIT varsayilan (0) gosterir. (Sebep: kriter sayfasi
  ders_kriterleri bossa performans/populerlik'e fallback yapip sentetik
  random degerleri gosteriyordu.)
- Not veri seti / elle giris sonrasi degerler tekrar dolar.

SILINEN (computed/derived + kriter):
- Kriter & turetilmis: ders_kriterleri, performans, populerlik, skor
- Karar ciktilari: decision_runs, course_decisions, score_breakdowns, trend,
  data_confidence, explanations, sensitivity, fairness, staleness, vb.
- Plan ciktilari: semester_plan_runs ve bagli tablolar
- Kalite snapshot'lari: data_coverage_reports, data_readiness_assessments, ...

KORUNAN (kaynak/yapilandirma):
- ders, fakulte, bolum, mufredat, mufredat_ders, ogrenci, kayit, anket_*, havuz
- ahp_weight_profiles, decision_policies, planlama politikalari, ML/benchmark

GUVENLIK:
- Once DB yedegi alinir (data/adil_secmeli.db.bak_reset_<zaman>).
- Varsayilan KURU CALISMA (dry-run): ne silinecegini gosterir, SILMEZ.
- Gercekten silmek icin: --onayla

Kullanim:
    python -m scripts.reset_computed_data                 # kuru calisma (onizleme)
    python -m scripts.reset_computed_data --onayla        # yedek al + sil
    python -m scripts.reset_computed_data --db data/adil_secmeli.db --onayla
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent

# Temizlenecek tablolar (yalnizca var olanlar islenir).
CLEAR_TABLES: list[str] = [
    # Kriter & turetilmis
    "ders_kriterleri", "performans", "populerlik", "skor",
    # Karar ciktilari
    "decision_runs", "course_decisions", "course_score_breakdowns",
    "course_trend_analysis", "course_data_confidence",
    "course_decision_explanations", "course_governance_flags",
    "decision_sensitivity_results", "decision_fairness_reports",
    "fairness_metric_items", "low_confidence_decision_flags",
    "post_decision_outcomes", "decision_run_import_sources",
    "decision_staleness_flags", "ahp_sensitivity_results",
    "ahp_course_sensitivity_items",
    # Karar kaynakli statu gecisleri
    "course_state_transitions", "course_state_approvals",
    # Plan ciktilari
    "semester_plan_runs", "semester_plan_course_assignments",
    "semester_plan_constraint_violations", "semester_plan_scenarios",
    # Kalite snapshot / turetilmis kayitlar
    "data_coverage_reports", "data_readiness_assessments", "data_snapshots",
    "criteria_completion_history", "criteria_completion_matrix",
    "criteria_completion_tasks", "criteria_missing_data_risks",
    "missing_data_items", "criteria_validation_issues", "data_validation_issues",
]


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _count(cur: sqlite3.Cursor, name: str) -> int:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        return int(cur.fetchone()[0] or 0)
    except sqlite3.OperationalError:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Hesaplanan verileri temizle (tam temiz sayfa)")
    parser.add_argument("--db", default=str(KOK / "data" / "adil_secmeli.db"))
    parser.add_argument("--onayla", action="store_true",
                        help="Yedek alip GERCEKTEN siler. Verilmezse yalnizca onizleme.")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"HATA: DB bulunamadi: {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    mevcut = [(t, _count(cur, t)) for t in CLEAR_TABLES if _table_exists(cur, t)]
    eksik = [t for t in CLEAR_TABLES if not _table_exists(cur, t)]
    toplam = sum(n for _, n in mevcut)

    print("=" * 64)
    print("  HESAPLANAN VERI TEMIZLIGI — " + ("UYGULANACAK" if args.onayla else "ONIZLEME (kuru calisma)"))
    print("=" * 64)
    print(f"  DB: {db_path}")
    print(f"  Silinecek tablo sayisi: {len(mevcut)}   |   Toplam satir: {toplam}")
    print("-" * 64)
    for t, n in mevcut:
        if n:
            print(f"  {t:<42} {n:>8} satir -> 0")
    if eksik:
        print(f"  (DB'de olmayan {len(eksik)} tablo atlandi)")
    print("-" * 64)
    print("  KORUNUR: ders, fakulte, bolum, mufredat, ogrenci, kayit, anket_*,")
    print("           havuz, ahp_weight_profiles, decision_policies, planlama politikalari.")

    if not args.onayla:
        print("\nONIZLEME bitti. Gercekten silmek icin: python -m scripts.reset_computed_data --onayla")
        conn.close()
        return 0

    # Yedek al
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    yedek = db_path.with_name(f"{db_path.name}.bak_reset_{ts}")
    conn.close()  # kopyalamadan once baglantiyi kapat
    shutil.copy2(str(db_path), str(yedek))
    print(f"\n  Yedek alindi: {yedek}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    silinen = 0
    for t, _ in mevcut:
        try:
            cur.execute(f"DELETE FROM {t}")
            silinen += 1
        except sqlite3.OperationalError as exc:
            print(f"  [UYARI] {t} silinemedi: {exc}")
    conn.commit()
    cur.execute("VACUUM")
    conn.commit()
    conn.close()
    print(f"  Temizlendi: {silinen} tablo. VACUUM uygulandi.")
    print("\nArtik Kriter Girdi sayfasinda her ders SABIT varsayilan (0) gosterir;")
    print("not veri seti veya elle giris sonrasi degerler tekrar dolar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

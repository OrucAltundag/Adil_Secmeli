# -*- coding: utf-8 -*-
"""
TUM kriter girdilerini ve turev tablolari temizle.
ders_kriterleri + criteria_completion_* / department_status / faculty_status /
validation_issues / missing_data_risks vb.
Sadece policy (yapilandirma) tablosu korunur.
"""
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "adil_secmeli.db"


def main():
    yedek = str(DB) + ".bak_kriter_temiz_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(str(DB), yedek)
    print(f"Yedek: {Path(yedek).name}")

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    # Silinecek tablolar (policy korunur)
    temizle = [
        "ders_kriterleri",
        "criteria_completion_matrix",
        "criteria_completion_history",
        "criteria_completion_overrides",
        "criteria_completion_tasks",
        "criteria_department_status",
        "criteria_faculty_status",
        "criteria_import",
        "criteria_import_rows",
        "criteria_missing_data_risks",
        "criteria_validation_issues",
        "criteria_value_sources",
    ]
    silinen = {}
    for t in temizle:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            n_oncesi = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {t}")
            silinen[t] = n_oncesi
        except sqlite3.OperationalError:
            pass  # tablo yoksa atla

    conn.commit()

    print("\n=== SILINEN ===")
    for t, n in silinen.items():
        if n:
            print(f"  {t}: {n} satir silindi")

    print("\n=== DOGRULAMA (kalan) ===")
    for t in temizle:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            print(f"  {t}: {cur.fetchone()[0]}")
        except sqlite3.OperationalError:
            pass
    conn.close()
    print("\nTAMAMLANDI - tum kriter girdileri temizlendi.")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
2022 disindaki TUM karar verilerini sil.

Sistemde sadece 2022 mufredati var; tum decision_runs 2024 (gecersiz).
Bu script karar motoru ciktilarini tamamen temizler — yeni karar
calistirildiginda 2022 icin sifirdan uretilecek.
"""
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "adil_secmeli.db"
KORUNAN_YIL = 2022


def main():
    yedek = str(DB) + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(str(DB), yedek)
    print(f"Yedek: {Path(yedek).name}")

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    # Korunacak 2022 run id'leri (muhtemelen bos)
    cur.execute(
        "SELECT id FROM decision_runs WHERE year = ?", (KORUNAN_YIL,)
    )
    kalan_runlar = [int(r[0]) for r in cur.fetchall()]
    print(f"Korunan 2022 run sayisi: {len(kalan_runlar)}")

    if kalan_runlar:
        ph = ",".join("?" * len(kalan_runlar))
        run_kosul = f"decision_run_id NOT IN ({ph})"
        params = tuple(kalan_runlar)
    else:
        run_kosul = "1=1"  # hicbir 2022 run yok -> hepsini sil
        params = ()

    silinen = {}

    # 1) course_decision_explanations -> course_decisions uzerinden
    cur.execute(
        f"""
        DELETE FROM course_decision_explanations
        WHERE course_decision_id IN (
            SELECT id FROM course_decisions WHERE {run_kosul}
        )
        """,
        params,
    )
    silinen["course_decision_explanations"] = cur.rowcount

    # 2) decision_run_id ile bagli tablolar
    for t in [
        "course_decisions",
        "decision_sensitivity_results",
        "decision_fairness_reports",
        "course_state_transitions",
        "course_data_confidence",
        "course_trend_analysis",
        "course_score_breakdowns",
        "decision_run_import_sources",
        "decision_staleness_flags",
        "ahp_sensitivity_results",
        "low_confidence_decision_flags",
        "post_decision_outcomes",
    ]:
        try:
            cur.execute(f"DELETE FROM {t} WHERE {run_kosul}", params)
            silinen[t] = cur.rowcount
        except sqlite3.OperationalError:
            pass  # tabloda decision_run_id yoksa atla

    # 3) year ile bagli (decision_run_id'siz) tablolar
    for t in ["course_state_approvals", "decision_runs"]:
        cur.execute(
            f"DELETE FROM {t} WHERE year != ?", (KORUNAN_YIL,)
        )
        silinen[t] = cur.rowcount

    conn.commit()

    print("\n=== SILINEN KAYITLAR ===")
    for t, n in silinen.items():
        if n:
            print(f"  {t}: {n}")

    print("\n=== DOGRULAMA (kalan satirlar) ===")
    for t in [
        "decision_runs", "course_decisions", "decision_fairness_reports",
        "decision_sensitivity_results", "course_state_transitions",
        "course_state_approvals", "course_decision_explanations",
    ]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur.fetchone()[0]}")
    conn.close()
    print("\nTAMAMLANDI — tum 2022-disi karar verisi temizlendi.")


if __name__ == "__main__":
    main()

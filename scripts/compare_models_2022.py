# -*- coding: utf-8 -*-
"""
2022 verisiyle HIBRIT karar modelini (AHP-TOPSIS) iki baseline ile karsilastir.

Final sunumu geregi: 1 hibrit + 2 algoritma + karsilastirmali degerlendirme.
Bu script gercek 2022 verisinden ders-kriter matrisini kurar ve uc modeli
(Esit Agirlikli TOPSIS, AHP-SAW, AHP-TOPSIS Hibrit) calistirip Spearman/Kendall
korelasyonlariyla raporlar. Cikti dogrudan sunuma/kitapciga konabilir.

Kullanim:
    python -m scripts.compare_models_2022
    python -m scripts.compare_models_2022 --yil 2022 --fakulte-id 1
    python -m scripts.compare_models_2022 --donem Guz
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from app.services.ahp_profile_service import resolve_ahp_profile  # noqa: E402
from app.services.calculation import get_faculty_year_topsis_results  # noqa: E402
from app.services.db import get_raw_connection  # noqa: E402
from app.services.hybrid_model_service import (  # noqa: E402
    compare_models,
    format_comparison_report,
)

CRITERIA = ["basari", "trend", "populerlik", "anket"]


def _ahp_weights(conn, faculty_id, year):
    try:
        prof = resolve_ahp_profile(conn, faculty_id=faculty_id, department_id=None, year=year)
        w = prof.get("weights") or {}
        vec = [float(w.get(k, 0.0)) for k in CRITERIA]
        if sum(vec) > 0:
            return vec, prof.get("name", "aktif profil")
    except Exception as exc:  # noqa: BLE001
        print(f"  (AHP profili okunamadi, varsayilan agirlik: {exc})")
    return [0.45, 0.20, 0.20, 0.15], "varsayilan (0.45/0.20/0.20/0.15)"


def _build_matrix(conn, faculty_id, year, donem):
    cur = conn.cursor()
    pack = get_faculty_year_topsis_results(
        cur=cur, fakulte_id=int(faculty_id), akademik_yil=int(year), donem=donem
    )
    if not pack.get("ok"):
        return [], []
    metric_map = pack.get("metric_map", {})
    ids, rows = [], []
    for cid, m in metric_map.items():
        try:
            vals = [float(m.get(k)) for k in CRITERIA]
        except (TypeError, ValueError):
            continue
        if any(v != v for v in vals):  # NaN
            continue
        # Kriterleri 0-100 olcegine getir (populerlik/anket 0-1 gelebilir)
        vals = [v * 100.0 if 0.0 <= v <= 1.0 and k in ("populerlik", "anket") else v
                for k, v in zip(CRITERIA, vals)]
        # Verisi olmayan (tum kriterleri 0) dersleri kiyasa alma.
        if all(v == 0 for v in vals):
            continue
        ids.append(m.get("kod") or cid)
        rows.append(vals)
    return ids, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Hibrit AHP-TOPSIS model karsilastirmasi")
    parser.add_argument("--yil", type=int, default=2022)
    parser.add_argument("--fakulte-id", type=int, default=1)
    parser.add_argument("--donem", default="Guz")
    parser.add_argument("--db", default=str(KOK / "data" / "adil_secmeli.db"))
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"HATA: DB bulunamadi: {db_path}", file=sys.stderr)
        return 2

    conn = get_raw_connection(str(db_path))
    try:
        weights, wname = _ahp_weights(conn, args.fakulte_id, args.yil)
        ids, matrix = _build_matrix(conn, args.fakulte_id, args.yil, args.donem)
    finally:
        conn.close()

    if len(ids) < 3:
        print("Yeterli ders verisi yok (en az 3 ders gerekli). "
              "Once kriter/performans/populerlik verisini doldurun.")
        return 1

    print(f"AHP agirlik kaynagi: {wname}")
    result = compare_models(ids, matrix, CRITERIA, weights)
    print(format_comparison_report(result, top_n=20))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
2022 yili icin tum fakultelerde ilk donem (Guz/Bahar) planini uret.

Faz 4 (nihai_senaryo.md) kapsaminda yazildi. UI'daki "Plan Uret" butonunun
cagirdigi `generate_semester_plan` ile ayni hatti kullanir; her fakulte icin
ayri bir `semester_plan_runs` kaydi olusturur. Plan, Karar Merkezi'nin
urettigi acilabilirlik skorlarini (Faz 3) aday siralamasinda kullanir.

On kosul: once karar calistirmasi yapilmis olmali
(`python -m scripts.run_first_decision_2022`). Karar yoksa planlama eski
skor kaynagina (skor tablosu) duser ama yine de calisir.

Kullanim:
    python -m scripts.run_first_semester_plan_2022
    python -m scripts.run_first_semester_plan_2022 --yil 2022
    python -m scripts.run_first_semester_plan_2022 --fakulte-id 3
    python -m scripts.run_first_semester_plan_2022 --db data/adil_secmeli.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from app.services.db import get_raw_connection  # noqa: E402
from app.services.semester_planning_engine import generate_semester_plan  # noqa: E402


def _count(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return int(cur.fetchone()[0])
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()


def _fmt_section(title: str) -> str:
    return f"\n{'=' * 60}\n  {title}\n{'=' * 60}"


def _faculties(db_path: Path, only: int | None) -> list[tuple[int, str]]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        if only is not None:
            cur.execute("SELECT fakulte_id, ad FROM fakulte WHERE fakulte_id = ?", (int(only),))
        else:
            cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY fakulte_id")
        return [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="2022 ilk donem plani uret")
    parser.add_argument("--yil", type=int, default=2022)
    parser.add_argument("--fakulte-id", type=int, default=None)
    parser.add_argument("--db", default=str(KOK / "data" / "adil_secmeli.db"))
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"HATA: DB bulunamadi: {db_path}", file=sys.stderr)
        return 2

    plans_before = _count(db_path, "semester_plan_runs")
    faculties = _faculties(db_path, args.fakulte_id)

    print(_fmt_section("Donem Plani Baslangici"))
    print(f"  DB                         : {db_path}")
    print(f"  Yil                        : {args.yil}")
    print(f"  Fakulte sayisi             : {len(faculties)}")
    print(f"  semester_plan_runs (oncesi): {plans_before}")

    ok_count = 0
    fail_count = 0
    conn = get_raw_connection(str(db_path))
    try:
        for fid, fad in faculties:
            try:
                result = generate_semester_plan(
                    conn,
                    year=args.yil,
                    faculty_id=fid,
                    persist=True,
                    generate_alternatives=True,
                    created_by="cli-run_first_semester_plan",
                )
                conn.commit()
                plan_id = result.get("plan_id")
                fall = len(result.get("fall_courses") or [])
                spring = len(result.get("spring_courses") or [])
                unassigned = len(result.get("unassigned_courses") or [])
                if plan_id is not None:
                    ok_count += 1
                    print(
                        f"  [OK]  [{fid}] {fad}: plan_id={plan_id} "
                        f"Guz={fall} Bahar={spring} yerlesemeyen={unassigned}"
                    )
                else:
                    print(f"  [--]  [{fid}] {fad}: plan uretildi ama plan_id yok (persist?)")
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                fail_count += 1
                print(f"  [HATA] [{fid}] {fad}: {exc}")
    finally:
        conn.close()

    plans_after = _count(db_path, "semester_plan_runs")
    print(_fmt_section("Sonuc"))
    print(f"  basarili fakulte           : {ok_count}")
    print(f"  hatali fakulte             : {fail_count}")
    print(f"  semester_plan_runs (sonra) : {plans_after} (+{plans_after - plans_before})")

    if plans_after == plans_before:
        print("\nUYARI: semester_plan_runs degismedi. Aday ders bulunamamis olabilir.")
        return 1
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

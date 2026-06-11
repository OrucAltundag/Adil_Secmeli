# -*- coding: utf-8 -*-
"""
2022 yili icin tum fakultelerde ilk resmi karar calistirmasini uret.

Faz 2 (nihai_senaryo.md) kapsaminda yazildi. UI'daki "Yeni Karar Calistir"
butonunun cagirdigi `run_all_algorithms_for_year` ile ayni hatti kullanir
ama komut satirindan calistirilabilir; uygulama acikken DB kilitli kaldigi
durumda uygulama kapatildiktan sonra elle kosturulabilir.

Kullanim:
    python -m scripts.run_first_decision_2022
    python -m scripts.run_first_decision_2022 --yil 2022 --donem Guz
    python -m scripts.run_first_decision_2022 --fakulte-id 3
    python -m scripts.run_first_decision_2022 --db data/adil_secmeli.db

Cikti:
    - Islenen / atlanan / hatali fakulte ozetleri
    - Yeni eklenen decision_runs satir sayisi
    - Yeni eklenen course_decisions satir sayisi
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from app.services.calculation import run_all_algorithms_for_year  # noqa: E402


def _count(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def _fmt_section(title: str) -> str:
    return f"\n{'=' * 60}\n  {title}\n{'=' * 60}"


def main() -> int:
    parser = argparse.ArgumentParser(description="2022 ilk karar calistirma")
    parser.add_argument("--yil", type=int, default=2022)
    parser.add_argument("--donem", default="Guz", choices=["Guz", "Bahar"])
    parser.add_argument(
        "--fakulte-id",
        type=int,
        default=None,
        help="Belirli bir fakulte icin (None = tum fakulteler)",
    )
    parser.add_argument(
        "--db",
        default=str(KOK / "data" / "adil_secmeli.db"),
        help="Veritabani dosyasi yolu",
    )
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"HATA: DB bulunamadi: {db_path}", file=sys.stderr)
        return 2

    runs_before = _count(db_path, "decision_runs")
    decisions_before = _count(db_path, "course_decisions")

    print(_fmt_section("Karar Calistirma Baslangici"))
    print(f"  DB         : {db_path}")
    print(f"  Yil        : {args.yil}")
    print(f"  Donem      : {args.donem}")
    print(f"  Fakulte    : {args.fakulte_id if args.fakulte_id is not None else 'TUMU'}")
    print(f"  decision_runs (oncesi)     : {runs_before}")
    print(f"  course_decisions (oncesi)  : {decisions_before}")

    result = run_all_algorithms_for_year(
        yil=args.yil,
        db_path=str(db_path),
        donem=args.donem,
        fakulte_id=args.fakulte_id,
    )

    runs_after = _count(db_path, "decision_runs")
    decisions_after = _count(db_path, "course_decisions")

    print(_fmt_section("Sonuc"))
    print(f"  ok         : {result.get('ok')}")
    print(f"  islenen    : {len(result.get('processed', []))} fakulte")
    print(f"  atlanan    : {len(result.get('skipped', []))} fakulte")
    print(f"  hatali     : {len(result.get('errors', []))} fakulte")
    print(f"  decision_runs (sonra)      : {runs_after} (+{runs_after - runs_before})")
    print(f"  course_decisions (sonra)   : {decisions_after} (+{decisions_after - decisions_before})")

    if result.get("processed"):
        print(_fmt_section("Islenen Fakulteler"))
        for item in result["processed"]:
            print(f"  [{item.get('fakulte_id')}] {item.get('fakulte', '-')}")

    if result.get("skipped"):
        print(_fmt_section("Atlanan Fakulteler"))
        for item in result["skipped"]:
            print(f"  [{item.get('fakulte_id')}] {item.get('fakulte', '-')}")
            print(f"      sebep: {item.get('reason', '-')}")

    if result.get("errors"):
        print(_fmt_section("Hatalar"))
        for item in result["errors"]:
            print(f"  [{item.get('fakulte_id', '-')}] {item.get('fakulte', '-')}")
            print(f"      hata: {item.get('error', '-')}")

    if result.get("messages"):
        print(_fmt_section("Mesajlar"))
        for msg in result["messages"]:
            print(f"  - {msg}")

    if not result.get("ok"):
        return 1
    if runs_after == runs_before:
        print("\nUYARI: decision_runs satir sayisi degismedi. Tum fakulteler atlanmis olabilir.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

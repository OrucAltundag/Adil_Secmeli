# -*- coding: utf-8 -*-
"""
Safely clean non-elective rows from the pool table.

Default mode is dry-run. Use --apply to persist changes.
Deleted rows are copied into `havuz_cleanup_backup`.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime

from app.services.course_type import build_course_type_expr, build_elective_predicate


def _build_non_elective_query(cur: sqlite3.Cursor) -> tuple[str, str]:
    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    type_expr = build_course_type_expr(cur=cur, alias="d")
    if elective_predicate == "0=1":
        # No compatible type column found: avoid unsafe broad cleanup.
        return "SELECT NULL WHERE 0=1", elective_predicate
    query = f"""
        SELECT
            h.id,
            h.ders_id,
            h.yil,
            h.fakulte_id,
            h.bolum_id,
            d.ad AS ders_adi,
            {type_expr} AS ders_tipi
        FROM havuz h
        LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
        WHERE NOT ({elective_predicate})
        ORDER BY h.yil, h.fakulte_id, h.id
    """
    return query, elective_predicate


def run_cleanup(db_path: str, apply_changes: bool = False) -> dict:
    if not os.path.exists(db_path):
        return {"ok": False, "error": f"DB bulunamadi: {db_path}"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        query, elective_predicate = _build_non_elective_query(cur)
        if elective_predicate == "0=1":
            return {
                "ok": False,
                "error": (
                    "Ders tipi kolonu tespit edilemedi (DersTipi/ders_tipi/tip/tur). "
                    "Temizlik guvenlik nedeniyle durduruldu."
                ),
            }
        cur.execute(query)
        rows = cur.fetchall()
        ids = [int(r["id"]) for r in rows if r["id"] is not None]

        summary = {
            "ok": True,
            "db_path": db_path,
            "apply": bool(apply_changes),
            "candidate_count": len(ids),
            "deleted_count": 0,
            "backup_count": 0,
            "sample": [
                {
                    "id": int(r["id"]),
                    "ders_id": str(r["ders_id"]),
                    "yil": int(r["yil"]) if r["yil"] is not None else None,
                    "fakulte_id": int(r["fakulte_id"]) if r["fakulte_id"] is not None else None,
                    "ders_adi": str(r["ders_adi"] or ""),
                    "ders_tipi": str(r["ders_tipi"] or ""),
                }
                for r in rows[:20]
            ],
        }

        if not apply_changes or not ids:
            return summary

        # Backup table keeps a safety copy of removed rows.
        cur.execute("CREATE TABLE IF NOT EXISTS havuz_cleanup_backup AS SELECT * FROM havuz WHERE 0")

        placeholders = ",".join("?" for _ in ids)
        cur.execute(
            f"""
            INSERT INTO havuz_cleanup_backup
            SELECT *
            FROM havuz
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )
        summary["backup_count"] = int(cur.rowcount or 0)

        cur.execute(
            f"""
            DELETE FROM havuz
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )
        summary["deleted_count"] = int(cur.rowcount or 0)

        # Optional audit marker.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS havuz_cleanup_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cleaned_at TEXT NOT NULL,
                deleted_count INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            "INSERT INTO havuz_cleanup_audit (cleaned_at, deleted_count) VALUES (?, ?)",
            (datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), int(summary["deleted_count"])),
        )

        conn.commit()
        return summary
    except Exception as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup non-elective rows in havuz.")
    parser.add_argument("--db-path", default="data/adil_secmeli.db", help="SQLite DB path")
    parser.add_argument("--apply", action="store_true", help="Apply cleanup changes")
    args = parser.parse_args()

    result = run_cleanup(db_path=str(args.db_path), apply_changes=bool(args.apply))
    if not result.get("ok"):
        print(f"[ERROR] {result.get('error', 'Unknown error')}")
        return 1

    print(f"DB: {result['db_path']}")
    print(f"Mode: {'APPLY' if result['apply'] else 'DRY-RUN'}")
    print(f"Candidates: {result['candidate_count']}")
    print(f"Backup rows: {result.get('backup_count', 0)}")
    print(f"Deleted rows: {result.get('deleted_count', 0)}")
    if result.get("sample"):
        print("Sample:")
        for row in result["sample"]:
            print(
                f"  id={row['id']} yil={row['yil']} fakulte={row['fakulte_id']} "
                f"ders={row['ders_id']} tip={row['ders_tipi']} ad={row['ders_adi']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

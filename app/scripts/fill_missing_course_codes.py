from __future__ import annotations

import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.services.course_code_service import (
    apply_missing_course_codes,
    preview_missing_course_codes,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bos ders kodlarini fakulte+bolum+ders_id kuralina gore doldurur.")
    parser.add_argument("--db", required=True, help="SQLite veritabani yolu")
    parser.add_argument("--dry-run", action="store_true", help="Sadece onizleme yapar, guncelleme yapmaz")
    args = parser.parse_args()

    result = preview_missing_course_codes(args.db) if args.dry_run else apply_missing_course_codes(args.db)
    rows = list(result.get("rows") or [])

    if args.dry_run:
        print(f"dry_run_missing_count={int(result.get('missing_count') or 0)}")
    else:
        print(f"updated_count={int(result.get('updated_count') or 0)}")
        print(f"remaining_blank_count={int(result.get('remaining_blank_count') or 0)}")

    for row in rows[:20]:
        print(
            f"ders_id={row['ders_id']} "
            f"fakulte={row.get('fakulte_adi') or '-'} "
            f"bolum={row.get('bolum_adi') or '-'} "
            f"ders_adi={row.get('ders_adi') or '-'} "
            f"generated_code={row['generated_code']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

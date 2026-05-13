"""Run production decision algorithms and save a JSON report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.services.calculation import run_all_algorithms_for_year


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the production algorithm pipeline for one academic year."
    )
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--db-path", default="data/adil_secmeli.db")
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to reports/production_algorithm_runs_<year>_to_<year+1>_final.json",
    )
    args = parser.parse_args()

    terms = ["Güz", "Bahar"]
    output_path = Path(
        args.output
        or f"reports/production_algorithm_runs_{args.year}_to_{args.year + 1}_final.json"
    )

    report = {
        "year": args.year,
        "target_year": args.year + 1,
        "db_path": args.db_path,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runs": [],
    }

    for term in terms:
        result = run_all_algorithms_for_year(
            args.year,
            db_path=args.db_path,
            donem=term,
        )
        report["runs"].append({"donem": term, "result": result})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = [
        {
            "donem": run["donem"],
            "ok": run["result"].get("ok"),
            "processed": run["result"].get("processed_faculties"),
            "errors": len(run["result"].get("errors", [])),
        }
        for run in report["runs"]
    ]
    print(output_path)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

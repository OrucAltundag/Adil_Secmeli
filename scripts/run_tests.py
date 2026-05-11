#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adil Secmeli — Tek komut test runner.

Kullanim:
    python scripts/run_tests.py              # Tum testler
    python scripts/run_tests.py --unit       # Sadece unit
    python scripts/run_tests.py --coverage   # Coverage ile
    python scripts/run_tests.py --quick      # Slow haric
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports" / "test_results"


def run_pytest(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "pytest"] + args
    print(f"\n{'='*60}")
    print(f"  Calistirilan: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=capture, text=True)


def main():
    parser = argparse.ArgumentParser(description="Adil Secmeli Test Runner")
    parser.add_argument("--unit", action="store_true", help="Sadece unit testler")
    parser.add_argument("--integration", action="store_true")
    parser.add_argument("--e2e", action="store_true")
    parser.add_argument("--regression", action="store_true")
    parser.add_argument("--api", action="store_true")
    parser.add_argument("--db", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--quick", action="store_true", help="Slow testleri atla")
    parser.add_argument("--coverage", action="store_true", help="Coverage raporu uret")
    parser.add_argument("--report", action="store_true", help="JSON rapor kaydet")
    args = parser.parse_args()

    pytest_args = ["-v", "--tb=short"]

    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.e2e:
        markers.append("e2e")
    if args.regression:
        markers.append("regression")
    if args.api:
        markers.append("api")
    if args.db:
        markers.append("db")
    if args.benchmark:
        markers.append("benchmark")

    if markers:
        pytest_args.extend(["-m", " or ".join(markers)])
    elif args.quick:
        pytest_args.extend(["-m", "not slow and not requires_display"])

    if args.coverage:
        pytest_args.extend([
            "--cov=app", "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
        ])

    if args.report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        junit_path = str(REPORTS_DIR / "junit.xml")
        pytest_args.extend([f"--junitxml={junit_path}"])

    result = run_pytest(pytest_args)

    if args.report:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "returncode": result.returncode,
            "status": "passed" if result.returncode == 0 else "failed",
            "command": " ".join([sys.executable, "-m", "pytest"] + pytest_args),
        }
        summary_path = REPORTS_DIR / "test_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\nRapor kaydedildi: {summary_path}")

    print(f"\n{'='*60}")
    print(f"  Sonuc: {'BASARILI' if result.returncode == 0 else 'BASARISIZ'}")
    print(f"{'='*60}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

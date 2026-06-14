# -*- coding: utf-8 -*-
"""Benchmark dataset'lerini sistem veritabanından üretip data/benchmark/ altına yazar.

Kullanıcı talebi: "Dataset eksik diyor; ihtiyacı olan bütün dataset'leri oluştur,
data klasörüne ekle."

Üretilen katmanlar (data/benchmark/ altına CSV):
- raw_real/   : students, courses, preferences, survey_responses, allocations
- derived/    : student_course_features, student_course_features_unencoded
- synthetic/  : 5k, 10k, 50k, 100k, 250k ölçek katmanları

Çalıştırma:
    python -m scripts.build_benchmark_datasets
    python -m scripts.build_benchmark_datasets --db data/adil_secmeli.db --out data/benchmark
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.datasets.preprocess import DataPipeline, PipelineConfig, save_dataset_layers


def build(db_path: str, out_dir: str, dataset_name: str = "adil_real") -> dict:
    config = PipelineConfig(
        dataset_name=dataset_name,
        source_type="sqlite",
        source_path=db_path,
    )
    bundle = DataPipeline().run(config)
    save_dataset_layers(bundle, out_dir)

    info = {
        "dataset_name": bundle.dataset_name,
        "out_dir": str(out_dir),
        "raw_real": {k: tuple(v.shape) for k, v in bundle.raw_real.items()},
        "derived": {k: tuple(v.shape) for k, v in bundle.derived.items()},
        "synthetic_tiers": {k: tuple(v.shape) for k, v in bundle.synthetic.items()},
    }
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark dataset üretici")
    parser.add_argument("--db", default="data/adil_secmeli.db", help="Kaynak SQLite veritabanı")
    parser.add_argument("--out", default="data/benchmark", help="Çıktı klasörü")
    parser.add_argument("--name", default="adil_real", help="Dataset adı")
    args = parser.parse_args(argv)

    if not Path(args.db).exists():
        print(f"[HATA] Veritabanı bulunamadı: {args.db}")
        return 1

    print(f"[1/2] Dataset üretiliyor: {args.db} -> {args.out}")
    info = build(args.db, args.out, dataset_name=args.name)
    print("[2/2] Tamamlandı. Üretilen tablolar:")
    for layer in ("raw_real", "derived"):
        for name, shape in info[layer].items():
            print(f"   {layer}/{name}: {shape[0]} satır × {shape[1]} kolon")
    print("   synthetic tiers:", ", ".join(info["synthetic_tiers"].keys()))
    print(f"\nCSV dosyaları: {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

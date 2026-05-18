"""End-to-end dataset preparation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from app.datasets.entities import DatasetBundle
from app.datasets.feature_engineering import FeatureEngineer
from app.datasets.loaders import RealDatasetLoader, sanitize_dataset
from app.datasets.synthetic_generator import SyntheticDataGenerator


@dataclass(slots=True)
class PipelineConfig:
    dataset_name: str = "benchmark_dataset"
    source_type: Literal["csv", "sqlite"] = "sqlite"
    source_path: str = "data/adil_secmeli.db"
    synth_noise_std: float = 0.02
    synth_class_imbalance_alpha: float = 0.0
    synth_capacity_scale: float = 1.0


class DataPipeline:
    """Pipeline that materializes raw_real, derived, synthetic layers."""

    def __init__(
        self,
        loader: RealDatasetLoader | None = None,
        feature_engineer: FeatureEngineer | None = None,
        synthetic_generator: SyntheticDataGenerator | None = None,
    ) -> None:
        self.loader = loader or RealDatasetLoader()
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.synthetic_generator = synthetic_generator or SyntheticDataGenerator()

    def run(self, config: PipelineConfig) -> DatasetBundle:
        bundle = self._load(config)
        cleaned = sanitize_dataset(bundle)
        derived = self.feature_engineer.generate(cleaned)
        synthetic_tables = self.synthetic_generator.generate_scale_tiers(
            derived,
            table_name="student_course_features_unencoded",
            noise_std=config.synth_noise_std,
            class_imbalance_alpha=config.synth_class_imbalance_alpha,
            capacity_scale=config.synth_capacity_scale,
        )
        return DatasetBundle(
            dataset_name=config.dataset_name,
            raw_real=dict(derived.raw_real),
            derived=dict(derived.derived),
            synthetic=synthetic_tables,
            metadata={
                **dict(derived.metadata),
                "pipeline": {
                    "source_type": config.source_type,
                    "source_path": config.source_path,
                    "synth_noise_std": config.synth_noise_std,
                    "synth_class_imbalance_alpha": config.synth_class_imbalance_alpha,
                    "synth_capacity_scale": config.synth_capacity_scale,
                },
            },
        )

    def _load(self, config: PipelineConfig) -> DatasetBundle:
        self.loader.dataset_name = config.dataset_name
        if config.source_type == "csv":
            return self.loader.from_csv_folder(config.source_path)
        return self.loader.from_sqlite(config.source_path)


def save_dataset_layers(bundle: DatasetBundle, output_root: str | Path) -> None:
    root = Path(output_root)
    for layer_name, layer_data in (
        ("raw_real", bundle.raw_real),
        ("derived", bundle.derived),
        ("synthetic", bundle.synthetic),
    ):
        layer_dir = root / layer_name
        layer_dir.mkdir(parents=True, exist_ok=True)
        for table_name, table in layer_data.items():
            if isinstance(table, pd.DataFrame):
                table.to_csv(layer_dir / f"{table_name}.csv", index=False)

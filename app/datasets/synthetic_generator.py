"""Synthetic dataset generator with bootstrap-based scaling controls."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.datasets.entities import DatasetBundle


@dataclass(slots=True)
class SyntheticConfig:
    target_size: int
    noise_std: float = 0.02
    class_imbalance_alpha: float = 0.0
    capacity_scale: float = 1.0
    random_seed: int = 42


SCALE_TIERS = {
    "5k": 5_000,
    "10k": 10_000,
    "50k": 50_000,
    "100k": 100_000,
    "250k": 250_000,
}


class SyntheticDataGenerator:
    """Produces synthetic variants while preserving source distribution."""

    def __init__(self, default_seed: int = 42) -> None:
        self.default_seed = default_seed

    def generate(
        self,
        bundle: DatasetBundle,
        table_name: str = "student_course_features_unencoded",
        config: SyntheticConfig | None = None,
    ) -> pd.DataFrame:
        cfg = config or SyntheticConfig(target_size=10_000, random_seed=self.default_seed)
        base = self._resolve_base_table(bundle, table_name)
        if base.empty:
            raise ValueError(f"Base table '{table_name}' is empty; cannot synthesize data.")

        rng = np.random.default_rng(cfg.random_seed)
        sampled = self._bootstrap_sample(base, cfg.target_size, cfg.class_imbalance_alpha, rng)
        noised = self._inject_noise(sampled, cfg.noise_std, rng)
        constrained = self._apply_capacity_constraints(noised, cfg.capacity_scale, rng)
        return constrained.reset_index(drop=True)

    def generate_scale_tiers(
        self,
        bundle: DatasetBundle,
        table_name: str = "student_course_features_unencoded",
        noise_std: float = 0.02,
        class_imbalance_alpha: float = 0.0,
        capacity_scale: float = 1.0,
    ) -> dict[str, pd.DataFrame]:
        synthetic: dict[str, pd.DataFrame] = {}
        for tier, size in SCALE_TIERS.items():
            cfg = SyntheticConfig(
                target_size=size,
                noise_std=noise_std,
                class_imbalance_alpha=class_imbalance_alpha,
                capacity_scale=capacity_scale,
                random_seed=self.default_seed + size,
            )
            synthetic[tier] = self.generate(bundle=bundle, table_name=table_name, config=cfg)
        return synthetic

    def _resolve_base_table(self, bundle: DatasetBundle, table_name: str) -> pd.DataFrame:
        if table_name in bundle.derived:
            return bundle.derived[table_name].copy()
        if table_name in bundle.raw_real:
            return bundle.raw_real[table_name].copy()
        raise KeyError(f"Base table not found in raw_real/derived: {table_name}")

    def _bootstrap_sample(
        self,
        base: pd.DataFrame,
        target_size: int,
        class_imbalance_alpha: float,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        n = len(base)
        if n == 0:
            return base.copy()

        weights = np.ones(n, dtype=float)
        if class_imbalance_alpha > 0 and "course_id" in base.columns:
            counts = base["course_id"].value_counts(dropna=False).to_dict()
            course_series = base["course_id"].map(lambda x: counts.get(x, 1))
            inv = 1.0 / np.maximum(course_series.to_numpy(dtype=float), 1.0)
            inv = inv / inv.sum()
            weights = (1 - class_imbalance_alpha) * (np.ones(n) / n) + class_imbalance_alpha * inv
            weights = weights / weights.sum()
        indices = rng.choice(np.arange(n), size=int(target_size), replace=True, p=weights)
        return base.iloc[indices].copy()

    def _inject_noise(self, df: pd.DataFrame, noise_std: float, rng: np.random.Generator) -> pd.DataFrame:
        if noise_std <= 0:
            return df
        out = df.copy()
        numeric_cols = out.select_dtypes(include=["number"]).columns.tolist()
        protected = {"student_id", "course_id"}
        for col in numeric_cols:
            if col in protected:
                continue
            sigma = float(np.nanstd(out[col].to_numpy()))
            scale = noise_std if sigma == 0.0 else noise_std * sigma
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0) + rng.normal(0.0, scale, len(out))
            if col.endswith("_norm") or col.endswith("_score") or col == "composite_score":
                out[col] = out[col].clip(lower=0.0, upper=1.0)
        return out

    def _apply_capacity_constraints(
        self,
        df: pd.DataFrame,
        capacity_scale: float,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        out = df.copy()
        if "capacity" not in out.columns:
            return out
        cap = pd.to_numeric(out["capacity"], errors="coerce").fillna(0.0)
        cap = (cap * float(capacity_scale)).round().clip(lower=1.0)
        jitter = rng.integers(low=-2, high=3, size=len(cap))
        out["capacity"] = (cap + jitter).clip(lower=1.0)
        return out

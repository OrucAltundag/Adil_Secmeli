"""Dataset pipeline package."""

from app.datasets.entities import (
    Allocation,
    BenchmarkRun,
    Course,
    DatasetBundle,
    MetricResult,
    Preference,
    Student,
    SurveyResponse,
)
from app.datasets.feature_engineering import FeatureEngineer, split_features_and_target
from app.datasets.loaders import RealDatasetLoader, sanitize_dataset
from app.datasets.preprocess import DataPipeline, PipelineConfig, save_dataset_layers
from app.datasets.synthetic_generator import (
    SCALE_TIERS,
    SyntheticConfig,
    SyntheticDataGenerator,
)

__all__ = [
    "Allocation",
    "BenchmarkRun",
    "Course",
    "DataPipeline",
    "DatasetBundle",
    "FeatureEngineer",
    "MetricResult",
    "PipelineConfig",
    "Preference",
    "RealDatasetLoader",
    "SCALE_TIERS",
    "Student",
    "SurveyResponse",
    "SyntheticConfig",
    "SyntheticDataGenerator",
    "sanitize_dataset",
    "save_dataset_layers",
    "split_features_and_target",
]

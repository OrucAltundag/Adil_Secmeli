"""Machine-learning algorithms for benchmarking."""

from app.algorithms.ml.baselines import (
    MajorityClassPredictor,
    PopularityRecommender,
    RandomPredictor,
)
from app.algorithms.ml.classifiers import (
    LogisticRegressionPredictor,
    MLPPredictor,
    NaiveBayesPredictor,
    RandomForestPredictor,
    XGBoostLikePredictor,
    build_adaptive_predictor,
)

__all__ = [
    "RandomPredictor",
    "MajorityClassPredictor",
    "PopularityRecommender",
    "NaiveBayesPredictor",
    "LogisticRegressionPredictor",
    "MLPPredictor",
    "RandomForestPredictor",
    "XGBoostLikePredictor",
    "build_adaptive_predictor",
]

"""Machine-learning algorithms for benchmarking."""

from app.algorithms.ml.baselines import (
    MajorityClassPredictor,
    PopularityRecommender,
    RandomPredictor,
)
from app.algorithms.ml.classifiers import (
    LogisticRegressionPredictor,
    NaiveBayesPredictor,
    RandomForestPredictor,
    XGBoostLikePredictor,
)

__all__ = [
    "RandomPredictor",
    "MajorityClassPredictor",
    "PopularityRecommender",
    "NaiveBayesPredictor",
    "LogisticRegressionPredictor",
    "RandomForestPredictor",
    "XGBoostLikePredictor",
]

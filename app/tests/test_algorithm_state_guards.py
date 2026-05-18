import pandas as pd
import pytest

from app.algorithms.mcdm.promethee import PROMETHEERanker
from app.algorithms.mcdm.topsis import TOPSISRanker
from app.algorithms.mcdm.vikor import VIKORRanker
from app.algorithms.ml.baselines import (
    MajorityClassPredictor,
    PopularityRecommender,
    RandomPredictor,
)


def _two_criteria_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "item_id": [1, 2],
            "success": [0.8, 0.6],
            "demand": [0.3, 0.7],
        }
    )


def _three_criteria_frame() -> pd.DataFrame:
    df = _two_criteria_frame()
    df["capacity"] = [40, 50]
    return df


@pytest.mark.parametrize("ranker_cls", [TOPSISRanker, VIKORRanker, PROMETHEERanker])
def test_mcdm_weight_length_checked_on_fit(ranker_cls):
    ranker = ranker_cls(weights=[0.5])

    with pytest.raises(ValueError, match="Weight length mismatch"):
        ranker.fit(_two_criteria_frame())


@pytest.mark.parametrize("ranker_cls", [TOPSISRanker, VIKORRanker, PROMETHEERanker])
def test_mcdm_weight_length_checked_after_fit_when_input_shape_changes(ranker_cls):
    ranker = ranker_cls(weights=[0.5, 0.5]).fit(_two_criteria_frame())

    with pytest.raises(ValueError, match="Weight length mismatch"):
        ranker.rank(_three_criteria_frame())


@pytest.mark.parametrize(
    "model",
    [
        RandomPredictor(classes=[0, 1]),
        MajorityClassPredictor(),
        PopularityRecommender(),
    ],
)
def test_baseline_models_reject_predict_before_fit(model):
    with pytest.raises(ValueError, match="Model not fitted"):
        model.predict(pd.DataFrame({"x": [1, 2]}))


def test_baseline_models_set_is_fitted_after_fit():
    X = pd.DataFrame({"course_id": [10, 10, 20]})
    y = pd.Series([1, 1, 0])

    random_model = RandomPredictor(classes=[0, 1]).fit(X, y)
    majority_model = MajorityClassPredictor().fit(X, y)
    popularity_model = PopularityRecommender().fit(X)

    assert random_model.is_fitted is True
    assert majority_model.is_fitted is True
    assert popularity_model.is_fitted is True

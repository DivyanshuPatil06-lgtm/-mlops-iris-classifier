# tests/test_training_pipeline.py
"""
Smoke tests confirming the training pipeline runs end-to-end on a
small synthetic dataset and produces a well-formed model object.
"""
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

FEATURE_COLS = [
    "sepal length (cm)", "sepal width (cm)",
    "petal length (cm)", "petal width (cm)",
]


@pytest.fixture
def synthetic_dataset():
    rng = np.random.default_rng(42)
    n = 30
    X = pd.DataFrame(rng.normal(5, 1, size=(n, 4)), columns=FEATURE_COLS)
    y = rng.integers(0, 3, size=n)
    return X, y


def test_model_trains_without_error(synthetic_dataset):
    X, y = synthetic_dataset
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)  # should not raise
    assert hasattr(model, "predict")


def test_model_predict_output_shape(synthetic_dataset):
    X, y = synthetic_dataset
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    preds = model.predict(X)
    assert preds.shape == (len(X),)


def test_model_predict_proba_sums_to_one(synthetic_dataset):
    X, y = synthetic_dataset
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    probs = model.predict_proba(X)
    row_sums = probs.sum(axis=1)
    assert np.allclose(row_sums, 1.0, atol=1e-6)
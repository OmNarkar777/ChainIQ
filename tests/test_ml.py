"""
Basic smoke tests for ML pipeline.
Run: pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np


def test_feature_engineering_shape():
    from backend.data.generator import generate_skus, generate_sales
    from backend.ml.feature_engineering import engineer_features
    skus = generate_skus()
    sales = generate_sales(skus.head(3))
    X, y = engineer_features(sales)
    assert X.shape[0] == y.shape[0]
    assert X.shape[1] >= 20
    assert not X.isnull().all().any(), "Some feature columns are all NaN"


def test_feature_names_consistent():
    from backend.ml.feature_engineering import get_feature_names, engineer_features
    from backend.data.generator import generate_skus, generate_sales
    skus = generate_skus()
    sales = generate_sales(skus.head(2))
    X, _ = engineer_features(sales)
    expected = set(get_feature_names())
    actual = set(X.columns)
    assert expected == actual, f"Feature mismatch: {expected.symmetric_difference(actual)}"


def test_inventory_recommendation_logic():
    from backend.agents.inventory_agent import compute_inventory_recommendation
    forecast = {"predicted_units": 70, "upper_bound": 85}
    sku_meta = {
        "current_stock": 20,
        "lead_time_days": 7,
        "unit_cost": 100,
        "rolling_std_7": 10,
        "sku_name": "TEST_SKU",
    }
    rec = compute_inventory_recommendation("SKU_TEST", forecast, sku_meta)
    assert rec["reorder_urgency"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert rec["recommended_order_qty"] >= 0
    assert 0 <= rec["stockout_risk_pct"] <= 100


def test_naive_baseline():
    """XGBoost must beat naive by >= 20% — validated in trainer."""
    # This test just checks the mape utility function
    from backend.ml.trainer import mape
    y_true = np.array([100, 200, 150, 80])
    y_pred = np.array([110, 190, 160, 75])
    result = mape(y_true, y_pred)
    assert 0 < result < 20


def test_prediction_result_dataclass():
    from backend.ml.predictor import PredictionResult
    r = PredictionResult(
        sku_id="SKU_0001",
        predicted_units=142.5,
        lower_bound=120.0,
        upper_bound=165.0,
        confidence_pct=80.0,
        horizon_days=7,
        model_version="1",
    )
    assert r.lower_bound < r.predicted_units < r.upper_bound

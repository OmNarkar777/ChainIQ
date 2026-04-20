# ChainIQ_FixFeatures.ps1
# Run from ChainIQ folder:
#   .\.venv\Scripts\Activate.ps1
#   .\ChainIQ_FixFeatures.ps1

$path = "backend\ml\feature_engineering.py"
[System.IO.File]::WriteAllText(
  (Join-Path (Get-Location) $path),
  @'
"""
Feature engineering for XGBoost demand forecasting.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def engineer_features(
    df: pd.DataFrame,
    target_horizon: int = 7
) -> Tuple[pd.DataFrame, pd.Series]:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["sku_id", "date"]).reset_index(drop=True)

    # Target: sum of next horizon days of units_sold
    df["target"] = (
        df.groupby("sku_id")["units_sold"]
        .transform(lambda x: x.shift(-1).rolling(window=target_horizon).sum().shift(-(target_horizon - 1)))
    )

    # Lag features
    for lag in [1, 7, 14, 28]:
        df[f"lag_{lag}"] = df.groupby("sku_id")["units_sold"].transform(lambda x: x.shift(lag))

    # Rolling stats — using transform with explicit lambda (fixes the bug)
    for window in [7, 14]:
        df[f"rolling_mean_{window}"] = df.groupby("sku_id")["units_sold"].transform(
            lambda x, w=window: x.shift(1).rolling(w, min_periods=1).mean()
        )
        df[f"rolling_std_{window}"] = df.groupby("sku_id")["units_sold"].transform(
            lambda x, w=window: x.shift(1).rolling(w, min_periods=1).std().fillna(0)
        )

    # Exponential weighted mean
    df["ewm_7"] = df.groupby("sku_id")["units_sold"].transform(
        lambda x: x.shift(1).ewm(span=7, min_periods=1).mean()
    )

    # Calendar features
    df["day_of_week"]    = df["date"].dt.dayofweek
    df["day_of_month"]   = df["date"].dt.day
    df["month"]          = df["date"].dt.month
    df["week_of_year"]   = df["date"].dt.isocalendar().week.astype(int)
    df["is_weekend"]     = (df["day_of_week"] >= 5).astype(int)
    df["quarter"]        = df["date"].dt.quarter
    df["is_month_start"] = df["date"].dt.is_month_start.astype(int)
    df["is_month_end"]   = df["date"].dt.is_month_end.astype(int)

    # Boolean flags
    df["is_holiday"]     = df["holiday_flag"].astype(int)
    df["is_promotional"] = df["promotional_flag"].astype(int)

    # Inventory features
    df["stock_to_reorder_ratio"] = (
        df["stock_level"] / (df["reorder_point"].replace(0, 1))
    ).clip(0, 10)
    df["days_of_supply"] = (
        df["stock_level"] / (df["rolling_mean_7"].replace(0, 1))
    ).clip(0, 90)

    # Categorical encodings
    le_cat = LabelEncoder()
    le_sup = LabelEncoder()
    df["category_encoded"] = le_cat.fit_transform(df["category"].astype(str))
    df["supplier_encoded"]  = le_sup.fit_transform(df["supplier_id"].astype(str))

    # Price feature
    df["log_unit_price"] = np.log1p(df["unit_price"])

    feature_cols = get_feature_names()
    df_clean = df.dropna(subset=feature_cols + ["target"])
    X = df_clean[feature_cols].reset_index(drop=True)
    y = df_clean["target"].reset_index(drop=True)

    logger.info(f"Feature matrix: {X.shape}, target: {y.shape}")
    return X, y


def get_feature_names() -> list:
    return [
        "lag_1", "lag_7", "lag_14", "lag_28",
        "rolling_mean_7", "rolling_mean_14",
        "rolling_std_7", "rolling_std_14",
        "ewm_7",
        "day_of_week", "day_of_month", "month",
        "week_of_year", "is_weekend", "quarter",
        "is_month_start", "is_month_end",
        "is_holiday", "is_promotional",
        "category_encoded", "supplier_encoded",
        "log_unit_price", "lead_time_days",
        "stock_to_reorder_ratio", "days_of_supply",
    ]
'@,
  [System.Text.UTF8Encoding]::new($false)
)
Write-Host "  [OK] Fixed: backend\ml\feature_engineering.py" -ForegroundColor Green
Write-Host ""
Write-Host "  Now run:" -ForegroundColor Yellow
Write-Host "    python ml_training\train.py --generate" -ForegroundColor White

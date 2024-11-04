"""
XGBoost training pipeline with time-series cross-validation.
Run via:  python ml_training/train.py
"""

import json
import time
import logging
from pathlib import Path
from typing import Tuple, Dict

import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.ml.feature_engineering import engineer_features

logger = logging.getLogger(__name__)

# ── XGBoost hyper-parameters ─────────────────────────────────
XGB_PARAMS = dict(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    eval_metric="rmse",
    random_state=42,
    n_jobs=-1,
)


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 1e-6
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def naive_forecast(X_test: pd.DataFrame) -> np.ndarray:
    """Baseline: rolling_mean_7 as the forecast."""
    return X_test["rolling_mean_7"].values * 7  # scale to 7-day horizon


def train(
    data_path: str = "backend/data/sample_data.csv",
    model_store_dir: str = "model_store",
    target_horizon: int = 7,
    test_days: int = 30,
) -> Tuple[xgb.XGBRegressor, Dict]:
    start = time.time()
    print("\n" + "=" * 60)
    print("  ChainIQ — XGBoost Training Pipeline")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────
    df = pd.read_csv(data_path, parse_dates=["date"])
    print(f"[data]  Loaded {len(df):,} rows, {df['sku_id'].nunique()} SKUs")

    X, y = engineer_features(df, target_horizon=target_horizon)
    print(f"[feat]  Feature matrix: {X.shape}")

    # ── Time-series split (last test_days days as held-out) ───
    df_indexed = df.copy()
    df_indexed["date"] = pd.to_datetime(df_indexed["date"])
    cutoff = df_indexed["date"].max() - pd.Timedelta(days=test_days)

    # Use positional indices aligned with X (after dropna)
    df_clean = df.copy()
    df_clean["date"] = pd.to_datetime(df_clean["date"])
    from backend.ml.feature_engineering import get_feature_names
    feature_cols = get_feature_names()
    df_clean["target"] = (
        df_clean.groupby("sku_id")["units_sold"]
        .transform(lambda x: x.shift(-1).rolling(window=target_horizon).sum().shift(-(target_horizon - 1)))
    )
    # Rebuild full df after feature engineering to get the dates
    full_df = df_clean.dropna(subset=feature_cols + ["target"])
    full_df = full_df.reset_index(drop=True)

    train_mask = pd.to_datetime(full_df["date"]) <= cutoff
    X_train, y_train = X[train_mask], y[train_mask]
    X_test,  y_test  = X[~train_mask], y[~train_mask]

    print(f"[split] Train: {len(X_train):,} | Test (last {test_days}d): {len(X_test):,}")

    # ── TimeSeriesSplit CV ────────────────────────────────────
    tscv = TimeSeriesSplit(n_splits=5)
    cv_mapes = []
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        Xtr, Xval = X_train.iloc[tr_idx], X_train.iloc[val_idx]
        ytr, yval = y_train.iloc[tr_idx], y_train.iloc[val_idx]
        m = xgb.XGBRegressor(**XGB_PARAMS, early_stopping_rounds=50)
        m.fit(Xtr, ytr, eval_set=[(Xval, yval)], verbose=False)
        preds = m.predict(Xval)
        fold_mape = mape(yval.values, preds)
        cv_mapes.append(fold_mape)
        print(f"  CV Fold {fold+1}: MAPE = {fold_mape:.2f}%")

    print(f"[cv]    Mean CV MAPE: {np.mean(cv_mapes):.2f}% ± {np.std(cv_mapes):.2f}%")

    # ── Final model training ──────────────────────────────────
    final_model = xgb.XGBRegressor(**XGB_PARAMS, early_stopping_rounds=50)
    final_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=100,
    )

    # ── Evaluation ────────────────────────────────────────────
    y_pred_xgb   = final_model.predict(X_test)
    y_pred_naive = naive_forecast(X_test)

    xgb_mape  = mape(y_test.values, y_pred_xgb)
    xgb_rmse  = rmse(y_test.values, y_pred_xgb)
    xgb_mae   = mean_absolute_error(y_test.values, y_pred_xgb)

    naive_mape = mape(y_test.values, y_pred_naive)
    naive_rmse = rmse(y_test.values, y_pred_naive)

    improvement_pct = (naive_mape - xgb_mape) / naive_mape * 100

    print("\n" + "-" * 50)
    print(f"{'Metric':<20} {'XGBoost':>12} {'Naive Baseline':>16}")
    print("-" * 50)
    print(f"{'MAPE':<20} {xgb_mape:>11.2f}% {naive_mape:>15.2f}%")
    print(f"{'RMSE':<20} {xgb_rmse:>12.2f} {naive_rmse:>16.2f}")
    print(f"{'MAE':<20} {xgb_mae:>12.2f}")
    print("-" * 50)
    print(f"  XGBoost beats naive by {improvement_pct:.1f}%")
    if improvement_pct >= 20:
        print("  ✓ Meets 20%+ improvement threshold")
    else:
        print("  ✗ Below 20% threshold — consider tuning")
    print("-" * 50)

    # ── Per-SKU metrics (sample) ──────────────────────────────
    sku_ids_test = full_df[~train_mask]["sku_id"].reset_index(drop=True)
    per_sku = pd.DataFrame({
        "sku_id": sku_ids_test,
        "actual": y_test.values,
        "predicted": y_pred_xgb,
    })
    per_sku_metrics = per_sku.groupby("sku_id").apply(
        lambda g: pd.Series({
            "mape": mape(g["actual"].values, g["predicted"].values),
            "rmse": rmse(g["actual"].values, g["predicted"].values),
        })
    ).reset_index()
    print(f"\n[per-sku] Top 5 worst MAPE SKUs:")
    print(per_sku_metrics.nlargest(5, "mape").to_string(index=False))

    # ── Feature importance plot ───────────────────────────────
    store_path = Path(model_store_dir)
    store_path.mkdir(exist_ok=True)

    fi = pd.DataFrame({
        "feature": X_train.columns,
        "importance": final_model.feature_importances_,
    }).sort_values("importance", ascending=False)

    plt.figure(figsize=(10, 8))
    plt.barh(fi["feature"][:15][::-1], fi["importance"][:15][::-1], color="#2196F3")
    plt.xlabel("Feature Importance (gain)")
    plt.title("ChainIQ XGBoost — Top 15 Feature Importances")
    plt.tight_layout()
    fi_path = store_path / "feature_importance.png"
    plt.savefig(fi_path, dpi=150)
    plt.close()
    print(f"[plot]  Saved feature importance → {fi_path}")

    # ── Save model ────────────────────────────────────────────
    existing = sorted(store_path.glob("xgb_v*.json"))
    version = len(existing) + 1
    model_path = store_path / f"xgb_v{version}.json"
    final_model.save_model(str(model_path))

    meta = {
        "version": version,
        "model_path": str(model_path),
        "target_horizon": target_horizon,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "xgb_mape": round(xgb_mape, 4),
        "xgb_rmse": round(xgb_rmse, 4),
        "xgb_mae": round(xgb_mae, 4),
        "naive_mape": round(naive_mape, 4),
        "improvement_pct": round(improvement_pct, 2),
        "cv_mean_mape": round(float(np.mean(cv_mapes)), 4),
        "cv_std_mape": round(float(np.std(cv_mapes)), 4),
        "feature_names": list(X_train.columns),
        "training_time_sec": round(time.time() - start, 1),
    }
    meta_path = store_path / f"xgb_v{version}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    print(f"\n[save]  Model → {model_path}")
    print(f"[save]  Meta  → {meta_path}")
    print(f"\n[done]  Training completed in {meta['training_time_sec']}s")
    print("=" * 60 + "\n")

    return final_model, meta

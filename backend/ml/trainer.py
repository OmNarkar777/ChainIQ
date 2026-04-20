"""
XGBoost training pipeline with time-series cross-validation.
"""
import json, time, logging
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
from backend.ml.feature_engineering import engineer_features, get_feature_names

logger = logging.getLogger(__name__)

XGB_PARAMS = dict(
    n_estimators=500, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    objective="reg:squarederror", eval_metric="rmse",
    random_state=42, n_jobs=-1,
)

def mape(y_true, y_pred):
    yt, yp = np.array(y_true), np.array(y_pred)
    mask = yt > 1e-6
    if mask.sum() == 0: return 0.0
    return float(np.mean(np.abs((yt[mask] - yp[mask]) / yt[mask])) * 100)

def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))

def naive_forecast(X_test):
    return X_test["rolling_mean_7"].values * 7

def train(data_path="backend/data/sample_data.csv", model_store_dir="model_store",
          target_horizon=7, test_days=30):
    start = time.time()
    print("\n" + "="*60)
    print("  ChainIQ - XGBoost Training Pipeline")
    print("="*60)

    df = pd.read_csv(data_path, parse_dates=["date"])
    print(f"[data]  Loaded {len(df):,} rows, {df['sku_id'].nunique()} SKUs")

    # Sort df the same way engineer_features does — to align indices
    df_sorted = df.copy()
    df_sorted["date"] = pd.to_datetime(df_sorted["date"])
    df_sorted = df_sorted.sort_values(["sku_id","date"]).reset_index(drop=True)

    # Engineer features — dropna happens inside, returns reset-indexed X, y
    X, y = engineer_features(df, target_horizon=target_horizon)
    print(f"[feat]  Feature matrix: {X.shape}")

    # To get dates aligned with X, recompute target on sorted df,
    # drop same NaN rows, extract the date column
    df_sorted["_target_tmp"] = (
        df_sorted.groupby("sku_id")["units_sold"]
        .transform(lambda x: x.shift(-1).rolling(window=target_horizon).sum().shift(-(target_horizon-1)))
    )
    # Also compute lag_1 to match the same dropna mask as engineer_features
    df_sorted["_lag1_tmp"] = df_sorted.groupby("sku_id")["units_sold"].transform(lambda x: x.shift(1))

    df_aligned = df_sorted.dropna(subset=["_target_tmp", "_lag1_tmp"]).reset_index(drop=True)

    # Trim to same length as X in case of minor differences
    min_len = min(len(X), len(df_aligned))
    X        = X.iloc[:min_len].reset_index(drop=True)
    y        = y.iloc[:min_len].reset_index(drop=True)
    df_aligned = df_aligned.iloc[:min_len].reset_index(drop=True)

    # Time split based on date
    cutoff   = df_sorted["date"].max() - pd.Timedelta(days=test_days)
    mask     = df_aligned["date"] <= cutoff

    X_train, y_train = X[mask].reset_index(drop=True), y[mask].reset_index(drop=True)
    X_test,  y_test  = X[~mask].reset_index(drop=True), y[~mask].reset_index(drop=True)
    print(f"[split] Train: {len(X_train):,} | Test (last {test_days}d): {len(X_test):,}")

    if len(X_test) == 0:
        print("[WARN] No test rows — using last 20% of train as test")
        split = int(len(X_train) * 0.8)
        X_test,  y_test  = X_train.iloc[split:], y_train.iloc[split:]
        X_train, y_train = X_train.iloc[:split], y_train.iloc[:split]

    # TimeSeriesSplit CV
    tscv     = TimeSeriesSplit(n_splits=5)
    cv_mapes = []
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        Xtr, Xval = X_train.iloc[tr_idx], X_train.iloc[val_idx]
        ytr, yval = y_train.iloc[tr_idx], y_train.iloc[val_idx]
        m = xgb.XGBRegressor(**XGB_PARAMS, early_stopping_rounds=50)
        m.fit(Xtr, ytr, eval_set=[(Xval, yval)], verbose=False)
        fold_mape = mape(yval.values, m.predict(Xval))
        cv_mapes.append(fold_mape)
        print(f"  CV Fold {fold+1}: MAPE = {fold_mape:.2f}%")
    print(f"[cv]    Mean CV MAPE: {np.mean(cv_mapes):.2f}% +/- {np.std(cv_mapes):.2f}%")

    # Final model
    final_model = xgb.XGBRegressor(**XGB_PARAMS, early_stopping_rounds=50)
    final_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=100)

    # Evaluation
    y_pred_xgb   = final_model.predict(X_test)
    y_pred_naive = naive_forecast(X_test)
    xgb_mape  = mape(y_test.values, y_pred_xgb)
    xgb_rmse  = rmse(y_test.values, y_pred_xgb)
    xgb_mae   = mean_absolute_error(y_test.values, y_pred_xgb)
    naive_mape = mape(y_test.values, y_pred_naive)
    naive_rmse = rmse(y_test.values, y_pred_naive)
    improvement = (naive_mape - xgb_mape) / max(naive_mape, 1e-6) * 100

    print("\n" + "-"*50)
    print(f"{'Metric':<20} {'XGBoost':>12} {'Naive Baseline':>16}")
    print("-"*50)
    print(f"{'MAPE':<20} {xgb_mape:>11.2f}% {naive_mape:>15.2f}%")
    print(f"{'RMSE':<20} {xgb_rmse:>12.2f} {naive_rmse:>16.2f}")
    print(f"{'MAE':<20} {xgb_mae:>12.2f}")
    print("-"*50)
    print(f"  XGBoost beats naive by {improvement:.1f}%")
    print("[PASS]" if improvement >= 20 else "[WARN]", "20%+ threshold")
    print("-"*50)

    # Feature importance plot
    store_path = Path(model_store_dir)
    store_path.mkdir(exist_ok=True)
    fi = pd.DataFrame({"feature": X_train.columns, "importance": final_model.feature_importances_})
    fi = fi.sort_values("importance", ascending=False)
    plt.figure(figsize=(10,8))
    plt.barh(fi["feature"][:15][::-1], fi["importance"][:15][::-1], color="#2196F3")
    plt.xlabel("Feature Importance (gain)")
    plt.title("ChainIQ XGBoost - Top 15 Feature Importances")
    plt.tight_layout()
    fi_path = store_path / "feature_importance.png"
    plt.savefig(fi_path, dpi=150)
    plt.close()
    print(f"[plot]  Saved -> {fi_path}")

    existing   = [m for m in sorted(store_path.glob("xgb_v*.json")) if "_meta" not in m.name]
    version    = len(existing) + 1
    model_path = store_path / f"xgb_v{version}.json"
    final_model.save_model(str(model_path))

    meta = {
        "version": version, "model_path": str(model_path),
        "target_horizon": target_horizon,
        "train_rows": len(X_train), "test_rows": len(X_test),
        "xgb_mape": round(xgb_mape,4), "xgb_rmse": round(xgb_rmse,4),
        "xgb_mae":  round(xgb_mae,4),  "naive_mape": round(naive_mape,4),
        "improvement_pct": round(improvement,2),
        "cv_mean_mape": round(float(np.mean(cv_mapes)),4),
        "cv_std_mape":  round(float(np.std(cv_mapes)),4),
        "feature_names": list(X_train.columns),
        "training_time_sec": round(time.time()-start,1),
    }
    (store_path / f"xgb_v{version}_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"\n[save]  Model -> {model_path}")
    print(f"[done]  Completed in {meta['training_time_sec']}s")
    print("="*60 + "\n")
    return final_model, meta
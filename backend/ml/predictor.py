"""
Inference engine: load trained XGBoost and produce 7-day demand forecasts
with confidence intervals via bootstrap noise injection.

Two-level cache:
  _feature_row_cache  — stores X_latest (25-feature row) per SKU.
                        Eliminates pandas feature engineering on cache misses.
  _prediction_cache   — stores full PredictionResult per SKU.
                        Cache hits cost ~0 μs (dict lookup only).

Both caches live for the process lifetime (model + data are static).
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb

from backend.ml.model_store import load_model, load_meta, get_latest_version
from backend.ml.feature_engineering import engineer_features

logger = logging.getLogger(__name__)

# ── Module-level caches ───────────────────────────────────────────────────────
_prediction_cache:  dict[str, "PredictionResult"] = {}
_feature_row_cache: dict[str, pd.DataFrame]        = {}  # sku_id → X.iloc[[-1]]

_cache_hits:   int = 0
_cache_misses: int = 0


def get_cache_stats() -> dict:
    total = _cache_hits + _cache_misses
    return {
        "prediction_cache_size":     len(_prediction_cache),
        "prediction_cache_hits":     _cache_hits,
        "prediction_cache_misses":   _cache_misses,
        "prediction_cache_hit_rate": round(_cache_hits / total * 100, 1) if total > 0 else 0.0,
        "feature_row_cache_size":    len(_feature_row_cache),
    }


def clear_prediction_cache() -> None:
    global _cache_hits, _cache_misses
    _prediction_cache.clear()
    _feature_row_cache.clear()
    _cache_hits = 0
    _cache_misses = 0


@dataclass
class PredictionResult:
    sku_id:          str
    predicted_units: float
    lower_bound:     float
    upper_bound:     float
    confidence_pct:  float
    horizon_days:    int
    model_version:   str
    top_features:    List[dict] = field(default_factory=list)
    mape_estimate:   Optional[float] = None


class DemandPredictor:
    """
    Production inference class for ChainIQ demand forecasting.

    predict_sku() is O(1) for warmed SKUs (cache hit, dict lookup only).
    Feature engineering only runs on first prediction per SKU.
    """

    def __init__(self, data_path: str = "backend/data/sample_data.csv"):
        self.model:     Optional[xgb.XGBRegressor] = None
        self.version:   Optional[str]               = None
        self.meta:      dict                         = {}
        self.data_path: str                          = data_path
        self._raw_df:   Optional[pd.DataFrame]       = None

    def load_model(self, version: Optional[str] = None) -> None:
        self.model   = load_model(version)
        self.version = version or get_latest_version()
        self.meta    = load_meta(self.version)
        logger.info(f"Loaded XGBoost model v{self.version}")

    def _ensure_data(self) -> None:
        if self._raw_df is None:
            self._raw_df = pd.read_csv(self.data_path, parse_dates=["date"])
            logger.info(f"Loaded {len(self._raw_df):,} rows from {self.data_path}")

    def _get_feature_row(self, sku_id: str) -> pd.DataFrame:
        """Return the latest feature row for a SKU, using per-SKU cache."""
        if sku_id in _feature_row_cache:
            return _feature_row_cache[sku_id]

        self._ensure_data()
        sku_df = self._raw_df[self._raw_df["sku_id"] == sku_id].copy()
        if len(sku_df) == 0:
            raise ValueError(f"SKU not found: {sku_id}")

        X, _ = engineer_features(sku_df, target_horizon=self.meta.get("target_horizon", 7))
        if len(X) == 0:
            raise ValueError(f"No feature rows for SKU {sku_id}")

        row = X.iloc[[-1]].reset_index(drop=True)
        _feature_row_cache[sku_id] = row
        return row

    def _bootstrap_confidence(
        self,
        X_row: pd.DataFrame,
        n_bootstraps: int = 200,
        noise_scale:  float = 0.08,
    ) -> tuple[float, float, float]:
        """80% CI via bootstrap noise injection on feature values."""
        base = X_row.values[0]
        preds = []
        for _ in range(n_bootstraps):
            noise  = np.random.normal(1.0, noise_scale, size=base.shape)
            X_noisy = pd.DataFrame([base * noise], columns=X_row.columns)
            preds.append(max(0.0, float(self.model.predict(X_noisy)[0])))
        preds = np.array(preds)
        return float(np.percentile(preds, 10)), float(np.percentile(preds, 90)), float(np.std(preds))

    def predict_sku(
        self,
        sku_id:       str,
        horizon_days: int = 7,
        n_bootstraps: int = 200,
    ) -> PredictionResult:
        global _cache_hits, _cache_misses

        if self.model is None:
            raise RuntimeError("Call load_model() first")

        # Level 2: full prediction cache (O(1) dict lookup)
        if sku_id in _prediction_cache:
            _cache_hits += 1
            return _prediction_cache[sku_id]

        # Level 1: feature row cache (avoids pandas re-computation)
        X_latest    = self._get_feature_row(sku_id)
        point_pred  = max(0.0, float(self.model.predict(X_latest)[0]))
        lower, upper, _ = self._bootstrap_confidence(X_latest, n_bootstraps=n_bootstraps)

        fi   = self.meta.get("feature_names", list(X_latest.columns))
        imps = self.model.feature_importances_
        top5 = sorted(
            [{"feature": n, "importance": float(v)} for n, v in zip(fi, imps)],
            key=lambda x: x["importance"], reverse=True
        )[:5]

        result = PredictionResult(
            sku_id=sku_id,
            predicted_units=round(point_pred, 2),
            lower_bound=round(lower, 2),
            upper_bound=round(upper, 2),
            confidence_pct=80.0,
            horizon_days=horizon_days,
            model_version=str(self.version),
            top_features=top5,
            mape_estimate=self.meta.get("xgb_mape"),
        )

        _prediction_cache[sku_id] = result
        _cache_misses += 1
        return result

    def predict_batch(self, sku_ids: List[str]) -> List[PredictionResult]:
        results = []
        for sku_id in sku_ids:
            try:
                results.append(self.predict_sku(sku_id))
            except Exception as e:
                logger.warning(f"Failed to predict {sku_id}: {e}")
        return results

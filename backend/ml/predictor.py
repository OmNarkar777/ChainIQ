"""
Inference engine: load trained XGBoost and produce
demand forecasts with confidence intervals via bootstrap sampling.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from backend.ml.model_store import load_model, load_meta, get_latest_version
from backend.ml.feature_engineering import engineer_features

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    sku_id: str
    predicted_units: float
    lower_bound: float
    upper_bound: float
    confidence_pct: float
    horizon_days: int
    model_version: str
    top_features: List[dict] = field(default_factory=list)
    mape_estimate: Optional[float] = None


class DemandPredictor:
    """
    Production-grade inference class for ChainIQ demand forecasting.

    Usage:
        predictor = DemandPredictor()
        predictor.load_model()
        result = predictor.predict_sku("SKU_0001", horizon_days=7)
    """

    def __init__(self, data_path: str = "backend/data/sample_data.csv"):
        self.model: Optional[xgb.XGBRegressor] = None
        self.version: Optional[str] = None
        self.meta: dict = {}
        self.data_path = data_path
        self._raw_df: Optional[pd.DataFrame] = None
        self._feature_df: Optional[pd.DataFrame] = None

    def load_model(self, version: Optional[str] = None) -> None:
        self.model = load_model(version)
        self.version = version or get_latest_version()
        self.meta = load_meta(self.version)
        logger.info(f"Loaded model v{self.version}")

    def _ensure_data(self) -> None:
        if self._raw_df is None:
            self._raw_df = pd.read_csv(self.data_path, parse_dates=["date"])
            logger.info(f"Loaded {len(self._raw_df):,} rows from {self.data_path}")

    def _get_sku_features(self, sku_id: str) -> pd.DataFrame:
        """Return latest feature row for a SKU."""
        self._ensure_data()
        sku_df = self._raw_df[self._raw_df["sku_id"] == sku_id].copy()
        if len(sku_df) == 0:
            raise ValueError(f"SKU not found: {sku_id}")
        X, _ = engineer_features(sku_df, target_horizon=self.meta.get("target_horizon", 7))
        return X

    def _bootstrap_confidence(
        self,
        X_row: pd.DataFrame,
        n_bootstraps: int = 200,
        noise_scale: float = 0.08,
    ) -> tuple[float, float, float]:
        """
        Estimate confidence interval via bootstrap noise injection.
        Adds small Gaussian noise to features, re-predicts n times,
        uses 10th/90th percentile as 80% CI.
        """
        preds = []
        base_values = X_row.values[0]
        for _ in range(n_bootstraps):
            noise = np.random.normal(1.0, noise_scale, size=base_values.shape)
            X_noisy = pd.DataFrame([base_values * noise], columns=X_row.columns)
            pred = float(self.model.predict(X_noisy)[0])
            preds.append(max(0, pred))
        preds = np.array(preds)
        return float(np.percentile(preds, 10)), float(np.percentile(preds, 90)), float(np.std(preds))

    def predict_sku(
        self,
        sku_id: str,
        horizon_days: int = 7,
    ) -> PredictionResult:
        if self.model is None:
            raise RuntimeError("Call load_model() first")

        X = self._get_sku_features(sku_id)
        if len(X) == 0:
            raise ValueError(f"No feature rows for SKU {sku_id}")

        X_latest = X.iloc[[-1]]
        point_pred = float(self.model.predict(X_latest)[0])
        point_pred = max(0, point_pred)

        lower, upper, std = self._bootstrap_confidence(X_latest)

        # Top-5 feature contributions
        fi = self.meta.get("feature_names", list(X_latest.columns))
        importances = self.model.feature_importances_
        top5 = sorted(
            [{"feature": n, "importance": float(v)} for n, v in zip(fi, importances)],
            key=lambda x: x["importance"],
            reverse=True
        )[:5]

        # Rough MAPE estimate from training meta
        mape_est = self.meta.get("xgb_mape")

        return PredictionResult(
            sku_id=sku_id,
            predicted_units=round(point_pred, 2),
            lower_bound=round(lower, 2),
            upper_bound=round(upper, 2),
            confidence_pct=80.0,
            horizon_days=horizon_days,
            model_version=str(self.version),
            top_features=top5,
            mape_estimate=mape_est,
        )

    def predict_batch(self, sku_ids: List[str]) -> List[PredictionResult]:
        results = []
        for sku_id in sku_ids:
            try:
                results.append(self.predict_sku(sku_id))
            except Exception as e:
                logger.warning(f"Failed to predict {sku_id}: {e}")
        return results

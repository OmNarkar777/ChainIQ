"""
Forecasting agent: calls XGBoost predictor for each SKU in state.
"""

import logging
from typing import Any, Dict
from backend.agents.state import ChainIQState
from backend.ml.predictor import DemandPredictor

logger = logging.getLogger(__name__)
_predictor: DemandPredictor | None = None


def get_predictor() -> DemandPredictor:
    global _predictor
    if _predictor is None:
        _predictor = DemandPredictor()
        _predictor.load_model()
    return _predictor


def forecasting_agent(state: ChainIQState) -> ChainIQState:
    """LangGraph node: produce demand forecasts for all SKUs."""
    logger.info(f"[ForecastAgent] run_id={state['run_id']} skus={len(state['sku_ids'])}")
    try:
        predictor = get_predictor()
        results = []
        for sku_id in state["sku_ids"]:
            try:
                r = predictor.predict_sku(sku_id)
                results.append({
                    "sku_id": r.sku_id,
                    "predicted_units": r.predicted_units,
                    "lower_bound": r.lower_bound,
                    "upper_bound": r.upper_bound,
                    "confidence_pct": r.confidence_pct,
                    "horizon_days": r.horizon_days,
                    "model_version": r.model_version,
                    "top_features": r.top_features,
                    "mape_estimate": r.mape_estimate,
                })
            except Exception as e:
                logger.warning(f"  SKU {sku_id} forecast failed: {e}")
                state["errors"].append(f"Forecast failed for {sku_id}: {str(e)}")

        return {**state, "forecast_results": results, "forecast_error": None}
    except Exception as e:
        logger.error(f"[ForecastAgent] fatal error: {e}")
        return {**state, "forecast_results": [], "forecast_error": str(e)}

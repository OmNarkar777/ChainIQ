"""
Forecasting agent: calls XGBoost predictor for each SKU in state.
Reuses the singleton from the forecast router to avoid loading the
model twice in memory.
"""
import logging
from backend.agents.state import ChainIQState

logger = logging.getLogger(__name__)


def _get_predictor():
    from backend.routers.forecast import get_predictor
    return get_predictor()


def forecasting_agent(state: ChainIQState) -> ChainIQState:
    """LangGraph node: produce demand forecasts for all SKUs."""
    logger.info(f"[ForecastAgent] run_id={state['run_id']} skus={len(state['sku_ids'])}")
    try:
        predictor = _get_predictor()
        results = []
        for sku_id in state["sku_ids"]:
            try:
                r = predictor.predict_sku(sku_id)
                results.append({
                    "sku_id":          r.sku_id,
                    "predicted_units": r.predicted_units,
                    "lower_bound":     r.lower_bound,
                    "upper_bound":     r.upper_bound,
                    "confidence_pct":  r.confidence_pct,
                    "horizon_days":    r.horizon_days,
                    "model_version":   r.model_version,
                    "top_features":    r.top_features,
                    "mape_estimate":   r.mape_estimate,
                })
            except Exception as e:
                logger.warning(f"  SKU {sku_id} forecast failed: {e}")
                state["errors"].append(f"Forecast failed for {sku_id}: {str(e)}")

        return {**state, "forecast_results": results, "forecast_error": None}
    except Exception as e:
        logger.error(f"[ForecastAgent] fatal error: {e}")
        return {**state, "forecast_results": [], "forecast_error": str(e)}

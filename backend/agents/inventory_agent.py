"""
Inventory agent: compute reorder quantities, safety stock,
stockout risk, and urgency classification.

Business logic:
  safety_stock    = Z * sigma_d * sqrt(lead_time)
  reorder_point   = avg_demand * lead_time + safety_stock
  order_qty (EOQ) = sqrt(2 * D * S / H)
  days_until_stockout = current_stock / avg_daily_demand
"""

import logging
import math
import pandas as pd
from typing import Any, Dict, List
from backend.agents.state import ChainIQState

logger = logging.getLogger(__name__)

SERVICE_LEVEL_Z = 1.645  # 95% service level


def _classify_urgency(days_until_stockout: float, lead_time: int) -> str:
    if days_until_stockout <= lead_time * 0.5:
        return "CRITICAL"
    elif days_until_stockout <= lead_time:
        return "HIGH"
    elif days_until_stockout <= lead_time * 2:
        return "MEDIUM"
    return "LOW"


def _stockout_risk(days_until_stockout: float, lead_time: int) -> float:
    """Probability of stockout during lead time (simple sigmoid)."""
    ratio = days_until_stockout / max(lead_time, 1)
    risk = 1 / (1 + math.exp(2 * (ratio - 1)))
    return round(min(max(risk * 100, 0), 99.9), 1)


def _eoq(annual_demand: float, order_cost: float = 500, holding_cost_pct: float = 0.25, unit_cost: float = 100) -> float:
    """Economic Order Quantity."""
    H = holding_cost_pct * unit_cost
    if H <= 0 or annual_demand <= 0:
        return 0
    return math.sqrt(2 * annual_demand * order_cost / H)


def compute_inventory_recommendation(
    sku_id: str,
    forecast: Dict[str, Any],
    sku_meta: Dict[str, Any],
) -> Dict[str, Any]:
    predicted_7d     = forecast.get("predicted_units", 0)
    upper_7d         = forecast.get("upper_bound", predicted_7d * 1.2)
    current_stock    = sku_meta.get("current_stock", 0)
    lead_time        = sku_meta.get("lead_time_days", 7)
    unit_cost        = sku_meta.get("unit_cost", 100)
    rolling_std      = sku_meta.get("rolling_std_7", predicted_7d * 0.15)

    avg_daily_demand = predicted_7d / 7.0
    sigma_d          = rolling_std / math.sqrt(7) if rolling_std > 0 else avg_daily_demand * 0.2

    # Safety stock (normal demand variability)
    safety_stock     = SERVICE_LEVEL_Z * sigma_d * math.sqrt(lead_time)

    # Reorder point
    reorder_point    = avg_daily_demand * lead_time + safety_stock

    # Days until stockout
    days_until_stockout = current_stock / max(avg_daily_demand, 0.01)

    # How much to order (EOQ aligned)
    annual_demand    = avg_daily_demand * 365
    eoq              = _eoq(annual_demand, unit_cost=unit_cost)
    demand_during_lt = avg_daily_demand * lead_time
    gap              = max(0, reorder_point - current_stock + demand_during_lt)
    order_qty        = max(gap, eoq) if current_stock <= reorder_point else 0

    urgency          = _classify_urgency(days_until_stockout, lead_time)
    risk_pct         = _stockout_risk(days_until_stockout, lead_time)

    return {
        "sku_id":                sku_id,
        "sku_name":              sku_meta.get("sku_name", sku_id),
        "current_stock":         round(current_stock, 1),
        "reorder_point":         round(reorder_point, 1),
        "safety_stock":          round(safety_stock, 1),
        "avg_daily_demand":      round(avg_daily_demand, 2),
        "predicted_demand_7d":   round(predicted_7d, 1),
        "upper_demand_7d":       round(upper_7d, 1),
        "days_until_stockout":   round(days_until_stockout, 1),
        "recommended_order_qty": round(order_qty, 0),
        "reorder_urgency":       urgency,
        "stockout_risk_pct":     risk_pct,
        "lead_time_days":        lead_time,
    }


def inventory_agent(state: ChainIQState) -> ChainIQState:
    """LangGraph node: compute inventory recommendations from forecasts."""
    logger.info(f"[InventoryAgent] processing {len(state['forecast_results'])} forecasts")
    try:
        # Load latest stock data
        import pandas as pd
        df = pd.read_csv("backend/data/sample_data.csv", parse_dates=["date"])
        latest = df.sort_values("date").groupby("sku_id").last().reset_index()
        sku_lookup = latest.set_index("sku_id").to_dict("index")

        recs = []
        for fc in state["forecast_results"]:
            sku_id = fc["sku_id"]
            meta   = sku_lookup.get(sku_id, {})
            meta["sku_name"] = meta.get("sku_name", sku_id)
            rec = compute_inventory_recommendation(sku_id, fc, meta)
            recs.append(rec)

        recs_sorted = sorted(
            recs,
            key=lambda r: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[r["reorder_urgency"]]
        )

        return {
            **state,
            "inventory_recommendations": recs_sorted,
            "inventory_error": None,
            "skus_analyzed": len(recs_sorted),
        }
    except Exception as e:
        logger.error(f"[InventoryAgent] error: {e}")
        return {**state, "inventory_recommendations": [], "inventory_error": str(e)}

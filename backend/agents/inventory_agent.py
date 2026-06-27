"""
Inventory agent: computes EOQ, safety stock, ROP, and urgency for each SKU.
Uses the module-level cached DataFrame from inventory.py to avoid re-reading
the 109 500-row CSV on every analysis run.
"""
import math
import logging

from backend.agents.state import ChainIQState

logger = logging.getLogger(__name__)

Z_95           = 1.65
ORDERING_COST  = 500
HOLDING_COST   = 0.20


# ── Pure inventory-math helpers (also imported by inventory.py) ────────────────

def calc_safety_stock(sigma_daily_demand: float, lead_time_days: int,
                      service_level_z: float = Z_95) -> float:
    if sigma_daily_demand <= 0 or lead_time_days <= 0:
        return 0.0
    return service_level_z * sigma_daily_demand * math.sqrt(lead_time_days)


def calc_reorder_point(avg_daily_demand: float, lead_time_days: int,
                       safety_stock: float) -> float:
    return avg_daily_demand * lead_time_days + safety_stock


def calc_eoq(avg_daily_demand: float, unit_cost: float,
             ordering_cost: float = ORDERING_COST,
             holding_cost_pct: float = HOLDING_COST) -> float:
    annual = avg_daily_demand * 365
    H = holding_cost_pct * max(unit_cost, 1.0)
    if annual <= 0 or H <= 0:
        return 0.0
    return math.sqrt(2 * annual * ordering_cost / H)


def calc_days_until_stockout(current_stock: float,
                             avg_daily_demand: float) -> float:
    if avg_daily_demand <= 0:
        return 365.0
    return min(current_stock / avg_daily_demand, 365.0)


def calc_stockout_risk_pct(days_until_stockout: float,
                           lead_time_days: int) -> float:
    ratio = days_until_stockout / max(lead_time_days, 1)
    risk  = 1.0 / (1.0 + math.exp(2.0 * (ratio - 1.0)))
    return round(min(max(risk * 100.0, 0.0), 99.9), 1)


def classify_urgency(days_until_stockout: float, lead_time_days: int,
                     current_stock: float, reorder_point: float) -> str:
    if days_until_stockout < lead_time_days:
        return "CRITICAL"
    if days_until_stockout < lead_time_days * 1.5:
        return "HIGH"
    if current_stock < reorder_point:
        return "MEDIUM"
    return "LOW"


def calc_recommended_order_qty(eoq: float, reorder_point: float,
                               current_stock: float, urgency: str) -> float:
    gap = max(0.0, reorder_point - current_stock)
    qty = max(eoq, gap)
    if urgency == "CRITICAL":
        qty *= 1.2
    return round(qty, 0)


# ── Per-SKU computation ────────────────────────────────────────────────────────

def compute_inventory_recommendation(sku_id: str, forecast: dict,
                                     sku_meta: dict) -> dict:
    predicted_7d  = forecast.get("predicted_units", 0)
    upper_7d      = forecast.get("upper_bound", predicted_7d * 1.2)
    current_stock = sku_meta.get("stock_level", sku_meta.get("current_stock", 0))
    lead_time     = int(sku_meta.get("lead_time_days", 7))
    unit_cost     = float(sku_meta.get("unit_cost", 100))
    avg_daily     = predicted_7d / 7.0
    std_daily     = float(sku_meta.get("rolling_std_7", avg_daily * 0.2))
    if std_daily <= 0:
        std_daily = avg_daily * 0.2

    ss  = calc_safety_stock(std_daily, lead_time)
    rop = calc_reorder_point(avg_daily, lead_time, ss)
    eoq = calc_eoq(avg_daily, unit_cost)
    dus = calc_days_until_stockout(current_stock, avg_daily)
    srp = calc_stockout_risk_pct(dus, lead_time)
    urg = classify_urgency(dus, lead_time, current_stock, rop)
    qty = calc_recommended_order_qty(eoq, rop, current_stock, urg)

    return {
        # Core fields required by InventoryRecommendationResponse schema
        "sku_id":                sku_id,
        "sku_name":              str(sku_meta.get("sku_name", sku_id)),
        "current_stock":         round(current_stock, 1),
        "reorder_point":         round(rop, 1),
        "recommended_order_qty": qty,
        "reorder_urgency":       urg,
        "stockout_risk_pct":     srp,
        "days_until_stockout":   round(dus, 1),
        "predicted_demand_7d":   round(predicted_7d, 1),
        # Extra fields (passed through to frontend via recommendations)
        "category":              str(sku_meta.get("category", "")),
        "supplier_id":           str(sku_meta.get("supplier_id", "")),
        "warehouse_id":          str(sku_meta.get("warehouse_id", "")),
        "safety_stock":          round(ss, 1),
        "avg_daily_demand":      round(avg_daily, 3),
        "upper_demand_7d":       round(upper_7d, 1),
        "lead_time_days":        lead_time,
        "unit_cost":             round(unit_cost, 2),
    }


# ── LangGraph node ─────────────────────────────────────────────────────────────

def inventory_agent(state: ChainIQState) -> ChainIQState:
    """LangGraph node: compute inventory recommendations for all forecast SKUs."""
    logger.info("[InventoryAgent] processing forecasts")
    try:
        # Use the module-level cached DataFrame (no redundant CSV reads)
        from backend.routers.inventory import _get_df
        df     = _get_df()
        latest = df.sort_values("date").groupby("sku_id").last().reset_index()
        lookup = latest.set_index("sku_id").to_dict("index")

        recs = []
        for fc in state.get("forecast_results", []):
            sku_id = fc["sku_id"]
            meta   = dict(lookup.get(sku_id, {}))
            meta.setdefault("sku_name", sku_id)
            recs.append(compute_inventory_recommendation(sku_id, fc, meta))

        recs.sort(
            key=lambda r: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[r["reorder_urgency"]]
        )
        return {
            **state,
            "inventory_recommendations": recs,
            "inventory_error":           None,
            "skus_analyzed":             len(recs),
        }
    except Exception as e:
        logger.error(f"[InventoryAgent] error: {e}")
        return {**state, "inventory_recommendations": [], "inventory_error": str(e)}

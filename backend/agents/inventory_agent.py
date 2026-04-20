import math, logging, pandas as pd
from typing import Any, Dict, List
from backend.agents.state import ChainIQState

logger = logging.getLogger(__name__)
Z_95 = 1.65
ORDERING_COST = 500
HOLDING_COST_PCT = 0.20

def calc_safety_stock(sigma_daily_demand, lead_time_days, service_level_z=Z_95):
    if sigma_daily_demand <= 0 or lead_time_days <= 0:
        return 0.0
    return service_level_z * sigma_daily_demand * math.sqrt(lead_time_days)

def calc_reorder_point(avg_daily_demand, lead_time_days, safety_stock):
    return (avg_daily_demand * lead_time_days) + safety_stock

def calc_eoq(avg_daily_demand, unit_cost, ordering_cost=ORDERING_COST, holding_cost_pct=HOLDING_COST_PCT):
    annual_demand = avg_daily_demand * 365
    H = holding_cost_pct * max(unit_cost, 1.0)
    if annual_demand <= 0 or H <= 0:
        return 0.0
    return math.sqrt(2 * annual_demand * ordering_cost / H)

def calc_days_until_stockout(current_stock, avg_daily_demand):
    if avg_daily_demand <= 0:
        return 365.0
    return min(current_stock / avg_daily_demand, 365.0)

def calc_stockout_risk_pct(days_until_stockout, lead_time_days):
    ratio = days_until_stockout / max(lead_time_days, 1)
    risk = 1.0 / (1.0 + math.exp(2.0 * (ratio - 1.0)))
    return round(min(max(risk * 100.0, 0.0), 99.9), 1)

def classify_urgency(days_until_stockout, lead_time_days, current_stock, reorder_point):
    if days_until_stockout < lead_time_days:
        return "CRITICAL"
    if days_until_stockout < lead_time_days * 1.5:
        return "HIGH"
    if current_stock < reorder_point:
        return "MEDIUM"
    return "LOW"

def calc_recommended_order_qty(eoq, reorder_point, current_stock, urgency):
    gap = max(0.0, reorder_point - current_stock)
    qty = max(eoq, gap)
    if urgency == "CRITICAL":
        qty *= 1.2
    return round(qty, 0)

def compute_inventory_recommendation(sku_id, forecast, sku_meta):
    predicted_7d = forecast.get("predicted_units", 0)
    upper_7d = forecast.get("upper_bound", predicted_7d * 1.2)
    current_stock = sku_meta.get("current_stock", 0)
    lead_time = sku_meta.get("lead_time_days", 7)
    unit_cost = sku_meta.get("unit_cost", 100)
    avg_daily = predicted_7d / 7.0
    std_daily = sku_meta.get("rolling_std_7", avg_daily * 0.2)
    if std_daily <= 0:
        std_daily = avg_daily * 0.2
    ss = calc_safety_stock(std_daily, lead_time)
    rop = calc_reorder_point(avg_daily, lead_time, ss)
    eoq = calc_eoq(avg_daily, unit_cost)
    dus = calc_days_until_stockout(current_stock, avg_daily)
    srp = calc_stockout_risk_pct(dus, lead_time)
    urg = classify_urgency(dus, lead_time, current_stock, rop)
    qty = calc_recommended_order_qty(eoq, rop, current_stock, urg)
    return {
        "sku_id": sku_id,
        "sku_name": sku_meta.get("sku_name", sku_id),
        "current_stock": round(current_stock, 1),
        "reorder_point": round(rop, 1),
        "safety_stock": round(ss, 1),
        "avg_daily_demand": round(avg_daily, 3),
        "predicted_demand_7d": round(predicted_7d, 1),
        "upper_demand_7d": round(upper_7d, 1),
        "days_until_stockout": round(dus, 1),
        "recommended_order_qty": qty,
        "reorder_urgency": urg,
        "stockout_risk_pct": srp,
        "lead_time_days": lead_time,
    }

def inventory_agent(state):
    logger.info("[InventoryAgent] processing forecasts")
    try:
        df = pd.read_csv("backend/data/sample_data.csv", parse_dates=["date"])
        latest = df.sort_values("date").groupby("sku_id").last().reset_index()
        sku_lookup = latest.set_index("sku_id").to_dict("index")
        recs = []
        for fc in state.get("forecast_results", []):
            sku_id = fc["sku_id"]
            meta = dict(sku_lookup.get(sku_id, {}))
            meta["sku_name"] = meta.get("sku_name", sku_id)
            rec = compute_inventory_recommendation(sku_id, fc, meta)
            recs.append(rec)
        recs.sort(key=lambda r: {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}[r["reorder_urgency"]])
        return {**state, "inventory_recommendations": recs, "inventory_error": None, "skus_analyzed": len(recs)}
    except Exception as e:
        logger.error(f"[InventoryAgent] error: {e}")
        return {**state, "inventory_recommendations": [], "inventory_error": str(e)}

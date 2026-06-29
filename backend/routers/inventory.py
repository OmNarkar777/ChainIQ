"""
Inventory REST endpoints.

Caching architecture:
  _df           — raw 109 500-row DataFrame, loaded once
  _sku_records  — 300 computed inventory records, built once from _df
  _analytics    — dashboard analytics dict, computed once from _df + _sku_records

Every endpoint that reads inventory data hits these in-memory caches.
No pandas computation happens per request after the first warmup.

New endpoints:
  GET /inventory/sku-ids    — lightweight list ({sku_id, category}) for combobox (< 5 KB)
  GET /inventory/dashboard  — single call returning all dashboard data (4-in-1)
"""
from __future__ import annotations

import time
from collections import Counter
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.agents.inventory_agent import (
    calc_days_until_stockout,
    calc_eoq,
    calc_reorder_point,
    calc_safety_stock,
    calc_stockout_risk_pct,
    classify_urgency,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

DATA = "backend/data/sample_data.csv"

_df:        Optional[pd.DataFrame] = None
_sku_records: Optional[list[dict]] = None
_analytics:   Optional[dict]       = None   # computed once, never recalculated


# ── Singletons ────────────────────────────────────────────────────────────────

def _get_df() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_csv(DATA, parse_dates=["date"])
    return _df


def _build_sku_records() -> list[dict]:
    df     = _get_df()
    latest = df.sort_values("date").groupby("sku_id").last().reset_index()

    cutoff = df["date"].max() - pd.Timedelta(days=30)
    stats  = (
        df[df["date"] >= cutoff]
        .groupby("sku_id")["units_sold"]
        .agg(avg_daily="mean", std_daily="std")
        .fillna(0)
        .reset_index()
    )
    stats["std_daily"] = stats["std_daily"].fillna(stats["avg_daily"] * 0.2)
    merged = latest.merge(stats, on="sku_id", how="left")

    records = []
    for _, row in merged.iterrows():
        avg   = float(row.get("avg_daily", 0))
        std   = float(row.get("std_daily", avg * 0.2))
        lt    = int(row.get("lead_time_days", 7))
        stk   = float(row.get("stock_level", 0))
        price = float(row.get("unit_price", 100))
        uc    = float(row.get("unit_cost", price * 0.55))

        ss  = calc_safety_stock(std, lt)
        rop = calc_reorder_point(avg, lt, ss)
        eoq = calc_eoq(avg, uc)
        dus = calc_days_until_stockout(stk, avg)
        srp = calc_stockout_risk_pct(dus, lt)
        urg = classify_urgency(dus, lt, stk, rop)
        gap = max(0.0, rop - stk)
        qty = round(max(eoq, gap) * (1.2 if urg == "CRITICAL" else 1.0), 0)

        records.append({
            "sku_id":               str(row["sku_id"]),
            "sku_name":             str(row.get("sku_name", row["sku_id"])),
            "category":             str(row.get("category", "")),
            "supplier_id":          str(row.get("supplier_id", "")),
            "warehouse_id":         str(row.get("warehouse_id", "")),
            "unit_price":           round(price, 2),
            "unit_cost":            round(uc, 2),
            "lead_time_days":       lt,
            "current_stock":        round(stk, 1),
            "avg_daily_demand":     round(avg, 2),
            "days_until_stockout":  round(dus, 1),
            "reorder_point":        round(rop, 1),
            "safety_stock":         round(ss, 1),
            "eoq":                  round(eoq, 0),
            "recommended_order_qty": qty,
            "reorder_urgency":      urg,
            "stockout_risk_pct":    srp,
        })

    records.sort(
        key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[x["reorder_urgency"]]
    )
    return records


def _get_sku_records() -> list[dict]:
    global _sku_records
    if _sku_records is None:
        _sku_records = _build_sku_records()
    return _sku_records


def _build_analytics() -> dict:
    """Compute analytics once from cached DataFrame + records."""
    df      = _get_df()
    records = _get_sku_records()

    max_date  = df["date"].max()
    cutoff    = max_date - pd.Timedelta(days=30)
    demand_trend = (
        df[df["date"] >= cutoff]
        .groupby("date")["units_sold"].sum().reset_index()
        .assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
        .rename(columns={"units_sold": "total_units"})
        .to_dict(orient="records")
    )

    latest = df.sort_values("date").groupby("sku_id").last().reset_index()
    category_breakdown = (
        latest.groupby("category")
        .agg(skus=("sku_id", "count"), total_stock=("stock_level", "sum"))
        .reset_index()
        .sort_values("skus", ascending=False)
        .to_dict(orient="records")
    )
    warehouse_breakdown = (
        latest.groupby("warehouse_id")
        .agg(skus=("sku_id", "count"), total_stock=("stock_level", "sum"))
        .reset_index()
        .sort_values("skus", ascending=False)
        .to_dict(orient="records")
    ) if "warehouse_id" in latest.columns else []

    if "unit_cost" in latest.columns:
        total_value = float((latest["stock_level"] * latest["unit_cost"]).sum())
    else:
        total_value = sum(r["current_stock"] * r["unit_cost"] for r in records)

    at_risk     = [r for r in records if r["reorder_urgency"] in ("CRITICAL", "HIGH")]
    order_value = sum(r["recommended_order_qty"] * r["unit_cost"] for r in at_risk)
    avg_days    = sum(r["days_until_stockout"] for r in records) / len(records) if records else 0

    return {
        "demand_trend":          demand_trend,
        "category_breakdown":    category_breakdown,
        "warehouse_breakdown":   warehouse_breakdown,
        "total_inventory_value": round(total_value, 2),
        "avg_days_of_supply":    round(avg_days, 1),
        "order_value_needed":    round(order_value, 2),
        "at_risk_pct":           round(len(at_risk) / len(records) * 100, 1) if records else 0,
        "at_risk_count":         len(at_risk),
        "total_skus":            len(records),
    }


def get_analytics_cached() -> dict:
    global _analytics
    if _analytics is None:
        _analytics = _build_analytics()
    return _analytics


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/skus")
async def list_skus():
    return _get_sku_records()


@router.get("/sku-ids")
async def list_sku_ids():
    """
    Lightweight SKU index — only sku_id + category.
    ~5 KB vs ~90 KB for the full /skus endpoint.
    Used by the Analysis page combobox and Forecast search.
    """
    return [
        {"sku_id": r["sku_id"], "sku_name": r["sku_name"], "category": r["category"]}
        for r in _get_sku_records()
    ]


@router.get("/summary")
async def inventory_summary():
    data   = _get_sku_records()
    counts = Counter(s["reorder_urgency"] for s in data)
    return {
        "total_skus":      len(data),
        "critical":        counts.get("CRITICAL", 0),
        "high":            counts.get("HIGH", 0),
        "medium":          counts.get("MEDIUM", 0),
        "low":             counts.get("LOW", 0),
        "order_now_count": counts.get("CRITICAL", 0) + counts.get("HIGH", 0),
    }


@router.get("/critical")
async def critical_skus():
    return [s for s in _get_sku_records() if s["reorder_urgency"] in ("CRITICAL", "HIGH")]


@router.get("/analytics")
async def analytics():
    return get_analytics_cached()


@router.get("/dashboard")
async def dashboard():
    """
    Single endpoint for the Dashboard page — replaces 4 separate API calls.
    Returns summary + top critical SKUs + analytics in one round-trip.
    Frontend latency: 1× RTT instead of 4×.
    """
    records = _get_sku_records()
    counts  = Counter(s["reorder_urgency"] for s in records)
    summary = {
        "total_skus":      len(records),
        "critical":        counts.get("CRITICAL", 0),
        "high":            counts.get("HIGH", 0),
        "medium":          counts.get("MEDIUM", 0),
        "low":             counts.get("LOW", 0),
        "order_now_count": counts.get("CRITICAL", 0) + counts.get("HIGH", 0),
    }
    critical_skus = [s for s in records if s["reorder_urgency"] in ("CRITICAL", "HIGH")]

    from backend.store import _run_cache
    runs = sorted(_run_cache.values(), key=lambda r: r.created_at, reverse=True)
    recent_runs = [
        {
            "run_id":        r.run_id,
            "status":        r.status,
            "skus_analyzed": r.skus_analyzed,
            "created_at":    r.created_at,
            "completed_at":  r.completed_at,
        }
        for r in runs[:10]
    ]

    return {
        "summary":      summary,
        "critical_skus": critical_skus,
        "analytics":    get_analytics_cached(),
        "recent_runs":  recent_runs,
    }


@router.get("/suppliers")
async def supplier_metrics():
    records = _get_sku_records()
    by_sup: dict[str, list] = {}
    for r in records:
        by_sup.setdefault(r["supplier_id"], []).append(r)

    result = []
    for sup_id, skus in sorted(by_sup.items()):
        critical = sum(1 for s in skus if s["reorder_urgency"] == "CRITICAL")
        high     = sum(1 for s in skus if s["reorder_urgency"] == "HIGH")
        order_v  = sum(s["recommended_order_qty"] * s["unit_cost"]
                       for s in skus if s["reorder_urgency"] in ("CRITICAL", "HIGH"))
        result.append({
            "supplier_id":        sup_id,
            "sku_count":          len(skus),
            "critical_count":     critical,
            "high_count":         high,
            "avg_lead_days":      round(sum(s["lead_time_days"] for s in skus) / len(skus), 1),
            "avg_stockout_risk":  round(sum(s["stockout_risk_pct"] for s in skus) / len(skus), 1),
            "order_value_needed": round(order_v, 2),
        })
    return result


@router.get("/skus/{sku_id}")
async def sku_detail(sku_id: str):
    match = next((s for s in _get_sku_records() if s["sku_id"] == sku_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
    return match


@router.get("/skus/{sku_id}/history")
async def sku_history(sku_id: str, days: int = 30):
    df     = _get_df()
    sku_df = df[df["sku_id"] == sku_id].sort_values("date")
    if sku_df.empty:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
    cols = ["date", "units_sold", "stock_level", "promotional_flag", "holiday_flag"]
    return (
        sku_df.tail(days)[cols]
        .assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
        .to_dict(orient="records")
    )

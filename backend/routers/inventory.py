from collections import Counter

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


def _build_sku_records() -> list[dict]:
    df = pd.read_csv(DATA, parse_dates=["date"])
    latest = df.sort_values("date").groupby("sku_id").last().reset_index()

    cutoff = df["date"].max() - pd.Timedelta(days=30)
    stats = (
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
        avg = float(row.get("avg_daily", 0))
        std = float(row.get("std_daily", avg * 0.2))
        lt = int(row.get("lead_time_days", 7))
        stk = float(row.get("stock_level", 0))
        uc = float(row.get("unit_price", 100)) * 0.55  # approximate cost as 55% of price

        ss = calc_safety_stock(std, lt)
        rop = calc_reorder_point(avg, lt, ss)
        eoq = calc_eoq(avg, uc)
        dus = calc_days_until_stockout(stk, avg)
        srp = calc_stockout_risk_pct(dus, lt)
        urg = classify_urgency(dus, lt, stk, rop)

        gap = max(0.0, rop - stk)
        qty = round(max(eoq, gap) * (1.2 if urg == "CRITICAL" else 1.0), 0)

        records.append({
            "sku_id": str(row["sku_id"]),
            "sku_name": str(row.get("sku_name", row["sku_id"])),
            "category": str(row.get("category", "")),
            "current_stock": round(stk, 1),
            "avg_daily_demand": round(avg, 2),
            "days_until_stockout": round(dus, 1),
            "reorder_point": round(rop, 1),
            "safety_stock": round(ss, 1),
            "eoq": round(eoq, 0),
            "recommended_order_qty": qty,
            "reorder_urgency": urg,
            "stockout_risk_pct": srp,
            "supplier_id": str(row.get("supplier_id", "")),
            "lead_time_days": lt,
        })

    records.sort(key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[x["reorder_urgency"]])
    return records


@router.get("/skus")
async def list_skus():
    return _build_sku_records()


@router.get("/summary")
async def inventory_summary():
    data = _build_sku_records()
    counts = Counter(s["reorder_urgency"] for s in data)
    return {
        "total_skus": len(data),
        "critical": counts.get("CRITICAL", 0),
        "high": counts.get("HIGH", 0),
        "medium": counts.get("MEDIUM", 0),
        "low": counts.get("LOW", 0),
        "order_now_count": counts.get("CRITICAL", 0) + counts.get("HIGH", 0),
    }


@router.get("/critical")
async def critical_skus():
    return [s for s in _build_sku_records() if s["reorder_urgency"] in ("CRITICAL", "HIGH")]


@router.get("/skus/{sku_id}")
async def sku_detail(sku_id: str):
    data = _build_sku_records()
    match = next((s for s in data if s["sku_id"] == sku_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
    return match


@router.get("/skus/{sku_id}/history")
async def sku_history(sku_id: str, days: int = 30):
    df = pd.read_csv(DATA, parse_dates=["date"])
    sku_df = df[df["sku_id"] == sku_id].sort_values("date")
    if sku_df.empty:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found")
    cols = ["date", "units_sold", "stock_level", "promotional_flag", "holiday_flag"]
    return (
        sku_df.tail(days)[cols]
        .assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
        .to_dict(orient="records")
    )

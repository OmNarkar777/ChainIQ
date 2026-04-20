import os

inv = '''
import math, pandas as pd
from fastapi import APIRouter, HTTPException
from backend.agents.inventory_agent import (
    calc_safety_stock, calc_reorder_point, calc_eoq,
    calc_days_until_stockout, calc_stockout_risk_pct, classify_urgency,
)
router = APIRouter(prefix="/inventory", tags=["inventory"])
DATA = "backend/data/sample_data.csv"

def get_skus_data():
    df = pd.read_csv(DATA, parse_dates=["date"])
    latest = df.sort_values("date").groupby("sku_id").last().reset_index()
    cutoff = df["date"].max() - pd.Timedelta(days=30)
    stats = df[df["date"]>=cutoff].groupby("sku_id")["units_sold"].agg(avg_daily="mean",std_daily="std").fillna(0).reset_index()
    stats["std_daily"] = stats["std_daily"].fillna(stats["avg_daily"]*0.2)
    merged = latest.merge(stats, on="sku_id", how="left")
    result = []
    for _, row in merged.iterrows():
        avg = float(row.get("avg_daily",0))
        std = float(row.get("std_daily",avg*0.2))
        lt  = int(row.get("lead_time_days",7))
        stk = float(row.get("stock_level",0))
        uc  = float(row.get("unit_price",100))*0.55
        ss  = calc_safety_stock(std,lt)
        rop = calc_reorder_point(avg,lt,ss)
        eoq = calc_eoq(avg,uc)
        dus = calc_days_until_stockout(stk,avg)
        srp = calc_stockout_risk_pct(dus,lt)
        urg = classify_urgency(dus,lt,stk,rop)
        gap = max(0.0, rop-stk)
        qty = round(max(eoq,gap)*(1.2 if urg=="CRITICAL" else 1.0),0)
        result.append({
            "sku_id":str(row["sku_id"]),"sku_name":str(row.get("sku_name",row["sku_id"])),
            "category":str(row.get("category","")),"current_stock":round(stk,1),
            "avg_daily_demand":round(avg,2),"days_until_stockout":round(dus,1),
            "reorder_point":round(rop,1),"safety_stock":round(ss,1),
            "eoq":round(eoq,0),"recommended_order_qty":qty,
            "reorder_urgency":urg,"stockout_risk_pct":srp,
            "supplier_id":str(row.get("supplier_id","")),"lead_time_days":lt,
        })
    result.sort(key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}[x["reorder_urgency"]])
    return result

@router.get("/skus")
async def list_skus(): return get_skus_data()

@router.get("/summary")
async def summary():
    data = get_skus_data()
    from collections import Counter
    c = Counter(s["reorder_urgency"] for s in data)
    return {"total_skus":len(data),"critical":c.get("CRITICAL",0),"high":c.get("HIGH",0),"medium":c.get("MEDIUM",0),"low":c.get("LOW",0),"order_now_count":c.get("CRITICAL",0)+c.get("HIGH",0)}

@router.get("/critical")
async def critical(): return [s for s in get_skus_data() if s["reorder_urgency"] in ("CRITICAL","HIGH")]

@router.get("/skus/{sku_id}")
async def sku_detail(sku_id:str):
    data = get_skus_data()
    m = next((s for s in data if s["sku_id"]==sku_id),None)
    if not m: raise HTTPException(404,f"SKU {sku_id} not found")
    return m

@router.get("/skus/{sku_id}/history")
async def sku_history(sku_id:str,days:int=30):
    df = pd.read_csv(DATA,parse_dates=["date"])
    d = df[df["sku_id"]==sku_id].sort_values("date")
    if d.empty: raise HTTPException(404,f"SKU {sku_id} not found")
    return d.tail(days)[["date","units_sold","stock_level","promotional_flag","holiday_flag"]].assign(date=lambda x:x["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
'''

fc = '''
import uuid
from fastapi import APIRouter, HTTPException
from backend.schemas import ForecastRequest, ForecastResponse, PredictionResult
from backend.ml.predictor import DemandPredictor
router = APIRouter(prefix="/forecast", tags=["forecast"])
_p = None

def get_p():
    global _p
    if _p is None:
        _p = DemandPredictor(); _p.load_model()
    return _p

def to_schema(r):
    return PredictionResult(sku_id=r.sku_id,predicted_units=r.predicted_units,lower_bound=r.lower_bound,upper_bound=r.upper_bound,confidence_pct=r.confidence_pct,horizon_days=r.horizon_days,model_version=r.model_version,top_features=r.top_features)

@router.get("/sku/{sku_id}", response_model=PredictionResult)
async def forecast_get(sku_id:str, horizon_days:int=7):
    try: return to_schema(get_p().predict_sku(sku_id,horizon_days=horizon_days))
    except ValueError as e: raise HTTPException(404,str(e))

@router.post("/sku/{sku_id}", response_model=PredictionResult)
async def forecast_post(sku_id:str, horizon_days:int=7):
    try: return to_schema(get_p().predict_sku(sku_id,horizon_days=horizon_days))
    except ValueError as e: raise HTTPException(404,str(e))

@router.post("/batch", response_model=ForecastResponse)
async def forecast_batch(req:ForecastRequest):
    p = get_p()
    return ForecastResponse(results=[to_schema(r) for r in p.predict_batch(req.sku_ids)],run_id=str(uuid.uuid4()),model_version=str(p.version or "latest"))
'''

open("backend/routers/inventory.py","w").write(inv)
open("backend/routers/forecast.py","w").write(fc)
print("Routers fixed!")

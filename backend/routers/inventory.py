from fastapi import APIRouter
from typing import List
import pandas as pd

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("/skus")
async def list_skus():
    df = pd.read_csv("backend/data/sample_data.csv")
    skus = df[["sku_id", "sku_name", "category", "supplier_id"]].drop_duplicates()
    return skus.to_dict(orient="records")

@router.get("/skus/{sku_id}/history")
async def sku_history(sku_id: str):
    df = pd.read_csv("backend/data/sample_data.csv", parse_dates=["date"])
    sku_df = df[df["sku_id"] == sku_id].sort_values("date")
    return sku_df.tail(30).to_dict(orient="records")

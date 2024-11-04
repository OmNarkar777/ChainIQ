from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class ReorderUrgency(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── SKU ──────────────────────────────────────────────────────
class SKUBase(BaseModel):
    sku_id: str
    name: str
    category: Optional[str] = None
    current_stock: float = 0.0
    reorder_point: float = 0.0
    safety_stock: float = 0.0
    lead_time_days: int = 7
    supplier_id: Optional[str] = None
    unit_cost: float = 0.0
    unit_price: float = 0.0


class SKUCreate(SKUBase):
    pass


class SKUResponse(SKUBase):
    id: str
    model_config = {"from_attributes": True}


# ── Forecast ─────────────────────────────────────────────────
class ForecastRequest(BaseModel):
    sku_ids: List[str]
    horizon_days: int = Field(default=7, ge=1, le=90)


class PredictionResult(BaseModel):
    sku_id: str
    predicted_units: float
    lower_bound: float
    upper_bound: float
    confidence_pct: float
    horizon_days: int
    model_version: str
    top_features: List[dict]


class ForecastResponse(BaseModel):
    results: List[PredictionResult]
    run_id: str
    model_version: str


# ── Inventory ────────────────────────────────────────────────
class InventoryRecommendationResponse(BaseModel):
    sku_id: str
    sku_name: str
    current_stock: float
    reorder_point: float
    recommended_order_qty: float
    reorder_urgency: ReorderUrgency
    stockout_risk_pct: float
    days_until_stockout: float
    predicted_demand_7d: float

    model_config = {"from_attributes": True}


# ── Agent ────────────────────────────────────────────────────
class AgentAnalyzeRequest(BaseModel):
    sku_ids: Optional[List[str]] = None
    analyze_all: bool = False
    include_rag_context: bool = True


class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    skus_analyzed: int
    report_text: Optional[str] = None
    recommendations: List[InventoryRecommendationResponse] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

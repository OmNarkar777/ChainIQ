from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ReorderUrgency(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


# ── Forecast ──────────────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    sku_ids:      List[str]
    horizon_days: int = Field(default=7, ge=1, le=90)


class PredictionResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    sku_id:          str
    predicted_units: float
    lower_bound:     float
    upper_bound:     float
    confidence_pct:  float
    horizon_days:    int
    model_version:   str
    top_features:    List[dict]
    mape_estimate:   Optional[float] = None


class ForecastResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    results:       List[PredictionResult]
    run_id:        str
    model_version: str


# ── Inventory ─────────────────────────────────────────────────────────────────

class InventoryRecommendationResponse(BaseModel):
    model_config = {"from_attributes": True}

    # Core fields (always populated)
    sku_id:                str
    sku_name:              str
    current_stock:         float
    reorder_point:         float
    recommended_order_qty: float
    reorder_urgency:       ReorderUrgency
    stockout_risk_pct:     float
    days_until_stockout:   float
    predicted_demand_7d:   Optional[float] = None

    # Enrichment fields (populated by inventory_agent, missing in older data)
    category:     Optional[str]   = None
    supplier_id:  Optional[str]   = None
    warehouse_id: Optional[str]   = None
    safety_stock: Optional[float] = None
    unit_cost:    Optional[float] = None
    lead_time_days: Optional[int] = None


# ── Agent ─────────────────────────────────────────────────────────────────────

class AgentAnalyzeRequest(BaseModel):
    sku_ids:             Optional[List[str]] = None
    analyze_all:         bool = False
    include_rag_context: bool = True


class AgentRunResponse(BaseModel):
    model_config = {"from_attributes": True}

    run_id:          str
    status:          str
    skus_analyzed:   int
    report_text:     Optional[str] = None
    recommendations: List[InventoryRecommendationResponse] = []
    created_at:      datetime
    completed_at:    Optional[datetime] = None

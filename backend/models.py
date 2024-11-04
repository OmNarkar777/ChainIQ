import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, Text, Date
)
from sqlalchemy.orm import relationship
from backend.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ReorderUrgency(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SKU(Base):
    __tablename__ = "skus"

    id = Column(String, primary_key=True, default=gen_uuid)
    sku_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    current_stock = Column(Float, default=0.0)
    reorder_point = Column(Float, default=0.0)
    safety_stock = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=7)
    supplier_id = Column(String(50))
    unit_cost = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)

    sales = relationship("SalesRecord", back_populates="sku", lazy="dynamic")
    forecasts = relationship("ForecastResult", back_populates="sku", lazy="dynamic")
    recommendations = relationship("InventoryRecommendation", back_populates="sku", lazy="dynamic")


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    sku_id = Column(String(50), ForeignKey("skus.sku_id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    units_sold = Column(Float, nullable=False)
    promotional_flag = Column(Boolean, default=False)
    holiday_flag = Column(Boolean, default=False)

    sku = relationship("SKU", back_populates="sales")


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    sku_id = Column(String(50), ForeignKey("skus.sku_id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    horizon_days = Column(Integer, default=7)
    predicted_units = Column(Float)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    model_version = Column(String(50))
    mape_on_last_30d = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    sku = relationship("SKU", back_populates="forecasts")


class InventoryRecommendation(Base):
    __tablename__ = "inventory_recommendations"

    id = Column(String, primary_key=True, default=gen_uuid)
    sku_id = Column(String(50), ForeignKey("skus.sku_id"), nullable=False, index=True)
    recommended_order_qty = Column(Float)
    reorder_urgency = Column(Enum(ReorderUrgency), default=ReorderUrgency.LOW)
    stockout_risk_pct = Column(Float)
    days_until_stockout = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    agent_run_id = Column(String, ForeignKey("agent_runs.run_id"), nullable=True)

    sku = relationship("SKU", back_populates="recommendations")
    agent_run = relationship("AgentRun", back_populates="recommendations")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=gen_uuid)
    run_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), default="PENDING")
    skus_analyzed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    report_text = Column(Text, nullable=True)

    recommendations = relationship("InventoryRecommendation", back_populates="agent_run")

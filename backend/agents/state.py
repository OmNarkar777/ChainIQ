"""
LangGraph typed state for the ChainIQ multi-agent pipeline.
"""

from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass


class ChainIQState(TypedDict):
    # Input
    run_id: str
    sku_ids: List[str]
    include_rag_context: bool

    # Forecasting agent output
    forecast_results: List[Dict[str, Any]]
    forecast_error: Optional[str]

    # Inventory agent output
    inventory_recommendations: List[Dict[str, Any]]
    inventory_error: Optional[str]

    # RAG agent output
    supplier_context: Dict[str, str]  # sku_id -> relevant doc text
    rag_error: Optional[str]

    # Report agent output
    report_text: Optional[str]
    report_error: Optional[str]

    # Meta
    status: str  # PENDING / RUNNING / DONE / FAILED
    skus_analyzed: int
    errors: List[str]

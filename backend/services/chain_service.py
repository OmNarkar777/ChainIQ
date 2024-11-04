"""
ChainService: orchestrates the full analysis pipeline.
Entry point called by API routers.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional

from backend.agents.graph import chain_graph
from backend.agents.state import ChainIQState
from backend.schemas import AgentRunResponse, InventoryRecommendationResponse

logger = logging.getLogger(__name__)


def _get_all_sku_ids() -> List[str]:
    """Read SKU IDs from the sample dataset."""
    import pandas as pd
    df = pd.read_csv("backend/data/sample_data.csv")
    return df["sku_id"].unique().tolist()


async def run_analysis(
    sku_ids: Optional[List[str]] = None,
    analyze_all: bool = False,
    include_rag_context: bool = True,
) -> AgentRunResponse:
    run_id = str(uuid.uuid4())
    logger.info(f"[ChainService] Starting run {run_id}")

    if analyze_all or not sku_ids:
        sku_ids = _get_all_sku_ids()

    initial_state: ChainIQState = {
        "run_id": run_id,
        "sku_ids": sku_ids,
        "include_rag_context": include_rag_context,
        "forecast_results": [],
        "forecast_error": None,
        "inventory_recommendations": [],
        "inventory_error": None,
        "supplier_context": {},
        "rag_error": None,
        "report_text": None,
        "report_error": None,
        "status": "RUNNING",
        "skus_analyzed": 0,
        "errors": [],
    }

    final_state = chain_graph.invoke(initial_state)

    recs = [
        InventoryRecommendationResponse(**r)
        for r in final_state["inventory_recommendations"]
    ]

    return AgentRunResponse(
        run_id=run_id,
        status=final_state["status"],
        skus_analyzed=final_state["skus_analyzed"],
        report_text=final_state.get("report_text"),
        recommendations=recs,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )

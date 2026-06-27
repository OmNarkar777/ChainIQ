"""
ChainService: orchestrates the full analysis pipeline.
Entry point called by API routers.
"""
import asyncio
import uuid
import logging
from datetime import datetime
from typing import List, Optional

from backend.agents.state import ChainIQState
from backend.schemas import AgentRunResponse, InventoryRecommendationResponse

logger = logging.getLogger(__name__)


def _get_all_sku_ids() -> List[str]:
    from backend.routers.inventory import _get_df
    return _get_df()["sku_id"].unique().tolist()


def _run_pipeline(initial_state: ChainIQState) -> dict:
    from backend.agents.graph import get_chain_graph
    return get_chain_graph().invoke(initial_state)


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
        "run_id":                  run_id,
        "sku_ids":                 sku_ids,
        "include_rag_context":     include_rag_context,
        "forecast_results":        [],
        "forecast_error":          None,
        "inventory_recommendations": [],
        "inventory_error":         None,
        "supplier_context":        {},
        "rag_error":               None,
        "report_text":             None,
        "report_error":            None,
        "status":                  "RUNNING",
        "skus_analyzed":           0,
        "errors":                  [],
    }

    loop = asyncio.get_event_loop()
    final_state = await loop.run_in_executor(None, _run_pipeline, initial_state)

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

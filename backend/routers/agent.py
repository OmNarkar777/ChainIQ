from fastapi import APIRouter, HTTPException
from datetime import datetime
from backend.schemas import AgentAnalyzeRequest, AgentRunResponse
from backend.services.chain_service import run_analysis

router = APIRouter(prefix="/agent", tags=["agent"])

_run_cache = {}

@router.post("/analyze", response_model=AgentRunResponse)
async def analyze(req: AgentAnalyzeRequest):
    result = await run_analysis(
        sku_ids=req.sku_ids,
        analyze_all=req.analyze_all,
        include_rag_context=req.include_rag_context,
    )
    _run_cache[result.run_id] = result
    return result

@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    if run_id in _run_cache:
        return _run_cache[run_id]
    raise HTTPException(404, f"Run {run_id} not found")

@router.get("/runs")
async def list_runs():
    runs = sorted(_run_cache.values(), key=lambda r: r.created_at, reverse=True)
    return [{"run_id": r.run_id, "status": r.status, "skus_analyzed": r.skus_analyzed,
             "created_at": r.created_at, "completed_at": r.completed_at} for r in runs[:10]]

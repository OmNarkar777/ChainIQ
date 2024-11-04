from fastapi import APIRouter
from backend.schemas import AgentAnalyzeRequest, AgentRunResponse
from backend.services.chain_service import run_analysis

router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/analyze", response_model=AgentRunResponse)
async def analyze(req: AgentAnalyzeRequest):
    return await run_analysis(
        sku_ids=req.sku_ids,
        analyze_all=req.analyze_all,
        include_rag_context=req.include_rag_context,
    )

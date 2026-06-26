from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/health", tags=["health"])


class ComponentStatus(BaseModel):
    model_loaded: bool
    chroma_chunks: int
    data_rows: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    components: Optional[ComponentStatus] = None


@router.get("", response_model=HealthResponse)
async def health():
    model_ok = False
    chroma_chunks = 0
    data_rows = None

    try:
        from backend.ml.model_store import get_latest_version
        model_ok = get_latest_version() is not None
    except Exception:
        pass

    try:
        from backend.rag.vectorstore import collection_size
        chroma_chunks = collection_size()
    except Exception:
        pass

    try:
        import pandas as pd
        df = pd.read_csv("backend/data/sample_data.csv")
        data_rows = len(df)
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        service="chainiq-api",
        version="2.0.0",
        components=ComponentStatus(
            model_loaded=model_ok,
            chroma_chunks=chroma_chunks,
            data_rows=data_rows,
        ),
    )

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

@router.get("", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="chainiq-api", version="1.0.0")

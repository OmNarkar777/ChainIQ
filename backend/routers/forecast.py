
import uuid
from fastapi import APIRouter, HTTPException
from backend.schemas import ForecastRequest, ForecastResponse, PredictionResult
from backend.ml.predictor import DemandPredictor
router = APIRouter(prefix="/forecast", tags=["forecast"])
_p = None

def get_p():
    global _p
    if _p is None:
        _p = DemandPredictor(); _p.load_model()
    return _p

def to_schema(r):
    return PredictionResult(sku_id=r.sku_id,predicted_units=r.predicted_units,lower_bound=r.lower_bound,upper_bound=r.upper_bound,confidence_pct=r.confidence_pct,horizon_days=r.horizon_days,model_version=r.model_version,top_features=r.top_features)

@router.get("/sku/{sku_id}", response_model=PredictionResult)
async def forecast_get(sku_id:str, horizon_days:int=7):
    try: return to_schema(get_p().predict_sku(sku_id,horizon_days=horizon_days))
    except ValueError as e: raise HTTPException(404,str(e))

@router.post("/sku/{sku_id}", response_model=PredictionResult)
async def forecast_post(sku_id:str, horizon_days:int=7):
    try: return to_schema(get_p().predict_sku(sku_id,horizon_days=horizon_days))
    except ValueError as e: raise HTTPException(404,str(e))

@router.post("/batch", response_model=ForecastResponse)
async def forecast_batch(req:ForecastRequest):
    p = get_p()
    return ForecastResponse(results=[to_schema(r) for r in p.predict_batch(req.sku_ids)],run_id=str(uuid.uuid4()),model_version=str(p.version or "latest"))

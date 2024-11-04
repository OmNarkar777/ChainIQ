from fastapi import APIRouter
from backend.schemas import ForecastRequest, ForecastResponse, PredictionResult
from backend.ml.predictor import DemandPredictor
import uuid

router = APIRouter(prefix="/forecast", tags=["forecast"])
_predictor = None

def get_predictor():
    global _predictor
    if _predictor is None:
        _predictor = DemandPredictor()
        _predictor.load_model()
    return _predictor

@router.post("/run", response_model=ForecastResponse)
async def run_forecast(req: ForecastRequest):
    predictor = get_predictor()
    results = predictor.predict_batch(req.sku_ids)
    return ForecastResponse(
        results=[
            PredictionResult(
                sku_id=r.sku_id,
                predicted_units=r.predicted_units,
                lower_bound=r.lower_bound,
                upper_bound=r.upper_bound,
                confidence_pct=r.confidence_pct,
                horizon_days=r.horizon_days,
                model_version=r.model_version,
                top_features=r.top_features,
            )
            for r in results
        ],
        run_id=str(uuid.uuid4()),
        model_version=predictor.version or "latest",
    )

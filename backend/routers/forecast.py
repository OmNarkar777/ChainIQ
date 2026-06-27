import uuid
from fastapi import APIRouter, HTTPException
from backend.schemas import ForecastRequest, ForecastResponse, PredictionResult
from backend.ml.predictor import DemandPredictor

router = APIRouter(prefix="/forecast", tags=["forecast"])

_predictor: DemandPredictor | None = None


def get_predictor() -> DemandPredictor:
    global _predictor
    if _predictor is None:
        _predictor = DemandPredictor()
        _predictor.load_model()
    return _predictor


def _to_schema(r) -> PredictionResult:
    return PredictionResult(
        sku_id=r.sku_id,
        predicted_units=r.predicted_units,
        lower_bound=r.lower_bound,
        upper_bound=r.upper_bound,
        confidence_pct=r.confidence_pct,
        horizon_days=r.horizon_days,
        model_version=r.model_version,
        top_features=r.top_features,
        mape_estimate=getattr(r, "mape_estimate", None),
    )


@router.get("/sku/{sku_id}", response_model=PredictionResult)
async def forecast_sku(sku_id: str, horizon_days: int = 7):
    try:
        return _to_schema(get_predictor().predict_sku(sku_id, horizon_days=horizon_days))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sku/{sku_id}", response_model=PredictionResult)
async def forecast_sku_post(sku_id: str, horizon_days: int = 7):
    try:
        return _to_schema(get_predictor().predict_sku(sku_id, horizon_days=horizon_days))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/batch", response_model=ForecastResponse)
async def forecast_batch(req: ForecastRequest):
    predictor = get_predictor()
    results = [_to_schema(r) for r in predictor.predict_batch(req.sku_ids)]
    return ForecastResponse(
        results=results,
        run_id=str(uuid.uuid4()),
        model_version=str(predictor.version or "latest"),
    )

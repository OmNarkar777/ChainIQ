"""
Lightweight health check — responds in < 5ms, zero heavy imports.
Only checks filesystem artifacts baked in at Docker build time.

/meta is slightly heavier but still non-blocking — reads model meta JSON
and queries in-process cache counters (no pandas, no XGBoost calls).
"""
import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

_MODEL_STORE = Path("model_store")
_CHROMA_DIR  = Path("chroma_db")
_DATA_FILE   = Path("backend/data/sample_data.csv")
_META_FILE   = Path("model_store/xgb_v1_meta.json")


@router.get("")
async def health():
    models    = [m for m in _MODEL_STORE.glob("xgb_v*.json") if "_meta" not in m.name] \
                if _MODEL_STORE.exists() else []
    model_ok  = bool(models)
    chroma_ok = _CHROMA_DIR.exists() and any(_CHROMA_DIR.iterdir())
    data_ok   = _DATA_FILE.exists()

    return {
        "status":  "ok",
        "service": "chainiq-api",
        "version": "2.0.0",
        "components": {
            "model_loaded":  model_ok,
            "chroma_ready":  chroma_ok,
            "data_ready":    data_ok,
        },
    }


@router.get("/meta")
async def meta():
    """Model info + cache statistics — used by the dashboard."""
    model_meta: dict = {}
    if _META_FILE.exists():
        try:
            model_meta = json.loads(_META_FILE.read_text())
        except Exception:
            pass

    # Cache stats — imported lazily so health stays lightweight at import time
    try:
        from backend.ml.predictor import get_cache_stats
        cache_stats = get_cache_stats()
    except Exception:
        cache_stats = {}

    try:
        from backend.agents.report_agent import get_report_cache_stats
        report_stats = get_report_cache_stats()
    except Exception:
        report_stats = {}

    try:
        from backend.routers.inventory import _sku_records
        inv_cached = _sku_records is not None
        sku_count  = len(_sku_records) if _sku_records else 300
    except Exception:
        inv_cached = False
        sku_count  = 300

    pred_size = cache_stats.get("prediction_cache_size", 0)
    cache_warm = pred_size > 0 or inv_cached

    return {
        "model_version":      f"xgb_v{model_meta.get('version', 1)}",
        "model_mape":         model_meta.get("xgb_mape"),
        "model_rmse":         model_meta.get("xgb_rmse"),
        "improvement_pct":    model_meta.get("improvement_pct"),
        "confidence_pct":     80.0,
        "sku_count":          sku_count,
        "feature_count":      len(model_meta.get("feature_names", [])),
        "target_horizon_days": model_meta.get("target_horizon", 7),
        "training_rows":      model_meta.get("train_rows"),
        "cache_warm":         cache_warm,
        "cache_status":       "WARM" if cache_warm else "COLD",
        **cache_stats,
        **report_stats,
    }

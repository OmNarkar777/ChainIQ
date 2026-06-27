"""
Lightweight health check — responds in < 5ms, zero heavy imports.
Only checks filesystem artifacts baked in at Docker build time.
"""
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

_MODEL_STORE = Path("model_store")
_CHROMA_DIR  = Path("chroma_db")
_DATA_FILE   = Path("backend/data/sample_data.csv")


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

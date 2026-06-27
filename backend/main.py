import sys, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from backend.config import get_settings
from backend.routers import health, forecast, inventory, agent, stream

logging.basicConfig(level=logging.WARNING)
logger.remove()
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ChainIQ API v2.0.0 starting up...")

    # Pre-warm the forecast predictor using the same global singleton that
    # /forecast routes use — first HTTP request won't pay the model-load cost.
    try:
        from backend.routers.forecast import get_predictor
        p = get_predictor()
        logger.info(f"XGBoost model v{p.version} loaded")
    except Exception as exc:
        logger.warning(f"Model warm-up skipped: {exc}")

    # Pre-build the inventory SKU cache so the first HTTP request doesn't pay
    # the ~2s build cost (300 SKUs × inventory math) and doesn't race with
    # concurrent requests from the frontend on initial page load.
    try:
        from backend.routers.inventory import _get_sku_records
        recs = _get_sku_records()
        logger.info(f"Inventory cache warm ({len(recs)} SKUs)")
    except Exception as exc:
        logger.warning(f"Inventory warm-up skipped: {exc}")

    # Ensure ChromaDB is populated (no-op when Dockerfile pre-ingested at build time).
    try:
        from backend.rag.vectorstore import ingest_supplier_docs, collection_size
        n = collection_size()
        if n == 0:
            n = ingest_supplier_docs()
            logger.info(f"RAG: ingested {n} supplier doc chunks")
        else:
            logger.info(f"RAG: ChromaDB ready ({n} chunks)")
    except Exception as exc:
        logger.warning(f"RAG warm-up skipped: {exc}")

    yield
    logger.info("ChainIQ API shutting down.")

app = FastAPI(
    title="ChainIQ - Supply Chain Intelligence API",
    description="Multi-agent demand forecasting and inventory optimisation",
    version="2.0.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(inventory.router)
app.include_router(agent.router)
app.include_router(stream.router)

@app.get("/")
async def root():
    return {
        "service": "ChainIQ", "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "health":    "GET /health",
            "forecast":  "POST /forecast/sku/{sku_id}",
            "inventory": "GET /inventory/skus",
            "critical":  "GET /inventory/critical",
            "summary":   "GET /inventory/summary",
            "agent":     "POST /agent/analyze",
            "stream":    "GET /stream/analyze",
        }
    }
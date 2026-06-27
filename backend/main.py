import asyncio
import sys
import logging
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


def _sync_warmup() -> None:
    """
    Blocking warm-up: load XGBoost model + build inventory cache.
    Runs in a thread-pool so it never blocks the event loop or the
    initial health check (Render pings /health almost immediately).
    """
    try:
        from backend.routers.forecast import get_predictor
        p = get_predictor()
        logger.info(f"XGBoost model v{p.version} ready")
    except Exception as exc:
        logger.warning(f"Model warm-up skipped: {exc}")

    try:
        from backend.routers.inventory import _get_sku_records
        recs = _get_sku_records()
        logger.info(f"Inventory cache ready ({len(recs)} SKUs)")
    except Exception as exc:
        logger.warning(f"Inventory warm-up skipped: {exc}")

    logger.info("ChainIQ API warm-up complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ChainIQ API v2.0.0 starting up…")
    # Fire warm-up in background — app starts serving immediately,
    # so Render's health check never waits for heavy initialisation.
    asyncio.get_event_loop().run_in_executor(None, _sync_warmup)
    yield
    logger.info("ChainIQ API shutting down.")


app = FastAPI(
    title="ChainIQ – Supply Chain Intelligence API",
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
        "service":   "ChainIQ",
        "version":   "2.0.0",
        "docs":      "/docs",
        "endpoints": {
            "health":    "GET  /health",
            "forecast":  "GET  /forecast/sku/{sku_id}",
            "inventory": "GET  /inventory/skus",
            "critical":  "GET  /inventory/critical",
            "summary":   "GET  /inventory/summary",
            "analytics": "GET  /inventory/analytics",
            "suppliers": "GET  /inventory/suppliers",
            "agent":     "POST /agent/analyze",
            "stream":    "GET  /stream/analyze",
        },
    }

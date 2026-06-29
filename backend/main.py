import asyncio
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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
    Blocking warmup: initialise every singleton that would otherwise block
    the first user request. Runs in thread-pool executor so the event loop
    and health endpoint remain responsive during startup.

    Order matters:
    1. XGBoost model       — fast, < 1s
    2. Inventory records   — 109 500-row CSV + math, ~2s
    3. Prediction cache    — 300 SKUs × 50 bootstraps, ~10-20s
    4. SentenceTransformer — all-MiniLM-L6-v2 load, ~3s
    5. ChromaDB client     — opens SQLite, < 1s
    6. Analytics cache     — groupby on loaded DataFrame, ~0.5s
    7. RAG supplier cache  — embed+retrieve 10 suppliers, ~3s
    """

    # ── 1. XGBoost ───────────────────────────────────────────────────────────
    predictor = None
    try:
        from backend.routers.forecast import get_predictor
        predictor = get_predictor()
        logger.info(f"XGBoost model v{predictor.version} ready")
    except Exception as exc:
        logger.warning(f"Model warmup skipped: {exc}")

    # ── 2. Inventory CSV + computed records ───────────────────────────────────
    try:
        from backend.routers.inventory import _get_sku_records
        recs = _get_sku_records()
        logger.info(f"Inventory cache ready ({len(recs)} SKUs)")
    except Exception as exc:
        logger.warning(f"Inventory warmup skipped: {exc}")

    # ── 3. Prediction cache (fast bootstraps for warmup, full on demand) ──────
    if predictor is not None:
        try:
            from backend.routers.inventory import _get_df
            df = _get_df()
            all_skus = df["sku_id"].unique().tolist()
            warmed = 0
            for sku_id in all_skus:
                try:
                    predictor.predict_sku(sku_id, n_bootstraps=50)
                    warmed += 1
                except Exception:
                    pass
            logger.info(f"Prediction cache warmed: {warmed}/{len(all_skus)} SKUs")
        except Exception as exc:
            logger.warning(f"Prediction warmup skipped: {exc}")

    # ── 4. SentenceTransformer ────────────────────────────────────────────────
    try:
        from backend.rag.vectorstore import get_embedder
        get_embedder()
        logger.info("SentenceTransformer ready")
    except Exception as exc:
        logger.warning(f"Embedder warmup skipped: {exc}")

    # ── 5. ChromaDB ───────────────────────────────────────────────────────────
    try:
        from backend.rag.vectorstore import get_collection
        col = get_collection()
        logger.info(f"ChromaDB ready ({col.count()} chunks)")
    except Exception as exc:
        logger.warning(f"ChromaDB warmup skipped: {exc}")

    # ── 6. Analytics cache ────────────────────────────────────────────────────
    try:
        from backend.routers.inventory import get_analytics_cached
        get_analytics_cached()
        logger.info("Analytics cache ready")
    except Exception as exc:
        logger.warning(f"Analytics warmup skipped: {exc}")

    # ── 7. RAG supplier context cache ─────────────────────────────────────────
    try:
        from backend.rag.retriever import warm_supplier_cache
        warm_supplier_cache()
        logger.info("RAG supplier cache warmed")
    except Exception as exc:
        logger.warning(f"RAG warmup skipped: {exc}")

    logger.info("ChainIQ API warmup complete — all singletons ready")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ChainIQ API v2.1.0 starting…")
    asyncio.get_event_loop().run_in_executor(None, _sync_warmup)
    yield
    logger.info("ChainIQ API shutting down.")


app = FastAPI(
    title="ChainIQ – Supply Chain Intelligence API",
    description="Multi-agent demand forecasting and inventory optimisation",
    version="2.1.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
# GZip compresses responses > 1 KB — reduces 90KB inventory payload to ~18KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

_origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(forecast.router)
app.include_router(inventory.router)
app.include_router(agent.router)
app.include_router(stream.router)


@app.get("/")
async def root():
    return {
        "service":   "ChainIQ",
        "version":   "2.1.0",
        "docs":      "/docs",
        "endpoints": {
            "health":     "GET  /health",
            "meta":       "GET  /health/meta",
            "forecast":   "GET  /forecast/sku/{sku_id}",
            "inventory":  "GET  /inventory/skus",
            "sku-ids":    "GET  /inventory/sku-ids",
            "dashboard":  "GET  /inventory/dashboard",
            "critical":   "GET  /inventory/critical",
            "summary":    "GET  /inventory/summary",
            "analytics":  "GET  /inventory/analytics",
            "suppliers":  "GET  /inventory/suppliers",
            "agent":      "POST /agent/analyze",
            "stream":     "GET  /stream/analyze",
        },
    }

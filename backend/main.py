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
    logger.info("ChainIQ API starting up...")
    try:
        from backend.ml.predictor import DemandPredictor
        p = DemandPredictor()
        p.load_model()
        logger.info(f"XGBoost model v{p.version} loaded")
    except Exception as exc:
        logger.warning(f"Model warm-up skipped: {exc}")
    try:
        from backend.rag.vectorstore import ingest_supplier_docs, collection_size
        if collection_size() == 0:
            n = ingest_supplier_docs()
            logger.info(f"RAG: ingested {n} supplier doc chunks")
        else:
            logger.info(f"RAG: ChromaDB already has {collection_size()} chunks")
    except Exception as exc:
        logger.warning(f"RAG ingestion skipped: {exc}")
    yield
    logger.info("ChainIQ API shutting down.")

app = FastAPI(
    title="ChainIQ - Supply Chain Intelligence API",
    description="Multi-agent demand forecasting and inventory optimisation",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
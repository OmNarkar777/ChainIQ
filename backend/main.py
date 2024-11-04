"""
ChainIQ FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.config import get_settings
from backend.routers import health, forecast, inventory, agent, stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ChainIQ API starting up...")
    # Ingest supplier docs into ChromaDB on startup
    try:
        from backend.rag.vectorstore import ingest_supplier_docs
        n = ingest_supplier_docs()
        logger.info(f"RAG: ingested {n} doc chunks")
    except Exception as e:
        logger.warning(f"RAG ingestion skipped: {e}")
    yield
    logger.info("ChainIQ API shutting down.")


app = FastAPI(
    title="ChainIQ — Supply Chain Intelligence API",
    description="Multi-agent demand forecasting and inventory optimization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "service": "ChainIQ",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

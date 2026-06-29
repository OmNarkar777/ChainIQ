FROM python:3.11-slim

WORKDIR /app

# ── Layer 1: Python dependencies ──────────────────────────────────────────────
# Cached unless requirements.txt changes (~3 min first build, instant after).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Layer 2: Build-time artifact generation ───────────────────────────────────
# Copy ONLY the exact files that build scripts need — nothing more.
# This keeps this layer cached even when routers, agents, main.py, or
# predictor.py change (the common case during development).
#
# build_train.py imports:
#   backend.data.generator, backend.ml.trainer,
#   backend.ml.feature_engineering, backend.ml.model_store
#
# build_ingest.py imports:
#   backend.rag.vectorstore, backend.config
#
COPY backend/__init__.py                    backend/__init__.py
COPY backend/config.py                      backend/config.py
COPY backend/data/__init__.py               backend/data/__init__.py
COPY backend/data/generator.py              backend/data/generator.py
COPY backend/data/supplier_docs/            backend/data/supplier_docs/
COPY backend/ml/__init__.py                 backend/ml/__init__.py
COPY backend/ml/trainer.py                  backend/ml/trainer.py
COPY backend/ml/model_store.py              backend/ml/model_store.py
COPY backend/ml/feature_engineering.py     backend/ml/feature_engineering.py
COPY backend/rag/__init__.py                backend/rag/__init__.py
COPY backend/rag/vectorstore.py             backend/rag/vectorstore.py
COPY scripts/                               scripts/

# Generate synthetic 109 500-row dataset + train XGBoost model.
# Only re-runs when the files copied above change (data gen / trainer / features).
RUN python scripts/build_train.py

# Pre-ingest supplier docs into ChromaDB.
# Downloads all-MiniLM-L6-v2 from HuggingFace (~80 MB) on first build;
# subsequent builds use the cached Docker layer.
RUN python scripts/build_ingest.py

# ── Layer 3: Remaining application source ─────────────────────────────────────
# All other source files (routers, agents, main, schemas, predictor, retriever).
# Changing these — the day-to-day development files — only invalidates this
# layer, NOT the expensive ML training + ChromaDB ingestion above.
COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

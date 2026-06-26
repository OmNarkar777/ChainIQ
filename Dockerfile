FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Generate synthetic dataset + train XGBoost model at build time.
# This runs only once per image build; Docker layer caching means
# subsequent builds reuse this layer if source code is unchanged.
RUN python -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')

data_path = Path('backend/data/sample_data.csv')
model_store = Path('model_store')

if not data_path.exists():
    print('[build] Generating synthetic dataset...')
    from backend.data.generator import main as generate_data
    generate_data()
    print('[build] Dataset ready.')
else:
    print(f'[build] Dataset already present ({data_path.stat().st_size // 1024}KB).')

existing = [m for m in sorted(model_store.glob('xgb_v*.json')) if '_meta' not in m.name] if model_store.exists() else []
if not existing:
    print('[build] Training XGBoost model (first-time build, ~3s)...')
    from backend.ml.trainer import train
    train()
    print('[build] Model trained and saved.')
else:
    print(f'[build] Model already present: {existing[-1]}')
"

# Pre-ingest supplier documents into ChromaDB
# (sentence-transformers downloads the embedding model from HuggingFace here)
RUN python -c "
import sys
sys.path.insert(0, '.')
try:
    from backend.rag.vectorstore import ingest_supplier_docs, collection_size
    if collection_size() == 0:
        n = ingest_supplier_docs()
        print(f'[build] RAG: ingested {n} supplier doc chunks into ChromaDB.')
    else:
        print(f'[build] RAG: ChromaDB already has {collection_size()} chunks.')
except Exception as e:
    print(f'[build] RAG ingestion skipped: {e}')
"

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

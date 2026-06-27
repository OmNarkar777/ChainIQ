FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Generate synthetic dataset + train XGBoost model at build time.
# Runs once; subsequent builds reuse this layer from Docker cache.
RUN python scripts/build_train.py

# Pre-ingest supplier documents into ChromaDB.
# sentence-transformers downloads all-MiniLM-L6-v2 from HuggingFace here.
RUN python scripts/build_ingest.py

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

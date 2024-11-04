# ChainIQ — Supply Chain Intelligence System

> Production-grade multi-agent AI system for demand forecasting and inventory optimization.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)
![LangGraph](https://img.shields.io/badge/LangGraph-0.0.66-purple)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)

## Architecture

```
POST /agent/analyze
        │
        ▼
┌───────────────────────────────────────────────────┐
│              LangGraph Orchestration               │
│                                                   │
│  ForecastAgent → InventoryAgent → RAGNode → ReportAgent
│      (XGBoost)    (EOQ + Safety   (ChromaDB)  (Groq LLM)
│                    Stock rules)                    │
└───────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Generate data and train model
python ml_training/train.py --generate

# 3. Start PostgreSQL
docker-compose up postgres -d

# 4. Copy and edit env
cp .env.example .env

# 5. Run migrations
alembic upgrade head

# 6. Start API
uvicorn backend.main:app --reload

# 7. Open docs
open http://localhost:8000/docs
```

## ML Pipeline

| Metric   | XGBoost | Naive Baseline |
|----------|---------|----------------|
| MAPE     | ~12-15% | ~25-30%        |
| RMSE     | Lower   | Higher         |
| Beat by  | **>20%**|                |

## Features

- **XGBoost** demand forecasting with lag, rolling, and calendar features
- **LangGraph** multi-agent pipeline: Forecast → Inventory → RAG → Report
- **ChromaDB** RAG over supplier documents for context-aware recommendations
- **Safety stock & EOQ** business logic (Z=1.645 for 95% service level)
- **Groq LLM** (Llama 3.3 70B) for executive report generation
- **FastAPI** async REST API with full OpenAPI docs

## Project Structure

```
chainiq/
├── backend/
│   ├── data/generator.py        # 50 SKU synthetic dataset
│   ├── ml/                      # XGBoost training & inference
│   ├── agents/                  # LangGraph multi-agent nodes
│   ├── rag/                     # ChromaDB + retriever
│   └── routers/                 # FastAPI endpoints
├── ml_training/train.py         # Standalone training script
└── tests/                       # Pytest unit tests
```

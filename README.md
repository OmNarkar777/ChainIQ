# ChainIQ — Supply Chain Intelligence System

> Production-grade multi-agent AI that tells operations managers what to order, how much, and when.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)](https://xgboost.readthedocs.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)

---

## Architecture

```
User / Dashboard
     │  POST /agent/analyze     GET /stream/analyze (SSE)
     ▼
 FastAPI Backend
     │
     ▼
 LangGraph Pipeline
     │
     ▼
 [1] Forecasting Agent       XGBoost predict_sku()
     │  25 features · lag/rolling/calendar · bootstrap CI
     ▼
 [2] Inventory Agent         EOQ + Safety Stock
     │  Z=1.65 · reorder point · urgency classification
     ▼
     ├── CRITICAL/HIGH SKUs? ──► [3] RAG Node
     │                               ChromaDB · cosine sim
     ▼                               all-MiniLM-L6-v2
 [4] Report Agent            Groq Llama 3.3 70B
     │  structured markdown · data-grounded · no hallucination surface
     ▼
 PostgreSQL
 AgentRun + InventoryRecommendation persistence
```

---

## Model Performance

| Metric | Result |
|--------|--------|
| Test MAPE | **12.4%** vs 15.5% naive baseline |
| Stockout reduction | **34%** simulated across 50 SKUs · 12-month dataset |
| CV MAPE | 19.3% ±2.4 · TimeSeriesSplit(5 folds) |
| Training time | **2.7s** on 16,500 rows · 25 features |
| Improvement over naive | **20%+** MAPE reduction |

---

## Inventory Formulas

| Metric | Formula | Notes |
|--------|---------|-------|
| Safety Stock | `Z × σ_daily × √lead_time_days` | Z = 1.65 → 95% service level |
| Reorder Point | `avg_daily × lead_time + safety_stock` | trigger before stockout |
| EOQ | `√(2 × D × S / H)` | minimises order + holding cost |
| Urgency | `days_to_SO vs lead_time` | CRITICAL / HIGH / MEDIUM / LOW |

---

## Quick Start — 3 Commands

```bash
git clone https://github.com/OmNarkar777/ChainIQ.git && cd ChainIQ
cp .env.example .env   # add GROQ_API_KEY (optional — fallback report if absent)
docker-compose up --build
```

Open `http://localhost:3000` (dashboard) · `http://localhost:8000/docs` (Swagger UI)

**Without Docker:**
```bash
pip install -r requirements.txt
python ml_training/train.py --generate   # generates data + trains model
uvicorn backend.main:app --reload
cd frontend && npm install && npm run dev
```

---

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/agent/analyze` | Full LangGraph pipeline → report + recommendations |
| `GET`  | `/stream/analyze` | SSE — real-time agent progress events |
| `GET`  | `/inventory/critical` | CRITICAL + HIGH urgency SKUs for alert panel |
| `GET`  | `/inventory/summary` | Urgency counts across all 50 SKUs |
| `GET`  | `/forecast/sku/{id}` | XGBoost forecast + 80% CI + top-5 feature importances |
| `GET`  | `/docs` | Interactive Swagger UI |

---

## Technical Decisions

**XGBoost over LSTM / Prophet.** Benchmarked all three. XGBoost trains in 2.7s on the full dataset, handles cross-SKU tabular features natively (category, supplier, price), and produces interpretable feature importance — `rolling_mean_14` and `ewm_7` dominate, validating the lag-feature design. Prophet's additive model couldn't capture the non-linear interaction between promotional flags and demand spikes that drives the most variance in this dataset.

**LangGraph over CrewAI.** ChainIQ has a deterministic pipeline with a hard conditional edge — skip RAG entirely if no CRITICAL/HIGH SKUs exist. LangGraph models this exactly: typed `ChainIQState`, first-class conditional routing, and `MemorySaver` checkpointing for run recovery. CrewAI optimises for open-ended conversational agent loops, not for typed ETL-style pipelines with measurable intermediate outputs.

**Safety stock formula.** Used `Z × σ × √LT` (normal demand during lead time) rather than simpler fixed-buffer approaches. Z = 1.65 targets 95% service level — the standard operations management threshold. EOQ minimises total inventory cost by equating marginal order cost and holding cost saved. Both formulas are auditable by the operations manager without ML knowledge, which is essential for real-world adoption.

---

## Project Structure

```
chainiq/
├── backend/
│   ├── agents/          # LangGraph nodes: forecast → inventory → RAG → report
│   ├── ml/              # XGBoost training, feature engineering, inference
│   ├── rag/             # ChromaDB ingestion + semantic retrieval
│   └── routers/         # FastAPI endpoints + SSE streaming
├── frontend/src/
│   ├── pages/           # Dashboard, Analysis (SSE), Inventory, Forecast
│   └── components/      # Table, Chart, ReportViewer, StepIndicator
├── ml_training/train.py # Standalone training entry point
└── tests/               # 26 unit tests for all inventory formulas
```

---

## Running Tests

```bash
pytest tests/test_inventory_formulas.py -v   # 26 tests, no model or DB needed
pytest tests/ -v
```
````


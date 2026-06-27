# ChainIQ — Supply Chain Intelligence System

> Production-grade multi-agent AI that tells operations managers what to order, how much, and when.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)](https://xgboost.readthedocs.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)

ChainIQ combines XGBoost machine learning, LangGraph multi-agent orchestration, ChromaDB retrieval-augmented generation, and a Groq LLM to deliver actionable supply chain intelligence — forecasting demand, computing optimal reorder quantities, retrieving supplier context, and generating executive reports, all in a single pipeline.

---

## Architecture

```
POST /agent/analyze  (or GET /stream/analyze for real-time SSE)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Orchestration                     │
│                                                             │
│  ForecastAgent  →  InventoryAgent  →  RAGNode  →  ReportAgent
│   (XGBoost)        (EOQ + Safety      (ChromaDB)   (Groq LLM)
│                     Stock rules)                            │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|---|---|---|
| **Forecast Agent** | XGBoost (n=500, depth=6) | 7-day demand forecast with 80% CI via bootstrap |
| **Inventory Agent** | Pure Python (EOQ, safety stock) | Reorder points, order quantities, urgency classification |
| **RAG Node** | ChromaDB + sentence-transformers | Supplier document retrieval for critical SKUs |
| **Report Agent** | Groq LLaMA 3.3 70B | Natural language executive summary |
| **Orchestrator** | LangGraph typed state machine | Agent pipeline with conditional RAG routing |
| **API** | FastAPI + async | REST + Server-Sent Events streaming |
| **Frontend** | React + Recharts + Tailwind | Real-time pipeline visualization |

---

## ML Pipeline Performance

Trained on a 50-SKU synthetic dataset with 18,250 daily sales records (50 SKUs × 365 days), using a temporal train/test split (last 30 days as holdout) and 5-fold time-series cross-validation.

| Metric | XGBoost | Naive Baseline |
|---|---|---|
| **MAPE** | **12.4%** | 15.5% |
| **RMSE** | 71.97 | higher |
| **MAE** | 49.12 | — |
| **Beat naive by** | **20.0%** | — |
| CV Mean MAPE | 19.3% ± 2.4% | — |

**25 engineered features**: lag (1/7/14/28d), rolling mean/std (7/14d), EWM (7d), 9 calendar features, category/supplier encodings, log price, lead time, stock-to-reorder ratio, days of supply.

---

## Features

- **Demand forecasting** — XGBoost with time-series CV, bootstrap confidence intervals, MAPE tracking
- **Inventory optimization** — Economic Order Quantity (EOQ), safety stock (Z=1.645 for 95% service level), reorder point calculation
- **Multi-agent pipeline** — LangGraph typed state machine with conditional RAG routing
- **Supplier RAG** — ChromaDB + `all-MiniLM-L6-v2` embeddings over supplier documents
- **LLM reports** — Groq LLaMA 3.3 70B generates executive summaries with specific order recommendations
- **Real-time streaming** — SSE endpoint streams pipeline progress event-by-event
- **Graceful degradation** — fallback template report when Groq API is unavailable

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier available; optional — app degrades gracefully)

### 1. Clone and install

```bash
git clone <repo-url>
cd chainiq
pip install -r requirements.txt
```

### 2. Generate synthetic data and train the model

```bash
python ml_training/train.py --generate
```

This creates `backend/data/sample_data.csv` (50 SKUs × 3 years) and trains the XGBoost model into `model_store/`.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 4. Start the API

```bash
uvicorn backend.main:app --reload
```

API documentation: http://localhost:8000/docs

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

---

## API Reference

### Health

```
GET /health
```
Returns service status and component health (model loaded, ChromaDB chunks, data rows).

### Forecasting

```
GET  /forecast/sku/{sku_id}?horizon_days=7
POST /forecast/sku/{sku_id}?horizon_days=7
POST /forecast/batch   body: {"sku_ids": ["SKU_0001", ...], "horizon_days": 7}
```

Returns predicted units, 80% confidence interval (lower/upper bound), top 5 feature importances, and MAPE estimate.

### Inventory

```
GET /inventory/skus               — all SKUs with urgency, reorder qty, days-to-stockout
GET /inventory/summary            — aggregate counts by urgency level
GET /inventory/critical           — CRITICAL + HIGH urgency SKUs only
GET /inventory/skus/{sku_id}      — single SKU detail
GET /inventory/skus/{sku_id}/history?days=30  — sales history
```

### Agent Pipeline

```
POST /agent/analyze
body: {
  "sku_ids": ["SKU_0001", "SKU_0002"],   // omit or leave empty + analyze_all:true for all 50
  "analyze_all": false,
  "include_rag_context": true
}

GET /agent/runs           — list last 10 runs
GET /agent/runs/{run_id}  — full result including report text and recommendations
```

### Streaming (SSE)

```
GET /stream/analyze?sku_ids=SKU_0001,SKU_0002&analyze_all=false&include_rag=true
```

Streams JSON events: `run_started` → `forecasting_start` → `forecasting_complete` → `inventory_complete` → `rag_complete` → `report_complete` → `done`

Each `report_complete` event includes the `run_id` so clients can fetch the full result from `/agent/runs/{run_id}`.

---

## Project Structure

```
chainiq/
├── backend/
│   ├── agents/
│   │   ├── graph.py              # LangGraph pipeline definition
│   │   ├── state.py              # Typed state (ChainIQState TypedDict)
│   │   ├── forecasting_agent.py  # XGBoost forecast node
│   │   ├── inventory_agent.py    # EOQ/safety stock/urgency node
│   │   └── report_agent.py       # Groq LLM report node
│   ├── ml/
│   │   ├── feature_engineering.py  # 25 time-series + calendar features
│   │   ├── predictor.py            # Inference with bootstrap CI
│   │   ├── trainer.py              # Time-series CV training pipeline
│   │   └── model_store.py          # Model versioning (load/save)
│   ├── rag/
│   │   ├── vectorstore.py    # ChromaDB ingestion + retrieval
│   │   └── retriever.py      # Query interface
│   ├── routers/
│   │   ├── agent.py          # POST /agent/analyze
│   │   ├── forecast.py       # GET/POST /forecast/sku/{id}
│   │   ├── inventory.py      # GET /inventory/*
│   │   ├── stream.py         # GET /stream/analyze (SSE)
│   │   └── health.py         # GET /health
│   ├── data/
│   │   ├── generator.py      # 50-SKU synthetic data generator
│   │   └── supplier_docs/    # Supplier text documents for RAG
│   ├── services/
│   │   └── chain_service.py  # orchestrates run_analysis()
│   ├── config.py             # pydantic-settings configuration
│   ├── main.py               # FastAPI app + lifespan
│   └── store.py              # In-memory run cache
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, Analysis, Inventory, Forecast
│   │   ├── components/       # InventoryTable, ForecastChart, ReportViewer, ...
│   │   ├── api/client.js     # Typed API client + SSE stream helper
│   │   └── hooks/            # useInventorySummary, useAllSkus
│   ├── nginx.conf            # Production nginx config (proxy /api → backend)
│   └── Dockerfile            # Multi-stage frontend build
├── ml_training/
│   └── train.py              # Standalone training entry point
├── tests/
│   ├── test_inventory_formulas.py  # 20 unit tests for EOQ/SS/ROP math
│   └── test_ml.py                  # ML pipeline smoke tests
├── Dockerfile                # Backend container
├── docker-compose.yml        # Backend + frontend services
└── requirements.txt
```

---

## Running Tests

```bash
pytest tests/ -v
```

Covers: safety stock formula, reorder point, EOQ, days-until-stockout, stockout risk, urgency classification, order quantity, feature engineering shape/consistency, inventory recommendation logic, MAPE utility, and PredictionResult dataclass.

---

## Deployment

### 1. Local Development

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# Clone
git clone https://github.com/OmNarkar777/ChainIQ.git
cd ChainIQ

# Backend
pip install -r requirements.txt
cp .env.example .env
# Optional: add your GROQ_API_KEY to .env for AI reports

# Generate data + train model (runs once, ~5s)
python ml_training/train.py --generate

# Start API
uvicorn backend.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

The Vite dev server automatically proxies `/api/*` → `http://localhost:8000` (see `vite.config.js`), so no `VITE_API_URL` is needed locally.

---

### 2. Docker (Full Stack)

```bash
cp .env.example .env
# Add GROQ_API_KEY to .env if desired

docker-compose up --build
```

- API: `http://localhost:8000`
- Frontend: `http://localhost:80`

The Docker image generates synthetic data, trains the XGBoost model, and pre-populates ChromaDB on first build (~3–5 minutes). Subsequent builds use Docker layer cache and are instant.

To run the backend only:

```bash
docker build -t chainiq-api .
docker run -p 8000:8000 --env-file .env chainiq-api
```

---

### 3. Render — Backend Deployment

The backend deploys as a Docker container on Render. The `render.yaml` IaC file handles all service configuration automatically.

**Steps:**

1. Push your repository to GitHub (already done if you forked this repo).
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect your GitHub account and select the `ChainIQ` repository.
4. Render detects `render.yaml` and pre-fills all settings. Click **Apply**.
5. In **Environment** → **Secret Files / Environment Variables**, add:
   - `GROQ_API_KEY` = your key from [console.groq.com](https://console.groq.com) (free tier available)
6. Click **Deploy**.

The first deploy takes **5–10 minutes** (installs Python deps, generates data, trains XGBoost, downloads the `all-MiniLM-L6-v2` embedding model, pre-ingests ChromaDB). Subsequent deploys reuse Docker layer cache and take ~2 minutes.

**After deployment:**

```bash
# Verify the API is healthy
curl https://chainiq-api.onrender.com/health
# Expected: {"status":"ok","version":"2.0.0","components":{"model_loaded":true,"chroma_chunks":...}}

# View Swagger docs
open https://chainiq-api.onrender.com/docs
```

> **Free tier note:** Render's free plan spins down after 15 minutes of inactivity. The first request after idle takes ~30 seconds for cold start. The $7/month Starter plan keeps the service always-on.

---

### 4. Vercel — Frontend Deployment

**Steps:**

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → **Import Git Repository**.
2. Select `OmNarkar777/ChainIQ`.
3. Set **Root Directory** to `frontend`.
4. Under **Environment Variables**, add:
   - `VITE_API_URL` = `https://chainiq-api.onrender.com` (your Render service URL from step 3)
5. Click **Deploy**.

Vercel auto-detects `vercel.json` in the `frontend/` directory and configures SPA routing.

**After deployment:**

```
https://your-project.vercel.app           → Dashboard
https://your-project.vercel.app/inventory → Inventory table
https://your-project.vercel.app/analysis  → Run pipeline
https://your-project.vercel.app/forecast  → Demand forecast
```

---

### 5. Environment Variables Reference

#### Backend (`.env` / Render dashboard)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Optional* | `""` | Groq API key. Without it, reports use a fallback template. |
| `GROQ_MODEL` | Optional | `llama-3.3-70b-versatile` | Groq model for report generation |
| `CHROMA_PERSIST_DIR` | Optional | `./chroma_db` | ChromaDB persistence directory |
| `MODEL_STORE_DIR` | Optional | `./model_store` | XGBoost model directory |
| `APP_ENV` | Optional | `development` | `development` or `production` |
| `LOG_LEVEL` | Optional | `INFO` | Log verbosity: DEBUG / INFO / WARNING / ERROR |
| `CORS_ORIGINS` | Optional | `*` | Comma-separated allowed origins. Set to your Vercel URL in production. |

*`GROQ_API_KEY` is strongly recommended for full functionality. Get one free at [console.groq.com](https://console.groq.com).

#### Frontend (Vercel dashboard)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | **Yes** (Vercel/standalone Docker only) | Full URL of the backend API. Example: `https://chainiq-api.onrender.com`. Not needed for local dev (Vite proxy handles it) or docker-compose (nginx proxy handles it). |

---

### 6. Post-Deployment Verification Checklist

After deploying both backend and frontend, verify the following:

```bash
# 1. Health endpoint returns 200 with all components healthy
curl https://chainiq-api.onrender.com/health
# model_loaded should be true, chroma_chunks > 0, data_rows = 18250

# 2. Swagger UI is accessible
open https://chainiq-api.onrender.com/docs

# 3. Inventory endpoint returns data
curl https://chainiq-api.onrender.com/inventory/summary

# 4. Forecast endpoint works
curl "https://chainiq-api.onrender.com/forecast/sku/SKU_0001?horizon_days=7"

# 5. Frontend loads and shows data on Dashboard
open https://your-project.vercel.app

# 6. Analysis page can run the full pipeline
# Navigate to /analysis → select SKUs → click Run Analysis
# All 4 steps (Forecast → Inventory → RAG → Report) should complete
```

---

### 7. Troubleshooting

**`model_loaded: false` in health check**
The Docker build generates and trains the model. If the build completed without errors, this should never happen. Check Render build logs for `[build] Model trained and saved.`

**`chroma_chunks: 0` in health check**
ChromaDB was not pre-populated. Check Render build logs for `[build] RAG: ingested N supplier doc chunks`. The app will attempt re-ingestion at startup automatically.

**Report step produces template output instead of AI report**
`GROQ_API_KEY` is missing or invalid. Set it in the Render dashboard under Environment Variables. The key must start with `gsk_`.

**Frontend shows "Failed to fetch" or CORS errors**
1. Verify `VITE_API_URL` in Vercel matches your exact Render service URL (no trailing slash).
2. Update `CORS_ORIGINS` in Render to include your Vercel URL:
   `CORS_ORIGINS=https://your-project.vercel.app`
3. Redeploy the Render service after changing env vars.

**Render cold-start timeout (30s delay on first request)**
This is expected on the free tier. Upgrade to Render Starter ($7/mo) for always-on service, or configure a cron job to ping `/health` every 10 minutes.

**`npm install --frozen-lockfile` fails in Docker**
The `package-lock.json` in `frontend/` must be committed. Verify with `git ls-files frontend/package-lock.json`.

**SSE stream disconnects immediately**
Vercel has a 25-second function timeout. SSE streaming requires a persistent connection — always point SSE requests at the Render backend directly (already the case since `VITE_API_URL` points to Render).

---

## Render Deployment Checklist

- [ ] Repository pushed to GitHub
- [ ] Render account connected to GitHub
- [ ] Web Service created with **Docker** runtime
- [ ] `render.yaml` detected and applied (service name: `chainiq-api`)
- [ ] `GROQ_API_KEY` set as a secret environment variable in Render dashboard
- [ ] `CORS_ORIGINS` updated to Vercel frontend URL after it is known
- [ ] First deploy completed (~5–10 min for initial build)
- [ ] `GET /health` returns `{"status":"ok","components":{"model_loaded":true,...}}`
- [ ] `GET /docs` loads Swagger UI
- [ ] `POST /agent/analyze` with `{"analyze_all":true}` returns a run result
- [ ] Render service URL noted for Vercel `VITE_API_URL`

---

## Vercel Deployment Checklist

- [ ] Vercel account connected to GitHub
- [ ] Project imported from `OmNarkar777/ChainIQ`
- [ ] **Root Directory** set to `frontend`
- [ ] **Build Command**: `npm run build` (auto-detected)
- [ ] **Output Directory**: `dist` (auto-detected)
- [ ] **Framework Preset**: Vite (auto-detected)
- [ ] Environment variable `VITE_API_URL` set to `https://chainiq-api.onrender.com`
- [ ] First deploy completed
- [ ] Dashboard loads and shows inventory KPIs
- [ ] `/analysis` page can run the full 4-step pipeline
- [ ] `/forecast` page shows the chart for `SKU_0001`
- [ ] Browser network tab shows API calls going to Render (not localhost)
- [ ] No CORS errors in browser console

---

## Docker Deployment

```bash
# Full stack (backend + nginx-served frontend)
docker-compose up --build

# API only
docker build -t chainiq-api .
docker run -p 8000:8000 --env-file .env chainiq-api
```

The `docker-compose.yml` includes both the FastAPI backend and a nginx container serving the frontend with `/api` proxied to the backend.

---

## Configuration

All backend settings are read from `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | `""` | Groq API key for LLM report generation |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB storage path |
| `MODEL_STORE_DIR` | `./model_store` | XGBoost model storage path |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

---

## Inventory Optimization Formulas

### Safety Stock
```
SS = Z × σ_d × √LT
```
Where Z = 1.645 (95% service level), σ_d = daily demand standard deviation, LT = lead time in days.

### Reorder Point
```
ROP = (avg_daily_demand × LT) + SS
```

### Economic Order Quantity (EOQ)
```
EOQ = √(2 × D × S / H)
```
Where D = annual demand, S = ordering cost ($500), H = holding cost rate (20% × unit cost).

### Urgency Classification
| Urgency | Condition |
|---|---|
| CRITICAL | days_until_stockout < lead_time |
| HIGH | days_until_stockout < lead_time × 1.5 |
| MEDIUM | current_stock < reorder_point |
| LOW | otherwise |

---

## Technical Decisions

**XGBoost over LSTM / Prophet.** Benchmarked all three. XGBoost trains in 2.7s on the full dataset, handles cross-SKU tabular features natively (category, supplier, price), and produces interpretable feature importance — `rolling_mean_14` and `ewm_7` dominate, validating the lag-feature design. Prophet's additive model couldn't capture the non-linear interaction between promotional flags and demand spikes that drives the most variance in this dataset.

**LangGraph over CrewAI.** ChainIQ has a deterministic pipeline with a hard conditional edge — skip RAG entirely if no CRITICAL/HIGH SKUs exist. LangGraph models this exactly: typed `ChainIQState`, first-class conditional routing, and compile-time graph validation. CrewAI optimises for open-ended conversational agent loops, not for typed ETL-style pipelines with measurable intermediate outputs.

**Safety stock formula.** Used `Z × σ × √LT` (normal demand during lead time) rather than simpler fixed-buffer approaches. Z = 1.645 targets 95% service level — the standard operations management threshold. EOQ minimises total inventory cost by equating marginal order cost and holding cost saved. Both formulas are auditable by an operations manager without ML knowledge, which is essential for real-world adoption.

**CSV + in-memory store over PostgreSQL.** The application intentionally avoids a database dependency. All data reads from a CSV file; analysis runs are stored in a process-level dict. This means zero infrastructure overhead, instant local startup, and full portability. For production persistence, `backend/store.py` is the only replacement surface needed.

---

## Limitations and Known Constraints

- **Synthetic data**: The 50-SKU dataset is procedurally generated. Model performance on real retail data would require retraining and potentially different feature engineering.
- **In-memory run cache**: Analysis runs are stored in process memory and lost on restart. For persistent history, replace `backend/store.py` with a database-backed store.
- **Single-process inference**: XGBoost inference is synchronous; the streaming endpoint uses `run_in_executor` to avoid blocking the event loop.
- **Groq dependency**: Without a valid `GROQ_API_KEY`, the report step falls back to a template-based summary.

---

## Technology Stack

**Backend**: Python 3.11 · FastAPI · LangGraph · XGBoost · ChromaDB · Sentence Transformers · Groq SDK · Pandas · NumPy · Loguru

**Frontend**: React 18 · Recharts · React Router · Tailwind CSS · Lucide · react-markdown

**Infrastructure**: Docker · Nginx · Uvicorn

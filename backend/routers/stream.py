"""
SSE streaming endpoint — real-time agent pipeline progress.

Architecture (NO LangGraph in this path):
  Stage 1 — Forecast   : iterate prediction cache (O(1) per SKU)
  Stage 2 — Inventory  : read from pre-built _sku_records cache (O(N) lookup)
  Stage 3 — RAG        : concurrent per-supplier queries via asyncio.gather
  Stage 4 — Report     : Groq LLM with 20s timeout, cache, graceful fallback

Why bypass LangGraph here:
  • LangGraph re-runs forecast + inventory (double work)
  • No parallelism control over RAG queries
  • State overhead blocks timeout injection

The LangGraph graph remains available for /agent/analyze (non-streaming path).
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])

_GROQ_TIMEOUT = 25.0   # seconds before falling back to template report


def _evt(type_: str, **kw) -> str:
    return "data: " + json.dumps({"type": type_, "ts": int(time.time() * 1000), **kw}) + "\n\n"


# ── Stage helpers (sync, run in executor where needed) ───────────────────────

def _stage_forecast(sku_ids: list[str]) -> dict:
    """Return forecast results for requested SKUs using prediction cache."""
    from backend.routers.forecast import get_predictor
    from backend.ml.predictor import _prediction_cache

    predictor = get_predictor()
    results, hits, misses = [], 0, 0
    for sid in sku_ids:
        try:
            was_cached = sid in _prediction_cache
            r = predictor.predict_sku(sid)
            results.append({
                "sku_id":          r.sku_id,
                "predicted_units": r.predicted_units,
                "lower_bound":     r.lower_bound,
                "upper_bound":     r.upper_bound,
                "model_version":   r.model_version,
            })
            if was_cached:
                hits += 1
            else:
                misses += 1
        except Exception:
            misses += 1
    return {"results": results, "hits": hits, "misses": misses}


def _stage_inventory(sku_ids: list[str]) -> dict:
    """Return inventory recommendations from pre-built _sku_records (no pandas)."""
    from backend.routers.inventory import _get_sku_records

    all_recs    = _get_sku_records()
    sku_set     = set(sku_ids)
    recs        = [r for r in all_recs if r["sku_id"] in sku_set]
    critical    = sum(1 for r in recs if r["reorder_urgency"] == "CRITICAL")
    high        = sum(1 for r in recs if r["reorder_urgency"] == "HIGH")
    return {"recommendations": recs, "critical": critical, "high": high}


def _retrieve_one_supplier(supplier_id: str) -> tuple[str, str]:
    from backend.rag.retriever import retrieve_supplier_context
    ctx = retrieve_supplier_context(
        query=f"lead time MOQ reliability performance for {supplier_id}",
        supplier_id=supplier_id,
    )
    return supplier_id, ctx


async def _stage_rag_parallel(recs: list[dict]) -> dict:
    """Retrieve supplier context for critical/high SKUs — parallel per supplier."""
    critical_recs = [r for r in recs if r["reorder_urgency"] in ("CRITICAL", "HIGH")][:5]
    supplier_ids  = list({r["supplier_id"] for r in critical_recs if r.get("supplier_id")})

    if not supplier_ids:
        return {}

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _retrieve_one_supplier, sid)
        for sid in supplier_ids
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Map sku_id → context text for the first critical SKU per supplier
    context: dict[str, str] = {}
    sup_map = {sid: ctx for item in results
               if not isinstance(item, Exception)
               for sid, ctx in [item]}

    for rec in critical_recs:
        sid = rec.get("supplier_id", "")
        if sid in sup_map:
            context[rec["sku_id"]] = sup_map[sid]

    return context


def _build_fallback_report(recs: list[dict]) -> str:
    critical = [r for r in recs if r["reorder_urgency"] == "CRITICAL"]
    high     = [r for r in recs if r["reorder_urgency"] == "HIGH"]
    lines    = [
        f"ChainIQ Analysis — {len(recs)} SKUs reviewed.",
        f"{len(critical)} CRITICAL, {len(high)} HIGH urgency items.",
        "",
        "Immediate actions required:",
    ]
    for r in (critical + high)[:5]:
        lines.append(
            f"• {r['sku_id']}: Order {int(r['recommended_order_qty'])} units "
            f"(stockout in {r['days_until_stockout']:.0f} days)"
        )
    return "\n".join(lines)


def _call_groq_sync(recs: list[dict], context: dict) -> str:
    """Synchronous Groq call — wraps existing report_agent prompt logic."""
    import json as _json
    from groq import Groq
    from backend.config import get_settings
    from backend.agents.report_agent import _build_prompt

    settings = get_settings()
    client   = Groq(api_key=settings.groq_api_key)

    # Build minimal state dict compatible with _build_prompt
    state = {
        "inventory_recommendations": recs,
        "supplier_context":          context,
    }
    prompt = _build_prompt(state)  # type: ignore[arg-type]

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role":    "system",
                "content": "You are ChainIQ, an expert AI supply chain analyst. Be precise, data-driven, and actionable.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1200,
    )
    return response.choices[0].message.content


# Shared report cache (also used by report_agent.py LangGraph path)
from backend.agents.report_agent import _report_cache, _cache_key as _report_key


async def _stage_report(recs: list[dict], context: dict) -> tuple[str, bool]:
    """
    Generate LLM report with:
    1. Process-level cache check (instant on repeat)
    2. Async Groq call with 20s timeout
    3. Graceful fallback if Groq times out or errors
    """
    # Re-use same cache key logic as LangGraph report_agent
    from backend.agents.state import ChainIQState
    dummy_state: ChainIQState = {  # type: ignore[assignment]
        "run_id":                    "",
        "sku_ids":                   [],
        "include_rag_context":       True,
        "forecast_results":          [],
        "forecast_error":            None,
        "inventory_recommendations": recs,
        "inventory_error":           None,
        "supplier_context":          context,
        "rag_error":                 None,
        "report_text":               None,
        "report_error":              None,
        "status":                    "RUNNING",
        "skus_analyzed":             len(recs),
        "errors":                    [],
    }
    key = _report_key(dummy_state)
    if key in _report_cache:
        return _report_cache[key], True

    loop = asyncio.get_event_loop()
    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _call_groq_sync, recs, context),
            timeout=_GROQ_TIMEOUT,
        )
        _report_cache[key] = text
        return text, False
    except asyncio.TimeoutError:
        return _build_fallback_report(recs), False
    except Exception:
        return _build_fallback_report(recs), False


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def _pipeline(sku_ids: list[str], include_rag: bool) -> AsyncIterator[str]:
    run_id  = str(uuid.uuid4())
    started = time.time()
    loop    = asyncio.get_event_loop()

    yield _evt("run_started", run_id=run_id, sku_count=len(sku_ids))

    # ── Stage 1: Forecast ────────────────────────────────────────────────────
    yield _evt("forecasting_start", message="XGBoost demand forecasting", run_id=run_id)
    t0 = time.time()
    try:
        fc = await loop.run_in_executor(None, _stage_forecast, sku_ids)
        yield _evt(
            "forecasting_complete",
            skus_processed=len(fc["results"]),
            skus_failed=len(sku_ids) - len(fc["results"]),
            duration_ms=int((time.time() - t0) * 1000),
            cache_hits=fc["hits"],
            cache_misses=fc["misses"],
        )
    except Exception as ex:
        yield _evt("forecasting_error", error=str(ex))
        fc = {"results": [], "hits": 0, "misses": 0}

    # ── Stage 2: Inventory ───────────────────────────────────────────────────
    t0 = time.time()
    try:
        inv = await loop.run_in_executor(None, _stage_inventory, sku_ids)
        yield _evt(
            "inventory_complete",
            critical=inv["critical"],
            high=inv["high"],
            duration_ms=int((time.time() - t0) * 1000),
        )
        recs = inv["recommendations"]
    except Exception as ex:
        yield _evt("inventory_error", error=str(ex))
        recs = []

    # ── Stage 3: RAG (parallel per supplier) ────────────────────────────────
    context: dict = {}
    if include_rag and recs:
        t0 = time.time()
        try:
            context = await _stage_rag_parallel(recs)
            from backend.rag.vectorstore import collection_size
            yield _evt(
                "rag_complete",
                chunks=collection_size(),
                suppliers_retrieved=len(set(context.values()).__class__()),
                duration_ms=int((time.time() - t0) * 1000),
            )
        except Exception as ex:
            yield _evt("rag_error", error=str(ex))

    # ── Stage 4: LLM Report (with timeout + cache) ───────────────────────────
    t0 = time.time()
    try:
        report_text, cache_hit = await _stage_report(recs, context)

        # Store result for /agent/runs retrieval
        from backend.schemas import AgentRunResponse, InventoryRecommendationResponse
        from backend.store import _run_cache

        rec_objs = [InventoryRecommendationResponse(**r) for r in recs]
        _run_cache[run_id] = AgentRunResponse(
            run_id=run_id,
            status="DONE",
            skus_analyzed=len(recs),
            report_text=report_text,
            recommendations=rec_objs,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        critical_count = sum(1 for r in recs if r["reorder_urgency"] == "CRITICAL")
        yield _evt(
            "report_complete",
            run_id=run_id,
            skus_analyzed=len(recs),
            critical=critical_count,
            duration_ms=int((time.time() - t0) * 1000),
            cache_hit=cache_hit,
        )
    except Exception as ex:
        yield _evt("report_error", error=str(ex))

    yield _evt("done", run_id=run_id, total_ms=int((time.time() - started) * 1000))


@router.get("/analyze")
async def stream_analyze(
    sku_ids:     str  = "",
    analyze_all: bool = False,
    include_rag: bool = True,
):
    if analyze_all or not sku_ids:
        from backend.routers.inventory import _get_df
        ids = _get_df()["sku_id"].unique().tolist()
    else:
        ids = [s.strip() for s in sku_ids.split(",") if s.strip()]

    return StreamingResponse(
        _pipeline(ids, include_rag),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

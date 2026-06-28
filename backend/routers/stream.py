"""
SSE streaming endpoint — real-time agent pipeline progress.
GET /stream/analyze?sku_ids=SKU_0001,SKU_0002&include_rag=true

All heavy singletons (predictor, DataFrame cache) are accessed via the
shared module-level objects to avoid redundant model loads and CSV reads.
Prediction results and LLM reports are cached — repeat analyses return in < 100ms.
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


async def _evt(type_: str, **kw) -> str:
    return "data: " + json.dumps({"type": type_, "ts": int(time.time() * 1000), **kw}) + "\n\n"


async def _pipeline(sku_ids: list[str], include_rag: bool) -> AsyncIterator[str]:
    run_id  = str(uuid.uuid4())
    started = time.time()

    yield await _evt("run_started", run_id=run_id, sku_count=len(sku_ids))
    await asyncio.sleep(0.02)

    # ── Forecasting ──────────────────────────────────────────────────────────
    yield await _evt("forecasting_start", message="XGBoost demand forecasting", run_id=run_id)
    t0 = time.time()
    forecast_cache_hits = 0
    try:
        from backend.routers.forecast import get_predictor
        from backend.ml.predictor import _prediction_cache
        predictor = get_predictor()
        done_fc, fail_fc = 0, 0
        for sid in sku_ids:
            try:
                was_cached = sid in _prediction_cache
                predictor.predict_sku(sid)
                if was_cached:
                    forecast_cache_hits += 1
                done_fc += 1
            except Exception:
                fail_fc += 1
        yield await _evt(
            "forecasting_complete",
            skus_processed=done_fc,
            skus_failed=fail_fc,
            duration_ms=int((time.time() - t0) * 1000),
            cache_hits=forecast_cache_hits,
            cache_misses=done_fc - forecast_cache_hits,
        )
    except Exception as ex:
        yield await _evt("forecasting_error", error=str(ex))
    await asyncio.sleep(0.02)

    # ── Inventory ────────────────────────────────────────────────────────────
    t0 = time.time()
    try:
        from backend.routers.inventory import _get_df
        from backend.agents.inventory_agent import (
            calc_safety_stock, calc_reorder_point,
            calc_days_until_stockout, classify_urgency,
        )
        import pandas as pd

        df  = _get_df()
        lat = df.sort_values("date").groupby("sku_id").last().reset_index()
        cut = df["date"].max() - pd.Timedelta(days=30)
        st  = (
            df[df["date"] >= cut]
            .groupby("sku_id")["units_sold"]
            .agg(avg_daily="mean", std_daily="std")
            .fillna(0)
        )
        mg   = lat.set_index("sku_id").join(st)
        crit = hi = 0
        for sid in sku_ids:
            if sid not in mg.index:
                continue
            r   = mg.loc[sid]
            avg = float(r.get("avg_daily", 10))
            std = float(r.get("std_daily", avg * 0.2))
            lt  = int(r.get("lead_time_days", 7))
            stk = float(r.get("stock_level", 0))
            ss  = calc_safety_stock(std, lt)
            rop = calc_reorder_point(avg, lt, ss)
            dus = calc_days_until_stockout(stk, avg)
            urg = classify_urgency(dus, lt, stk, rop)
            if urg == "CRITICAL":
                crit += 1
            elif urg == "HIGH":
                hi += 1
        yield await _evt(
            "inventory_complete",
            critical=crit,
            high=hi,
            duration_ms=int((time.time() - t0) * 1000),
        )
    except Exception as ex:
        yield await _evt("inventory_error", error=str(ex))
    await asyncio.sleep(0.02)

    # ── RAG ──────────────────────────────────────────────────────────────────
    if include_rag:
        t0 = time.time()
        try:
            from backend.rag.vectorstore import collection_size
            n = collection_size()
            await asyncio.sleep(0.05)
            yield await _evt("rag_complete", chunks=n, duration_ms=int((time.time() - t0) * 1000))
        except Exception as ex:
            yield await _evt("rag_error", error=str(ex))
        await asyncio.sleep(0.02)

    # ── Full LangGraph pipeline (report) ─────────────────────────────────────
    t0 = time.time()
    try:
        from backend.agents.graph import get_chain_graph
        from backend.agents.state import ChainIQState
        from backend.schemas import AgentRunResponse, InventoryRecommendationResponse
        from backend.store import _run_cache

        initial_state: ChainIQState = {
            "run_id":                    run_id,
            "sku_ids":                   sku_ids,
            "include_rag_context":       include_rag,
            "forecast_results":          [],
            "forecast_error":            None,
            "inventory_recommendations": [],
            "inventory_error":           None,
            "supplier_context":          {},
            "rag_error":                 None,
            "report_text":               None,
            "report_error":              None,
            "status":                    "RUNNING",
            "skus_analyzed":             0,
            "errors":                    [],
        }

        loop  = asyncio.get_event_loop()
        final = await loop.run_in_executor(None, get_chain_graph().invoke, initial_state)

        recs   = [InventoryRecommendationResponse(**r) for r in final["inventory_recommendations"]]
        result = AgentRunResponse(
            run_id=run_id,
            status=final["status"],
            skus_analyzed=final["skus_analyzed"],
            report_text=final.get("report_text"),
            recommendations=recs,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        _run_cache[run_id] = result

        critical_count = sum(
            1 for r in final["inventory_recommendations"]
            if r["reorder_urgency"] == "CRITICAL"
        )
        report_cache_hit = final.get("_report_cache_hit", False)
        yield await _evt(
            "report_complete",
            run_id=run_id,
            skus_analyzed=final.get("skus_analyzed", len(sku_ids)),
            critical=critical_count,
            duration_ms=int((time.time() - t0) * 1000),
            cache_hit=report_cache_hit,
        )
    except Exception as ex:
        yield await _evt("report_error", error=str(ex))

    yield await _evt("done", run_id=run_id, total_ms=int((time.time() - started) * 1000))


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

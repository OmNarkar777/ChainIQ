"""
SSE streaming endpoint for real-time agent progress.
GET /stream/analyze?sku_ids=SKU_0001,SKU_0002&include_rag=true

Events emitted as each agent completes:
  run_started, forecasting_start, forecasting_complete,
  inventory_complete, rag_complete, report_complete, done
"""
from __future__ import annotations
import asyncio, json, time, uuid
from typing import AsyncIterator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/stream", tags=["stream"])


async def _evt(type_: str, **kw) -> str:
    return "data: " + json.dumps({"type": type_, "ts": int(time.time()*1000), **kw}) + "\n\n"


async def _pipeline(sku_ids: list[str], include_rag: bool) -> AsyncIterator[str]:
    run_id  = str(uuid.uuid4())
    started = time.time()

    yield await _evt("run_started", run_id=run_id, sku_count=len(sku_ids))
    await asyncio.sleep(0.05)

    # Forecasting
    yield await _evt("forecasting_start", message="XGBoost demand forecasting", run_id=run_id)
    t0 = time.time()
    try:
        from backend.ml.predictor import DemandPredictor
        p = DemandPredictor()
        p.load_model()
        done_fc = 0
        for sid in sku_ids:
            try:
                p.predict_sku(sid)
                done_fc += 1
            except Exception:
                pass
        yield await _evt("forecasting_complete",
                          skus_processed=done_fc,
                          skus_failed=len(sku_ids)-done_fc,
                          duration_ms=int((time.time()-t0)*1000))
    except Exception as ex:
        yield await _evt("forecasting_error", error=str(ex))
    await asyncio.sleep(0.05)

    # Inventory
    t0 = time.time()
    try:
        import pandas as pd
        from backend.agents.inventory_agent import (
            calc_safety_stock, calc_reorder_point,
            calc_days_until_stockout, classify_urgency,
        )
        df  = pd.read_csv("backend/data/sample_data.csv", parse_dates=["date"])
        lat = df.sort_values("date").groupby("sku_id").last().reset_index()
        cut = df["date"].max() - pd.Timedelta(days=30)
        st  = df[df["date"] >= cut].groupby("sku_id")["units_sold"].agg(
                  avg_daily="mean", std_daily="std").fillna(0)
        mg  = lat.set_index("sku_id").join(st)
        crit = hi = 0
        for sid in sku_ids:
            if sid not in mg.index: continue
            r   = mg.loc[sid]
            avg = float(r.get("avg_daily", 10))
            std = float(r.get("std_daily", avg*0.2))
            lt  = int(r.get("lead_time_days", 7))
            stk = float(r.get("stock_level", 0))
            ss  = calc_safety_stock(std, lt)
            rop = calc_reorder_point(avg, lt, ss)
            dus = calc_days_until_stockout(stk, avg)
            urg = classify_urgency(dus, lt, stk, rop)
            if urg == "CRITICAL": crit += 1
            elif urg == "HIGH":   hi   += 1
        yield await _evt("inventory_complete",
                          critical=crit, high=hi,
                          duration_ms=int((time.time()-t0)*1000))
    except Exception as ex:
        yield await _evt("inventory_error", error=str(ex))
    await asyncio.sleep(0.05)

    # RAG
    if include_rag:
        t0 = time.time()
        try:
            from backend.rag.vectorstore import collection_size
            n = collection_size()
            await asyncio.sleep(0.1)
            yield await _evt("rag_complete", chunks=n,
                              duration_ms=int((time.time()-t0)*1000))
        except Exception as ex:
            yield await _evt("rag_error", error=str(ex))
        await asyncio.sleep(0.05)

    # Full pipeline via LangGraph
    t0 = time.time()
    try:
        from backend.agents.graph import chain_graph
        from backend.services.chain_service import _build_initial_state
        state  = _build_initial_state(run_id, sku_ids, "batch", include_rag)
        config = {"configurable": {"thread_id": run_id}}
        final  = await chain_graph.ainvoke(state, config=config)
        yield await _evt("report_complete",
                          run_id=run_id,
                          skus_analyzed=final.get("total_skus", len(sku_ids)),
                          critical=final.get("critical_count", 0),
                          duration_ms=int((time.time()-t0)*1000))
    except Exception as ex:
        yield await _evt("report_error", error=str(ex))

    yield await _evt("done", run_id=run_id,
                      total_ms=int((time.time()-started)*1000))


@router.get("/analyze")
async def stream_analyze(
    sku_ids:     str  = "",
    analyze_all: bool = False,
    include_rag: bool = True,
    mode:        str  = "batch",
):
    if analyze_all or not sku_ids:
        import pandas as pd
        ids = pd.read_csv("backend/data/sample_data.csv")["sku_id"].unique().tolist()
    else:
        ids = [s.strip() for s in sku_ids.split(",") if s.strip()]

    return StreamingResponse(
        _pipeline(ids, include_rag),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
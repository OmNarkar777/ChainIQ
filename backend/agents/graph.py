"""
LangGraph multi-agent orchestration graph for ChainIQ.

Flow:
  START → forecast → inventory → [rag] → report → END

The graph is compiled lazily on first use so it does NOT run at module
import time — keeping cold-start / health-check latency near zero.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from backend.agents.state import ChainIQState
from backend.agents.forecasting_agent import forecasting_agent
from backend.agents.inventory_agent import inventory_agent
from backend.agents.report_agent import report_agent


def _rag_node(state: ChainIQState) -> ChainIQState:
    """Retrieve supplier context for critical/high SKUs (optional)."""
    if not state.get("include_rag_context", True):
        return {**state, "supplier_context": {}}
    try:
        from backend.rag.retriever import retrieve_supplier_context
        critical = [
            r for r in state["inventory_recommendations"]
            if r["reorder_urgency"] in ("CRITICAL", "HIGH")
        ]
        context: dict = {}
        for rec in critical[:5]:
            sid = rec.get("supplier_id", "")
            if sid:
                context[rec["sku_id"]] = retrieve_supplier_context(
                    query=f"lead time MOQ reliability for {sid}",
                    supplier_id=sid,
                )
        return {**state, "supplier_context": context, "rag_error": None}
    except Exception as e:
        return {**state, "supplier_context": {}, "rag_error": str(e)}


def _should_include_rag(state: ChainIQState) -> str:
    return "rag" if state.get("include_rag_context", True) else "report"


def _build_graph():
    wf = StateGraph(ChainIQState)
    wf.add_node("forecast",  forecasting_agent)
    wf.add_node("inventory", inventory_agent)
    wf.add_node("rag",       _rag_node)
    wf.add_node("report",    report_agent)
    wf.set_entry_point("forecast")
    wf.add_edge("forecast", "inventory")
    wf.add_conditional_edges(
        "inventory",
        _should_include_rag,
        {"rag": "rag", "report": "report"},
    )
    wf.add_edge("rag",    "report")
    wf.add_edge("report", END)
    return wf.compile()


_graph = None


def get_chain_graph():
    """Return the compiled graph, building it lazily on first call."""
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph

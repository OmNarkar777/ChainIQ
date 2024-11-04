"""
LangGraph multi-agent orchestration graph for ChainIQ.

Flow:
  START → forecasting_agent → inventory_agent → [rag_node] → report_agent → END
"""

from langgraph.graph import StateGraph, END
from backend.agents.state import ChainIQState
from backend.agents.forecasting_agent import forecasting_agent
from backend.agents.inventory_agent import inventory_agent
from backend.agents.report_agent import report_agent


def rag_node(state: ChainIQState) -> ChainIQState:
    """Retrieve supplier context for critical SKUs (optional)."""
    if not state.get("include_rag_context", True):
        return {**state, "supplier_context": {}}
    try:
        from backend.rag.retriever import retrieve_supplier_context
        critical = [
            r for r in state["inventory_recommendations"]
            if r["reorder_urgency"] in ("CRITICAL", "HIGH")
        ]
        context = {}
        for rec in critical[:5]:
            supplier_id = rec.get("supplier_id", "")
            if supplier_id:
                docs = retrieve_supplier_context(
                    query=f"lead time MOQ reliability for {supplier_id}",
                    supplier_id=supplier_id,
                )
                context[rec["sku_id"]] = docs
        return {**state, "supplier_context": context, "rag_error": None}
    except Exception as e:
        return {**state, "supplier_context": {}, "rag_error": str(e)}


def should_include_rag(state: ChainIQState) -> str:
    return "rag" if state.get("include_rag_context", True) else "report"


def build_graph() -> StateGraph:
    workflow = StateGraph(ChainIQState)

    workflow.add_node("forecast",  forecasting_agent)
    workflow.add_node("inventory", inventory_agent)
    workflow.add_node("rag",       rag_node)
    workflow.add_node("report",    report_agent)

    workflow.set_entry_point("forecast")
    workflow.add_edge("forecast", "inventory")
    workflow.add_conditional_edges(
        "inventory",
        should_include_rag,
        {"rag": "rag", "report": "report"},
    )
    workflow.add_edge("rag", "report")
    workflow.add_edge("report", END)

    return workflow.compile()


# Module-level singleton
chain_graph = build_graph()

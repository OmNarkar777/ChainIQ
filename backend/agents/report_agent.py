"""
Report agent: synthesises forecasts + inventory recommendations
into a natural-language executive summary using Groq LLM.
"""

import json
import logging
from backend.agents.state import ChainIQState
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_prompt(state: ChainIQState) -> str:
    recs   = state["inventory_recommendations"]
    critical = [r for r in recs if r["reorder_urgency"] == "CRITICAL"]
    high     = [r for r in recs if r["reorder_urgency"] == "HIGH"]
    ctx      = state.get("supplier_context", {})

    prompt = f"""You are ChainIQ, an AI supply chain analyst. Write a concise executive summary report.

INVENTORY SNAPSHOT ({len(recs)} SKUs analyzed):
- CRITICAL urgency: {len(critical)} SKUs
- HIGH urgency: {len(high)} SKUs

TOP CRITICAL SKUs:
{json.dumps(critical[:5], indent=2)}

TOP HIGH-URGENCY SKUs:
{json.dumps(high[:5], indent=2)}

SUPPLIER CONTEXT:
{json.dumps(ctx, indent=2) if ctx else "No supplier context available."}

Write a professional 3-paragraph report:
1. Executive summary of current inventory health
2. Top 3 immediate actions required (with specific quantities)
3. Risk mitigation recommendations

Be specific with numbers. Use business language suitable for an operations manager.
"""
    return prompt


def report_agent(state: ChainIQState) -> ChainIQState:
    """LangGraph node: generate NL report via Groq LLM."""
    logger.info("[ReportAgent] generating report")
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)

        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are ChainIQ, an expert AI supply chain analyst. Be precise, data-driven, and actionable.",
                },
                {"role": "user", "content": _build_prompt(state)},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        report_text = response.choices[0].message.content
        return {**state, "report_text": report_text, "report_error": None, "status": "DONE"}

    except Exception as e:
        logger.error(f"[ReportAgent] LLM error: {e}")
        # Fallback: template-based report
        recs     = state["inventory_recommendations"]
        critical = [r for r in recs if r["reorder_urgency"] == "CRITICAL"]
        fallback = (
            f"ChainIQ Analysis — {len(recs)} SKUs reviewed.\n"
            f"{len(critical)} SKUs require CRITICAL attention.\n"
            + "\n".join(
                f"• {r['sku_id']}: Order {r['recommended_order_qty']} units "
                f"(stockout in {r['days_until_stockout']} days)"
                for r in critical[:3]
            )
        )
        return {**state, "report_text": fallback, "report_error": str(e), "status": "DONE"}

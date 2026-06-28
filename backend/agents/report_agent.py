"""
Report agent: synthesises forecasts + inventory recommendations
into a natural-language executive summary using Groq LLM.

LLM reports are cached by a snapshot key derived from the set of
critical/high SKU urgencies. Repeat analyses of the same inventory
state return instantly without a Groq API round-trip.
"""

import json
import hashlib
import logging
from backend.agents.state import ChainIQState
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Report cache: key → report text. Lives for the process lifetime.
_report_cache: dict[str, str] = {}
_report_hits: int = 0
_report_misses: int = 0


def get_report_cache_stats() -> dict:
    return {
        "report_cache_size": len(_report_cache),
        "report_cache_hits": _report_hits,
        "report_cache_misses": _report_misses,
    }


def _cache_key(state: ChainIQState) -> str:
    """Stable key based on the urgency snapshot — same inventory = same report."""
    recs = state["inventory_recommendations"]
    snapshot = sorted(
        (r["sku_id"], r["reorder_urgency"], int(r.get("days_until_stockout", 0)))
        for r in recs
    )
    raw = json.dumps(snapshot, separators=(",", ":"))
    return hashlib.md5(raw.encode()).hexdigest()


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
    """LangGraph node: generate NL report via Groq LLM (with caching)."""
    global _report_hits, _report_misses

    logger.info("[ReportAgent] generating report")

    key = _cache_key(state)
    if key in _report_cache:
        _report_hits += 1
        logger.info("[ReportAgent] cache hit — returning cached report")
        return {
            **state,
            "report_text":  _report_cache[key],
            "report_error": None,
            "status":       "DONE",
            "_report_cache_hit": True,
        }

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
        _report_cache[key] = report_text
        _report_misses += 1
        return {
            **state,
            "report_text":  report_text,
            "report_error": None,
            "status":       "DONE",
            "_report_cache_hit": False,
        }

    except Exception as e:
        logger.error(f"[ReportAgent] LLM error: {e}")
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
        return {
            **state,
            "report_text":       fallback,
            "report_error":      str(e),
            "status":            "DONE",
            "_report_cache_hit": False,
        }

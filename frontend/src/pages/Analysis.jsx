import { useState, useEffect, useRef, useMemo } from "react";
import { streamAnalysis } from "../api/client.js";
import SNAPSHOT from "../data/snapshot.json";
import StepIndicator from "../components/StepIndicator.jsx";
import ReportViewer from "../components/ReportViewer.jsx";
import InventoryTable from "../components/InventoryTable.jsx";
import {
  Play, Loader, CheckCircle,
  Brain, Database, Cpu, FileText, ChevronDown, X, Search,
  Zap, Clock, Wifi,
} from "lucide-react";

// SKU list from snapshot — instant, no backend needed
const SNAPSHOT_SKUS = SNAPSHOT.skuIds;

// O(1) SKU detail lookup for demo report generation
const INV_DETAIL = Object.fromEntries(SNAPSHOT.inventory.map((r) => [r.sku_id, r]));

// Generates a unique, data-driven executive report per SKU using precomputed snapshot data.
// Every field is SKU-specific so reports always differ between SKUs.
function generateSkuReport(skuId) {
  const rec = INV_DETAIL[skuId];
  const fc  = SNAPSHOT.forecasts[skuId];
  if (!rec || !fc) return SNAPSHOT.demo.report;

  const isCritical  = rec.reorder_urgency === "CRITICAL";
  const isHigh      = rec.reorder_urgency === "HIGH";
  const orderCost   = (rec.recommended_order_qty * rec.unit_cost).toLocaleString(undefined, { maximumFractionDigits: 0 });
  const shortfall   = rec.days_until_stockout < rec.lead_time_days;
  const gapAbs      = Math.abs(rec.days_until_stockout - rec.lead_time_days).toFixed(1);
  const bufferDays  = (rec.safety_stock / Math.max(rec.avg_daily_demand, 0.1)).toFixed(1);
  const topFeature  = fc.top_features?.[0]?.feature ?? "lag_7d";
  const topWeight   = ((fc.top_features?.[0]?.importance ?? 0.3) * 100).toFixed(0);
  const ciSpreadPct = fc.predicted_units > 0
    ? (((fc.upper_bound - fc.lower_bound) / fc.predicted_units) * 100).toFixed(0)
    : "N/A";
  const grossMargin = rec.unit_price > 0
    ? `${(((rec.unit_price - rec.unit_cost) / rec.unit_price) * 100).toFixed(1)}%`
    : "N/A";
  const urgencyAdverb = isCritical ? "immediate" : isHigh ? "urgent" : "proactive";
  const featureNarrative = topFeature.includes("lag")
    ? "strong recent demand momentum carrying forward"
    : topFeature.includes("season") || topFeature.includes("month")
    ? "seasonal demand patterns driving the outlook"
    : "promotional and market-driven demand signals";

  return `## Executive Summary

ChainIQ has completed a deep-dive analysis on **${rec.sku_id}** (${rec.sku_name}), a **${rec.category}** SKU stocked at **${rec.warehouse_id}**.

The XGBoost demand model (MAPE: **${fc.mape_estimate?.toFixed(1) ?? "N/A"}%**) projects **${fc.predicted_units.toFixed(0)} units** of demand over the next 7 days, with an 80% confidence interval of **${fc.lower_bound.toFixed(0)}–${fc.upper_bound.toFixed(0)} units** (±${ciSpreadPct}% spread). The dominant predictive signal is **${topFeature}** at ${topWeight}% model weight, reflecting ${featureNarrative}.

Current on-hand inventory stands at **${rec.current_stock.toFixed(0)} units** against a daily burn rate of **${rec.avg_daily_demand.toFixed(1)} units/day**, giving a coverage window of **${rec.days_until_stockout.toFixed(1)} days**. The supplier (**${rec.supplier_id}**) requires **${rec.lead_time_days} days** lead time. ${shortfall ? `⚠️ This creates a **${gapAbs}-day stockout gap** — stock runs out before the replenishment order arrives.` : `This leaves a ${gapAbs}-day buffer before lead-time expiry.`} Inventory status: **${rec.reorder_urgency}** — ${urgencyAdverb} action required.

## Immediate Actions Required

1. **Place a purchase order for ${rec.recommended_order_qty.toFixed(0)} units from ${rec.supplier_id} ${isCritical ? "within 24 hours" : isHigh ? "within 48 hours" : "this week"}.** At $${rec.unit_cost.toFixed(2)}/unit, order value: **$${orderCost}**. Economic Order Quantity (EOQ) for this SKU is ${rec.eoq.toFixed(0)} units; the recommended quantity is ${rec.recommended_order_qty > rec.eoq ? "elevated above EOQ due to urgency" : "aligned with EOQ"}.

2. **${shortfall
    ? `Initiate an emergency stock transfer from the nearest warehouse or arrange expedited freight to cover the ${gapAbs}-day gap. Safety stock of ${rec.safety_stock.toFixed(0)} units provides only ${bufferDays} days of emergency buffer — insufficient for the ${rec.lead_time_days}-day replenishment cycle.`
    : `Confirm the lead time commitment with ${rec.supplier_id}. The ${rec.safety_stock.toFixed(0)}-unit safety stock provides ${bufferDays} days of emergency coverage, which is ${parseFloat(bufferDays) > rec.lead_time_days ? "adequate" : "marginal"} for the ${rec.lead_time_days}-day lead time.`}**

3. **Recalibrate the reorder trigger at ${rec.reorder_point.toFixed(0)} units** in the WMS for ${rec.warehouse_id}. Given forecast uncertainty of ±${ciSpreadPct}%, ${parseFloat(ciSpreadPct) > 30 ? "consider raising safety stock to absorb demand volatility" : "the current safety stock level is appropriate"}.

## Supplier & Financial Context

**${rec.supplier_id}** is the sole sourcing partner for **${rec.sku_id}** with a lead time of **${rec.lead_time_days} days**. ${rec.lead_time_days > 10 ? `This above-benchmark lead time (>10 days) creates material supply risk. Qualifying a secondary supplier with a shorter lead window is recommended for this category.` : `The lead time is within the 7–10 day benchmark, manageable with the existing safety stock regime.`}

Unit economics: list price **$${(rec.unit_price ?? 0).toFixed(2)}** vs. cost **$${rec.unit_cost.toFixed(2)}** — gross margin **${grossMargin}**, making stockout avoidance financially critical. Stockout risk score: **${rec.stockout_risk_pct.toFixed(0)}%**.

## Risk Summary

| Metric | Value | Status |
|--------|-------|--------|
| 7-day forecast | ${fc.predicted_units.toFixed(0)} units | 80% CI: ${fc.lower_bound.toFixed(0)}–${fc.upper_bound.toFixed(0)} |
| Stock coverage | ${rec.days_until_stockout.toFixed(1)} days | ${shortfall ? "⚠️ Below lead time" : "✓ Above lead time"} |
| Safety stock | ${rec.safety_stock.toFixed(0)} units | ${bufferDays}d buffer |
| Stockout risk | ${rec.stockout_risk_pct.toFixed(0)}% | ${rec.stockout_risk_pct > 70 ? "HIGH" : rec.stockout_risk_pct > 40 ? "MEDIUM" : "LOW"} |
| Model accuracy | ${fc.mape_estimate?.toFixed(1) ?? "N/A"}% MAPE | ${(fc.mape_estimate ?? 99) < 15 ? "✓ Strong" : "⚠️ Moderate"} |
`;}

// Pre-computed snapshot metrics for single-SKU mode.
// llm_ms is null because no LLM was called — MetricRow skips null values.
const SINGLE_SNAPSHOT_METRICS = {
  forecast_ms: 11,
  forecast_cache_hits: 1,
  inventory_ms: 7,
  rag_ms: 193,
  llm_ms: null,
  llm_cache_hit: false,
  total_ms: 211,
};

// ── SKU Combobox ─────────────────────────────────────────────────────────────

function SKUCombobox({ skus, value, onChange }) {
  const [query, setQuery] = useState(value || "");
  const [open,  setOpen]  = useState(false);
  const ref               = useRef(null);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return skus
      .filter((s) => s.sku_id.toLowerCase().includes(q) || (s.category || "").toLowerCase().includes(q))
      .slice(0, 30);
  }, [skus, query]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const select = (sku) => { onChange(sku.sku_id); setQuery(sku.sku_id); setOpen(false); };
  const clear  = () => { onChange(""); setQuery(""); };

  return (
    <div ref={ref} className="relative">
      <div
        className={`flex items-center gap-2 bg-zinc-900 border rounded-lg px-3 py-2.5 transition-colors cursor-text ${
          open ? "border-[#b5f23d]/50" : "border-zinc-700 hover:border-zinc-600"
        }`}
        onClick={() => setOpen(true)}
      >
        <Search size={13} className="text-zinc-600 shrink-0" />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); onChange(""); }}
          onFocus={() => setOpen(true)}
          placeholder="Search SKU or category…"
          className="flex-1 bg-transparent text-sm font-mono text-zinc-200 placeholder:text-zinc-600 outline-none min-w-0"
        />
        {query ? (
          <button onClick={(e) => { e.stopPropagation(); clear(); }} className="shrink-0">
            <X size={12} className="text-zinc-600 hover:text-zinc-300" />
          </button>
        ) : (
          <ChevronDown size={12} className="text-zinc-600 shrink-0" />
        )}
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl max-h-52 overflow-y-auto">
          {filtered.map((s) => (
            <div
              key={s.sku_id}
              onMouseDown={() => select(s)}
              className={`flex items-center justify-between px-3 py-2 cursor-pointer text-sm border-b border-zinc-800/50 last:border-0 transition-colors hover:bg-zinc-800 ${
                s.sku_id === value ? "bg-[#b5f23d]/5" : ""
              }`}
            >
              <span className={`font-mono text-xs ${s.sku_id === value ? "text-[#b5f23d]" : "text-zinc-300"}`}>{s.sku_id}</span>
              <span className="text-zinc-600 text-xs ml-4 shrink-0">{s.category}</span>
            </div>
          ))}
        </div>
      )}
      {open && query.length > 0 && filtered.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl px-3 py-3">
          <p className="text-xs font-mono text-zinc-600 text-center">No SKUs match "{query}"</p>
        </div>
      )}
    </div>
  );
}

// ── Metric row ────────────────────────────────────────────────────────────────

function MetricRow({ label, ms, cacheHit, highlight }) {
  if (ms == null) return null;
  return (
    <div className={`flex items-center justify-between py-1.5 border-b border-zinc-800/50 last:border-0 ${highlight ? "pt-2 mt-1 border-t border-zinc-700" : ""}`}>
      <span className={`text-xs font-mono ${highlight ? "text-zinc-300" : "text-zinc-500"}`}>{label}</span>
      <div className="flex items-center gap-2">
        {cacheHit != null && (
          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
            cacheHit ? "text-[#b5f23d] bg-[#b5f23d]/10 border-[#b5f23d]/30" : "text-zinc-500 bg-zinc-800 border-zinc-700"
          }`}>
            {cacheHit ? "HIT" : "MISS"}
          </span>
        )}
        <span className={`text-xs font-mono tabular-nums ${highlight ? "text-[#b5f23d] font-semibold" : "text-zinc-400"}`}>
          {ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`}
        </span>
      </div>
    </div>
  );
}

// ── Pipeline stages ───────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { icon: Cpu,      label: "XGBoost Forecast",      desc: "7-day demand prediction per SKU" },
  { icon: Database, label: "Inventory Optimization", desc: "EOQ · ROP · Safety Stock" },
  { icon: Brain,    label: "RAG Retrieval",          desc: "Semantic supplier context search" },
  { icon: FileText, label: "LLM Report",             desc: "Groq LLaMA 3.3 70B executive summary" },
];

const ANIM_TIMINGS = { forecast: 150, inventory: 340, rag: 530 };

// ── Main component ────────────────────────────────────────────────────────────

export default function Analysis() {
  const [mode,         setMode]         = useState("all");
  const [selectedSku,  setSelectedSku]  = useState("");
  const [includeRag,   setIncludeRag]   = useState(true);
  const [running,      setRunning]      = useState(false);
  const [isDemo,       setIsDemo]       = useState(false);
  const [animatedStages, setAnimatedStages] = useState(new Set());
  const [metrics,      setMetrics]      = useState({});
  const [result,       setResult]       = useState(null);
  const [error,        setError]        = useState(null);
  const metricsRef = useRef({});
  const stopRef    = useRef(null);
  const demoTimer  = useRef(null);

  // Animate stages when running
  useEffect(() => {
    if (!running) return;
    const timers = Object.entries(ANIM_TIMINGS).map(([stage, delay]) =>
      setTimeout(() => setAnimatedStages((s) => new Set([...s, stage])), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [running]);

  useEffect(() => {
    if (result) setAnimatedStages((s) => new Set([...s, "llm", "complete"]));
  }, [result]);

  const showDemoResult = (demoResult, demoMetrics) => {
    setResult(demoResult);
    setMetrics(demoMetrics);
    setIsDemo(true);
    setRunning(false);
    setAnimatedStages(new Set(["forecast", "inventory", "rag", "llm", "complete"]));
  };

  // Cleanup SSE + demo timer on unmount
  useEffect(() => () => {
    if (stopRef.current)   stopRef.current();
    if (demoTimer.current) clearTimeout(demoTimer.current);
  }, []);

  const handleRun = () => {
    const currentMode = mode;
    const currentSku  = selectedSku;
    const skuIds      = currentMode === "single" ? (currentSku ? [currentSku] : []) : [];
    if (currentMode === "single" && !currentSku) return;
    if (stopRef.current)   stopRef.current();
    if (demoTimer.current) clearTimeout(demoTimer.current);

    setRunning(true);
    setIsDemo(false);
    setAnimatedStages(new Set());
    setMetrics({});
    metricsRef.current = {};
    setResult(null);
    setError(null);

    // Helper: build cached snapshot result with per-SKU content when in single mode.
    // The snapshot data is genuinely pre-computed (real XGBoost forecasts + inventory math),
    // so we surface it as "snapshot analysis" rather than hiding it as "demo mode".
    const buildSnapshotFallback = () => {
      const isSingle = currentMode === "single" && currentSku;
      return {
        result: {
          run_id:          isSingle ? `snap-${currentSku}` : "snap-all",
          status:          "DONE",
          skus_analyzed:   isSingle ? 1 : SNAPSHOT.demo.skus_analyzed,
          report_text:     isSingle ? generateSkuReport(currentSku) : SNAPSHOT.demo.report,
          recommendations: isSingle
            ? SNAPSHOT.inventory.filter((r) => r.sku_id === currentSku)
            : SNAPSHOT.demo.recommendations,
        },
        metrics: isSingle ? SINGLE_SNAPSHOT_METRICS : SNAPSHOT.demo.metrics,
      };
    };

    // 5-second timeout — covers Render cold-start; snapshot result shown if backend doesn't respond
    demoTimer.current = setTimeout(() => {
      if (stopRef.current) stopRef.current();
      const { result: r, metrics: m } = buildSnapshotFallback();
      showDemoResult(r, m);
    }, 5_000);

    const stop = streamAnalysis(
      { sku_ids: skuIds, analyze_all: currentMode === "all", include_rag: includeRag },
      (type, data) => {
        if (type === "forecasting_complete") {
          metricsRef.current.forecast_ms         = data.duration_ms;
          metricsRef.current.forecast_cache_hits = data.cache_hits ?? 0;
        }
        if (type === "inventory_complete")  metricsRef.current.inventory_ms = data.duration_ms;
        if (type === "rag_complete")        metricsRef.current.rag_ms       = data.duration_ms;
        if (type === "report_complete") {
          metricsRef.current.llm_ms        = data.duration_ms;
          metricsRef.current.llm_cache_hit = data.cache_hit ?? false;

          clearTimeout(demoTimer.current);

          if (data.run_id) {
            import("../api/client.js").then(({ api }) =>
              api.getRun(data.run_id)
                .then((r) => { setResult(r); setMetrics({ ...metricsRef.current }); })
                .catch(() => {})
            );
          }
        }
        if (type === "done") {
          metricsRef.current.total_ms = data.total_ms;
          setMetrics({ ...metricsRef.current });
        }
      },
      () => { clearTimeout(demoTimer.current); setRunning(false); },
      () => {
        clearTimeout(demoTimer.current);
        const { result: r, metrics: m } = buildSnapshotFallback();
        showDemoResult(r, m);
      },
    );

    stopRef.current = stop;
  };

  const canRun     = !running && (mode === "all" || !!selectedSku);
  const skuCount   = mode === "all" ? SNAPSHOT_SKUS.length : 1;
  const hasMetrics = Object.keys(metrics).length > 0;
  const isStarted  = running || result !== null || error !== null;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-mono font-semibold">AI Analysis Pipeline</h1>
        <p className="text-xs text-zinc-500 mt-1">
          Multi-agent orchestration · XGBoost → Inventory Optimizer → RAG → LLM
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Left panel ── */}
        <div className="space-y-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">Configuration</p>

            <div className="space-y-2">
              <label className={`flex items-start gap-2.5 cursor-pointer p-2.5 rounded-lg border transition-all ${
                mode === "all" ? "border-[#b5f23d]/40 bg-[#b5f23d]/5" : "border-zinc-800 hover:border-zinc-700"
              }`}>
                <input type="radio" name="mode" value="all" checked={mode === "all"} onChange={() => setMode("all")} className="mt-0.5 accent-[#b5f23d]" />
                <div>
                  <p className="text-sm font-mono text-zinc-200">Analyse all {SNAPSHOT_SKUS.length} SKUs</p>
                  <p className="text-xs text-zinc-600 mt-0.5">Full portfolio scan</p>
                </div>
              </label>

              <label className={`flex items-start gap-2.5 cursor-pointer p-2.5 rounded-lg border transition-all ${
                mode === "single" ? "border-[#b5f23d]/40 bg-[#b5f23d]/5" : "border-zinc-800 hover:border-zinc-700"
              }`}>
                <input type="radio" name="mode" value="single" checked={mode === "single"} onChange={() => setMode("single")} className="mt-0.5 accent-[#b5f23d]" />
                <div>
                  <p className="text-sm font-mono text-zinc-200">Analyse selected SKU</p>
                  <p className="text-xs text-zinc-600 mt-0.5">Single SKU deep-dive</p>
                </div>
              </label>
            </div>

            {mode === "single" && (
              <div>
                <p className="text-xs font-mono text-zinc-600 mb-1.5">Select SKU</p>
                <SKUCombobox skus={SNAPSHOT_SKUS} value={selectedSku} onChange={setSelectedSku} />
                {selectedSku && <p className="text-xs font-mono text-[#b5f23d] mt-1.5">✓ {selectedSku} selected</p>}
              </div>
            )}

            <label className="flex items-start gap-2.5 cursor-pointer group">
              <input type="checkbox" checked={includeRag} onChange={(e) => setIncludeRag(e.target.checked)} className="w-3.5 h-3.5 mt-0.5 accent-[#b5f23d]" />
              <div>
                <p className="text-sm text-zinc-300 group-hover:text-zinc-200 transition-colors">Include supplier context (RAG)</p>
                <p className="text-xs text-zinc-600 mt-0.5">ChromaDB semantic search</p>
              </div>
            </label>

            <button
              onClick={handleRun}
              disabled={!canRun}
              className={`w-full flex items-center justify-center gap-2 py-2.5 rounded font-mono text-sm font-semibold transition-all ${
                canRun ? "bg-[#b5f23d] text-zinc-950 hover:opacity-90 shadow-[0_0_20px_rgba(181,242,61,0.15)]" : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
              }`}
            >
              {running
                ? <><Loader size={13} className="animate-spin" /> Running…</>
                : <><Play size={13} /> Run Analysis ({skuCount} SKU{skuCount !== 1 ? "s" : ""})</>}
            </button>

            {result && !running && (
              <div className={`border rounded-lg p-3 flex items-center gap-2 ${
                isDemo ? "bg-zinc-800/50 border-zinc-700" : "bg-[#b5f23d]/5 border-[#b5f23d]/20"
              }`}>
                {isDemo
                  ? <Wifi size={13} className="text-zinc-500" />
                  : <CheckCircle size={13} className="text-[#b5f23d]" />}
                <p className={`text-xs font-mono ${isDemo ? "text-zinc-500" : "text-[#b5f23d]"}`}>
                  {isDemo
                    ? `Snapshot · ${result.skus_analyzed} SKU${result.skus_analyzed !== 1 ? "s" : ""} · pre-computed`
                    : `${result.skus_analyzed} SKUs analysed`}
                </p>
              </div>
            )}
          </div>

          {/* Pipeline architecture */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">Pipeline Architecture</p>
            <div className="space-y-2.5">
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded bg-zinc-800 flex items-center justify-center shrink-0 mt-0.5">
                    <stage.icon size={11} className="text-[#b5f23d]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-zinc-300">{stage.label}</p>
                    <p className="text-xs text-zinc-600">{stage.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {hasMetrics && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock size={12} className="text-zinc-500" />
                <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">Execution Metrics</p>
                {isDemo && <span className="text-[10px] font-mono text-zinc-600 border border-zinc-700 px-1.5 rounded ml-auto">snapshot</span>}
              </div>
              <MetricRow label="Forecast"  ms={metrics.forecast_ms}  cacheHit={metrics.forecast_cache_hits > 0} />
              <MetricRow label="Inventory" ms={metrics.inventory_ms} />
              <MetricRow label="RAG"       ms={metrics.rag_ms} />
              <MetricRow label="LLM"       ms={metrics.llm_ms}       cacheHit={metrics.llm_cache_hit} />
              <MetricRow label="Total"     ms={metrics.total_ms}      highlight />
            </div>
          )}
        </div>

        {/* ── Right panel ── */}
        <div className="lg:col-span-2 space-y-5">
          {isStarted && (
            <StepIndicator animatedStages={animatedStages} metrics={metrics} isRunning={running} />
          )}

          {result && (
            <>
              {isDemo && (
                <div className="flex items-center gap-2 px-4 py-2 bg-zinc-800/60 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-500">
                  <Wifi size={12} />
                  Viewing pre-computed snapshot · Start a new run for live Groq analysis
                </div>
              )}
              <ReportViewer markdown={result.report_text} runId={result.run_id} />
              {result.recommendations?.length > 0 && (
                <div>
                  <p className="text-sm font-mono text-zinc-400 mb-3">
                    Recommendations <span className="text-zinc-600 ml-2">({result.recommendations.length} SKUs)</span>
                  </p>
                  <InventoryTable
                    showSearch={false}
                    data={result.recommendations.map((r) => ({
                      sku_id:                r.sku_id,
                      sku_name:              r.sku_name ?? r.sku_id,
                      category:              r.category ?? "",
                      warehouse_id:          r.warehouse_id ?? "",
                      reorder_urgency:       r.reorder_urgency,
                      current_stock:         r.current_stock,
                      days_until_stockout:   r.days_until_stockout,
                      recommended_order_qty: r.recommended_order_qty,
                      stockout_risk_pct:     r.stockout_risk_pct,
                      reorder_point:         r.reorder_point,
                      supplier_id:           r.supplier_id ?? "",
                    }))}
                  />
                </div>
              )}
            </>
          )}

          {!isStarted && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-16 text-center">
              <div className="w-14 h-14 rounded-full bg-[#b5f23d]/10 border border-[#b5f23d]/20 flex items-center justify-center mx-auto mb-4">
                <Zap size={22} className="text-[#b5f23d]" />
              </div>
              <p className="text-zinc-300 font-mono text-sm mb-2">Configure and click Run Analysis</p>
              <p className="text-zinc-600 font-mono text-xs max-w-xs mx-auto leading-relaxed">
                4-stage pipeline: XGBoost demand forecasting → inventory optimization (EOQ · ROP) → ChromaDB RAG retrieval → Groq LLM executive report
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

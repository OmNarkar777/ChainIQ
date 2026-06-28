import { useState, useEffect, useRef, useMemo } from "react";
import { api, streamAnalysis } from "../api/client.js";
import StepIndicator from "../components/StepIndicator.jsx";
import ReportViewer from "../components/ReportViewer.jsx";
import InventoryTable from "../components/InventoryTable.jsx";
import {
  Play, Loader, CheckCircle, AlertCircle,
  Brain, Database, Cpu, FileText, ChevronDown, X, Search,
  Zap, Clock,
} from "lucide-react";

// ── SKU Combobox ─────────────────────────────────────────────────────────────

function SKUCombobox({ skus, value, onChange }) {
  const [query, setQuery]   = useState(value || "");
  const [open, setOpen]     = useState(false);
  const ref                 = useRef(null);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return skus
      .filter(s =>
        s.sku_id.toLowerCase().includes(q) ||
        (s.category || "").toLowerCase().includes(q)
      )
      .slice(0, 30);
  }, [skus, query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const select = (sku) => {
    onChange(sku.sku_id);
    setQuery(sku.sku_id);
    setOpen(false);
  };

  const clear = () => { onChange(""); setQuery(""); };

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
              <span className={`font-mono text-xs ${s.sku_id === value ? "text-[#b5f23d]" : "text-zinc-300"}`}>
                {s.sku_id}
              </span>
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
            cacheHit
              ? "text-[#b5f23d] bg-[#b5f23d]/10 border-[#b5f23d]/30"
              : "text-zinc-500 bg-zinc-800 border-zinc-700"
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

// ── Main component ────────────────────────────────────────────────────────────

const PIPELINE_STAGES = [
  { icon: Cpu,      label: "XGBoost Forecast",      desc: "7-day demand prediction per SKU" },
  { icon: Database, label: "Inventory Optimization", desc: "EOQ · ROP · Safety Stock" },
  { icon: Brain,    label: "RAG Retrieval",          desc: "Semantic supplier context search" },
  { icon: FileText, label: "LLM Report",             desc: "Groq LLaMA 3.3 70B executive summary" },
];

// Cosmetic animation timings (ms after run starts)
const ANIM_TIMINGS = {
  forecast:  150,
  inventory: 340,
  rag:       530,
};

export default function Analysis() {
  const [allSkus, setAllSkus]         = useState([]);
  const [mode, setMode]               = useState("all");    // "all" | "single"
  const [selectedSku, setSelectedSku] = useState("");
  const [includeRag, setIncludeRag]   = useState(true);
  const [running, setRunning]         = useState(false);
  const [animatedStages, setAnimatedStages] = useState(new Set());
  const [metrics, setMetrics]         = useState({});
  const [result, setResult]           = useState(null);
  const [error, setError]             = useState(null);
  const metricsRef                    = useRef({});
  const stopRef                       = useRef(null);

  useEffect(() => {
    api.getAllSkus().then(setAllSkus).catch(() => {});
  }, []);

  // ── Cosmetic animation when running starts ──────────────────────────────
  useEffect(() => {
    if (!running) return;
    const timers = Object.entries(ANIM_TIMINGS).map(([stage, delay]) =>
      setTimeout(() => setAnimatedStages((s) => new Set([...s, stage])), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [running]);

  // ── Complete LLM + Complete stages when real result arrives ─────────────
  useEffect(() => {
    if (result) {
      setAnimatedStages((s) => new Set([...s, "llm", "complete"]));
    }
  }, [result]);

  const handleRun = () => {
    const skuIds = mode === "single" ? (selectedSku ? [selectedSku] : []) : [];
    if (mode === "single" && !selectedSku) return;

    // Stop any previous stream
    if (stopRef.current) stopRef.current();

    setRunning(true);
    setAnimatedStages(new Set());
    setMetrics({});
    metricsRef.current = {};
    setResult(null);
    setError(null);

    const stop = streamAnalysis(
      { sku_ids: skuIds, analyze_all: mode === "all", include_rag: includeRag },
      (type, data) => {
        if (type === "forecasting_complete") {
          metricsRef.current.forecast_ms         = data.duration_ms;
          metricsRef.current.forecast_cache_hits = data.cache_hits ?? 0;
        }
        if (type === "inventory_complete") {
          metricsRef.current.inventory_ms = data.duration_ms;
        }
        if (type === "rag_complete") {
          metricsRef.current.rag_ms = data.duration_ms;
        }
        if (type === "report_complete") {
          metricsRef.current.llm_ms        = data.duration_ms;
          metricsRef.current.llm_cache_hit = data.cache_hit ?? false;
          if (data.run_id) {
            api.getRun(data.run_id)
              .then((r) => {
                setResult(r);
                setMetrics({ ...metricsRef.current });
              })
              .catch(() => {});
          }
        }
        if (type === "done") {
          metricsRef.current.total_ms = data.total_ms;
          setMetrics({ ...metricsRef.current });
        }
      },
      () => setRunning(false),
      (e) => { setError(e.message); setRunning(false); }
    );

    stopRef.current = stop;
  };

  const canRun    = !running && (mode === "all" || !!selectedSku);
  const skuCount  = mode === "all" ? (allSkus.length || 300) : 1;
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
          {/* Configuration */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">
              Configuration
            </p>

            {/* Mode selector */}
            <div className="space-y-2">
              <label className={`flex items-start gap-2.5 cursor-pointer p-2.5 rounded-lg border transition-all ${
                mode === "all"
                  ? "border-[#b5f23d]/40 bg-[#b5f23d]/5"
                  : "border-zinc-800 hover:border-zinc-700"
              }`}>
                <input
                  type="radio"
                  name="mode"
                  value="all"
                  checked={mode === "all"}
                  onChange={() => setMode("all")}
                  className="mt-0.5 accent-[#b5f23d]"
                />
                <div>
                  <p className="text-sm font-mono text-zinc-200">
                    Analyse all {allSkus.length || 300} SKUs
                  </p>
                  <p className="text-xs text-zinc-600 mt-0.5">Full portfolio scan</p>
                </div>
              </label>

              <label className={`flex items-start gap-2.5 cursor-pointer p-2.5 rounded-lg border transition-all ${
                mode === "single"
                  ? "border-[#b5f23d]/40 bg-[#b5f23d]/5"
                  : "border-zinc-800 hover:border-zinc-700"
              }`}>
                <input
                  type="radio"
                  name="mode"
                  value="single"
                  checked={mode === "single"}
                  onChange={() => setMode("single")}
                  className="mt-0.5 accent-[#b5f23d]"
                />
                <div>
                  <p className="text-sm font-mono text-zinc-200">Analyse selected SKU</p>
                  <p className="text-xs text-zinc-600 mt-0.5">Single SKU deep-dive</p>
                </div>
              </label>
            </div>

            {/* SKU combobox — only in single mode */}
            {mode === "single" && (
              <div>
                <p className="text-xs font-mono text-zinc-600 mb-1.5">Select SKU</p>
                <SKUCombobox
                  skus={allSkus}
                  value={selectedSku}
                  onChange={setSelectedSku}
                />
                {selectedSku && (
                  <p className="text-xs font-mono text-[#b5f23d] mt-1.5">
                    ✓ {selectedSku} selected
                  </p>
                )}
              </div>
            )}

            {/* RAG toggle */}
            <label className="flex items-start gap-2.5 cursor-pointer group">
              <input
                type="checkbox"
                checked={includeRag}
                onChange={(e) => setIncludeRag(e.target.checked)}
                className="w-3.5 h-3.5 mt-0.5 accent-[#b5f23d]"
              />
              <div>
                <p className="text-sm text-zinc-300 group-hover:text-zinc-200 transition-colors">
                  Include supplier context (RAG)
                </p>
                <p className="text-xs text-zinc-600 mt-0.5">
                  ChromaDB semantic search
                </p>
              </div>
            </label>

            {/* Run button */}
            <button
              onClick={handleRun}
              disabled={!canRun}
              className={`w-full flex items-center justify-center gap-2 py-2.5 rounded font-mono text-sm font-semibold transition-all ${
                canRun
                  ? "bg-[#b5f23d] text-zinc-950 hover:opacity-90 shadow-[0_0_20px_rgba(181,242,61,0.15)]"
                  : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
              }`}
            >
              {running ? (
                <><Loader size={13} className="animate-spin" /> Running…</>
              ) : (
                <><Play size={13} /> Run Analysis ({skuCount} SKU{skuCount !== 1 ? "s" : ""})</>
              )}
            </button>

            {error && (
              <div className="bg-red-950/50 border border-red-800 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle size={13} className="text-red-400 mt-0.5 shrink-0" />
                <p className="text-xs text-red-400 font-mono break-all">{error}</p>
              </div>
            )}

            {result && !running && (
              <div className="bg-[#b5f23d]/5 border border-[#b5f23d]/20 rounded-lg p-3 flex items-center gap-2">
                <CheckCircle size={13} className="text-[#b5f23d]" />
                <p className="text-xs text-[#b5f23d] font-mono">
                  {result.skus_analyzed} SKUs analysed
                </p>
              </div>
            )}
          </div>

          {/* Pipeline architecture diagram */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">
              Pipeline Architecture
            </p>
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

          {/* Execution metrics — shown after run */}
          {hasMetrics && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock size={12} className="text-zinc-500" />
                <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">
                  Execution Metrics
                </p>
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
            <StepIndicator
              animatedStages={animatedStages}
              metrics={metrics}
              isRunning={running}
            />
          )}

          {result && (
            <>
              <ReportViewer markdown={result.report_text} runId={result.run_id} />
              {result.recommendations?.length > 0 && (
                <div>
                  <p className="text-sm font-mono text-zinc-400 mb-3">
                    Recommendations
                    <span className="text-zinc-600 ml-2">({result.recommendations.length} SKUs)</span>
                  </p>
                  <InventoryTable
                    showSearch={false}
                    data={result.recommendations.map((r) => ({
                      sku_id:               r.sku_id,
                      sku_name:             r.sku_name ?? r.sku_id,
                      category:             r.category ?? "",
                      warehouse_id:         r.warehouse_id ?? "",
                      reorder_urgency:      r.reorder_urgency,
                      current_stock:        r.current_stock,
                      days_until_stockout:  r.days_until_stockout,
                      recommended_order_qty:r.recommended_order_qty,
                      stockout_risk_pct:    r.stockout_risk_pct,
                      reorder_point:        r.reorder_point,
                      supplier_id:          r.supplier_id ?? "",
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
              <p className="text-zinc-300 font-mono text-sm mb-2">
                Configure and click Run Analysis
              </p>
              <p className="text-zinc-600 font-mono text-xs max-w-xs mx-auto leading-relaxed">
                4-stage pipeline: XGBoost demand forecasting → inventory
                optimization (EOQ · ROP) → ChromaDB RAG retrieval →
                Groq LLM executive report
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

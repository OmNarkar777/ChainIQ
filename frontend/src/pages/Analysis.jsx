import { useState, useEffect } from "react";
import { api, streamAnalysis } from "../api/client.js";
import SKUSelector from "../components/SKUSelector.jsx";
import StepIndicator from "../components/StepIndicator.jsx";
import ReportViewer from "../components/ReportViewer.jsx";
import InventoryTable from "../components/InventoryTable.jsx";
import { Play, Loader, CheckCircle, AlertCircle, Brain, Database, Cpu, FileText } from "lucide-react";

const PIPELINE_STAGES = [
  { icon: Cpu,      label: "XGBoost Forecast",      desc: "7-day demand prediction per SKU" },
  { icon: Database, label: "Inventory Optimization", desc: "EOQ · ROP · Safety Stock" },
  { icon: Brain,    label: "RAG Retrieval",          desc: "Semantic supplier context search" },
  { icon: FileText, label: "LLM Report",             desc: "Groq LLaMA 3.3 70B executive summary" },
];

export default function Analysis() {
  const [skus,       setSkus]       = useState([]);
  const [selected,   setSelected]   = useState([]);
  const [analyzeAll, setAnalyzeAll] = useState(false);
  const [includeRag, setIncludeRag] = useState(true);
  const [running,    setRunning]    = useState(false);
  const [events,     setEvents]     = useState([]);
  const [result,     setResult]     = useState(null);
  const [error,      setError]      = useState(null);

  useEffect(() => {
    api.getAllSkus().then(setSkus).catch(() => {});
  }, []);

  const handleRun = () => {
    setRunning(true);
    setEvents([]);
    setResult(null);
    setError(null);

    const body = {
      sku_ids:     analyzeAll ? [] : selected,
      analyze_all: analyzeAll,
      include_rag: includeRag,
    };

    const stop = streamAnalysis(
      body,
      (type, data) => {
        setEvents((prev) => [...prev, { ...data, ts: Date.now() }]);
        if (type === "report_complete" && data.run_id) {
          api.getRun(data.run_id).then(setResult).catch(() => {});
        }
      },
      () => setRunning(false),
      (e) => { setError(e.message); setRunning(false); }
    );

    return () => stop();
  };

  const canRun  = (selected.length > 0 || analyzeAll) && !running;
  const skuCount = analyzeAll ? skus.length : selected.length;

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
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-4">
              Configuration
            </p>

            <label className="flex items-start gap-2.5 cursor-pointer mb-4 group">
              <input
                type="checkbox"
                checked={analyzeAll}
                onChange={(e) => setAnalyzeAll(e.target.checked)}
                className="w-3.5 h-3.5 mt-0.5 accent-[#b5f23d]"
              />
              <div>
                <p className="text-sm text-zinc-300 group-hover:text-zinc-200 transition-colors">
                  Analyse all {skus.length > 0 ? skus.length : "300"} SKUs
                </p>
                <p className="text-xs text-zinc-600 mt-0.5">
                  Full portfolio scan — 5–15s
                </p>
              </div>
            </label>

            <label className="flex items-start gap-2.5 cursor-pointer mb-5 group">
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
                  ChromaDB semantic search over 10 supplier profiles
                </p>
              </div>
            </label>

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
                <><Play size={13} /> Run Analysis{skuCount > 0 ? ` (${skuCount} SKUs)` : ""}</>
              )}
            </button>

            {error && (
              <div className="mt-3 bg-red-950/50 border border-red-800 rounded-lg p-3 flex items-start gap-2">
                <AlertCircle size={13} className="text-red-400 mt-0.5 shrink-0" />
                <p className="text-xs text-red-400 font-mono">{error}</p>
              </div>
            )}

            {result && !running && (
              <div className="mt-3 bg-[#b5f23d]/5 border border-[#b5f23d]/20 rounded-lg p-3 flex items-center gap-2">
                <CheckCircle size={13} className="text-[#b5f23d]" />
                <p className="text-xs text-[#b5f23d] font-mono">
                  {result.skus_analyzed} SKUs analysed
                </p>
              </div>
            )}
          </div>

          {/* Pipeline diagram */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">
              Pipeline Architecture
            </p>
            <div className="space-y-2">
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded bg-zinc-800 flex items-center justify-center shrink-0 mt-0.5">
                    <stage.icon size={11} className="text-[#b5f23d]" />
                  </div>
                  <div>
                    <p className="text-xs font-mono text-zinc-300">{stage.label}</p>
                    <p className="text-xs text-zinc-600">{stage.desc}</p>
                  </div>
                  {i < PIPELINE_STAGES.length - 1 && (
                    <div className="absolute ml-3 mt-7 w-px h-3 bg-zinc-700" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* SKU selector */}
          {!analyzeAll && (
            <div>
              <p className="text-xs font-mono text-zinc-500 mb-2 uppercase tracking-wider">
                Select SKUs
              </p>
              <SKUSelector skus={skus} selected={selected} onChange={setSelected} />
            </div>
          )}
        </div>

        {/* ── Right panel ── */}
        <div className="lg:col-span-2 space-y-5">
          {(running || events.length > 0) && (
            <StepIndicator events={events} isRunning={running} />
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

          {!running && !result && events.length === 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-16 text-center">
              <div className="w-14 h-14 rounded-full bg-[#b5f23d]/10 border border-[#b5f23d]/20 flex items-center justify-center mx-auto mb-4">
                <Play size={22} className="text-[#b5f23d]" />
              </div>
              <p className="text-zinc-300 font-mono text-sm mb-2">
                Select SKUs and click Run Analysis
              </p>
              <p className="text-zinc-600 font-mono text-xs max-w-xs mx-auto leading-relaxed">
                The 4-stage pipeline runs XGBoost demand forecasting, inventory
                optimization (EOQ · ROP · safety stock), ChromaDB RAG retrieval,
                and Groq LLM executive report generation.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import SNAPSHOT from "../data/snapshot.json";
import ForecastChart from "../components/ForecastChart.jsx";
import UrgencyBadge from "../components/UrgencyBadge.jsx";
import { Search, TrendingUp } from "lucide-react";

// Build sku→detail lookup once from snapshot
const SKU_DETAIL = Object.fromEntries(SNAPSHOT.inventory.map((r) => [r.sku_id, r]));

function Stat({ label, value, sub, highlight = false }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <p className="text-xs font-mono text-zinc-600 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-mono font-bold ${highlight ? "text-[#b5f23d]" : "text-zinc-200"}`}>{value}</p>
      {sub && <p className="text-xs text-zinc-600 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function Forecast() {
  const [params] = useSearchParams();
  const defaultSku = params.get("sku") || "SKU_0001";

  const [skuId,   setSkuId]   = useState(defaultSku);
  const [input,   setInput]   = useState(defaultSku);
  // Initialise directly from snapshot — zero loading time
  const [forecast, setForecast] = useState(() => SNAPSHOT.forecasts[defaultSku] ?? null);
  const [detail,   setDetail]   = useState(() => SKU_DETAIL[defaultSku] ?? null);
  const [history,  setHistory]  = useState([]);
  const [histLoading, setHistLoading] = useState(false);

  // Load history chart data from backend (background — stats already visible)
  const loadHistory = useCallback((id) => {
    setHistLoading(true);
    setHistory([]);
    api.getSkuHistory(id, 30)
      .then(setHistory)
      .catch(() => {})
      .finally(() => setHistLoading(false));
  }, []);

  // When SKU changes: immediately show precomputed data, fetch chart in background
  useEffect(() => {
    setForecast(SNAPSHOT.forecasts[skuId] ?? null);
    setDetail(SKU_DETAIL[skuId] ?? null);
    loadHistory(skuId);
  }, [skuId, loadHistory]);

  const onSearch = (e) => {
    e.preventDefault();
    const id = input.trim().toUpperCase();
    if (id) setSkuId(id);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-mono font-semibold">Demand Forecast</h1>
        <p className="text-xs text-zinc-600 mt-0.5">
          30-day sales history + 7-day XGBoost forecast with 80% confidence interval
        </p>
      </div>

      <form onSubmit={onSearch} className="flex gap-2 mb-6">
        <div className="flex items-center gap-2 flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 focus-within:border-[#b5f23d]/50 transition-colors">
          <Search size={13} className="text-zinc-600" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            placeholder="Enter SKU ID (e.g. SKU_0001)"
            className="flex-1 bg-transparent text-sm font-mono text-zinc-200 placeholder:text-zinc-600 outline-none"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 bg-[#b5f23d] text-zinc-950 rounded font-mono text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Load
        </button>
      </form>

      {forecast && detail ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Stat
              label="7-Day Forecast"
              value={`${forecast.predicted_units?.toFixed(0)} units`}
              sub={`80% CI: ${forecast.lower_bound?.toFixed(0)}–${forecast.upper_bound?.toFixed(0)}`}
              highlight
            />
            <Stat
              label="Stock on Hand"
              value={detail.current_stock?.toFixed(0)}
              sub={`${detail.days_until_stockout?.toFixed(1)} days supply`}
            />
            <Stat label="Reorder Point" value={detail.reorder_point?.toFixed(0)} sub="units (ROP)" />
            <Stat
              label="Model Accuracy"
              value={forecast.mape_estimate != null ? `${forecast.mape_estimate.toFixed(1)}% MAPE` : "—"}
              sub={`${forecast.confidence_pct}% confidence interval`}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              {histLoading && history.length === 0 ? (
                <div>
                  <p className="text-sm font-mono text-zinc-400 mb-4">{skuId} — 30d History</p>
                  <div className="skeleton h-56 w-full rounded" />
                </div>
              ) : (
                <ForecastChart history={history} forecast={forecast} skuId={skuId} />
              )}
            </div>

            <div className="space-y-4">
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">
                  Inventory Position
                </p>
                <div className="space-y-2.5">
                  {[
                    ["Urgency",      <UrgencyBadge urgency={detail.reorder_urgency} />],
                    ["Safety Stock", `${detail.safety_stock?.toFixed(0)} units`],
                    ["EOQ",          `${detail.eoq?.toFixed(0)} units`],
                    ["Order Qty",    `${detail.recommended_order_qty?.toFixed(0)} units`],
                    ["Lead Time",    `${detail.lead_time_days} days`],
                    ["Supplier",     detail.supplier_id || "—"],
                    ["Avg Daily",    `${detail.avg_daily_demand?.toFixed(1)} units/day`],
                  ].map(([lbl, val]) => (
                    <div key={lbl} className="flex justify-between items-center">
                      <span className="text-zinc-600 text-xs">{lbl}</span>
                      {typeof val === "string"
                        ? <span className="font-mono text-zinc-300 text-xs">{val}</span>
                        : val}
                    </div>
                  ))}
                </div>
              </div>

              {forecast.top_features?.length > 0 && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                  <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">
                    Top Forecast Features
                  </p>
                  <div className="space-y-2">
                    {forecast.top_features.map((f) => (
                      <div key={f.feature} className="flex items-center gap-2">
                        <p className="text-xs font-mono text-zinc-400 flex-1 truncate">{f.feature}</p>
                        <div className="w-20 h-1.5 bg-zinc-800 rounded-full overflow-hidden shrink-0">
                          <div
                            className="h-full bg-[#b5f23d] rounded-full"
                            style={{ width: `${(f.importance / (forecast.top_features[0]?.importance || 1)) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-16 text-center">
          <TrendingUp size={32} className="text-zinc-700 mx-auto mb-3" />
          <p className="text-zinc-500 font-mono text-sm">Enter a SKU ID to view its forecast</p>
        </div>
      )}
    </div>
  );
}

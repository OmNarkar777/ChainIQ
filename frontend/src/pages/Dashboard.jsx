import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api, clearCache } from "../api/client.js";
import SNAPSHOT from "../data/snapshot.json";
import AlertBanner from "../components/AlertBanner.jsx";
import UrgencyBadge from "../components/UrgencyBadge.jsx";
import {
  Activity, TrendingDown, Package, Zap,
  RefreshCw, ArrowRight, DollarSign, Clock,
  AlertTriangle, Play, Cpu, Database,
} from "lucide-react";

function formatCurrency(v) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function formatRunTime(isoStr) {
  if (!isoStr) return "—";
  const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
  return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

function KPI({ label, value, sub, icon: Icon, accent = "text-[#b5f23d]", refreshing }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 flex flex-col gap-3 hover:border-zinc-700 transition-colors">
      <div className="flex items-center justify-between">
        <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">{label}</p>
        <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center">
          <Icon size={13} className={accent} />
        </div>
      </div>
      <p className={`text-3xl font-mono font-bold ${accent} ${refreshing ? "opacity-60" : ""} transition-opacity`}>
        {value ?? "—"}
      </p>
      {sub && <p className="text-xs text-zinc-600">{sub}</p>}
    </div>
  );
}

function DemandTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs font-mono shadow-xl">
      <p className="text-zinc-400 mb-1">{label}</p>
      <p className="text-[#b5f23d]">{payload[0]?.value?.toLocaleString()} units</p>
    </div>
  );
}

function CategoryTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs font-mono shadow-xl">
      <p className="text-zinc-300">{payload[0]?.payload?.category}</p>
      <p className="text-[#b5f23d]">{payload[0]?.value} SKUs</p>
    </div>
  );
}

// Renders instantly from precomputed snapshot; silently refreshes from live backend.
export default function Dashboard() {
  const [data,       setData]       = useState(SNAPSHOT.dashboard);
  const [meta,       setMeta]       = useState(SNAPSHOT.meta);
  const [refreshing, setRefreshing] = useState(false);
  const [liveTs,     setLiveTs]     = useState(null);
  const [runs,       setRuns]       = useState([]);

  // Background refresh — update data silently when backend is available
  useEffect(() => {
    Promise.all([
      api.getDashboard().catch(() => null),
      api.getMeta().catch(() => null),
    ]).then(([dash, m]) => {
      if (dash) { setData(dash); setRuns(dash.recent_runs ?? []); setLiveTs(new Date()); }
      if (m)    setMeta(m);
    });
  }, []);

  const refresh = () => {
    setRefreshing(true);
    clearCache();
    Promise.all([
      api.getDashboard().catch(() => null),
      api.getMeta().catch(() => null),
    ]).then(([dash, m]) => {
      if (dash) { setData(dash); setRuns(dash.recent_runs ?? []); setLiveTs(new Date()); }
      if (m)    setMeta(m);
    }).finally(() => setRefreshing(false));
  };

  const sum      = data?.summary;
  const critical = data?.critical_skus ?? [];
  const analytics = data?.analytics ?? null;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-mono font-semibold">Operations Dashboard</h1>
          <p className="text-xs text-zinc-600 mt-0.5">
            {liveTs
              ? `Live · Refreshed ${liveTs.toLocaleTimeString()}`
              : `Snapshot · ${new Date(SNAPSHOT.generatedAt).toLocaleDateString()}`}
            {" · 300-SKU multi-category enterprise dataset"}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-[#b5f23d] border border-zinc-700 hover:border-[#b5f23d]/50 px-3 py-1.5 rounded transition-all disabled:opacity-50"
        >
          <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      <AlertBanner criticalSkus={critical} />

      {meta && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mb-5 px-4 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <Cpu size={11} className="text-[#b5f23d]" />
            <span className="text-zinc-500">Model</span>
            <span className="text-zinc-300">{meta.model_version}</span>
          </div>
          <div className="w-px h-3 bg-zinc-700" />
          <div className="flex items-center gap-1.5">
            <span className="text-zinc-500">MAPE</span>
            <span className="text-[#b5f23d]">{meta.model_mape?.toFixed(1)}%</span>
          </div>
          <div className="w-px h-3 bg-zinc-700" />
          <div className="flex items-center gap-1.5">
            <span className="text-zinc-500">Confidence</span>
            <span className="text-zinc-300">{meta.confidence_pct}% CI</span>
          </div>
          <div className="w-px h-3 bg-zinc-700" />
          <div className="flex items-center gap-1.5">
            <span className="text-zinc-500">Features</span>
            <span className="text-zinc-300">{meta.feature_count}</span>
          </div>
          <div className="w-px h-3 bg-zinc-700" />
          <div className="flex items-center gap-1.5">
            <Database size={11} className="text-zinc-500" />
            <span className="text-zinc-500">Cache</span>
            <span className={meta.cache_warm ? "text-[#b5f23d]" : "text-amber-400"}>
              {meta.cache_status}
            </span>
          </div>
          {meta.prediction_cache_size > 0 && (
            <>
              <div className="w-px h-3 bg-zinc-700" />
              <span className="text-zinc-600">{meta.prediction_cache_size} SKUs cached</span>
            </>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        <KPI label="Critical"   value={sum?.critical}                              icon={Zap}           accent="text-red-400"    refreshing={refreshing} sub="order immediately" />
        <KPI label="High Risk"  value={sum?.high}                                  icon={TrendingDown}  accent="text-amber-400"  refreshing={refreshing} sub="order within 2 days" />
        <KPI label="At Risk"    value={analytics ? `${analytics.at_risk_pct}%` : null}   icon={AlertTriangle} accent="text-orange-400" refreshing={refreshing} sub="of total SKUs" />
        <KPI label="Avg Supply" value={analytics ? `${analytics.avg_days_of_supply}d` : null} icon={Clock}      accent="text-yellow-400" refreshing={refreshing} sub="days remaining" />
        <KPI label="Inv. Value" value={analytics ? formatCurrency(analytics.total_inventory_value) : null} icon={Package} accent="text-[#b5f23d]" refreshing={refreshing} sub="total stock value" />
        <KPI label="Order Now"  value={analytics ? formatCurrency(analytics.order_value_needed) : null}    icon={DollarSign} accent="text-red-300" refreshing={refreshing} sub="CRITICAL + HIGH value" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-mono text-zinc-300">30-Day Demand Trend</p>
              <p className="text-xs text-zinc-600 mt-0.5">Aggregate daily units sold across all 300 SKUs</p>
            </div>
            <Activity size={14} className="text-zinc-600" />
          </div>
          {analytics?.demand_trend?.length ? (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={analytics.demand_trend} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#b5f23d" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#b5f23d" stopOpacity={0}    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#52525b", fontSize: 10, fontFamily: "DM Mono" }} tickFormatter={(v) => v?.slice(5)} interval="preserveStartEnd" axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#52525b", fontSize: 10, fontFamily: "DM Mono" }} width={44} axisLine={false} tickLine={false} tickFormatter={(v) => v.toLocaleString()} />
                <Tooltip content={<DemandTooltip />} />
                <Area dataKey="total_units" stroke="#b5f23d" strokeWidth={2} fill="url(#demandGrad)" dot={false} activeDot={{ r: 3, fill: "#b5f23d", strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-zinc-600 font-mono text-sm text-center py-16">No trend data</p>
          )}
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-mono text-zinc-300">Category Mix</p>
              <p className="text-xs text-zinc-600 mt-0.5">SKU distribution</p>
            </div>
            <Package size={14} className="text-zinc-600" />
          </div>
          {analytics?.category_breakdown?.length ? (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={analytics.category_breakdown} layout="vertical" margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
                <XAxis type="number" tick={{ fill: "#52525b", fontSize: 10, fontFamily: "DM Mono" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="category" tick={{ fill: "#71717a", fontSize: 10, fontFamily: "DM Mono" }} width={72} axisLine={false} tickLine={false} />
                <Tooltip content={<CategoryTooltip />} />
                <Bar dataKey="skus" fill="#b5f23d" fillOpacity={0.7} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-zinc-600 font-mono text-sm text-center py-16">No data</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <p className="text-sm font-mono text-zinc-300">Top At-Risk SKUs</p>
            <Link to="/inventory" className="text-xs font-mono text-[#b5f23d] flex items-center gap-1 hover:opacity-80 transition-opacity">
              View all <ArrowRight size={11} />
            </Link>
          </div>
          {critical.slice(0, 6).map((s) => (
            <Link key={s.sku_id} to={`/forecast?sku=${s.sku_id}`}
              className="flex items-center justify-between px-5 py-3 border-b border-zinc-800/50 last:border-0 hover:bg-zinc-800/40 transition-colors"
            >
              <div>
                <p className="text-sm font-mono text-zinc-200">{s.sku_id}</p>
                <p className="text-xs text-zinc-600">
                  {s.days_until_stockout?.toFixed(1)}d left{s.supplier_id ? ` · ${s.supplier_id}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <UrgencyBadge urgency={s.reorder_urgency} />
                {s.recommended_order_qty > 0 && (
                  <span className="text-xs font-mono text-[#b5f23d] bg-[#b5f23d]/10 border border-[#b5f23d]/20 px-2 py-0.5 rounded">
                    +{s.recommended_order_qty?.toFixed(0)}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <p className="text-sm font-mono text-zinc-300">Recent Analysis Runs</p>
            <Link to="/analysis" className="text-xs font-mono text-[#b5f23d] flex items-center gap-1 hover:opacity-80 transition-opacity">
              New run <ArrowRight size={11} />
            </Link>
          </div>
          {runs.length > 0 ? (
            runs.slice(0, 6).map((r) => (
              <div key={r.run_id} className="flex items-center justify-between px-5 py-3 border-b border-zinc-800/50 last:border-0">
                <div>
                  <p className="text-xs font-mono text-zinc-400">#{r.run_id.slice(0, 8)}</p>
                  <p className="text-xs text-zinc-600">{r.skus_analyzed} SKUs · {formatRunTime(r.created_at)}</p>
                </div>
                <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                  r.status === "DONE" ? "text-[#b5f23d] border-[#b5f23d]/30 bg-[#b5f23d]/10" : "text-zinc-500 border-zinc-700"
                }`}>{r.status}</span>
              </div>
            ))
          ) : (
            <div className="py-12 text-center">
              <Play size={20} className="text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-600 font-mono text-sm mb-3">No analysis runs yet</p>
              <Link to="/analysis" className="inline-flex items-center gap-1.5 text-xs font-mono text-[#b5f23d] border border-[#b5f23d]/30 px-3 py-1.5 rounded hover:bg-[#b5f23d]/10 transition-colors">
                <Play size={11} /> Run first analysis
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

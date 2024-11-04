import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useInventorySummary } from "../hooks/useInventory.js";
import AlertBanner from "../components/AlertBanner.jsx";
import UrgencyBadge from "../components/UrgencyBadge.jsx";
import { Activity, TrendingDown, Package, Zap, RefreshCw, ArrowRight } from "lucide-react";
function KPI({ label, value, sub, icon:Icon, accent="text-[#b5f23d]", loading }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider">{label}</p>
        <Icon size={14} className={accent}/>
      </div>
      {loading?<div className="skeleton h-8 w-20 rounded"/>:<p className={`text-3xl font-mono font-bold ${accent}`}>{value}</p>}
      {sub&&<p className="text-xs text-zinc-600">{sub}</p>}
    </div>
  );
}
export default function Dashboard() {
  const { data:sum, loading, refetch } = useInventorySummary();
  const [critical,setCritical] = useState([]);
  const [runs,setRuns]         = useState([]);
  const [ts,setTs]             = useState(new Date());
  useEffect(() => {
    api.getCriticalSkus().then(setCritical).catch(()=>{});
    api.listRuns().then(setRuns).catch(()=>{});
  }, []);
  const refresh = () => { refetch(); api.getCriticalSkus().then(setCritical).catch(()=>{}); setTs(new Date()); };
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-xl font-mono font-semibold">Operations Dashboard</h1>
          <p className="text-xs text-zinc-600 mt-0.5">Refreshed {ts.toLocaleTimeString()}</p></div>
        <button onClick={refresh} className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-[#b5f23d] border border-zinc-700 hover:border-[#b5f23d]/50 px-3 py-1.5 rounded transition-all">
          <RefreshCw size={12}/> Refresh</button>
      </div>
      <AlertBanner criticalSkus={critical}/>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPI label="Critical SKUs"  value={sum?.critical||0}    icon={Zap}         accent="text-red-400"    loading={loading} sub="Need immediate orders"/>
        <KPI label="High Urgency"   value={sum?.high||0}        icon={TrendingDown} accent="text-amber-400"  loading={loading} sub="Order within 2 days"/>
        <KPI label="Monitoring"     value={sum?.medium||0}      icon={Activity}    accent="text-yellow-400" loading={loading} sub="Below reorder point"/>
        <KPI label="Total SKUs"     value={sum?.total_skus||0}  icon={Package}     accent="text-[#b5f23d]"  loading={loading} sub="In inventory"/>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <p className="text-sm font-mono text-zinc-300">Top At-Risk SKUs</p>
            <Link to="/inventory" className="text-xs font-mono text-[#b5f23d] flex items-center gap-1">View all<ArrowRight size={11}/></Link>
          </div>
          {critical.slice(0,5).map(s=>(
            <div key={s.sku_id} className="flex items-center justify-between px-5 py-3 border-b border-zinc-800/50 last:border-0">
              <div><p className="text-sm font-mono text-zinc-200">{s.sku_id}</p>
                <p className="text-xs text-zinc-600">{s.days_until_stockout?.toFixed(1)}d left - {s.supplier_id}</p></div>
              <div className="flex items-center gap-3">
                <UrgencyBadge urgency={s.reorder_urgency}/>
                {s.recommended_order_qty>0&&<span className="text-xs font-mono text-[#b5f23d] bg-[#b5f23d]/10 border border-[#b5f23d]/20 px-2 py-0.5 rounded">+{s.recommended_order_qty?.toFixed(0)}</span>}
              </div>
            </div>
          ))}
          {critical.length===0&&!loading&&<div className="py-10 text-center text-zinc-600 font-mono text-sm">No critical SKUs</div>}
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <p className="text-sm font-mono text-zinc-300">Recent Runs</p>
            <Link to="/analysis" className="text-xs font-mono text-[#b5f23d] flex items-center gap-1">New run<ArrowRight size={11}/></Link>
          </div>
          {runs.slice(0,5).map(r=>(
            <div key={r.run_id} className="flex items-center justify-between px-5 py-3 border-b border-zinc-800/50 last:border-0">
              <div><p className="text-xs font-mono text-zinc-400">#{r.run_id.slice(0,8)}</p>
                <p className="text-xs text-zinc-600">{r.skus_analyzed} SKUs - {new Date(r.created_at).toLocaleString()}</p></div>
              <span className={`text-xs font-mono px-2 py-0.5 rounded border ${r.status==="DONE"?"text-[#b5f23d] border-[#b5f23d]/30 bg-[#b5f23d]/10":"text-zinc-500 border-zinc-700"}`}>{r.status}</span>
            </div>
          ))}
          {runs.length===0&&<div className="py-10 text-center text-zinc-600 font-mono text-sm">No runs yet</div>}
        </div>
      </div>
    </div>
  );
}
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import ForecastChart from "../components/ForecastChart.jsx";
import UrgencyBadge from "../components/UrgencyBadge.jsx";
import { Search } from "lucide-react";
function Stat({ label, value, sub }) {
  return <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
    <p className="text-xs font-mono text-zinc-600 uppercase tracking-wider mb-1">{label}</p>
    <p className="text-xl font-mono font-bold text-[#b5f23d]">{value}</p>
    {sub&&<p className="text-xs text-zinc-600 mt-0.5">{sub}</p>}
  </div>;
}
export default function Forecast() {
  const [params]             = useSearchParams();
  const [skuId,setSkuId]     = useState(params.get("sku")||"SKU_0001");
  const [input,setInput]     = useState(params.get("sku")||"SKU_0001");
  const [history,setHistory] = useState([]);
  const [forecast,setFc]     = useState(null);
  const [detail,setDetail]   = useState(null);
  const [loading,setLoading] = useState(false);
  const [error,setError]     = useState(null);
  const load = id => {
    setLoading(true); setError(null);
    Promise.all([api.getSkuHistory(id,30),api.forecastSku(id,7),api.getSkuDetail(id)])
      .then(([h,f,d])=>{setHistory(h);setFc(f);setDetail(d);})
      .catch(e=>setError(e.message)).finally(()=>setLoading(false));
  };
  useEffect(()=>{load(skuId);},[skuId]);
  const onSearch = e => { e.preventDefault(); setSkuId(input.trim().toUpperCase()); };
  return (
    <div>
      <div className="mb-6"><h1 className="text-xl font-mono font-semibold">Demand Forecast</h1>
        <p className="text-xs text-zinc-600 mt-0.5">30-day history + 7-day XGBoost forecast with CI</p></div>
      <form onSubmit={onSearch} className="flex gap-2 mb-6">
        <div className="flex items-center gap-2 flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 focus-within:border-[#b5f23d]/50">
          <Search size={13} className="text-zinc-600"/>
          <input value={input} onChange={e=>setInput(e.target.value.toUpperCase())} placeholder="Enter SKU ID (e.g. SKU_0001)"
            className="flex-1 bg-transparent text-sm font-mono text-zinc-200 placeholder:text-zinc-600 outline-none"/>
        </div>
        <button type="submit" className="px-4 py-2 bg-[#b5f23d] text-zinc-950 rounded font-mono text-sm font-medium hover:opacity-90">Load</button>
      </form>
      {error&&<div className="bg-red-950/50 border border-red-800 rounded-lg p-4 mb-6 font-mono text-sm text-red-400">{error}</div>}
      {loading&&<div className="space-y-4"><div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{[...Array(4)].map((_,i)=><div key={i} className="skeleton h-24 rounded-lg"/>)}</div><div className="skeleton h-72 rounded-lg"/></div>}
      {!loading&&forecast&&detail&&<>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Stat label="7-Day Forecast" value={`${forecast.predicted_units?.toFixed(0)} units`} sub={`CI: ${forecast.lower_bound?.toFixed(0)}-${forecast.upper_bound?.toFixed(0)}`}/>
          <Stat label="Stock on Hand"  value={detail.current_stock?.toFixed(0)} sub={`${detail.days_until_stockout?.toFixed(1)} days supply`}/>
          <Stat label="Reorder Point"  value={detail.reorder_point?.toFixed(0)} sub="units"/>
          <Stat label="Confidence"     value={`${forecast.confidence_pct}%`} sub={`MAPE ${forecast.mape_estimate?.toFixed(1)||"--"}%`}/>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-lg p-5">
            <ForecastChart history={history} forecast={forecast} skuId={skuId}/>
          </div>
          <div className="space-y-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">Inventory Position</p>
              <div className="space-y-2.5">
                {[["Urgency",<UrgencyBadge urgency={detail.reorder_urgency}/>],["Safety Stock",`${detail.safety_stock?.toFixed(0)} units`],
                  ["EOQ",`${detail.eoq?.toFixed(0)} units`],["Lead Time",`${detail.lead_time_days} days`],
                  ["Supplier",detail.supplier_id],["Avg Daily",`${detail.avg_daily_demand?.toFixed(1)} units`]
                ].map(([lbl,val])=>(
                  <div key={lbl} className="flex justify-between items-center">
                    <span className="text-zinc-600 text-xs">{lbl}</span>
                    {typeof val==="string"?<span className="font-mono text-zinc-300 text-xs">{val}</span>:val}
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">Top Features</p>
              <div className="space-y-2">
                {forecast.top_features?.map(f=>(
                  <div key={f.feature} className="flex items-center gap-2">
                    <p className="text-xs font-mono text-zinc-400 flex-1 truncate">{f.feature}</p>
                    <div className="w-20 h-1 bg-zinc-800 rounded-full overflow-hidden shrink-0">
                      <div className="h-full bg-[#b5f23d] rounded-full" style={{width:`${(f.importance/(forecast.top_features[0]?.importance||1))*100}%`}}/>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </>}
    </div>
  );
}
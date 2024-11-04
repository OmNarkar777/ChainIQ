import { Check, Loader, Clock } from "lucide-react";
const STEPS = [
  { key:"forecasting_start",    label:"XGBoost Forecast",     sub:"Forecasting Agent" },
  { key:"forecasting_complete", label:"Forecast Ready",        sub:"" },
  { key:"inventory_complete",   label:"Inventory Calculated",  sub:"Inventory Agent (EOQ + Safety Stock)" },
  { key:"rag_complete",         label:"Supplier Context",      sub:"RAG Retriever (ChromaDB)" },
  { key:"report_complete",      label:"Report Generated",      sub:"Report Agent (Groq LLM)" },
];
const ORDER = ["forecasting_start","forecasting_complete","inventory_complete","rag_complete","report_complete"];
export default function StepIndicator({ events=[], isRunning }) {
  const done = new Set(events.map(e=>e.type));
  const lastI = ORDER.reduce((a,k,i)=>done.has(k)?i:a,-1);
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-6">
      <p className="text-xs text-zinc-500 font-mono mb-3 uppercase tracking-wider">Pipeline Progress</p>
      <div className="space-y-2">
        {STEPS.map((s,i)=>{
          const d=done.has(s.key), r=isRunning&&i===lastI+1, p=!d&&!r;
          return (
            <div key={s.key} className={`flex items-center gap-3 transition-all duration-300 ${p?"opacity-40":""}`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border ${d?"bg-acid/20 border-[#b5f23d]":r?"bg-zinc-800 border-zinc-600 animate-pulse":"bg-zinc-900 border-zinc-700"}`}>
                {d?<Check size={12} className="text-[#b5f23d]"/>:r?<Loader size={12} className="text-zinc-400 animate-spin"/>:<Clock size={12} className="text-zinc-600"/>}
              </div>
              <div>
                <p className={`text-sm font-mono ${d?"text-[#b5f23d]":r?"text-zinc-200":"text-zinc-500"}`}>{s.label}</p>
                {s.sub&&<p className="text-xs text-zinc-600">{s.sub}</p>}
              </div>
              {d&&events.find(e=>e.type===s.key)?.duration_ms&&(
                <span className="ml-auto text-xs font-mono text-zinc-600">{events.find(e=>e.type===s.key).duration_ms}ms</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
import { AlertTriangle, X } from "lucide-react";
import { useState } from "react";
export default function AlertBanner({ criticalSkus=[] }) {
  const [dismissed,setDismissed] = useState(false);
  if (dismissed || criticalSkus.length===0) return null;
  return (
    <div className="bg-red-950/60 border border-red-700 rounded-lg px-4 py-3 flex items-start gap-3 mb-6">
      <AlertTriangle className="text-red-400 mt-0.5 shrink-0" size={16}/>
      <div className="flex-1 min-w-0">
        <p className="text-red-300 font-mono text-sm font-medium mb-1">
          {criticalSkus.length} SKU{criticalSkus.length!==1?"s":""} require immediate ordering
        </p>
        <div className="flex flex-wrap gap-2 mt-1.5">
          {criticalSkus.slice(0,6).map(s=>(
            <span key={s.sku_id} className="flex items-center gap-1.5 text-xs text-red-400 bg-red-900/40 px-2 py-0.5 rounded border border-red-800 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"/>
              {s.sku_id} <span className="text-red-500 ml-1">{s.days_until_stockout?.toFixed(1)}d</span>
            </span>
          ))}
        </div>
      </div>
      <button onClick={()=>setDismissed(true)} className="text-red-600 hover:text-red-400"><X size={14}/></button>
    </div>
  );
}
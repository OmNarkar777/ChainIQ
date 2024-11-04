import { useState } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import UrgencyBadge from "./UrgencyBadge.jsx";
const UR = {CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3};
function SortBtn({col,sort,onSort}) {
  const a=sort.col===col;
  return <button onClick={()=>onSort(col)} className="inline-flex items-center gap-1 hover:text-[#b5f23d]">
    {!a&&<ArrowUpDown size={11} className="text-zinc-600"/>}
    {a&&sort.dir==="asc"&&<ArrowUp size={11} className="text-[#b5f23d]"/>}
    {a&&sort.dir==="desc"&&<ArrowDown size={11} className="text-[#b5f23d]"/>}
  </button>;
}
export default function InventoryTable({ data=[], onRowClick }) {
  const [sort,setSort]   = useState({col:"reorder_urgency",dir:"asc"});
  const [filter,setFilter] = useState("ALL");
  const FILTERS = ["ALL","CRITICAL","HIGH","MEDIUM","LOW"];
  const counts  = Object.fromEntries(FILTERS.map(f=>[f,f==="ALL"?data.length:data.filter(r=>r.reorder_urgency===f).length]));
  const filtered = data.filter(r=>filter==="ALL"||r.reorder_urgency===filter);
  const sorted   = [...filtered].sort((a,b)=>{
    let va=a[sort.col],vb=b[sort.col];
    if(sort.col==="reorder_urgency"){va=UR[va];vb=UR[vb];}
    if(typeof va==="string") return sort.dir==="asc"?va.localeCompare(vb):vb.localeCompare(va);
    return sort.dir==="asc"?va-vb:vb-va;
  });
  const onSort = col => setSort(s=>({col,dir:s.col===col&&s.dir==="asc"?"desc":"asc"}));
  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {FILTERS.map(f=>(
          <button key={f} onClick={()=>setFilter(f)}
            className={`px-3 py-1 rounded text-xs font-mono border transition-all ${filter===f?"bg-[#b5f23d] text-zinc-950 border-[#b5f23d]":"bg-zinc-900 text-zinc-400 border-zinc-700 hover:border-zinc-500"}`}>
            {f} <span className="opacity-60">({counts[f]})</span>
          </button>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-zinc-900 border-b border-zinc-800">
              {[["sku_id","SKU"],["reorder_urgency","Urgency"],["current_stock","Stock"],["days_until_stockout","Days Left"],["recommended_order_qty","Order Qty"],["stockout_risk_pct","Risk"]].map(([col,lbl])=>(
                <th key={col} className="px-4 py-3 text-left text-xs font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                  <span className="flex items-center gap-1.5">{lbl}<SortBtn col={col} sort={sort} onSort={onSort}/></span>
                </th>
              ))}
              <th className="px-4 py-3 text-left text-xs font-mono text-zinc-500">Supplier</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/50">
            {sorted.map(row=>(
              <tr key={row.sku_id} onClick={()=>onRowClick?.(row)}
                className={`transition-colors cursor-pointer ${row.reorder_urgency==="CRITICAL"?"bg-red-950/20 hover:bg-red-950/40":row.reorder_urgency==="HIGH"?"bg-amber-950/20 hover:bg-amber-950/40":"hover:bg-zinc-800/40"}`}>
                <td className="px-4 py-3 font-mono text-zinc-200 text-xs">{row.sku_id}</td>
                <td className="px-4 py-3"><UrgencyBadge urgency={row.reorder_urgency}/></td>
                <td className="px-4 py-3 font-mono text-zinc-300 tabular-nums">{row.current_stock?.toFixed(0)}</td>
                <td className={`px-4 py-3 font-mono tabular-nums ${row.days_until_stockout<7?"text-red-400":row.days_until_stockout<14?"text-amber-400":"text-zinc-300"}`}>{row.days_until_stockout?.toFixed(1)}d</td>
                <td className="px-4 py-3 font-mono text-[#b5f23d] tabular-nums">{row.recommended_order_qty>0?`+${row.recommended_order_qty?.toFixed(0)}`:"--"}</td>
                <td className="px-4 py-3 text-xs font-mono text-zinc-400">{row.stockout_risk_pct?.toFixed(0)}%</td>
                <td className="px-4 py-3 text-xs font-mono text-zinc-500">{row.supplier_id}</td>
              </tr>
            ))}
            {sorted.length===0&&<tr><td colSpan={7} className="py-10 text-center text-zinc-600 font-mono text-sm">No SKUs match filter</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
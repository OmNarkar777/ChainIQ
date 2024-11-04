import { useState, useMemo } from "react";
import { Search, X, CheckSquare, Square } from "lucide-react";
export default function SKUSelector({ skus=[], selected=[], onChange }) {
  const [q,setQ] = useState("");
  const filtered = useMemo(()=>skus.filter(s=>s.sku_id.toLowerCase().includes(q.toLowerCase())||(s.category||"").toLowerCase().includes(q.toLowerCase())),[skus,q]);
  const toggle = id => onChange(selected.includes(id)?selected.filter(s=>s!==id):[...selected,id]);
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800">
        <Search size={13} className="text-zinc-600"/>
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search SKU or category..."
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none font-mono"/>
        {q&&<button onClick={()=>setQ("")}><X size={12} className="text-zinc-600"/></button>}
      </div>
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-950/50 border-b border-zinc-800">
        <span className="text-xs font-mono text-zinc-600">{selected.length} selected</span>
        <div className="flex gap-3">
          <button onClick={()=>onChange(filtered.map(s=>s.sku_id))} className="text-xs font-mono text-[#b5f23d] hover:opacity-80">All ({filtered.length})</button>
          <button onClick={()=>onChange([])} className="text-xs font-mono text-zinc-500 hover:text-zinc-300">Clear</button>
        </div>
      </div>
      <div className="max-h-52 overflow-y-auto">
        {filtered.map(s=>{
          const sel=selected.includes(s.sku_id);
          return <div key={s.sku_id} onClick={()=>toggle(s.sku_id)}
            className={`flex items-center gap-2.5 px-3 py-2 cursor-pointer text-sm border-b border-zinc-800/40 last:border-0 ${sel?"bg-[#b5f23d]/5":"hover:bg-zinc-800/50"}`}>
            {sel?<CheckSquare size={13} className="text-[#b5f23d]"/>:<Square size={13} className="text-zinc-700"/>}
            <span className={`font-mono text-xs ${sel?"text-[#b5f23d]":"text-zinc-300"}`}>{s.sku_id}</span>
            <span className="text-zinc-600 text-xs ml-auto">{s.category}</span>
          </div>;
        })}
      </div>
    </div>
  );
}
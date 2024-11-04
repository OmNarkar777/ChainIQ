import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import InventoryTable from "../components/InventoryTable.jsx";
import { RefreshCw } from "lucide-react";
export default function Inventory() {
  const [skus,setSkus]       = useState([]);
  const [loading,setLoading] = useState(true);
  const nav = useNavigate();
  const load = () => { setLoading(true); api.getAllSkus().then(setSkus).catch(console.error).finally(()=>setLoading(false)); };
  useEffect(()=>{load();},[]);
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-xl font-mono font-semibold">Inventory</h1>
          <p className="text-xs text-zinc-600 mt-0.5">{skus.length} SKUs tracked</p></div>
        <button onClick={load} className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-[#b5f23d] border border-zinc-700 px-3 py-1.5 rounded transition-all">
          <RefreshCw size={12} className={loading?"animate-spin":""}/> Refresh</button>
      </div>
      {loading?<div className="space-y-2">{[...Array(8)].map((_,i)=><div key={i} className="skeleton h-12 w-full rounded"/>)}</div>
        :<InventoryTable data={skus} onRowClick={row=>nav(`/forecast?sku=${row.sku_id}`)}/>}
    </div>
  );
}
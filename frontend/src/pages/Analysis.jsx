import { useState, useEffect } from "react";
import { api, streamAnalysis } from "../api/client.js";
import SKUSelector from "../components/SKUSelector.jsx";
import StepIndicator from "../components/StepIndicator.jsx";
import ReportViewer from "../components/ReportViewer.jsx";
import InventoryTable from "../components/InventoryTable.jsx";
import { Play, Loader, CheckCircle, AlertCircle } from "lucide-react";
export default function Analysis() {
  const [skus,setSkus]           = useState([]);
  const [selected,setSelected]   = useState([]);
  const [analyzeAll,setAll]      = useState(false);
  const [includeRag,setRag]      = useState(true);
  const [running,setRunning]     = useState(false);
  const [events,setEvents]       = useState([]);
  const [result,setResult]       = useState(null);
  const [error,setError]         = useState(null);
  useEffect(() => { api.getAllSkus().then(setSkus).catch(()=>{}); }, []);
  const handleRun = () => {
    setRunning(true); setEvents([]); setResult(null); setError(null);
    const body = {sku_ids:analyzeAll?[]:selected,analyze_all:analyzeAll,include_rag:includeRag,mode:"batch"};
    const stop = streamAnalysis(body,
      (type,data) => {
        setEvents(p=>[...p,{...data,ts:Date.now()}]);
        if (type==="report_complete"&&data.run_id) api.getRun(data.run_id).then(setResult).catch(()=>{});
      },
      ()=>setRunning(false),
      (e)=>{setError(e.message);setRunning(false);}
    );
    return ()=>stop();
  };
  const canRun = (selected.length>0||analyzeAll)&&!running;
  return (
    <div>
      <div className="mb-6"><h1 className="text-xl font-mono font-semibold">Run Analysis</h1>
        <p className="text-xs text-zinc-600 mt-0.5">Select SKUs and launch the multi-agent pipeline</p></div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <p className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-3">Configuration</p>
            <label className="flex items-center gap-2.5 cursor-pointer mb-3">
              <input type="checkbox" checked={analyzeAll} onChange={e=>setAll(e.target.checked)} className="w-3.5 h-3.5 accent-[#b5f23d]"/>
              <span className="text-sm text-zinc-300">Analyse all 50 SKUs</span>
            </label>
            <label className="flex items-center gap-2.5 cursor-pointer mb-4">
              <input type="checkbox" checked={includeRag} onChange={e=>setRag(e.target.checked)} className="w-3.5 h-3.5 accent-[#b5f23d]"/>
              <span className="text-sm text-zinc-300">Include supplier context (RAG)</span>
            </label>
            <button onClick={handleRun} disabled={!canRun}
              className={`w-full flex items-center justify-center gap-2 py-2.5 rounded font-mono text-sm font-medium transition-all ${canRun?"bg-[#b5f23d] text-zinc-950 hover:opacity-90":"bg-zinc-800 text-zinc-600 cursor-not-allowed"}`}>
              {running?<><Loader size={13} className="animate-spin"/>Running...</>:<><Play size={13}/>Run Analysis</>}
            </button>
          </div>
          {!analyzeAll&&<div><p className="text-xs font-mono text-zinc-500 mb-2 uppercase tracking-wider">Select SKUs</p>
            <SKUSelector skus={skus} selected={selected} onChange={setSelected}/></div>}
          {error&&<div className="bg-red-950/50 border border-red-800 rounded-lg p-3 flex items-start gap-2">
            <AlertCircle size={13} className="text-red-400 mt-0.5"/>
            <p className="text-xs text-red-400 font-mono">{error}</p></div>}
          {result&&!running&&<div className="bg-[#b5f23d]/5 border border-[#b5f23d]/20 rounded-lg p-3 flex items-center gap-2">
            <CheckCircle size={13} className="text-[#b5f23d]"/>
            <p className="text-xs text-[#b5f23d] font-mono">{result.skus_analyzed} SKUs analysed</p></div>}
        </div>
        <div className="lg:col-span-2 space-y-4">
          {(running||events.length>0)&&<StepIndicator events={events} isRunning={running}/>}
          {result&&<>
            <ReportViewer markdown={result.report_text} runId={result.run_id}/>
            {result.recommendations?.length>0&&<div>
              <p className="text-sm font-mono text-zinc-400 mb-3">Recommendations ({result.recommendations.length} SKUs)</p>
              <InventoryTable data={result.recommendations.map(r=>({
                sku_id:r.sku_id,reorder_urgency:r.reorder_urgency,current_stock:r.current_stock,
                days_until_stockout:r.days_until_stockout,recommended_order_qty:r.recommended_order_qty,
                stockout_risk_pct:r.stockout_risk_pct,reorder_point:r.reorder_point,supplier_id:""}))}/>
            </div>}</>}
          {!running&&!result&&events.length===0&&<div className="bg-zinc-900 border border-zinc-800 rounded-lg p-16 text-center">
            <div className="w-12 h-12 rounded-full bg-[#b5f23d]/10 border border-[#b5f23d]/20 flex items-center justify-center mx-auto mb-4">
              <Play size={20} className="text-[#b5f23d]"/></div>
            <p className="text-zinc-400 font-mono text-sm">Select SKUs and click Run Analysis</p></div>}
        </div>
      </div>
    </div>
  );
}
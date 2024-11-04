import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, FileText } from "lucide-react";
function exportPDF(md) {
  const w = window.open("","_blank");
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"/><title>ChainIQ Report</title>
  <style>body{font-family:Segoe UI,sans-serif;max-width:800px;margin:40px auto;color:#111;}
  h1,h2,h3{color:#1a1a2e;}table{border-collapse:collapse;width:100%;margin:1em 0;}
  th{background:#1a1a2e;color:white;padding:8px 12px;text-align:left;}
  td{padding:6px 12px;border-bottom:1px solid #ddd;}code{background:#f0f0f0;padding:2px 6px;border-radius:3px;}
  @media print{@page{margin:2cm}}</style></head><body>${md}</body></html>`);
  w.document.close(); w.print();
}
export default function ReportViewer({ markdown="", runId="" }) {
  if (!markdown) return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-12 text-center">
      <FileText size={32} className="text-zinc-700 mx-auto mb-3"/>
      <p className="text-zinc-600 font-mono text-sm">No report generated yet.</p>
    </div>
  );
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 bg-zinc-950/50">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-[#b5f23d]"/>
          <span className="text-xs font-mono text-zinc-400">ChainIQ Report</span>
          {runId&&<span className="text-xs font-mono text-zinc-700 ml-2">#{runId.slice(0,8)}</span>}
        </div>
        <button onClick={()=>exportPDF(markdown)}
          className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-[#b5f23d] px-2.5 py-1 rounded border border-zinc-700">
          <Download size={11}/> Export PDF
        </button>
      </div>
      <div className="p-6 report-body overflow-y-auto max-h-[70vh]">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}
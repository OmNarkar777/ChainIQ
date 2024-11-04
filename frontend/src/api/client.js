const BASE = import.meta.env.VITE_API_URL || "/api";
async function req(path, opts = {}) {
  const r = await fetch(`${BASE}${path}`, { headers: {"Content-Type":"application/json",...opts.headers}, ...opts });
  if (!r.ok) { const e = await r.json().catch(() => ({detail:r.statusText})); throw new Error(e.detail||`HTTP ${r.status}`); }
  return r.json();
}
export const api = {
  getInventorySummary:  ()      => req("/inventory/summary"),
  getCriticalSkus:      ()      => req("/inventory/critical"),
  getAllSkus:           ()      => req("/inventory/skus"),
  getSkuDetail:        (id)     => req(`/inventory/skus/${id}`),
  getSkuHistory:       (id,d=30)=> req(`/inventory/skus/${id}/history?days=${d}`),
  forecastSku:   (id,h=7)       => req(`/forecast/sku/${id}?horizon_days=${h}`),
  forecastBatch: (ids)          => req("/forecast/batch",{method:"POST",body:JSON.stringify({sku_ids:ids,horizon_days:7})}),
  runAnalysis:  (body)          => req("/agent/analyze",{method:"POST",body:JSON.stringify(body)}),
  getRun:       (id)            => req(`/agent/runs/${id}`),
  listRuns:     ()              => req("/agent/runs"),
  health:       ()              => req("/health"),
};
export function streamAnalysis(body, onEvent, onDone, onError) {
  const ctrl  = new AbortController();
  const query = new URLSearchParams({
    sku_ids:     (body.sku_ids||[]).join(","),
    analyze_all: body.analyze_all ? "true":"false",
    include_rag: body.include_rag ? "true":"false",
    mode:        body.mode||"batch",
  });
  fetch(`${BASE}/stream/analyze?${query}`,{signal:ctrl.signal})
    .then(async (res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const dec    = new TextDecoder();
      let buf = "";
      while (true) {
        const {done,value} = await reader.read();
        if (done) break;
        buf += dec.decode(value,{stream:true});
        const lines = buf.split("\n");
        buf = lines.pop();
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try { const p = JSON.parse(line.slice(6)); onEvent(p.type,p); } catch(_) {}
          }
        }
      }
      onDone();
    })
    .catch((e) => { if (e.name!=="AbortError") onError(e); });
  return () => ctrl.abort();
}
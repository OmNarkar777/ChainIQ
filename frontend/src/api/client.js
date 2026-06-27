// API base URL.
// • Local dev:       not set → Vite proxy routes /api/* → localhost:8000
// • docker-compose:  build arg VITE_API_URL=/api → nginx proxies /api → backend
// • Vercel + Render: VITE_API_URL=https://chainiq-api.onrender.com (Vercel dashboard)
const BASE = import.meta.env.VITE_API_URL ?? "/api";

async function req(path, opts = {}) {
  const url    = `${BASE}${path}`;
  const method = (opts.method ?? "GET").toUpperCase();
  const headers = { ...opts.headers };

  // Only set Content-Type on requests that have a body — sending it on
  // GET requests turns simple CORS requests into preflighted ones unnecessarily.
  if (!["GET", "HEAD"].includes(method)) {
    headers["Content-Type"] = "application/json";
  }

  let r;
  try {
    r = await fetch(url, { ...opts, method, headers });
  } catch (networkErr) {
    throw new Error(
      `Network error — cannot reach the API at ${BASE}. ` +
        (BASE === "/api"
          ? "VITE_API_URL is not set. Add it in Vercel → Project Settings → Environment Variables, then redeploy."
          : "Check that the backend is running and CORS_ORIGINS includes this origin.")
    );
  }

  // Detect HTML responses: Vercel SPA fallback returns index.html with status
  // 200 when VITE_API_URL is not set and requests hit /api/* on the frontend
  // domain. An nginx or Render error page would also return text/html.
  const contentType = r.headers.get("content-type") ?? "";
  if (contentType.includes("text/html")) {
    throw new Error(
      BASE === "/api"
        ? "API unreachable: VITE_API_URL is not configured. " +
            "Set it to your Render backend URL in Vercel dashboard and redeploy."
        : `Unexpected HTML from ${BASE}. The service may be starting up (cold start). Retry in 30 s.`
    );
  }

  if (!r.ok) {
    const payload = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(payload.detail ?? `HTTP ${r.status}`);
  }

  return r.json();
}

export const api = {
  // Health
  health: () => req("/health"),

  // Inventory
  getInventorySummary: ()         => req("/inventory/summary"),
  getCriticalSkus:     ()         => req("/inventory/critical"),
  getAllSkus:          ()         => req("/inventory/skus"),
  getSkuDetail:        (id)       => req(`/inventory/skus/${id}`),
  getSkuHistory:       (id, d=30) => req(`/inventory/skus/${id}/history?days=${d}`),
  getAnalytics:        ()         => req("/inventory/analytics"),

  // Forecast
  forecastSku:   (id, h=7) => req(`/forecast/sku/${id}?horizon_days=${h}`),
  forecastBatch: (ids)     => req("/forecast/batch", { method: "POST", body: JSON.stringify({ sku_ids: ids, horizon_days: 7 }) }),

  // Agent
  runAnalysis: (body) => req("/agent/analyze", { method: "POST", body: JSON.stringify(body) }),
  getRun:      (id)   => req(`/agent/runs/${id}`),
  listRuns:    ()     => req("/agent/runs"),
};

export function streamAnalysis(body, onEvent, onDone, onError) {
  const ctrl  = new AbortController();
  const query = new URLSearchParams({
    sku_ids:     (body.sku_ids ?? []).join(","),
    analyze_all: body.analyze_all ? "true" : "false",
    include_rag: body.include_rag ? "true" : "false",
  });

  fetch(`${BASE}/stream/analyze?${query}`, { signal: ctrl.signal })
    .then(async (res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const dec    = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const p = JSON.parse(line.slice(6));
              onEvent(p.type, p);
            } catch (_) { /* malformed SSE chunk — skip */ }
          }
        }
      }
      onDone();
    })
    .catch((e) => { if (e.name !== "AbortError") onError(e); });

  return () => ctrl.abort();
}

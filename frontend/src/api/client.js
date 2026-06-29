// API base URL.
// • Local dev:       not set → Vite proxy routes /api/* → localhost:8000
// • docker-compose:  build arg VITE_API_URL=/api → nginx proxies /api → backend
// • Vercel + Render: VITE_API_URL=https://chainiq-api.onrender.com (Vercel dashboard)
const BASE = import.meta.env.VITE_API_URL ?? "/api";

// ── In-memory TTL cache ───────────────────────────────────────────────────────
// Shared across all pages — navigating back to a page returns cached data
// instantly without another Render round-trip.
//
// Static-list paths use an exact key; per-SKU paths use prefix matching.
const _cache = new Map(); // key → { data, expires }

const CACHE_TTL = {
  // Exact-path keys
  "/inventory/dashboard": 30_000,   // 30 s — summary, analytics, critical SKUs
  "/inventory/skus":      120_000,  // 2 min — full 300-record list (gzipped ~18 KB)
  "/inventory/sku-ids":   300_000,  // 5 min — static lightweight list (~5 KB)
  "/inventory/summary":   30_000,
  "/inventory/critical":  30_000,
  "/inventory/analytics": 60_000,
  "/inventory/suppliers": 60_000,
  "/health/meta":         60_000,
  "/agent/runs":          10_000,   // runs change frequently

  // Prefix keys (paths starting with these get the associated TTL)
  "/forecast/sku/":        60_000,  // per-SKU forecast (warmed cache = instant)
  "/inventory/skus/":      60_000,  // per-SKU detail + history
};

function _getTtl(path) {
  // Exact match first
  if (CACHE_TTL[path] !== undefined) return CACHE_TTL[path];
  // Prefix match for dynamic per-resource paths
  for (const [prefix, ttl] of Object.entries(CACHE_TTL)) {
    if (prefix.endsWith("/") && path.startsWith(prefix)) return ttl;
  }
  return 0; // not cacheable
}

function _getCached(path) {
  const entry = _cache.get(path);
  if (entry && Date.now() < entry.expires) return entry.data;
  return null;
}

function _setCached(path, data) {
  const ttl = _getTtl(path);
  if (ttl > 0) _cache.set(path, { data, expires: Date.now() + ttl });
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function req(path, opts = {}) {
  const url    = `${BASE}${path}`;
  const method = (opts.method ?? "GET").toUpperCase();
  const headers = { ...opts.headers };

  // Use cache only for cacheable GET requests (unless caller says skipCache)
  if (method === "GET" && !opts.skipCache) {
    const cached = _getCached(path);
    if (cached !== null) return cached;
  }

  if (!["GET", "HEAD"].includes(method)) {
    headers["Content-Type"] = "application/json";
  }

  // 15-second timeout on all REST requests.
  // Render free tier cold starts take 30-60s, but with warmup the backend
  // responds in <1s once hot. 15s gives comfortable headroom for warm
  // backends while providing a clear error instead of infinite hang on
  // cold starts.
  let timeoutId;
  const timeoutCtrl = new AbortController();
  timeoutId = setTimeout(() => timeoutCtrl.abort(), 15_000);

  // Merge with any existing signal from opts
  const signal = opts.signal ?? timeoutCtrl.signal;

  let r;
  try {
    r = await fetch(url, { ...opts, method, headers, signal });
  } catch (networkErr) {
    clearTimeout(timeoutId);
    if (networkErr.name === "AbortError") {
      throw new Error(
        `Request timed out after 15s — the backend may be starting up (Render cold start). ` +
        `Please wait 30–60 seconds and try again.`
      );
    }
    throw new Error(
      `Network error — cannot reach the API at ${BASE}. ` +
        (BASE === "/api"
          ? "VITE_API_URL is not set. Add it in Vercel → Project Settings → Environment Variables, then redeploy."
          : "Check that the backend is running and CORS_ORIGINS includes this origin.")
    );
  }
  clearTimeout(timeoutId);

  // Detect HTML responses: Vercel SPA fallback returns index.html with status
  // 200 when VITE_API_URL is not set and requests hit /api/* on the frontend
  // domain. An nginx or Render error page would also return text/html.
  const contentType = r.headers.get("content-type") ?? "";
  if (contentType.includes("text/html")) {
    throw new Error(
      BASE === "/api"
        ? "API unreachable: VITE_API_URL is not configured. " +
            "Set it to your Render backend URL in Vercel dashboard and redeploy."
        : `Unexpected HTML from ${BASE}. The backend may be starting up. Retry in 30 s.`
    );
  }

  if (!r.ok) {
    const payload = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(payload.detail ?? `HTTP ${r.status}`);
  }

  const data = await r.json();
  if (method === "GET") _setCached(path, data);
  return data;
}

// ── Public API ─────────────────────────────────────────────────────────────────

export const api = {
  // Health / Meta
  health:   () => req("/health"),
  getMeta:  () => req("/health/meta"),

  // Dashboard — single call replacing 4 separate round-trips
  getDashboard: () => req("/inventory/dashboard"),

  // Inventory
  getInventorySummary: ()         => req("/inventory/summary"),
  getCriticalSkus:     ()         => req("/inventory/critical"),
  getAllSkus:          ()         => req("/inventory/skus"),
  getSkuIds:           ()         => req("/inventory/sku-ids"),
  getSkuDetail:        (id)       => req(`/inventory/skus/${id}`),
  getSkuHistory:       (id, d=30) => req(`/inventory/skus/${id}/history?days=${d}`),
  getAnalytics:        ()         => req("/inventory/analytics"),
  getSupplierMetrics:  ()         => req("/inventory/suppliers"),

  // Forecast
  forecastSku:   (id, h=7) => req(`/forecast/sku/${id}?horizon_days=${h}`),
  forecastBatch: (ids)     => req("/forecast/batch", { method: "POST", body: JSON.stringify({ sku_ids: ids, horizon_days: 7 }) }),

  // Agent
  runAnalysis: (body) => req("/agent/analyze", { method: "POST", body: JSON.stringify(body) }),
  getRun:      (id)   => req(`/agent/runs/${id}`),
  listRuns:    ()     => req("/agent/runs"),
};

// ── Cache utilities ────────────────────────────────────────────────────────────

/** Invalidate a specific cached path. */
export function invalidateCache(path) {
  _cache.delete(path);
}

/** Clear the entire cache (e.g. on manual Refresh click). */
export function clearCache() {
  _cache.clear();
}

// ── SSE streaming ─────────────────────────────────────────────────────────────

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

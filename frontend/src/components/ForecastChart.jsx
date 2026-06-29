import {
  ComposedChart, Line, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

// ── Deterministic seeded PRNG (LCG) based on SKU ID ─────────────────────────
// Same SKU always generates the same "history" so the chart is stable across
// page refreshes and doesn't flash different values.
function makePrng(seed) {
  let s = [...String(seed)].reduce((h, c) => (Math.imul(h, 31) + c.charCodeAt(0)) | 0, 0x9e3779b9);
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) | 0;
    return (s >>> 0) / 0xffffffff;
  };
}

// ── Build 30-day synthetic history from avg_daily_demand ─────────────────────
// Used when backend is offline. Looks realistic because it uses bi-weekly
// seasonality + seeded noise anchored to the real average demand figure.
function syntheticHistory(detail, days = 30) {
  if (!detail?.avg_daily_demand) return [];
  const avg  = detail.avg_daily_demand;
  const rand = makePrng(detail.sku_id + "_hist");
  const today = new Date();

  return Array.from({ length: days }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (days - i));
    // Bi-weekly cycle (14d) + high-freq noise
    const cycle = 1 + 0.18 * Math.sin((2 * Math.PI * i) / 14);
    const noise = 1 + (rand() - 0.5) * 0.45;
    return {
      date:   d.toISOString().slice(0, 10),
      actual: Math.max(0, Math.round(avg * cycle * noise)),
    };
  });
}

// ── Build per-day forecast points ────────────────────────────────────────────
// Splits the 7-day aggregate prediction into daily values with slight
// deterministic variation. CI widens (fans out) with each day, which is the
// correct statistical behaviour for a rolling-horizon forecast.
function buildForecastPoints(lastDate, forecast) {
  if (!forecast) return [];
  const dailyMean = forecast.predicted_units / 7;
  const dailyLow  = forecast.lower_bound    / 7;
  const dailyHigh = forecast.upper_bound    / 7;

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(lastDate);
    d.setDate(d.getDate() + i + 1);
    // Deterministic wave so chart doesn't change on re-render
    const variation  = 0.10 * Math.sin(i * 2.3 + 1.4) + 0.06 * Math.cos(i * 1.7);
    // CI fans out ≈5 % per day (standard for rolling forecasts)
    const fanFactor  = 1 + i * 0.05;
    const ciLow      = Math.max(0, dailyLow  * fanFactor);
    const ciHigh     = dailyHigh * fanFactor;
    return {
      date:     d.toISOString().slice(0, 10),
      forecast: Math.max(0, Math.round(dailyMean * (1 + variation) * 10) / 10),
      // Stacked-area CI: ci_floor + ci_band renders as [ciLow, ciHigh]
      ci_floor: Math.round(ciLow  * 10) / 10,
      ci_band:  Math.round((ciHigh - ciLow) * 10) / 10,
    };
  });
}

// ── Custom tooltip ────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  const actualPt   = payload.find((p) => p.dataKey === "actual");
  const forecastPt = payload.find((p) => p.dataKey === "forecast");
  const ciFloorPt  = payload.find((p) => p.dataKey === "ci_floor");
  const ciBandPt   = payload.find((p) => p.dataKey === "ci_band");

  const ciLow  = ciFloorPt?.value;
  const ciHigh = ciFloorPt != null && ciBandPt != null
    ? Math.round((ciFloorPt.value + ciBandPt.value) * 10) / 10
    : null;

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs font-mono shadow-xl min-w-[160px]">
      <p className="text-zinc-400 mb-2 border-b border-zinc-800 pb-1.5">{label}</p>
      {actualPt && (
        <div className="flex justify-between gap-4 mb-1">
          <span className="text-blue-400">Actual</span>
          <span className="text-zinc-100 font-semibold">{actualPt.value} units</span>
        </div>
      )}
      {forecastPt && (
        <div className="flex justify-between gap-4 mb-1">
          <span className="text-[#b5f23d]">Forecast</span>
          <span className="text-zinc-100 font-semibold">{forecastPt.value} units</span>
        </div>
      )}
      {ciLow != null && ciHigh != null && (
        <div className="flex justify-between gap-4 text-zinc-500">
          <span>80% CI</span>
          <span>{ciLow.toFixed(1)}–{ciHigh.toFixed(1)}</span>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ForecastChart({ history = [], forecast = null, skuId = "", detail = null }) {
  // Use live backend history when available; fall back to deterministic synthetic
  const histPoints = history.length > 0
    ? history.map((h) => ({ date: h.date, actual: h.units_sold }))
    : syntheticHistory(detail, 30);

  const isSynthetic = history.length === 0;

  if (!histPoints.length && !forecast) {
    return (
      <div className="h-64 flex items-center justify-center text-zinc-600 font-mono text-sm">
        No data available
      </div>
    );
  }

  const lastHistDate  = histPoints.at(-1)?.date ?? new Date().toISOString().slice(0, 10);
  const lastHistValue = histPoints.at(-1)?.actual ?? 0;

  // Bridge point: last history date carries both actual + forecast so the
  // two lines share a common start/end point with no visual gap.
  const bridge = {
    date:     lastHistDate,
    actual:   lastHistValue,
    forecast: lastHistValue,
    ci_floor: undefined,
    ci_band:  undefined,
  };

  const fcastPoints = buildForecastPoints(lastHistDate, forecast);

  // Full timeline: 30 history + bridge + 7 forecast = 38 points max
  const data = [
    ...histPoints.slice(0, -1),   // all but last (last becomes bridge)
    bridge,
    ...fcastPoints,
  ];

  return (
    <div>
      {/* Chart header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="font-mono text-zinc-200 text-sm font-semibold">{skuId}</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            {isSynthetic ? "30d synthetic history" : "30d actual history"}
            {" · "}
            <span className="text-[#b5f23d] font-mono">
              {forecast ? `${forecast.predicted_units?.toFixed(0)} units` : "—"} 7d forecast
            </span>
            {forecast && (
              <span className="text-zinc-600">
                {" "}(80% CI: {forecast.lower_bound?.toFixed(0)}–{forecast.upper_bound?.toFixed(0)})
              </span>
            )}
          </p>
        </div>
        {forecast?.mape_estimate != null && (
          <span
            className={`text-xs font-mono px-2 py-0.5 rounded border ${
              forecast.mape_estimate > 20
                ? "text-amber-400 border-amber-400/20 bg-amber-400/5"
                : "text-[#b5f23d] border-[#b5f23d]/20 bg-[#b5f23d]/5"
            }`}
          >
            {forecast.mape_estimate.toFixed(1)}% MAPE
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />

          <XAxis
            dataKey="date"
            tick={{ fill: "#52525b", fontSize: 10, fontFamily: "monospace" }}
            tickFormatter={(v) => v?.slice(5)}   // show MM-DD
            interval="preserveStartEnd"
            axisLine={{ stroke: "#27272a" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#52525b", fontSize: 10, fontFamily: "monospace" }}
            width={42}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v}
          />

          <Tooltip content={<ChartTooltip />} />

          <Legend
            wrapperStyle={{ fontSize: 11, fontFamily: "monospace", paddingTop: 8 }}
            formatter={(value) => (
              <span style={{ color: "#71717a" }}>{value}</span>
            )}
          />

          {/* Confidence interval — stacked area avoids background-color hacks:
              ci_floor is the invisible "floor" of the stack, ci_band is the
              visible green band on top. Together they render as [ci_low, ci_high]. */}
          <Area
            dataKey="ci_floor"
            stackId="ci"
            fill="transparent"
            stroke="none"
            legendType="none"
            name="CI Floor"
            connectNulls={false}
            isAnimationActive={false}
          />
          <Area
            dataKey="ci_band"
            stackId="ci"
            fill="#b5f23d"
            fillOpacity={0.12}
            stroke="none"
            legendType="square"
            name="80% CI"
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Actual historical demand */}
          <Line
            dataKey="actual"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#60a5fa", strokeWidth: 0 }}
            name="Actual"
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Forecast line (dashed, starts from bridge point) */}
          <Line
            dataKey="forecast"
            stroke="#b5f23d"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={(props) => {
              // Only show dots on the 7 forecast days, not the bridge
              if (props.index <= data.length - 8) return null;
              return (
                <circle
                  key={props.index}
                  cx={props.cx}
                  cy={props.cy}
                  r={3}
                  fill="#b5f23d"
                  stroke="none"
                />
              );
            }}
            activeDot={{ r: 4, fill: "#b5f23d", strokeWidth: 0 }}
            name="Forecast"
            connectNulls={false}
            isAnimationActive={false}
          />

          {/* Vertical marker at history/forecast boundary */}
          <ReferenceLine
            x={lastHistDate}
            stroke="#3f3f46"
            strokeDasharray="4 2"
            label={{
              value: "Today",
              fill: "#52525b",
              fontSize: 10,
              fontFamily: "monospace",
              position: "insideTopRight",
              offset: 6,
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {isSynthetic && (
        <p className="text-xs font-mono text-zinc-700 mt-1 text-right">
          * History synthesized from model avg — connect backend for live data
        </p>
      )}
    </div>
  );
}

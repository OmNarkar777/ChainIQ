import {
  ComposedChart, Line, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-xs font-mono shadow-xl">
      <p className="text-zinc-400 mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="text-zinc-200">
            {typeof p.value === "number" ? p.value.toFixed(1) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ForecastChart({ history = [], forecast = null, skuId = "" }) {
  if (!history.length && !forecast) {
    return (
      <div className="h-64 flex items-center justify-center text-zinc-600 font-mono text-sm">
        No data
      </div>
    );
  }

  const histPoints = history.map((h) => ({ date: h.date, actual: h.units_sold }));
  // Use a real date fallback — "Today" is not a valid Date string and crashes toISOString()
  const today      = history.at(-1)?.date ?? new Date().toISOString().slice(0, 10);

  let data = [...histPoints];
  if (forecast) {
    const lastDate = new Date(today);
    for (let i = 1; i <= 7; i++) {
      const d = new Date(lastDate);
      d.setDate(d.getDate() + i);
      data.push({
        date:     d.toISOString().slice(0, 10),
        forecast: forecast.predicted_units / 7,
        ci_low:   forecast.lower_bound / 7,
        ci_high:  forecast.upper_bound / 7,
      });
    }
  }

  // Show last 37 data points (30 history + 7 forecast)
  data = data.slice(-37);

  return (
    <div>
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="font-mono text-zinc-200 text-sm">{skuId}</p>
          {forecast && (
            <p className="text-xs text-zinc-500 mt-0.5">
              7-day:{" "}
              <span className="text-[#b5f23d] font-mono">
                {forecast.predicted_units?.toFixed(1)} units
              </span>
              {" "}(80% CI: {forecast.lower_bound?.toFixed(0)}–{forecast.upper_bound?.toFixed(0)})
            </p>
          )}
        </div>
        {forecast?.mape_estimate != null && (
          <p
            className={`text-sm font-mono ${
              forecast.mape_estimate > 20 ? "text-amber-400" : "text-[#b5f23d]"
            }`}
          >
            {forecast.mape_estimate.toFixed(1)}% MAPE
          </p>
        )}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#52525b", fontSize: 10, fontFamily: "DM Mono" }}
            tickFormatter={(v) => v?.slice(5)}
            interval="preserveStartEnd"
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#52525b", fontSize: 10, fontFamily: "DM Mono" }}
            width={36}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11, fontFamily: "DM Mono", color: "#71717a" }} />

          {/* Confidence interval shading */}
          <Area dataKey="ci_high" fill="#b5f23d" stroke="none" fillOpacity={0.08} name="CI Upper" legendType="none" />
          <Area dataKey="ci_low"  fill="#09090b" stroke="none" fillOpacity={1}    name="CI Lower" legendType="none" />

          <Line dataKey="actual"   stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual"   connectNulls />
          <Line
            dataKey="forecast"
            stroke="#b5f23d"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={{ fill: "#b5f23d", r: 3 }}
            name="Forecast"
            connectNulls
          />

          <ReferenceLine
            x={today}
            stroke="#3f3f46"
            strokeDasharray="4 2"
            label={{ value: "Today", fill: "#52525b", fontSize: 10, fontFamily: "DM Mono" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

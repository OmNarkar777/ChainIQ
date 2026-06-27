import { Check, Loader, Clock } from "lucide-react";

const STEPS = [
  { key: "forecasting_start",    label: "XGBoost Forecast",      sub: "Forecasting Agent" },
  { key: "forecasting_complete", label: "Forecast Ready",         sub: "" },
  { key: "inventory_complete",   label: "Inventory Calculated",   sub: "Inventory Agent (EOQ + Safety Stock)" },
  { key: "rag_complete",         label: "Supplier Context",       sub: "RAG Retriever (ChromaDB)" },
  { key: "report_complete",      label: "Report Generated",       sub: "Report Agent (Groq LLM)" },
];

const ORDER = STEPS.map((s) => s.key);

export default function StepIndicator({ events = [], isRunning }) {
  const done  = new Set(events.map((e) => e.type));
  const lastI = ORDER.reduce((a, k, i) => (done.has(k) ? i : a), -1);

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 mb-6">
      <p className="text-xs text-zinc-500 font-mono mb-3 uppercase tracking-wider">
        Pipeline Progress
      </p>
      <div className="space-y-2">
        {STEPS.map((step, i) => {
          const isDone    = done.has(step.key);
          const isRunning_ = isRunning && i === lastI + 1;
          const isPending  = !isDone && !isRunning_;
          const durationMs = events.find((e) => e.type === step.key)?.duration_ms;

          return (
            <div
              key={step.key}
              className={`flex items-center gap-3 transition-all duration-300 ${isPending ? "opacity-40" : ""}`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border ${
                  isDone
                    ? "bg-[#b5f23d]/20 border-[#b5f23d]"
                    : isRunning_
                    ? "bg-zinc-800 border-zinc-600 animate-pulse"
                    : "bg-zinc-900 border-zinc-700"
                }`}
              >
                {isDone    && <Check  size={12} className="text-[#b5f23d]" />}
                {isRunning_ && <Loader size={12} className="text-zinc-400 animate-spin" />}
                {isPending  && <Clock  size={12} className="text-zinc-600" />}
              </div>

              <div className="flex-1 min-w-0">
                <p className={`text-sm font-mono ${
                  isDone ? "text-[#b5f23d]" : isRunning_ ? "text-zinc-200" : "text-zinc-500"
                }`}>
                  {step.label}
                </p>
                {step.sub && <p className="text-xs text-zinc-600">{step.sub}</p>}
              </div>

              {isDone && durationMs && (
                <span className="text-xs font-mono text-zinc-600 shrink-0">{durationMs}ms</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

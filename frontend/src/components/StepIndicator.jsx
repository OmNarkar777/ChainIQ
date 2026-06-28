import { Check, Loader, Clock } from "lucide-react";

const STAGES = [
  { id: "forecast",  label: "Forecast",  sub: "XGBoost demand prediction" },
  { id: "inventory", label: "Inventory", sub: "EOQ · ROP · Safety stock" },
  { id: "rag",       label: "RAG",       sub: "ChromaDB supplier context" },
  { id: "llm",       label: "LLM",       sub: "Groq LLaMA 3.3 70B report" },
  { id: "complete",  label: "Complete",  sub: "" },
];

export default function StepIndicator({ animatedStages = new Set(), metrics = {}, isRunning = false }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <p className="text-xs text-zinc-500 font-mono mb-3 uppercase tracking-wider">
        Pipeline Progress
      </p>
      <div className="space-y-2.5">
        {STAGES.map((stage, i) => {
          const isDone    = animatedStages.has(stage.id);
          const isActive  = isRunning && !isDone && animatedStages.size === i;
          const isPending = !isDone && !isActive;

          // Pick the real latency if available
          const ms =
            stage.id === "forecast"  ? metrics.forecast_ms  :
            stage.id === "inventory" ? metrics.inventory_ms :
            stage.id === "rag"       ? metrics.rag_ms       :
            stage.id === "llm"       ? metrics.llm_ms       :
            stage.id === "complete"  ? metrics.total_ms     : undefined;

          const cacheHit =
            stage.id === "forecast" ? metrics.forecast_cache_hits > 0 :
            stage.id === "llm"      ? metrics.llm_cache_hit          : false;

          return (
            <div
              key={stage.id}
              className={`flex items-center gap-3 transition-all duration-300 ${
                isPending ? "opacity-30" : ""
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border transition-all duration-300 ${
                  isDone
                    ? "bg-[#b5f23d]/20 border-[#b5f23d]"
                    : isActive
                    ? "bg-zinc-800 border-zinc-500 animate-pulse"
                    : "bg-zinc-900 border-zinc-700"
                }`}
              >
                {isDone   && <Check  size={12} className="text-[#b5f23d]" />}
                {isActive && <Loader size={12} className="text-zinc-400 animate-spin" />}
                {isPending && !isActive && <Clock size={12} className="text-zinc-700" />}
              </div>

              <div className="flex-1 min-w-0">
                <p className={`text-sm font-mono font-medium ${
                  isDone ? "text-[#b5f23d]" : isActive ? "text-zinc-200" : "text-zinc-600"
                }`}>
                  {stage.label}
                </p>
                {stage.sub && (
                  <p className="text-xs text-zinc-600 truncate">{stage.sub}</p>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {cacheHit && isDone && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 bg-[#b5f23d]/10 border border-[#b5f23d]/30 text-[#b5f23d] rounded">
                    HIT
                  </span>
                )}
                {isDone && ms != null && (
                  <span className="text-xs font-mono text-zinc-500">{ms.toLocaleString()}ms</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

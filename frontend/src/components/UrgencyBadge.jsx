const C = {
  CRITICAL: { bg:"bg-red-950/80 border border-red-700",    text:"text-red-400",    dot:"bg-red-500 animate-pulse" },
  HIGH:     { bg:"bg-amber-950/80 border border-amber-700", text:"text-amber-400",  dot:"bg-amber-400" },
  MEDIUM:   { bg:"bg-yellow-950/80 border border-yellow-700",text:"text-yellow-400",dot:"bg-yellow-400" },
  LOW:      { bg:"bg-zinc-800/80 border border-zinc-700",   text:"text-zinc-400",   dot:"bg-zinc-500" },
};
export default function UrgencyBadge({ urgency }) {
  const c = C[urgency]||C.LOW;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`}/>{urgency||"LOW"}
    </span>
  );
}
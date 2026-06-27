import { useState, useMemo } from "react";
import { Search, X, CheckSquare, Square } from "lucide-react";

export default function SKUSelector({ skus = [], selected = [], onChange }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      skus.filter(
        (s) =>
          s.sku_id.toLowerCase().includes(query.toLowerCase()) ||
          (s.category ?? "").toLowerCase().includes(query.toLowerCase())
      ),
    [skus, query]
  );

  const toggle = (id) =>
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
      {/* Search input */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800">
        <Search size={13} className="text-zinc-600 shrink-0" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search SKU or category…"
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none font-mono"
        />
        {query && (
          <button onClick={() => setQuery("")}>
            <X size={12} className="text-zinc-600 hover:text-zinc-400" />
          </button>
        )}
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-950/50 border-b border-zinc-800">
        <span className="text-xs font-mono text-zinc-600">{selected.length} selected</span>
        <div className="flex gap-3">
          <button
            onClick={() => onChange(filtered.map((s) => s.sku_id))}
            className="text-xs font-mono text-[#b5f23d] hover:opacity-80"
          >
            All ({filtered.length})
          </button>
          <button
            onClick={() => onChange([])}
            className="text-xs font-mono text-zinc-500 hover:text-zinc-300"
          >
            Clear
          </button>
        </div>
      </div>

      {/* SKU list */}
      <div className="max-h-52 overflow-y-auto">
        {filtered.map((s) => {
          const isSelected = selected.includes(s.sku_id);
          return (
            <div
              key={s.sku_id}
              onClick={() => toggle(s.sku_id)}
              className={`flex items-center gap-2.5 px-3 py-2 cursor-pointer text-sm border-b border-zinc-800/40 last:border-0 transition-colors ${
                isSelected ? "bg-[#b5f23d]/5" : "hover:bg-zinc-800/50"
              }`}
            >
              {isSelected
                ? <CheckSquare size={13} className="text-[#b5f23d] shrink-0" />
                : <Square      size={13} className="text-zinc-700 shrink-0" />
              }
              <span className={`font-mono text-xs ${isSelected ? "text-[#b5f23d]" : "text-zinc-300"}`}>
                {s.sku_id}
              </span>
              <span className="text-zinc-600 text-xs ml-auto">{s.category}</span>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <p className="text-center text-zinc-600 font-mono text-xs py-6">No matches</p>
        )}
      </div>
    </div>
  );
}

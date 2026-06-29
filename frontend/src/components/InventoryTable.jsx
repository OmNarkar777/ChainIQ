import { useState, useMemo } from "react";
import { ArrowUpDown, ArrowUp, ArrowDown, Search, X, ChevronLeft, ChevronRight } from "lucide-react";
import UrgencyBadge from "./UrgencyBadge.jsx";

const URGENCY_RANK = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const PAGE_SIZE = 25;

function SortBtn({ col, sort, onSort }) {
  const active = sort.col === col;
  return (
    <button onClick={() => onSort(col)} className="inline-flex items-center gap-1 hover:text-[#b5f23d] transition-colors">
      {!active && <ArrowUpDown size={10} className="text-zinc-600" />}
      {active && sort.dir === "asc"  && <ArrowUp   size={10} className="text-[#b5f23d]" />}
      {active && sort.dir === "desc" && <ArrowDown  size={10} className="text-[#b5f23d]" />}
    </button>
  );
}

const SORTABLE_COLS = [
  { col: "reorder_urgency",       label: "Urgency"   },
  { col: "sku_id",                label: "SKU"       },
  { col: "current_stock",         label: "Stock"     },
  { col: "days_until_stockout",   label: "Days Left" },
  { col: "recommended_order_qty", label: "Order Qty" },
  { col: "stockout_risk_pct",     label: "Risk %"    },
];

export default function InventoryTable({ data = [], onRowClick, showSearch = true }) {
  const [sort,   setSort]   = useState({ col: "reorder_urgency", dir: "asc" });
  const [filter, setFilter] = useState("ALL");
  const [query,  setQuery]  = useState("");
  const [page,   setPage]   = useState(0);

  const FILTERS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

  const counts = useMemo(() => Object.fromEntries(
    FILTERS.map((f) => [f, f === "ALL" ? data.length : data.filter((r) => r.reorder_urgency === f).length])
  ), [data]);

  const sorted = useMemo(() => {
    let rows = filter === "ALL" ? data : data.filter((r) => r.reorder_urgency === filter);
    if (query.trim()) {
      const q = query.toLowerCase();
      rows = rows.filter((r) =>
        r.sku_id?.toLowerCase().includes(q) ||
        r.sku_name?.toLowerCase().includes(q) ||
        r.category?.toLowerCase().includes(q) ||
        r.supplier_id?.toLowerCase().includes(q) ||
        r.warehouse_id?.toLowerCase().includes(q)
      );
    }
    return [...rows].sort((a, b) => {
      let va = a[sort.col];
      let vb = b[sort.col];
      if (sort.col === "reorder_urgency") { va = URGENCY_RANK[va]; vb = URGENCY_RANK[vb]; }
      if (typeof va === "string") return sort.dir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
      return sort.dir === "asc" ? va - vb : vb - va;
    });
  }, [data, filter, query, sort]);

  // Reset to page 0 when filter/query/sort changes
  const setFilterReset  = (f) => { setFilter(f);  setPage(0); };
  const setQueryReset   = (q) => { setQuery(q);   setPage(0); };

  const onSort = (col) => {
    setSort((s) => ({ col, dir: s.col === col && s.dir === "asc" ? "desc" : "asc" }));
    setPage(0);
  };

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageRows   = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div>
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        {showSearch && (
          <div className="relative flex-1 max-w-sm">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
            <input
              value={query}
              onChange={(e) => setQueryReset(e.target.value)}
              placeholder="Search SKU, name, category, supplier…"
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-8 pr-8 py-2 text-xs font-mono text-zinc-200 placeholder:text-zinc-600 outline-none focus:border-zinc-600 transition-colors"
            />
            {query && (
              <button onClick={() => setQueryReset("")} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X size={12} className="text-zinc-600 hover:text-zinc-400" />
              </button>
            )}
          </div>
        )}

        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilterReset(f)}
              className={`px-2.5 py-1 rounded text-xs font-mono border transition-all ${
                filter === f
                  ? "bg-[#b5f23d] text-zinc-950 border-[#b5f23d]"
                  : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:border-zinc-600"
              }`}
            >
              {f} <span className="opacity-60">({counts[f]})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Count + pagination info */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-mono text-zinc-600">
          {sorted.length} of {data.length} SKUs
          {query && ` matching "${query}"`}
          {totalPages > 1 && ` · page ${page + 1}/${totalPages}`}
        </p>
        {totalPages > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1 rounded text-zinc-500 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs font-mono text-zinc-600 px-1">{page + 1}/{totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="p-1 rounded text-zinc-500 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Table — renders only PAGE_SIZE rows at a time */}
      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-zinc-900/80 border-b border-zinc-800">
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                <span className="flex items-center gap-1">
                  Urgency <SortBtn col="reorder_urgency" sort={sort} onSort={onSort} />
                </span>
              </th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                <span className="flex items-center gap-1">
                  SKU <SortBtn col="sku_id" sort={sort} onSort={onSort} />
                </span>
              </th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider">Name</th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider">Category</th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                <span className="flex items-center gap-1">
                  Stock <SortBtn col="current_stock" sort={sort} onSort={onSort} />
                </span>
              </th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                <span className="flex items-center gap-1">
                  Days Left <SortBtn col="days_until_stockout" sort={sort} onSort={onSort} />
                </span>
              </th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                <span className="flex items-center gap-1">
                  Order Qty <SortBtn col="recommended_order_qty" sort={sort} onSort={onSort} />
                </span>
              </th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">
                <span className="flex items-center gap-1">
                  Risk <SortBtn col="stockout_risk_pct" sort={sort} onSort={onSort} />
                </span>
              </th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">Supplier</th>
              <th className="px-3 py-2.5 text-left font-mono text-zinc-500 uppercase tracking-wider whitespace-nowrap">WH</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/40">
            {pageRows.map((row) => (
              <tr
                key={row.sku_id}
                onClick={() => onRowClick?.(row)}
                className={`transition-colors group ${onRowClick ? "cursor-pointer" : ""} ${
                  row.reorder_urgency === "CRITICAL"
                    ? "bg-red-950/10 hover:bg-red-950/30"
                    : row.reorder_urgency === "HIGH"
                    ? "bg-amber-950/10 hover:bg-amber-950/30"
                    : "hover:bg-zinc-800/30"
                }`}
              >
                <td className="px-3 py-2.5">
                  <UrgencyBadge urgency={row.reorder_urgency} />
                </td>
                <td className="px-3 py-2.5 font-mono text-zinc-200 whitespace-nowrap group-hover:text-[#b5f23d] transition-colors">
                  {row.sku_id}
                </td>
                <td className="px-3 py-2.5 text-zinc-400 max-w-[180px] truncate" title={row.sku_name}>
                  {row.sku_name || "—"}
                </td>
                <td className="px-3 py-2.5">
                  <span className="text-zinc-500 bg-zinc-800/60 px-1.5 py-0.5 rounded text-xs">
                    {row.category || "—"}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums text-zinc-300">
                  {row.current_stock?.toFixed(0)}
                </td>
                <td className={`px-3 py-2.5 font-mono tabular-nums ${
                  row.days_until_stockout < 5
                    ? "text-red-400 font-bold"
                    : row.days_until_stockout < 12
                    ? "text-amber-400"
                    : "text-zinc-300"
                }`}>
                  {row.days_until_stockout?.toFixed(1)}d
                </td>
                <td className="px-3 py-2.5 font-mono text-[#b5f23d] tabular-nums">
                  {row.recommended_order_qty > 0 ? `+${row.recommended_order_qty?.toFixed(0)}` : "—"}
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums">
                  <span className={
                    row.stockout_risk_pct > 70 ? "text-red-400" :
                    row.stockout_risk_pct > 40 ? "text-amber-400" : "text-zinc-500"
                  }>
                    {row.stockout_risk_pct?.toFixed(0)}%
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-zinc-500 whitespace-nowrap">
                  {row.supplier_id || "—"}
                </td>
                <td className="px-3 py-2.5 font-mono text-zinc-600 whitespace-nowrap">
                  {row.warehouse_id?.replace("WH_", "") || "—"}
                </td>
              </tr>
            ))}
            {pageRows.length === 0 && (
              <tr>
                <td colSpan={10} className="py-16 text-center text-zinc-600 font-mono text-sm">
                  {query ? `No SKUs match "${query}"` : "No SKUs match the current filter"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Bottom pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-3">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-mono text-zinc-500 border border-zinc-800 rounded hover:border-zinc-600 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            <ChevronLeft size={12} /> Prev
          </button>
          <span className="text-xs font-mono text-zinc-600">
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, sorted.length)} of {sorted.length}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-mono text-zinc-500 border border-zinc-800 rounded hover:border-zinc-600 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Next <ChevronRight size={12} />
          </button>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearCache } from "../api/client.js";
import InventoryTable from "../components/InventoryTable.jsx";
import { RefreshCw, AlertCircle } from "lucide-react";

export default function Inventory() {
  const [skus, setSkus]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const navigate = useNavigate();

  const load = (bust = false) => {
    if (bust) clearCache();
    setLoading(true);
    setError(null);
    api.getAllSkus()
      .then(setSkus)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-mono font-semibold">Inventory</h1>
          <p className="text-xs text-zinc-600 mt-0.5">
            {loading ? "Loading…" : `${skus.length} SKUs tracked`}
          </p>
        </div>
        <button
          onClick={() => load(true)}
          className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-[#b5f23d] border border-zinc-700 hover:border-[#b5f23d]/50 px-3 py-1.5 rounded transition-all"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-950/50 border border-red-800 rounded-lg p-4 mb-6 flex items-start gap-2">
          <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-red-400 font-mono text-sm">{error}</p>
            {error.includes("starting up") && (
              <p className="text-red-500 text-xs mt-1">
                The backend is waking up on Render. Wait 30–60 seconds and click Refresh.
              </p>
            )}
          </div>
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="skeleton h-12 w-full rounded" />
          ))}
        </div>
      ) : (
        <InventoryTable
          data={skus}
          onRowClick={(row) => navigate(`/forecast?sku=${row.sku_id}`)}
        />
      )}
    </div>
  );
}

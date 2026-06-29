import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearCache } from "../api/client.js";
import SNAPSHOT from "../data/snapshot.json";
import InventoryTable from "../components/InventoryTable.jsx";
import { RefreshCw } from "lucide-react";

// Renders instantly from precomputed snapshot; silently refreshes from live backend.
export default function Inventory() {
  const [skus,       setSkus]       = useState(SNAPSHOT.inventory);
  const [refreshing, setRefreshing] = useState(false);
  const [liveTs,     setLiveTs]     = useState(null);
  const navigate = useNavigate();

  // Background refresh — show live data when backend is available
  useEffect(() => {
    api.getAllSkus()
      .then((data) => { setSkus(data); setLiveTs(new Date()); })
      .catch(() => {});
  }, []);

  const refresh = () => {
    setRefreshing(true);
    clearCache();
    api.getAllSkus()
      .then((data) => { setSkus(data); setLiveTs(new Date()); })
      .catch(() => {})
      .finally(() => setRefreshing(false));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-mono font-semibold">Inventory</h1>
          <p className="text-xs text-zinc-600 mt-0.5">
            {skus.length} SKUs tracked
            {liveTs
              ? ` · Live ${liveTs.toLocaleTimeString()}`
              : ` · Snapshot ${new Date(SNAPSHOT.generatedAt).toLocaleDateString()}`}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-[#b5f23d] border border-zinc-700 hover:border-[#b5f23d]/50 px-3 py-1.5 rounded transition-all disabled:opacity-50"
        >
          <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <InventoryTable
        data={skus}
        onRowClick={(row) => navigate(`/forecast?sku=${row.sku_id}`)}
      />
    </div>
  );
}

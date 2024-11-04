import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client.js";
export function useInventorySummary() {
  const [data,setData]       = useState(null);
  const [loading,setLoading] = useState(true);
  const [error,setError]     = useState(null);
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try { setData(await api.getInventorySummary()); setError(null); }
    catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { fetch_(); }, [fetch_]);
  return { data, loading, error, refetch: fetch_ };
}
export function useAllSkus() {
  const [skus,setSkus]       = useState([]);
  const [loading,setLoading] = useState(true);
  const [error,setError]     = useState(null);
  useEffect(() => {
    api.getAllSkus().then(setSkus).catch(e=>setError(e.message)).finally(()=>setLoading(false));
  }, []);
  return { skus, loading, error };
}
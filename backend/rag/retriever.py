"""
RAG retriever: semantic search over supplier documents.

Caching:
  _supplier_context_cache — keyed by supplier_id; queries are formulaic
  (same supplier_id always produces the same query string), so we cache
  per-supplier and skip re-embedding on repeat lookups.

warm_supplier_cache() is called at startup to pre-populate all supplier
contexts so the first user request doesn't hit a cold SentenceTransformer.
"""

import logging
from typing import Optional
from backend.rag.vectorstore import get_collection, get_embedder

logger = logging.getLogger(__name__)

_supplier_context_cache: dict[str, str] = {}   # supplier_id → context text


def retrieve_supplier_context(
    query: str,
    supplier_id: Optional[str] = None,
    n_results: int = 3,
) -> str:
    if supplier_id and supplier_id in _supplier_context_cache:
        return _supplier_context_cache[supplier_id]

    try:
        embedder   = get_embedder()
        collection = get_collection()

        query_emb = embedder.encode([query]).tolist()
        where     = {"supplier_id": supplier_id} if supplier_id else None

        results = collection.query(
            query_embeddings=query_emb,
            n_results=n_results,
            where=where,
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            text = "No relevant supplier information found."
        else:
            text = "\n---\n".join(docs)

        if supplier_id:
            _supplier_context_cache[supplier_id] = text
        return text

    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return f"Supplier context unavailable: {str(e)}"


def warm_supplier_cache() -> None:
    """
    Pre-populate supplier context cache for all known suppliers.
    Called once at startup so first user request is a cache hit.
    """
    try:
        collection = get_collection()
        # Extract unique supplier_ids from ChromaDB metadata
        data    = collection.get(include=["metadatas"])
        metas   = data.get("metadatas", []) or []
        sup_ids = list(set(
            m["supplier_id"] for m in metas
            if m and "supplier_id" in m and m["supplier_id"]
        ))
        for sid in sup_ids:
            retrieve_supplier_context(
                query=f"lead time MOQ reliability performance for {sid}",
                supplier_id=sid,
            )
        logger.info(f"RAG supplier cache warmed: {len(sup_ids)} suppliers")
    except Exception as e:
        logger.warning(f"warm_supplier_cache failed: {e}")

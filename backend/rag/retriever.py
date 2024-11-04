"""
RAG retriever: semantic search over supplier documents.
"""

import logging
from typing import Optional
from backend.rag.vectorstore import get_collection, get_embedder

logger = logging.getLogger(__name__)


def retrieve_supplier_context(
    query: str,
    supplier_id: Optional[str] = None,
    n_results: int = 3,
) -> str:
    """
    Retrieve top-k relevant supplier doc chunks.

    Parameters
    ----------
    query : str
        Natural language query, e.g. "lead time and MOQ for SUP_001"
    supplier_id : str, optional
        Filter to a specific supplier
    n_results : int
        Number of chunks to return

    Returns
    -------
    str
        Concatenated relevant context passages
    """
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
            return "No relevant supplier information found."

        return "\n---\n".join(docs)

    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return f"Supplier context unavailable: {str(e)}"

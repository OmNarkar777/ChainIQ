"""
Docker build step 2: pre-ingest supplier documents into ChromaDB.
sentence-transformers downloads all-MiniLM-L6-v2 from HuggingFace here.
Called by Dockerfile — do not run manually.
"""
import sys

sys.path.insert(0, ".")

try:
    from backend.rag.vectorstore import ingest_supplier_docs, collection_size

    if collection_size() == 0:
        n = ingest_supplier_docs()
        print(f"[build] RAG: ingested {n} supplier doc chunks into ChromaDB.")
    else:
        print(f"[build] RAG: ChromaDB already has {collection_size()} chunks.")
except Exception as e:
    print(f"[build] RAG ingestion skipped: {e}")

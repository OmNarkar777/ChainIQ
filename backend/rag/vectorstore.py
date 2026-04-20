"""
ChromaDB vector store setup and document ingestion.
"""

import logging
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "supplier_docs"
_client = None
_collection = None
_embedder = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def ingest_supplier_docs(docs_dir: str = "backend/data/supplier_docs") -> int:
    """Ingest all .txt supplier docs into ChromaDB."""
    doc_path = Path(docs_dir)
    if not doc_path.exists():
        logger.warning(f"Supplier docs dir not found: {doc_path}")
        return 0

    embedder   = get_embedder()
    collection = get_collection()

    docs, ids, metas = [], [], []
    for txt_file in doc_path.glob("*.txt"):
        content = txt_file.read_text()
        supplier_id = txt_file.stem.replace("supplier_", "")
        # Chunk by paragraph
        for i, para in enumerate(content.split("\n\n")):
            para = para.strip()
            if len(para) < 20:
                continue
            docs.append(para)
            ids.append(f"{supplier_id}_chunk_{i}")
            metas.append({"supplier_id": supplier_id, "source": txt_file.name})

    if docs:
        embeddings = embedder.encode(docs).tolist()
        collection.upsert(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)
        logger.info(f"Ingested {len(docs)} chunks from {docs_dir}")

    return len(docs)


def collection_size() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0

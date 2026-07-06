"""Vector retriever stub (Phase 2).

This class documents the migration path to a vector database. It intentionally
raises on use unless the `rag` extra is installed and configured. It is
interface-compatible with `MarkdownRetriever`, so switching RAG_PROVIDER to
`qdrant` requires no changes in the agent code.

Migration outline (Phase 2):
  1. Chunk markdown → embeddings (OpenAI text-embedding-3-small).
  2. Upsert into Qdrant / pgvector with metadata.
  3. On `search`: embed query → ANN search → return top_k chunks.
"""
from __future__ import annotations

from priya.knowledge.base import KnowledgeRetriever, RetrievedChunk
from priya.utils.logging import get_logger

log = get_logger(__name__)


class QdrantRetriever(KnowledgeRetriever):
    def __init__(self, url: str, api_key: str, collection: str = "priya_kb") -> None:
        self.url = url
        self.api_key = api_key
        self.collection = collection
        log.info("knowledge.qdrant.init_stub", collection=collection)

    async def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:  # pragma: no cover
        raise NotImplementedError(
            "QdrantRetriever is a Phase 2 stub. Install extras `.[rag]`, implement "
            "embedding + ANN search, then set RAG_PROVIDER=qdrant."
        )

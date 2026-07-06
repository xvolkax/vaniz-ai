"""Retriever factory — selects implementation from RAG_PROVIDER."""
from __future__ import annotations

from functools import lru_cache

from priya.config import settings
from priya.knowledge.base import KnowledgeRetriever
from priya.knowledge.markdown_store import MarkdownRetriever
from priya.utils.logging import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_retriever() -> KnowledgeRetriever:
    provider = settings.rag_provider.lower()
    if provider == "markdown":
        return MarkdownRetriever()
    if provider == "qdrant":
        from priya.knowledge.vector_store import QdrantRetriever

        return QdrantRetriever(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    log.warning("knowledge.factory.unknown_provider", provider=provider)
    return MarkdownRetriever()

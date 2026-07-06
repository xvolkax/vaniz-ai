"""Retrieval layer abstraction.

`KnowledgeRetriever` is the stable interface the agent depends on. Concrete
implementations: MarkdownRetriever (Phase 1) and a QdrantRetriever stub
(Phase 2). Swapping is controlled by RAG_PROVIDER env var via the factory.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedChunk:
    """A single retrieved knowledge fragment."""

    content: str
    source: str
    score: float = 0.0
    metadata: dict | None = None


class KnowledgeRetriever(ABC):
    """Stable retrieval interface used by the agent's function tools."""

    @abstractmethod
    async def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """Return the most relevant chunks for a natural-language query."""
        raise NotImplementedError

    async def aclose(self) -> None:  # optional cleanup hook
        return None

"""Knowledge base package — retrieval abstraction with markdown default.

Company knowledge is kept OUT of the system prompt and retrieved on demand,
so migrating to a vector DB (Qdrant/pgvector) is a drop-in change.
"""
from priya.knowledge.base import KnowledgeRetriever, RetrievedChunk
from priya.knowledge.factory import get_retriever

__all__ = ["KnowledgeRetriever", "RetrievedChunk", "get_retriever"]

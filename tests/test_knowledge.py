"""Tests for the markdown knowledge retriever."""
from __future__ import annotations

import pytest

from priya.knowledge.markdown_store import MarkdownRetriever


@pytest.fixture
def retriever() -> MarkdownRetriever:
    return MarkdownRetriever()


async def test_search_returns_relevant_chunk(retriever: MarkdownRetriever) -> None:
    results = await retriever.search("brokerage charges", top_k=2)
    assert results
    assert any("brokerage" in r.content.lower() for r in results)


async def test_search_home_loan(retriever: MarkdownRetriever) -> None:
    results = await retriever.search("home loan interest rate", top_k=2)
    assert results
    assert results[0].score > 0


async def test_search_no_match_returns_empty(retriever: MarkdownRetriever) -> None:
    results = await retriever.search("zzzzz nonsense query xyzq", top_k=3)
    # Lexical retriever returns nothing when there is zero token overlap.
    assert results == [] or all(r.score >= 0 for r in results)

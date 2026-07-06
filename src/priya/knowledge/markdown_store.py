"""Markdown-backed retriever (Phase 1).

Loads all `*.md` files from the knowledge data directory, splits them into
sections by markdown headings, and performs a lightweight lexical (token
overlap + fuzzy) ranking. Zero external dependencies → lowest latency and
trivial to run locally. Interface-compatible with a future vector retriever.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from priya.knowledge.base import KnowledgeRetriever, RetrievedChunk
from priya.utils.logging import get_logger

log = get_logger(__name__)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_TOKEN_RE = re.compile(r"[a-z0-9\u0900-\u097F]+")  # includes Devanagari range


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class _Section:
    __slots__ = ("title", "content", "source", "tokens")

    def __init__(self, title: str, content: str, source: str) -> None:
        self.title = title
        self.content = content
        self.source = source
        self.tokens = _tokenize(f"{title} {content}")


class MarkdownRetriever(KnowledgeRetriever):
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir or Path(__file__).parent / "data")
        self._sections: list[_Section] = []
        self._load()

    def _load(self) -> None:
        self._sections.clear()
        if not self.data_dir.exists():
            log.warning("knowledge.markdown.missing_dir", dir=str(self.data_dir))
            return
        for md in sorted(self.data_dir.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            self._sections.extend(self._split(text, md.name))
        log.info(
            "knowledge.markdown.loaded",
            sections=len(self._sections),
            files=len(list(self.data_dir.glob("*.md"))),
        )

    @staticmethod
    def _split(text: str, source: str) -> list[_Section]:
        matches = list(_HEADING_RE.finditer(text))
        sections: list[_Section] = []
        if not matches:
            return [_Section("", text.strip(), source)] if text.strip() else []
        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if body:
                sections.append(_Section(title, body, source))
        return sections

    def _score(self, query_tokens: set[str], query: str, section: _Section) -> float:
        if not query_tokens:
            return 0.0
        overlap = len(query_tokens & section.tokens) / len(query_tokens)
        fuzzy = SequenceMatcher(None, query.lower(), section.title.lower()).ratio()
        return 0.75 * overlap + 0.25 * fuzzy

    async def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        query_tokens = _tokenize(query)
        ranked = sorted(
            (
                (self._score(query_tokens, query, s), s)
                for s in self._sections
            ),
            key=lambda t: t[0],
            reverse=True,
        )
        results = [
            RetrievedChunk(
                content=(f"{s.title}\n{s.content}" if s.title else s.content),
                source=s.source,
                score=round(score, 4),
                metadata={"title": s.title},
            )
            for score, s in ranked[:top_k]
            if score > 0.0
        ]
        return results

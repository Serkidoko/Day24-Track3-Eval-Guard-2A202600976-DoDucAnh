from __future__ import annotations

"""Small lexical search fallback for the Day 24 lab.

It intentionally avoids external services so reports and tests can run in a
fresh workspace.
"""

from dataclasses import dataclass, field
import math
import re
import unicodedata
from typing import Any


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", no_accents)


def _tokens(text: str) -> list[str]:
    return [token for token in _normalize(text).split() if len(token) > 1]


class HybridSearch:
    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []
        self._doc_tokens: list[set[str]] = []

    def index(self, chunks: list[dict[str, Any]], collection: str | None = None) -> None:
        self._docs = chunks
        self._doc_tokens = [set(_tokens(chunk.get("text", ""))) for chunk in chunks]

    def search(
        self,
        query: str,
        top_k: int = 20,
        collection: str | None = None,
    ) -> list[SearchResult]:
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return []

        scored: list[SearchResult] = []
        for chunk, doc_tokens in zip(self._docs, self._doc_tokens):
            overlap = query_tokens & doc_tokens
            if not overlap:
                continue
            coverage = len(overlap) / len(query_tokens)
            specificity = sum(1.0 / math.sqrt(max(1, len(token))) for token in overlap)
            score = coverage + specificity / 10
            scored.append(
                SearchResult(
                    text=chunk.get("text", ""),
                    score=score,
                    metadata=chunk.get("metadata", {}),
                )
            )
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


class DenseSearch(HybridSearch):
    pass

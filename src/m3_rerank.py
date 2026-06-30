from __future__ import annotations

"""Lexical reranker fallback used by setup_answers.py."""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RerankResult:
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", no_accents)


class CrossEncoderReranker:
    def rerank(self, query: str, docs: list[dict[str, Any]], top_k: int = 3) -> list[RerankResult]:
        query_terms = set(_normalize(query).split())
        reranked: list[RerankResult] = []
        for doc in docs:
            text = doc.get("text", "")
            doc_terms = set(_normalize(text).split())
            overlap = len(query_terms & doc_terms)
            base_score = float(doc.get("score", 0.0))
            reranked.append(
                RerankResult(
                    text=text,
                    score=base_score + overlap,
                    metadata=doc.get("metadata", {}),
                )
            )
        return sorted(reranked, key=lambda item: item.score, reverse=True)[:top_k]

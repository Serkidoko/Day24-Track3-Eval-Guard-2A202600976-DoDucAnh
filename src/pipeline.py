from __future__ import annotations

"""Minimal local RAG pipeline entry point."""

from src.m1_chunking import chunk_hierarchical, load_documents
from src.m2_search import HybridSearch
from src.m3_rerank import CrossEncoderReranker


class RAGPipeline:
    def __init__(self) -> None:
        self.search = HybridSearch()
        self.reranker = CrossEncoderReranker()
        self._ready = False

    def build(self) -> None:
        chunks = []
        for doc in load_documents():
            _, children = chunk_hierarchical(doc["text"], doc["metadata"])
            chunks.extend({"text": child.text, "metadata": child.metadata} for child in children)
        self.search.index(chunks)
        self._ready = True

    def answer(self, question: str) -> tuple[str, list[str]]:
        if not self._ready:
            self.build()
        docs = [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in self.search.search(question)]
        contexts = [r.text for r in self.reranker.rerank(question, docs, top_k=3)]
        return (contexts[0] if contexts else "Khong tim thay thong tin."), contexts

"""Second-stage reranking with a cross-encoder that reads the question and each passage together (lesson 17)."""

from __future__ import annotations

from langchain_community.cross_encoders import BaseCrossEncoder
from langchain_core.documents import Document


class Reranker:
    def __init__(self, cross_encoder: BaseCrossEncoder, top_n: int):
        self._cross_encoder = cross_encoder
        self.top_n = top_n

    def rerank(self, query: str, docs: list[Document]) -> list[tuple[Document, float]]:
        """Score every (query, passage) pair, best first, keeping the top n."""
        if not docs:
            return []
        scores = self._cross_encoder.score([(query, d.page_content) for d in docs])
        ranked = sorted(zip(docs, (float(s) for s in scores), strict=True), key=lambda pair: pair[1], reverse=True)
        return ranked[: self.top_n]

"""Hybrid search: dense vectors from Chroma and sparse BM25 keywords, fused with reciprocal rank fusion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from .config import RetrievalConfig
from .fusion import reciprocal_rank_fusion
from .store import ChunkStore

Filter = dict[str, Any]


@dataclass(frozen=True)
class Scored:
    doc: Document
    score: float | None


def keyword_tokens(text: str) -> list[str]:
    """Lowercased Unicode word runs. Works for any script that uses spaces; CJK runs stay whole (a known limit)."""
    return re.findall(r"\w+", text.casefold())


class HybridSearcher:
    def __init__(self, store: ChunkStore, cfg: RetrievalConfig):
        self._store = store
        self._cfg = cfg
        self._chunks = store.chunks()
        self._bm25 = (
            BM25Retriever.from_documents(self._chunks, preprocess_func=keyword_tokens) if self._chunks else None
        )

    def vector_search(self, query: str, filter: Filter | None) -> list[Scored]:
        cfg, where = self._cfg, _chroma_filter(filter)
        if not self._chunks:
            return []
        if cfg.search_type == "mmr":
            docs = self._store.vectors.max_marginal_relevance_search(
                query, k=cfg.k, fetch_k=max(cfg.fetch_k, cfg.k), lambda_mult=cfg.lambda_mult, filter=where
            )
            return [Scored(d, None) for d in docs]
        pairs = self._store.vectors.similarity_search_with_relevance_scores(query, k=cfg.k, filter=where)
        results = [Scored(d, float(s)) for d, s in pairs]
        if cfg.search_type == "threshold":
            results = [r for r in results if r.score is not None and r.score >= cfg.score_threshold]
        return results

    def keyword_search(self, query: str, filter: Filter | None) -> list[Scored]:
        if self._bm25 is None:
            return []
        scores = self._bm25.vectorizer.get_scores(keyword_tokens(query))
        ranked = sorted(
            (
                Scored(doc, float(score))
                for doc, score in zip(self._bm25.docs, scores, strict=True)
                if score > 0 and _matches(doc, filter)
            ),
            key=lambda r: r.score or 0.0,
            reverse=True,
        )
        return ranked[: self._cfg.k]

    def search(self, query: str, filter: Filter | None) -> tuple[list[Scored], dict[str, list[Scored]]]:
        """Fused results, plus each retriever's own list for the trace."""
        stages = {"vector": self.vector_search(query, filter), "keyword": self.keyword_search(query, filter)}
        fused = reciprocal_rank_fusion(
            [[r.doc for r in stages["vector"]], [r.doc for r in stages["keyword"]]],
            weights=[self._cfg.vector_weight, self._cfg.keyword_weight],
            k=self._cfg.rrf_k,
        )
        return [Scored(doc, score) for doc, score in fused], stages


def _matches(doc: Document, filter: Filter | None) -> bool:
    return not filter or all(doc.metadata.get(key) == value for key, value in filter.items())


def _chroma_filter(filter: Filter | None) -> dict[str, Any] | None:
    if not filter:
        return None
    if len(filter) == 1:
        return dict(filter)
    return {"$and": [{key: value} for key, value in filter.items()]}

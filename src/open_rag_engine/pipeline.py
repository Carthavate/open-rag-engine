"""The retrieval pipeline: fixed slots filled from configuration (ADR-0003), with a trace of every stage (driver D-08).

query expansion (optional) -> vector search + keyword search -> fusion -> rerank (optional) -> top passages
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever

from .config import RetrievalConfig
from .documents import CHUNK_ID, CHUNK_INDEX, citation_label
from .fusion import generate_queries, reciprocal_rank_fusion
from .rerank import Reranker
from .retrieval import Filter, HybridSearcher, Scored
from .store import ChunkStore

TRACE_LIMIT = 10


@dataclass(frozen=True)
class Passage:
    doc: Document
    score: float
    stage_scores: dict[str, float | None]


@dataclass(frozen=True)
class StageTrace:
    name: str
    ms: float
    results: list[tuple[str, str, float | None]] = field(default_factory=list)
    """(query, chunk label, score) for the top results of the stage."""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    queries: list[str]
    passages: list[Passage]
    trace: list[StageTrace]


def _label(doc: Document) -> str:
    return f"{citation_label(doc)} #{doc.metadata.get(CHUNK_INDEX, '?')}"


def _key(doc: Document) -> str:
    return str(doc.metadata.get(CHUNK_ID) or doc.page_content)


class RetrievalPipeline:
    def __init__(
        self,
        store: ChunkStore,
        cfg: RetrievalConfig,
        reranker: Reranker | None = None,
        llm: BaseChatModel | None = None,
        top_n: int = 5,
    ):
        if cfg.multi_query and llm is None:
            raise ValueError("Multi-query retrieval needs an LLM")
        self._store, self._cfg, self._reranker, self._llm, self._top_n = store, cfg, reranker, llm, top_n

    def run(self, query: str, filter: Filter | None = None) -> RetrievalResult:
        trace: list[StageTrace] = []
        queries = [query]
        if self._cfg.multi_query and self._llm is not None:
            start = time.perf_counter()
            queries = generate_queries(self._llm, query, self._cfg.num_queries)
            trace.append(StageTrace("query_expansion", _ms(start), detail={"queries": queries}))

        searcher = HybridSearcher(self._store, self._cfg)
        best: dict[str, dict[str, float | None]] = {}
        stage_entries: dict[str, list[tuple[str, str, float | None]]] = {"vector": [], "keyword": []}
        stage_ms = {"vector": 0.0, "keyword": 0.0}
        fused_lists: list[list[Scored]] = []
        for q in queries:
            start = time.perf_counter()
            fused, stages = searcher.search(q, filter)
            fused_lists.append(fused)
            for name, results in stages.items():
                stage_ms[name] += _ms(start) / 2
                stage_entries[name] += [(q, _label(r.doc), r.score) for r in results[:TRACE_LIMIT]]
                for r in results:
                    scores = best.setdefault(_key(r.doc), {})
                    if r.score is not None and (scores.get(name) or float("-inf")) < r.score:
                        scores[name] = r.score
        trace += [StageTrace(name, stage_ms[name], stage_entries[name]) for name in ("vector", "keyword")]

        start = time.perf_counter()
        if len(fused_lists) == 1:
            fused_pairs = [(r.doc, r.score or 0.0) for r in fused_lists[0]]
        else:
            fused_pairs = reciprocal_rank_fusion([[r.doc for r in lst] for lst in fused_lists], k=self._cfg.rrf_k)
        candidates = fused_pairs[: self._cfg.k]
        trace.append(
            StageTrace(
                "fusion",
                _ms(start),
                [("*", _label(d), s) for d, s in candidates[:TRACE_LIMIT]],
                {"queries": len(queries), "candidates": len(candidates)},
            )
        )

        if self._reranker is not None:
            start = time.perf_counter()
            final = self._reranker.rerank(query, [d for d, _ in candidates])
            trace.append(StageTrace("rerank", _ms(start), [("*", _label(d), s) for d, s in final]))
        else:
            final = candidates[: self._top_n]

        fusion_scores = {_key(d): s for d, s in candidates}
        passages = []
        for doc, score in final:
            stage_scores = {
                "vector": None,
                "keyword": None,
                **best.get(_key(doc), {}),
                "fusion": fusion_scores.get(_key(doc)),
            }
            if self._reranker is not None:
                stage_scores["rerank"] = score
            passages.append(Passage(doc, score, stage_scores))
        return RetrievalResult(query=query, queries=queries, passages=passages, trace=trace)

    def as_retriever(self, filter: Filter | None = None) -> BaseRetriever:
        """This pipeline as a LangChain retriever, so it composes with LangChain chains."""
        return PipelineRetriever(pipeline=self, filter=filter)


class PipelineRetriever(BaseRetriever):
    pipeline: Any
    filter: dict[str, Any] | None = None

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        result = self.pipeline.run(query, self.filter)
        return [
            Document(page_content=p.doc.page_content, metadata={**p.doc.metadata, "score": p.score})
            for p in result.passages
        ]


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)

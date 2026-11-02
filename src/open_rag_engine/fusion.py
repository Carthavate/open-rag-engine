"""Reciprocal rank fusion and multi-query expansion (RAG course lessons 14 to 16)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from .documents import CHUNK_ID
from .llm_text import strip_think

QUERY_PROMPT = (
    "Write {n} different search queries that ask for the same information as the question below, "
    "each phrased differently. Use the same language as the question. "
    "Return one query per line, with no numbering and nothing else.\n\nQuestion: {question}"
)


def _key(doc: Document) -> str:
    return str(doc.metadata.get(CHUNK_ID) or doc.page_content)


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[Document]], weights: Sequence[float] | None = None, k: int = 60
) -> list[tuple[Document, float]]:
    """Each list gives a document weight / (k + rank), rank starting at 1; the sums decide the order.

    The same formula as LangChain's EnsembleRetriever, but the fused scores are kept for the trace.
    """
    weights = list(weights) if weights is not None else [1.0] * len(ranked_lists)
    if len(weights) != len(ranked_lists):
        raise ValueError("Need one weight per ranked list")
    scores: dict[str, float] = {}
    docs: dict[str, Document] = {}
    for weight, ranked in zip(weights, ranked_lists, strict=True):
        for rank, doc in enumerate(ranked, start=1):
            key = _key(doc)
            docs.setdefault(key, doc)
            scores[key] = scores.get(key, 0.0) + weight / (k + rank)
    return sorted(((docs[key], score) for key, score in scores.items()), key=lambda pair: pair[1], reverse=True)


def generate_queries(llm: BaseChatModel, question: str, n: int) -> list[str]:
    """The question itself first, then up to n rephrasings written by the LLM."""
    reply = llm.invoke([HumanMessage(QUERY_PROMPT.format(n=n, question=question))])
    variations = [q for q in parse_queries(str(reply.content), limit=n + 1) if q != question][:n]
    return [question, *variations]


def parse_queries(text: str, limit: int) -> list[str]:
    """One query per line, without bullets, numbering or <think> blocks; duplicates removed."""
    text = strip_think(text)
    queries: list[str] = []
    for line in text.splitlines():
        query = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if query and query not in queries:
            queries.append(query)
    return queries[:limit]

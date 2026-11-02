"""The application service behind the CLI (and later the API): wires configuration, models and pipelines together."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from functools import cached_property
from pathlib import Path
from typing import Any, Protocol

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from .answer import Answer, generate_answer
from .chunking import make_splitter
from .config import EngineConfig
from .conversation import Turn, standalone_question
from .evaluation import EvalReport, evaluate, load_dataset
from .ingest import IndexMismatchError, IngestReport, Progress, ingest
from .pipeline import RetrievalPipeline, RetrievalResult
from .rerank import Reranker
from .retrieval import Filter
from .store import ChunkStore


class Models(Protocol):
    """The models the engine needs. Built lazily, so retrieval-only use never loads the LLM."""

    @property
    def embeddings(self) -> Embeddings: ...

    @property
    def cross_encoder(self) -> Any: ...

    @property
    def llm(self) -> BaseChatModel: ...


class Engine:
    def __init__(self, config: EngineConfig, models: Models):
        self.config = config
        self._models = models

    @classmethod
    def from_config(cls, config: EngineConfig) -> Engine:
        from .factory import LocalModels

        return cls(config, LocalModels(config))

    @cached_property
    def store(self) -> ChunkStore:
        return ChunkStore(self.config.data_dir, self.config.collection, self._models.embeddings)

    def ingest(
        self,
        paths: Iterable[Path],
        rebuild: bool = False,
        prune: bool = False,
        on_progress: Progress | None = None,
        keep: Sequence[str] = (),
    ) -> IngestReport:
        cfg = self.config
        embeddings = self._models.embeddings if cfg.chunking.strategy == "semantic" else None
        splitter = make_splitter(cfg.chunking, embeddings)
        return ingest(paths, self.store, splitter, cfg.index_fingerprint(), rebuild, prune, on_progress, keep)

    def pipeline(self, rerank: bool | None = None, top_n: int | None = None) -> RetrievalPipeline:
        """The configured pipeline; `rerank` and `top_n` override the configuration for this call only."""
        cfg = self.config
        indexed_with = self.store.manifest().index_fingerprint
        if indexed_with is not None and indexed_with != cfg.index_fingerprint():
            raise IndexMismatchError(
                "The collection was indexed with a different chunking or embedding configuration. "
                "Run `ore ingest --rebuild` with the current configuration first."
            )
        top_n = top_n or cfg.rerank.top_n
        use_reranker = cfg.rerank.enabled if rerank is None else rerank
        reranker = Reranker(self._models.cross_encoder, top_n) if use_reranker else None
        llm = self._models.llm if cfg.retrieval.multi_query else None
        return RetrievalPipeline(self.store, cfg.retrieval, reranker=reranker, llm=llm, top_n=top_n)

    def retrieve(self, query: str, filter: Filter | None = None) -> RetrievalResult:
        return self.pipeline().run(query, filter)

    def ask(
        self,
        question: str,
        history: Sequence[Turn] = (),
        filter: Filter | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> Answer:
        standalone = standalone_question(self._models.llm, history, question)
        retrieval = self.pipeline().run(standalone, filter)
        min_score = self.config.answer.min_rerank_score if self.config.rerank.enabled else None
        return generate_answer(standalone, retrieval, self._models.llm, min_score, on_token)

    def evaluate(self, dataset: Path, k: int | None = None) -> EvalReport:
        return evaluate(
            load_dataset(dataset), self.pipeline(), k or self.config.rerank.top_n, self.config.fingerprint()
        )

    def stats(self) -> dict[str, Any]:
        manifest = self.store.manifest()
        return {
            "collection": self.config.collection,
            "documents": len(manifest.documents),
            "chunks": len(self.store.chunks()),
            "index_fingerprint": manifest.index_fingerprint,
        }

"""The desktop app's service: sections with their own indexes, background indexing, and answers scoped to a
section or to a whole category."""

from __future__ import annotations

import logging
import shutil
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from langchain_core.documents import Document

from .answer import Answer, generate_answer
from .config import EngineConfig
from .conversation import Turn, standalone_question
from .documents import CHUNK_INDEX, SOURCE, citation_label
from .engine import Engine, Models
from .fusion import reciprocal_rank_fusion
from .ingest import IngestReport
from .pipeline import Passage, RetrievalResult, StageTrace
from .rerank import Reranker
from .workspace import Section, Workspace

log = logging.getLogger(__name__)

SECTION_ID = "section_id"
ScopeKind = Literal["section", "category"]


class ConflictError(RuntimeError):
    """The request clashes with work in progress, such as asking a section while it is being indexed."""


@dataclass(frozen=True)
class IndexStatus:
    state: Literal["idle", "indexing", "error"] = "idle"
    done: int = 0
    total: int = 0
    current: str | None = None
    error: str | None = None
    missing_folders: tuple[str, ...] = ()
    report: IngestReport | None = None


class Library:
    def __init__(self, config: EngineConfig, models: Models, executor: Executor | None = None):
        self.config = config
        self._models = models
        self.workspace = Workspace(Path(config.data_dir) / "workspace.json")
        # One indexing job at a time: on a laptop CPU, parallel jobs only slow each other down.
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="indexer")
        self._engines: dict[str, Engine] = {}
        self._status: dict[str, IndexStatus] = {}
        self._futures: dict[str, Future] = {}
        self._lock = threading.RLock()

    def engine(self, section_id: str) -> Engine:
        section = self.workspace.section(section_id)
        with self._lock:
            if section_id not in self._engines:
                config = EngineConfig.model_validate({**self.config.model_dump(), "collection": section.collection})
                engine = Engine(config, self._models)
                _ = engine.store  # open the store now, under the lock
                self._engines[section_id] = engine
            return self._engines[section_id]

    def status(self, section_id: str) -> IndexStatus:
        self.workspace.section(section_id)
        return self._status.get(section_id, IndexStatus())

    def stats(self, section_id: str) -> dict[str, Any]:
        return self.engine(section_id).stats()

    def documents(self, section_id: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for chunk in self.engine(section_id).store.chunks():
            source = str(chunk.metadata.get(SOURCE))
            counts[source] = counts.get(source, 0) + 1
        return [{"source": s, "name": PurePosixPath(s).name, "chunks": n} for s, n in sorted(counts.items())]

    def start_indexing(self, section_id: str) -> IndexStatus:
        self.workspace.section(section_id)
        with self._lock:
            current = self.status(section_id)
            if current.state == "indexing":
                return current
            started = IndexStatus(state="indexing", missing_folders=current.missing_folders)
            self._status[section_id] = started
            self._futures[section_id] = self._executor.submit(self._index, section_id)
            return started

    def wait_for_index(self, section_id: str, timeout: float | None = None) -> IndexStatus:
        future = self._futures.get(section_id)
        if future is not None:
            future.result(timeout)
        return self.status(section_id)

    def delete_section(self, section_id: str) -> None:
        if self.status(section_id).state == "indexing":
            raise ConflictError("Wait until this section has finished indexing")
        engine = self.engine(section_id)
        engine.store.vectors.delete_collection()
        with self._lock:
            self._engines.pop(section_id, None)
            self._status.pop(section_id, None)
        shutil.rmtree(engine.store.directory, ignore_errors=True)
        self.workspace.delete_section(section_id)

    def ask(
        self,
        kind: ScopeKind,
        scope_id: str,
        question: str,
        history: Sequence[Turn] = (),
        on_token: Callable[[str], None] | None = None,
    ) -> Answer:
        sections = self.scope_sections(kind, scope_id)
        if kind == "section":
            return self.engine(scope_id).ask(question, history, on_token=on_token)
        llm = self._models.llm
        standalone = standalone_question(llm, history, question)
        retrieval = self._retrieve_across(sections, standalone)
        min_score = self.config.answer.min_rerank_score if self.config.rerank.enabled else None
        return generate_answer(standalone, retrieval, llm, min_score, on_token)

    def scope_sections(self, kind: ScopeKind, scope_id: str) -> list[Section]:
        """The sections a question searches. Raises when the scope is unknown or a section is still indexing."""
        if kind == "section":
            sections = [self.workspace.section(scope_id)]
        else:
            self.workspace.category(scope_id)
            sections = self.workspace.sections(scope_id)
        busy = [s.name for s in sections if self.status(s.id).state == "indexing"]
        if busy:
            raise ConflictError(f"Still indexing: {', '.join(busy)}. Ask again when it has finished.")
        return sections

    def _index(self, section_id: str) -> None:
        section = self.workspace.section(section_id)
        present = [Path(f) for f in section.folders if Path(f).is_dir()]
        missing = tuple(f for f in section.folders if not Path(f).is_dir())

        def progress(done: int, total: int, source: str) -> None:
            self._set(section_id, IndexStatus("indexing", done, total, source, None, missing))

        try:
            report = self.engine(section_id).ingest(present, prune=True, keep=missing, on_progress=progress)
        except Exception as error:  # surfaced to the app as an error state rather than lost in a thread
            log.exception("Indexing section %s failed", section_id)
            self._set(section_id, IndexStatus(state="error", error=str(error), missing_folders=missing))
            return
        files = len(report.added) + len(report.updated) + len(report.unchanged) + len(report.failed)
        self._set(section_id, IndexStatus("idle", files, files, None, None, missing, report))

    def _set(self, section_id: str, status: IndexStatus) -> None:
        with self._lock:
            self._status[section_id] = status

    def _retrieve_across(self, sections: list[Section], query: str) -> RetrievalResult:
        """Search each section, fuse their lists with RRF, then rerank the fused candidates once."""
        cfg = self.config
        lists: list[list[Document]] = []
        trace: list[StageTrace] = []
        for section in sections:
            result = self.engine(section.id).pipeline(rerank=False, top_n=cfg.retrieval.k).run(query)
            docs = [_tagged(p.doc, section.id) for p in result.passages]
            lists.append(docs)
            trace.append(
                StageTrace(
                    f"section {section.name}",
                    sum(t.ms for t in result.trace),
                    [("*", _label(d), p.score) for d, p in zip(docs, result.passages, strict=True)][:10],
                )
            )
        fused = reciprocal_rank_fusion(lists, k=cfg.retrieval.rrf_k)[: cfg.retrieval.k]
        trace.append(StageTrace("fusion", 0.0, [("*", _label(d), s) for d, s in fused[:10]]))
        fusion_scores = {id(d): s for d, s in fused}
        if cfg.rerank.enabled:
            ranked = Reranker(self._models.cross_encoder, cfg.rerank.top_n).rerank(query, [d for d, _ in fused])
            trace.append(StageTrace("rerank", 0.0, [("*", _label(d), s) for d, s in ranked]))
        else:
            ranked = fused[: cfg.rerank.top_n]
        passages = [
            Passage(d, s, {"fusion": fusion_scores.get(id(d)), **({"rerank": s} if cfg.rerank.enabled else {})})
            for d, s in ranked
        ]
        return RetrievalResult(query=query, queries=[query], passages=passages, trace=trace)


def _tagged(doc: Document, section_id: str) -> Document:
    return Document(page_content=doc.page_content, metadata={**doc.metadata, SECTION_ID: section_id})


def _label(doc: Document) -> str:
    return f"{citation_label(doc)} #{doc.metadata.get(CHUNK_INDEX, '?')}"

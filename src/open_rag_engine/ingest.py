"""Ingestion: find files, skip unchanged ones, chunk and index the rest with provenance. Idempotent per content hash."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from langchain_core.documents import Document

from .documents import CHUNK_ID, CHUNK_INDEX, DOC_ID, chunk_id, content_hash
from .loaders import discover, load
from .store import ChunkStore

log = logging.getLogger(__name__)


class Splitter(Protocol):
    def split_documents(self, documents: Iterable[Document]) -> list[Document]: ...


class IndexMismatchError(RuntimeError):
    """The collection was indexed with a different chunking or embedding configuration."""


@dataclass(frozen=True)
class IngestReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    chunks_added: int = 0


def ingest(
    paths: Iterable[Path], store: ChunkStore, splitter: Splitter, index_fingerprint: str, rebuild: bool = False
) -> IngestReport:
    files = discover(paths)
    stored = store.manifest().index_fingerprint
    if rebuild:
        store.reset()
    elif stored is not None and stored != index_fingerprint:
        raise IndexMismatchError(
            "This collection was indexed with a different chunking or embedding configuration. "
            "Re-ingest with --rebuild to re-index everything."
        )

    added: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    failed: list[tuple[str, str]] = []
    chunks_added = 0
    for path in files:
        source = path.as_posix()
        doc_id = content_hash(path.read_bytes())
        previous = store.manifest().documents.get(source)
        if previous == doc_id:
            unchanged.append(source)
            continue
        try:
            chunks = _chunk(load(path), splitter, doc_id, index_fingerprint)
        except Exception as error:  # one unreadable file must not stop the batch
            log.warning("Could not ingest %s: %s", source, error)
            failed.append((source, str(error)))
            continue
        if previous is not None:
            store.remove(source)
        store.add(source, doc_id, chunks, index_fingerprint)
        (updated if previous is not None else added).append(source)
        chunks_added += len(chunks)
    return IngestReport(added, updated, unchanged, failed, chunks_added)


def _chunk(documents: list[Document], splitter: Splitter, doc_id: str, index_fingerprint: str) -> list[Document]:
    chunks = splitter.split_documents(documents)
    return [
        Document(
            page_content=c.page_content,
            metadata={
                **c.metadata,
                DOC_ID: doc_id,
                CHUNK_INDEX: i,
                CHUNK_ID: chunk_id(doc_id, index_fingerprint, i, c.page_content),
            },
        )
        for i, c in enumerate(chunks)
    ]

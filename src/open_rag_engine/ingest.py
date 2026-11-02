"""Ingestion: find files, skip unchanged ones, chunk and index the rest with provenance. Idempotent per content hash."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
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
    removed: list[str] = field(default_factory=list)


Progress = Callable[[int, int, str], None]
"""Called after each file with (files done, files in total, source path)."""


def ingest(
    paths: Iterable[Path],
    store: ChunkStore,
    splitter: Splitter,
    index_fingerprint: str,
    rebuild: bool = False,
    prune: bool = False,
    on_progress: Progress | None = None,
    keep: Sequence[str] = (),
) -> IngestReport:
    """Index the files under `paths`.

    With `prune`, documents that are no longer under `paths` leave the index, except those under a folder in
    `keep` (for example a USB drive that is unplugged right now).
    """
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
    outcomes: dict[str, list[str]] = {"added": added, "updated": updated, "unchanged": unchanged}
    for done, path in enumerate(files, start=1):
        source = path.as_posix()
        outcome, count, error = _ingest_file(path, source, store, splitter, index_fingerprint)
        if error is not None:
            failed.append((source, error))
        else:
            outcomes[outcome].append(source)
        chunks_added += count
        if on_progress:
            on_progress(done, len(files), source)

    removed: list[str] = []
    if prune:
        present = {path.as_posix() for path in files}
        kept = tuple(folder.rstrip("/") + "/" for folder in keep)
        for source in store.manifest().documents:
            if source not in present and not source.startswith(kept):
                store.remove(source)
                removed.append(source)
    return IngestReport(added, updated, unchanged, failed, chunks_added, removed)


def _ingest_file(
    path: Path, source: str, store: ChunkStore, splitter: Splitter, index_fingerprint: str
) -> tuple[str, int, str | None]:
    """Index one file unless it is unchanged: (outcome, chunks added, error message or None)."""
    doc_id = content_hash(path.read_bytes())
    previous = store.manifest().documents.get(source)
    if previous == doc_id:
        return "unchanged", 0, None
    try:
        chunks = _chunk(load(path), splitter, doc_id, index_fingerprint)
    except Exception as error:  # one unreadable file must not stop the batch
        log.warning("Could not ingest %s: %s", source, error)
        return "failed", 0, str(error)
    if previous is not None:
        store.remove(source)
    store.add(source, doc_id, chunks, index_fingerprint)
    return ("updated" if previous is not None else "added"), len(chunks), None


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

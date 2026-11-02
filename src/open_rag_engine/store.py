"""A collection's storage: a Chroma vector index, a JSONL copy of the chunks for BM25, and a manifest of documents."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .documents import CHUNK_ID, DOC_ID


@dataclass(frozen=True)
class Manifest:
    index_fingerprint: str | None
    documents: dict[str, str]
    """Source path to the document version (content hash) that is indexed."""


class ChunkStore:
    def __init__(self, data_dir: Path, collection: str, embeddings: Embeddings):
        self.directory = Path(data_dir) / collection
        self.directory.mkdir(parents=True, exist_ok=True)
        self._collection = collection
        self._embeddings = embeddings
        self._chunks_path = self.directory / "chunks.jsonl"
        self._manifest_path = self.directory / "manifest.json"
        self.vectors = self._open_vectors()

    def _open_vectors(self) -> Chroma:
        return Chroma(
            collection_name=self._collection,
            embedding_function=self._embeddings,
            persist_directory=str(self.directory / "chroma"),
            client_settings=Settings(anonymized_telemetry=False),
            collection_metadata={"hnsw:space": "cosine"},
        )

    def manifest(self) -> Manifest:
        if not self._manifest_path.exists():
            return Manifest(None, {})
        data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        return Manifest(data["index_fingerprint"], dict(data["documents"]))

    def chunks(self) -> list[Document]:
        if not self._chunks_path.exists():
            return []
        with self._chunks_path.open(encoding="utf-8") as handle:
            return [Document(**json.loads(line)) for line in handle if line.strip()]

    def add(self, source: str, doc_id: str, chunks: list[Document], index_fingerprint: str) -> None:
        if chunks:
            self.vectors.add_documents([_for_chroma(c) for c in chunks], ids=[c.metadata[CHUNK_ID] for c in chunks])
        self._write_chunks([*self.chunks(), *chunks])
        manifest = self.manifest()
        self._write_manifest(Manifest(index_fingerprint, {**manifest.documents, source: doc_id}))

    def remove(self, source: str) -> None:
        manifest = self.manifest()
        doc_id = manifest.documents.get(source)
        if doc_id is None:
            return
        kept, dropped = [], []
        for chunk in self.chunks():
            (dropped if chunk.metadata.get(DOC_ID) == doc_id else kept).append(chunk)
        if dropped:
            self.vectors.delete(ids=[c.metadata[CHUNK_ID] for c in dropped])
        self._write_chunks(kept)
        self._write_manifest(
            Manifest(manifest.index_fingerprint, {k: v for k, v in manifest.documents.items() if k != source})
        )

    def reset(self) -> None:
        """Drop everything in this collection, for a rebuild with a new index configuration."""
        self.vectors.delete_collection()
        for path in (self._chunks_path, self._manifest_path):
            path.unlink(missing_ok=True)
        shutil.rmtree(self.directory / "chroma", ignore_errors=True)
        self.vectors = self._open_vectors()

    def _write_chunks(self, chunks: list[Document]) -> None:
        lines = (
            json.dumps({"page_content": c.page_content, "metadata": c.metadata}, ensure_ascii=False) for c in chunks
        )
        _atomic_write(self._chunks_path, "".join(f"{line}\n" for line in lines))

    def _write_manifest(self, manifest: Manifest) -> None:
        data = {"index_fingerprint": manifest.index_fingerprint, "documents": manifest.documents}
        _atomic_write(self._manifest_path, json.dumps(data, indent=1, ensure_ascii=False))


def _for_chroma(chunk: Document) -> Document:
    """Chroma metadata accepts only scalars and no None values."""
    meta: dict[str, Any] = {
        k: v if isinstance(v, str | int | float | bool) else str(v) for k, v in chunk.metadata.items() if v is not None
    }
    return Document(page_content=chunk.page_content, metadata=meta)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

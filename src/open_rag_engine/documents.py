"""Document identity and chunk metadata. Every chunk carries provenance back to its source (principle 4)."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from langchain_core.documents import Document

SOURCE = "source"
DOC_ID = "doc_id"
CHUNK_ID = "chunk_id"
CHUNK_INDEX = "chunk_index"
PAGE = "page"


def content_hash(data: bytes) -> str:
    """The document version: a hash of its bytes, so re-ingesting identical content changes nothing."""
    return hashlib.sha256(data).hexdigest()


def chunk_id(doc_id: str, index_fingerprint: str, index: int, text: str) -> str:
    """A chunk's ID comes from its document version, the index configuration, its position and its text."""
    return hashlib.sha256(f"{doc_id}|{index_fingerprint}|{index}|{text}".encode()).hexdigest()[:32]


def citation_label(doc: Document) -> str:
    """How a chunk is cited to a reader: the file name, plus the page when there is one."""
    name = PurePosixPath(str(doc.metadata.get(SOURCE, "unknown"))).name
    page = doc.metadata.get(PAGE)
    return f"{name}, p. {page}" if page else name

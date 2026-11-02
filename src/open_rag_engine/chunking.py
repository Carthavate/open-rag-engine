"""Chunking strategies from the course: recursive character, Markdown-aware and semantic chunking."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from .config import ChunkingConfig

# Ends of sentences in Latin scripts (followed by a space) and in CJK scripts (no space after them).
SENTENCE_SPLIT = r"(?<=[.?!])\s+|(?<=[。！？])"


def make_splitter(
    cfg: ChunkingConfig, embeddings: Embeddings | None
) -> RecursiveCharacterTextSplitter | SemanticChunker:
    """Build the configured splitter. Every strategy records each chunk's start offset in its source."""
    if cfg.strategy == "semantic":
        if embeddings is None:
            raise ValueError("Semantic chunking needs embeddings")
        return SemanticChunker(
            embeddings,
            add_start_index=True,
            breakpoint_threshold_type=cfg.semantic_threshold_type,
            breakpoint_threshold_amount=cfg.semantic_threshold_amount,
            sentence_split_regex=SENTENCE_SPLIT,
        )
    if cfg.strategy == "markdown":
        return RecursiveCharacterTextSplitter.from_language(
            Language.MARKDOWN, chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap, add_start_index=True
        )
    return RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap, add_start_index=True
    )

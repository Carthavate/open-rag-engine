import pytest
from langchain_core.documents import Document

from open_rag_engine.chunking import make_splitter
from open_rag_engine.config import ChunkingConfig

from .conftest import HashEmbeddings

LONG = " ".join(f"Sentence number {i} talks about the pump." for i in range(60))


def test_recursive_splits_with_overlap_and_offsets():
    splitter = make_splitter(ChunkingConfig(chunk_size=200, chunk_overlap=40), embeddings=None)
    chunks = splitter.split_documents([Document(page_content=LONG, metadata={"source": "s"})])
    assert len(chunks) > 5
    assert all(len(c.page_content) <= 200 for c in chunks)
    assert all("start_index" in c.metadata and c.metadata["source"] == "s" for c in chunks)
    assert LONG[chunks[1].metadata["start_index"] :].startswith(chunks[1].page_content)


def test_markdown_strategy_prefers_heading_boundaries():
    text = (
        "# Install\n" + "Put the pump on a level surface. " * 6 + "\n\n# Winter\n" + "Drain the pump before frost. " * 6
    )
    splitter = make_splitter(ChunkingConfig(strategy="markdown", chunk_size=220, chunk_overlap=0), embeddings=None)
    chunks = splitter.split_documents([Document(page_content=text)])
    assert any(c.page_content.startswith("# Winter") for c in chunks)


def test_semantic_needs_embeddings():
    with pytest.raises(ValueError, match="embeddings"):
        make_splitter(ChunkingConfig(strategy="semantic"), embeddings=None)


def test_semantic_splits_at_topic_changes_including_cjk_sentences():
    text = (
        "The pump needs 230 V. The pump draws 1.2 kW. "
        "Bananas are yellow fruit. Bananas grow in bunches. ポンプは水を送る。ポンプは静かだ。"
    )
    splitter = make_splitter(
        ChunkingConfig(strategy="semantic", semantic_threshold_amount=50), embeddings=HashEmbeddings()
    )
    chunks = splitter.split_documents([Document(page_content=text)])
    assert len(chunks) >= 2
    assert "".join(c.page_content for c in chunks).replace(" ", "") == text.replace(" ", "")

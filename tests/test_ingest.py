from pathlib import Path

import pytest

from open_rag_engine.chunking import make_splitter
from open_rag_engine.ingest import IndexMismatchError, ingest
from open_rag_engine.store import ChunkStore

from .conftest import HashEmbeddings


def _store(config) -> ChunkStore:
    return ChunkStore(config.data_dir, config.collection, HashEmbeddings())


def _ingest(paths, config, store=None, rebuild=False):
    store = store or _store(config)
    splitter = make_splitter(config.chunking, embeddings=None)
    return store, ingest(paths, store, splitter, config.index_fingerprint(), rebuild=rebuild)


def test_ingest_stores_chunks_with_provenance(corpus: Path, config):
    store, report = _ingest([corpus], config)
    assert len(report.added) == 5 and report.chunks_added == 5 and not report.failed
    chunks = store.chunks()
    assert len(chunks) == 5
    meta = chunks[0].metadata
    assert {"source", "doc_id", "chunk_id", "chunk_index", "start_index"} <= meta.keys()
    assert store.vectors.get()["ids"] and len(store.vectors.get()["ids"]) == 5


def test_reingesting_unchanged_files_is_a_no_op(corpus: Path, config):
    store, _ = _ingest([corpus], config)
    _, report = _ingest([corpus], config, store)
    assert len(report.unchanged) == 5 and not report.added and report.chunks_added == 0
    assert len(store.chunks()) == 5


def test_changed_file_replaces_its_old_chunks(corpus: Path, config):
    store, _ = _ingest([corpus], config)
    (corpus / "power.md").write_text("The pump now runs on 110 V.", encoding="utf-8")
    _, report = _ingest([corpus], config, store)
    assert [Path(s).name for s in report.updated] == ["power.md"]
    texts = [c.page_content for c in store.chunks()]
    assert "The pump now runs on 110 V." in texts and not any("230 V" in t for t in texts)
    assert len(store.vectors.get()["ids"]) == 5


def test_a_broken_file_is_reported_not_fatal(corpus: Path, config):
    (corpus / "broken.pdf").write_bytes(b"not a pdf")
    _, report = _ingest([corpus], config)
    assert len(report.added) == 5
    assert [Path(s).name for s, _ in report.failed] == ["broken.pdf"]


def test_a_different_index_configuration_needs_a_rebuild(corpus: Path, config):
    store, _ = _ingest([corpus], config)
    changed = config.updated("chunking", chunk_size=300)
    with pytest.raises(IndexMismatchError):
        _ingest([corpus], changed, store)
    _, report = _ingest([corpus], changed, store, rebuild=True)
    assert len(report.added) == 5 and len(store.chunks()) == 5


def test_prune_removes_documents_whose_files_are_gone(corpus: Path, config):
    store, _ = _ingest([corpus], config)
    (corpus / "winter.md").unlink()
    splitter = make_splitter(config.chunking, embeddings=None)
    report = ingest([corpus], store, splitter, config.index_fingerprint(), prune=True)
    assert [Path(s).name for s in report.removed] == ["winter.md"]
    assert len(store.chunks()) == 4 and len(store.vectors.get()["ids"]) == 4


def test_prune_with_no_paths_empties_the_collection(corpus: Path, config):
    store, _ = _ingest([corpus], config)
    report = ingest([], store, make_splitter(config.chunking, None), config.index_fingerprint(), prune=True)
    assert len(report.removed) == 5 and store.chunks() == []


def test_progress_is_reported_per_file(corpus: Path, config):
    seen: list[tuple[int, int]] = []
    store = _store(config)
    ingest(
        [corpus],
        store,
        make_splitter(config.chunking, None),
        config.index_fingerprint(),
        on_progress=lambda done, total, source: seen.append((done, total)),
    )
    assert seen == [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)]

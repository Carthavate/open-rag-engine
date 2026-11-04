from pathlib import Path

import pytest

from open_rag_engine.chunking import make_splitter
from open_rag_engine.ingest import IndexMismatchError, IngestReport, ingest
from open_rag_engine.pipeline import RetrievalPipeline
from open_rag_engine.store import ChunkStore

from .conftest import HashEmbeddings

VALVE = "The pressure relief valve opens at six bar."


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


def _update(folder: Path, config, store: ChunkStore) -> IngestReport:
    """What the app's Update button does: index the folder and drop files that are gone."""
    return ingest([folder], store, make_splitter(config.chunking, None), config.index_fingerprint(), prune=True)


def _names(sources) -> set[str]:
    return {Path(str(source)).name for source in sources}


def _vector_files(store: ChunkStore) -> set[str]:
    return _names(meta["source"] for meta in store.vectors.get()["metadatas"])


@pytest.fixture
def twins(corpus: Path) -> Path:
    """Two byte-identical files, as when a document is saved twice. They share chunk IDs, so Chroma holds one copy."""
    (corpus / "valve.md").write_text(VALVE, encoding="utf-8")
    (corpus / "valve copy.md").write_text(VALVE, encoding="utf-8")
    return corpus


@pytest.mark.parametrize(("deleted", "kept"), [("valve.md", "valve copy.md"), ("valve copy.md", "valve.md")])
def test_deleting_one_of_two_identical_files_keeps_the_other(twins: Path, config, deleted: str, kept: str):
    store, _ = _ingest([twins], config)
    (twins / deleted).unlink()
    report = _update(twins, config, store)
    assert _names(report.removed) == {deleted}
    assert kept in _names(store.manifest().documents) and deleted not in _names(store.manifest().documents)
    assert kept in _names(c.metadata["source"] for c in store.chunks())
    assert deleted not in _names(c.metadata["source"] for c in store.chunks())
    # A citation must never name the deleted file, whichever copy Chroma's shared vector was labelled with.
    assert kept in _vector_files(store) and deleted not in _vector_files(store)


def test_update_keeps_working_after_removing_a_copy(twins: Path, config):
    store, _ = _ingest([twins], config)
    (twins / "valve copy.md").unlink()
    _update(twins, config, store)
    report = _update(twins, config, store)
    assert len(report.unchanged) == 6 and not report.added and not report.removed


def test_changing_one_of_two_identical_files_keeps_the_other(twins: Path, config):
    store, _ = _ingest([twins], config)
    (twins / "valve copy.md").write_text("The relief valve now opens at eight bar.", encoding="utf-8")
    report = _update(twins, config, store)
    assert _names(report.updated) == {"valve copy.md"}
    vectors = store.vectors.get()
    files_by_text = dict(zip(vectors["documents"], vectors["metadatas"], strict=True))
    assert _names([files_by_text[VALVE]["source"]]) == {"valve.md"}
    assert "The relief valve now opens at eight bar." in files_by_text


def test_deleting_both_identical_files_removes_their_vector(twins: Path, config):
    store, _ = _ingest([twins], config)
    (twins / "valve.md").unlink()
    (twins / "valve copy.md").unlink()
    _update(twins, config, store)
    assert len(store.chunks()) == 5 and len(store.vectors.get()["ids"]) == 5
    assert VALVE not in store.vectors.get()["documents"]


def test_identical_files_take_one_place_in_search_results(twins: Path, config):
    store, _ = _ingest([twins], config)
    result = RetrievalPipeline(store, config.retrieval, top_n=5).run("pressure relief valve")
    assert [p.doc.page_content for p in result.passages].count(VALVE) == 1

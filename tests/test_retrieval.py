from pathlib import Path

import pytest

from open_rag_engine.chunking import make_splitter
from open_rag_engine.ingest import ingest
from open_rag_engine.retrieval import HybridSearcher, keyword_tokens
from open_rag_engine.store import ChunkStore

from .conftest import HashEmbeddings


@pytest.fixture
def store(corpus: Path, config) -> ChunkStore:
    store = ChunkStore(config.data_dir, config.collection, HashEmbeddings())
    ingest([corpus], store, make_splitter(config.chunking, None), config.index_fingerprint())
    return store


def names(results) -> list[str]:
    return [Path(r.doc.metadata["source"]).name for r in results]


def test_keyword_tokens_are_unicode_aware():
    assert keyword_tokens("Größe: E1042, Pompe à eau!") == ["grösse", "e1042", "pompe", "à", "eau"]


def test_keyword_search_finds_exact_codes(store, config):
    results = HybridSearcher(store, config.retrieval).keyword_search("error E1042", None)
    assert names(results)[0] == "e1042.md"
    assert all(r.score > 0 for r in results)


def test_vector_search_scores_are_relevances(store, config):
    results = HybridSearcher(store, config.retrieval).vector_search("pump warranty two years", None)
    assert names(results)[0] == "warranty.md"
    assert all(0 <= r.score <= 1 for r in results)
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)


def test_threshold_drops_weak_matches(store, config):
    searcher = HybridSearcher(
        store, config.retrieval.model_copy(update={"search_type": "threshold", "score_threshold": 0.5})
    )
    results = searcher.vector_search("pump warranty two years", None)
    assert names(results) == ["warranty.md"]


def test_mmr_returns_k_results(store, config):
    searcher = HybridSearcher(store, config.retrieval.model_copy(update={"search_type": "mmr", "k": 3, "fetch_k": 5}))
    assert len(searcher.vector_search("pump", None)) == 3


def test_filters_apply_to_both_retrievers(store, config):
    source = next(c.metadata["source"] for c in store.chunks() if c.metadata["source"].endswith("winter.md"))
    searcher = HybridSearcher(store, config.retrieval)
    assert set(names(searcher.vector_search("pump", {"source": source}))) == {"winter.md"}
    assert set(names(searcher.keyword_search("pump", {"source": source}))) == {"winter.md"}


def test_hybrid_fuses_both_lists(store, config):
    fused, stages = HybridSearcher(store, config.retrieval).search("error E1042 pump sensor", None)
    assert names(fused)[0] == "e1042.md"
    assert set(stages) == {"vector", "keyword"}

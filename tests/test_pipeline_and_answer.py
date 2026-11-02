from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from open_rag_engine.answer import ABSTAIN, format_context, generate_answer, parse_citations
from open_rag_engine.chunking import make_splitter
from open_rag_engine.conversation import standalone_question
from open_rag_engine.ingest import ingest
from open_rag_engine.pipeline import Passage, RetrievalPipeline, RetrievalResult
from open_rag_engine.rerank import Reranker
from open_rag_engine.store import ChunkStore

from .conftest import HashEmbeddings, OverlapCrossEncoder


@pytest.fixture
def store(corpus: Path, config) -> ChunkStore:
    store = ChunkStore(config.data_dir, config.collection, HashEmbeddings())
    ingest([corpus], store, make_splitter(config.chunking, None), config.index_fingerprint())
    return store


def pipeline(store, config, llm=None, rerank=True) -> RetrievalPipeline:
    reranker = Reranker(OverlapCrossEncoder(), config.rerank.top_n) if rerank else None
    return RetrievalPipeline(store, config.retrieval, reranker=reranker, llm=llm)


def test_pipeline_reranks_and_traces_every_stage(store, config):
    result = pipeline(store, config).run("How much power does the pump draw at full speed?")
    assert Path(result.passages[0].doc.metadata["source"]).name == "power.md"
    assert len(result.passages) <= config.rerank.top_n
    assert [s.name for s in result.trace] == ["vector", "keyword", "fusion", "rerank"]
    assert {"vector", "keyword", "fusion", "rerank"} <= result.passages[0].stage_scores.keys()


def test_pipeline_without_reranker_keeps_fused_order(store, config):
    result = pipeline(store, config, rerank=False).run("pump frost winter")
    assert [s.name for s in result.trace] == ["vector", "keyword", "fusion"]
    assert len(result.passages) <= config.rerank.top_n


def test_multi_query_expands_and_fuses(store, config):
    llm = FakeListChatModel(responses=["1. How many kW does the pump draw?\n2. Pump draws at full speed"])
    cfg = config.retrieval.model_copy(update={"multi_query": True, "num_queries": 2})
    result = RetrievalPipeline(store, cfg, reranker=None, llm=llm).run("power?")
    assert result.queries == ["power?", "How many kW does the pump draw?", "Pump draws at full speed"]
    assert result.trace[0].name == "query_expansion"
    assert Path(result.passages[0].doc.metadata["source"]).name == "power.md"


def test_multi_query_needs_an_llm(store, config):
    with pytest.raises(ValueError):
        RetrievalPipeline(store, config.retrieval.model_copy(update={"multi_query": True}), reranker=None, llm=None)


def test_as_retriever_plugs_into_langchain(store, config):
    docs = pipeline(store, config).as_retriever().invoke("pump warranty")
    assert Path(docs[0].metadata["source"]).name == "warranty.md"
    assert "score" in docs[0].metadata


def _result(*texts: str) -> RetrievalResult:
    passages = [
        Passage(Document(page_content=t, metadata={"source": f"/d/{i}.md", "chunk_id": str(i)}), 0.9, {})
        for i, t in enumerate(texts)
    ]
    return RetrievalResult(query="q", queries=["q"], passages=passages, trace=[])


def test_parse_citations_handles_groups_and_repeats():
    assert parse_citations("Yes [1]. Also [2, 3] and [1][4].") == [1, 2, 3, 4]


def test_format_context_numbers_sources():
    assert format_context(_result("alpha", "beta").passages) == "[1] (0.md)\nalpha\n\n[2] (1.md)\nbeta"


def test_answer_with_valid_citations_is_grounded():
    llm = FakeListChatModel(responses=["<think>hmm</think>It draws 1.2 kW [1]."])
    answer = generate_answer("power?", _result("1.2 kW"), llm)
    assert answer.text == "It draws 1.2 kW [1]."
    assert [c.number for c in answer.citations] == [1]
    assert answer.grounded and not answer.abstained and not answer.invalid_citations


def test_citation_to_a_missing_source_is_flagged():
    answer = generate_answer("power?", _result("1.2 kW"), FakeListChatModel(responses=["It draws 1.2 kW [1][7]."]))
    assert answer.invalid_citations == [7] and not answer.grounded


def test_answer_without_citations_is_not_grounded():
    answer = generate_answer("power?", _result("1.2 kW"), FakeListChatModel(responses=["It draws 1.2 kW."]))
    assert not answer.grounded


def test_abstains_without_calling_the_llm_when_nothing_was_found():
    answer = generate_answer("power?", _result(), FakeListChatModel(responses=[]))
    assert answer.abstained and answer.text == ABSTAIN


def test_abstains_below_the_minimum_rerank_score():
    answer = generate_answer("power?", _result("x"), FakeListChatModel(responses=[]), min_score=0.95)
    assert answer.abstained


def test_model_abstention_is_recognised():
    answer = generate_answer("power?", _result("x"), FakeListChatModel(responses=[ABSTAIN]))
    assert answer.abstained and not answer.grounded


def test_streaming_passes_tokens_and_still_parses():
    tokens: list[str] = []
    answer = generate_answer(
        "power?", _result("1.2 kW"), FakeListChatModel(responses=["1.2 kW [1]"]), on_token=tokens.append
    )
    assert "".join(tokens) == "1.2 kW [1]" and answer.grounded


def test_standalone_question_rewrites_follow_ups():
    llm = FakeListChatModel(responses=["How much power does the pump draw?"])
    history = [("What voltage does the pump use?", "230 V [1].")]
    assert standalone_question(llm, history, "And how much power?") == "How much power does the pump draw?"


def test_standalone_question_without_history_is_unchanged():
    assert standalone_question(FakeListChatModel(responses=[]), [], "Hi?") == "Hi?"

import pytest
from langchain_core.documents import Document

from open_rag_engine.fusion import parse_queries, reciprocal_rank_fusion


def doc(name: str) -> Document:
    return Document(page_content=name, metadata={"chunk_id": name})


def test_rrf_rewards_appearing_in_several_lists():
    fused = reciprocal_rank_fusion([[doc("a"), doc("b")], [doc("c"), doc("b")]])
    assert [d.metadata["chunk_id"] for d, _ in fused][0] == "b"


def test_rrf_matches_the_lesson_15_worked_example():
    lists = [[doc("revenue")], [doc("x"), doc("y"), doc("z"), doc("revenue")], [doc("revenue")]]
    scores = {d.metadata["chunk_id"]: s for d, s in reciprocal_rank_fusion(lists, k=60)}
    assert scores["revenue"] == pytest.approx(1 / 61 + 1 / 64 + 1 / 61)
    assert round(scores["revenue"], 3) == 0.048


def test_weights_scale_each_list():
    fused = reciprocal_rank_fusion([[doc("vec")], [doc("kw")]], weights=[0.7, 0.3])
    assert [d.metadata["chunk_id"] for d, _ in fused] == ["vec", "kw"]
    assert fused[0][1] == pytest.approx(0.7 / 61)


def test_weights_must_match_lists():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[doc("a")]], weights=[0.5, 0.5])


def test_parse_queries_cleans_numbering_and_duplicates():
    text = "1. How much power does it use?\n- What is the wattage?\n\n2) How much power does it use?\n* Voltage?"
    assert parse_queries(text, limit=5) == ["How much power does it use?", "What is the wattage?", "Voltage?"]
    assert len(parse_queries(text, limit=2)) == 2

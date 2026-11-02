import json
from pathlib import Path

import pytest
from langchain_core.documents import Document

from open_rag_engine.evaluation import EvalCase, evaluate, load_dataset
from open_rag_engine.pipeline import Passage, RetrievalResult


class StubPipeline:
    """Returns fixed rankings per question."""

    def __init__(self, rankings: dict[str, list[str]]):
        self.rankings = rankings

    def run(self, query: str, filter=None) -> RetrievalResult:
        passages = [
            Passage(Document(page_content="", metadata={"source": f"/docs/{name}"}), 1.0, {})
            for name in self.rankings[query]
        ]
        return RetrievalResult(query=query, queries=[query], passages=passages, trace=[])


def test_load_dataset(tmp_path: Path):
    path = tmp_path / "eval.jsonl"
    path.write_text(
        '{"question": "q1", "expected_sources": ["a.md"]}\n\n{"question": "q2", "expected_sources": ["b.md"]}\n',
        encoding="utf-8",
    )
    assert load_dataset(path) == [EvalCase("q1", ("a.md",)), EvalCase("q2", ("b.md",))]


@pytest.mark.parametrize("line", ['{"question": "q"}', "not json", '{"question": "", "expected_sources": ["a"]}'])
def test_bad_dataset_lines_name_the_line(tmp_path: Path, line: str):
    path = tmp_path / "eval.jsonl"
    path.write_text('{"question": "ok", "expected_sources": ["a.md"]}\n' + line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_dataset(path)


def test_metrics_hit_rate_mrr_and_recall():
    cases = [EvalCase("q1", ("a.md",)), EvalCase("q2", ("b.md", "c.md")), EvalCase("q3", ("z.md",))]
    stub = StubPipeline({"q1": ["a.md", "x.md"], "q2": ["x.md", "c.md", "c.md"], "q3": ["x.md"]})
    report = evaluate(cases, stub, k=5, config_fingerprint="abc")
    assert report.hit_rate == pytest.approx(2 / 3)
    assert report.mrr == pytest.approx((1 + 1 / 2 + 0) / 3)
    assert report.recall == pytest.approx((1 + 0.5 + 0) / 3)
    assert report.cases[1].ranked_sources == ["x.md", "c.md"]
    data = json.loads(report.to_json())
    assert data["config_fingerprint"] == "abc" and len(data["cases"]) == 3

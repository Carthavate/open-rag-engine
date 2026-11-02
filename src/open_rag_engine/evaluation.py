"""Retrieval evaluation on a labelled dataset: hit rate, MRR and recall at k, through the production pipeline (D-07)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from .documents import SOURCE
from .pipeline import RetrievalResult


class Retrieves(Protocol):
    def run(self, query: str, filter: dict | None = None) -> RetrievalResult: ...


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected_sources: tuple[str, ...]


@dataclass(frozen=True)
class CaseResult:
    question: str
    expected_sources: tuple[str, ...]
    ranked_sources: list[str]
    hit: bool
    reciprocal_rank: float
    recall: float


@dataclass(frozen=True)
class EvalReport:
    config_fingerprint: str
    k: int
    cases: list[CaseResult]
    hit_rate: float
    mrr: float
    recall: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1, ensure_ascii=False)


def load_dataset(path: Path) -> list[EvalCase]:
    """JSONL, one case per line: {"question": "...", "expected_sources": ["file.md", ...]}."""
    cases = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: line {number} is not valid JSON ({error.msg})") from error
        question, expected = data.get("question"), data.get("expected_sources")
        if not (
            isinstance(question, str)
            and question.strip()
            and isinstance(expected, list)
            and expected
            and all(isinstance(s, str) and s for s in expected)
        ):
            raise ValueError(f'{path}: line {number} needs a non-empty "question" and a list of "expected_sources"')
        cases.append(EvalCase(question, tuple(expected)))
    return cases


def _matches(source: str, expected: str) -> bool:
    expected = expected.replace("\\", "/").lstrip("/")
    return source == expected or source.endswith("/" + expected)


def evaluate(cases: Sequence[EvalCase], pipeline: Retrieves, k: int, config_fingerprint: str) -> EvalReport:
    results = []
    for case in cases:
        sources: list[str] = []
        for passage in pipeline.run(case.question).passages:
            source = str(passage.doc.metadata.get(SOURCE, ""))
            if source not in sources:
                sources.append(source)
        sources = sources[:k]
        ranks = [i for i, s in enumerate(sources, start=1) if any(_matches(s, e) for e in case.expected_sources)]
        found = [e for e in case.expected_sources if any(_matches(s, e) for s in sources)]
        results.append(
            CaseResult(
                question=case.question,
                expected_sources=case.expected_sources,
                ranked_sources=[PurePosixPath(s).name for s in sources],
                hit=bool(ranks),
                reciprocal_rank=1 / ranks[0] if ranks else 0.0,
                recall=len(found) / len(case.expected_sources),
            )
        )
    n = len(results) or 1
    return EvalReport(
        config_fingerprint=config_fingerprint,
        k=k,
        cases=results,
        hit_rate=sum(r.hit for r in results) / n,
        mrr=sum(r.reciprocal_rank for r in results) / n,
        recall=sum(r.recall for r in results) / n,
    )

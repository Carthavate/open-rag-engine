"""Answers with numbered citations. Citations are parsed and checked against the sources, never trusted (ADR-0005)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .documents import CHUNK_ID, citation_label
from .llm_text import ThinkFilter, strip_think
from .pipeline import Passage, RetrievalResult

ABSTAIN = "I don't know based on the provided documents."

SYSTEM_PROMPT = f"""You answer questions using only the numbered sources you are given.
- Support every statement with the number of its source in square brackets, like [1] or [2][3].
- Use only facts from the sources. If they don't contain the answer, reply with exactly: {ABSTAIN}
- Answer in the same language as the question. Be concise."""

_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


@dataclass(frozen=True)
class Citation:
    number: int
    label: str
    chunk_id: str


@dataclass(frozen=True)
class Answer:
    question: str
    text: str
    citations: list[Citation]
    invalid_citations: list[int]
    abstained: bool
    grounded: bool
    """True when the answer cites at least one source and every citation points to a real source."""
    retrieval: RetrievalResult


def parse_citations(text: str) -> list[int]:
    """Cited source numbers in order of first use: [1], [2, 3] and [1][4] all count."""
    numbers: list[int] = []
    for group in _CITATION.findall(text):
        for part in group.split(","):
            number = int(part)
            if number not in numbers:
                numbers.append(number)
    return numbers


def format_context(passages: list[Passage]) -> str:
    return "\n\n".join(
        f"[{i}] ({citation_label(p.doc)})\n{p.doc.page_content}" for i, p in enumerate(passages, start=1)
    )


def generate_answer(
    question: str,
    retrieval: RetrievalResult,
    llm: BaseChatModel,
    min_score: float | None = None,
    on_token: Callable[[str], None] | None = None,
) -> Answer:
    """Answer from the retrieved passages, or abstain when the evidence is missing or too weak."""
    passages = retrieval.passages
    if not passages or (min_score is not None and passages[0].score < min_score):
        if on_token:
            on_token(ABSTAIN)
        return Answer(question, ABSTAIN, [], [], abstained=True, grounded=False, retrieval=retrieval)

    messages = [
        SystemMessage(SYSTEM_PROMPT),
        HumanMessage(f"Sources:\n{format_context(passages)}\n\nQuestion: {question}"),
    ]
    if on_token is None:
        raw = str(llm.invoke(messages).content)
    else:
        parts: list[str] = []
        visible = ThinkFilter()
        for chunk in llm.stream(messages):
            token = str(chunk.content)
            parts.append(token)
            if shown := visible.feed(token):
                on_token(shown)
        raw = "".join(parts)
    text = strip_think(raw)

    cited = parse_citations(text)
    valid = [n for n in cited if 1 <= n <= len(passages)]
    invalid = [n for n in cited if n not in valid]
    citations = [
        Citation(n, citation_label(passages[n - 1].doc), str(passages[n - 1].doc.metadata.get(CHUNK_ID, "")))
        for n in valid
    ]
    abstained = ABSTAIN.lower().rstrip(".") in text.lower()
    grounded = bool(valid) and not invalid and not abstained
    return Answer(question, text, citations, invalid, abstained, grounded, retrieval)

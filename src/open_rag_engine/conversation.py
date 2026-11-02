"""Conversational RAG (lesson 7): rewrite a follow-up question into one that stands on its own before retrieving."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .llm_text import strip_think

CONTEXTUALIZE_PROMPT = (
    "Given the conversation and a follow-up question that may refer to it, rewrite the follow-up as a standalone "
    "question that can be understood without the conversation. Do not answer it. Keep its language. "
    "Return only the question."
)

Turn = tuple[str, str]
"""One exchange: (user question, assistant answer)."""


def standalone_question(llm: BaseChatModel, history: Sequence[Turn], question: str) -> str:
    if not history:
        return question
    messages: list[BaseMessage] = [SystemMessage(CONTEXTUALIZE_PROMPT)]
    for asked, answered in history:
        messages += [HumanMessage(asked), AIMessage(answered)]
    messages.append(HumanMessage(f"Follow-up question: {question}"))
    rewritten = strip_think(str(llm.invoke(messages).content))
    return rewritten or question

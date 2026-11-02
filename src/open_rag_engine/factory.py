"""The default models: free, local and CPU-friendly (drivers D-02 and D-10). Each is loaded on first use."""

from __future__ import annotations

from functools import cached_property

from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from .config import EngineConfig


class LocalModels:
    def __init__(self, config: EngineConfig):
        self._config = config

    @cached_property
    def embeddings(self) -> Embeddings:
        from langchain_huggingface import HuggingFaceEmbeddings

        cfg = self._config.embeddings
        return HuggingFaceEmbeddings(
            model_name=cfg.model,
            model_kwargs={"device": "cpu"},
            encode_kwargs=_encode_kwargs(cfg.passage_prefix),
            query_encode_kwargs=_encode_kwargs(cfg.query_prefix),
        )

    @cached_property
    def cross_encoder(self) -> HuggingFaceCrossEncoder:
        return HuggingFaceCrossEncoder(model_name=self._config.rerank.model, model_kwargs={"device": "cpu"})

    @cached_property
    def llm(self) -> BaseChatModel:
        from langchain_ollama import ChatOllama

        cfg = self._config.llm
        # Reasoning adds minutes before the first answer token on a CPU, so it is off by default (LLMConfig.think).
        return ChatOllama(
            model=cfg.model,
            base_url=cfg.base_url,
            temperature=cfg.temperature,
            num_ctx=cfg.num_ctx,
            reasoning=cfg.think,
        )


def _encode_kwargs(prefix: str) -> dict[str, object]:
    """e5-style models expect "query: " and "passage: " prefixes; vectors are normalised for cosine similarity."""
    kwargs: dict[str, object] = {"normalize_embeddings": True}
    if prefix:
        kwargs["prompt"] = prefix
    return kwargs

"""The default models: free, local and CPU-friendly (drivers D-02 and D-10). Each is loaded on first use."""

from __future__ import annotations

import os
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

        _quiet_transformers()
        cfg = self._config.embeddings
        return HuggingFaceEmbeddings(
            model_name=self._config.model_path(cfg.model),
            model_kwargs={"device": "cpu"},
            encode_kwargs=_encode_kwargs(cfg.passage_prefix),
            query_encode_kwargs=_encode_kwargs(cfg.query_prefix),
        )

    @cached_property
    def cross_encoder(self) -> HuggingFaceCrossEncoder:
        _quiet_transformers()
        model = self._config.model_path(self._config.rerank.model)
        return HuggingFaceCrossEncoder(model_name=model, model_kwargs={"device": "cpu"})

    @cached_property
    def llm(self) -> BaseChatModel:
        cfg = self._config.llm
        if cfg.provider == "openai":
            from langchain_openai import ChatOpenAI

            # A local server needs no key; a hosted one reads the user's own key from the environment (C-03).
            key = os.environ.get("ORE_LLM_API_KEY", "not-needed")
            return ChatOpenAI(model=cfg.model, base_url=cfg.base_url, api_key=key, temperature=cfg.temperature)

        from langchain_ollama import ChatOllama

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


def _quiet_transformers() -> None:
    """No "Loading weights" progress bars or advisory warnings on the console."""
    from transformers.utils import logging as transformers_logging

    transformers_logging.disable_progress_bar()
    transformers_logging.set_verbosity_error()

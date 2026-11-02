"""Shared fakes: deterministic stand-ins for the embedding model, cross-encoder and LLM, so tests need no downloads."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import pytest
from langchain_community.cross_encoders import BaseCrossEncoder
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from open_rag_engine.config import EngineConfig
from open_rag_engine.retrieval import keyword_tokens

DIM = 256


def _bucket(word: str) -> int:
    return int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM


class HashEmbeddings(Embeddings):
    """Bag-of-words vectors: texts that share words point the same way."""

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for word in keyword_tokens(text):
            vec[_bucket(word)] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class OverlapCrossEncoder(BaseCrossEncoder):
    """Scores a (query, passage) pair by the share of query words found in the passage."""

    def score(self, text_pairs: list[tuple[str, str]]) -> list[float]:
        scores = []
        for query, passage in text_pairs:
            q, p = set(keyword_tokens(query)), set(keyword_tokens(passage))
            scores.append(len(q & p) / (len(q) or 1))
        return scores


@dataclass
class FakeModels:
    embeddings: Embeddings
    cross_encoder: BaseCrossEncoder
    llm: FakeListChatModel


PUMP_MANUAL = {
    "e1042.md": "Error code E1042 means the pump pressure sensor reads out of range. Replace the sensor.",
    "e1024.md": "Error code E1024 means the pump motor is overheating. Let it cool for 30 minutes.",
    "power.md": "The pump runs on 230 V and draws up to 1.2 kW at full speed.",
    "winter.md": "Before winter, drain the pump and store it indoors to protect it from frost.",
    "warranty.md": "The pump warranty covers parts for two years from the date of purchase.",
}


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    folder = tmp_path / "docs"
    folder.mkdir()
    for name, text in PUMP_MANUAL.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder


@pytest.fixture
def config(tmp_path: Path) -> EngineConfig:
    return EngineConfig(data_dir=tmp_path / "data", collection="test-collection")


@pytest.fixture
def models() -> FakeModels:
    return FakeModels(HashEmbeddings(), OverlapCrossEncoder(), FakeListChatModel(responses=["unused"]))

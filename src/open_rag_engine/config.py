"""Engine configuration: declarative, validated when loaded, immutable afterwards (architecture principle 3)."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ChunkingConfig(_Section):
    strategy: Literal["recursive", "markdown", "semantic"] = "recursive"
    chunk_size: int = Field(800, ge=100, le=8000)
    chunk_overlap: int = Field(120, ge=0)
    semantic_threshold_type: Literal["percentile", "standard_deviation", "interquartile", "gradient"] = "percentile"
    semantic_threshold_amount: float = 95.0

    @model_validator(mode="after")
    def _overlap_below_size(self) -> Self:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


class EmbeddingConfig(_Section):
    model: str = "intfloat/multilingual-e5-small"
    query_prefix: str = "query: "
    passage_prefix: str = "passage: "


class RetrievalConfig(_Section):
    search_type: Literal["similarity", "mmr", "threshold"] = "similarity"
    k: int = Field(20, ge=1, le=200)
    fetch_k: int = Field(50, ge=1, le=1000)
    lambda_mult: float = Field(0.5, ge=0, le=1)
    score_threshold: float = Field(0.3, ge=0, le=1)
    vector_weight: float = Field(0.7, ge=0, le=1)
    keyword_weight: float = Field(0.3, ge=0, le=1)
    rrf_k: int = Field(60, ge=1)
    multi_query: bool = False
    num_queries: int = Field(3, ge=1, le=10)


class RerankConfig(_Section):
    enabled: bool = True
    model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    top_n: int = Field(5, ge=1, le=50)


class LLMConfig(_Section):
    provider: Literal["ollama", "openai"] = "ollama"
    """`openai` means any OpenAI-compatible server, such as llama.cpp's `llama-server` bundled with the desktop app."""
    model: str = "qwen3:4b-instruct-2507-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = Field(0.0, ge=0, le=2)
    num_ctx: int = Field(8192, ge=1024)
    think: bool | None = False
    """False turns reasoning off where the model allows it; None keeps the model's default; True asks for it.
    Reasoning-only models (such as Qwen3 "thinking" releases) need None or True, so their reasoning arrives
    separately instead of mixed into the answer."""


class AnswerConfig(_Section):
    min_rerank_score: float | None = None
    """Abstain without calling the LLM when the best reranked passage scores below this."""


class EngineConfig(_Section):
    data_dir: Path = Path(".ore")
    models_dir: Path | None = None
    """Bundled model folders, named like the model with "/" as "--" (intfloat--multilingual-e5-small). A model found
    there loads from it; the configured model name, and so the index fingerprint, stays the same."""
    collection: str = Field("default", pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,61}[A-Za-z0-9]$")
    chunking: ChunkingConfig = ChunkingConfig()
    embeddings: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    rerank: RerankConfig = RerankConfig()
    llm: LLMConfig = LLMConfig()
    answer: AnswerConfig = AnswerConfig()

    def updated(self, section: str, **values: Any) -> EngineConfig:
        """A validated copy with some values of one section changed."""
        current: _Section = getattr(self, section)
        new_section = type(current).model_validate({**current.model_dump(), **values})
        return self.model_copy(update={section: new_section})

    def index_fingerprint(self) -> str:
        """Identifies everything that shapes the stored index; when it changes, the index must be rebuilt."""
        return _digest(self.chunking.model_dump_json() + self.embeddings.model_dump_json())

    def fingerprint(self) -> str:
        """Identifies the whole configuration, for reproducible evaluation runs (driver D-07)."""
        return _digest(self.model_dump_json(exclude={"data_dir", "models_dir"}))

    def model_path(self, model: str) -> str:
        """Where to load a Hugging Face model from: its bundled folder when there is one, else its name."""
        if self.models_dir is not None:
            folder = self.models_dir / model.replace("/", "--")
            if folder.is_dir():
                return str(folder)
        return model


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def load_config(path: Path | None) -> EngineConfig:
    """Load a TOML configuration file; with no path, use the defaults."""
    if path is None:
        return EngineConfig()
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    # A relative models_dir is relative to the configuration file, so a bundled engine works wherever it is installed.
    if isinstance(data.get("models_dir"), str) and not Path(data["models_dir"]).is_absolute():
        data["models_dir"] = str(path.resolve().parent / data["models_dir"])
    return EngineConfig.model_validate(data)

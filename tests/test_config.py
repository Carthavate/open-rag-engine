from pathlib import Path

import pytest
from pydantic import ValidationError

from open_rag_engine.config import EngineConfig, load_config


def test_defaults_are_valid_and_local():
    cfg = EngineConfig()
    assert cfg.llm.model == "qwen3:4b-instruct-2507-q4_K_M"
    assert cfg.llm.think is False
    assert cfg.embeddings.model == "intfloat/multilingual-e5-small"
    assert cfg.rerank.enabled is True
    assert cfg.retrieval.rrf_k == 60


def test_load_from_toml(tmp_path: Path):
    path = tmp_path / "ore.toml"
    path.write_text('collection = "manuals"\n[retrieval]\nsearch_type = "mmr"\nk = 8\n', encoding="utf-8")
    cfg = load_config(path)
    assert cfg.collection == "manuals"
    assert cfg.retrieval.search_type == "mmr"
    assert cfg.retrieval.k == 8


def test_missing_explicit_file_is_an_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.toml")


def test_no_file_gives_defaults():
    assert load_config(None) == EngineConfig()


@pytest.mark.parametrize(
    "toml",
    [
        "[chunking]\nchunk_size = 200\nchunk_overlap = 200\n",
        '[retrieval]\nsearch_type = "fancy"\n',
        "[retrieval]\nunknown_option = 1\n",
        'collection = "x"\n',
    ],
)
def test_invalid_configuration_is_rejected(tmp_path: Path, toml: str):
    path = tmp_path / "ore.toml"
    path.write_text(toml, encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(path)


def test_config_is_immutable():
    cfg = EngineConfig()
    with pytest.raises(ValidationError):
        cfg.retrieval.k = 3  # type: ignore[misc]


def test_updated_returns_a_validated_copy():
    cfg = EngineConfig()
    new = cfg.updated("retrieval", search_type="mmr", k=5)
    assert new.retrieval.search_type == "mmr" and new.retrieval.k == 5
    assert cfg.retrieval.search_type == "similarity"
    with pytest.raises(ValidationError):
        cfg.updated("retrieval", k=0)


def test_index_fingerprint_tracks_only_what_changes_the_index():
    cfg = EngineConfig()
    assert cfg.index_fingerprint() == cfg.updated("retrieval", k=3).index_fingerprint()
    assert cfg.index_fingerprint() != cfg.updated("chunking", chunk_size=400).index_fingerprint()
    assert cfg.fingerprint() != cfg.updated("retrieval", k=3).fingerprint()

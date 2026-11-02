from pathlib import Path

from open_rag_engine.offline import available_offline, go_offline_if_possible, quiet_and_private


def cached(cache: Path, repo: str) -> None:
    snapshot = cache / f"models--{repo.replace('/', '--')}" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text("{}", encoding="utf-8")


def test_quiet_and_private_keeps_explicit_settings():
    env = {"DO_NOT_TRACK": "0"}
    quiet_and_private(env)
    assert env["DO_NOT_TRACK"] == "0" and env["HF_HUB_DISABLE_TELEMETRY"] == "1"


def test_local_folders_and_cached_repos_are_available(tmp_path: Path):
    env = {"HF_HUB_CACHE": str(tmp_path / "cache")}
    cached(tmp_path / "cache", "intfloat/multilingual-e5-small")
    folder = tmp_path / "models" / "reranker"
    folder.mkdir(parents=True)
    assert available_offline("intfloat/multilingual-e5-small", env)
    assert available_offline(str(folder), env)
    assert not available_offline("other/model", env)
    assert not available_offline("qwen3:4b", env)


def test_goes_offline_only_when_every_model_is_on_disk(tmp_path: Path):
    env = {"HF_HOME": str(tmp_path)}
    cached(tmp_path / "hub", "a/one")
    assert not go_offline_if_possible(["a/one", "b/two"], env) and "HF_HUB_OFFLINE" not in env
    cached(tmp_path / "hub", "b/two")
    assert go_offline_if_possible(["a/one", "b/two"], env)
    assert env["HF_HUB_OFFLINE"] == "1" and env["TRANSFORMERS_OFFLINE"] == "1"

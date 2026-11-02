"""Keep the engine private and quiet: no telemetry, no progress bars, and no network when the models are on disk.

Call these before any Hugging Face library is imported; they read the environment once, at import time.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, MutableMapping
from pathlib import Path

PRIVATE_DEFAULTS = {
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "DO_NOT_TRACK": "1",
    "ANONYMIZED_TELEMETRY": "False",
    "HF_HUB_DISABLE_PROGRESS_BARS": "1",
    "TRANSFORMERS_VERBOSITY": "error",
    "TOKENIZERS_PARALLELISM": "false",
}


def quiet_and_private(env: MutableMapping[str, str] = os.environ) -> None:
    for key, value in PRIVATE_DEFAULTS.items():
        env.setdefault(key, value)


def hf_cache(env: MutableMapping[str, str] = os.environ) -> Path:
    if "HF_HUB_CACHE" in env:
        return Path(env["HF_HUB_CACHE"])
    home = Path(env["HF_HOME"]) if "HF_HOME" in env else Path.home() / ".cache" / "huggingface"
    return home / "hub"


def available_offline(model: str, env: MutableMapping[str, str] = os.environ) -> bool:
    """A local model folder, or a Hugging Face repo that is already in the cache."""
    if Path(model).is_dir():
        return True
    if model.count("/") != 1:
        return False
    snapshots = hf_cache(env) / f"models--{model.replace('/', '--')}" / "snapshots"
    return any((snap / "config.json").is_file() for snap in snapshots.glob("*")) if snapshots.is_dir() else False


def go_offline_if_possible(models: Iterable[str], env: MutableMapping[str, str] = os.environ) -> bool:
    """Forbid network access to Hugging Face when every model is already on disk. Returns whether it did."""
    if not all(available_offline(m, env) for m in models):
        return False
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    return True

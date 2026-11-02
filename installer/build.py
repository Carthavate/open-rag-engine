"""Builds the Open RAG installer: one setup that needs no internet, no Python and no Ollama on the target computer.

    uv run python installer/build.py             # stage everything, check it, run Inno Setup
    uv run python installer/build.py --no-iscc   # stage and check only (installer/build/stage)

The stage mirrors the installed app:

    OpenRag.exe, wwwroot/ ...       the desktop app (self-contained .NET) and its interface
    engine/python/                  a standalone CPython with open-rag-engine and its locked dependencies
    engine/models/<org>--<name>/    the embedding and reranker models, copied from the Hugging Face cache
    engine/llm/                     llama.cpp's llama-server (CPU build) and the Qwen3 GGUF, copied from Ollama
    engine/ore.toml                 points the engine at those models

Before building, the models must be on this computer: run `ore ask` once (Hugging Face models) and
`ollama pull qwen3:4b-instruct-2507-q4_K_M`. The only download is the pinned llama.cpp release, verified by its digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

from open_rag_engine.config import EngineConfig

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "installer"
BUILD = HERE / "build"
STAGE = BUILD / "stage"
ENGINE = STAGE / "engine"
CACHE = HERE / ".cache"
DIST = HERE / "dist"
APP_PROJECT = ROOT / "desktop" / "src" / "OpenRag.App"

PYTHON_VERSION = "3.12"
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"

LLAMA_BUILD = "b12052"
LLAMA_ZIP = f"llama-{LLAMA_BUILD}-bin-win-cpu-x64.zip"
LLAMA_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_BUILD}/{LLAMA_ZIP}"
LLAMA_SHA256 = "0f6a20186bed5ad765ccac87832ce8e15a7a44eedc7825cd1dbdd114d423e7f0"

OLLAMA_MODEL = ("qwen3", "4b-instruct-2507-q4_K_M")
# Must match LlmBundle.ModelAlias in desktop/src/OpenRag.Core/Engine.cs, which passes it to llama-server.
LLM_ALIAS = "qwen3-4b-instruct"

ISCC = Path(os.environ.get("ISCC", r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"))
GITHUB_FILE_LIMIT = 2 * 1024**3


def run(*args: str | Path, cwd: Path = ROOT, attempts: int = 1) -> str:
    """Runs a build tool and returns its output. `attempts` > 1 retries a step that antivirus scanning of freshly
    written files can briefly lock ("Access is denied")."""
    print("  >", " ".join(str(a) for a in args), flush=True)
    for attempt in range(1, attempts + 1):
        result = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            return result.stdout.strip()
        if attempt < attempts:
            print(f"  failed ({result.returncode}), trying again", flush=True)
    command = " ".join(map(str, args))
    sys.exit(f"Failed ({result.returncode}): {command}\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}")


def step(title: str) -> None:
    print(f"\n== {title}", flush=True)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def folder_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


# --- the app ------------------------------------------------------------------------------------------------------


def publish_app() -> None:
    step("Desktop app (dotnet publish, self-contained win-x64)")
    run("dotnet", "publish", APP_PROJECT, "-c", "Release", "-r", "win-x64", "--self-contained", "-o", STAGE)
    if not (STAGE / "OpenRag.exe").is_file() or not (STAGE / "wwwroot" / "index.html").is_file():
        sys.exit("The publish output has no OpenRag.exe or wwwroot/index.html.")


# --- the engine ---------------------------------------------------------------------------------------------------


def stage_python() -> Path:
    step(f"Standalone Python {PYTHON_VERSION}")
    run("uv", "python", "install", PYTHON_VERSION)
    # --system: under `uv run` the project's virtualenv is active, and it must not be the one we copy.
    source = Path(run("uv", "python", "find", "--system", "--managed-python", PYTHON_VERSION)).parent
    target = ENGINE / "python"
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    # uv marks its Pythons as managed elsewhere; this private copy is ours to install into.
    for marker in target.glob("Lib/EXTERNALLY-MANAGED"):
        marker.unlink()
    return target / "python.exe"


def install_engine(python: Path) -> None:
    step("open-rag-engine and its locked dependencies (CPU torch)")
    wheels = BUILD / "wheel"
    run("uv", "build", "--wheel", "--out-dir", wheels)
    requirements = BUILD / "requirements.txt"
    run("uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes", "--output-file", requirements)
    # Copies, not links into uv's cache: the stage must stand alone.
    install = ("uv", "pip", "install", "--python", python, "--link-mode", "copy")
    torch_cpu = ("--index-strategy", "unsafe-best-match", "--extra-index-url", TORCH_INDEX)
    run(*install, *torch_cpu, "-r", requirements, attempts=3)
    wheel = max(wheels.glob("open_rag_engine-*.whl"), key=lambda w: w.stat().st_mtime)
    run(*install, "--no-deps", wheel, attempts=3)
    trim_python(python.parent)


def trim_python(python_dir: Path) -> None:
    """Drops what only building software needs: console-script launchers (they hold this build machine's paths),
    torch's C++ headers and import libraries."""
    site = python_dir / "Lib" / "site-packages"
    removable = [python_dir / "Scripts", site / "torch" / "include", *site.glob("torch/lib/*.lib")]
    freed = 0
    for path in removable:
        if path.is_dir():
            freed += folder_size(path)
            shutil.rmtree(path)
        elif path.is_file():
            freed += path.stat().st_size
            path.unlink()
    print(f"  trimmed {freed / 1e6:.0f} MB")


def hf_cache() -> Path:
    if cache := os.environ.get("HF_HUB_CACHE"):
        return Path(cache)
    home = os.environ.get("HF_HOME")
    return Path(home) / "hub" if home else Path.home() / ".cache" / "huggingface" / "hub"


def stage_models(config: EngineConfig) -> None:
    step("Embedding and reranker models (from the Hugging Face cache)")
    for model in (config.embeddings.model, config.rerank.model):
        repo = hf_cache() / f"models--{model.replace('/', '--')}"
        ref = repo / "refs" / "main"
        if not ref.is_file():
            sys.exit(f"{model} is not in {hf_cache()}. Run `ore ask` once so it downloads, then build again.")
        snapshot = repo / "snapshots" / ref.read_text().strip()
        target = ENGINE / "models" / model.replace("/", "--")
        # The cache may hold symlinks to its blobs; copytree copies the files they point to.
        shutil.copytree(snapshot, target, symlinks=False, ignore=shutil.ignore_patterns("onnx", "openvino"))
        print(f"  {model}: {folder_size(target) / 1e6:.0f} MB")


def write_config() -> None:
    step("Engine configuration")
    (ENGINE / "ore.toml").write_text(
        "# Written by installer/build.py. The installed engine loads its models from this folder and asks the\n"
        "# language model the app starts (llama-server); the app passes that server's address with --llm-url.\n"
        'models_dir = "models"\n'
        "\n"
        "[llm]\n"
        'provider = "openai"\n'
        f'model = "{LLM_ALIAS}"\n',
        encoding="utf-8",
    )


# --- the language model -------------------------------------------------------------------------------------------


def llama_zip() -> Path:
    """The pinned llama.cpp release, downloaded once into installer/.cache and checked against its digest."""
    archive = CACHE / LLAMA_ZIP
    if not archive.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {LLAMA_URL}")
        partial = archive.with_suffix(".part")
        with urllib.request.urlopen(LLAMA_URL, timeout=60) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out)
        partial.replace(archive)
    if (actual := sha256_of(archive)) != LLAMA_SHA256:
        sys.exit(f"{archive} has digest {actual}, expected {LLAMA_SHA256}. Delete it and build again.")
    return archive


def stage_llama_server() -> None:
    step(f"llama.cpp {LLAMA_BUILD} (CPU build)")
    target = ENGINE / "llm"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(llama_zip()) as archive:
        for member in archive.infolist():
            # Names are flattened, so nothing can land outside the target folder.
            name = Path(member.filename).name
            if not member.is_dir() and is_server_file(name):
                with archive.open(member) as source, (target / name).open("wb") as out:
                    shutil.copyfileobj(source, out)
    if not (target / "llama-server.exe").is_file():
        sys.exit(f"{LLAMA_ZIP} has no llama-server.exe.")
    # The release zip carries only the OpenMP licence; llama.cpp's own (MIT) is kept in installer/licenses.
    shutil.copyfile(HERE / "licenses" / "llama.cpp-LICENSE.txt", target / "LICENSE-llama.cpp.txt")


def is_server_file(name: str) -> bool:
    """llama-server and the libraries it loads; the release's other tools (bench, quantize ...) and their `-impl`
    libraries stay out."""
    if name.startswith("LICENSE") or name in ("llama-server.exe", "llama-server-impl.dll"):
        return True
    return name.endswith(".dll") and not name.endswith("-impl.dll")


def ollama_models() -> Path:
    return Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama" / "models"))


def stage_gguf() -> None:
    step(f"Language model {':'.join(OLLAMA_MODEL)} (from Ollama)")
    name, tag = OLLAMA_MODEL
    manifest = ollama_models() / "manifests" / "registry.ollama.ai" / "library" / name / tag
    if not manifest.is_file():
        sys.exit(f"Run `ollama pull {name}:{tag}` first ({manifest} is missing).")
    layers = {layer["mediaType"]: layer["digest"] for layer in json.loads(manifest.read_text())["layers"]}

    def blob(media_type: str) -> tuple[Path, str]:
        digest = layers[media_type]
        return ollama_models() / "blobs" / digest.replace(":", "-"), digest.split(":", 1)[1]

    source, expected = blob("application/vnd.ollama.image.model")
    target = ENGINE / "llm" / "model.gguf"
    shutil.copyfile(source, target)
    if sha256_of(target) != expected:
        sys.exit(f"The copied model doesn't match Ollama's digest {expected}.")
    if "application/vnd.ollama.image.license" in layers:
        shutil.copyfile(blob("application/vnd.ollama.image.license")[0], ENGINE / "llm" / "MODEL_LICENSE.txt")
    print(f"  {target.stat().st_size / 1e9:.2f} GB, digest verified")


# --- checks and the installer -------------------------------------------------------------------------------------


def copy_notices() -> None:
    shutil.copyfile(ROOT / "LICENSE", STAGE / "LICENSE.txt")
    shutil.copyfile(HERE / "THIRD_PARTY_NOTICES.md", STAGE / "THIRD_PARTY_NOTICES.md")


def check_stage(python: Path) -> None:
    """The staged engine must import with nothing from this machine: isolated mode, no user site, no PYTHONPATH."""
    step("Checking the stage")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "VIRTUAL_ENV", "UV_"))}
    probe = "import open_rag_engine, torch, chromadb, sentence_transformers, langchain_openai; print(torch.__version__)"
    result = subprocess.run([python, "-I", "-c", probe], capture_output=True, text=True, env=env, cwd=ENGINE)
    if result.returncode != 0:
        sys.exit(f"The bundled engine doesn't import:\n{result.stderr[-3000:]}")
    print(f"  engine imports (torch {result.stdout.strip()})")
    server = ENGINE / "llm" / "llama-server.exe"
    result = subprocess.run([server, "--version"], capture_output=True, text=True, cwd=server.parent)
    if result.returncode != 0:
        sys.exit(f"llama-server doesn't start:\n{result.stderr[-2000:]}")
    # It prints its version to stderr.
    print(f"  llama-server: {(result.stdout + result.stderr).strip().splitlines()[0]}")
    print(f"  stage: {folder_size(STAGE) / 1e9:.2f} GB")


def version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def run_iscc() -> None:
    step("Inno Setup")
    if not ISCC.is_file():
        sys.exit(f"Inno Setup's compiler isn't at {ISCC}; install Inno Setup 6 or set ISCC.")
    run(ISCC, f"/DAppVersion={version()}", f"/DStage={STAGE}", f"/DOutputDir={DIST}", HERE / "OpenRag.iss")
    for file in sorted(DIST.glob("OpenRag-Setup*")):
        print(f"  {file.name}: {file.stat().st_size / 1e6:.0f} MB")
        if file.stat().st_size >= GITHUB_FILE_LIMIT:
            sys.exit(f"{file.name} is too large for a GitHub release (2 GiB per file); lower DiskSliceSize.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-iscc", action="store_true", help="stage and check, but don't build the installer")
    args = parser.parse_args()

    if STAGE.exists():
        shutil.rmtree(STAGE)
    if DIST.exists():
        shutil.rmtree(DIST)
    publish_app()
    python = stage_python()
    install_engine(python)
    stage_models(EngineConfig())
    write_config()
    stage_llama_server()
    stage_gguf()
    copy_notices()
    check_stage(python)
    if not args.no_iscc:
        run_iscc()


if __name__ == "__main__":
    main()

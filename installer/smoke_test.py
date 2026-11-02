"""End-to-end check of a built Open RAG, without its window: starts the bundled llama-server and engine the way the
app does, with model downloads blocked, indexes the example pump manual and asks it a question.

    uv run python installer/smoke_test.py                                      # the stage (installer/build/stage)
    uv run python installer/smoke_test.py "%LOCALAPPDATA%\\Programs\\Open RAG"   # an installed app

The data goes to a temporary folder, so it never touches the app's own library.
"""

from __future__ import annotations

import json
import os
import queue
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "installer" / "build" / "stage"
DOCS = ROOT / "examples" / "docs"
QUESTION = "Why does my pump keep turning itself off?"
# Must match LlmBundle in desktop/src/OpenRag.Core/Engine.cs.
MODEL_ALIAS = "qwen3-4b-instruct"
START_TIMEOUT = 300


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def clean_env(**extra: str) -> dict[str, str]:
    """This machine's environment minus anything that could point Python at a developer setup, with model
    downloads sent to a dead address so any attempt fails loudly."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "VIRTUAL_ENV", "UV_", "HF_"))}
    return {**env, "HF_ENDPOINT": "http://127.0.0.1:9", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", **extra}


def request(url: str, body: object | None = None, token: str | None = None, method: str | None = None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} | ({"Authorization": f"Bearer {token}"} if token else {})
    return urllib.request.urlopen(urllib.request.Request(url, data, headers, method=method), timeout=600)


def call(base: str, token: str, path: str, body: object | None = None) -> dict:
    with request(base + path, body, token) as response:
        return json.loads(response.read() or b"{}")


def wait_for(check, what: str, timeout: float = START_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (urllib.error.URLError, ConnectionError):
            pass
        time.sleep(1)
    sys.exit(f"FAIL: {what} not ready within {timeout} s")


def start(args: list[str | Path], env: dict[str, str], log: Path, cwd: Path) -> tuple[subprocess.Popen, queue.Queue]:
    """Starts a process with its output copied to a log and to a queue of lines (to spot ORE_READY)."""
    process = subprocess.Popen(
        [str(a) for a in args],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    lines: queue.Queue = queue.Queue()

    def pump() -> None:
        with log.open("w", encoding="utf-8") as out:
            for line in process.stdout:
                out.write(line)
                out.flush()
                lines.put(line.strip())

    threading.Thread(target=pump, daemon=True).start()
    return process, lines


def ready_port(lines: queue.Queue, process: subprocess.Popen, log: Path) -> int:
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            sys.exit(f"FAIL: the engine exited ({process.returncode}). See {log}")
        try:
            line = lines.get(timeout=1)
        except queue.Empty:
            continue
        if line.startswith("ORE_READY port="):
            return int(line.split("=", 1)[1])
    sys.exit(f"FAIL: the engine didn't print ORE_READY. See {log}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # answers quote units such as °C
    app = Path(sys.argv[1]) if len(sys.argv) > 1 else STAGE
    engine = app / "engine"
    work = Path(tempfile.mkdtemp(prefix="openrag-smoke-"))
    port, key, token = free_port(), secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    llm_url = f"http://127.0.0.1:{port}"
    print(f"app: {app}\nlogs: {work}")

    started = time.monotonic()
    llm, _ = start(
        [
            engine / "llm" / "llama-server.exe",
            "-m",
            engine / "llm" / "model.gguf",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--ctx-size",
            "8192",
            "--jinja",
            "--alias",
            MODEL_ALIAS,
            "--no-webui",
        ],
        clean_env(LLAMA_API_KEY=key),
        work / "llm.log",
        engine / "llm",
    )
    server, lines = start(
        [
            engine / "python" / "python.exe",
            "-m",
            "open_rag_engine",
            "serve",
            "--data-dir",
            work / "data",
            "--parent-pid",
            str(os.getpid()),
            "--warm",
            "--llm-url",
            f"{llm_url}/v1",
            "--config",
            engine / "ore.toml",
        ],
        clean_env(ORE_API_TOKEN=token, ORE_LLM_API_KEY=key),
        work / "engine.log",
        engine,
    )
    try:
        base = f"http://127.0.0.1:{ready_port(lines, server, work / 'engine.log')}"
        print(f"engine ready after {time.monotonic() - started:.0f} s")
        wait_for(lambda: request(f"{llm_url}/health").status == 200, "llama-server")
        print(f"language model ready after {time.monotonic() - started:.0f} s")

        try:
            # /health and /v1/models are public in llama-server; chat is not.
            request(f"{llm_url}/v1/chat/completions", {"messages": [{"role": "user", "content": "hi"}]}).close()
            sys.exit("FAIL: llama-server answered without its key")
        except urllib.error.HTTPError as error:
            assert error.code == 401, error.code
        print("language model refuses requests without the key")

        category = call(base, token, "/categories", {"name": "Smoke test"})
        section = call(base, token, "/sections", {"name": "Pump manual", "category_id": category["id"]})
        call(base, token, f"/sections/{section['id']}/folders", {"path": str(DOCS)})
        call(base, token, f"/sections/{section['id']}/index", {})
        wait_for(lambda: call(base, token, f"/sections/{section['id']}/status")["state"] == "idle", "indexing")
        status = call(base, token, f"/sections/{section['id']}/status")
        if status["error"]:
            sys.exit(f"FAIL: indexing: {status['error']}")
        print(f"indexed {DOCS.name}: {status['report']}")

        asked = time.monotonic()
        ask = {"scope": {"kind": "section", "id": section["id"]}, "question": QUESTION}
        with request(base + "/ask", ask, token) as response:
            events = [json.loads(line) for line in response.read().decode().splitlines() if line.strip()]
        done = events[-1]
        if done.get("type") != "done" or not done.get("text") or not done.get("sources"):
            sys.exit(f"FAIL: no cited answer: {done}")
        print(f"\nQ: {QUESTION}\nA ({time.monotonic() - asked:.0f} s): {done['text']}")
        print("sources:", ", ".join(s["label"] for s in done["sources"]))
        print("\nPASS")
    finally:
        for process in (server, llm):
            process.terminate()


if __name__ == "__main__":
    main()

"""The `ore` command line: ingest documents, search them, ask questions with citations, chat, and evaluate."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from pydantic import ValidationError

from .answer import Answer
from .config import EngineConfig, load_config
from .conversation import Turn
from .engine import Engine
from .ingest import IndexMismatchError
from .offline import go_offline_if_possible, quiet_and_private
from .pipeline import RetrievalResult

app = typer.Typer(
    help="open-rag-engine: hybrid retrieval, reranking and cited answers on your own documents.",
    no_args_is_help=True,
    add_completion=False,
)

DEFAULT_CONFIG = Path("ore.toml")


@app.callback()
def _startup() -> None:
    """Private, quiet, UTF-8 output. Runs before any command loads a model."""
    quiet_and_private()
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


ConfigOpt = Annotated[
    Path | None, typer.Option("--config", "-c", help="TOML configuration (default: ./ore.toml if present).")
]
CollectionOpt = Annotated[str | None, typer.Option(help="Collection to use instead of the configured one.")]
SearchTypeOpt = Annotated[str | None, typer.Option(help="Vector search: similarity, mmr or threshold.")]
KOpt = Annotated[int | None, typer.Option("--k", help="Candidates per retriever.")]
NoRerankOpt = Annotated[bool, typer.Option("--no-rerank", help="Skip the cross-encoder reranker.")]
MultiQueryOpt = Annotated[
    bool, typer.Option("--multi-query", help="Let the LLM rephrase the question and fuse the results.")
]
SourceOpt = Annotated[str | None, typer.Option(help="Only search chunks from this source file (absolute path).")]
TraceOpt = Annotated[bool, typer.Option("--trace", help="Show what every pipeline stage returned.")]


def build_engine(config: EngineConfig) -> Engine:
    go_offline_if_possible([config.embeddings.model, config.rerank.model])
    return Engine.from_config(config)


def _config(
    path: Path | None,
    collection: str | None = None,
    search_type: str | None = None,
    k: int | None = None,
    no_rerank: bool = False,
    multi_query: bool = False,
) -> EngineConfig:
    cfg = load_config(path or (DEFAULT_CONFIG if DEFAULT_CONFIG.is_file() else None))
    if collection:
        cfg = EngineConfig.model_validate({**cfg.model_dump(), "collection": collection})
    retrieval: dict[str, Any] = {"search_type": search_type, "k": k, "multi_query": True if multi_query else None}
    retrieval = {key: value for key, value in retrieval.items() if value is not None}
    if retrieval:
        cfg = cfg.updated("retrieval", **retrieval)
    if no_rerank:
        cfg = cfg.updated("rerank", enabled=False)
    return cfg


def _fail(message: str) -> typer.Exit:
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=True)
    return typer.Exit(code=1)


def _run(action):
    """Run a command and turn expected failures into one readable line instead of a traceback."""
    try:
        return action()
    except (FileNotFoundError, IndexMismatchError, ValueError) as error:
        raise _fail(str(error)) from error
    except ValidationError as error:
        raise _fail(f"invalid configuration:\n{error}") from error
    except httpx.ConnectError as error:
        raise _fail(
            "can't reach Ollama. Start it with `ollama serve` and pull the model, e.g. `ollama pull qwen3:4b`."
        ) from error


@app.command()
def ingest(
    paths: Annotated[list[Path], typer.Argument(help="Files or folders (.md, .txt, .pdf).")],
    rebuild: Annotated[bool, typer.Option(help="Drop the collection and re-index everything.")] = False,
    config: ConfigOpt = None,
    collection: CollectionOpt = None,
) -> None:
    """Index documents. Unchanged files are skipped; changed files replace their old chunks."""

    def action():
        report = build_engine(_config(config, collection)).ingest(paths, rebuild=rebuild)
        typer.echo(
            f"{len(report.added)} added, {len(report.updated)} updated, {len(report.unchanged)} unchanged, "
            f"{len(report.failed)} failed | {report.chunks_added} chunks indexed"
        )
        for source, error in report.failed:
            typer.secho(f"  failed: {source}: {error}", fg=typer.colors.YELLOW)

    _run(action)


@app.command()
def search(
    query: str,
    trace: TraceOpt = False,
    source: SourceOpt = None,
    config: ConfigOpt = None,
    collection: CollectionOpt = None,
    search_type: SearchTypeOpt = None,
    k: KOpt = None,
    no_rerank: NoRerankOpt = False,
    multi_query: MultiQueryOpt = False,
) -> None:
    """Retrieve passages without an LLM answer."""

    def action():
        engine = build_engine(_config(config, collection, search_type, k, no_rerank, multi_query))
        result = engine.retrieve(query, {"source": source} if source else None)
        _print_passages(result)
        if trace:
            _print_trace(result)

    _run(action)


@app.command()
def ask(
    question: str,
    trace: TraceOpt = False,
    source: SourceOpt = None,
    config: ConfigOpt = None,
    collection: CollectionOpt = None,
    search_type: SearchTypeOpt = None,
    k: KOpt = None,
    no_rerank: NoRerankOpt = False,
    multi_query: MultiQueryOpt = False,
) -> None:
    """Answer a question from your documents, with citations."""

    def action():
        engine = build_engine(_config(config, collection, search_type, k, no_rerank, multi_query))
        answer = engine.ask(question, filter={"source": source} if source else None, on_token=_echo_token)
        _print_answer_footer(answer)
        if trace:
            _print_trace(answer.retrieval)

    _run(action)


@app.command()
def chat(
    config: ConfigOpt = None,
    collection: CollectionOpt = None,
    no_rerank: NoRerankOpt = False,
    multi_query: MultiQueryOpt = False,
) -> None:
    """A conversation: follow-up questions are rewritten using the history. Empty line or 'exit' to stop."""

    def action():
        engine = build_engine(_config(config, collection, no_rerank=no_rerank, multi_query=multi_query))
        history: list[Turn] = []
        while True:
            question = typer.prompt("You", default="", show_default=False).strip()
            if question.lower() in {"", "exit", "quit"}:
                return
            answer = engine.ask(question, history=history, on_token=_echo_token)
            _print_answer_footer(answer)
            history = [*history, (question, answer.text)]

    _run(action)


@app.command("eval")
def evaluate(
    dataset: Annotated[Path, typer.Argument(help="JSONL with question and expected_sources per line.")],
    output: Annotated[Path | None, typer.Option(help="Write the full report as JSON.")] = None,
    config: ConfigOpt = None,
    collection: CollectionOpt = None,
    search_type: SearchTypeOpt = None,
    k: KOpt = None,
    no_rerank: NoRerankOpt = False,
    multi_query: MultiQueryOpt = False,
) -> None:
    """Measure retrieval quality: hit rate, MRR and recall at k."""

    def action():
        engine = build_engine(_config(config, collection, search_type, k, no_rerank, multi_query))
        report = engine.evaluate(dataset)
        typer.echo(f"{len(report.cases)} questions | config {report.config_fingerprint} | k={report.k}")
        typer.echo(f"hit rate {report.hit_rate:.2f} | MRR {report.mrr:.2f} | recall {report.recall:.2f}")
        for case in report.cases:
            if not case.hit:
                typer.secho(
                    f"  miss: {case.question} -> got {', '.join(case.ranked_sources) or 'nothing'}",
                    fg=typer.colors.YELLOW,
                )
        if output:
            output.write_text(report.to_json(), encoding="utf-8")
            typer.echo(f"report written to {output}")

    _run(action)


@app.command()
def info(config: ConfigOpt = None, collection: CollectionOpt = None) -> None:
    """Show what is indexed and which models are configured."""

    def action():
        cfg = _config(config, collection)
        for key, value in build_engine(cfg).stats().items():
            typer.echo(f"{key}: {value}")
        typer.echo(
            f"embeddings: {cfg.embeddings.model}\nreranker: {cfg.rerank.model if cfg.rerank.enabled else 'off'}"
            f"\nllm: {cfg.llm.model} via {cfg.llm.base_url}"
        )

    _run(action)


TOKEN_VARIABLE = "ORE_API_TOKEN"


@app.command()
def serve(
    port: Annotated[int, typer.Option(help="Port on 127.0.0.1; 0 picks a free one.")] = 0,
    origin: Annotated[list[str] | None, typer.Option(help="Web origin allowed to call the API.")] = None,
    parent_pid: Annotated[int | None, typer.Option(help="Exit when this process exits.")] = None,
    data_dir: Annotated[Path | None, typer.Option(help="Where indexes and the workspace live.")] = None,
    warm: Annotated[bool, typer.Option(help="Load the embedding and reranker models in the background.")] = False,
    config: ConfigOpt = None,
) -> None:
    """Run the local API for the desktop app. Prints `ORE_READY port=<n>` once it listens."""

    def action():
        token = os.environ.get(TOKEN_VARIABLE, "")
        if len(token) < 32:
            raise ValueError(f"Set {TOKEN_VARIABLE} to a random secret of at least 32 characters.")
        cfg = _config(config)
        if data_dir is not None:
            cfg = EngineConfig.model_validate({**cfg.model_dump(), "data_dir": data_dir})
        go_offline_if_possible([cfg.embeddings.model, cfg.rerank.model])
        from .api import create_app
        from .factory import LocalModels
        from .library import Library

        models = LocalModels(cfg)
        api = create_app(Library(cfg, models), token, origin or ["https://app.ore"])
        if warm:
            threading.Thread(target=_warm, args=(models,), name="warm-up", daemon=True).start()
        server = _listen(port)
        typer.echo(f"ORE_READY port={server.getsockname()[1]}")
        sys.stdout.flush()
        if parent_pid:
            threading.Thread(target=_exit_with_parent, args=(parent_pid,), daemon=True).start()
        import uvicorn

        uvicorn.Server(uvicorn.Config(api, log_level="warning", access_log=False)).run(sockets=[server])

    _run(action)


def _warm(models: Any) -> None:
    """Load the models before the first question, so it isn't the one that waits."""
    try:
        models.embeddings.embed_query("warm-up")
        models.cross_encoder.score([("warm-up", "warm-up")])
    except Exception as error:  # the first real request will load (and report) them instead
        typer.echo(f"warm-up skipped: {error}", err=True)


def _listen(port: int) -> socket.socket:
    """Bind to loopback only. The socket is handed to uvicorn, so the chosen port is known before it starts."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))
    return server


def _exit_with_parent(pid: int) -> None:
    """Backstop for the app's job object: if the app disappears, the engine must not linger."""
    if sys.platform == "win32":
        import ctypes

        synchronize, infinite = 0x00100000, 0xFFFFFFFF
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
        if handle:
            ctypes.windll.kernel32.WaitForSingleObject(handle, infinite)
    else:
        while os.getppid() == pid:
            time.sleep(2)
    os._exit(0)


def _echo_token(token: str) -> None:
    typer.echo(token, nl=False)


def _print_passages(result: RetrievalResult) -> None:
    if not result.passages:
        typer.echo("No passages found.")
    for rank, passage in enumerate(result.passages, start=1):
        from .documents import citation_label

        snippet = " ".join(passage.doc.page_content.split())[:160]
        typer.echo(f"{rank}. [{passage.score:.3f}] {citation_label(passage.doc)}\n   {snippet}")


def _print_answer_footer(answer: Answer) -> None:
    typer.echo("")
    for citation in answer.citations:
        typer.echo(f"  [{citation.number}] {citation.label}")
    if answer.invalid_citations:
        typer.secho(f"  warning: cites sources that don't exist: {answer.invalid_citations}", fg=typer.colors.YELLOW)
    elif not answer.grounded and not answer.abstained:
        typer.secho(
            "  warning: the answer cites no source, so it may not come from your documents", fg=typer.colors.YELLOW
        )


def _print_trace(result: RetrievalResult) -> None:
    typer.echo("\ntrace:")
    for stage in result.trace:
        typer.echo(f"  {stage.name} ({stage.ms} ms) {stage.detail or ''}".rstrip())
        for query, label, score in stage.results[:5]:
            shown = "-" if score is None else f"{score:.3f}"
            prefix = "" if query == "*" or len(result.queries) == 1 else f"[{query[:30]}] "
            typer.echo(f"    {prefix}{shown}  {label}")

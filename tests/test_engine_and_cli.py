import json
from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from typer.testing import CliRunner

from open_rag_engine import cli
from open_rag_engine.engine import Engine

from .conftest import FakeModels, HashEmbeddings, OverlapCrossEncoder


def engine(config, *answers: str) -> Engine:
    return Engine(
        config, FakeModels(HashEmbeddings(), OverlapCrossEncoder(), FakeListChatModel(responses=list(answers) or ["-"]))
    )


def test_engine_ingest_retrieve_and_ask(corpus: Path, config):
    eng = engine(config, "Up to 1.2 kW [1].")
    assert eng.ingest([corpus]).chunks_added == 5
    assert Path(eng.retrieve("pump power full speed").passages[0].doc.metadata["source"]).name == "power.md"
    answer = eng.ask("How much power does the pump draw?")
    assert answer.grounded and answer.citations[0].label == "power.md"


def test_engine_rewrites_follow_ups_from_history(corpus: Path, config):
    eng = engine(config, "How long is the pump warranty?", "Two years [1].")
    eng.ingest([corpus])
    answer = eng.ask("And the warranty?", history=[("What voltage?", "230 V [1].")])
    assert answer.question == "How long is the pump warranty?"
    assert answer.citations[0].label == "warranty.md"


def test_engine_evaluate(corpus: Path, config, tmp_path: Path):
    eng = engine(config)
    eng.ingest([corpus])
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        json.dumps({"question": "error E1042", "expected_sources": ["e1042.md"]}) + "\n", encoding="utf-8"
    )
    report = eng.evaluate(dataset)
    assert report.hit_rate == 1.0 and report.config_fingerprint == config.fingerprint()


def run_cli(monkeypatch, config, *args: str, answers=("Two years [1].",)):
    monkeypatch.setattr(cli, "build_engine", lambda cfg: engine(cfg, *answers))
    monkeypatch.setattr(cli, "load_config", lambda path: config)
    return CliRunner().invoke(cli.app, list(args))


def test_cli_ingest_search_ask(monkeypatch, corpus: Path, config):
    result = run_cli(monkeypatch, config, "ingest", str(corpus))
    assert result.exit_code == 0, result.output
    assert "5 added" in result.output
    result = run_cli(monkeypatch, config, "search", "pump warranty", "--trace")
    assert result.exit_code == 0 and "warranty.md" in result.output and "rerank" in result.output
    result = run_cli(monkeypatch, config, "ask", "How long is the warranty?")
    assert result.exit_code == 0 and "Two years [1]." in result.output and "[1] warranty.md" in result.output


def test_cli_overrides_and_eval(monkeypatch, corpus: Path, config, tmp_path: Path):
    run_cli(monkeypatch, config, "ingest", str(corpus))
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        json.dumps({"question": "frost winter", "expected_sources": ["winter.md"]}) + "\n", encoding="utf-8"
    )
    out = tmp_path / "report.json"
    result = run_cli(
        monkeypatch, config, "eval", str(dataset), "--no-rerank", "--search-type", "mmr", "--output", str(out)
    )
    assert result.exit_code == 0, result.output
    assert "hit rate" in result.output.lower() and json.loads(out.read_text(encoding="utf-8"))["hit_rate"] == 1.0


def test_cli_reports_errors_without_a_traceback(monkeypatch, config, tmp_path: Path):
    result = run_cli(monkeypatch, config, "ingest", str(tmp_path / "missing"))
    assert result.exit_code == 1 and "not found" in result.output.lower() and "Traceback" not in result.output


def test_cli_chat_keeps_history(monkeypatch, corpus: Path, config):
    run_cli(monkeypatch, config, "ingest", str(corpus))
    monkeypatch.setattr(
        cli, "build_engine", lambda cfg: engine(cfg, "230 V [1].", "How long is the pump warranty?", "Two years [1].")
    )
    result = CliRunner().invoke(cli.app, ["chat"], input="What voltage?\nAnd the warranty?\n\n")
    assert result.exit_code == 0, result.output
    assert "230 V [1]." in result.output and "Two years [1]." in result.output and "[1] warranty.md" in result.output


def test_cli_info(monkeypatch, corpus: Path, config):
    run_cli(monkeypatch, config, "ingest", str(corpus))
    result = run_cli(monkeypatch, config, "info")
    assert result.exit_code == 0 and "documents: 5" in result.output and "qwen3:4b-instruct" in result.output


def test_cli_warns_about_uncited_answers(monkeypatch, corpus: Path, config):
    run_cli(monkeypatch, config, "ingest", str(corpus))
    result = run_cli(monkeypatch, config, "ask", "warranty?", answers=("Two years.",))
    assert "cites no source" in result.output


def test_querying_with_a_changed_index_configuration_asks_for_a_rebuild(monkeypatch, corpus: Path, config):
    run_cli(monkeypatch, config, "ingest", str(corpus))
    changed = config.updated("chunking", chunk_size=300)
    result = run_cli(monkeypatch, changed, "search", "pump")
    assert result.exit_code == 1 and "--rebuild" in result.output


def test_serve_refuses_to_start_without_a_strong_token(monkeypatch):
    monkeypatch.delenv("ORE_API_TOKEN", raising=False)
    result = CliRunner().invoke(cli.app, ["serve"])
    assert result.exit_code == 1 and "ORE_API_TOKEN" in result.output


def test_listen_binds_loopback_on_a_free_port():
    server = cli._listen(0)
    try:
        host, port = server.getsockname()
        assert host == "127.0.0.1" and port > 0
    finally:
        server.close()

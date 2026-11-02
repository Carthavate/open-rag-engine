from concurrent.futures import Future
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from open_rag_engine.library import ConflictError, Library
from open_rag_engine.workspace import NotFoundError

from .conftest import FakeModels, HashEmbeddings, OverlapCrossEncoder


class ManualExecutor:
    """Holds submitted jobs until the test runs them."""

    def __init__(self):
        self.jobs = []

    def submit(self, fn, *args):
        future = Future()
        self.jobs.append((fn, args, future))
        return future

    def run_all(self):
        for fn, args, future in self.jobs:
            future.set_result(fn(*args))
        self.jobs = []


def write(folder: Path, files: dict[str, str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    return folder


@pytest.fixture
def library(config) -> Library:
    llm = FakeListChatModel(responses=["It draws 1.2 kW [1]."])
    return Library(config, FakeModels(HashEmbeddings(), OverlapCrossEncoder(), llm))


@pytest.fixture
def two_sections(library: Library, tmp_path: Path):
    category = library.workspace.add_category("Garden")
    pump = library.workspace.add_section("Pump", category.id)
    mower = library.workspace.add_section("Mower", category.id)
    library.workspace.add_folder(
        pump.id, write(tmp_path / "pump", {"power.md": "The pump draws 1.2 kW at full speed."})
    )
    library.workspace.add_folder(
        mower.id, write(tmp_path / "mower", {"blade.md": "Sharpen the mower blade every spring."})
    )
    for section in (pump, mower):
        library.start_indexing(section.id)
        library.wait_for_index(section.id)
    return category, pump, mower


def sources(answer) -> set[str]:
    return {Path(p.doc.metadata["source"]).name for p in answer.retrieval.passages}


def test_indexing_reports_progress_and_counts(library: Library, two_sections):
    _, pump, _ = two_sections
    status = library.status(pump.id)
    assert status.state == "idle" and (status.done, status.total) == (1, 1)
    assert library.stats(pump.id)["documents"] == 1
    assert [d["name"] for d in library.documents(pump.id)] == ["power.md"]


def test_a_section_answers_only_from_its_own_documents(library: Library, two_sections):
    _, pump, _ = two_sections
    answer = library.ask("section", pump.id, "When should I sharpen the blade?")
    assert sources(answer) <= {"power.md"}


def test_a_category_answers_from_all_its_sections(library: Library, two_sections):
    category, _, mower = two_sections
    answer = library.ask("category", category.id, "sharpen the mower blade")
    assert Path(answer.retrieval.passages[0].doc.metadata["source"]).name == "blade.md"
    assert answer.retrieval.passages[0].doc.metadata["section_id"] == mower.id
    assert {"power.md", "blade.md"} >= sources(answer)


def test_cannot_ask_while_the_section_is_indexing(config, tmp_path: Path):
    executor = ManualExecutor()
    library = Library(
        config,
        FakeModels(HashEmbeddings(), OverlapCrossEncoder(), FakeListChatModel(responses=["-"])),
        executor=executor,
    )
    section = library.workspace.add_section("Pump", library.workspace.add_category("Garden").id)
    library.workspace.add_folder(section.id, write(tmp_path / "pump", {"a.md": "pump"}))
    assert library.start_indexing(section.id).state == "indexing"
    assert library.start_indexing(section.id).state == "indexing" and len(executor.jobs) == 1
    with pytest.raises(ConflictError):
        library.ask("section", section.id, "pump?")
    executor.run_all()
    assert library.status(section.id).state == "idle"


def test_removed_files_and_folders_leave_the_index(library: Library, two_sections, tmp_path: Path):
    _, pump, _ = two_sections
    library.workspace.remove_folder(pump.id, tmp_path / "pump")
    library.start_indexing(pump.id)
    status = library.wait_for_index(pump.id)
    assert len(status.report.removed) == 1 and library.stats(pump.id)["documents"] == 0


def test_a_missing_folder_is_reported_and_its_documents_are_kept(library: Library, two_sections, tmp_path: Path):
    _, pump, _ = two_sections
    for file in (tmp_path / "pump").iterdir():
        file.unlink()
    (tmp_path / "pump").rmdir()
    library.start_indexing(pump.id)
    status = library.wait_for_index(pump.id)
    assert status.missing_folders == ((tmp_path / "pump").resolve().as_posix(),)
    assert library.stats(pump.id)["documents"] == 1


def test_indexing_errors_are_reported(library: Library, two_sections, monkeypatch):
    _, pump, _ = two_sections

    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(library.engine(pump.id), "ingest", boom)
    library.start_indexing(pump.id)
    status = library.wait_for_index(pump.id)
    assert status.state == "error" and "disk full" in status.error


def test_deleting_a_section_removes_its_index(library: Library, two_sections, config):
    _, pump, _ = two_sections
    library.delete_section(pump.id)
    with pytest.raises(NotFoundError):
        library.status(pump.id)
    assert not (config.data_dir / pump.collection / "chunks.jsonl").exists()

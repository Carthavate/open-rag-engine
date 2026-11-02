from pathlib import Path

import pytest

from open_rag_engine.workspace import NotFoundError, Workspace, WorkspaceError


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "workspace.json")


def test_categories_and_sections_persist(ws: Workspace, tmp_path: Path):
    physics = ws.add_category("Physics")
    optics = ws.add_section("Lesson 3: Optics", physics.id)
    again = Workspace(tmp_path / "workspace.json")
    assert [c.name for c in again.categories()] == ["Physics"]
    assert again.section(optics.id) == optics
    assert optics.collection.startswith("s-") and optics.collection != optics.id


def test_sections_filter_by_category(ws: Workspace):
    a, b = ws.add_category("A"), ws.add_category("B")
    ws.add_section("one", a.id)
    ws.add_section("two", b.id)
    assert [s.name for s in ws.sections(a.id)] == ["one"]
    assert len(ws.sections()) == 2


def test_rename_and_move(ws: Workspace):
    a, b = ws.add_category("A"), ws.add_category("B")
    section = ws.add_section("one", a.id)
    assert ws.rename_category(a.id, "Alpha").name == "Alpha"
    moved = ws.update_section(section.id, name="uno", category_id=b.id)
    assert (moved.name, moved.category_id) == ("uno", b.id)


@pytest.mark.parametrize("name", ["", "   ", "x" * 81])
def test_names_are_validated(ws: Workspace, name: str):
    with pytest.raises(WorkspaceError):
        ws.add_category(name)


def test_a_category_with_sections_cannot_be_deleted(ws: Workspace):
    cat = ws.add_category("A")
    section = ws.add_section("one", cat.id)
    with pytest.raises(WorkspaceError):
        ws.delete_category(cat.id)
    ws.delete_section(section.id)
    ws.delete_category(cat.id)
    assert ws.categories() == []


def test_unknown_ids_raise_not_found(ws: Workspace):
    with pytest.raises(NotFoundError):
        ws.section("nope")
    with pytest.raises(NotFoundError):
        ws.add_section("x", "missing-category")


def test_folders_are_validated_and_deduplicated(ws: Workspace, tmp_path: Path):
    section = ws.add_section("one", ws.add_category("A").id)
    folder = tmp_path / "notes"
    folder.mkdir()
    ws.add_folder(section.id, folder)
    updated = ws.add_folder(section.id, folder)
    assert updated.folders == (folder.resolve().as_posix(),)
    with pytest.raises(WorkspaceError):
        ws.add_folder(section.id, tmp_path / "missing")
    assert ws.remove_folder(section.id, folder).folders == ()

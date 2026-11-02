"""Categories and sections for the desktop app. A section is a set of folders with its own index (one collection)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path

MAX_NAME = 80


class WorkspaceError(ValueError):
    """A request that breaks a workspace rule, such as an empty name."""


class NotFoundError(KeyError):
    """An unknown category or section."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else "Not found"


@dataclass(frozen=True)
class Category:
    id: str
    name: str


@dataclass(frozen=True)
class Section:
    id: str
    name: str
    category_id: str
    folders: tuple[str, ...] = ()

    @property
    def collection(self) -> str:
        return f"s-{self.id}"


@dataclass(frozen=True)
class _State:
    categories: tuple[Category, ...] = ()
    sections: tuple[Section, ...] = ()


class Workspace:
    """Persisted as one JSON file. Every change writes a new state; nothing is mutated in place."""

    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def categories(self) -> list[Category]:
        return list(self._load().categories)

    def sections(self, category_id: str | None = None) -> list[Section]:
        return [s for s in self._load().sections if category_id is None or s.category_id == category_id]

    def category(self, category_id: str) -> Category:
        return _find(self._load().categories, category_id, "category")

    def section(self, section_id: str) -> Section:
        return _find(self._load().sections, section_id, "section")

    def add_category(self, name: str) -> Category:
        category = Category(_new_id(), _valid_name(name))
        self._update(lambda s: replace(s, categories=(*s.categories, category)))
        return category

    def rename_category(self, category_id: str, name: str) -> Category:
        renamed = replace(self.category(category_id), name=_valid_name(name))
        self._update(lambda s: replace(s, categories=_swap(s.categories, renamed)))
        return renamed

    def delete_category(self, category_id: str) -> None:
        self.category(category_id)
        if self.sections(category_id):
            raise WorkspaceError("Move or delete the sections in this category first")
        self._update(lambda s: replace(s, categories=tuple(c for c in s.categories if c.id != category_id)))

    def add_section(self, name: str, category_id: str) -> Section:
        self.category(category_id)
        section = Section(_new_id(), _valid_name(name), category_id)
        self._update(lambda s: replace(s, sections=(*s.sections, section)))
        return section

    def update_section(self, section_id: str, name: str | None = None, category_id: str | None = None) -> Section:
        section = self.section(section_id)
        if category_id is not None:
            self.category(category_id)
        updated = replace(
            section,
            name=_valid_name(name) if name is not None else section.name,
            category_id=category_id or section.category_id,
        )
        self._update(lambda s: replace(s, sections=_swap(s.sections, updated)))
        return updated

    def delete_section(self, section_id: str) -> None:
        self.section(section_id)
        self._update(lambda s: replace(s, sections=tuple(x for x in s.sections if x.id != section_id)))

    def add_folder(self, section_id: str, folder: Path) -> Section:
        section = self.section(section_id)
        if not folder.is_dir():
            raise WorkspaceError(f"Not a folder: {folder}")
        path = folder.resolve().as_posix()
        if path in section.folders:
            return section
        updated = replace(section, folders=(*section.folders, path))
        self._update(lambda s: replace(s, sections=_swap(s.sections, updated)))
        return updated

    def remove_folder(self, section_id: str, folder: Path | str) -> Section:
        section = self.section(section_id)
        target = Path(folder).resolve().as_posix() if Path(folder).exists() else str(folder)
        updated = replace(section, folders=tuple(f for f in section.folders if f not in {target, str(folder)}))
        self._update(lambda s: replace(s, sections=_swap(s.sections, updated)))
        return updated

    def _load(self) -> _State:
        if not self._path.exists():
            return _State()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return _State(
            categories=tuple(Category(**c) for c in data.get("categories", [])),
            sections=tuple(Section(**{**s, "folders": tuple(s.get("folders", []))}) for s in data.get("sections", [])),
        )

    def _update(self, change) -> None:
        with self._lock:
            state = change(self._load())
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(state), indent=1, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self._path)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _valid_name(name: str) -> str:
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME:
        raise WorkspaceError(f"A name needs 1 to {MAX_NAME} characters")
    return name


def _find(items, item_id: str, kind: str):
    for item in items:
        if item.id == item_id:
            return item
    raise NotFoundError(f"Unknown {kind}: {item_id}")


def _swap(items, new):
    return tuple(new if item.id == new.id else item for item in items)

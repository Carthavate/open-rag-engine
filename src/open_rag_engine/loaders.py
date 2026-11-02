"""Find supported files and load them as LangChain documents with their source path and page."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from .documents import PAGE, SOURCE

TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
PDF_SUFFIXES = {".pdf"}
SUPPORTED = TEXT_SUFFIXES | PDF_SUFFIXES


def discover(paths: Iterable[Path]) -> list[Path]:
    """Expand files and folders (recursively) into the supported files, sorted and without duplicates."""
    found: set[Path] = set()
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        candidates = path.rglob("*") if path.is_dir() else [path]
        found |= {p.resolve() for p in candidates if p.is_file() and p.suffix.lower() in SUPPORTED}
    return sorted(found)


def load(path: Path) -> list[Document]:
    """One document for a text file, one per non-empty page for a PDF."""
    source = path.resolve().as_posix()
    if path.suffix.lower() in PDF_SUFFIXES:
        pages = PyPDFLoader(str(path)).load()
        return [
            Document(
                page_content=page.page_content, metadata={SOURCE: source, PAGE: int(page.metadata.get("page", 0)) + 1}
            )
            for page in pages
            if page.page_content.strip()
        ]
    return [Document(page_content=_decode(path.read_bytes()), metadata={SOURCE: source})]


def _decode(data: bytes) -> str:
    """UTF-8 first (with or without BOM); otherwise Windows-1252, which never fails."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")

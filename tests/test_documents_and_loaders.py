from pathlib import Path

import pytest
from langchain_core.documents import Document

from open_rag_engine.documents import chunk_id, citation_label, content_hash
from open_rag_engine.loaders import discover, load


def test_content_hash_is_stable_and_content_based():
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_chunk_id_depends_on_document_index_config_and_text():
    base = chunk_id("doc", "cfg", 0, "text")
    assert base == chunk_id("doc", "cfg", 0, "text")
    assert (
        len(
            {
                base,
                chunk_id("doc2", "cfg", 0, "text"),
                chunk_id("doc", "cfg2", 0, "text"),
                chunk_id("doc", "cfg", 1, "text"),
                chunk_id("doc", "cfg", 0, "other"),
            }
        )
        == 5
    )


def test_citation_label_uses_file_name_and_page():
    assert (
        citation_label(Document(page_content="x", metadata={"source": "/a/b/manual.pdf", "page": 3}))
        == "manual.pdf, p. 3"
    )
    assert citation_label(Document(page_content="x", metadata={"source": "/a/notes.md"})) == "notes.md"


def test_discover_walks_folders_and_skips_unsupported(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "sub" / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "sub" / "c.exe").write_bytes(b"\x00")
    assert [p.name for p in discover([tmp_path])] == ["a.md", "b.txt"]


def test_discover_reports_missing_paths(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        discover([tmp_path / "missing"])


def test_load_text_utf8_and_legacy_encoding(tmp_path: Path):
    utf8 = tmp_path / "de.md"
    utf8.write_text("Größe der Pumpe", encoding="utf-8")
    legacy = tmp_path / "fr.txt"
    legacy.write_bytes("Pompe à eau".encode("cp1252"))
    [doc] = load(utf8)
    assert doc.page_content == "Größe der Pumpe"
    assert doc.metadata["source"] == utf8.resolve().as_posix()
    assert load(legacy)[0].page_content == "Pompe à eau"


def _minimal_pdf(pages: list[str]) -> bytes:
    """A tiny valid PDF with one line of text per page."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    font_id = 3 + 2 * len(pages)
    for i, text in enumerate(pages):
        content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        )
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = b"%PDF-1.4\n", []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def test_load_pdf_gives_one_document_per_page_with_1_based_pages(tmp_path: Path):
    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(_minimal_pdf(["First page text", "Second page text"]))
    docs = load(pdf)
    assert [d.metadata["page"] for d in docs] == [1, 2]
    assert "Second page" in docs[1].page_content

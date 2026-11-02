"""ADR-0006 confirmation: packages LangChain is sunsetting stay inside the adapter modules that wrap them."""

import ast
from pathlib import Path

PACKAGE = Path(__file__).parents[1] / "src" / "open_rag_engine"
ALLOWED = {
    "langchain_community": {"loaders.py", "retrieval.py", "rerank.py", "factory.py"},
    "langchain_experimental": {"chunking.py"},
}


def imported_roots(path: Path) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_sunsetting_packages_are_confined_to_adapters():
    offenders = [
        f"{path.name} imports {pkg}"
        for path in PACKAGE.glob("*.py")
        for pkg, allowed in ALLOWED.items()
        if pkg in imported_roots(path) and path.name not in allowed
    ]
    assert not offenders, offenders

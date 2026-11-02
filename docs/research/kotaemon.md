# Kotaemon

> Snapshot: 2026-10-17. Repository facts from the GitHub API, source code and release notes on that date.

| | |
|---|---|
| Repository | [Cinnamon/kotaemon](https://github.com/Cinnamon/kotaemon) |
| Licence | Apache-2.0 (depends on PyMuPDF, which is AGPL or commercial) |
| Backing | Cinnamon |
| Popularity | About 25.8k stars |
| Latest release | [v0.12.0](https://github.com/Cinnamon/kotaemon/releases/tag/v0.12.0), 2026-05-31 |
| Activity | **Dormant on main:** no commits in the last three months; one to two commits a month through 2026. A large refactoring branch is unmerged, and community fixes from October 2026 are unreviewed |
| Shape | A Python library (`libs/kotaemon`) and a Gradio app (`libs/ktem`). **No REST API**, a request open since 2024 ([#366](https://github.com/Cinnamon/kotaemon/issues/366), [#647](https://github.com/Cinnamon/kotaemon/issues/647)) |

## How it works

**Loaders.** Text-only PDF reading by default; Docling and PaddleOCR locally; Azure Document Intelligence, Adobe and Mathpix as hosted options. Some components call Cinnamon services that are not in the repository (an OCR endpoint and the "knet" index, [source](https://github.com/Cinnamon/kotaemon/blob/main/libs/kotaemon/kotaemon/loaders/ocr_loader.py)). Figure questions go to a vision model, Azure GPT-4o by default.

**Chunking.** One token splitter: 1,024 tokens with 256 overlap.

**Storage.** All embedded: LanceDB for full-text search, Chroma for vectors, SQLite for metadata, with server stores as options ([flowsettings.py](https://github.com/Cinnamon/kotaemon/blob/main/flowsettings.py)).

**Retrieval.** Hybrid mode **concatenates rather than fuses** ([source](https://github.com/Cinnamon/kotaemon/blob/main/libs/kotaemon/kotaemon/indices/vectorindex.py#L186-L237)): full-text hits are given a fixed score and placed before the vector hits, and by our reading the deduplication check compares objects with ID strings, so it never removes duplicates. The query scope is passed as a filter listing every chunk ID of the selected files, which scales poorly. MMR comes from LlamaIndex with a "TODO: double check" comment. The default reranker is the hosted Cohere API. The full-text index hard-codes an **English stemmer** ([source](https://github.com/Cinnamon/kotaemon/blob/main/libs/kotaemon/kotaemon/storages/docstores/lancedb.py)).

**Graphs.** Microsoft GraphRAG pinned to a 2024 version, plus nano-graphrag and LightRAG, which cause dependency conflicts ([#440](https://github.com/Cinnamon/kotaemon/issues/440)). With local models, extraction fails on parsing ([#140](https://github.com/Cinnamon/kotaemon/issues/140), [#591](https://github.com/Cinnamon/kotaemon/issues/591)).

**Citations: the best user experience we found.** A function-calling mode returns direct quotes; an inline mode makes the model emit a citation marker with a start phrase and an end phrase of about six words each, copied exactly from the source ([source](https://github.com/Cinnamon/kotaemon/blob/main/libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py)). The app turns these anchors into highlighted spans in a PDF viewer, with relevance scores and warnings when relevance is low.

**Reasoning.** Question decomposition, ReAct and ReWOO agents, query rewriting, mind maps, web search and MCP tools.

**Evaluation and observability.** None; mostly `print()` in retrieval code.

**Users.** SQLite-backed users with a default `admin/admin` account, private and public collections, chat sharing. No document-level access control.

## Architecture

The split between a library and an app is right in concept, and index types and reasoning pipelines are pluggable by import path. In practice the layers leak: pipeline classes declare **Gradio widget specifications** for their settings; configuration is spread across a Python settings file, an environment file that only seeds the database on first run, and UI state in SQLite; and three abstraction stacks are layered on each other (Cinnamon's own `theflow`, LlamaIndex 0.10 and LangChain). Dependencies are pinned to old major versions of fast-moving libraries (Gradio below 5, LlamaIndex below 0.11). The unmerged refactoring branch ("completely remove theflow", "decouple VS DS from retriever") shows the maintainers know.

## Local and hardware story

**The lightest install of all the projects reviewed:** everything is embedded, with no services to run, and there is an arm64 image. Local models work through Ollama or llama.cpp ([docs](https://github.com/Cinnamon/kotaemon/blob/main/docs/local_model.md)). The defaults are still cloud-first: OpenAI or Gemini for the LLM, Cohere for reranking.

## Strengths

- Lowest footprint; embedded stores; runs on a laptop.
- The best citation experience: quotes anchored and highlighted in the PDF.
- Library and app split; pluggable index and reasoning types; question decomposition.

## Gaps

- Maintenance has stalled; no API.
- Hybrid search is concatenation; English-only full-text search; hosted reranker by default.
- No evaluation, no tracing.
- Fragile GraphRAG pinned to old versions.
- Components that depend on services outside the repository.
- Weak security defaults (`admin/admin`; a path-traversal fix arrived only in v0.11, [#755](https://github.com/Cinnamon/kotaemon/pull/755)).

## Lessons for open-rag-engine

- **Adopt:** quote-anchored citations highlighted in the source viewer, with visible relevance and low-relevance warnings; the library and app split; embedded default stores; question decomposition as a strategy.
- **Avoid:** UI concerns inside pipeline code; the UI framework standing in for an API; concatenation presented as fusion; hard-coded English analysis; stacking several frameworks; filters that enumerate every chunk ID.
- **Do differently:** API first, with the UI as one client among others; locate the cited span in code (exact, then fuzzy, then embedding alignment) instead of trusting the model to copy text exactly; few, loosely pinned core dependencies.

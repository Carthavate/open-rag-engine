# RAGFlow

> Snapshot: 2026-10-17. Repository facts from the GitHub API, source code, release notes and docs on that date.

| | |
|---|---|
| Repository | [infiniflow/ragflow](https://github.com/infiniflow/ragflow) |
| Licence | Apache-2.0. InfiniFlow also sells cloud plans and an enterprise edition ([ragflow.io](https://ragflow.io/)); the docs refer to an "open-source edition", so some features differ (which ones is unverified) |
| Popularity | About 92.4k stars, the most of any project in this research |
| Latest release | v1.0.0-rc2 (2026-10-16); latest stable v0.27.2 (2026-09-10) |
| Activity | **Very active:** about 2,800 commits in three months |
| Shape | An application server with a React web UI. Not usable as a library |

## v1.0 is a rewrite in Go

The [v1.0 release candidate](https://github.com/infiniflow/ragflow/releases/tag/v1.0.0-rc1) is "a comprehensive rewrite of RAGFlow in Go". The message queue moved from Redis to NATS; the upgrade from v0.27 is irreversible; deprecated API aliases were removed. In the first release candidate, the document parser ran on CPU only, the local code sandbox was gone, and team permissions were missing until rc2. The repository is now mostly Go, built with CGO against several native libraries; the Windows build is currently broken ([#21096](https://github.com/infiniflow/ragflow/issues/21096)), and the v1 Docker target is Linux x86-64 only, with macOS "temporarily not supported" ([docs](https://github.com/infiniflow/ragflow/blob/main/docs/develop/build_docker_image.mdx)).

## How it works

**Parsing** is RAGFlow's strength ([configuration](https://github.com/infiniflow/ragflow/blob/main/docs/guides/dataset/configuration.md)). Its own DeepDoc engine does OCR, layout analysis and table-structure recognition with ONNX models. Docling, MinerU, MonkeyOCR, Mistral OCR and others are alternatives, and any configured vision model can be used per format. Ingestion is a visual pipeline: parser, chunker, optional compiler, indexer.

**Chunking** offers templates per document type (general, Q&A, manual, table, paper, book, laws, presentation, email and more), heading-aware chunkers that keep the full heading path, parent-child chunks, a "table context window", and optional LLM enrichment with keywords and questions.

**Storage** goes through a `DocEngine` interface with Elasticsearch as the default and Infinity, OpenSearch, OceanBase and others as alternatives ([engine.go](https://github.com/infiniflow/ragflow/blob/main/internal/engine/engine.go)). Metadata lives in MySQL, files in a MinIO-compatible store.

**Retrieval** fuses full-text and vector scores with a **weighted sum, not reciprocal rank fusion** ([types.go](https://github.com/infiniflow/ragflow/blob/main/internal/engine/types/types.go)), which depends on the two scores being comparable. Reranker scores are blended into that sum rather than replacing it ([reranker.go](https://github.com/infiniflow/ragflow/blob/main/internal/service/nlp/reranker.go)). We found no MMR. It supports metadata filters, cross-language search by LLM query translation, and an agentic mode that decomposes questions.

**Graphs:** v0.27 deprecated GraphRAG and RAPTOR in the UI in favour of "knowledge compilation": LLM-generated graphs, trees, page indexes, mind maps, timelines and wikis ([overview](https://github.com/infiniflow/ragflow/blob/main/docs/guides/knowledge_compilation/overview.md)). Users objected to losing the knowledge-graph option ([#16337](https://github.com/infiniflow/ragflow/issues/16337)).

**Citations** use two mechanisms: a strict prompt makes the model emit `[ID:n]` markers, and a post-hoc pass embeds each answer sentence and attaches up to four matching chunks, relaxing its similarity threshold step by step ([citation.go](https://github.com/infiniflow/ragflow/blob/main/internal/service/citation.go)).

**Also:** canvas-based agent workflows, an MCP client and server, more than 50 data-source connectors, OpenAI-compatible endpoints, Langfuse tracing per tenant.

**Evaluation:** a manual retrieval-testing page in the UI. The benchmark folder measures only latency and throughput. **No answer-quality evaluation.**

**Access:** tenants and teams; resources shared as "only me" or "team". No document-level access control.

**Languages:** the UI is widely translated, but lexical retrieval is weak outside Chinese and English. A pull request notes that Slovak and Czech datasets "are effectively BM25-blind today" because the tokenizer fragments accented words ([#19013](https://github.com/infiniflow/ragflow/pull/19013)); mixed-language datasets fall back to English; DeepDoc OCR does not support Arabic ([#8691](https://github.com/infiniflow/ragflow/issues/8691)).

## Architecture

The storage interface is wide (about 30 methods) and untyped: it mixes chunk storage, metadata, raw SQL, scoring and PageRank, and passes chunks as generic maps. The service layer special-cases particular database engines. The result is powerful but hard to extend cleanly.

## Local and hardware story

The README recommends **4 CPU cores, 16 GB of RAM and 50 GB of disk just to start**, and the Elasticsearch container alone defaults to about 8 GB. Required services: Elasticsearch or Infinity, MySQL, an object store, Kvrocks and NATS. Embedding models are no longer bundled; the optional embedding service's comment says its default model "requires 25GB RAM/vRAM to load". Local LLMs work through Ollama or vLLM. **On a 16 GB laptop, RAGFlow uses the whole machine before a local LLM is even loaded.**

## Strengths

- The deepest parsing and structure-aware chunking among open-source peers, with many parser backends and vision-model fallbacks.
- Chunks can be inspected and edited in the UI.
- Two-stage citations that work even with weak models.
- Huge development velocity and test suite; OpenAI-compatible API and MCP.

## Gaps

- Heavy infrastructure; no laptop story.
- Constant churn: the Go rewrite, an irreversible upgrade, removed APIs, dropped macOS support and Helm chart, graph features replaced.
- Graph builds are slow and expensive: "GraphRAG will not finish… after 36 hours and $200" ([#7957](https://github.com/infiniflow/ragflow/issues/7957)).
- Parsing reliability: many reports of stuck or slow parsing; the new ingestor can be killed by large PDFs ([#20956](https://github.com/infiniflow/ragflow/issues/20956)).
- Deleted files keep being cited ([practitioner gaps](practitioner-gaps.md)).
- Score-based fusion, no MMR, no quality evaluation, weak non-CJK multilingual search.

## Lessons for open-rag-engine

- **Adopt:** structure-aware chunking with heading paths and parent sections; per-format parser choice with vision-model fallback; a retrieval-testing view; two-stage citations as a fallback for weak models; OpenAI-compatible and MCP interfaces.
- **Avoid:** a server stack as the default; weighted-sum fusion that depends on calibrated scores; a wide, untyped storage interface; tokenisation chosen per dataset with a silent English fallback.
- **Do differently:** embedded stores by default with server stores as optional adapters; narrow typed ports with declared capabilities; reciprocal rank fusion; per-element language detection with script-aware analysers; cost estimates and budgets for graph builds; a versioned API with a deprecation policy; an evaluation loop from day one.

# Haystack

> Snapshot: 2026-10-17. Repository facts from the GitHub API, source code and release notes on that date.

| | |
|---|---|
| Repository | [deepset-ai/haystack](https://github.com/deepset-ai/haystack), plus [haystack-core-integrations](https://github.com/deepset-ai/haystack-core-integrations) and [Hayhooks](https://github.com/deepset-ai/hayhooks) |
| Licence | Apache-2.0 for all three. No enterprise-licensed code in the open repositories |
| Backing | deepset GmbH, Berlin. Commercial layer: Haystack Enterprise Starter (support) and the Haystack Enterprise Platform (visual pipeline builder, deployment, RBAC, SSO, audit logs, guardrails, compliance), [product page](https://www.deepset.ai/products-and-services/haystack-enterprise-platform) |
| Popularity | About 26.8k stars |
| Latest release | [v3.4.0](https://github.com/deepset-ai/haystack/releases/tag/v3.4.0), 2026-10-15. 3.0 shipped in July 2026, then a minor release about every month |
| Activity | **Very active:** about 760 merged pull requests in three months; 108 integration packages |
| Shape | A Python **framework** (`pip install haystack-ai`). Serving through Hayhooks. No open-source UI for building pipelines |

## Component model

Haystack has the best-specified contracts of any project we looked at, and it is our architectural benchmark.

- **Components** are classes decorated with `@component` that expose `run(**inputs) -> dict`. Input sockets come from the typed parameters of `run`; outputs are declared with `@component.output_types`. Optional `run_async`. A symmetric lifecycle: `warm_up` acquires resources (clients and keys are created there, not in the constructor), `close` releases them. Serialisation through `to_dict` and `from_dict` ([custom components](https://docs.haystack.deepset.ai/docs/custom-components)).
- **Pipelines** are directed multigraphs with branches and bounded loops. `connect("a.out", "b.in")` **type-checks when the connection is made**, so a pipeline can be validated without running it. One `Pipeline` class offers `run`, `run_async` and streaming. Whole pipelines can be wrapped as one component, and breakpoints with snapshots allow pausing and resuming ([pipelines](https://docs.haystack.deepset.ai/docs/pipelines)).
- **Protocols** are deliberately small. A `DocumentStore` counts, filters, writes (with a duplicate policy) and deletes ([custom stores](https://docs.haystack.deepset.ai/docs/creating-custom-document-stores)). Newer retriever and embedder protocols let wrappers compose a retriever with an embedder.
- **Safety:** a `Secret` type for keys; pipeline loading restricted to an allow-list of trusted modules; mock generators and embedders for CI without keys.
- **Packaging:** integrations are separately versioned packages under one namespace. A written [breaking-change policy](https://docs.haystack.deepset.ai/docs/breaking-change-policy) limits major releases to one a year, with migration guides.

### Where the model leaks

- **Retrievers are bound to concrete store classes.** The in-memory BM25 retriever checks the store's exact type ([source](https://github.com/deepset-ai/haystack/blob/main/haystack/components/retrievers/in_memory/bm25_retriever.py)), because search is not part of the store protocol. Hybrid search therefore needs at least four components wired by hand, and a proposal for a store-agnostic hybrid component was closed in favour of a store-specific one ([#9210](https://github.com/deepset-ai/haystack/issues/9210)).
- Filter support varies by store ([#9138](https://github.com/deepset-ai/haystack/issues/9138)), and there is no multi-vector storage ([#13257](https://github.com/deepset-ai/haystack/issues/13257)).
- The synchronous `run` executes components one after another; parallel execution is still an open request ([#10941](https://github.com/deepset-ai/haystack/issues/10941)).

## Pipeline building blocks

- **Ingestion:** converters for PDF, office formats, HTML, Markdown, CSV, e-mail and JSON; a file-type router for mixed inputs. Layout analysis and OCR come from integrations (Docling, Unstructured, PaddleOCR, cloud services). A component sends page images to a vision model for OCR, including tables.
- **Chunking:** many splitters (recursive, hierarchical with auto-merging retrieval, semantic, Markdown headers, code, CSV).
- **Retrieval:** in-memory BM25 (with a new per-character tokenizer for Chinese, Japanese and Korean whose precision is still debated, [#12867](https://github.com/deepset-ai/haystack/issues/12867)), store-specific dense and sparse retrievers, a joiner with reciprocal rank fusion and distribution-based score fusion ([source](https://github.com/deepset-ai/haystack/blob/main/haystack/components/joiners/document_joiner.py)), multi-query retrievers ([QueryExpander](https://docs.haystack.deepset.ai/docs/queryexpander)), sentence-window retrieval.
- **Reranking:** cross-encoders, MMR diversity ranking, LLM ranking, lost-in-the-middle reordering.
- **Citations:** prompting plus a regex that marks which documents were referenced ([AnswerBuilder](https://github.com/deepset-ai/haystack/blob/main/haystack/components/builders/answer_builder.py)). Document-level only: no spans, no check that the source supports the claim.
- **Agents:** the strongest area in 3.x. An `Agent` with hooks before and after model and tool calls, runtime tool selection, human-in-the-loop, context compaction and token budgets ([v3.0](https://github.com/deepset-ai/haystack/releases/tag/v3.0.0), [v3.2](https://github.com/deepset-ai/haystack/releases/tag/v3.2.0)).
- **GraphRAG:** not in core. Graph database integrations (FalkorDB, ArangoDB and others) provide storage and query retrievers, but no entity extraction or communities.
- **Evaluation:** faithfulness and context relevance (LLM-judged), semantic answer similarity, exact match, and document-level MAP, MRR, nDCG and recall ([evaluation](https://docs.haystack.deepset.ai/docs/evaluation)); Ragas and DeepEval integrations.
- **Observability:** a tracer abstraction; OpenTelemetry, Datadog, Langfuse and Weave via integrations; tracing is opt-in since 3.0.
- **Access control:** none in open source beyond metadata filters. Hayhooks has no built-in authentication ([production guide](https://github.com/deepset-ai/hayhooks/blob/main/docs/guides/production-best-practices.md)); RBAC and SSO are in the commercial platform.

## Hayhooks

Serves pipelines over REST endpoints generated from type hints, OpenAI-compatible chat endpoints with streaming, an MCP server and Agent2Agent. Version 2.0 added durable execution: checkpoints in Redis, restart recovery, idempotency keys and streams that clients can reattach to ([v2.0.0](https://github.com/deepset-ai/hayhooks/releases/tag/v2.0.0)).

## Local and hardware story

The core is light (Jinja2, networkx, pydantic, the OpenAI client) and runs fully on CPU with Ollama, llama.cpp or transformers integrations and local embedders. No infrastructure is required: the in-memory store can persist to disk. Two caveats for local-first users: after 3.0, a local stack needs several integration packages, and **usage telemetry is a core dependency and on by default** ([telemetry](https://docs.haystack.deepset.ai/docs/telemetry)).

## Strengths

- Typed sockets, connection-time validation, small protocols and a symmetric lifecycle.
- Safe serialisation, a written breaking-change policy, a huge maintained integration ecosystem.
- First-class async and streaming, mature agent hooks, durable serving.

## Gaps

- **Churn:** 2.0 was a rewrite; 3.0 removed components and moved 30 out of core, and **changed how document IDs are computed**, which forces re-indexing of persistent stores ([migration guide](https://github.com/deepset-ai/haystack/blob/main/MIGRATION.md)).
- Store-bound retrievers; hybrid search wired by hand.
- No GraphRAG, no open-source UI, no authentication in serving.
- Citations are document-level regex matches.
- Multilingual keyword search is still being worked out.

## Lessons for open-rag-engine

- **Adopt:** typed component contracts validated before anything runs (our capability checks at startup); small protocols; a warm-up and close lifecycle; a secret type; an allow-list for anything loaded from configuration; mock model adapters for CI without keys; hook points as the seam for agentic behaviour; separately versioned adapter packages; a written breaking-change policy.
- **Avoid:** retrievers bound to a store class. Our retrievers depend on capability ports (`LexicalIndex`, `VectorIndex`, `GraphStore`), and fusion is one backend-agnostic slot, so hybrid search, multi-query and MMR work on any adapter. Avoid telemetry on by default, and ID schemes that change silently.
- **Do differently:** ship the full default pipeline ready to run (hybrid retrieval, multi-query, MMR, reranking, verified span-level citations), ship GraphRAG and multimodal ingestion in the default install, and include API-key authentication with a data model ready for collection-level access control.

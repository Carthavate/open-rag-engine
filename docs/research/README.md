# Research: the open-source RAG landscape

> Snapshot: 2026-10-17. Projects in this space change monthly, so every claim links to its source, and each page states its snapshot date.

Before designing open-rag-engine we studied the engines people actually use, what they do well, and where they fall short. We looked at five projects in depth (RAGFlow, R2R, LightRAG, Haystack, Kotaemon), Microsoft GraphRAG and its family, about twenty newer or smaller engines, the evaluation ecosystem, the building blocks (parsers, models, runtimes), and two years of practitioner complaints. Facts were checked against repositories, source code, release notes, model cards and papers, mostly through the GitHub and Hugging Face APIs.

## Pages

| Page | Covers |
|------|--------|
| [RAGFlow](ragflow.md) | The most popular open-source RAG engine; deep parsing, heavy infrastructure |
| [R2R](r2r.md) | The most complete RAG server of its generation, now abandoned |
| [LightRAG](lightrag.md) | The leading open-source GraphRAG product |
| [Haystack](haystack.md) | The best-specified component framework |
| [Kotaemon](kotaemon.md) | The lightest install and the best citation experience, now stalled |
| [Microsoft GraphRAG and the graph-RAG family](graphrag-family.md) | GraphRAG, LazyGraphRAG, HippoRAG 2, NER-built graphs, and when graphs help |
| [RAG inside larger apps](app-peers.md) | Onyx, AnythingLLM, Dify, Open WebUI |
| [Frameworks and small libraries](frameworks.md) | LlamaIndex, txtai, RAGLite |
| [Other engines worth knowing](other-engines.md) | WeKnora, PrivateGPT, Quivr, Khoj, UltraRAG, EdgeQuake and more |
| [Building blocks](building-blocks.md) | Parsers, visual retrieval, embedders, rerankers, small LLMs, runtimes, licences |
| [Evaluation](evaluation.md) | Frameworks, small judges, judge reliability, citation evaluation, benchmarks |
| [Practitioner gaps](practitioner-gaps.md) | What users repeatedly report as missing or broken |

## The five main projects at a glance

| | [RAGFlow](ragflow.md) | [R2R](r2r.md) | [LightRAG](lightrag.md) | [Haystack](haystack.md) | [Kotaemon](kotaemon.md) | **open-rag-engine (target)** |
|---|---|---|---|---|---|---|
| Licence | Apache-2.0, plus paid editions | MIT | MIT | Apache-2.0, plus a paid platform | Apache-2.0 | AGPL-3.0 |
| State, October 2026 | Very active; v1.0 is a Go rewrite in release candidate | **Abandoned** since November 2025, unpatched security reports | Very active | Very active (3.4) | **Stalled** since May 2026 | Design phase |
| Shape | App server and UI | Server, SDKs, dashboard | Library, server, UI | Framework, serving add-on | Gradio app and library, no API | Library, API server, UI |
| Runs well on a 16 GB CPU laptop | No: 16 GB is its minimum before any LLM | With local presets; PostgreSQL required | Retrieval yes; graph extraction needs a 30B-class model | Yes | Yes, the lightest | **Design target** |
| Hybrid fusion | Weighted score sum | RRF in SQL | Graph plus vectors, no BM25 | RRF or score fusion, wired by hand | Concatenation | RRF, any retriever |
| Keyword search beyond English | Weak outside Chinese and English | English-only stemming | n/a | CJK tokenizer just added | English stemmer | Per-language analysis, any script |
| Reranking and MMR | Reranker blended into scores; no MMR | Optional, falls back silently | Optional reranker | Both | Hosted reranker by default; MMR via LlamaIndex | Both, local by default |
| GraphRAG | Replaced by LLM "knowledge compilation" | LLM extraction, Leiden communities | Core feature, no communities | Not in core | Old pinned versions, fragile locally | Tiered: NER graph on CPU, LLM optional, lazy summaries |
| Multimodal documents | **Strongest:** own layout, OCR and table engine, many parsers | Hosted vision models and OCR | Via merged RAG-Anything | Via integrations | Docling and PaddleOCR optional | Per-page routing, multilingual OCR, figures described |
| Citations | Model markers plus embedding backfill | Character spans | Yes | Document-level regex | **Best UX:** quotes highlighted in the PDF | Verified, page and region exact |
| Evaluation | Manual retrieval testing only | None built in | Ragas hook | Evaluators, no harness | None | Built in, per stage, CI gate |
| Access control | Tenants and teams | Users and collections | Workspaces | None in open source | Private and public collections | Seam from day one, filters inside every search |
| Infrastructure | Elasticsearch, MySQL, object store, Kvrocks, NATS | PostgreSQL, up to 14 services | Embedded (not for production) or PostgreSQL | None | None | **None:** one data directory |

## What we learned

1. **No maintained project combines what we want.** RAGFlow has the depth but needs a server. Kotaemon has the footprint and the citations but weak retrieval, and has stalled. R2R had the product shape and is abandoned. Haystack is an excellent framework that leaves the product to you. LightRAG's graph needs a model a laptop can't run. Nobody ships a built-in evaluation loop.
2. **The laptop is an unserved target.** The popular engines either need server infrastructure or fall back to weak retrieval to stay light. [RAGLite](frameworks.md#raglite) shows a 4B model, a multilingual embedder and an embedded database are enough on a CPU.
3. **Keyword search outside English is broken almost everywhere:** English stemmers hard-coded in R2R and Kotaemon, whitespace tokenisation in Open WebUI, English fallbacks in RAGFlow.
4. **LLM-built knowledge graphs are a cost trap on small models**, and their published gains shrink under unbiased evaluation. Graphs built from named entities with no LLM now match them on multi-hop benchmarks ([graph research](graphrag-family.md)).
5. **Evaluation is the most visible gap.** Users ask "how did you evaluate this?" and get no answer; the best-known framework has stalled; small calibrated checkers make faithfulness measurable on a CPU ([evaluation](evaluation.md)).
6. **Deletion, updates and model changes are where engines break in production** ([practitioner gaps](practitioner-gaps.md)).
7. **Projects die and licences drift.** Four engines and tools were archived or orphaned in two years; several popular ones are not OSI-licensed. A small core with few dependencies and an AGPL licence is our defence.

## Where open-rag-engine stands out

| Differentiator | Why it matters | Where it is designed |
|----------------|----------------|----------------------|
| **Laptop-first, zero infrastructure:** one process, one data directory, CPU defaults | The audience the big engines can't serve | [Containers](../architecture/02-containers.md), QR-RES, QR-LAT |
| **Any-language hybrid retrieval:** per-element language detection, script-aware BM25, multilingual models, cross-language query variants | The near-universal weak spot | FR-RET-01, FR-RET-06, QR-I18N |
| **Verified, page-exact citations:** enforced format, support checking, abstention | Citations users can trust, even from small models | [ADR-0005](../adr/0005-verified-citations.md) |
| **GraphRAG that works on a CPU:** NER graph by default, LLM extraction optional, lazy summaries, fused rather than replacing | Graph benefits without the cost trap | [Ingestion](../architecture/07-ingestion.md#graph-enrichment) |
| **Evaluation built in:** per-stage metrics, calibrated judges, CI gate | Every change comes with numbers | [Evaluation loop](../architecture/09-evaluation.md) |
| **Deletion-correct, versioned indexing:** immutable versions, tombstones, index generations with rollback | Where production systems break | [ADR-0004](../adr/0004-index-generations.md) |
| **Clean architecture:** ports and adapters with enforced rules and contract tests | Long life with two maintainers; easy to review and extend | [ADR-0002](../adr/0002-ports-and-adapters.md) |

## Risks we take on

Honest about what could go wrong:

- **Scope.** Everything above is a lot for two part-time maintainers. The MoSCoW priorities in the [requirements](../requirements/02-functional.md) and the spikes are how we keep it shippable.
- **CPU latency.** Time to first token with a local model on a CPU may disappoint (QR-LAT-02). Spike S-1 decides the default model, and retrieval-only mode stays fully useful without an LLM.
- **Multilingual verification.** The best small support checkers are mostly English-trained (open question Q-06).
- **Graph value.** GraphRAG must earn its place on our own multi-hop and global slices (QR-QUAL-06), or it stays off by default.
- **Parsing on CPU.** The best parsers are small vision models with no published CPU speeds (spike S-2).

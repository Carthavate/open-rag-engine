# Architecture

> **Status:** draft, started 2026-10-17. It is being written alongside the [research](../research/README.md) and ahead of the requirements, so for now it traces to the *architecture drivers* below. When `docs/requirements/` lands, each driver will link to the requirement IDs it covers.

open-rag-engine is a retrieval-augmented generation engine that runs on a laptop without a GPU, reads documents in any language and format, answers with citations you can check, and measures its own quality. This folder describes how it is built.

## Views

| # | View | Question it answers |
|---|------|---------------------|
| 1 | [System context](01-context.md) | Who uses it, and which external systems does it talk to? |
| 2 | [Containers](02-containers.md) | Which processes and data stores make up the system? |
| 3 | [Components](03-components.md) | What is inside the API server and the worker? |
| 4 | [Layers and dependency rules](04-layers.md) | Which code may depend on which, and how is that enforced? |
| 5 | [Ports and interfaces](05-interfaces.md) | What are the contracts between the core and its adapters? |
| 6 | [Domain model](06-domain-model.md) | What are documents, chunks, index generations and citations, and which invariants always hold? |
| 7 | [Ingestion pipeline](07-ingestion.md) | How does a file become searchable chunks with provenance, cheaply on a CPU? |
| 8 | [Query pipeline](08-query.md) | How does a question become a verified, cited answer? |
| 9 | [Evaluation loop](09-evaluation.md) | How do we know a change made it better, and where it got worse? |
| 10 | Deployment and runtime | *Planned, with the deployment ADR* |

Views 1 to 3 follow the [C4 model](https://c4model.com/). The diagrams are Mermaid flowcharts in C4 notation: dark blue for people, blue for our system and its parts, grey for external systems, cylinders for data. We use flowcharts rather than Mermaid's own C4 syntax because the latter lays out poorly on GitHub.

## Architecture drivers

These are the decisions from the scoping session on 2026-10-17 that shape the structure most. Every major design choice traces back to at least one of them.

| ID | Driver | What it forces in the design |
|----|--------|------------------------------|
| D-01 | Ships as a library, an API server and a web UI. | The core is a plain library with no web dependencies. The server, the CLI and the UI are thin layers over the same application services. |
| D-02 | Runs fully local on a 16 GB laptop without a GPU. A GPU, or a hosted LLM with the user's own key, is optional. | The default profile keeps all data in one local directory and needs no database server. Every model sits behind a port, so moving to a GPU or a hosted model is a configuration change. Heavy stages (layout parsing, OCR, graph extraction) are optional, budgeted, and run in the background. |
| D-03 | Any document and query language. | Nothing English-only on the default path. Language is detected per element, lexical analysis is per language with a Unicode fallback, the default models are multilingual, and so are the evaluation sets. |
| D-04 | GraphRAG in v1. | The knowledge graph is one more index next to the lexical and vector indexes. It is built incrementally from chunks, and every graph result carries chunk provenance, so it is cited like any other source. |
| D-05 | Multimodal documents in v1: layout, tables, figures, scanned pages. | One structured document model with provenance on every element (page and bounding box). Tables and figures are first-class elements, not text flattened beyond recognition. |
| D-06 | Grounded answers with citations that can be checked. | Provenance travels from parsing all the way to the answer. A verification stage checks every citation, and the engine abstains when the evidence is missing. |
| D-07 | Evaluation is built in. | Evaluation runs the production query pipeline, not a copy of it, and every run records a fingerprint that makes it reproducible. |
| D-08 | Every answer can be explained. | Each pipeline stage emits a trace span with its inputs, outputs and scores. |
| D-09 | Agentic RAG and multi-user permissions are out of v1 but must fit later without a rewrite. | A *query strategy* seam where multi-step retrieval plugs in. A principal and access fields on every request and every stored record from day one, enforced by an access-policy port that allows everything in v1. |
| D-10 | Free and open: AGPL-3.0, no paid service required. | Every default adapter is free to run. Paid services only ever appear as optional adapters. |

## Principles

1. **Dependencies point inward.** The domain knows nothing about databases, model runtimes or HTTP. It defines ports, and adapters implement them ([layers](04-layers.md)).
2. **Pipelines are fixed sequences of typed slots.** You choose which implementation fills each slot and how it is configured; you don't rewire the pipeline. That keeps every configuration testable and comparable in evaluation, and keeps traces structurally identical across runs. Multi-step behaviour goes through a query strategy, not through ad-hoc pipeline graphs. *Trade-off: less freedom than Haystack-style pipeline graphs. This gets its own ADR.*
3. **Configuration is declarative, validated at startup, and immutable at runtime.** Changing it creates a new engine instance and, if it affects indexing, a new [index generation](06-domain-model.md#index-generations).
4. **Provenance is never dropped.** Every derived artefact (element, chunk, vector, entity, community summary, answer statement) points back to source spans.
5. **One code path for production and evaluation.**
6. **Degrade visibly, never silently.** When an optional stage or model is unavailable, the pipeline skips it, says so in the trace, and still answers or abstains.
7. **Ingestion is idempotent and resumable**, keyed by content hashes.
8. **Measure first.** Every change to retrieval or generation comes with evaluation numbers.

## For readers coming from AUTOSAR

The structure maps closely onto concepts an automotive software architect already uses. The analogy is structural only: there is no code generation, and the wiring happens when the process starts.

| AUTOSAR | open-rag-engine |
|---------|-----------------|
| Software component (SWC) | A component that fills a pipeline slot, such as a reranker |
| Client-server port interface | A port: a typed request/response interface owned by the core |
| Sender-receiver port interface | A domain event, such as `DocumentIndexed`, delivered to subscribers |
| RTE | The composition root, which binds every port to an adapter from the configuration at startup |
| Basic software | Infrastructure adapters: storage, model runtimes, file system, network |
| ECU configuration (ARXML) | The engine configuration file, schema-validated, with profiles |
| Variant handling | Profiles (`laptop`, `gpu`, `server`) and optional install extras for heavy adapters |
| Port compatibility checks at configuration time | Capability checks at startup: adapters declare what they can do, and the engine refuses an inconsistent configuration |

## Decisions this draft leaves open

The structure above deliberately names no technologies. Each of these gets an ADR in `docs/adr/`:

- Language and framework for the core, the API server and the web UI
- Metadata store, lexical index and vector index, for the laptop and server profiles
- Graph store and the GraphRAG method (extraction, entity resolution, communities)
- Document parsing stack (layout, OCR, tables, figures)
- Default embedding and reranker models
- LLM backends (local runtimes, and hosted providers through the user's own key)
- API style (REST, streaming, MCP)
- Job queue and deployment packaging
- The architecture-level choices made in this draft: ports and adapters with enforced import rules, fixed-slot pipelines, index generations

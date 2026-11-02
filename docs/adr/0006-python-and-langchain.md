# ADR-0006: Python and LangChain for the first engine

- **Status:** Proposed
- **Date:** 2026-11-02
- **Deciders:** Wadi, Ghassen
- **Requirements:** C-01, C-02, C-03, C-05 (and drivers D-02, D-07, D-08, D-10)

## Context and problem

The architecture leaves the language and framework open. We want a working engine soon, built with the techniques from the RAG course we just finished: chunking, hybrid search, reciprocal rank fusion, multi-query, reranking, conversational rewriting and cited answers. What do we build it with?

## Decision drivers

- Two maintainers, part-time (C-05): prefer mature libraries over custom code.
- Everything free and local by default (C-03, D-02, D-10); licences compatible with AGPL-3.0 (C-01, C-02).
- We already know one framework well from the course.
- Pipelines must stay fixed and traceable (ADR-0003, D-08) and evaluation must use the production path (D-07).

## Considered options

1. **Own core in Python**, with our own ports, and libraries only inside adapters (as ADR-0002 describes).
2. **Python on LangChain**, using its interfaces as our ports and its components where they fit.
3. **Haystack** or **LlamaIndex**.

## Decision

Option 2: **Python 3.12 on LangChain 1.x**, because it is the stack we learned and it covers almost every course technique out of the box.

How it fits the earlier records:

- **Ports (ADR-0002).** LangChain's abstract interfaces are the ports: `Embeddings`, `VectorStore`, `BaseRetriever`, `BaseChatModel`, `TextSplitter` and `BaseCrossEncoder`. Adapters are LangChain integrations: Chroma, sentence-transformers through `langchain-huggingface`, Ollama through `langchain-ollama`. The composition root (`engine.py` and `factory.py`) is the only place that picks concrete ones.
- **Fixed slots (ADR-0003).** We don't hand the query to a free-form LangChain chain. `RetrievalPipeline` runs a fixed sequence of slots: query expansion, vector search, keyword search, fusion, rerank. Each slot is filled from configuration and records a trace. It is also exposed as a LangChain `BaseRetriever`, so it still composes with LangChain chains.
- **Fusion stays ours.** The formula is the same as `EnsembleRetriever`'s weighted reciprocal rank fusion, but we keep the fused scores so they appear in the trace (D-08).

### Consequences

- **Good:**
  - Every course technique maps to a library component we already understand.
  - Swapping a model or store is a configuration change behind an existing LangChain interface.
- **Bad:**
  - We inherit LangChain's churn. `langchain-community` and `langchain-experimental` are being sunset. We use them only for `BM25Retriever`, `HuggingFaceCrossEncoder`, `PyPDFLoader` and `SemanticChunker`.
    - **Mitigation:** those imports are confined to four adapter modules, so each can be replaced by a small own implementation behind the same interface.
    - Versions are pinned to a major range in `pyproject.toml`.
- **Bad:**
  - LangChain types (`Document`, messages) appear in our core, so the core is not framework-free as ADR-0002 intended.
  - **We accept this for v0.** If it starts to hurt, a later ADR can introduce our own domain types at the boundary.

### Confirmation

`tests/test_architecture.py` fails if any module other than the listed adapters imports `langchain_community` or `langchain_experimental`.

## Pros and cons of the options

### Own core in Python

- Good, because it is the cleanest reading of ADR-0002 and has no framework churn.
- Bad, because we would rewrite splitters, loaders, retriever and model wrappers that already exist, which is a poor use of two part-time maintainers.

### Python on LangChain

- Good, because it is the framework we learned the techniques in, and it is mature and widely used.
- Bad, because of the churn and the deprecated community packages described above.

### Haystack or LlamaIndex

- Good, because both are capable. Haystack's typed pipelines are close to our fixed-slot idea.
- Bad, because we would be learning a second framework while also building the engine.

## More information

- [Framework research](../research/frameworks.md), [ADR-0002](0002-ports-and-adapters.md), [ADR-0003](0003-fixed-slot-pipelines.md)
- Default models, all permissively licensed and CPU-friendly:
  - `intfloat/multilingual-e5-small` (MIT) for embeddings.
  - `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (Apache-2.0) for reranking.
  - `qwen3:4b-instruct-2507` (Apache-2.0) through Ollama for answers.
  - The models ADR (spike S-4) can replace them with measured choices.

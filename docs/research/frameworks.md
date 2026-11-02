# Frameworks and small libraries

> Snapshot: 2026-10-17. Short profiles of three Python projects that sit next to the engines we compare.

## LlamaIndex

[run-llama/llama_index](https://github.com/run-llama/llama_index), MIT, about 52.5k stars, latest [v0.14.25](https://github.com/run-llama/llama_index/releases) (2026-09-21).

- **Activity is slowing:** about 105 commits in the last three months against about 372 a year earlier. The README says the company's "primary focus has shifted towards LlamaParse", its paid, credit-based parsing service ([pricing](https://developers.llamaindex.ai/llamaparse/general/pricing/)). A free Rust parser, [LiteParse](https://github.com/run-llama/liteparse) (Apache-2.0), exists.
- **Abstractions:** documents and nodes, ingestion transformations, indexes and retrievers, node post-processors (rerankers), query engines, event-driven workflows, a property-graph index for GraphRAG, and evaluation modules, across more than 300 integration packages. Its fusion retriever generates four queries by default and fuses them with reciprocal rank or score-based modes ([source](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/retrievers/fusion_retriever.py)).
- **Weakness:** the global settings object falls back to OpenAI for the default LLM and embedder ([source](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/settings.py)), and the API surface is broad and sprawling.
- **Lesson:** good vocabulary to borrow. Never default to a hosted model. Be wary of building on a framework whose owner now treats it as secondary to a paid product.

## txtai

[neuml/txtai](https://github.com/neuml/txtai), Apache-2.0, about 13.0k stars, latest [v9.14.0](https://github.com/neuml/txtai/releases) (2026-10-06), roughly monthly releases. One person wrote almost all of the code.

- **Core idea:** one "embeddings database" combining a dense index (Faiss by default, many alternatives), sparse BM25 scoring, SQL content storage and an automatically built semantic graph.
- **Fusion chosen by score type** ([source](https://github.com/neuml/txtai/blob/master/src/python/txtai/embeddings/search/hybrid.py)): a log-odds combination for normalised BM25, a convex combination for normalised scores, reciprocal rank fusion otherwise.
- Also: a RAG pipeline, graph traversal, local LLMs through transformers, llama.cpp or LiteLLM, workflows, agents, and an API and MCP server configured in YAML.
- **Strengths:** genuinely local and light; backends pluggable by import path.
- **Weaknesses:** a monolithic facade rather than layered interfaces; citations shown in notebooks, not as a first-class output; no access control; a high bus factor.
- **Lesson:** pick the fusion method according to whether scores are calibrated; allow adapters to be named by import path.

## RAGLite

[superlinear-ai/raglite](https://github.com/superlinear-ai/raglite), MPL-2.0, about 1.2k stars, latest [v1.1.1](https://github.com/superlinear-ai/raglite/releases) (2026-05-18). Activity is slowing, with one main maintainer.

- **A very small functional API:** insert documents, hybrid, keyword and vector search, rerank, answer, and evaluate, all driven by one frozen configuration object ([source](https://github.com/superlinear-ai/raglite/blob/main/src/raglite/__init__.py)).
- **Storage:** one DuckDB file (full-text and vector search) or PostgreSQL, fused with reciprocal rank fusion.
- **Chunking:** sentence and semantic chunking solved as an integer program, late chunking, contextual chunk headings.
- **CPU-aware defaults** ([source](https://github.com/superlinear-ai/raglite/blob/main/src/raglite/_config.py)): Qwen3-4B Q4 on a CPU, or Qwen3-8B with GPU offload, through llama.cpp; bge-m3 embeddings; **rerankers chosen per language** (an English model for English, a multilingual one otherwise); deliberately no PyTorch and no LangChain.
- **Gaps:** no GraphRAG, no access control, little multimodal support.
- **Lesson:** the closest existing template for our 16 GB CPU target. Copy the hardware-aware default selection, the per-language model map and the single-file embedded database.

## What this tells us

- **Frameworks leave the product to you.** LlamaIndex and Haystack give building blocks; neither ships a ready-to-run engine with GraphRAG, multimodal ingestion, verified citations, evaluation and a UI in one install.
- **Small libraries prove the laptop target is realistic.** RAGLite already runs a 4B model, a multilingual embedder and an embedded database on a CPU; txtai shows hybrid search and a graph in one local store.
- **Per-language model choice is a cheap win.** RAGLite's language-keyed reranker map is the simplest form of assumption A-04's fallback.

# LightRAG

> Snapshot: 2026-10-17. Repository statistics from the GitHub API on that date.

| | |
|---|---|
| Repository | [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) |
| Licence | MIT |
| Backing | HKU Data Intelligence Lab; paper [arXiv 2410.05779](https://arxiv.org/abs/2410.05779) (EMNLP 2025) |
| Popularity | About 40.2k stars |
| Latest release | [v1.5.7](https://github.com/HKUDS/LightRAG/releases/tag/v1.5.7), 2026-09-02 |
| Activity | **Very active:** 419 merged pull requests and 176 new issues in the three months to 2026-10-17, including security fixes |
| Shape | Python library plus an API server and web UI |

## How it works

**Indexing.** Documents are cut into chunks of 1,200 tokens by default. One LLM call per chunk extracts entities (name, type, description) and relations (source, target, keywords, description) in a delimited text format, capped per response; a JSON mode trades latency for reliability. One extra "gleaning" pass is on by default, so up to two calls per chunk ([prompt](https://github.com/HKUDS/LightRAG/blob/main/lightrag/prompt.py), [constants](https://github.com/HKUDS/LightRAG/blob/main/lightrag/constants.py)).

**Entity resolution** is an exact match on the normalised name. Descriptions of merged entities are concatenated and summarised by the LLM once they grow long. Fuzzy and semantic merging has been requested since April 2025 ([#1323](https://github.com/HKUDS/LightRAG/issues/1323)) and is still an open, opt-in pull request ([#3766](https://github.com/HKUDS/LightRAG/pull/3766)).

**No communities.** Unlike Microsoft GraphRAG, LightRAG does not cluster the graph or write community reports. This is the simplification that makes incremental updates cheap.

**Querying.** One LLM call extracts low-level keywords (entities) and high-level keywords (relations). Modes: `local` (entity search and neighbourhood), `global` (relation search), `hybrid` (both), `naive` (chunk vectors only) and `mix`, the default, which combines the graph with chunk vectors. A reranker is recommended. Default context budgets are large: up to 30,000 tokens in total.

**Updates.** New documents merge into the graph without a global recompute. Deletion with graph regeneration from cached extraction results arrived in August 2025.

## Product surface

Four storage roles (key-value, vector, graph, document status), each with many backends: JSON files, NanoVectorDB and NetworkX by default, plus PostgreSQL, Redis, MongoDB, Milvus, Qdrant, Faiss, Neo4j, Memgraph, Apache AGE and OpenSearch ([API server docs](https://github.com/HKUDS/LightRAG/blob/main/docs/LightRAG-API-Server.md)). The defaults are in memory and documented as unsuitable for production; PostgreSQL is recommended. On an 8k-node graph, plain PostgreSQL tables answered about 28 times faster than Apache AGE at the median ([#3103](https://github.com/HKUDS/LightRAG/pull/3103)).

The server provides a REST API, a web UI with document management and graph visualisation, an Ollama-compatible chat endpoint, citations, Ragas evaluation and Langfuse tracing. Multimodal processing from RAG-Anything (images, tables and equations as graph nodes, parsed with MinerU, Docling or a native parser) was merged into the core in 2026.

## Cost, and what happens with small models

| Measurement | Indexing | Per query |
|-------------|----------|-----------|
| [GraphRAG-Bench](https://arxiv.org/abs/2506.05690) (ICLR 2026), one book of about 56k tokens | About 474k tokens, 710 s: the slowest method tested | About 100k tokens (vanilla RAG: 879) |
| [HippoRAG 2 paper](https://arxiv.org/abs/2502.14802), MuSiQue, 11,656 passages | 68.5M input and 18.3M output tokens, 235 minutes | 13.3 s (dense retrieval: 0.3 s) |
| [BM25 Wins at Scale](https://arxiv.org/abs/2607.26497) (July 2026) | Completed only up to about 3M corpus tokens; full-corpus build extrapolated at about 102B tokens | |

The project's own guidance is that local extraction needs **a model of about 30B parameters** (the README names Qwen3-30B-A3B; a maintainer wrote in 2024 that "you need a model of 32B or above to get some effect", [#512](https://github.com/HKUDS/LightRAG/issues/512)). At Q4 quantisation that is about 19 GB: it does not fit a 16 GB laptop. With small models the graph degrades sharply. The docs' own low-memory example with a 2B model found about 197 entities but only 19 relations ([docs](https://github.com/HKUDS/LightRAG/blob/main/docs/ProgramingWithCore.md)). In the [MiniRAG paper](https://arxiv.org/abs/2501.06713), LightRAG's accuracy on MultiHop-RAG fell from 64.91% to 19–27% with 1.5–4B models. Common failure reports: no entities extracted ([#30](https://github.com/HKUDS/LightRAG/issues/30)), malformed records ([#2252](https://github.com/HKUDS/LightRAG/issues/2252)), timeouts and endless output.

## Quality evidence

The paper reports win rates of 60–85% against naive RAG, judged pairwise by an LLM. A [bias-corrected re-evaluation](https://arxiv.org/abs/2506.06331) found those numbers inflated: on one dataset the win rate against naive RAG fell from 66.7% to 39.1%, swapping answer order alone moved results by more than 30 points, and a 25-token difference in answer length shifted the win rate by more than 50 points. On reference-based multi-hop QA, LightRAG roughly ties vanilla top-5 RAG (HotpotQA 59.5 vs 58.6; 2Wiki 39.0 vs 43.0; MuSiQue 28.6 vs 29.6), while HippoRAG 2 beats both ([LinearRAG](https://arxiv.org/abs/2510.10114), [EHRAG](https://arxiv.org/abs/2604.17458)).

## Strengths

- The most complete open-source GraphRAG product: server, UI, many storage backends, deletion, multimodal input, citations, evaluation hooks and tracing.
- Very active, MIT-licensed, works with Ollama.
- Incremental updates without community recomputation.

## Gaps

- Extraction is token-hungry and needs a 30B-class model; it does not work as designed on a 16 GB laptop.
- Entity resolution is exact-match only.
- Default query contexts of up to 30k tokens are far beyond what a CPU can prefill quickly.
- In-memory defaults; production needs PostgreSQL or several services.
- Published gains shrink under unbiased evaluation.
- Practitioners report deletion and cache-cleanup bugs ([#985](https://github.com/HKUDS/LightRAG/issues/985), [#3833](https://github.com/HKUDS/LightRAG/issues/3833)) and that changing the embedding model requires clearing vector storage.

## Lessons for open-rag-engine

- **Adopt** the product surface: query modes, a storage abstraction per role, deletion through an extraction cache, graph visualisation.
- **Do differently:** cheap extraction tiers that work on a CPU, real entity resolution, and query contexts sized for CPU prefill (a few thousand tokens, not 30,000).
- **Measure honestly:** reference-based metrics and order-swapped judging, never unchecked pairwise win rates.

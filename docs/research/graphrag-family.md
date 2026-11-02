# Microsoft GraphRAG and the graph-RAG family

> Snapshot: 2026-10-17. Repository statistics from the GitHub API on that date. Time and cost estimates marked as ours are back-of-envelope, not measurements.

## Microsoft GraphRAG

| | |
|---|---|
| Repository | [microsoft/graphrag](https://github.com/microsoft/graphrag) |
| Licence | MIT |
| Popularity | About 36.4k stars |
| Latest release | [v3.3.0](https://github.com/microsoft/graphrag/releases/tag/v3.3.0), 2026-10-08 |
| Activity | **Maintenance mode since 2026-08-14:** the README says it will not accept new pull requests or features, only bug, dependency and security fixes ([#2486](https://github.com/microsoft/graphrag/pull/2486)) |
| Shape | Python library and CLI. No supported server or UI |

### How it works

**Standard indexing** ([dataflow](https://github.com/microsoft/graphrag/blob/main/docs/index/default_dataflow.md)): 1,200-token chunks; an LLM extracts entities and relationships per chunk; entities with the same title and type are merged and their descriptions summarised; the graph is clustered hierarchically with Leiden; **an LLM writes a report for every community at every level**. Smaller chunks extract more: the paper found almost twice as many entity references at 600 tokens as at 2,400 ([Edge et al.](https://arxiv.org/abs/2404.16130)).

**FastGraphRAG** ([methods](https://github.com/microsoft/graphrag/blob/main/docs/index/methods.md)) replaces LLM extraction with noun phrases (NLTK or regex, "primarily suitable for English", or spaCy) and chunk co-occurrence. The LLM writes only the community reports. Microsoft estimates extraction at about 75% of indexing cost.

**Querying:** *local* search (entities, relations, reports and chunks); *global* search (map-reduce over community reports; dynamic community selection cuts its cost by about 77%, [blog](https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/)); *DRIFT* (start from the top reports, generate follow-up questions, refine with local search, [blog](https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/)); and a plain vector baseline.

**Updates:** `graphrag update` indexes new documents separately and appends their communities. There is no full rebuild, but also no re-clustering, so community structure drifts as the corpus grows (our reading of [the code](https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/index/update/communities.py)).

**Storage:** Parquet or CSV tables on files, blob storage or Cosmos DB, and LanceDB for vectors. No graph database: the graph is two tables. LLM calls need structured JSON output, and the docs warn that Ollama proxies "frequently see issues with malformed responses" ([models](https://github.com/microsoft/graphrag/blob/main/docs/config/models.md)).

### LazyGraphRAG: announced, never released

[LazyGraphRAG](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) builds the graph with NLP only and defers all LLM work to query time: it splits the question into sub-queries, runs budgeted LLM relevance tests over communities, and deepens only into promising ones. Microsoft reported indexing at 0.1% of full GraphRAG's cost and quality comparable to global search at more than 700 times lower query cost (LLM-judged). **The code was never open-sourced:** the tracking issue was closed as "not planned" in November 2025 ([#1512](https://github.com/microsoft/graphrag/issues/1512), [#1935](https://github.com/microsoft/graphrag/issues/1935)). It ships only inside Microsoft products. The idea is public; the implementation is not.

### Cost

| Measurement | Indexing | Per query |
|-------------|----------|-----------|
| [GraphRAG-Bench](https://arxiv.org/abs/2506.05690), one book of about 56k tokens | About 655k tokens | About 39k tokens (local), 331k (global) |
| [Zhou et al.](https://arxiv.org/abs/2503.04338), MultihopSum | | Global search: 521 s and 354k tokens, against 9.1 s and 1.7k tokens for vanilla RAG |
| [BM25 Wins at Scale](https://arxiv.org/abs/2607.26497) | Completed only up to about 10.6M corpus tokens | |

With small models it fails: in [MiniRAG](https://arxiv.org/abs/2501.06713)'s tests it produced no useful answers with any small model, and its issue tracker is dominated by JSON format errors and empty graphs with local models ([#339](https://github.com/microsoft/graphrag/issues/339), [#562](https://github.com/microsoft/graphrag/issues/562), [#657](https://github.com/microsoft/graphrag/issues/657)).

### Strengths and gaps

- **Strengths:** the reference design for "sensemaking" questions over a whole corpus; DRIFT; bring-your-own-graph; prompt tuning per domain; clean tabular outputs.
- **Gaps:** frozen roadmap; the most expensive indexing and global queries of any method; needs reliable JSON output; the cheap mode is English-oriented; no server or UI; append-only community updates; its best idea (LazyGraphRAG) is unavailable.

## When graph retrieval helps, and when it hurts

Independent evaluations from 2025–2026 agree on the shape of the trade-off:

| Graph retrieval helps | Graph retrieval hurts or adds nothing |
|----------------------|---------------------------------------|
| Multi-hop and complex reasoning ([GraphRAG-Bench](https://arxiv.org/abs/2506.05690); HippoRAG 2 and LinearRAG on 2Wiki and MuSiQue) | Single-fact lookups such as NQ and PopQA ([Han et al.](https://arxiv.org/abs/2502.11371), GraphRAG-Bench) |
| Global summaries and sensemaking over a whole corpus ([Zhou et al.](https://arxiv.org/abs/2503.04338)) | **Unanswerable questions:** global search hallucinated, scoring 19.3 against 96.0 for vanilla RAG on MultiHop-RAG null queries ([Han et al.](https://arxiv.org/abs/2502.11371)) |
| Temporal and comparison questions (MultiHop-RAG temporal: 50.6 against 30.7) | Cost: 10 to 300 times more tokens per query, and index cost that grows with the corpus |
| Combined **with** vector RAG rather than replacing it (+6.4% when results were merged) | Small extraction models, where graph quality collapses ([MiniRAG](https://arxiv.org/abs/2501.06713)) |

Two more cautions. Many published win rates come from pairwise LLM judging that flips with answer order and length ([Zeng et al.](https://arxiv.org/abs/2506.06331)). And at large scale, plain BM25 beat the graph methods on quality per token: 74.7 at 2.9M amortised tokens against 66.2 at 10.7M for HippoRAG 2, with GraphRAG and LightRAG far behind ([BM25 Wins at Scale](https://arxiv.org/abs/2607.26497)).

## The family

| Project | Licence | State | Approach | Relevance for a CPU engine |
|---------|---------|-------|----------|---------------------------|
| [HippoRAG 2](https://github.com/OSU-NLP-Group/HippoRAG) (OSU, ICML 2025) | MIT | Active | LLM OpenIE triples, a graph of phrases and passages with synonym edges, Personalized PageRank seeded from query-matched triples ([paper](https://arxiv.org/abs/2502.14802)) | Strongest independent results among LLM-built graphs, and about 9 times cheaper to index than LightRAG, but the reference setup uses a 7B embedder and a 70B LLM |
| [LinearRAG](https://github.com/DEEP-PolyU/LinearRAG) (ICLR 2026) | GPL-3.0 | Small | **No LLM at indexing:** a graph of passages, sentences and spaCy entities, then Personalized PageRank ([paper](https://arxiv.org/abs/2510.10114)) | Indexed 2Wiki in 250 s against 4,933 s for LightRAG, and beat HippoRAG 2 on accuracy |
| EHRAG (April 2026) | | Research code | Hypergraph from GLiNER or spaCy entities plus embedding clusters; no LLM at indexing ([paper](https://arxiv.org/abs/2604.17458)) | Beat LinearRAG on 2Wiki |
| SPRIG, LiteRAG (2026) | | Research | Token-free entity co-occurrence graphs with PageRank; algorithmic query-time exploration instead of LLM steps ([SPRIG](https://arxiv.org/abs/2602.23372), [LiteRAG](https://arxiv.org/abs/2609.10239)) | Same direction |
| SAP "Towards Practical GraphRAG" | | Paper | Dependency-parse triples reached 94% of an LLM-built graph's performance; graph and dense rankings fused with RRF ([paper](https://arxiv.org/abs/2507.03226)) | Validates fusion over replacement |
| [Cognee](https://github.com/topoteretes/cognee) | Apache-2.0 | Very active | Memory platform; since v1.6 a "keyless" mode extracts graphs on CPU with GLiNER and no LLM | Proof that CPU-only graph extraction ships in practice. Production Postgres graph store is a paid product |
| [Graphiti](https://github.com/getzep/graphiti) (Zep) | Apache-2.0 | Very active | Bi-temporal graph for agent memory; contradicted facts are invalidated | Built for memory, not documents; warns that small models cause ingestion failures |
| [RAG-Anything](https://github.com/HKUDS/RAG-Anything) | MIT | Active, merged into LightRAG | Images, tables and equations as graph nodes, each described by a vision model | Every figure costs a vision-model call |
| [nano-graphrag](https://github.com/gusye1234/nano-graphrag), [fast-graphrag](https://github.com/circlemind-ai/fast-graphrag), [MiniRAG](https://github.com/HKUDS/MiniRAG) | MIT | Dormant | A 1,100-line GraphRAG clone; PageRank exploration with domain-guided extraction; a graph design for 1.5–4B models | Readable reference code. MiniRAG's main value is its evidence that LLM-built graphs fail with small models |
| [neo4j-graphrag-python](https://github.com/neo4j/neo4j-graphrag-python) | Apache-2.0 | Active | Schema-guided extraction with exact, fuzzy and semantic entity resolvers; many retrievers | Needs a Neo4j server (JVM), which competes with the LLM for memory on a laptop |
| PathRAG, LeanRAG, Youtu-GraphRAG | No licence or custom licence | | | **Do not reuse code** |

Storage note: [Kùzu](https://github.com/kuzudb/kuzu), an embedded graph database many of these projects used, was archived in October 2025. Graphiti has deprecated it; we should not depend on it.

## Implications for open-rag-engine

1. **Tiered extraction, CPU first.** Tier 1, on by default: multilingual NER (for example [GLiNER multi](https://huggingface.co/urchade/gliner_multi-v2.1), Apache-2.0) and co-occurrence, building a graph of passages, sentences and entities with no LLM. Tier 2, optional: LLM extraction of typed relations, as a background job or through a hosted model with the user's key. Tier 3, lazy: community summaries generated only for communities that queries actually touch, then cached (the LazyGraphRAG idea).
2. **Fuse, don't replace.** Graph retrieval (Personalized PageRank seeded from the question's entities) produces one more ranked list for reciprocal rank fusion. Lookups go to hybrid retrieval with reranking; multi-hop questions add graph fusion; global questions use communities under a fixed budget.
3. **Ground and abstain.** Every graph artefact links to chunks, answers cite chunks, and global answers go through the same abstention checks, given the hallucination finding on unanswerable questions.
4. **Real entity resolution,** in cheap steps: normalisation, then embedding and fuzzy similarity, then an optional LLM verdict.
5. **Incremental and deletion-correct:** extraction cached by chunk hash, model and prompt version; re-clustering limited to the affected part of the graph; stale flags instead of append-only communities.
6. **Hardened small-model extraction:** constrained decoding, 300–600-token extraction windows, per-window record caps, no gleaning on CPU, timeouts, and fallback to NER on parse failures.
7. **Plain tables for the graph** in the embedded store; no JVM database and no Kùzu by default.
8. **Honest evaluation:** reference-based metrics on multi-hop benchmarks, order-swapped judging, and index and query token costs reported next to quality. Graph retrieval is enabled by default only if it wins on our own multi-hop and global slices (QR-QUAL-06).

Our rough estimate of LLM-based indexing time for one 56k-token book on a laptop CPU, from the GraphRAG-Bench token counts and assumed CPU speeds: several hours for LightRAG or Microsoft GraphRAG, against minutes for an NER graph. Spike S-3 replaces this estimate with measurements.

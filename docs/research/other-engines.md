# Other engines worth knowing

> Snapshot: 2026-10-17. Short profiles: what each one is, the idea worth taking, and its main gap. The five main competitors have their own pages.

| Project | Licence | State | Idea worth taking | Main gap |
|---------|---------|-------|-------------------|----------|
| [WeKnora](https://github.com/Tencent/WeKnora) (Tencent) | MIT | Very active, about 34.5k stars, Go backend | Retrieval chunks that can be edited, diffed and rolled back; tracing built in; RAG, agent and wiki modes over the same knowledge base | Heavy: its compose file lists more than ten services; no evaluation harness |
| [PrivateGPT](https://github.com/zylon-ai/private-gpt) (Zylon) | Apache-2.0 | v1.0 rewrite in June 2026, about 57.6k stars | Runs no models itself: it talks to any OpenAI-compatible server and copies a well-known API shape | No graph retrieval or evaluation loop (unverified) |
| [Quivr](https://github.com/The-Vibe-Company/quivr) | MIT | v2 is an alpha Go rewrite | Immutable versions and idempotent writes; keyword search available before embeddings finish; indexes as rebuildable projections of the database; every hit re-authorised at query time; outages return errors, never an empty "success" | Alpha; needs Temporal, Weaviate and S3 |
| [Khoj](https://github.com/khoj-ai/khoj) | AGPL-3.0 | Slowing; team focus moved to a new project | Many clients (Obsidian, Emacs, chat apps); public benchmark results from CI | A personal assistant rather than an engine |
| [UltraRAG](https://github.com/OpenBMB/UltraRAG) (OpenBMB) | Apache-2.0 | Active | Every component is an MCP server; YAML pipelines with loops and branches; a visual pipeline IDE | Research-first |
| [FlashRAG](https://github.com/RUC-NLPIR/FlashRAG) | MIT | Active | 36 preprocessed benchmark datasets and 23 reference methods | A research toolkit, not a product |
| [SWIRL](https://github.com/swirlai/swirl-search) | Apache-2.0 community edition | Slowing since mid-2026 | Federated search with no index: queries sources live under the user's own permissions | Best reranker and MCP server are enterprise-only |
| [EdgeQuake](https://github.com/raphaelmansuy/edgequake) | Apache-2.0 | Very active, Rust | LightRAG-style GraphRAG as one binary plus one Postgres; detects local runtimes; listens on localhost only; an "honest numbers" section | Young project |
| [Ragit](https://github.com/baehyunsol/ragit) | MIT | One maintainer, Rust | Knowledge bases as Git-like artefacts you can clone and push | Small community |
| [PageIndex](https://github.com/VectifyAI/PageIndex) | MIT | Popular, about 39k stars | Vector-free: an LLM navigates a tree index of the document | Expensive LLM calls per query; little evidence on large corpora |
| [LEANN](https://arxiv.org/abs/2506.08276) | MIT | About 13k stars | A vector index that recomputes embeddings on demand, claiming 97% less storage | Trades storage for query-time compute |
| [OpenViking](https://github.com/volcengine/OpenViking) (Volcengine) | AGPL-3.0 | New in 2026, about 40k stars | Context as a virtual file system with summaries at several levels and directory-scoped search | Aimed at agent memory |
| [CocoIndex](https://github.com/cocoindex-io/cocoindex) | Apache-2.0 | Active, Rust core | Incremental processing of only what changed | A data-pipeline framework, not a RAG engine |
| [Morphik](https://github.com/morphik-org/morphik-core) | **BSL 1.1** (not open source) | The company has pivoted | Page-image retrieval as a first-class mode | Licence and focus |
| [Pathway llm-app](https://github.com/pathwaycom/serviette) | MIT app on a **BSL 1.1** framework that needs a licence key | Popular | Streaming indexing: edits and deletions show up in answers within seconds | The key and the BSL framework conflict with "free and local-first" |
| [Kiln](https://github.com/Kiln-AI/Kiln) | MIT libraries, proprietary desktop app | Active | Comparing RAG configurations side by side on your own data, with generated retrieval test sets | The app is not open source |
| [Cognita](https://github.com/truefoundry/cognita), [Verba](https://github.com/weaviate/Verba), [PIKE-RAG](https://github.com/microsoft/PIKE-RAG) | Apache-2.0, BSD-3, MIT | **Archived** in 2025–2026 | Cognita's registries for parsers, embedders and retrievers; Verba's chunk inspector UI; PIKE-RAG's taxonomy of question difficulty for designing evaluation sets | Unmaintained |

## Patterns across this list

- **Abandonment is common.** Cognita, Verba, PIKE-RAG and ARES were archived or went dormant within two years; Ragas has stalled. Projects backed by one company's product strategy disappear when the strategy changes. Our answer is a small core with few dependencies, so two maintainers can keep it alive.
- **Licences drift away from open source.** Morphik moved to BSL; Pathway's framework needs a key; Phoenix is source-available. AGPL-3.0 keeps our engine and its hosted modifications open.
- **The best ideas are small and structural:** immutable versions and rebuildable indexes (Quivr), editable chunks (WeKnora), components exposed over MCP (UltraRAG), honest published numbers (EdgeQuake, Khoj). Most of these are already in our [architecture](../architecture/README.md).

# R2R

> Snapshot: 2026-10-17. Repository facts from the GitHub API, source code and release notes on that date.

| | |
|---|---|
| Repository | [SciPhi-AI/R2R](https://github.com/SciPhi-AI/R2R) |
| Licence | MIT |
| Popularity | About 8.0k stars |
| Latest release | [v3.6.5](https://github.com/SciPhi-AI/R2R/releases) on GitHub (2025-06-06); `r2r` 3.6.6 on [PyPI](https://pypi.org/project/r2r/) (2025-08-17) |
| Activity | **Dormant.** No commit to `main` since 2025-11-07 |
| Shape | Python server (FastAPI, REST API under `/v3`), Python and JavaScript SDKs, a separate Next.js dashboard |

## Status: orphaned

- The documentation site has returned "deployment not found" since about October 2025. Users asked in April 2026 whether the project is still active ([#2274](https://github.com/SciPhi-AI/R2R/issues/2274), [#2276](https://github.com/SciPhi-AI/R2R/issues/2276)); no maintainer answered.
- The security contact address bounces and private vulnerability reporting is off ([#2294](https://github.com/SciPhi-AI/R2R/issues/2294)). Public reports of SQL injection ([#2290](https://github.com/SciPhi-AI/R2R/issues/2290), [#2308](https://github.com/SciPhi-AI/R2R/issues/2308), [#2309](https://github.com/SciPhi-AI/R2R/issues/2309)), authentication bypass ([#2295](https://github.com/SciPhi-AI/R2R/issues/2295)), a hard-coded token-signing fallback key ([#2311](https://github.com/SciPhi-AI/R2R/issues/2311)) and access to other users' conversations ([#2292](https://github.com/SciPhi-AI/R2R/issues/2292)) are unanswered. We did not verify the exploits.
- SciPhi's Y Combinator page now redirects to Event Horizon Labs, which describes itself as automating investing, and the two main committers now list other employers. We found no acquisition of R2R. Our reading: the company pivoted, and R2R was left behind.

**Use R2R as a design reference, not as a dependency.**

## How it works

**Ingestion.** About 28 parsers (PDF, office formats, e-mail, EPUB, HTML, code, images, audio). Modes `fast`, `hi-res` (vision-model page parsing or Unstructured), `ocr` (which requires the hosted Mistral OCR) and `custom` ([cookbook](https://github.com/SciPhi-AI/R2R/blob/main/docs/cookbooks/ingestion.md)). No dedicated table-structure extraction. Recursive chunking by default; optional "contextual enrichment" of chunks; document summaries at ingestion.

**Storage.** **PostgreSQL with pgvector is the only supported database** ([source](https://github.com/SciPhi-AI/R2R/blob/main/py/core/base/providers/database.py)).

**Retrieval.** Vector search plus PostgreSQL full-text search, fused with reciprocal rank fusion inside one SQL query, with tunable weights ([docs](https://github.com/SciPhi-AI/R2R/blob/main/docs/documentation/retrieval/hybrid-search.md)). The full-text half is not BM25, and its text-search configuration is **hard-coded to English** ([source](https://github.com/SciPhi-AI/R2R/blob/main/py/core/providers/database/chunks.py)), so keyword search is English-stemmed for every language. HyDE and RAG-Fusion are marked beta. The optional reranker calls an external endpoint and, if the call fails, **silently returns unreranked results** ([source](https://github.com/SciPhi-AI/R2R/blob/main/py/core/providers/embeddings/litellm.py)).

**Answers and citations.** The RAG endpoint returns citations with character spans, and streaming uses typed server-sent events (`search_results`, `message`, `citation`, `final_answer`) ([docs](https://github.com/SciPhi-AI/R2R/blob/main/docs/documentation/retrieval/search-and-rag.md)). An open pull request reports that citation events can fire for citation IDs the model invented ([#2287](https://github.com/SciPhi-AI/R2R/pull/2287)).

**GraphRAG.** LLM extraction of entities and relationships per document, pulled into graphs scoped to a collection, with hierarchical Leiden communities computed in a separate service ([cookbook](https://github.com/SciPhi-AI/R2R/blob/main/docs/cookbooks/graphs.md)).

**Agents.** A RAG agent with search tools, and a "deep research" agent that can run Python.

**Users and access.** Users, superusers and collections as the unit of sharing and access control; built-in tokens, Supabase or Clerk for authentication. Defaults: authentication off, and a well-known default admin password ([config](https://github.com/SciPhi-AI/R2R/blob/main/py/r2r/r2r.toml)).

**Evaluation and observability.** No built-in evaluation, only a Ragas cookbook. Logging and Sentry; no OpenTelemetry.

## Architecture

R2R is layered: API routers call services (authentication, ingestion, retrieval, graph, management), which call providers (database, embedding, LLM, OCR, orchestration and others), each an abstract class with a configuration object chosen in a TOML file. One idea is worth taking: the **orchestration provider** runs workflows either in process (`simple`) or on a durable workflow engine (Hatchet).

The layering is undermined in practice:

- **No plugin mechanism.** Providers are created by a hard-coded `if/elif` chain ([factory](https://github.com/SciPhi-AI/R2R/blob/main/py/core/main/assembly/factory.py)); adding one means forking.
- **The database provider is a god object.** One provider aggregates 13 PostgreSQL handlers and exposes raw SQL execution ([source](https://github.com/SciPhi-AI/R2R/blob/main/py/core/providers/database/postgres.py)). "Pluggable storage" exists only in name.
- **Misplaced responsibilities:** reranking hangs off the embedding provider.
- **Large modules:** the retrieval service is about 2,100 lines, the graph database handler about 2,900.
- **A dependency kitchen sink** in the core install, and documentation that drifted from the code (some pages are empty after a migration).

## Local and hardware story

Local presets for Ollama and LM Studio exist ([cookbook](https://github.com/SciPhi-AI/R2R/blob/main/docs/cookbooks/local.md)), but the **defaults are hosted models** (GPT-5 family, Claude, Whisper, Mistral OCR). PostgreSQL is always required. The light deployment runs PostgreSQL, MinIO, a clustering service, R2R and the dashboard; the full deployment runs 14 services including a workflow engine, a second PostgreSQL, RabbitMQ and Unstructured ([compose](https://github.com/SciPhi-AI/R2R/blob/main/docker/compose.full.yaml)).

## Strengths

- The most complete open-source RAG *server* of its generation: ingestion, hybrid search, GraphRAG, agents, users and collections behind one coherent resource-oriented REST API with SDKs.
- Character-span citations and a clean set of streaming events.
- Search and ingestion presets that hide configuration complexity.

## Gaps

- Abandoned, with unpatched security reports and insecure defaults.
- Locked to PostgreSQL; English-only keyword search; no true BM25.
- Cloud-first defaults; the only OCR is a hosted service.
- Heavy full deployment; no built-in evaluation; extending it means forking.
- Two people wrote most of the code, and both have left.

## Lessons for open-rag-engine

- **Adopt:** the resource-oriented API (documents, chunks, collections, graphs, conversations); **collections as the scope for graphs and, later, for access control**; in-process versus durable job execution as an adapter choice; typed streaming events; presets layered over the full configuration.
- **Avoid:** a SQL-shaped storage interface (we split storage into capability ports: lexical index, vector index, graph store, repositories); hard-coded factories (we use a registry and plugin entry points); silent fallbacks (we record every skipped step); a hard-coded stemming language; authentication off with default credentials; hosted defaults in a product that calls itself local.
- **Do differently:** a working security policy with private vulnerability reporting, documentation that lives in the repository, two maintainers from day one, and citation IDs validated against the packed context before they are emitted ([ADR-0005](../adr/0005-verified-citations.md)).

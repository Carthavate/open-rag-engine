# 5. Ports and interfaces

> Draft, 2026-10-17. Operations are written language-neutrally. Concrete signatures arrive with the code, after the language ADR.

The core talks to the outside world through two kinds of interface:

- **Driving side:** the application services that the HTTP API, MCP server, CLI and SDK call.
- **Driven side:** the ports the core calls, implemented by infrastructure adapters.

## Rules every port follows

1. **A request context on every call.** Each operation receives the principal, the collection, a deadline and the current trace span. Permissions, timeouts and tracing therefore work the same way everywhere, with no special cases.
2. **Capabilities are declared, not discovered by failing.** Every adapter publishes what it supports (dimensions, languages, context window, filter operators, modalities), and the composition root checks it at startup.
3. **Batch first.** Model and index operations take lists. A single item is a list of one.
4. **Typed errors.** Adapters translate vendor errors into the categories below. Retryable errors carry a retry hint.
5. **Identity for reproducibility.** Model and parser adapters report the exact model or tool version, which goes into every fingerprint.
6. **Health.** Every adapter answers a readiness check.
7. **Domain types only** ([rule R-06](04-layers.md#rules)).

### Error categories

| Category | Meaning | Retry | HTTP |
|----------|---------|-------|------|
| `InvalidInput` | The request or the document breaks a contract | No | 400 or 422 |
| `NotFound` | The referenced resource doesn't exist, or the principal may not know it exists | No | 404 |
| `Conflict` | Version or idempotency-key conflict | No | 409 |
| `PermissionDenied` | The access policy refused the action | No | 403 |
| `Unavailable` | A backend is down or overloaded | Yes, with backoff | 503 |
| `Timeout` | The deadline passed | Yes, if budget remains | 504 |
| `BudgetExceeded` | A token, cost or time budget is used up | No | 429 |
| `CapabilityMissing` | An adapter can't do what the configuration asks | No; it's a configuration error, caught at startup | n/a |
| `Internal` | A bug | No | 500 |

HTTP errors use the problem details format ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)). Error bodies never include stack traces, secrets or document content.

## Driving side: application services

The HTTP API, the MCP server, the CLI and the SDK are thin mappings onto these operations.

| Service | Operation | Input | Output | Notes |
|---------|-----------|-------|--------|-------|
| Collections | create, get, list, delete | name, configuration | collection | Configuration is validated against adapter capabilities |
| | change configuration | collection, new configuration | job building a new index generation | The current generation keeps serving until the new one is activated |
| Ingestion | ingest | collection, source or upload, options | job id | Idempotent per content hash |
| | delete document | document id | job id | Excluded from search immediately, then purged everywhere ([deletion](06-domain-model.md#deletion)) |
| | job status | job id | stage, progress, errors | Also streamed as events |
| Query | retrieve | collection, query, filters, options | ranked passages with provenance and per-stage scores | Retrieval only; works without any LLM |
| | ask | collection, query, conversation, options | streamed answer, citations, support status, trace id | Abstains when the evidence is insufficient |
| Evaluation | create dataset, add cases | cases with expected sources and, optionally, expected answers | dataset | |
| | generate test set | collection, size, languages | draft dataset for human review | Synthetic questions drawn from the corpus |
| | run | dataset, optional configuration override | run id | Uses the production query service |
| | compare | two runs | metric deltas with confidence intervals | Feeds the CI quality gate |
| Traces | get | trace id | the full trace | |
| Feedback | submit | trace id, rating, comment | | Can be promoted to an evaluation case |

## Driven side: ports

### Ingestion

| Port | Operations | Declares | Notes |
|------|-----------|----------|-------|
| `SourceConnector` | `list(since)`, `fetch(item)` → raw document (bytes, media type, URI, source metadata) | URI schemes | The web connector enforces size limits, allow-lists and protection against server-side request forgery |
| `DocumentParser` | `parse(raw document, options)` → document tree | media types, layout analysis, OCR, table structure, figure extraction, languages, needs GPU | Several parsers can be registered; the parser router picks one per document and per page |
| `FigureDescriber` | `describe(images, surrounding text)` → text | languages, needs GPU | Optional. Makes figures searchable as text |
| `LanguageDetector` | `detect(texts)` → language and confidence | languages | Runs per element, not per document |
| `TextAnalyzer` | `analyze(texts, language)` → tokens | languages, scripts | The same analysis at index and query time, whatever lexical engine sits behind it |
| `Embedder` | `embed_documents(texts)`, `embed_query(texts)` → vectors | model identity, dimensions, max input tokens, languages, query instruction | Supports models that encode queries and documents differently |
| `VisualEmbedder` | `embed_pages(images)`, `embed_query(texts)` → multi-vectors | model identity, vector shape | Optional, for retrieving page images directly |
| `GraphExtractor` | `extract(chunks)` → entities and relations, with mentions | method (LLM or lightweight NER), languages, cost per chunk | Budgeted, and can be turned off |

### Storage

| Port | Operations | Declares | Notes |
|------|-----------|----------|-------|
| Repositories and unit of work | get, add, update per aggregate; `commit`, `rollback` | transaction support | The system of record |
| `BlobStore` | `put(bytes)` → content hash, `get`, `exists`, `delete` | maximum object size | Content-addressed, so writes are idempotent |
| `LexicalIndex` | `upsert(generation, analysed chunks)`, `delete(generation, chunk ids)`, `search(generation, tokens, filter, k)` → hits | filter operators, scoring parameters | |
| `VectorIndex` | `upsert(generation, vectors)`, `delete(generation, ids)`, `search(generation, vectors, filter, k)` → hits | distance metric, dimensions, multi-vector support, filter operators, exact or approximate | Filters run inside the search |
| `GraphStore` | upsert entities, relations and mentions; `merge(entities)`; `neighbours(entities, depth, filter)`; `find_entities(text or vector)`; `communities(level)`; `mentions(entity)` → chunk ids | traversal depth, filter operators | Every graph result resolves to chunks |
| `JobQueue` | `enqueue(job, idempotency key)`, `lease(kinds, ttl)`, `heartbeat`, `complete`, `fail(retryable)`, `progress` | durability | At-least-once delivery, so every job must be idempotent |
| `Cache` | `get`, `put` by key | size limit, eviction | Embeddings keyed by model identity and chunk hash; LLM outputs keyed by the full prompt fingerprint |

### Models

| Port | Operations | Declares | Notes |
|------|-----------|----------|-------|
| `ChatModel` | `generate(messages, parameters)` → completion; `stream(...)` → tokens; `count_tokens(texts)` | model identity, context window, maximum output, streaming, structured output, tool calling, image input | One adapter covers every OpenAI-compatible server: llama.cpp, Ollama, vLLM, LM Studio and many hosted providers |
| `Reranker` | `rerank(query, passages)` → scores | model identity, maximum input tokens, languages | |
| `SupportChecker` | `check(statements, passages)` → supported, unsupported or unclear, with scores | method (NLI model or LLM) | Used by citation verification |
| `Judge` | `score(metric, case, answer, passages)` → metric result with rationale | method, model identity | Evaluation only |

### Cross-cutting

| Port | Operations | Declares | Notes |
|------|-----------|----------|-------|
| `AccessPolicy` | `filter_for(principal, collection)` → filter; `authorize(principal, action, resource)` | | v1 binds an allow-all policy. The filter is applied inside every index search |
| `Tracer` | `start_span`, `record(event, attributes)`, `record_candidates(stage, ranked list)` | exporters | A local trace store by default; OTLP export optional |
| `SecretProvider` | `get(name)` | | Environment variables by default |
| `Clock`, `IdGenerator` | `now()`, `new_id()` | | Injected so tests and replays are deterministic |

## The filter language

Every search port takes the same small, typed filter expression: comparisons (`eq`, `in`, `range`) over metadata fields, combined with `and`, `or` and `not`. Each index adapter translates it into a native filter that runs **inside** the search.

Filtering after the search is not allowed. It silently returns fewer than *k* results, and once permissions exist it makes access bugs easy to write. Adapters declare the operators they support, and the access fields must always be supported.

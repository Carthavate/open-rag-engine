# Functional requirements

> Draft, 2026-10-17. Columns: **P** = priority (M, S, C), **Verified by** = test, eval, bench, inspect or demo, **Src** = architecture driver.

## Ingestion (ING)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-ING-01 | The engine shall ingest PDF (born-digital and scanned), DOCX, PPTX, HTML, Markdown and plain text. | M | Test | D-05 |
| FR-ING-02 | The engine shall ingest images (PNG, JPEG, TIFF) as scanned pages, and XLSX workbooks as tables. | S | Test | D-05 |
| FR-ING-03 | The engine shall accept documents by upload, from a local folder (recursive, with include and exclude patterns) and from a single URL. | M | Test | D-01 |
| FR-ING-04 | The engine shall choose the parsing method per page: the text layer where it is usable, layout analysis where structure requires it, and OCR where there is no usable text. | M | Test | D-02, D-05 |
| FR-ING-05 | The engine shall preserve document structure: reading order, heading hierarchy, lists, tables with their header cells, figures with their captions, and code blocks. | M | Eval (parsing set) | D-05 |
| FR-ING-06 | Every element and every chunk shall record its provenance: document version, page, bounding box, and character range where applicable. | M | Test | D-06 |
| FR-ING-07 | The engine shall run OCR on scanned pages in any script supported by the configured OCR adapter, and detect the language of every element. | M | Eval (language slices) | D-03 |
| FR-ING-08 | When enabled, the engine shall generate a text description of each figure with a vision-language model, so figures can be retrieved by text. | S | Eval | D-05 |
| FR-ING-09 | The engine shall chunk along the document structure, within a token limit measured with the embedding model's tokenizer, without splitting table rows or code blocks, and attach a context header (document title and section path) to every chunk. | M | Test | D-05 |
| FR-ING-10 | Re-ingesting unchanged content shall do nothing. Changed content shall create a new document version, and the document shall stay searchable throughout the update. | M | Test | D-02 |
| FR-ING-11 | Deleting a document shall remove it from search results immediately, and purge all derived data (chunks, vectors, graph evidence, blobs, cached content, quoted passages in traces) in the background. | M | Test | D-06 |
| FR-ING-12 | The engine shall report progress per document and a final ingestion report listing pages parsed, pages failed with reasons, and warnings. | M | Test | D-08 |
| FR-ING-13 | An interrupted ingestion job shall resume from its last completed stage without creating duplicates. | M | Test | D-02 |
| FR-ING-14 | The engine shall enforce configurable limits on file size, page count, decompression ratio and parse time per page, and never execute macros or embedded scripts. | M | Test | D-02 |
| FR-ING-15 | The engine shall watch a folder and ingest new, changed and deleted files automatically. | S | Test | D-02 |
| FR-ING-16 | Further sources (object storage, Git repositories, wikis) shall be addable as source-connector plugins without changes to the core. | C | Inspect | D-09 |
| FR-ING-17 | During large imports, documents shall become findable by keyword search as soon as they are chunked, before their embeddings are complete. | C | Test | D-02 |

## Retrieval (RET)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-RET-01 | The engine shall provide BM25 lexical retrieval with per-language analysis, falling back to Unicode word segmentation for languages without a dedicated analyser. | M | Eval (language slices) | D-03 |
| FR-RET-02 | The engine shall provide dense retrieval with a multilingual embedding model. | M | Eval | D-03 |
| FR-RET-03 | The engine shall fuse the results of all active retrievers and query variants with weighted reciprocal rank fusion. | M | Test, eval | D-07 |
| FR-RET-04 | The engine shall rerank fused candidates with a multilingual cross-encoder and use a relevance floor to detect insufficient evidence. | M | Eval | D-06 |
| FR-RET-05 | The engine shall diversify results with maximal marginal relevance and a configurable cap on chunks per document. | M | Test | D-07 |
| FR-RET-06 | The engine shall generate query variants (multi-query) and, when the question's language differs from the collection's main languages, cross-language variants for lexical retrieval. | M | Eval (cross-language slice) | D-03 |
| FR-RET-07 | Metadata filters (collection, document, language, date, element kind, custom fields) shall be applied inside every search, never after it. | M | Test | D-09 |
| FR-RET-08 | In a conversation, follow-up questions shall be rewritten into standalone questions before retrieval. | M | Eval | — |
| FR-RET-09 | The engine shall expand retrieved chunks to their parent section when that fits the context budget. | S | Eval | D-05 |
| FR-RET-10 | Retrieval shall be available as its own operation that returns ranked passages with provenance and per-stage scores, and works with no LLM configured. | M | Test | D-01 |
| FR-RET-11 | The engine shall support retrieving page images directly with a visual embedding model, as an optional retriever. | C | Eval (visual set) | D-05 |

## Knowledge graph (GRAPH)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-GRAPH-01 | The engine shall build a knowledge graph per collection: entities, relations and mentions, every one linked to the chunks it came from. | M | Test | D-04 |
| FR-GRAPH-02 | The extraction method shall be selectable per collection: off, multilingual NER with co-occurrence (no LLM, the laptop default), or LLM extraction of typed relations. LLM extraction shall fall back to NER for any chunk whose output cannot be parsed. | M | Test | D-02, D-04 |
| FR-GRAPH-03 | The engine shall resolve duplicate entities (spelling variants, abbreviations) into one, using normalisation and similarity before any LLM call. | M | Eval (entity set) | D-04 |
| FR-GRAPH-04 | Adding or deleting documents shall update the graph incrementally, without a full rebuild. | M | Test | D-02, D-04 |
| FR-GRAPH-05 | The engine shall group entities into communities, re-cluster only the affected part of the graph after updates, and summarise a community the first time a query needs it, caching the summary until the community changes. | M | Test | D-02, D-04 |
| FR-GRAPH-06 | The engine shall offer local graph retrieval (entities in the question and their neighbourhood) and global graph retrieval (relevant communities), fused with the other retrievers. | M | Eval (multi-hop and global slices) | D-04 |
| FR-GRAPH-07 | Answers based on graph retrieval shall cite the source chunks, never the generated summaries. | M | Test | D-06 |
| FR-GRAPH-08 | Graph extraction shall run within a per-collection token and time budget, show a cost estimate before it starts, and never block search. | M | Test | D-02 |
| FR-GRAPH-09 | The engine shall resolve the same entity across languages. | S | Eval | D-03 |

## Generation and citations (GEN)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-GEN-01 | The engine shall answer only from retrieved sources, in the language of the question. | M | Eval | D-03, D-06 |
| FR-GEN-02 | Every statement in an answer shall cite at least one source, and every citation shall resolve to a document, a page, and a region or character range. | M | Eval, test | D-06 |
| FR-GEN-03 | The engine shall verify each citation: the cited source must have been in the model's context and must support the statement. Unsupported statements are flagged or removed, as configured. | M | Eval | D-06 |
| FR-GEN-04 | When the evidence is insufficient, the engine shall abstain, say so, and show what it searched. | M | Eval (unanswerable slice) | D-06 |
| FR-GEN-05 | Answers shall stream, with verification verdicts delivered per statement as they become available. | M | Test | D-08 |
| FR-GEN-06 | Retrieved text shall reach the model as delimited data, never as instructions. | M | Eval (injection set) | D-06 |
| FR-GEN-07 | When the backend supports constrained output, the citation format shall be enforced by a schema or grammar. | S | Test | D-06 |
| FR-GEN-08 | The engine shall route each question to a strategy (`direct`, `multi_query`, `graph_global`, `retrieve_only`) automatically, and let callers force one. | M | Test, eval | D-04 |
| FR-GEN-09 | Each query shall run within a deadline and a token budget, degrade in the documented order when they are tight, and report which steps it skipped. | M | Test | D-02, D-08 |

## Models and backends (MOD)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-MOD-01 | The engine shall use local LLMs through any OpenAI-compatible server (llama.cpp, Ollama, vLLM, LM Studio). | M | Test | D-02 |
| FR-MOD-02 | The engine shall use hosted LLMs with the operator's own key, through the OpenAI-compatible API. | M | Test | D-02, D-10 |
| FR-MOD-03 | The engine shall provide native adapters for the major hosted providers whose APIs are not OpenAI-compatible. | S | Test | D-02 |
| FR-MOD-04 | Embedding, reranking and support-checking models shall run in-process on the CPU, and use a GPU automatically when one is available. | M | Bench | D-02 |
| FR-MOD-05 | Models shall be downloaded once and cached. The engine shall run offline from a pre-seeded model cache. | M | Test (network blocked) | D-02 |
| FR-MOD-06 | Changing the embedding model shall build a new index generation in the background while the current one keeps serving, with explicit activation and rollback. | M | Test | D-07 |
| FR-MOD-07 | The exact identity of every model used shall be recorded in each trace and evaluation run. | M | Test | D-07 |

## Evaluation (EVAL)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-EVAL-01 | Operators shall be able to create, import and version evaluation datasets. A case has a question, a language, expected source chunks, an optional reference answer and an answerable flag. | M | Test | D-07 |
| FR-EVAL-02 | The engine shall generate draft test sets from a collection, covering lookups, multi-hop questions, tables, figures, unanswerable questions and several languages, for human review. | M | Demo | D-07 |
| FR-EVAL-03 | Evaluation runs shall use the production query service and compute per-stage retrieval metrics, faithfulness, citation precision and recall, correctness, abstention accuracy, language match, latency and token usage. | M | Test | D-07 |
| FR-EVAL-04 | The engine shall compare two runs case by case, with bootstrap confidence intervals. | M | Test | D-07 |
| FR-EVAL-05 | A CLI command shall run an evaluation and exit non-zero when a quality gate fails, for use in CI. | M | Test | D-07 |
| FR-EVAL-06 | The judge model shall be configurable, shall not be the generator model, and shall come with a calibration report against human labels. | M | Inspect | D-07 |
| FR-EVAL-07 | The engine shall load standard public retrieval and QA benchmarks into its dataset format. | S | Demo | D-07 |
| FR-EVAL-08 | Traces with negative feedback, abstentions or unsupported statements shall feed a triage queue that turns accepted ones into evaluation cases. | S | Demo | D-07 |
| FR-EVAL-09 | Activating a new index generation shall optionally require that it does not score worse than the active one. | S | Test | D-07 |

## Observability (OBS)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-OBS-01 | Every query and every ingestion job shall produce a trace: stages, ranked candidates per stage with scores, prompts and template versions, model identities, timings, skipped steps and data egress. | M | Test | D-08 |
| FR-OBS-02 | Traces shall be stored locally with configurable retention, and be readable through the API and the UI. | M | Test | D-08 |
| FR-OBS-03 | Traces and metrics shall be exportable over OTLP. | S | Test | D-08 |
| FR-OBS-04 | Logs shall be structured, and shall contain no secrets and no document content at the default log level. | M | Test | D-08 |

## Interfaces (API)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-API-01 | A versioned REST API, described by an OpenAPI document, shall cover every application service. | M | Test | D-01 |
| FR-API-02 | Answers and job progress shall stream over server-sent events. | M | Test | D-01 |
| FR-API-03 | A Python library shall expose the same operations in-process. | M | Test | D-01 |
| FR-API-04 | An MCP server shall expose retrieval, question answering and collection listing as tools. | S | Test | D-01, D-09 |
| FR-API-05 | A CLI shall cover ingestion, asking, evaluation and administration. | M | Test | D-01 |
| FR-API-06 | API errors shall use RFC 9457 problem details, with no stack traces, secrets or document content. | M | Test | — |
| FR-API-07 | The API shall require an API key, and listen only on localhost unless configured otherwise. | M | Test | — |
| FR-API-08 | The engine shall offer an OpenAI-compatible chat endpoint, so existing chat front ends can use it. | C | Test | D-01 |

## Web UI (UI)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-UI-01 | A chat view shall stream answers, and each citation shall open the source document at the cited page with the region highlighted. | M | Demo, E2E test | D-06 |
| FR-UI-02 | A document library shall let users upload, check status, re-ingest and delete documents per collection. | M | E2E test | D-01 |
| FR-UI-03 | A trace view shall explain each answer: question class and strategy, candidates per stage, packed context, verdicts, timings. | M | E2E test | D-08 |
| FR-UI-04 | The UI shall always show which model backends are active and whether any data leaves the machine. | M | E2E test | D-02 |
| FR-UI-05 | An evaluation dashboard shall list runs, show metrics and comparisons, and drill down to individual cases. | S | E2E test | D-07 |
| FR-UI-06 | A graph explorer shall show entities, relations and the passages behind them. | S | E2E test | D-04 |
| FR-UI-07 | The UI shall show the effective configuration, read-only. | S | E2E test | — |
| FR-UI-08 | A retrieval playground shall run `retrieve` for a typed question and show the ranked candidates after each stage, without generating an answer. | S | E2E test | D-08 |

## Administration (ADM)

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-ADM-01 | The engine shall read one declarative configuration file with profiles (`laptop`, `gpu`, `server`), validate it against a schema and adapter capabilities at startup, and fail with a precise message when it is inconsistent. | M | Test | D-02 |
| FR-ADM-02 | Collections shall be able to override the configuration: models, chunking, retrievers, graph extraction, budgets. | M | Test | — |
| FR-ADM-03 | Operators shall be able to list, build, activate, roll back and delete index generations. | M | Test | D-07 |
| FR-ADM-04 | Operators shall be able to back up and restore the system of record (metadata and blobs). Indexes are rebuilt from it. | M | Test | — |
| FR-ADM-05 | The server shall expose health and readiness endpoints. | S | Test | — |
| FR-ADM-06 | On first setup, the engine shall detect the machine's memory, CPU features and GPU, and propose a profile and default models that fit. | S | Test | D-02 |

## Extension points (EXT)

These are v1 obligations for the *seam*, not for the feature behind it.

| ID | Requirement | P | Verified by | Src |
|----|-------------|---|-------------|-----|
| FR-EXT-01 | Every request shall carry a principal, and every stored record a tenant and access fields. An access-policy port shall turn the principal into a filter applied in every search. v1 ships an allow-all policy. | M | Test, inspect | D-09 |
| FR-EXT-02 | Query strategies shall be pluggable, so that a multi-step (agentic) strategy can be added without changing the pipeline slots. | M | Inspect, example plugin | D-09 |
| FR-EXT-03 | Third-party adapters shall register as plugins and must pass the port's contract test suite. | M | Test | D-01 |

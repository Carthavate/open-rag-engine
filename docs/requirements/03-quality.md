# Quality requirements

> Draft, 2026-10-17. Targets marked **(p)** are provisional. They are deliberately honest for a CPU-only laptop, and are checked by the spikes in [constraints and scope](04-constraints-and-scope.md#spikes) before the MVP is frozen.

## Reference setups

Quality targets are only meaningful against fixed conditions.

| ID | Setup |
|----|-------|
| **RH-1** | Reference laptop: x86-64 CPU with 4 performance cores / 8 threads and AVX2, 16 GB RAM, NVMe SSD, no discrete GPU. Windows 11 or Ubuntu 24.04. |
| **RH-2** | Apple Silicon laptop with 16 GB unified memory, macOS 14 or later. |
| **RH-3** | Reference server: 16 cores, 64 GB RAM, one 24 GB GPU, Ubuntu 24.04. |
| **Default stack** | The laptop profile's default models and adapters, as fixed by the model ADRs. |
| **DS-smoke** | The project's smoke evaluation set: tens of cases, run on every pull request. |
| **DS-main** | The project's main evaluation set: a mixed, multilingual corpus with born-digital and scanned PDFs, tables, figures and web pages, plus a few hundred reviewed cases sliced by language, question type (lookup, multi-hop, global, unanswerable), element kind (text, table, figure) and prompt-injection attempts. |
| **Language slices** | At least: English, French, German, Spanish (Latin script), Arabic (right-to-left), Russian (Cyrillic), Hindi (Devanagari), Chinese and Japanese (CJK). Together they cover the scripts that break naive tokenisation. |

All latency figures assume models already loaded ("warm") and a collection at the laptop scale target (QR-SCALE-01).

## Answer quality (QUAL)

Measured on DS-main with the default stack.

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-QUAL-01 | Faithfulness: share of answer statements supported by their cited passages | ≥ 0.90 overall; ≥ 0.85 on every language slice **(p)** | Eval |
| QR-QUAL-02 | Citation precision and recall | Precision ≥ 0.90; recall ≥ 0.85 **(p)** | Eval |
| QR-QUAL-03 | Abstention | Abstains on ≥ 0.80 of unanswerable cases; abstains on ≤ 0.10 of answerable ones **(p)** | Eval |
| QR-QUAL-04 | Hybrid retrieval earns its place | Hybrid retrieval with reranking beats the best single retriever on recall@10 and nDCG@10, overall and on every language slice with at least 30 cases | Eval |
| QR-QUAL-05 | Cross-language retrieval | When the question's language differs from the source's, recall@10 stays within 10 points of the same-language result **(p)** | Eval |
| QR-QUAL-06 | GraphRAG earns its place | On the multi-hop and global slices, graph-enabled strategies beat `direct` on correctness with statistical significance. On the lookup slice they are not worse beyond the gate tolerance. Otherwise graph retrieval is not enabled by default. | Eval |
| QR-QUAL-07 | Tables and figures | Recall@10 on the table and figure slices within 10 points of the text slice **(p)** | Eval |
| QR-QUAL-08 | Language of the answer | Matches the question's language in ≥ 0.98 of cases | Eval |
| QR-QUAL-09 | Prompt injection | Instructions planted in documents are followed in ≤ 0.05 of the injection cases **(p)** | Eval |
| QR-QUAL-10 | Public benchmarks | Results on the selected public benchmarks are published with every release, with the exact configuration. No fixed target. | Inspect |

## Latency (LAT)

On RH-1 with the default stack, unless stated otherwise.

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-LAT-01 | `retrieve` including reranking | p95 ≤ 2 s **(p)** | Bench |
| QR-LAT-02 | `ask`, time to first answer token, local model on CPU | p50 ≤ 10 s, p95 ≤ 20 s **(p)** | Bench |
| QR-LAT-03 | `ask`, time to first answer token, local GPU (RH-3) or a hosted model | p50 ≤ 3 s **(p)** | Bench |
| QR-LAT-04 | `ask`, complete answer of up to 200 tokens, local model on CPU | p50 ≤ 45 s **(p)** | Bench |
| QR-LAT-05 | Verification delay after the last answer token | p95 ≤ 1 s **(p)** | Bench |
| QR-LAT-06 | UI actions that don't call a model | p95 ≤ 200 ms | Bench |

QR-LAT-02 is the hardest target on a CPU. It constrains the default LLM's size and the context budget together, because reading the retrieved passages (prompt prefill) dominates time to first token on a CPU.

## Ingestion throughput (THR)

On RH-1, end to end until the document is searchable (graph enrichment excluded).

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-THR-01 | A 20-page born-digital PDF | Searchable within 60 s **(p)** | Bench |
| QR-THR-02 | Pages needing layout analysis (tables, multi-column) | ≥ 0.3 pages/s **(p)** | Bench |
| QR-THR-03 | Scanned pages needing OCR | ≤ 15 s per page **(p)** | Bench |
| QR-THR-04 | Bulk import while the engine is idle otherwise | 1,000 mixed documents overnight (≤ 10 h) **(p)** | Bench |

## Resources (RES)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-RES-01 | Peak memory of all engine processes plus the local LLM, during simultaneous ingestion and querying on RH-1 | ≤ 12 GB, leaving 4 GB for the operating system and a browser **(p)** | Bench |
| QR-RES-02 | Disk for the base install, excluding models | ≤ 2 GB **(p)** | Bench |
| QR-RES-03 | Disk for the default models | ≤ 6 GB **(p)** | Bench |
| QR-RES-04 | Index size per chunk, excluding originals and page images | ≤ 16 KB **(p)** | Bench |
| QR-RES-05 | CPU use when idle with no scheduled jobs | Near zero; no background polling | Bench |

## Scale (SCALE)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-SCALE-01 | Laptop profile, per collection, while meeting the latency targets | ≥ 250,000 chunks (roughly 50,000 pages) **(p)** | Bench |
| QR-SCALE-02 | Server profile, across collections, by adding workers and storage | ≥ 10 million chunks, `retrieve` p95 ≤ 1 s on RH-3 **(p)** | Bench |
| QR-SCALE-03 | Concurrent queries | Laptop: 2 at once without errors (more are queued). Server: 50 concurrent `retrieve` calls per API process **(p)** | Bench |

## Cost (COST)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-COST-01 | The default configuration runs with no paid service, no account and no API key. | Required | Inspect, test |
| QR-COST-02 | With hosted models, token usage and estimated cost are reported per query, per ingestion job and per evaluation run, and per-collection budgets are enforced. | Required | Test |
| QR-COST-03 | Before graph extraction starts, the engine estimates its cost: tokens and price for hosted models, CPU hours for local ones. | Estimate within ±30% of the actual **(p)** | Bench |

## Privacy (PRIV)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-PRIV-01 | Laptop profile with local models: no network traffic after the models are downloaded. | Zero egress; the full test suite passes with the network blocked | Test |
| QR-PRIV-02 | No telemetry or usage data is sent anywhere by default. | None | Inspect, test |
| QR-PRIV-03 | Any configured egress (hosted model, trace export) is shown in the UI and recorded in every trace. | Always | Test |
| QR-PRIV-04 | Deleted documents are purged from every derived store. | Within 10 minutes on RH-1 **(p)** | Test |
| QR-PRIV-05 | Secrets never appear in configuration files, logs, traces or error responses. | Never | Test |
| QR-PRIV-06 | Trace retention is configurable, and passages in traces can be redacted. | Default 30 days | Test |

## Security (SEC)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-SEC-01 | Untrusted documents are parsed in a child process with memory and time limits. | Always | Test |
| QR-SEC-02 | URL ingestion refuses private, loopback and link-local addresses unless explicitly allowed, and follows redirects only under the same rules. | Always | Test |
| QR-SEC-03 | Dependencies are scanned in CI. | No known critical vulnerabilities at release | Inspect |
| QR-SEC-04 | The API meets OWASP ASVS level 1. | At v1 release | Inspect |

## Reliability (REL)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-REL-01 | A crash during ingestion loses at most the stage in flight, and resuming creates no duplicates. | Killing the worker mid-job in a test leaves a consistent state | Test |
| QR-REL-02 | A corrupted or lost index is rebuilt from the system of record. | Rebuild produces identical retrieval results on DS-smoke | Test |
| QR-REL-03 | When an optional component fails, the engine degrades and says so instead of returning an error. | Covered by fault-injection tests for every optional stage | Test |

## Maintainability (MAINT)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-MAINT-01 | Layer and import rules hold. | Zero violations, enforced in CI | Test |
| QR-MAINT-02 | Test coverage of the domain and application layers. | ≥ 80% lines | Test |
| QR-MAINT-03 | Every adapter passes its port's contract suite. | All | Test |
| QR-MAINT-04 | Every significant architectural decision has an ADR. | All | Inspect |
| QR-MAINT-05 | A new adapter needs no change to domain or application code. | Shown by an example plugin | Demo |
| QR-MAINT-06 | A written compatibility policy covers the public API, the configuration schema and the on-disk data format. Breaking changes come with a migration path, and stored data from the previous minor release always upgrades automatically. | From v1.0 | Inspect, test |

## Portability (PORT)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-PORT-01 | Native install on Windows 11 (x86-64), macOS 14+ (Apple Silicon) and Ubuntu 22.04+ (x86-64 and arm64). | All pass the smoke suite in CI | Test |
| QR-PORT-02 | Container images for the server profile. | amd64 and arm64 | Test |

## Usability (USE)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-USE-01 | From a clean RH-1 machine to the first cited answer, following the README. | ≤ 15 minutes and ≤ 3 commands, on a 100 Mbit/s connection **(p)** | Demo |
| QR-USE-02 | The web UI is accessible. | WCAG 2.2 AA | Inspect, test |
| QR-USE-03 | Every error message says what happened and what to do next. | All user-facing errors | Inspect |

## Languages (I18N)

| ID | Requirement | Target | Verified by |
|----|-------------|--------|-------------|
| QR-I18N-01 | Ingestion and retrieval work for any Unicode script. Quality is measured on the language slices. | Every slice meets the per-slice targets above | Eval |
| QR-I18N-02 | The UI renders right-to-left and mixed-direction text correctly in answers and sources. | Arabic and Hebrew samples in UI tests | Test |
| QR-I18N-03 | UI text is in English in v1, with all strings externalised for translation. | All strings | Inspect |

# Constraints and scope

> Draft, 2026-10-17.

## Constraints

| ID | Constraint | Consequence |
|----|-----------|-------------|
| C-01 | Our code is AGPL-3.0. | Every dependency must have an AGPL-compatible licence. |
| C-02 | Default models must be under permissive licences (Apache-2.0, MIT or equivalent). | No model in the default configuration may carry non-commercial terms, research-only terms, revenue or user thresholds, or a use policy that passes through to our users. Such models can only be optional plugins, clearly labelled. |
| C-03 | No paid service may be required. | Hosted models are optional, always bring-your-own-key. |
| C-04 | The full feature set must run on RH-1 (16 GB, CPU only). | Heavy work is optional, budgeted and scheduled; defaults are sized for RH-1. |
| C-05 | Two maintainers working part-time. | Prefer mature libraries over custom code, embedded stores over services, few moving parts. |
| C-06 | Built in public. | Every change goes through a reviewed pull request; every significant decision gets an ADR. |

## Out of scope for v1

| Item | Why | What v1 still provides |
|------|-----|------------------------|
| User accounts, roles and document permissions | Large surface; not needed for the laptop and small-team cases first | Principal, tenant and access fields everywhere, and the access-policy seam (FR-EXT-01) |
| Agentic, multi-step retrieval | Hard to make reliable and fast on small CPU models | The query-strategy seam (FR-EXT-02) and retrieval exposed as an MCP tool |
| Connectors beyond files, folders and URLs | Each connector is its own maintenance burden | The source-connector port and plugin mechanism |
| Audio and video ingestion | Different pipeline, little demand in the target use cases | Nothing |
| Model fine-tuning | Out of the engine's job | Nothing |
| A hosted service run by us | Not our goal, and it would conflict with C-03 | Self-hosting guides |
| UI translations | English first | Externalised strings (QR-I18N-03) |
| Mobile-specific UI | Desktop browsers first | A responsive layout that works on small screens |

## Assumptions

| ID | Assumption | If it turns out false |
|----|-----------|-----------------------|
| A-01 | A small multilingual LLM on CPU can produce answers with correct citations when the format is enforced and verified. | Recommend a GPU or a hosted model for answers, keep retrieval-only fully local, and relax QR-QUAL targets for the CPU stack. |
| A-02 | Lightweight NER extraction gives a graph useful enough for local graph retrieval on CPU. | Make LLM extraction the only graph option and require a GPU or hosted model for it. |
| A-03 | Per-page routing keeps scanned and complex pages rare enough in typical corpora to meet the throughput targets. | Lower QR-THR targets for scan-heavy corpora and document it. |
| A-04 | Multilingual embedding and reranking models in the 0.3 to 0.6 billion parameter range are good enough across the language slices. | Offer language-specific models per collection. |
| A-05 | A small CPU support checker is accurate enough across the language slices to verify citations (ADR-0005). | Translate statement and passage to English before checking, or use an LLM checker for languages where the small model fails calibration. |

## Open questions

| ID | Question | Resolved by |
|----|----------|-------------|
| Q-01 | Which default LLM and context budget meet QR-LAT-02 on RH-1? | Spike S-1, then the LLM backends ADR |
| Q-02 | Which parser stack meets QR-THR on RH-1 with acceptable table quality? | Spike S-2, then the parsing ADR |
| Q-03 | What does graph extraction cost per page with a small local model, and is the result worth it (QR-QUAL-06)? | Spike S-3, then the GraphRAG ADR |
| Q-04 | Which embedder and reranker win on our language slices, since vendor benchmarks disagree? | Spike S-4, then the models ADR |
| Q-05 | Which public benchmarks do we report? | The [evaluation research](../research/evaluation.md#public-benchmarks-worth-reporting) proposes a set; confirmed in the evaluation ADR |
| Q-06 | The best small support checkers are trained mainly on English. Which one verifies citations reliably across our language slices? | Spike S-4 |

## Spikes

Short, time-boxed experiments on RH-1 that turn provisional targets into firm ones. Each produces a short report in `docs/spikes/` and feeds an ADR.

| ID | Spike | Measures | Feeds |
|----|-------|----------|-------|
| S-1 | Local LLM latency | Prefill and decode speed for candidate models and quantisations; time to first token at several context budgets; citation format compliance | QR-LAT-02, QR-LAT-04, A-01; LLM backends ADR |
| S-2 | Parsing throughput and quality | Pages per second and peak memory for candidate parsers on born-digital, complex and scanned pages; table structure accuracy on a small labelled set | QR-THR, QR-RES-01; parsing ADR |
| S-3 | Graph extraction cost and value | Tokens and time per page for NER and small-LLM extraction; entity-resolution quality; first QR-QUAL-06 measurement | A-02, QR-COST-03; GraphRAG ADR |
| S-4 | Embedders, rerankers and support checkers across languages | Recall@10 and nDCG@10 per language slice; support-checker agreement with human labels (Cohen's kappa) per slice; CPU latency per query | QR-QUAL-01, QR-QUAL-04, QR-QUAL-05, QR-LAT-01, QR-LAT-05, A-05; models ADR |

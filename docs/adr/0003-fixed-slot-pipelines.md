# ADR-0003: Fixed-slot pipelines with pluggable strategies, not free-form pipeline graphs

- **Status:** Proposed
- **Date:** 2026-10-17
- **Deciders:** Wadi, Ghassen
- **Requirements:** FR-GEN-08, FR-GEN-09, FR-EVAL-03, FR-OBS-01, FR-EXT-02, QR-QUAL-04, QR-QUAL-06

## Context and problem

A RAG query passes through many steps: rewriting, retrieval from several indexes, fusion, reranking, diversification, packing, generation and verification. Frameworks like Haystack let users wire components into arbitrary graphs. That flexibility is attractive, but every distinct graph is a new system to test, evaluate and debug. How should our pipelines be composed?

## Decision drivers

- Every configuration must be testable and comparable in evaluation (D-07).
- Traces must have the same shape across runs, so stages can be compared and regressions located (D-08).
- Users must be able to swap components and turn stages on and off.
- Multi-step, agentic behaviour must fit later without a redesign (D-09).

## Considered options

1. **Fixed sequence of typed slots**, with pluggable implementations per slot, and **strategies** that choose which slots and retrievers run.
2. **Free-form pipeline graphs** that users wire themselves.
3. **Agent-first:** an LLM decides at run time which tools to call and in what order.

## Decision

Option 1. The query pipeline has the slots described in the [query pipeline](../architecture/08-query.md): admit, understand, transform, retrieve, fuse, rerank, diversify, pack, generate, verify, respond. The ingestion pipeline has its own fixed stages. Configuration chooses the implementation of each slot, its parameters and whether optional slots run. A strategy decides which retrievers to use and how many passes to make. The agentic extension is a future strategy that loops over the retrieval slots within a budget.

### Consequences

- **Good:** a finite, documented set of behaviours. Every trace has the same structure, so per-stage evaluation metrics work for every configuration.
- **Good:** the degradation order under a tight budget can be defined once, because the slots are known.
- **Bad:** less freedom than arbitrary graphs. An unusual flow needs a new strategy, written in code and reviewed, rather than a configuration change. We accept this: it is the price of being testable and explainable.
- **Bad:** adding a new kind of slot is an architectural change that needs an ADR. That is intended.

### Confirmation

- Trace schema tests assert that every query produces one span per slot, including skipped slots marked as skipped.
- A new strategy must come with evaluation results on the slices it targets.

## Pros and cons of the options

### Fixed slots with strategies

- Good, because behaviour stays bounded, traceable and comparable.
- Good, because the agentic extension has a clear home.
- Bad, because it is less flexible for experiments that don't fit the slots.

### Free-form graphs

- Good, because it is maximally flexible.
- Bad, because the configuration space is unbounded, so evaluation results don't generalise and traces differ in shape.
- Bad, because graph wiring becomes a second programming language that users must debug.

### Agent-first

- Good, because it handles open-ended, multi-step questions.
- Bad, because it is slow and unreliable with small CPU models (assumption A-01), and harder to evaluate and to bound in cost.

## More information

- [Architecture: query pipeline](../architecture/08-query.md)
- [Architecture: ingestion pipeline](../architecture/07-ingestion.md)

# ADR-0004: Index generations built from independently keyed builds

- **Status:** Proposed
- **Date:** 2026-10-17
- **Deciders:** Wadi, Ghassen
- **Requirements:** FR-MOD-06, FR-ADM-03, FR-EVAL-09, FR-ING-10, QR-REL-02, UC-10

## Context and problem

Changing the embedding model, the chunker or the graph extractor invalidates some or all of an index. In many RAG systems this means re-ingesting everything while search is down or inconsistent, and there is no easy way back if the new model turns out worse. A CPU laptop makes this worse: a full rebuild can take hours, and graph extraction is the most expensive step of all. How do we change models and configuration safely?

## Decision drivers

- Search keeps working during a rebuild, and never mixes results from two models.
- A rebuild redoes only what changed. Re-embedding must not redo graph extraction.
- A new configuration can be evaluated before users see it, and rolled back afterwards.
- Every answer and evaluation run can say exactly which index produced it.

## Considered options

1. **Rebuild in place:** re-ingest everything into the existing index.
2. **One collection per configuration**, managed by the user.
3. **Index generations** made of independently keyed builds, with explicit activation and rollback.

## Decision

Option 3, as described in the [domain model](../architecture/06-domain-model.md#index-generations). A generation combines four builds: chunk set, lexical, vector and graph. Each build is keyed by its inputs and its own configuration, and unchanged builds are reused. Graph extraction results are additionally cached per chunk content hash. A query pins one generation when it starts. A new generation goes through `Building`, `Validating` and `Ready` before an operator, or a policy, activates it; the previous one is retired and can be reactivated.

Document additions and deletions update the active generation incrementally. New generations are only built when the configuration changes.

### Consequences

- **Good:** zero-downtime model changes, rollback, and evaluation gating before activation.
- **Good:** switching the embedding model re-embeds but keeps the chunks and the graph.
- **Good:** the generation fingerprint makes traces and evaluation runs reproducible.
- **Bad:** during a rebuild, disk use for the affected builds roughly doubles. The engine checks free space before starting and refuses to begin a build it cannot finish.
- **Bad:** more lifecycle states to implement and test. They are confined to the generation manager.

### Confirmation

- Tests switch the embedding model on a test collection and assert that queries keep working, that results never mix generations, and that the graph build is reused.
- QR-REL-02: deleting the index files and rebuilding gives identical retrieval results.

## Pros and cons of the options

### Rebuild in place

- Good, because it is simple.
- Bad, because search is degraded or inconsistent during the rebuild, and there is no rollback.

### One collection per configuration

- Good, because it isolates configurations.
- Bad, because it duplicates everything, including the expensive graph, and pushes the lifecycle onto users.

### Index generations

- Good, because it meets every driver.
- Bad, because of temporary extra disk and the added lifecycle complexity.

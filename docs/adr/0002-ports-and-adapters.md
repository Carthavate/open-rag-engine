# ADR-0002: Ports and adapters, with dependency rules enforced in CI

- **Status:** Proposed
- **Date:** 2026-10-17
- **Deciders:** Wadi, Ghassen
- **Requirements:** FR-API-03, FR-MOD-01 to FR-MOD-04, FR-EXT-01 to FR-EXT-03, QR-MAINT-01, QR-MAINT-03, QR-MAINT-05, C-05

## Context and problem

The engine must run the same logic as a library, behind an API server and from a CLI (D-01). It must swap storage, parsers and models between a CPU laptop, a GPU machine and a server without code changes (D-02). The RAG ecosystem moves fast: models, vector stores and parsers that are best today will be replaced within a year. How do we structure the code so that the core logic outlives its dependencies?

## Decision drivers

- Swap any model, store or parser through configuration.
- Test the core quickly and offline, without models or databases.
- Keep vendor types and SDK churn out of the core.
- Make the structure obvious to contributors and reviewers.

## Considered options

1. **Ports and adapters (hexagonal architecture):** the core defines ports; adapters implement them; dependency rules are enforced in CI.
2. **Build the core on an existing RAG framework** (LangChain, LlamaIndex or Haystack), using its abstractions as our domain model.
3. **Classic layering without ports:** services call database and model clients directly.

## Decision

Option 1, as described in [layers and dependency rules](../architecture/04-layers.md). The domain and application layers own the model and the ports. Infrastructure adapters implement the ports, and only the composition root names concrete adapters. An import-contract linter enforces rules R-01 to R-05 in CI, and every adapter must pass its port's contract test suite (R-07).

Existing frameworks and libraries remain welcome **inside adapters**. A parser adapter can wrap a document-conversion library, and a store adapter can wrap a vector database client. They never define our domain types.

### Consequences

- **Good:** any backend change is a new adapter plus configuration. Domain tests need no network. The same services sit behind the API, the CLI, MCP and the library.
- **Good:** contract suites make "swappable" a tested property rather than a claim.
- **Bad:** more interfaces and mapping code than calling a framework directly. We keep ports few and coarse-grained, and accept the mapping cost.
- **Bad:** we re-implement some things frameworks give for free (pipeline plumbing, retries). These are small, and owning them keeps behaviour predictable and traceable.

### Confirmation

- The import-contract check fails CI on any violation (QR-MAINT-01).
- Each port's contract suite runs against every registered adapter (QR-MAINT-03).
- An example third-party adapter plugin shows that no core change is needed (QR-MAINT-05).

## Pros and cons of the options

### Ports and adapters

- Good, because the core is independent of every vendor and testable offline.
- Good, because it matches the extension points we need (D-09): access policy, strategies, connectors.
- Bad, because of the extra interfaces and data mapping.

### Building on a RAG framework

- Good, because it is fast to start, with many integrations ready.
- Bad, because framework abstractions and versions churn, and their types would spread through our core.
- Bad, because tracing, provenance and evaluation would follow the framework's model rather than ours, which conflicts with D-06 to D-08.

### Classic layering without ports

- Good, because it is the least code at first.
- Bad, because swapping a backend means editing services, which breaks D-02.
- Bad, because tests need real databases and models.

## More information

- [Architecture: layers and dependency rules](../architecture/04-layers.md)
- [Architecture: ports and interfaces](../architecture/05-interfaces.md)

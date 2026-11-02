# Architecture decision records

Each significant decision gets one short record: the context, the options we weighed, what we chose and what it costs us. We use [MADR](https://adr.github.io/madr/) ([template](template.md)).

- **Status** is `Proposed` while the pull request is open, `Accepted` when it merges, and later `Superseded by ADR-NNNN` or `Deprecated`. Accepted records are never edited for substance; a change of mind is a new ADR.
- **Confirmation** says how we will know the decision is being followed, ideally by an automated check.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions with MADR | Proposed |
| [0002](0002-ports-and-adapters.md) | Ports and adapters, with dependency rules enforced in CI | Proposed |
| [0003](0003-fixed-slot-pipelines.md) | Fixed-slot pipelines with pluggable strategies, not free-form pipeline graphs | Proposed |
| [0004](0004-index-generations.md) | Index generations built from independently keyed builds | Proposed |
| [0005](0005-verified-citations.md) | Citations are enforced, verified and attributed, not trusted | Proposed |

## Planned

Technology decisions, which wait for the research and the spikes in the [requirements](../requirements/04-constraints-and-scope.md#spikes):

- Language and framework for the core, API server and web UI
- Storage: metadata store, lexical index and vector index, for the laptop and server profiles
- GraphRAG method and graph store
- Document parsing stack
- Default embedding and reranker models
- LLM backends and the default local model
- API style: REST, streaming and MCP
- Job queue, packaging and deployment

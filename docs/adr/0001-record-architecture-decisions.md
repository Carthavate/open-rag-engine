# ADR-0001: Record architecture decisions with MADR

- **Status:** Proposed
- **Date:** 2026-10-17
- **Deciders:** Wadi, Ghassen
- **Requirements:** C-06, QR-MAINT-04

## Context and problem

The project is built in public by two part-time maintainers who review each other's work. Decisions made in a chat or a call are lost; decisions buried in pull request threads are hard to find later. Contributors, and anyone judging the project, need to see not just what we chose but why, and what we gave up.

## Decision drivers

- Decisions must be findable and reviewable in the repository, next to the code.
- The format must be light enough that we actually write them.
- Superseded decisions must stay readable, so the history is honest.

## Considered options

1. MADR files in `docs/adr/`
2. A wiki or GitHub Discussions
3. No formal records; rely on pull request descriptions

## Decision

Option 1. Every significant decision gets a numbered MADR file in `docs/adr/`, reviewed in a pull request like code.

"Significant" means: it adds or changes a port, a layer dependency, a data store, a default model, a public API shape, a licence-relevant dependency, or anything that would be expensive to reverse.

### Consequences

- **Good:** decisions are versioned with the code, reviewed by the other maintainer, and linked from requirements and architecture.
- **Bad:** a little writing overhead per decision. We keep records short and use the [template](template.md).

### Confirmation

The pull request template asks whether an ADR is needed. A reviewer can block a pull request that makes a significant decision without one.

## Pros and cons of the options

### MADR in the repository

- Good, because it lives next to the code and goes through review.
- Good, because MADR is widely known and has a clear structure for options and consequences.
- Bad, because Markdown tables of pros and cons can grow long; we keep them short.

### Wiki or Discussions

- Good, because they are easy to edit.
- Bad, because they are not versioned with the code and are not reviewed.

### Pull request descriptions only

- Good, because it costs nothing extra.
- Bad, because decisions become impossible to find a few months later.

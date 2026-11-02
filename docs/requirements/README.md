# Requirements

> **Status:** draft, 2026-10-17. Quality targets marked *provisional* are checked against measurements in the benchmark spikes listed in [constraints and scope](04-constraints-and-scope.md#spikes) before the MVP is frozen.

This folder says what open-rag-engine must do and how well. It deliberately says nothing about how; that is the [architecture](../architecture/README.md).

| Document | Contents |
|----------|----------|
| [Stakeholders and use cases](01-stakeholders-and-use-cases.md) | Who it is for, and what they do with it |
| [Functional requirements](02-functional.md) | What the engine must do, by area |
| [Quality requirements](03-quality.md) | Answer quality, latency, resources, scale, cost, privacy, security, reliability, maintainability, portability, usability, languages |
| [Constraints and scope](04-constraints-and-scope.md) | Fixed constraints, what is out of v1, assumptions, open questions and spikes |

## Conventions

**IDs** are stable and never reused: `UC-` for use cases, `FR-<area>-NN` for functional requirements, `QR-<area>-NN` for quality requirements, `C-` for constraints. Architecture elements, ADRs, tests and evaluation runs refer to these IDs.

**Priority** for v1 uses MoSCoW:

| Priority | Meaning |
|----------|---------|
| **M**ust | v1 does not ship without it |
| **S**hould | Planned for v1; can slip to v1.x with a written reason |
| **C**ould | Only if time allows; the architecture must not block it |

**Verification** says how each requirement is proven:

| Method | Meaning |
|--------|---------|
| Test | An automated test in CI |
| Eval | A metric from the [evaluation loop](../architecture/09-evaluation.md) on a named dataset |
| Bench | A measurement on the reference hardware |
| Inspect | Review of code, configuration or documentation |
| Demo | Shown working end to end, recorded in the release notes |

**Sources** link each requirement to the [architecture drivers](../architecture/README.md#architecture-drivers) (`D-01` to `D-10`) that motivate it.

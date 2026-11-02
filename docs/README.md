# Documentation

Design documents for open-rag-engine. They are written before the code and change through pull requests like everything else.

## Reading order

| # | Document | What it answers | Status |
|---|----------|-----------------|--------|
| 1 | [Research](research/README.md) | What do existing open-source RAG engines do well, where do they fall short, and what should we do differently? | Draft |
| 2 | [Requirements](requirements/README.md) | Who is it for, what must it do, and how good, fast, cheap and private must it be? | Draft |
| 3 | [Architecture](architecture/README.md) | How is it structured: C4 context, containers and components, layers and interfaces, ingestion, query and evaluation pipelines | Draft |
| 4 | [Decision records](adr/README.md) | Why we chose each major technology and pattern, and what we gave up | Draft |

## Conventions

- **Diagrams** are Mermaid inside Markdown, so GitHub renders them and they diff like code. Architecture views follow the [C4 model](https://c4model.com/) (levels 1 to 3).
- **Decision records** use the [MADR](https://adr.github.io/madr/) format, one file per decision in `docs/adr/`, numbered in order (`0001-...md`). A superseded ADR is never deleted; it is marked as superseded and links to its replacement.
- **Requirements** have stable IDs (`FR-ING-01`, `QR-LAT-02`, ...), so architecture elements, ADRs, tests and evaluation runs can trace back to them.
- **Research** is a dated snapshot. Projects move quickly, so every claim links to its source and each page states its snapshot date at the top.

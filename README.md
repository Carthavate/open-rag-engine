# open-rag-engine

**An open-source RAG engine, built in the open by two engineers learning AI engineering.**

> 🏗️ **Status: designing the architecture.** There's no code yet. Watch or star the repo to follow along, and open a discussion if you have ideas.

## Why we're building it

We just finished a full course on retrieval-augmented generation and built a small RAG that runs in the browser for our learning platform, [AI Engineering Arena](https://github.com/TWadi/ai-engineering-arena). Now we want to build the real thing: a RAG engine you can run yourself, read end to end, and trust, because every answer shows exactly where it came from.

## What it will do

Planned, and subject to the architecture work:

- **Ingestion** of PDFs, Markdown and web pages, including tables and images, with structure-aware chunking.
- **Hybrid retrieval:** keyword search (BM25) and dense vectors, fused with reciprocal rank fusion, plus query rewriting, multi-query and MMR for diverse results.
- **Reranking** with a cross-encoder before anything reaches the model.
- **Grounded answers with citations.** When the sources don't support an answer, it says so instead of guessing.
- **Evaluation built in:** retrieval metrics (recall@k, MRR) and answer quality (faithfulness, relevance), run on every change.
- **Tracing:** every step of a query can be inspected.
- **Free to run:** fully local with open models, or with a hosted LLM using your own key.
- **API first**, with a small web UI on top.

## Principles

- **Free and open.** AGPL-3.0, and no paid service required.
- **Explainable.** You can see what was retrieved, why it ranked where it did, and what the model was sent.
- **Measured.** Changes to retrieval or generation come with evaluation numbers.
- **Decisions are written down.** Architecture docs and decision records (ADRs) live in `docs/`.

## Roadmap

1. **Architecture** (now): requirements, design, first decision records.
2. **MVP:** ingest → hybrid retrieval → answer with citations, plus the evaluation harness.
3. **Quality:** reranking, query transformations, multimodal documents.
4. **Product:** API, web UI, deployment guide.

## Contributing

We review each other's work through pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md). Found a security issue? Please follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

[AGPL-3.0](LICENSE). You're free to use, modify and self-host it. If you run a modified version as a network service, you must share your changes under the same license.

## Team

- [Wadi](https://github.com/TWadi)
- [Ghassen](https://github.com/GhassenJamoussi99)

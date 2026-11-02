# open-rag-engine

**An open-source RAG engine, built in the open by two engineers learning AI engineering.**

> 🧪 **Status: first working version.** A command-line engine with the techniques from the RAG course: hybrid search, reciprocal rank fusion, multi-query, reranking and cited answers, all running locally on a laptop CPU. API, web UI, knowledge graph and scanned documents come next.

## Why we're building it

We just finished a full course on retrieval-augmented generation and built a small RAG that runs in the browser for our learning platform, [AI Engineering Arena](https://github.com/TWadi/ai-engineering-arena). Now we want to build the real thing: a RAG engine you can run yourself, read end to end, and trust, because every answer shows exactly where it came from.

## Try it

**On Windows, without installing anything else:** download Open RAG, the desktop app, from the
[latest release](https://github.com/Carthavate/open-rag-engine/releases/latest). Put the `.exe` and its `.bin` parts in
one folder and run the `.exe`. It brings its own models and works offline.

**From source:** you need Python 3.12+, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/).

```bash
uv sync
ollama pull qwen3:4b-instruct-2507-q4_K_M
cd examples                      # a small pump manual, in English and German
uv run ore ingest docs
uv run ore ask "Why does my pump keep turning itself off?"
uv run ore search "error E1042" --trace
uv run ore eval eval.jsonl
uv run ore chat
```

The first run downloads the embedding and reranker models (about 1 GB). Everything then runs offline.

A real answer from the example:

```text
$ ore ask "Wie viel kostet der Drucksensor?"
Der Drucksensor PS-12 kostet 39 Euro [1].
  [1] service.md
```

### What's inside

| Course technique | Where | Switch |
|---|---|---|
| Recursive, Markdown and semantic chunking | `chunking.py` | `[chunking] strategy` |
| Multilingual embeddings in Chroma | `store.py`, `factory.py` | `[embeddings] model` |
| Similarity, score threshold, MMR, metadata filters | `retrieval.py` | `[retrieval] search_type`, `--source` |
| BM25 keyword search + vectors, fused with reciprocal rank fusion | `retrieval.py`, `fusion.py` | `vector_weight`, `keyword_weight`, `rrf_k` |
| Multi-query (RAG-Fusion) | `fusion.py`, `pipeline.py` | `--multi-query` |
| Cross-encoder reranking | `rerank.py` | `[rerank]`, `--no-rerank` |
| Conversational follow-ups | `conversation.py` | `ore chat` |
| Cited answers that are checked, and abstention | `answer.py` | `[answer] min_rerank_score` |
| Retrieval evaluation (hit rate, MRR, recall) | `evaluation.py` | `ore eval` |

`ore serve` runs the same engine as a local API for the desktop app (categories, sections, background indexing, streamed answers), reachable only from this machine. See [ADR-0007](docs/adr/0007-desktop-app.md).

Every setting lives in [`ore.toml`](examples/ore.toml). `--trace` shows what each stage returned and how long it took.

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

1. **Architecture:** requirements, design, first decision records.
2. **MVP** (now): ingest → hybrid retrieval → reranking → answer with citations, plus the evaluation harness.
3. **Quality:** reranking, query transformations, multimodal documents.
4. **Product:** API, web UI, deployment guide.

## Contributing

We review each other's work through pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md). Found a security issue? Please follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

[AGPL-3.0](LICENSE). You're free to use, modify and self-host it. If you run a modified version as a network service, you must share your changes under the same license.

## Team

Open RAG is developed by:

- Wadi Touil: [GitHub](https://github.com/TWadi) · [LinkedIn](https://www.linkedin.com/in/wadi-touil-117472319/)
- Ghassen Jamoussi: [GitHub](https://github.com/GhassenJamoussi99) · [LinkedIn](https://www.linkedin.com/in/ghassen-jamoussi/)

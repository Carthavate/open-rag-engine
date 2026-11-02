# Stakeholders and use cases

> Draft, 2026-10-17.

## Target users

| ID | Who | Situation | What they need most |
|----|-----|-----------|---------------------|
| U-1 | **Individual on a laptop** (developer, researcher, student, analyst) | Has a pile of PDFs, notes, papers and web pages, often in more than one language. No GPU, no budget, cares about privacy. | Install in minutes, ingest a folder, ask questions, trust the answers because every one is cited down to the page |
| U-2 | **Small team self-hosting a knowledge base** (a lab, an NGO, a company department, a law or medical practice) | Documents that cannot be sent to a cloud service. One modest server, maybe a GPU, one part-time admin. | Private by default, few moving parts to operate, documents kept current, quality they can prove |
| U-3 | **Application developer** | Adding retrieval or question answering to their own product or agent. | A stable library, REST and MCP API; predictable behaviour; retrieval without being forced to use our LLM or UI |
| U-4 | **RAG practitioner or researcher** | Comparing chunking, retrieval, reranking or graph methods. | Swappable components, reproducible runs, per-stage metrics, public benchmark adapters |

**Secondary stakeholders**

- **Maintainers** (Wadi and Ghassen): the project is also our portfolio, so its design documents, code quality and published benchmark results must hold up to scrutiny by experienced engineers.
- **Contributors:** need clear architecture, contribution rules and plugin points.
- **Model and tool authors whose work we build on:** we respect their licences, and credit them.

## Use cases

| ID | Use case | Primary user | Priority |
|----|----------|--------------|----------|
| UC-01 | Ask a question over my documents and check the answer against its sources | U-1, U-2 | M |
| UC-02 | Ingest a folder of mixed documents: born-digital and scanned PDFs, office files, HTML, Markdown, in several languages | U-1, U-2 | M |
| UC-03 | Keep the index current: re-ingest changed files, remove deleted ones | U-2 | M |
| UC-04 | Ask about a table or a figure and see the exact region of the page the answer came from | U-1, U-2 | M |
| UC-05 | Ask a global question across the whole collection ("what are the main themes?", "how are X and Y related?") | U-1, U-2 | M |
| UC-06 | See why an answer was given: what was retrieved, how it ranked, what the model was sent | U-1, U-3, U-4 | M |
| UC-07 | Call retrieval or Q&A from my own application, or give an agent access through MCP | U-3 | M |
| UC-08 | Generate a test set from my collection, review it, and evaluate a configuration | U-2, U-4 | M |
| UC-09 | Compare two configurations and block a change that makes quality worse | U-2, U-4 | M |
| UC-10 | Switch the embedding model or the LLM without downtime, and see the effect on quality | U-2, U-4 | M |
| UC-11 | Run completely offline after the models have been downloaded | U-1, U-2 | M |
| UC-12 | Use a hosted LLM with my own key for better or faster answers, knowing exactly what leaves my machine | U-1, U-2 | M |
| UC-13 | Delete a document and be sure it is gone everywhere | U-2 | M |
| UC-14 | Explore the knowledge graph: entities, relations and the passages behind them | U-1, U-4 | S |

## Key scenarios

### UC-01: ask and check

1. The user picks a collection and asks a question in any language.
2. The engine streams an answer in the same language. Each statement carries numbered citations.
3. Clicking a citation opens the source document at the cited page with the passage, table cell or figure highlighted.
4. Statements whose support could not be verified are visibly marked. If the collection doesn't contain the answer, the engine says so and shows what it searched.

### UC-02: ingest a mixed folder

1. The operator points the engine at a folder, or drops files in the UI.
2. Each document shows its progress. Born-digital documents become searchable first; scanned pages follow after OCR; graph enrichment follows in the background.
3. When a document is partly unreadable, the report names the pages that failed and why. Everything else is indexed.

### UC-05: global question

1. The user asks "what are the main disagreements between these reports?"
2. The router recognises a global question and uses the graph's community structure to find the relevant parts of the collection.
3. The answer cites the original passages behind each point, never the engine's own generated summaries.

### UC-09: block a regression

1. A contributor changes the chunker in a pull request.
2. CI runs the smoke evaluation with small local models and compares against `main`.
3. Recall@10 after reranking drops significantly on the Arabic slice. The check fails and shows the cases and the stage where the right passages were lost.

### UC-10: change the embedding model

1. The operator changes the embedding model in the collection's configuration.
2. The engine builds a new index generation in the background, reusing the chunks and the graph. The old generation keeps serving queries.
3. The new generation is evaluated on the collection's dataset. If it is not worse beyond the tolerance, the operator activates it, and can roll back later.

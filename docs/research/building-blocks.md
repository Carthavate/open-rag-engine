# Building blocks: parsers, retrievers, models and runtimes

> Snapshot: 2026-10-17. Benchmarks are mostly self-reported by vendors; treat close scores as ties. Licences were checked on the linked pages, but this is not legal advice: we re-check every licence before a dependency becomes a default.

This page surveys the components an engine is built from, with one question in mind: **what can run well on a 16 GB laptop without a GPU, in any language, under licences compatible with AGPL-3.0 and free for our users to use commercially?**

## Licence filter

Code under Apache-2.0, MIT, BSD or AGPL combines fine with our AGPL-3.0 code. The traps are mostly in **model weights** and paid add-ons. Requirement C-02 keeps these out of the defaults:

| Trap | Examples found |
|------|----------------|
| Non-commercial weights or data | All Jina embedding and reranker models ([v3](https://jina.ai/models/jina-embeddings-v3/), [reranker v3](https://huggingface.co/jinaai/jina-reranker-v3)), Nemotron ColEmbed v2 ([card](https://huggingface.co/nvidia/nemotron-colembed-vl-4b-v2)), zerank-2, Bespoke-MiniCheck-7B, Patronus Lynx, GOT-OCR training data |
| Research-only bases | jina-embeddings-v4 and ColQwen2.5 (Qwen Research License on the base model), ColNomic-3B |
| Revenue or user thresholds | Marker/Surya weights (modified OpenRAIL-M: limits above USD 5M revenue or funding, plus a competitor clause, [licence](https://github.com/datalab-to/marker/blob/master/MODEL_LICENSE)), MinerU (separate licence above 100M MAU or USD 20M monthly revenue, [licence](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md)), Liquid LFM models |
| Use policies that pass through to our users | Llama 3.2 community licence, Gemma 3 and EmbeddingGemma terms ([terms](https://ai.google.dev/gemma/terms)) |
| Paid add-ons hiding in free packages | PyMuPDF's layout add-on is Polyform-Noncommercial or commercial, and recent pymupdf4llm activates it on import ([Artifex](https://artifex.com/blog/introducing-the-new-pymupdf4llm-now-including-layout)). Core PyMuPDF itself is AGPL and fine |

Good news: **Gemma 4 moved to Apache-2.0** ([card](https://huggingface.co/google/gemma-4-E4B-it)), and the Qwen3 and Qwen3.5 families, Granite, Ministral 3 and SmolLM3 are all Apache-2.0.

## Document parsing and OCR

The [OmniDocBench](https://github.com/opendatalab/OmniDocBench) v1.6 leaderboard (updated 2026-09-11) is now led by small vision-language models of about 1B parameters: PaddleOCR-VL-1.6 (96.34), MinerU2.5-Pro (95.75) and GLM-OCR (95.22) score above Gemini 3 Pro (92.91). Classic pipelines trail: MinerU pipeline 86.47, olmOCR 85.74, Marker 78.44.

| Tool | Licence | CPU feasibility | Strengths | Verdict for us |
|------|---------|-----------------|-----------|----------------|
| [Docling](https://github.com/docling-project/docling) | MIT, permissive model licences | About 3.1 s/page on 8 vCPU with layout and table models; about 6.2 GB peak memory; OCR on CPU much slower ([paper](https://arxiv.org/html/2501.17887), [report](https://arxiv.org/html/2408.09869)) | Many formats, TableFormer table structure, mature integrations | **Default layout parser candidate.** Run in a separate worker process because of its memory peak |
| [PaddleOCR 3.x](https://github.com/PaddlePaddle/PaddleOCR) (PP-OCRv5, PP-StructureV3) | Apache-2.0 | ONNX and OpenVINO on CPU | **109 languages**, cell-level table coordinates | **Default OCR candidate** for scanned pages in any script |
| [PaddleOCR-VL 1.5/1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6) | Apache-2.0 | 0.9B; runs on llama.cpp since March 2026; CPU speed unpublished | Top open-licence OmniDocBench score; table TEDS 94.76 | **Optional "hard page" parser**, after a CPU benchmark (spike S-2). Default on GPU |
| [GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) | MIT | No CPU path documented | 95.22 overall | GPU option |
| [Granite-Docling-258M](https://huggingface.co/ibm-granite/granite-docling-258M) | Apache-2.0 | Small; CPU speed unpublished | Integrated in Docling's VLM pipeline | Watch; non-English support is "experimental" |
| PyMuPDF core | AGPL-3.0 | Very fast text-layer extraction | Born-digital PDFs | **Fast path** for pages with a good text layer. Never install the layout add-on |
| [Unstructured](https://github.com/Unstructured-IO/unstructured) (open source) | Apache-2.0 | About 4.2 s/page | Many formats | The vendor says its paid API is clearly better at tables; not a default |
| Marker/Surya, MinerU | See licence filter | | Strong quality | Plugins only |

**Takeaways.** Route per page: text layer first, layout analysis where needed, OCR for scans, and a 1B vision model for the hardest pages only when enabled (FR-ING-04). No credible CPU pages-per-second figures exist for the new 1B parsers, so spike S-2 measures them.

## Visual document retrieval

[ViDoRe V3](https://arxiv.org/html/2601.08620) (ACL 2026, about 26k pages, queries in 6 languages) shows visual late-interaction retrievers beating text retrievers of the same size: Nemotron ColEmbed-3B 59.8 nDCG@10, ColQwen2.5 51.9, against Qwen3-Embedding-0.6B at 43.8, bge-m3 at 41.3 and BM25 at 20.3. Three findings matter more for us than the leaderboard:

1. **Text rerankers help far more than visual ones.** A text reranker added 13.2 points to a text pipeline; a visual reranker added 0.2 to a visual one.
2. **Describing pages as text is competitive.** Having a vision model describe each page and indexing the description as text beat multi-vector visual encoders on ViDoRe V2 ([SERVAL](https://arxiv.org/html/2509.15432v1)).
3. **Multi-vector indexes are huge.** About 1,150 vectors of 128 dimensions per page is roughly 290 KB per page in fp16, against about 4 KB for one dense vector: 29 GB versus 0.4 GB for 100k pages (our calculation).

Small visual retrievers that fit a CPU (ColModernVBERT, 250M, [MIT](https://huggingface.co/ModernVBERT/colmodernvbert)) are English-only, and most permissive multilingual ones need a GPU ([Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B), Apache-2.0).

**Takeaway.** Visual retrieval stays an optional retriever (FR-RET-11). The default makes figures and visual pages searchable through text descriptions (FR-ING-08), which also benefits from the text reranker.

## Multilingual text embedders

| Model | Size | Context | Licence | MMTEB (mean) |
|-------|------|---------|---------|--------------|
| [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 0.6B, 32–1024 dims (Matryoshka) | 32K | Apache-2.0 | 64.33 |
| [multilingual-e5-large-instruct](https://huggingface.co/intfloat/multilingual-e5-large-instruct) | 560M | 512 | MIT | 63.22 |
| [bge-m3](https://huggingface.co/BAAI/bge-m3) | about 568M; dense, sparse and multi-vector from one model | 8K | MIT | 59.56 |
| [granite-embedding-311m-multilingual-r2](https://huggingface.co/ibm-granite/granite-embedding-311m-multilingual-r2) | 311M, 768 dims (Matryoshka to 128) | 32K | Apache-2.0 | not reported (multilingual retrieval 65.2) |
| granite-embedding-97m-multilingual-r2 | 97M, 384 dims | | Apache-2.0 | not reported (multilingual retrieval 60.3) |
| [gte-multilingual-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) | 305M, also sparse | 8K | Apache-2.0 | not found |
| [Snowflake Arctic Embed L v2.0](https://huggingface.co/Snowflake/snowflake-arctic-embed-l-v2.0) | 568M | 8K | Apache-2.0 | not found |
| EmbeddingGemma-300M, jina v3/v5 | | | Licence filter | Excluded |

**Takeaway.** Qwen3-Embedding-0.6B is the strongest permissive model with a verified multilingual score; Granite r2 (311M or 97M) is the lighter choice for weaker laptops. Matryoshka truncation to 256 or 512 dimensions trades a little quality for a much smaller index. Spike S-4 decides on our own language slices.

## Multilingual rerankers

The two vendor evaluations we found **contradict each other**. Qwen's table puts [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) first among small models (MMTEB-R 66.36, against 58.36 for bge-reranker-v2-m3). Jina's table puts [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) first on MIRACL (69.32, against 57.70 for Qwen3-Reranker-0.6B) ([source](https://huggingface.co/jinaai/jina-reranker-v3)).

| Model | Size | Licence | Note |
|-------|------|---------|------|
| [gte-multilingual-reranker-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base) | 306M encoder, 8K context, 70+ languages | Apache-2.0 | Likely the fastest on CPU |
| bge-reranker-v2-m3 | 0.6B encoder | Apache-2.0 | Strong on MIRACL |
| Qwen3-Reranker-0.6B | 0.6B decoder, 32K context | Apache-2.0 | Strong in Qwen's evaluation; slower on CPU |
| [mxbai-rerank-base-v2](https://huggingface.co/mixedbread-ai/mxbai-rerank-base-v2) | 0.5B | Apache-2.0 | 100+ languages |

**Takeaway.** Only our own evaluation can choose (spike S-4). That vendor tables disagree this much is itself an argument for the built-in evaluation loop.

## Small LLMs for CPU generation

| Model family | Licence | Languages | Note |
|--------------|---------|-----------|------|
| [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) | Apache-2.0 | Multilingual | Non-thinking, so no reasoning preamble to wait for; 262K context |
| [Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-4B) 0.8B / 2B / 4B / 9B | Apache-2.0 | 201 | Thinking on by default; can be turned off |
| [Gemma 4](https://huggingface.co/google/gemma-4-E4B-it) E2B / E4B | Apache-2.0 | 140+ | Text, image and audio input |
| [Granite 4.1](https://huggingface.co/ibm-granite/granite-4.1-3b) 3B / 8B | Apache-2.0 | 12 | RAG listed as a target use |
| [Phi-4-mini](https://huggingface.co/microsoft/Phi-4-mini-instruct) | MIT | 23 | Its card warns about non-English quality |
| [SmolLM3-3B](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) | Apache-2.0 | 6 European | |
| [Pleias-RAG-350M / 1B](https://huggingface.co/PleIAs/Pleias-RAG-1B) | Apache-2.0 | Main European languages | Trained to cite sources with quotes; the authors report about 20 s per complex answer on a CPU with 8 GB |
| Llama 3.2, Gemma 3, LFM2 | Licence filter | | Excluded |

Decode speeds reported for a 12 GB laptop with Ollama and Q4 quantisation ([It's FOSS](https://itsfoss.com/testing-local-llms-without-gpu), low confidence): Qwen3 0.6B about 35 tokens/s, Gemma 4 E2B about 10, Granite 4 3B about 9, Phi-4-mini about 7. **On a CPU, reading the retrieved passages (prefill) usually dominates time to first token**, and we found no credible laptop prefill figures. That is why QR-LAT-02 is provisional and spike S-1 exists.

## Local inference runtimes

| Runtime | Licence | Fit |
|---------|---------|-----|
| [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) | MIT | **Best single runtime for a laptop.** One server provides generation, embeddings, reranking and grammar- or schema-constrained output |
| [Ollama](https://github.com/ollama/ollama) | MIT | Easiest install, including Windows. Embeddings yes, no documented rerank endpoint |
| [sentence-transformers](https://sbert.net/docs/sentence_transformer/usage/efficiency.html) with ONNX or OpenVINO | Apache-2.0 | In-process embedders and cross-encoders; OpenVINO int8 fastest on Intel CPUs in their benchmark |
| [fastembed](https://github.com/qdrant/fastembed) | Apache-2.0 | ONNX without PyTorch; limited multilingual model list |
| vLLM, text-embeddings-inference | Apache-2.0 | GPU and server profile; weak or no Windows story on CPU |

## Candidate default stacks

These are hypotheses for the spikes and the model ADRs, not decisions.

| Role | Laptop profile (CPU) | GPU upgrade |
|------|----------------------|-------------|
| Parsing | PyMuPDF text layer, Docling layout and tables, PP-OCRv5 for scans; PaddleOCR-VL for hard pages if spike S-2 allows | PaddleOCR-VL-1.6 or GLM-OCR |
| Embeddings | Qwen3-Embedding-0.6B, or Granite r2 311M / 97M on weaker machines | Qwen3-Embedding-4B or 8B |
| Lexical | BM25 with per-language analysis | Same |
| Reranker | gte-multilingual-reranker-base; Qwen3-Reranker-0.6B or bge-reranker-v2-m3 as "quality" mode | Qwen3-Reranker-4B |
| Generator | Qwen3-4B-Instruct-2507 or Gemma 4 E2B/E4B; a 1–2B model if spike S-1 shows the 4B models miss QR-LAT-02 | Qwen3.5-9B, Granite 4.1 8B, Ministral 3 |
| Visual retrieval | Off; page descriptions instead | Qwen3-VL-Embedding-2B |
| Runtime | llama.cpp server for the LLM; ONNX or OpenVINO in-process for encoders | vLLM, TEI |

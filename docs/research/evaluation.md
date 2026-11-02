# Evaluation: frameworks, judges and benchmarks

> Snapshot: 2026-10-17. Activity and licences were checked against GitHub and Hugging Face on that date.

## Frameworks

| Tool | Licence | State | What it does well | Limits for us |
|------|---------|-------|-------------------|---------------|
| [Ragas](https://github.com/vibrantlabsai/ragas) | Apache-2.0 | **Stalled**: last release January 2026, last commit February 2026 | The best-known RAG metric set; knowledge-graph-based test set generation | Long-standing failures with local judge models ([NaN faithfulness](https://github.com/vibrantlabsai/ragas/issues/1274), [parse errors](https://github.com/vibrantlabsai/ragas/issues/1150)) |
| [DeepEval](https://github.com/confident-ai/deepeval) | Apache-2.0 | Very active | Native pytest runner; synthetic "goldens" | Nearly all metrics need an LLM judge; its docs warn that custom (local) models may struggle; no ranking metrics |
| [TruLens](https://github.com/truera/trulens) | MIT | Active (Snowflake) | The "RAG triad": context relevance, groundedness, answer relevance | No retrieval ranking metrics |
| [Arize Phoenix](https://github.com/Arize-ai/phoenix) | **Elastic License 2.0** (source-available) | Very active | Tracing built on OpenTelemetry | Ranking metrics only from LLM annotations; licence rules it out as a dependency |
| [Opik](https://github.com/comet-ml/opik) | Apache-2.0 | Very active | Fully self-hostable tracing and evaluation | LLM-judged RAG metrics |
| [promptfoo](https://github.com/promptfoo/promptfoo) | MIT | Active; [acquired by OpenAI](https://openai.com/blog/openai-to-acquire-promptfoo) in March 2026 | CI-first; a GitHub Action | Model-graded RAG metrics |
| [ARES](https://github.com/stanford-futuredata/ARES) | Apache-2.0 | Dormant | Small fine-tuned judges plus prediction-powered inference for confidence intervals ([paper](https://arxiv.org/abs/2311.09476)) | Unmaintained |
| [RAGChecker](https://github.com/amazon-science/RAGChecker) | Apache-2.0 | Dormant | Claim-level metrics that separate retriever and generator errors, with a human meta-evaluation set ([paper](https://arxiv.org/abs/2408.08067)) | Example setup uses a 70B model |
| [Vectara open-rag-eval](https://github.com/vectara/open-rag-eval) | Apache-2.0 | Small, active | Works without golden answers (UMBRELA relevance, nuggets, citation faithfulness) | Requires an OpenAI key |

Deterministic retrieval metrics are best taken from mature IR libraries: [ranx](https://github.com/AmenRa/ranx), pytrec_eval, BEIR and `mteb`. [FlashRAG](https://github.com/RUC-NLPIR/FlashRAG) (MIT) ships loaders for 36 benchmark datasets.

**Conclusion.** No existing framework gives us per-stage retrieval metrics, CPU-friendly faithfulness checks, multilingual slices and a CI gate together. We build the evaluation loop into the engine (FR-EVAL-01 to FR-EVAL-09) and reuse IR libraries for the metric arithmetic, rather than taking a framework dependency.

## Small judges and support checkers that run locally

Scores below are the average on the [LLM-AggreFact](https://llm-aggrefact.github.io/) grounded fact-checking leaderboard, which looks dated.

| Model | Size | Score | Licence | Usable as a default |
|-------|------|-------|---------|---------------------|
| [FactCG-DeBERTa-L](https://huggingface.co/yaxili96/FactCG-DeBERTa-v3-Large) | 0.4B | 75.6 | MIT | Yes |
| [MiniCheck-Flan-T5-L](https://huggingface.co/lytang/MiniCheck-Flan-T5-Large) | 0.8B | 75.0 | MIT | Yes |
| [Vectara HHEM-2.1-Open](https://huggingface.co/vectara/hallucination_evaluation_model) | about 110M | not listed | Apache-2.0 | Yes |
| [Granite Guardian 3.3](https://huggingface.co/ibm-granite/granite-guardian-3.3-8b) | 8B | 76.5 | Apache-2.0 | Yes, as the heavier option |
| Bespoke-MiniCheck-7B, Patronus Lynx | 7–8B | | CC BY-NC | No |

Small fine-tuned checkers match much larger prompted models: MiniCheck reaches GPT-4-level grounding accuracy at a fraction of the cost ([EMNLP 2024](https://aclanthology.org/2024.emnlp-main.499)), and a 400M DeBERTa trained on RAGBench beat few-shot LLM judges ([paper](https://arxiv.org/abs/2407.11005)).

**Open issue for "any language":** these checkers are trained mainly on English. Multilingual faithfulness data exists ([MEMERAG](https://arxiv.org/abs/2502.17163): English, German, Spanish, French, Hindi; [MIRAGE-Bench](https://arxiv.org/abs/2410.13716): 18 languages), but we found no small multilingual checker with published scores. This becomes open question Q-06 in the requirements.

## How far to trust LLM judges

- **Good at ranking systems, weak on single items.** In the TREC 2024 RAG Track, automatic relevance labels ranked 77 systems much like NIST assessors did ([paper](https://arxiv.org/abs/2411.08275)). For individual citation-support labels, GPT-4o agreed exactly with humans only 56% of the time when labelling from scratch ([paper](https://arxiv.org/abs/2504.15205)).
- **Agreement metrics can flatter.** A 2026 study of 21 judges found that exact-match agreement overstated chance-corrected agreement (Cohen's kappa) by 33 to 41 points, and that judge rankings shifted by up to 14 places across benchmarks ([paper](https://arxiv.org/abs/2606.19544)).
- **Judges can be gamed,** especially when the same model also ranks or generates ([paper](https://arxiv.org/abs/2412.17156)).
- **Smaller judges are worse** at relevance labelling ([paper](https://arxiv.org/abs/2507.09483)).

**Consequences for our design:** deterministic metrics first; small calibrated checkers for faithfulness; LLM judges only where needed, calibrated against human labels with Cohen's kappa reported; the judge is never the generator (FR-EVAL-06).

## Citation evaluation

- [ALCE](https://arxiv.org/abs/2305.14627) defined citation precision and recall scored with an NLI model. It is still the reference design.
- Attribution judging is hard even for fine-tuned models: about 80% macro-F1 on [AttributionBench](https://arxiv.org/abs/2402.15089).
- **A correct citation is not proof the model used it.** Up to 57% of citations can be post-rationalised: the cited passage supports the claim, but the model did not rely on it ([paper](https://arxiv.org/abs/2412.18004)). A September 2026 reproduction found about 1 in 7 on Wikipedia QA ([paper](https://arxiv.org/abs/2609.23053)).

**Idea to adopt:** alongside citation precision and recall, a counterfactual "reliance" check on a sample: remove or perturb the cited passage and see whether the answer changes. It is expensive, so it belongs in nightly runs, not in every pull request.

## Public benchmarks worth reporting

| Purpose | Benchmarks |
|---------|-----------|
| Retrieval | [BEIR](https://arxiv.org/abs/2104.08663) subsets, [MMTEB](https://arxiv.org/abs/2502.13595) retrieval, [MIRACL](https://arxiv.org/abs/2210.09984) (18 languages), [BRIGHT](https://arxiv.org/abs/2407.12883) (reasoning-heavy) |
| Multi-hop, to test whether GraphRAG pays off | [HotpotQA](https://arxiv.org/abs/1809.09600), [2WikiMultiHopQA](https://arxiv.org/abs/2011.01060), [MuSiQue](https://arxiv.org/abs/2108.00573), [MultiHop-RAG](https://arxiv.org/abs/2401.15391) |
| End-to-end RAG | [FRAMES](https://arxiv.org/abs/2409.12941), [CRAG](https://arxiv.org/abs/2406.04744), [RAGBench](https://arxiv.org/abs/2407.11005), [MTRAG](https://arxiv.org/abs/2501.03468) (multi-turn) |
| Citations | [ALCE](https://arxiv.org/abs/2305.14627) |
| Visual documents | [ViDoRe V3](https://arxiv.org/abs/2601.08620) |
| Text plus tables | [T²-RAGBench](https://arxiv.org/abs/2506.12071) |

## Recommended loop

Our [evaluation loop](../architecture/09-evaluation.md) follows these layers:

1. **Deterministic, no model:** recall@k, nDCG@10 and MRR per pipeline stage, as an ablation matrix (BM25, dense, fusion, multi-query, MMR, reranking), plus latency, memory and index size on the reference laptop.
2. **Small checkers on CPU:** claim-level faithfulness and citation precision and recall with a sub-1B MIT or Apache checker; exact match and F1 on short-answer benchmarks.
3. **Optional LLM judge:** a local Apache-licensed 7–8B model or the user's own key, for relevance, completeness and correctness. Log the judge, prompt hash and seed; calibrate on 100–200 human labels; report kappa; swap positions in pairwise comparisons; never judge with the generator.
4. **Test sets from the user's own corpus**, frozen, versioned and spot-checked by a person.
5. **Confidence intervals** on every comparison.
6. **CI:** a small CPU smoke set on every pull request; full runs and public benchmarks nightly. [Khoj](https://blog.khoj.dev/posts/evaluate-khoj-quality/) already publishes benchmark results from a GitHub workflow anyone can fork, which is the transparency bar to match.

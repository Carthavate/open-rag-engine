# ADR-0005: Citations are enforced, verified and attributed, not trusted

- **Status:** Proposed
- **Date:** 2026-10-17
- **Deciders:** Wadi, Ghassen
- **Requirements:** FR-GEN-02 to FR-GEN-05, FR-GEN-07, FR-GRAPH-07, QR-QUAL-01 to QR-QUAL-03, QR-LAT-05

## Context and problem

Citations are the core promise of the engine: every answer shows where it came from. Small local models, which we must support (D-02), often forget to cite, cite the wrong passage, or invent a source label. In AI Engineering Arena we used post-hoc attribution only: generate freely, then match sentences to passages. That always produces citations, but it can attach a citation to a claim the passage doesn't support. How do we make citations trustworthy with small models?

## Decision drivers

- A shown citation must point to a passage the model actually saw, and that passage must support the statement.
- Unsupported statements must be visible to the user, not silently kept.
- It must work with small CPU models, and add little latency (QR-LAT-05).
- It must work for answers built from graph retrieval too.

## Considered options

1. **Trust the model:** ask for citations in the prompt and show what comes back.
2. **Post-hoc attribution only:** generate without citations, then attach the best-matching passage to each sentence.
3. **Enforce, verify, attribute:** require citations in the output format, verify every citation and statement against the cited passage, attempt attribution for uncited statements, and flag, remove or abstain according to policy.

## Decision

Option 3, as described in the [query pipeline](../architecture/08-query.md):

1. **Enforce.** Passages are labelled `[S1]`, `[S2]` and so on. The prompt requires a label after every statement, and when the backend supports constrained output, a schema or grammar enforces the format.
2. **Verify.** Each cited label must exist in the packed context (invariant I-04). A support checker (a CPU-friendly NLI model by default, an LLM optionally) decides whether the passage supports the statement.
3. **Attribute.** Statements without a citation get a post-hoc attribution attempt against the packed passages, as in the Arena and in RAGFlow's second citation pass.
4. **Locate.** Within each supporting chunk, the verifier finds the sentence or table cell that best supports the statement (exact match first, then fuzzy, then embedding alignment), so the UI can highlight the exact region, as Kotaemon does with quote anchors, without trusting the model to copy text exactly.
5. **Decide.** Unsupported statements are flagged or removed according to the collection's policy. If nothing is supported, the engine abstains. The answer carries a support status.
6. **Cite originals only.** Community summaries and other generated text are never citable; graph-based answers cite the chunks behind them (invariant I-05).

### Consequences

- **Good:** citations shown to users have been checked, and failures are visible.
- **Good:** verification verdicts give the evaluation loop faithfulness and citation metrics for free.
- **Bad:** extra compute per answer. Verification runs per statement while the answer streams, so most of it overlaps with generation.
- **Bad:** NLI models make mistakes, especially across languages. The support checker is calibrated against human labels like the judge (FR-EVAL-06), and an LLM checker is available for higher accuracy.

### Confirmation

- QR-QUAL-01 to QR-QUAL-03 are measured on every evaluation run.
- A test asserts that a citation to a label outside the packed context never reaches the response.

## Pros and cons of the options

### Trust the model

- Good, because it adds no latency.
- Bad, because small models produce missing and wrong citations, and users can't tell.

### Post-hoc attribution only

- Good, because every statement gets a citation, even from weak models.
- Bad, because the attached passage may not support the claim; it only resembles it.

### Enforce, verify, attribute

- Good, because it combines the strengths of both and makes failures visible.
- Bad, because it costs more compute and needs a calibrated support checker.

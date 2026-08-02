# Kestrel Evaluation

This document explains how Kestrel's evaluation supports the core design question for the Agentic Systems track:

> **Why use an agentic monitoring pipeline instead of a single well-prompted LLM call?**

Kestrel is evaluated as three separate components rather than as one undifferentiated benchmark:

- **Tier A** isolates the value of retaining catalyst state over time.
- **Tier B** isolates the value of evidence guards around the LLM confirmation step.
- **Tier C** measures the economic benefit of the two-pass pipeline end-to-end.

This separation is deliberate: each experiment answers a different question, and none is presented as evidence for a claim it does not test.

---

## Reproducing the evaluation

**Evaluated commit:** `d5bd984fc5f5d5415738217cc340036af07f1bff`

All reported results in the submission were generated from this commit.

### Tier A — deterministic state-machine evaluation

```bash
python -m eval.run_eval
```

No API key or network access is required.

### Tier B — guarded confirmation pass vs. single-call baseline

```bash
python -m eval.run_eval --classify
```

Requires:

```bash
export OPENAI_API_KEY=...
```

### Tier B — cheaper-model arm

```bash
python -m eval.run_eval --classify --model gpt-5.4-mini
```

This is the same evaluation as Tier B, using the cheaper model to test whether the quote-traceability guard remains useful when model reliability degrades.

### Tier C — two-pass stream replay

```bash
python -m eval.run_eval --stream
```

This evaluates the relevance filter and the resulting reduction in Pass-2 calls, tokens, and cost.

Results are printed to the terminal and written to `results.json`.

---

# Tier A — State machine vs. history-insensitive boolean

### Question

Does retaining catalyst state over multiple articles prevent false final confirmations?

### What is isolated

The catalyst state machine:

```text
unconfirmed → rumored → confirmed → invalidated
```

The experiment begins from pre-labeled article classifications, so it **does not** measure news retrieval or LLM extraction accuracy. It isolates the value of retaining state and applying transition rules.

### Baseline

A history-insensitive boolean baseline:

> If any article ever produces a `confirmed` classification, the catalyst is considered met.

The baseline does not model:

- source credibility,
- speculation vs. confirmation,
- invalidation,
- state transitions over time.

### Dataset

16 curated catalyst sequences covering cases such as:

- signed-then-blocked mergers,
- denied rumors,
- catalysts that were reported but never credibly confirmed,
- other confirmation/invalidation sequences.

### Result

| Method                      | Precision | False final confirmations |
| --------------------------- | --------: | ------------------------: |
| Kestrel state machine       |       1.0 |                         0 |
| History-insensitive boolean |       0.6 |                         6 |

### Interpretation

The result supports a narrow architectural claim:

> **For these curated sequences, explicitly retaining catalyst state eliminated false final confirmations produced by a history-insensitive boolean rule.**

Because the sequences begin from given classifications, this experiment does **not** establish end-to-end news classification accuracy.

---

# Tier B — Guarded confirmation pass vs. single-call baseline

### Question

Does the quote-traceability guard provide a reliability property that a single unguarded LLM call does not?

### What is isolated

Tier B evaluates the **confirmation step (Pass 2) plus evidence guards**.

It does **not** benchmark the full two-pass pipeline end-to-end. The economics of the full two-pass pipeline are measured separately in Tier C.

### Baseline

One LLM call per `(article, catalyst)` pair.

The baseline trusts the model's verdict and supporting quote as returned.

### Guarded path

The guarded path rejects a state-changing verdict unless the cited supporting quote appears verbatim in the stored article headline or summary.

This provides **traceability to source text**, not proof of semantic entailment, context, or source credibility.

### Dataset

18-case adversarial smoke-test set containing:

- clean confirmations,
- speculative language,
- forward-looking language,
- headline-only stubs,
- off-catalyst articles,
- other cases designed to tempt over-confirmation.

### Frontier-model result

Both the guarded and unguarded methods classified all 18 cases correctly:

| Method                    | Precision | Recall | Fabricated-quote rate |
| ------------------------- | --------: | -----: | --------------------: |
| Single call               |       1.0 |    1.0 |                   0.0 |
| Guarded confirmation pass |       1.0 |    1.0 |                   0.0 |

On this frontier-model smoke test, the guard did **not** improve verdict accuracy.

### Cheaper-model result

Using `gpt-5.4-mini`:

- 6 positive confirmation cases were evaluated.
- The single-call baseline returned a source-absent supporting quote on 1 case.
- The guarded path rejected that quote because it was not present verbatim in the stored source text.

| Method                    | Fabricated-quote rate |
| ------------------------- | --------------------: |
| Single call               |           1/6 = 16.7% |
| Guarded confirmation pass |     0 by construction |

### Interpretation

The experiment does **not** show that the guard improves classification accuracy.

It shows something narrower:

> **The guard provides a structural traceability constraint: a state-changing verdict cannot survive unless its cited evidence appears in the stored source text.**

The frontier-model result shows that this property may not improve outcomes when the model already behaves correctly. The cheaper-model arm shows the property becoming useful when the unguarded model produces unsupported evidence.

The cheaper-model result is based on one run over a small smoke-test set and should not be interpreted as a production hallucination rate.

---

# Tier C — Two-pass pipeline economics

### Question

Does the two-pass architecture reduce expensive LLM work while retaining relevant articles?

### What is isolated

The complete relevance-filtering stage:

```text
Article
   ↓
Pass 1: cheap relevance filter
   ↓
Only relevant pairs
   ↓
Pass 2: expensive confirmation judgment
```

### Baseline

A naive architecture that sends every `(article, catalyst)` pair directly to Pass 2.

### Dataset

One stream replay containing:

- 20 articles,
- 3 catalysts,
- 60 total `(article, catalyst)` pairs.

### Result

| Metric                              | Result |
| ----------------------------------- | -----: |
| Relevant-pair recall                |    1.0 |
| Pass-1 precision                    |  ~0.86 |
| Filter rate                         |   0.88 |
| Pass-2 calls with two-pass pipeline |      7 |
| Pass-2 calls with naive baseline    |     60 |
| Two-pass cost                       | $0.048 |
| Naive cost                          | $0.366 |
| Cost reduction                      |   ~87% |
| Token reduction                     |   ~86% |

### Interpretation

In this replay, Pass 1 retained every relevant pair while eliminating most unnecessary Pass-2 calls.

The result supports the following claim:

> **For this stream replay, the two-pass architecture substantially reduced expensive model calls, tokens, and cost while retaining all labeled relevant pairs.**

This is an economics result, not an end-to-end accuracy benchmark.

---

# Metrics

The evaluation reports the following metrics:

### Precision

The fraction of positive predictions that are correct.

For Kestrel, precision is especially important because false catalyst confirmations can trigger unnecessary user attention or incorrect investment decisions.

### Recall

The fraction of true positive cases that are detected.

Recall is especially important for the relevance filter: dropping a genuinely relevant article before Pass 2 is a failure of the two-pass pipeline.

### Hallucination / fabricated-quote rate

The fraction of confirmation cases where the model provides a supporting quote that does not appear verbatim in the stored source text.

For the guarded path, this metric is structurally forced to zero because unsupported quotes are rejected.

This metric measures **quote traceability**, not factual truth or semantic entailment.

---

# What the evaluation does not yet prove

The current evaluation deliberately does **not** claim production-level end-to-end monitoring accuracy.

Known limitations include:

- Tier A begins from hand-authored classifications.
- Tier B is a small adversarial smoke test.
- Tier C measures two-pass economics, not end-to-end classification accuracy.
- The evaluation sets are small and partly synthetic.
- No repeated-run variance or confidence intervals are reported yet.
- No full historical replay has yet measured whether Kestrel reaches the correct catalyst state at the correct time.
- No decision-quality or user-time-saved study has yet been completed.
- The quote guard checks substring presence in stored source text; it does not establish entailment, context, or source credibility.

The next evaluation steps are:

1. Repeat the cheaper-model experiment across at least three runs and report variance/confidence intervals.
2. Run a full configuration ablation:
   `single call → +guard → +two-pass → +state machine`.
3. Replay approximately 20 historical investment theses against chronological news streams and measure whether Kestrel reaches the correct state at the correct time.
4. Add calibration and persist per-condition evidence for historical evaluations.

---

# Summary

The evaluation separates three claims:

| Claim                                                                     | Evidence   |
| ------------------------------------------------------------------------- | ---------- |
| Retaining catalyst state prevents history-insensitive false confirmations | **Tier A** |
| Evidence guards enforce quote traceability around LLM confirmation        | **Tier B** |
| Two-pass filtering reduces expensive LLM work                             | **Tier C** |

The experiments are intentionally modest in scope. The goal is not to claim that Kestrel is already production-perfect, but to show which parts of the architecture have been measured, what those measurements support, and where validation remains incomplete.

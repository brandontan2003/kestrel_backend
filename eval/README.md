# Kestrel evaluation harness

Answers the one question the agentic-track judges ask — *why an agent, not a
single well-prompted call?* — with a measured baseline comparison.

## Two tiers

| Tier  | Isolates                                                           | Needs API key?         | Run                                  |
|-------|--------------------------------------------------------------------|------------------------|--------------------------------------|
| **A** | the **state machine** (source credibility + the four-state ladder) | no — deterministic     | `python -m eval.run_eval`            |
| **B** | the **guards + two-pass classifier** vs a single call              | yes (`OPENAI_API_KEY`) | `python -m eval.run_eval --classify` |

Both compare against the naive thing you'd build first:

- **Tier A baseline** — a boolean: *any article that "confirmed" it ⇒ met.* No
  source check, no invalidation, no ladder.
- **Tier B baseline** — [`baseline.py`](baseline.py): one LLM call per
  (article, catalyst) pair, verdict trusted as-is. Same model as the full
  pipeline's Pass 2, so the comparison isolates architecture, not model choice.

Results print as a table and write to `results.json` for the write-up appendix.

## What the seed data shows (and its limits)

The committed `labeled_sequences.jsonl` (6 cases) and `labeled_pairs.jsonl`
(4 pairs) are **illustrative seeds** — enough to prove the harness runs and show
the *shape* of the result (on the seed set the boolean baseline posts two false
confirmations the state machine eliminates). They are **not** a publishable
sample size.

**Before you cite a number in the write-up:** grow both files to a real sample —
aim for ≥30–50 labeled pairs across several tickers and ≥15 sequences, label
them yourself, and report the sample size and confusion matrix, not just a
headline. That is the difference between a 3 and a 5 on the Evidence pillar.

## Labeled formats

`labeled_sequences.jsonl` (Tier A) — one JSON object per line:
```json
{"case": "name", "gold_met": false,
 "steps": [{"proposed_state": "confirmed", "source_kind": "speculation"}]}
```
`proposed_state` ∈ `no_change|rumored|confirmed|invalidated`;
`source_kind` ∈ `primary|reporting|speculation`.

`labeled_pairs.jsonl` (Tier B) — one JSON object per line:
```json
{"catalyst": {"id": "c_gpu", "description": "..."},
 "article": {"headline": "...", "summary": "...", "source": "reporting",
             "url": "https://...", "published_at": "2026-03-18T00:00:00Z"},
 "gold_confirmed": true}
```

## Metrics

`metrics.py` is pure and unit-tested (`tests/unit/test_eval_metrics.py`).
`precision` is the one to watch: low precision = the system cries wolf, the
failure mode that costs a user money. `hallucination_rate` = fraction of
*confirmations* whose supporting quote wasn't found verbatim in the article;
the full pipeline forces it to 0 by construction, the single-call baseline
doesn't — that gap is the guard's measured value.

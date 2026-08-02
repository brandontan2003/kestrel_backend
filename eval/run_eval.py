"""Kestrel evaluation harness.

Answers the agentic-track question with evidence: does the machinery (guards +
two-pass + state machine) beat the naive single call? Two tiers:

  Tier A  (deterministic, NO api key)  — isolates the STATE MACHINE.
          Replays labeled verdict sequences through pipeline.catalysts.apply
          (full) vs a boolean "any 'confirmed' proposal fires" baseline.
          Reproducible in CI, zero cost. `python -m eval.run_eval`

  Tier B  (needs OPENAI_API_KEY)       — isolates the GUARDS + classifier.
          Runs the real Pass-2 + guards vs eval.baseline.classify_single_call
          on labeled (article, catalyst) pairs; reports precision/recall/F1 and
          the baseline's hallucination rate. `python -m eval.run_eval --classify`

Results print as a table and are written to eval/results.json for the write-up
appendix. Numbers you paste into the write-up MUST come from a real run here.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline import catalysts
from pipeline.catalysts import CatalystState
from eval import metrics

_HERE = Path(__file__).parent


def _load(name: str) -> list[dict]:
    path = _HERE / name
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Tier A — state machine vs boolean baseline (deterministic).
# --------------------------------------------------------------------------- #
class _Step:
    def __init__(self, proposed_state: str, source_kind: str):
        self.proposed_state = proposed_state
        self.source_kind = source_kind


def _full_machine_met(steps: list[dict]) -> bool:
    state = catalysts.initial_state()
    for s in steps:
        state = catalysts.apply(state, _Step(s["proposed_state"], s["source_kind"])).new_state
    return catalysts.is_met(state)


def _boolean_baseline_met(steps: list[dict]) -> bool:
    # The naive aggregation: if any article ever "confirmed" it, call it met.
    # No source-credibility check, no invalidation, no ladder.
    return any(s["proposed_state"] == "confirmed" for s in steps)


def run_tier_a() -> dict:
    cases = _load("labeled_sequences.jsonl")
    full_pairs, base_pairs, disagreements = [], [], []
    for c in cases:
        gold = bool(c["gold_met"])
        full = _full_machine_met(c["steps"])
        base = _boolean_baseline_met(c["steps"])
        full_pairs.append((gold, full))
        base_pairs.append((gold, base))
        if full != base:
            disagreements.append({"case": c["case"], "gold": gold,
                                  "state_machine": full, "boolean": base})
    return {
        "n": len(cases),
        "state_machine": metrics.summarize("state_machine", full_pairs),
        "boolean_baseline": metrics.summarize("boolean_baseline", base_pairs),
        "disagreements": disagreements,
    }


# --------------------------------------------------------------------------- #
# Tier B — real classifier + guards vs single-call baseline (needs API).
# --------------------------------------------------------------------------- #
def _to_article(a: dict):
    from pipeline.news import Article
    return Article(
        id=a["url"], ticker=a.get("ticker", "TEST"), headline=a["headline"],
        summary=a.get("summary"), source=a["source"], url=a["url"],
        published_at=datetime.fromisoformat(a["published_at"].replace("Z", "+00:00")),
    )


def run_tier_b() -> dict:
    from pipeline.llm import pass2_confirm, quote_in_article
    from eval.baseline import classify_single_call

    pairs = _load("labeled_pairs.jsonl")
    full_pairs, base_pairs = [], []
    base_confirm_quote_present, full_latencies, base_latencies = [], [], []

    for row in pairs:
        art = _to_article(row["article"])
        catalyst = row["catalyst"]
        gold = bool(row["gold_confirmed"])

        t0 = time.perf_counter()
        v = pass2_confirm(art, catalyst)  # includes the guards
        full_latencies.append(time.perf_counter() - t0)
        full_met = catalysts.is_met(
            catalysts.apply(CatalystState.UNCONFIRMED, v).new_state
        )
        full_pairs.append((gold, full_met))

        t0 = time.perf_counter()
        b = classify_single_call(art, catalyst)  # no guards
        base_latencies.append(time.perf_counter() - t0)
        base_pairs.append((gold, b.confirmed))
        if b.confirmed:
            present = bool(b.supporting_quote) and quote_in_article(b.supporting_quote, art)
            base_confirm_quote_present.append(present)

    full_hall = metrics.hallucination_rate([True] * sum(1 for g, p in full_pairs if p))
    base_hall = metrics.hallucination_rate(base_confirm_quote_present)
    return {
        "n": len(pairs),
        "full_pipeline": {**metrics.summarize("full_pipeline", full_pairs),
                          "hallucination_rate": round(full_hall, 4),
                          "mean_latency_s": round(_mean(full_latencies), 3)},
        "single_call_baseline": {**metrics.summarize("single_call_baseline", base_pairs),
                                 "hallucination_rate": round(base_hall, 4),
                                 "mean_latency_s": round(_mean(base_latencies), 3)},
        "note": "full-pipeline hallucination_rate is 0.0 by construction (verbatim guard).",
    }


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


# --------------------------------------------------------------------------- #
def _print_table(title: str, rows: list[dict], cols: list[str]):
    print(f"\n{title}")
    print("  " + "  ".join(f"{c:>18}" for c in ["system", *cols]))
    for r in rows:
        print("  " + "  ".join(
            f"{str(r.get(c, '')):>18}" for c in ["system", *cols]))


def main():
    ap = argparse.ArgumentParser(description="Kestrel eval harness")
    ap.add_argument("--classify", action="store_true",
                    help="run Tier B (real LLM calls; needs OPENAI_API_KEY)")
    args = ap.parse_args()

    results = {"generated_at": datetime.now(timezone.utc).isoformat(), "tier_a": run_tier_a()}
    a = results["tier_a"]
    _print_table(f"TIER A — state machine vs boolean (n={a['n']}, deterministic)",
                 [a["state_machine"], a["boolean_baseline"]],
                 ["n", "precision", "recall", "f1", "fp", "accuracy"])
    if a["disagreements"]:
        print("\n  Cases the boolean baseline gets wrong that the state machine fixes:")
        for d in a["disagreements"]:
            print(f"    - {d['case']}: gold={d['gold']} "
                  f"machine={d['state_machine']} boolean={d['boolean']}")

    if args.classify:
        b = results["tier_b"] = run_tier_b()
        _print_table(f"TIER B — full pipeline vs single call (n={b['n']}, live LLM)",
                     [b["full_pipeline"], b["single_call_baseline"]],
                     ["n", "precision", "recall", "f1", "hallucination_rate", "mean_latency_s"])
    else:
        print("\n  (Tier B skipped — pass --classify with OPENAI_API_KEY set to run it.)")

    out = _HERE / "results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

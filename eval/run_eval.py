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


def run_tier_b(model: str | None = None) -> dict:
    from pipeline.llm import pass2_confirm, quote_in_article
    from pipeline.usage import track_usage, UsageTally
    from eval.baseline import classify_single_call

    pairs = _load("labeled_pairs.jsonl")
    full_pairs, base_pairs = [], []
    base_confirm_quote_present, full_latencies, base_latencies = [], [], []
    full_usage, base_usage = UsageTally(), UsageTally()

    for row in pairs:
        art = _to_article(row["article"])
        catalyst = row["catalyst"]
        gold = bool(row["gold_confirmed"])

        t0 = time.perf_counter()
        with track_usage() as u_full:
            v = pass2_confirm(art, catalyst, model=model)  # includes the guards
        full_latencies.append(time.perf_counter() - t0)
        full_usage.merge(u_full)
        full_met = catalysts.is_met(
            catalysts.apply(CatalystState.UNCONFIRMED, v).new_state
        )
        full_pairs.append((gold, full_met))

        t0 = time.perf_counter()
        with track_usage() as u_base:
            b = classify_single_call(art, catalyst, model=model)  # no guards
        base_latencies.append(time.perf_counter() - t0)
        base_usage.merge(u_base)
        base_pairs.append((gold, b.confirmed))
        if b.confirmed:
            present = bool(b.supporting_quote) and quote_in_article(b.supporting_quote, art)
            base_confirm_quote_present.append(present)

    full_hall = metrics.hallucination_rate([True] * sum(1 for g, p in full_pairs if p))
    base_hall = metrics.hallucination_rate(base_confirm_quote_present)
    return {
        "n": len(pairs),
        "model": model or "default",
        "full_pipeline": {**metrics.summarize("full_pipeline", full_pairs),
                          "hallucination_rate": round(full_hall, 4),
                          "mean_latency_s": round(_mean(full_latencies), 3),
                          "usage": full_usage.summary()},
        "single_call_baseline": {**metrics.summarize("single_call_baseline", base_pairs),
                                 "hallucination_rate": round(base_hall, 4),
                                 "mean_latency_s": round(_mean(base_latencies), 3),
                                 "usage": base_usage.summary()},
        "note": ("full-pipeline hallucination_rate is 0.0 by construction (verbatim guard). "
                 "Cost is confirmation-pass only (not the full two-pass pipeline); "
                 "token counts are exact, dollar cost depends on pipeline.usage.PRICING."),
    }


def run_tier_c(model: str | None = None) -> dict:
    """End-to-end two-pass economics: Pass 1 (relevance) over a full article
    stream, Pass 2 only on survivors, vs. the naive 'Pass 2 on every pair'.

    Measures what the write-up's Constraints section asserts: the relevance
    filter's drop rate, Pass-1 recall (did it keep the genuinely relevant
    pairs?), calls/article, and the real token + cost saving. Needs a key.
    """
    from pipeline.llm import pass1_relevance, pass2_confirm
    from pipeline.usage import track_usage, UsageTally

    cfg = json.loads((_HERE / "stream.json").read_text())
    catalysts = cfg["catalysts"]
    ticker = cfg.get("ticker", "TEST")
    raw = cfg["articles"]
    for i, a in enumerate(raw):
        a.setdefault("url", f"stream://{ticker}/{i}")  # stable id for gold alignment
    articles = [_to_article({**a, "ticker": ticker}) for a in raw]

    # gold relevance pairs, keyed by article id (== url) + catalyst id
    gold_pairs = set()
    for a in raw:
        for cid in a.get("relevant_catalyst_ids", []):
            gold_pairs.add((a["url"], cid))
    total_pairs = len(articles) * len(catalysts)

    # --- Pass 1 (relevance filter) ---
    with track_usage() as u_pass1:
        survivors = pass1_relevance(articles, catalysts)
    survivor_set = {(art.id, cat["id"]) for art, cat in survivors}
    kept_gold = survivor_set & gold_pairs
    pass1_recall = round(len(kept_gold) / len(gold_pairs), 4) if gold_pairs else None
    pass1_precision = round(len(kept_gold) / len(survivor_set), 4) if survivor_set else None
    filter_rate = round(1 - len(survivor_set) / total_pairs, 4) if total_pairs else 0.0

    # --- Pass 2 on survivors only (the two-pass production path) ---
    with track_usage() as u_pass2_survivors:
        for art, cat in survivors:
            try:
                pass2_confirm(art, cat, model=model)
            except Exception:
                pass

    # --- Naive baseline: Pass 2 on EVERY article x catalyst pair ---
    with track_usage() as u_naive:
        for art in articles:
            for cat in catalysts:
                try:
                    pass2_confirm(art, cat, model=model)
                except Exception:
                    pass

    two_pass = UsageTally()
    two_pass.merge(u_pass1)
    two_pass.merge(u_pass2_survivors)
    tp_cost, naive_cost = two_pass.cost_usd(), u_naive.cost_usd()
    tp_tok = two_pass.input_tokens + two_pass.output_tokens
    naive_tok = u_naive.input_tokens + u_naive.output_tokens

    def pct(saved_from, saved_to):
        return round(1 - saved_to / saved_from, 4) if saved_from else None

    pass1_calls = u_pass1.calls  # batched chunks
    return {
        "articles": len(articles), "catalysts": len(catalysts), "total_pairs": total_pairs,
        "model": model or "default",
        "pass1": {"calls": pass1_calls, "kept_pairs": len(survivor_set),
                  "filter_rate": filter_rate, "recall": pass1_recall,
                  "precision": pass1_precision, "usage": u_pass1.summary()},
        "two_pass": {"pass2_calls": len(survivors),
                     "calls_per_article": round((pass1_calls + len(survivors)) / len(articles), 3),
                     "total_cost_usd": tp_cost, "total_tokens": tp_tok,
                     "pass1_usage": u_pass1.summary(), "pass2_usage": u_pass2_survivors.summary()},
        "naive_pass2_only": {"pass2_calls": total_pairs, "total_cost_usd": naive_cost,
                             "total_tokens": naive_tok, "usage": u_naive.summary()},
        "savings": {"cost_pct": pct(naive_cost, tp_cost) if (naive_cost and tp_cost is not None) else None,
                    "token_pct": pct(naive_tok, tp_tok),
                    "pass2_calls_pct": pct(total_pairs, len(survivors))},
        "note": ("Pass-1 recall < 1.0 means the filter dropped a genuinely relevant pair "
                 "(a false negative that Pass 2 never sees). Cost $ depends on pipeline.usage.PRICING."),
    }


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _fmt_pct(x) -> str:
    return f"{x*100:.0f}%" if isinstance(x, (int, float)) else "n/a"


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
    ap.add_argument("--stream", action="store_true",
                    help="run Tier C end-to-end two-pass economics (real LLM calls; needs OPENAI_API_KEY)")
    ap.add_argument("--model", default=None,
                    help="override the confirmation/baseline model (e.g. gpt-5.4-mini) for the cheap-model arm; Pass 1 stays on its own model")
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
        b = results["tier_b"] = run_tier_b(model=args.model)
        _print_table(f"TIER B — guarded confirmation pass vs single call (n={b['n']}, model={b['model']})",
                     [b["full_pipeline"], b["single_call_baseline"]],
                     ["n", "precision", "recall", "f1", "hallucination_rate", "mean_latency_s"])
        # cost / token table (token counts exact; $ depends on pipeline.usage.PRICING)
        cost_rows = []
        for r in (b["full_pipeline"], b["single_call_baseline"]):
            u = r["usage"]
            cost_rows.append({
                "system": r["system"],
                "tokens/call": u["tokens_per_call"],
                "cost/call($)": u["cost_per_call_usd"] if u["cost_per_call_usd"] is not None else "SET PRICING",
                "total_cost($)": u["cost_usd"] if u["cost_usd"] is not None else "SET PRICING",
            })
        _print_table("        cost & tokens (counts exact; $ from pipeline.usage.PRICING)",
                     cost_rows, ["tokens/call", "cost/call($)", "total_cost($)"])
    else:
        print("\n  (Tier B skipped — pass --classify with OPENAI_API_KEY set to run it.)")

    if args.stream:
        c = results["tier_c"] = run_tier_c(model=args.model)
        p1, tp, nv, sv = c["pass1"], c["two_pass"], c["naive_pass2_only"], c["savings"]
        print(f"\nTIER C — end-to-end two-pass economics "
              f"({c['articles']} articles x {c['catalysts']} catalysts = {c['total_pairs']} pairs)")
        print(f"  Pass 1 filter: kept {p1['kept_pairs']}/{c['total_pairs']} pairs "
              f"(filter_rate {p1['filter_rate']}), recall {p1['recall']}, "
              f"in {p1['calls']} batched call(s)")
        _print_table("  cost & tokens per sweep (counts exact; $ from PRICING)",
                     [{"system": "two_pass (real)", "pass2_calls": tp["pass2_calls"],
                       "tokens": tp["total_tokens"], "cost($)": tp["total_cost_usd"]},
                      {"system": "naive (pass2-all)", "pass2_calls": nv["pass2_calls"],
                       "tokens": nv["total_tokens"], "cost($)": nv["total_cost_usd"]}],
                     ["pass2_calls", "tokens", "cost($)"])
        print(f"  SAVINGS from the relevance filter: "
              f"{_fmt_pct(sv['cost_pct'])} cost, {_fmt_pct(sv['token_pct'])} tokens, "
              f"{_fmt_pct(sv['pass2_calls_pct'])} of Pass-2 calls avoided")

    out = _HERE / "results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

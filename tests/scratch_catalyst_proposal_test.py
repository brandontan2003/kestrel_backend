"""MANUAL harness (not a pytest test) — makes real, paid OpenAI calls.

Does the reviewer propose catalyst edits when — and only when — warranted?
Two cases, so the output is interpretable:
  A. a catalyst the news has clearly OVERTAKEN (cancelled) -> should propose remove/update
  B. a well-worded catalyst with benign news             -> should propose nothing

Run from kestrel_backend with OPENAI_API_KEY in the environment:
    set -a; source .env.dev; set +a
    python -m tests.scratch_catalyst_proposal_test
"""
from datetime import datetime, timezone

from pipeline import proposals
from pipeline.news import make_article


def show(label, suggestions):
    print(f"=== {label} ===")
    cat = [s for s in suggestions if s.target == "catalyst"]
    if not suggestions:
        print("  (no proposals at all)\n")
        return
    for s in suggestions:
        print(f"  {s.target}/{s.action}  conf={s.confidence:.2f}  — {s.rationale}")
    print(f"  -> {len(cat)} catalyst proposal(s)\n")


# --- Case A: catalyst overtaken by news (should propose) --------------------- #
thesis_a = {
    "ticker": "ORCL", "quant_mode": "all", "catalyst_mode": "any",
    "quant_conditions": [],
    "catalysts": [{"id": "c1", "description": "Oracle wins a major new cloud contract", "enabled": True}],
}
eval_a = {
    "ticker": "ORCL", "signal": False, "status": "not_met",
    "reason": "no catalyst confirmed yet",
    "blocked_by": ["Oracle wins a major new cloud contract is unconfirmed, needs confirmed"],
    "quant_detail": [],
}
articles_a = [make_article(
    ticker="ORCL",
    headline="Oracle confirms it has cancelled the Stargate data-center expansion",
    summary="The company said Tuesday the multi-year expansion will not proceed this year.",
    url="https://example.com/orcl-cancel",
    published_at=datetime.now(timezone.utc), source="finnhub")]

# --- Case B: fine catalyst, benign news (should stay quiet) ------------------- #
thesis_b = {
    "ticker": "NVDA", "quant_mode": "all", "catalyst_mode": "any",
    "quant_conditions": [],
    "catalysts": [{"id": "c1", "description": "NVIDIA announces a new data-center GPU", "enabled": True}],
}
eval_b = {
    "ticker": "NVDA", "signal": False, "status": "not_met",
    "reason": "no catalyst confirmed yet",
    "blocked_by": ["NVIDIA announces a new data-center GPU is unconfirmed, needs confirmed"],
    "quant_detail": [],
}
articles_b = [make_article(
    ticker="NVDA",
    headline="Nvidia shares slip as broader tech sells off",
    summary="Analysts debated valuations across the chip sector on Monday.",
    url="https://example.com/nvda-slip",
    published_at=datetime.now(timezone.utc), source="finnhub")]


def test_main():
    print(f"proposal model in use: {proposals.PROPOSE_MODEL}\n")
    try:
        show("A: catalyst overtaken (expect a proposal)",
             proposals.suggest(thesis=thesis_a, evaluation=eval_a,
                               catalyst_states={"c1": "unconfirmed"}, articles=articles_a, metrics=()))
        show("B: fine catalyst, benign news (expect nothing)",
             proposals.suggest(thesis=thesis_b, evaluation=eval_b,
                               catalyst_states={"c1": "unconfirmed"}, articles=articles_b, metrics=()))
    except Exception as exc:
        print(f"!! call failed: {type(exc).__name__}: {exc}")
        print("   (if it's an auth/model error, that itself is useful signal)")

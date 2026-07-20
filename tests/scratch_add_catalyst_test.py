"""MANUAL harness (not a pytest test) — makes real, paid OpenAI calls.

Does the reviewer propose ADDING a catalyst for an event the user isn't tracking?
The thesis watches only "new data-center GPU". Each case feeds a DIFFERENT,
uncovered, material event and checks whether the reviewer surfaces it.

  A. strong: the event is across several headlines+bodies      -> expect ADD
  B. body-only: ONE article, bland headline, material BODY     -> expect ADD
                (this is the case that only works now that the
                 reviewer is given article bodies, not headlines)
  C. control: benign price/market chatter, no company event    -> expect NOTHING

Run from kestrel_backend with OPENAI_API_KEY in the environment:
    set -a; source .env.dev; set +a
    python -m tests.scratch_add_catalyst_test
"""
from datetime import datetime, timezone

from pipeline import proposals
from pipeline.news import make_article

thesis = {
    "ticker": "NVDA", "quant_mode": "all", "catalyst_mode": "any",
    "quant_conditions": [],
    "catalysts": [{"id": "c1", "description": "NVIDIA announces a new data-center GPU", "enabled": True}],
}
evaluation = {
    "ticker": "NVDA", "signal": False, "status": "not_met",
    "reason": "no catalyst confirmed yet",
    "blocked_by": ["NVIDIA announces a new data-center GPU is unconfirmed, needs confirmed"],
    "quant_detail": [],
}


def art(headline, body, url):
    return make_article(ticker="NVDA", headline=headline, summary=body,
                        url=url, published_at=datetime.now(timezone.utc), source="finnhub")


strong = [
    art("US moves to ban Nvidia's most advanced AI chips from export to China",
        "The administration issued rules barring export of Nvidia's top data-center accelerators to China without a license.",
        "u1"),
    art("Nvidia warns China export ban could cut billions from quarterly revenue",
        "In a filing, Nvidia said the restrictions could reduce quarterly revenue by several billion dollars.", "u2"),
    art("Analysts say fresh export curbs reshape Nvidia's China business",
        "Wall Street analysts cut estimates, citing the loss of a major market.", "u3"),
    art("Nvidia releases a minor driver update", "Routine software maintenance release.", "u4"),
]

# The headline gives NOTHING away — the materiality is entirely in the body.
# Under the old headline-only reviewer this produced no proposal.
body_only = [
    art("Chip stocks mixed as traders weigh rates",
        "Markets drifted as investors debated the rate path.", "b1"),
    art("Nvidia provides a business update",
        "Nvidia disclosed that US regulators have revoked its license to sell H20 chips in China, "
        "a market it had estimated at several billion dollars in annual revenue, effective immediately.", "b2"),
    art("Nvidia sponsors a university AI lab", "A philanthropic research partnership.", "b3"),
]

control = [
    art("Nvidia shares slip as broader tech sells off",
        "Analysts debated sector valuations on Monday; there was no company-specific news.", "c1"),
    art("Nvidia stock: what the charts say", "A technical-analysis opinion column.", "c2"),
]


def show(label, articles):
    print(f"=== {label} ===")
    sugg = proposals.suggest(thesis=thesis, evaluation=evaluation,
                             catalyst_states={"c1": "unconfirmed"}, articles=articles, metrics=())
    adds = [s for s in sugg if s.target == "catalyst" and s.action == "add"]
    if not sugg:
        print("  (no proposals)\n")
        return
    for s in sugg:
        cite = f"  [cites: {s.source_article_url}]" if s.source_article_url else ""
        print(f"  {s.target}/{s.action}  conf={s.confidence:.2f}  — {s.rationale}{cite}")
    print(f"  -> {len(adds)} catalyst ADD proposal(s)\n")


def test_main():
    print(f"proposal model: {proposals.PROPOSE_MODEL}\n")
    try:
        show("A: strong, event across headlines+bodies (expect ADD)", strong)
        show("B: ONE article, bland headline, material BODY (expect ADD)", body_only)
        show("C: benign market chatter (expect NOTHING)", control)
    except Exception as exc:
        print(f"!! call failed: {type(exc).__name__}: {exc}")

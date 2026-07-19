"""MANUAL labeled eval (real, paid OpenAI calls) — how good is the discovery prompt?

Each scenario is a thesis + recent news with a KNOWN right answer:
  expect="add"   -> a material, untracked, company-specific event is present; the
                    reviewer SHOULD propose adding a catalyst for it.
  expect="quiet" -> no such event (noise), OR it's already covered by a listed
                    catalyst, OR it merely confirms one (classifier's job) — the
                    reviewer should NOT propose a catalyst add.

Scores recall (positives caught) and specificity (negatives left alone), and
flags every miss so you can see WHERE it fails, not just a number.

Run from kestrel_backend:  set -a; source .env.dev; set +a
                           python -m tests.scratch_discovery_eval
"""
from datetime import datetime, timezone

from pipeline import proposals
from pipeline.news import make_article

_n = 0


def art(headline, body):
    global _n
    _n += 1
    return make_article(ticker="X", headline=headline, summary=body,
                        url=f"https://example.com/{_n}", published_at=datetime.now(timezone.utc),
                        source="finnhub")


# noise fillers, to force the reviewer to find signal among clutter (realistic)
NOISE = [
    art("Chip stocks mixed as traders weigh rates", "Markets drifted on macro data."),
    art("3 stocks to watch this week", "An opinion column listing popular tickers."),
]

SCENARIOS = [
    # ---- positives: material, untracked, company-specific -> expect ADD ----
    dict(name="export ban (regulatory)", ticker="NVDA",
         catalysts=["NVIDIA announces a new data-center GPU"], expect="add",
         articles=[art("US moves to ban Nvidia's advanced AI chips from export to China",
                       "New rules bar Nvidia's top accelerators from China without a license; Nvidia said it could cut billions from quarterly revenue.")] + NOISE),
    dict(name="bland headline / material body", ticker="NVDA",
         catalysts=["NVIDIA announces a new data-center GPU"], expect="add",
         articles=[art("Nvidia provides a business update",
                       "Nvidia disclosed US regulators revoked its license to sell H20 chips in China, a market worth several billion dollars annually, effective immediately.")] + NOISE),
    dict(name="FDA clinical hold (single article)", ticker="PFE",
         catalysts=["Pfizer reports Q3 results that beat consensus"], expect="add",
         articles=[art("Pfizer provides pipeline update",
                       "The FDA placed a clinical hold on Pfizer's lead oncology trial after a safety signal, halting enrollment; analysts called it a setback.")]),
    dict(name="FAA grounding (safety/regulatory)", ticker="BA",
         catalysts=["Boeing wins a large new aircraft order"], expect="add",
         articles=[art("FAA orders temporary grounding of Boeing 737 MAX fleet",
                       "Regulators grounded the fleet after an in-flight panel failure pending inspections.")] + NOISE),
    dict(name="DOJ criminal probe (legal)", ticker="TSLA",
         catalysts=["Tesla begins volume production of its next-gen vehicle"], expect="add",
         articles=[art("DOJ opens criminal investigation into Tesla Autopilot claims",
                       "Prosecutors are examining whether Tesla misled consumers and investors about its driver-assistance capabilities.")] + NOISE),
    dict(name="CEO abrupt resignation (executive)", ticker="DIS",
         catalysts=["Disney streaming subscriber growth reaccelerates"], expect="add",
         articles=[art("Disney CEO steps down effective immediately",
                       "The board announced the chief executive has resigned, with a search underway; shares fell in after-hours trading.")] + NOISE),

    # ---- negatives: no material untracked event -> expect QUIET ----
    dict(name="pure price/opinion noise", ticker="NVDA",
         catalysts=["NVIDIA announces a new data-center GPU"], expect="quiet",
         articles=NOISE + [art("Nvidia stock: what the charts say", "A technical-analysis opinion piece.")]),
    dict(name="confirms the existing catalyst (classifier's job)", ticker="NVDA",
         catalysts=["NVIDIA announces a new data-center GPU"], expect="quiet",
         articles=[art("Nvidia unveils Rubin Ultra, its new data-center GPU, shipping Q3",
                       "Nvidia announced its next-generation data-center accelerator at its developer conference.")] + NOISE),
    dict(name="already covered by another catalyst", ticker="AAPL",
         catalysts=["Apple unveils a new iPhone model", "Apple faces new EU antitrust action over the App Store"],
         expect="quiet",
         articles=[art("EU opens fresh antitrust case against Apple's App Store",
                       "Brussels regulators launched a new probe into Apple's App Store rules.")] + NOISE),
    dict(name="immaterial routine item", ticker="KO",
         catalysts=["Coca-Cola raises its dividend"], expect="quiet",
         articles=[art("Coca-Cola launches a new cherry-vanilla flavor",
                       "The limited-edition drink hits shelves next month."),
                   art("Analyst nudges Coca-Cola price target up $1", "A minor rating note.")] + NOISE),
    dict(name="macro selloff, no company event", ticker="MSFT",
         catalysts=["Microsoft announces an Azure price cut"], expect="quiet",
         articles=NOISE + [art("Tech shares fall as yields rise", "A broad market pullback on rate fears.")]),
]


def run():
    print(f"model: {proposals.PROPOSE_MODEL}  |  {len(SCENARIOS)} scenarios\n")
    tp = fp = tn = fn = 0
    misses = []
    for sc in SCENARIOS:
        thesis = {"ticker": sc["ticker"], "quant_mode": "all", "catalyst_mode": "any",
                  "quant_conditions": [],
                  "catalysts": [{"id": f"c{i}", "description": d, "enabled": True}
                                for i, d in enumerate(sc["catalysts"])]}
        evaluation = {"ticker": sc["ticker"], "signal": False, "status": "not_met",
                      "reason": "no catalyst confirmed yet", "blocked_by": ["catalyst unconfirmed"],
                      "quant_detail": []}
        states = {f"c{i}": "unconfirmed" for i in range(len(sc["catalysts"]))}
        sugg = proposals.suggest(thesis=thesis, evaluation=evaluation, catalyst_states=states,
                                 articles=sc["articles"], metrics=())
        adds = [s for s in sugg if s.target == "catalyst" and s.action == "add"]
        did_add = bool(adds)
        want_add = sc["expect"] == "add"
        ok = did_add == want_add
        if want_add and did_add: tp += 1
        elif want_add and not did_add: fn += 1; misses.append(("MISS (no add)", sc["name"]))
        elif not want_add and did_add: fp += 1; misses.append(("FALSE ADD", sc["name"], adds[0].rationale))
        else: tn += 1
        mark = "✓" if ok else "✗"
        conf = f" @{adds[0].confidence:.2f}" if adds else ""
        print(f"  {mark} [{sc['expect']:5}] {sc['name']:42} -> {'ADD'+conf if did_add else 'quiet'}")

    pos, neg = tp + fn, tn + fp
    print(f"\n  recall (material events caught):      {tp}/{pos}")
    print(f"  specificity (noise/covered ignored):  {tn}/{neg}")
    if misses:
        print("\n  failures:")
        for m in misses:
            print("   ", " — ".join(str(x) for x in m))
    else:
        print("\n  no misclassifications.")


def main():
    try:
        run()
    except Exception as exc:
        print(f"!! failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()

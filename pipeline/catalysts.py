"""Catalyst state machine (ml_plan.md §3).

A catalyst is not a boolean — news contradicts itself ("contract confirmed"
Tuesday, "contract delayed" Thursday), so each catalyst carries a state:

    unconfirmed ──▶ rumored ──▶ confirmed
         ▲             │            │
         └─────────────┴────────────┴──▶ invalidated
                                             │ (credible re-confirmation)
                                             └──▶ confirmed

Pass 2 (llm.py) proposes a state per (article, catalyst) pair; this module owns
the *rules* for whether that proposal actually moves the catalyst. It is pure:
no LLM, no I/O, no DB. It reads only two fields off a verdict (`proposed_state`,
`source_kind`) via a Protocol, so it never imports llm.py and unit tests can
drive it with plain stubs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# Re-exported for `from pipeline.catalysts import CatalystState` callers: this
# module owns the transition *rules*, `common` owns the vocabularies.
from common.enums.CatalystEnum import CatalystProposal, CatalystState


# The proposal vocabulary Pass 2 emits (llm.py CatalystVerdict.proposed_state).
# Derived from the enum so the two can never drift apart.
PROPOSALS = frozenset(p.value for p in CatalystProposal)

# Source categories credible enough to *confirm* or *invalidate*. Speculation
# (analyst guesses, "sources say") can only ever raise a rumor.
CREDIBLE_SOURCES = frozenset({"primary", "reporting"})


class VerdictLike(Protocol):
    """The slice of a Pass-2 verdict the state machine actually reads.

    Kept structural on purpose: catalysts.py must not depend on llm.py (which
    imports the OpenAI SDK). Anything with these two attributes works —
    the real CatalystVerdict, or a test stub.
    """
    proposed_state: str   # a CatalystProposal value
    source_kind: str      # "primary" | "reporting" | "speculation"


@dataclass(frozen=True)
class Transition:
    """Result of applying one verdict. `note` explains the outcome for the UI /
    the evaluator's `blocked_by` line (ml_plan.md §4) — e.g. why a `confirmed`
    proposal was capped at `rumored`.

    Refines the §7 contract (`-> (new_state, changed)`) with a human note; flag
    to Brandon before the contract is locked. `.as_tuple()` gives the plain
    shape if he'd rather keep it minimal.
    """
    new_state: CatalystState
    changed: bool
    note: str

    def as_tuple(self) -> tuple[str, bool]:
        return self.new_state.value, self.changed


def initial_state() -> CatalystState:
    """Every catalyst starts here."""
    return CatalystState.UNCONFIRMED


def is_met(state: CatalystState | str) -> bool:
    """Does this catalyst count as satisfied for signal purposes?

    Only `confirmed` counts. `rumored` is not enough; `invalidated` actively
    fails. The evaluator (§4) uses this when combining catalysts.
    """
    return CatalystState(state) is CatalystState.CONFIRMED


def apply(current: CatalystState | str, verdict: VerdictLike) -> Transition:
    """Apply one Pass-2 verdict to a catalyst's current state.

    Rules (ml_plan.md §3):
      * no_change            -> never moves the state.
      * confirmed/invalidated require a credible source; speculation is capped
        at `rumored` (for a would-be confirm) or ignored (for a would-be invalidate).
      * the positive ladder unconfirmed < rumored < confirmed never moves *down*
        on a weaker proposal — only `invalidated` (credible) can pull a confirmed
        catalyst back, and only a fresh `confirmed` can revive an invalidated one.
    """
    state = CatalystState(current)
    try:
        proposed = CatalystProposal(verdict.proposed_state)
    except ValueError:
        raise ValueError(
            f"unknown proposed_state {verdict.proposed_state!r}; expected one of {sorted(PROPOSALS)}"
        ) from None

    credible = verdict.source_kind in CREDIBLE_SOURCES

    if proposed is CatalystProposal.NO_CHANGE:
        return _stay(state, "article bears on the catalyst but does not move it")

    if proposed is CatalystProposal.INVALIDATED:
        if not credible:
            return _stay(state, "invalidation from a speculative source — ignored")
        return _to(state, CatalystState.INVALIDATED, "contradicted by a credible source")

    if proposed is CatalystProposal.CONFIRMED:
        if not credible:
            # A speculative "confirmation" is really just a rumor.
            proposed = CatalystProposal.RUMORED
        else:
            return _to(state, CatalystState.CONFIRMED, "confirmed by a credible source")

    # proposed is RUMORED (either directly, or downgraded from a speculative confirm)
    if state is CatalystState.UNCONFIRMED:
        return _to(state, CatalystState.RUMORED, "raised to rumored")
    # A rumor cannot downgrade a confirmation, nor revive an invalidated catalyst.
    reason = {
        CatalystState.RUMORED: "already rumored",
        CatalystState.CONFIRMED: "already confirmed — a rumor does not downgrade it",
        CatalystState.INVALIDATED: "invalidated — a rumor cannot revive it (needs a credible confirm)",
    }[state]
    return _stay(state, reason)


def _to(current: CatalystState, new: CatalystState, note: str) -> Transition:
    return Transition(new_state=new, changed=(new is not current), note=note)


def _stay(current: CatalystState, note: str) -> Transition:
    return Transition(new_state=current, changed=False, note=note)

"""Unit tests for the catalyst state machine (pipeline/catalysts.py).

These are pure: no LLM, no DB, no network. They drive `apply()` with plain
verdict stubs (the module reads only `proposed_state` + `source_kind` off a
verdict via a Protocol, exactly so it can be tested this way).

Each test asserts one transition RULE from the docstring / ml_plan.md §3, so a
failing test names the exact rule that broke. This suite is also the evidence
behind the write-up's Approach claims: "speculation is capped at rumored",
"a rumor never downgrades a confirmation", etc. — every one is a passing test.
"""

from dataclasses import dataclass

import pytest

from pipeline import catalysts
from pipeline.catalysts import CatalystProposal, CatalystState, apply, is_met, initial_state


@dataclass
class V:
    """Minimal verdict stub — the two fields the state machine reads."""
    proposed_state: str
    source_kind: str = "reporting"  # credible by default


CREDIBLE = ("primary", "reporting")
SPECULATIVE = "speculation"


# --------------------------------------------------------------------------- #
# is_met / initial_state — the "satisfied for signal purposes" contract.
# --------------------------------------------------------------------------- #
def test_only_confirmed_counts_as_met():
    assert is_met(CatalystState.CONFIRMED) is True
    for s in (CatalystState.UNCONFIRMED, CatalystState.RUMORED, CatalystState.INVALIDATED):
        assert is_met(s) is False, f"{s} must not count as met"


def test_is_met_accepts_raw_string():
    assert is_met("confirmed") is True
    assert is_met("rumored") is False


def test_every_catalyst_starts_unconfirmed():
    assert initial_state() is CatalystState.UNCONFIRMED


# --------------------------------------------------------------------------- #
# no_change never moves the state, from any starting point.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("start", list(CatalystState))
def test_no_change_is_inert(start):
    t = apply(start, V(CatalystProposal.NO_CHANGE.value))
    assert t.new_state is start
    assert t.changed is False


# --------------------------------------------------------------------------- #
# Confirmation requires a credible source.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("source", CREDIBLE)
def test_credible_confirm_from_unconfirmed(source):
    t = apply(CatalystState.UNCONFIRMED, V("confirmed", source))
    assert t.new_state is CatalystState.CONFIRMED
    assert t.changed is True


@pytest.mark.parametrize("source", CREDIBLE)
def test_credible_confirm_from_rumored(source):
    t = apply(CatalystState.RUMORED, V("confirmed", source))
    assert t.new_state is CatalystState.CONFIRMED


def test_speculative_confirm_is_only_a_rumor():
    # The headline guarantee of the whole project: a speculative "confirmation"
    # can never actually confirm — it is capped at rumored.
    t = apply(CatalystState.UNCONFIRMED, V("confirmed", SPECULATIVE))
    assert t.new_state is CatalystState.RUMORED
    assert t.changed is True


def test_speculative_confirm_does_not_downgrade_a_confirmed_catalyst():
    # confirmed --(speculative "confirm" => rumored proposal)--> stays confirmed
    t = apply(CatalystState.CONFIRMED, V("confirmed", SPECULATIVE))
    assert t.new_state is CatalystState.CONFIRMED
    assert t.changed is False


# --------------------------------------------------------------------------- #
# Invalidation requires a credible source; speculation can't invalidate.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("source", CREDIBLE)
def test_credible_invalidation_from_confirmed(source):
    t = apply(CatalystState.CONFIRMED, V("invalidated", source))
    assert t.new_state is CatalystState.INVALIDATED
    assert t.changed is True


def test_speculative_invalidation_is_ignored():
    t = apply(CatalystState.CONFIRMED, V("invalidated", SPECULATIVE))
    assert t.new_state is CatalystState.CONFIRMED
    assert t.changed is False


# --------------------------------------------------------------------------- #
# The positive ladder (unconfirmed < rumored < confirmed) never moves DOWN on a
# weaker proposal.
# --------------------------------------------------------------------------- #
def test_rumor_raises_unconfirmed():
    t = apply(CatalystState.UNCONFIRMED, V("rumored", SPECULATIVE))
    assert t.new_state is CatalystState.RUMORED
    assert t.changed is True


def test_rumor_on_already_rumored_is_inert():
    t = apply(CatalystState.RUMORED, V("rumored"))
    assert t.new_state is CatalystState.RUMORED
    assert t.changed is False


def test_rumor_never_downgrades_a_confirmation():
    t = apply(CatalystState.CONFIRMED, V("rumored"))
    assert t.new_state is CatalystState.CONFIRMED
    assert t.changed is False


def test_rumor_cannot_revive_an_invalidated_catalyst():
    t = apply(CatalystState.INVALIDATED, V("rumored"))
    assert t.new_state is CatalystState.INVALIDATED
    assert t.changed is False


def test_only_a_credible_confirm_revives_an_invalidated_catalyst():
    revive = apply(CatalystState.INVALIDATED, V("confirmed", "primary"))
    assert revive.new_state is CatalystState.CONFIRMED
    assert revive.changed is True


# --------------------------------------------------------------------------- #
# Robustness: an unknown proposal string is a hard error, not a silent no-op.
# --------------------------------------------------------------------------- #
def test_unknown_proposed_state_raises():
    with pytest.raises(ValueError):
        apply(CatalystState.UNCONFIRMED, V("definitely_confirmed"))


def test_transition_as_tuple_shape():
    t = apply(CatalystState.UNCONFIRMED, V("confirmed", "primary"))
    assert t.as_tuple() == ("confirmed", True)


# --------------------------------------------------------------------------- #
# End-to-end sequence: the "rumor Tuesday, confirmed Thursday" story that a
# boolean cannot model. This is the exact scenario in the write-up.
# --------------------------------------------------------------------------- #
def test_rumor_then_credible_confirm_then_speculative_noise():
    state = initial_state()
    # 1. A blog posts a rumor.
    state = apply(state, V("confirmed", SPECULATIVE)).new_state
    assert state is CatalystState.RUMORED
    # 2. A wire service confirms it.
    state = apply(state, V("confirmed", "primary")).new_state
    assert state is CatalystState.CONFIRMED
    # 3. A speculative "maybe it fell through" post must NOT unwind the confirm.
    state = apply(state, V("invalidated", SPECULATIVE)).new_state
    assert state is CatalystState.CONFIRMED
    assert is_met(state) is True

"""Unit tests for the thesis evaluator (pipeline/evaluator.py).

Pure: no LLM, no DB, no network. The load-bearing behaviour is three-valued
quant — a condition whose data came back None is `unknown`, and a thesis blocked
only by missing data is `incomplete`, never a silent `not_met`. That distinction
is the write-up's "a data outage never masquerades as a failed condition" claim,
proven here.

`status` is one of: firing | not_met | incomplete.
"""

import pytest

from common.enums.ThesesEnum import QuantModeEnum, CatalystModeEnum
from pipeline.evaluator import evaluate


def cond(metric="forward_pe", operator="<", value=40, enabled=True):
    return {"metric": metric, "operator": operator, "value": value, "enabled": enabled}


def res(value, passes):
    return {"value": value, "passes": passes}


def thesis(quant=None, catalysts=None, quant_mode="ALL", catalyst_mode="ALL", ticker="TEST"):
    return {
        "ticker": ticker,
        "quant_mode": quant_mode,
        "catalyst_mode": catalyst_mode,
        "quant_conditions": quant or [],
        "catalysts": catalysts or [],
    }


# --------------------------------------------------------------------------- #
# The three quant outcomes, ALL mode.
# --------------------------------------------------------------------------- #
def test_all_conditions_pass_fires():
    out = evaluate(thesis(quant=[cond()]), [res(31.2, True)], {})
    assert out["status"] == "firing"
    assert out["signal"] is True
    assert out["blocked_by"] == []


def test_a_definite_failure_is_not_met():
    out = evaluate(thesis(quant=[cond(value=28)]), [res(31.2, False)], {})
    assert out["status"] == "not_met"
    assert out["signal"] is False
    assert any("forward_pe" in b for b in out["blocked_by"])


def test_missing_data_is_incomplete_not_failed():
    # passes=None => couldn't evaluate. This must NOT read as not_met.
    out = evaluate(thesis(quant=[cond()]), [res(None, None)], {})
    assert out["status"] == "incomplete"
    assert out["signal"] is False
    assert any("couldn't evaluate" in b for b in out["blocked_by"])


def test_a_real_failure_dominates_an_unknown():
    # One condition fails outright, another is unknown -> the failure wins, so
    # the thesis is genuinely not_met (not merely incomplete).
    out = evaluate(
        thesis(quant=[cond(value=28), cond(metric="pb_ratio", value=2)]),
        [res(31.2, False), res(None, None)],
        {},
    )
    assert out["status"] == "not_met"


# --------------------------------------------------------------------------- #
# ANY mode.
# --------------------------------------------------------------------------- #
def test_any_mode_one_pass_is_enough():
    out = evaluate(
        thesis(quant=[cond(value=28), cond(metric="pb_ratio", value=2)], quant_mode="ANY"),
        [res(31.2, False), res(1.4, True)],
        {},
    )
    assert out["status"] == "firing"


def test_any_mode_no_pass_but_unknown_is_incomplete():
    out = evaluate(
        thesis(quant=[cond(value=28), cond(metric="pb_ratio", value=2)], quant_mode="ANY"),
        [res(31.2, False), res(None, None)],
        {},
    )
    assert out["status"] == "incomplete"


# --------------------------------------------------------------------------- #
# Catalyst combination + the quant/catalyst interaction.
# --------------------------------------------------------------------------- #
def test_unmet_catalyst_blocks_a_passing_quant():
    t = thesis(quant=[cond()], catalysts=[{"id": "c1", "description": "new GPU"}])
    out = evaluate(t, [res(31.2, True)], {"c1": "rumored"})
    assert out["status"] == "not_met"
    assert any("new GPU" in b for b in out["blocked_by"])


def test_confirmed_catalyst_plus_passing_quant_fires():
    t = thesis(quant=[cond()], catalysts=[{"id": "c1", "description": "new GPU"}])
    out = evaluate(t, [res(31.2, True)], {"c1": "confirmed"})
    assert out["status"] == "firing"


def test_missing_quant_data_with_unmet_catalyst_is_not_incomplete():
    # incomplete is reserved for "only data is missing". If a catalyst is also
    # unmet, the thesis is genuinely not_met.
    t = thesis(quant=[cond()], catalysts=[{"id": "c1", "description": "new GPU"}])
    out = evaluate(t, [res(None, None)], {"c1": "unconfirmed"})
    assert out["status"] == "not_met"


def test_none_required_catalyst_mode_ignores_catalysts():
    t = thesis(quant=[cond()], catalysts=[{"id": "c1", "description": "x"}],
               catalyst_mode="NONE_REQUIRED")
    out = evaluate(t, [res(31.2, True)], {"c1": "unconfirmed"})
    assert out["status"] == "firing"


def test_any_catalyst_mode_one_confirmed_is_enough():
    t = thesis(catalysts=[{"id": "a", "description": "x"}, {"id": "b", "description": "y"}],
               catalyst_mode="ANY")
    out = evaluate(t, [], {"a": "confirmed", "b": "unconfirmed"})
    assert out["signal"] is True


# --------------------------------------------------------------------------- #
# The case-normalization guard the code calls out explicitly: the backend's
# UPPERCASE enum values must not fall through to the "all" default.
# --------------------------------------------------------------------------- #
def test_uppercase_enum_modes_are_honoured():
    # Passing the actual enum objects (value "ANY") must behave as any-mode.
    out = evaluate(
        thesis(quant=[cond(value=28), cond(metric="pb_ratio", value=2)],
               quant_mode=QuantModeEnum.ANY),
        [res(31.2, False), res(1.4, True)],
        {},
    )
    assert out["status"] == "firing", "UPPERCASE ANY silently fell through to all-mode"


def test_none_required_enum_value():
    t = thesis(catalysts=[{"id": "c1", "description": "x"}],
               catalyst_mode=CatalystModeEnum.NONE_REQUIRED)
    out = evaluate(t, [], {"c1": "unconfirmed"})
    assert out["signal"] is True


# --------------------------------------------------------------------------- #
# Structural contract.
# --------------------------------------------------------------------------- #
def test_misaligned_results_raise():
    with pytest.raises(ValueError):
        evaluate(thesis(quant=[cond(), cond()]), [res(1, True)], {})


def test_output_has_the_documented_keys():
    out = evaluate(thesis(quant=[cond()]), [res(31.2, True)], {})
    for key in ("ticker", "signal", "status", "quant_ok", "catalysts_ok", "blocked_by", "reason"):
        assert key in out


def test_disabled_condition_does_not_gate():
    out = evaluate(thesis(quant=[cond(enabled=False)]), [res(None, None)], {})
    assert out["status"] == "firing"  # the only condition is disabled -> nothing gates

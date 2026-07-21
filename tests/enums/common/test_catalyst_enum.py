import pytest

from common.enums.CatalystEnum import CatalystState, CatalystProposal


@pytest.mark.parametrize("catalyst_enum_class, expected_values",
                         [(CatalystState, {"unconfirmed", "rumored", "confirmed", "invalidated"}),
                          (CatalystProposal, {"no_change", "rumored", "confirmed", "invalidated"})])
def test_enum_members(catalyst_enum_class, expected_values):
    actual_values = {member for member in catalyst_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("catalyst_enum_class, expected_values",
                         [(CatalystState, 4), (CatalystProposal, 4)])
def test_enum_length(catalyst_enum_class, expected_values):
    actual_values = {member.value for member in catalyst_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("catalyst_enum_class", [CatalystState, CatalystProposal])
def test_enum_invalid_value_raises_error(catalyst_enum_class):
    with pytest.raises(ValueError):
        catalyst_enum_class("invalid")

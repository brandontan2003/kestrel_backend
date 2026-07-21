import pytest

from common.enums.ThesesEnum import QuantModeEnum, ThesesStatusEnum, CatalystModeEnum


@pytest.mark.parametrize("catalyst_enum_class, expected_values",
                         [(QuantModeEnum, {"ALL", "ANY"}),
                          (CatalystModeEnum, {"ALL", "ANY", "NONE_REQUIRED"}),
                          (ThesesStatusEnum, {"TRACKING", "DELETED"})])
def test_enum_members(catalyst_enum_class, expected_values):
    actual_values = {member for member in catalyst_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("catalyst_enum_class, expected_values",
                         [(QuantModeEnum, 2), (CatalystModeEnum, 3), (ThesesStatusEnum, 2)])
def test_enum_length(catalyst_enum_class, expected_values):
    actual_values = {member.value for member in catalyst_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("catalyst_enum_class", [QuantModeEnum, CatalystModeEnum, ThesesStatusEnum])
def test_enum_invalid_value_raises_error(catalyst_enum_class):
    with pytest.raises(ValueError):
        catalyst_enum_class("invalid")

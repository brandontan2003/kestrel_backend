import pytest

from common.enums.AlertsEnum import AlertStatusEnum, AlertChannelsEnum


@pytest.mark.parametrize("alert_enum_class, expected_values",
                         [(AlertStatusEnum, {"NOT_SENT", "SENT", "IN_PROGRESS"}),
                          (AlertChannelsEnum, {"TELEGRAM", "EMAIL"})])
def test_enum_members(alert_enum_class, expected_values):
    actual_values = {member for member in alert_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("alert_enum_class, expected_values",
                         [(AlertStatusEnum, 3), (AlertChannelsEnum, 2)])
def test_enum_length(alert_enum_class, expected_values):
    actual_values = {member.value for member in alert_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("alert_enum_class", [AlertStatusEnum, AlertChannelsEnum])
def test_enum_invalid_value_raises_error(alert_enum_class):
    with pytest.raises(ValueError):
        alert_enum_class("invalid")

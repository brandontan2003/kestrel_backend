import pytest

from app.enums.UserEnum import UserStatusEnum


@pytest.mark.parametrize("user_enum_class, expected_values",
                         [(UserStatusEnum, {"ACTIVE", "INACTIVE"})])
def test_enum_members(user_enum_class, expected_values):
    actual_values = {member.value for member in user_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("user_enum_class, expected_values",
                         [(UserStatusEnum, 2)])
def test_enum_length(user_enum_class, expected_values):
    actual_values = {member.value for member in user_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("user_enum_class", [UserStatusEnum])
def test_enum_invalid_value_raises_error(user_enum_class):
    with pytest.raises(ValueError):
        user_enum_class("invalid_status")

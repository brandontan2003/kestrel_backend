import pytest

from app.enums.AuthorizationEnum import AuthorizationTypeEnum


@pytest.mark.parametrize("error_enum_class, expected_values",
                         [(AuthorizationTypeEnum, {"access", "refresh"})])
def test_enum_members(error_enum_class, expected_values):
    actual_values = {member.value for member in error_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("error_enum_class, expected_values",
                         [(AuthorizationTypeEnum, 2)])
def test_enum_length(error_enum_class, expected_values):
    actual_values = {member.value for member in error_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("error_enum_class", [AuthorizationTypeEnum])
def test_enum_invalid_value_raises_error(error_enum_class):
    with pytest.raises(ValueError):
        error_enum_class("invalid")

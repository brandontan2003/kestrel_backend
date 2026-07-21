import pytest

from app.enums.StockEnum import StockStatusEnum


@pytest.mark.parametrize("stock_enum_class, expected_values",
                         [(StockStatusEnum, {"LISTED", "DELISTED"})])
def test_enum_members(stock_enum_class, expected_values):
    actual_values = {member.value for member in stock_enum_class}
    assert actual_values == expected_values


@pytest.mark.parametrize("stock_enum_class, expected_values",
                         [(StockStatusEnum, 2)])
def test_enum_length(stock_enum_class, expected_values):
    actual_values = {member.value for member in stock_enum_class}
    assert len(actual_values) == expected_values


@pytest.mark.parametrize("stock_enum_class", [StockStatusEnum])
def test_enum_invalid_value_raises_error(stock_enum_class):
    with pytest.raises(ValueError):
        stock_enum_class("invalid_status")

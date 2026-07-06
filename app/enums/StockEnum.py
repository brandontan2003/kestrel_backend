import enum


class StockStatusEnum(str, enum.Enum):
    LISTED = "LISTED"
    DELISTED = "DELISTED"

import enum


class QuantModeEnum(str, enum.Enum):
    ALL = "ALL"
    ANY = "ANY"


class CatalystModeEnum(str, enum.Enum):
    ALL = "ALL"
    ANY = "ANY"
    NONE_REQUIRED = "NONE_REQUIRED"


class ThesesStatusEnum(str, enum.Enum):
    TRACKING = "TRACKING"
    DELETED = "DELETED"

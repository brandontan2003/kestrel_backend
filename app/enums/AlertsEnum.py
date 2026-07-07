import enum


class AlertStatusEnum(str, enum.Enum):
    NOT_SENT = "NOT_SENT"
    SENT = "SENT"
    IN_PROGRESS = "IN_PROGRESS"

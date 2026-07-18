import enum


class WebSocketEventTypeEnum(str, enum.Enum):
    ALERT = "ALERT"
    PROPOSAL = "PROPOSAL"
    EVALUATION = "EVALUATION"

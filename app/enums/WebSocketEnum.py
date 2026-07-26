import enum


class WebSocketEventTypeEnum(str, enum.Enum):
    ALERT = "ALERT"
    TELEGRAM_LINKED = "TELEGRAM_LINKED"
    TELEGRAM_UNLINKED = "TELEGRAM_UNLINKED"

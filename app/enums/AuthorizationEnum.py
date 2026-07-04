import enum


class AuthorizationTypeEnum(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"

import enum


class ErrorEnum(enum.Enum):
    VALIDATION_ERROR = ("VALIDATION_ERROR", "Validation Error")
    INTERNAL_SERVER_ERROR = ("INTERNAL_SERVER_ERROR", "An unexpected error occurred. Please try again later.")
    NOT_FOUND = ("NOT_FOUND", "NOT FOUND")
    METHOD_NOT_ALLOWED = ("METHOD_NOT_ALLOWED", "METHOD NOT ALLOWED")
    FORBIDDEN = ("FORBIDDEN", "FORBIDDEN")
    HTTP_ERROR = ("HTTP_ERROR", "HTTP ERROR")

    # Auth specific
    INVALID_TOKEN_ERROR = ("INVALID_TOKEN_ERROR", "Invalid or expired token")
    INVALID_USER_ERROR = ("INVALID_USER_ERROR", "User not found or inactive")
    EMAIL_ALREADY_EXISTS = ("EMAIL_ALREADY_EXISTS", "An account with this email already exists")
    INVALID_CREDENTIALS_ERROR = ("INVALID_CREDENTIALS_ERROR", "Invalid email or password")
    USER_REGISTRATION_FAILED = ("USER_REGISTRATION_FAILED", "Registration failed. Please try again.")

    # Stock
    STOCK_NOT_FOUND = ("STOCK_NOT_FOUND", "Stock does not exist or is not supported")

    # Theses
    THESES_NOT_FOUND = ("THESES_NOT_FOUND", "Theses not found")

    @property
    def error_code(self) -> str:
        return self.value[0]

    @property
    def error_message(self) -> str:
        return self.value[1]

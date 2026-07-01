import enum


class ErrorEnum(enum.Enum):
    VALIDATION_ERROR = ("VALIDATION_ERROR", "Validation Error")
    INTERNAL_SERVER_ERROR = ("INTERNAL_SERVER_ERROR", "An unexpected error occurred. Please try again later.")
    NOT_FOUND = ("NOT_FOUND", "NOT FOUND")
    METHOD_NOT_ALLOWED = ("METHOD_NOT_ALLOWED", "METHOD NOT ALLOWED")
    FORBIDDEN = ("FORBIDDEN", "FORBIDDEN")
    HTTP_ERROR = ("HTTP_ERROR", "HTTP ERROR")

    @property
    def error_code(self) -> str:
        return self.value[0]

    @property
    def error_message(self) -> str:
        return self.value[1]

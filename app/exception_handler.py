from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import logger
from app.dto.error import ErrorResponse, ErrorResult, ErrorDetail
from app.enums.ErrorEnum import ErrorEnum

err = ErrorEnum


class BaseAppException(Exception):
    def __init__(self, status_code: int, error_code: str, error_message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message


class InvalidAuthTokenException(BaseAppException):
    def __init__(self):
        super().__init__(401, err.INVALID_TOKEN_ERROR.error_code, err.INVALID_TOKEN_ERROR.error_message)


class InvalidUserException(BaseAppException):
    def __init__(self):
        super().__init__(401, err.INVALID_USER_ERROR.error_code, err.INVALID_USER_ERROR.error_message)


class InvalidCredentialsException(BaseAppException):
    def __init__(self):
        super().__init__(401, err.INVALID_CREDENTIALS_ERROR.error_code, err.INVALID_CREDENTIALS_ERROR.error_message)


class EmailAlreadyExistsException(BaseAppException):
    def __init__(self):
        super().__init__(400, err.EMAIL_ALREADY_EXISTS.error_code, err.EMAIL_ALREADY_EXISTS.error_message)


class RegistrationErrorException(BaseAppException):
    def __init__(self):
        super().__init__(500, err.USER_REGISTRATION_FAILED.error_code, err.USER_REGISTRATION_FAILED.error_message)


class StockNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.STOCK_NOT_FOUND.error_code, err.STOCK_NOT_FOUND.error_message)


class ThesesNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.THESES_NOT_FOUND.error_code, err.THESES_NOT_FOUND.error_message)


class TelegramAlreadyLinkedException(BaseAppException):
    def __init__(self):
        super().__init__(409, err.TELEGRAM_ALREADY_LINKED.error_code, err.TELEGRAM_ALREADY_LINKED.error_message)


class QuantConditionNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.QUANT_CONDITION_NOT_FOUND.error_code, err.QUANT_CONDITION_NOT_FOUND.error_message)


class CatalystNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.CATALYST_NOT_FOUND.error_code, err.CATALYST_NOT_FOUND.error_message)


class ThesesProposalNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.THESES_PROPOSAL_NOT_FOUND.error_code, err.THESES_PROPOSAL_NOT_FOUND.error_message)


class QuantProposalNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.QUANT_PROPOSAL_NOT_FOUND.error_code, err.QUANT_PROPOSAL_NOT_FOUND.error_message)


class InvalidProposalStatusException(BaseAppException):
    def __init__(self):
        super().__init__(409, err.INVALID_PROPOSAL_STATUS.error_code, err.INVALID_PROPOSAL_STATUS.error_message)


class InvalidProposalTypeException(BaseAppException):
    def __init__(self):
        super().__init__(422, err.INVALID_PROPOSAL_TYPE.error_code, err.INVALID_PROPOSAL_TYPE.error_message)


class CatalystProposalNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.CATALYST_PROPOSAL_NOT_FOUND.error_code, err.CATALYST_PROPOSAL_NOT_FOUND.error_message)


class EvaluationNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.EVALUATION_NOT_FOUND.error_code, err.EVALUATION_NOT_FOUND.error_message)


class AlertNotFoundException(BaseAppException):
    def __init__(self):
        super().__init__(404, err.ALERT_NOT_FOUND.error_code, err.ALERT_NOT_FOUND.error_message)


class CommonException(BaseAppException):
    pass


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Map common HTTP status codes to error codes
        error_code_map = {
            404: err.NOT_FOUND.error_code,
            405: err.METHOD_NOT_ALLOWED.error_code,
            403: err.FORBIDDEN.error_code,
            500: err.INTERNAL_SERVER_ERROR.error_code,
        }
        error_code = error_code_map.get(exc.status_code, err.HTTP_ERROR.error_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                result=ErrorResult(errors=[
                    ErrorDetail(
                        error_code=error_code,
                        error_message=str(exc.detail)
                    )
                ]),
                path=str(request.url.path)
            ).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        details = [
            ErrorDetail(
                error_code=err.VALIDATION_ERROR.error_code,
                error_message=error['msg'],
                field_name=f"{error['loc'][0]}.{error['loc'][-1]}" if len(error['loc']) > 1 else str(error['loc'][0])
            )
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                result=ErrorResult(errors=details),
                path=str(request.url.path)
            ).model_dump()
        )

    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                result=ErrorResult(errors=[
                    ErrorDetail(error_code=exc.error_code, error_message=exc.error_message)
                ]),
                path=str(request.url.path)
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s", request.url.path)

        error = ErrorResponse(
            result=ErrorResult(errors=[
                ErrorDetail(
                    error_code=err.INTERNAL_SERVER_ERROR.error_code,
                    error_message=err.INTERNAL_SERVER_ERROR.error_message
                )
            ]),
            path=str(request.url.path)
        )
        return JSONResponse(status_code=500, content=error.model_dump())

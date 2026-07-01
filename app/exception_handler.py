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

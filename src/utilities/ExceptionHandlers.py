from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from utilities.APIMessage import APIMessage
from utilities.Logging import Logging


class ExceptionHandlers:
    """Build PayTrace-standard error responses for framework exceptions."""

    _HTTP_ERROR_MAP: dict[int, tuple[str, str]] = {
        400: ("PT-1400", "Invalid request payload"),
        401: ("PT-1501", "Authentication failed"),
        403: ("PT-1502", "Authorization denied"),
        404: ("PT-1802", "Resource not found"),
        409: ("PT-1406", "Idempotency key conflict"),
        500: ("PT-1900", "Internal processing error"),
    }

    @classmethod
    async def http_exception_handler(
        cls,
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        result_code, description = cls._HTTP_ERROR_MAP.get(
            exc.status_code,
            ("PT-1900", "Internal processing error"),
        )
        detail = cls._normalize_detail(exc.detail)
        field = "request.path" if exc.status_code == 404 else "request"

        return JSONResponse(
            status_code=exc.status_code,
            content=APIMessage.error(
                code=result_code,
                description=description,
                errors=[
                    {
                        "code": result_code,
                        "description": detail or description,
                        "field": field,
                        "severity": "ERROR",
                    }
                ],
            ),
        )

    @classmethod
    async def validation_exception_handler(
        cls,
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=APIMessage.error(
                code="PT-1402",
                description="Validation failed",
                errors=[
                    {
                        "code": "PT-VAL-0007",
                        "description": error.get("msg", "Validation failed"),
                        "field": cls._format_location(error.get("loc", ())),
                        "severity": "ERROR",
                    }
                    for error in exc.errors()
                ],
            ),
        )

    @classmethod
    async def unhandled_exception_handler(
        cls,
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        Logging.error("Unhandled application error at path=%s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content=APIMessage.error(
                code="PT-1900",
                description="Internal processing error",
                errors=[
                    {
                        "code": "PT-1900",
                        "description": "An unexpected error occurred while processing the request.",
                        "field": "request",
                        "severity": "ERROR",
                    }
                ],
            ),
        )

    @staticmethod
    def _normalize_detail(detail: Any) -> str:
        if isinstance(detail, str):
            return detail
        if detail is None:
            return ""
        return str(detail)

    @staticmethod
    def _format_location(location: tuple[Any, ...] | list[Any]) -> str:
        if not location:
            return "request"
        parts = [str(item) for item in location if item != "body"]
        return ".".join(parts) if parts else "request"

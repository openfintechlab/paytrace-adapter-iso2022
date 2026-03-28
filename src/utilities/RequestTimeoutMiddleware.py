from __future__ import annotations

import asyncio
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from utilities.APIMessage import APIMessage
from utilities.ConfigLoader import ConfigLoader
from utilities.Logging import Logging


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Cancel long-running HTTP requests after the configured application timeout."""

    _TIMEOUT_CONFIG_KEY = "OFTL_SCA_SERVER_TIMEOUT"

    async def dispatch(self, request: Request, call_next: Callable):
        timeout_seconds = self._get_timeout_seconds()
        if timeout_seconds is None:
            return await call_next(request)

        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            Logging.error(f"Request processing exceeded timeout of {timeout_seconds} seconds.")
            return JSONResponse(
                status_code=500,
                content=APIMessage.error(
                    code="PT-1900",
                    description="Internal processing error",
                    errors=[
                        {
                            "code": "PT-1900",
                            "description": "Request processing timed out.",
                            "field": "request",
                            "severity": "ERROR",
                        }
                    ],
                ),
            )

    @classmethod
    def _get_timeout_seconds(cls) -> float | None:
        raw_value = ConfigLoader.get(cls._TIMEOUT_CONFIG_KEY)
        if raw_value in (None, ""):
            return None

        try:
            timeout_seconds = float(str(raw_value).strip())
        except (TypeError, ValueError):
            return None

        return timeout_seconds if timeout_seconds > 0 else None

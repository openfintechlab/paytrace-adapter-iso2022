from __future__ import annotations

from typing import Any


class APIMessage:
    """Build standard PayTrace API message envelopes."""

    @staticmethod
    def success(
        *,
        code: str = "PT-0000",
        description: str = "Operation completed successfully",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response: dict[str, Any] = {
            "result": {
                "code": code,
                "description": description,
            },
        }
        if payload is not None:
            response["payload"] = payload
        return response

    @staticmethod
    def error(
        *,
        code: str,
        description: str,
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "result": {
                "code": code,
                "description": description,
            },
            "errors": errors,
        }

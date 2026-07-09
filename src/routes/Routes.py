# -*- coding: utf-8 -*-
"""
Copyright 2026-2028 openfintechlab.com, Inc. All rights reserved.
Licenses: LICENSE.md
Description: Routes boilerplate for PayTrace SCA Service.
Reference: https://github.com/openfintechlab/pytrace-backlogs/issues/12
"""

from __future__ import annotations

import time
from fastapi import APIRouter, Request
from fastapi.responses import Response

from domain.ISO20022Pain001Parser import ISO20022Pain001Parser
from domain.ISO20022Serializer import ISO20022Serializer
from utilities import APIMessage, ConfigLoader


class Routes:
    """Defines base routes for the service."""

    def __init__(self) -> None:
        self.prefix = self._build_prefix()
        self.router = APIRouter(prefix=self.prefix)
        self.public_router = APIRouter()
        self._register_routes()

    @staticmethod
    def _normalize_segment(value: str) -> str:
        if not value:
            return ""
        value = value.strip()
        if not value:
            return ""
        if not value.startswith("/"):
            value = "/" + value
        return value.rstrip("/")

    @classmethod
    def _build_prefix(cls) -> str:
        context_root = ConfigLoader.get("OFTL_SCA_CONTEXT_ROOT")
        version = ConfigLoader.get("OFTL_SCA_VERSION")
        context_root = cls._normalize_segment(str(context_root)) if context_root else ""
        version = str(version).strip() if version else ""
        version_segment = f"/v{version}" if version else ""

        return f"{context_root}{version_segment}"

    def _register_routes(self) -> None:
        @self.router.post("/", name="post_pain001")
        async def post_pain001(request: Request) -> Response:
            return self.route_post_pain001(await request.body())

        @self.public_router.get("/_healthz")
        async def healthz() -> dict:
            return self.route_get_healthz()

        @self.public_router.get("/_probe")
        async def probe() -> dict:
            return self.route_get_probe()

    @staticmethod
    def route_get_healthz() -> dict:
        """Returns the health status."""
        return APIMessage.success(
            description="Resource retrieved successfully",
            code="PT-0200",
            payload={"status": "ok"},
        )

    @staticmethod
    def route_get_probe() -> dict:
        """Returns the probe status."""
        return APIMessage.success(
            description="Resource retrieved successfully",
            code="PT-0200",
            payload={"status": "ok"},
        )

    @classmethod
    def route_post_pain001(cls, payload: bytes) -> Response:
        """Validate an inbound pain.001 message and return a pain.002 status report."""
        parse_result = ISO20022Pain001Parser.parse(payload)
        # time.sleep(6) # Un-Comment to simulate a long-running request for testing the RequestTimeoutMiddleware.
        if parse_result.is_valid:
            serialization_result = ISO20022Serializer.serialize(parse_result)            
            if serialization_result.duplicate_message_id:
                parse_result = type(parse_result)(
                    is_valid=False,
                    reason=serialization_result.reason,
                    original_message_id=parse_result.original_message_id,
                    metadata=parse_result.metadata,
                )

        status_code = 200 if parse_result.is_valid else 400

        return Response(
            content=ISO20022Pain001Parser.build_pain002_response(parse_result),
            status_code=status_code,
            media_type="application/xml",
        )

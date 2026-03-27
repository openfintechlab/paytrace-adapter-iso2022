# -*- coding: utf-8 -*-
"""
Copyright 2026-2028 openfintechlab.com, Inc. All rights reserved.
Licenses: LICENSE.md
Description: pain.001 parser and pain.002 response builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import uuid
from xml.etree import ElementTree


@dataclass(frozen=True)
class Pain001ParseResult:
    """Represents the outcome of parsing a pain.001 message."""

    is_valid: bool
    reason: str = ""
    original_message_id: str = "UNKNOWN"


class ISO20022Pain001Parser:
    """Validate pain.001 XML and build pain.002 status reports."""

    PAIN_001_ROOT = "CstmrCdtTrfInitn"
    PAIN_001_MESSAGE_NAME = "pain.001.001.03"
    PAIN_002_NAMESPACE = "urn:iso:std:iso:20022:tech:xsd:pain.002.001.03"

    @classmethod
    def parse(cls, payload: bytes) -> Pain001ParseResult:
        if not payload or not payload.strip():
            return Pain001ParseResult(is_valid=False, reason="empty request body")

        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            return Pain001ParseResult(is_valid=False, reason=str(exc))

        if cls._local_name(root.tag) != "Document":
            return Pain001ParseResult(is_valid=False, reason="root element must be Document")

        customer_credit_transfer = cls._find_child_by_local_name(root, cls.PAIN_001_ROOT)
        if customer_credit_transfer is None:
            return Pain001ParseResult(
                is_valid=False,
                reason=f"missing {cls.PAIN_001_ROOT} element",
            )

        group_header = cls._find_child_by_local_name(customer_credit_transfer, "GrpHdr")
        original_message_id = cls._text_from_child(group_header, "MsgId") if group_header is not None else ""

        return Pain001ParseResult(
            is_valid=True,
            original_message_id=original_message_id or "UNKNOWN",
        )

    @classmethod
    def build_pain002_response(cls, parse_result: Pain001ParseResult) -> bytes:
        status = "ACCP" if parse_result.is_valid else "RJCT"
        description = (
            "pain.001 message accepted."
            if parse_result.is_valid
            else f"pain.001 syntax validation failed: {parse_result.reason}"
        )
        return cls._build_pain002(
            status=status,
            description=description,
            original_message_id=parse_result.original_message_id,
        )

    @classmethod
    def _build_pain002(
        cls,
        status: str,
        description: str,
        original_message_id: str,
    ) -> bytes:
        ElementTree.register_namespace("", cls.PAIN_002_NAMESPACE)

        document = ElementTree.Element(f"{{{cls.PAIN_002_NAMESPACE}}}Document")
        customer_payment_status = ElementTree.SubElement(
            document,
            f"{{{cls.PAIN_002_NAMESPACE}}}CstmrPmtStsRpt",
        )

        group_header = ElementTree.SubElement(
            customer_payment_status,
            f"{{{cls.PAIN_002_NAMESPACE}}}GrpHdr",
        )
        ElementTree.SubElement(
            group_header,
            f"{{{cls.PAIN_002_NAMESPACE}}}MsgId",
        ).text = f"pain002-{uuid.uuid4()}"
        ElementTree.SubElement(
            group_header,
            f"{{{cls.PAIN_002_NAMESPACE}}}CreDtTm",
        ).text = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        original_group_info = ElementTree.SubElement(
            customer_payment_status,
            f"{{{cls.PAIN_002_NAMESPACE}}}OrgnlGrpInfAndSts",
        )
        ElementTree.SubElement(
            original_group_info,
            f"{{{cls.PAIN_002_NAMESPACE}}}OrgnlMsgId",
        ).text = original_message_id
        ElementTree.SubElement(
            original_group_info,
            f"{{{cls.PAIN_002_NAMESPACE}}}OrgnlMsgNmId",
        ).text = cls.PAIN_001_MESSAGE_NAME
        ElementTree.SubElement(
            original_group_info,
            f"{{{cls.PAIN_002_NAMESPACE}}}GrpSts",
        ).text = status
        status_reason_info = ElementTree.SubElement(
            original_group_info,
            f"{{{cls.PAIN_002_NAMESPACE}}}StsRsnInf",
        )
        ElementTree.SubElement(
            status_reason_info,
            f"{{{cls.PAIN_002_NAMESPACE}}}AddtlInf",
        ).text = description

        return ElementTree.tostring(document, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.split("}", 1)[-1]

    @classmethod
    def _find_child_by_local_name(
        cls,
        root: ElementTree.Element,
        local_name: str,
    ) -> ElementTree.Element | None:
        for child in root:
            if cls._local_name(child.tag) == local_name:
                return child
        return None

    @classmethod
    def _text_from_child(cls, root: ElementTree.Element, local_name: str) -> str:
        child = cls._find_child_by_local_name(root, local_name)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

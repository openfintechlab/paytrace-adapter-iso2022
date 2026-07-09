# -*- coding: utf-8 -*-
"""
Copyright 2026-2028 openfintechlab.com, Inc. All rights reserved.
Licenses: LICENSE.md
Description: pain.001 parser and pain.002 response builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import UTC, datetime
import uuid
from xml.etree import ElementTree


@dataclass(frozen=True)
class Pain001Metadata:
    """Essential pain.001 message metadata extracted from the XML payload."""

    message_id: str
    message_name_id: str = "pain.001.001.03"
    creation_date_time: str | None = None
    number_of_transactions: int | None = None
    control_sum: Decimal | None = None
    payment_information_count: int | None = None
    payment_method: str | None = None
    requested_execution_date: str | None = None
    batch_booking: bool | None = None
    initiating_party_name: str | None = None
    initiating_party_id: str | None = None
    debtor_name: str | None = None
    debtor_account_iban: str | None = None
    debtor_account_other_id: str | None = None
    debtor_agent_bic: str | None = None
    charge_bearer: str | None = None
    service_level_code: str | None = None
    local_instrument_code: str | None = None
    category_purpose_code: str | None = None
    instructed_currency: str | None = None
    total_instructed_amount: Decimal | None = None


@dataclass(frozen=True)
class Pain001ParseResult:
    """Represents the outcome of parsing a pain.001 message."""

    is_valid: bool
    reason: str = ""
    original_message_id: str = "UNKNOWN"
    metadata: Pain001Metadata | None = None


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
        metadata = cls._extract_metadata(customer_credit_transfer, group_header)

        return Pain001ParseResult(
            is_valid=True,
            original_message_id=original_message_id or "UNKNOWN",
            metadata=metadata,
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
        root: ElementTree.Element | None,
        local_name: str,
    ) -> ElementTree.Element | None:
        if root is None:
            return None
        for child in root:
            if cls._local_name(child.tag) == local_name:
                return child
        return None

    @classmethod
    def _text_from_child(cls, root: ElementTree.Element | None, local_name: str) -> str:
        child = cls._find_child_by_local_name(root, local_name)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

    @classmethod
    def _find_children_by_local_name(
        cls,
        root: ElementTree.Element | None,
        local_name: str,
    ) -> list[ElementTree.Element]:
        if root is None:
            return []
        return [child for child in root if cls._local_name(child.tag) == local_name]

    @classmethod
    def _find_descendant_by_path(
        cls,
        root: ElementTree.Element | None,
        path: list[str],
    ) -> ElementTree.Element | None:
        current = root
        for local_name in path:
            if current is None:
                return None
            current = cls._find_child_by_local_name(current, local_name)
        return current

    @classmethod
    def _text_from_path(
        cls,
        root: ElementTree.Element | None,
        path: list[str],
    ) -> str:
        element = cls._find_descendant_by_path(root, path)
        if element is None or element.text is None:
            return ""
        return element.text.strip()

    @staticmethod
    def _parse_int(value: str) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _parse_decimal(value: str) -> Decimal | None:
        if not value:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_bool(value: str) -> bool | None:
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in {"true", "1"}:
            return True
        if normalized in {"false", "0"}:
            return False
        return None

    @classmethod
    def _extract_metadata(
        cls,
        customer_credit_transfer: ElementTree.Element,
        group_header: ElementTree.Element | None,
    ) -> Pain001Metadata:
        payment_information_blocks = cls._find_children_by_local_name(
            customer_credit_transfer,
            "PmtInf",
        )
        first_payment_information = payment_information_blocks[0] if payment_information_blocks else None

        total_amount = Decimal("0")
        amount_found = False
        instructed_currency = ""
        for payment_information in payment_information_blocks:
            for credit_transfer in cls._find_children_by_local_name(payment_information, "CdtTrfTxInf"):
                instructed_amount = cls._find_descendant_by_path(
                    credit_transfer,
                    ["Amt", "InstdAmt"],
                )
                if instructed_amount is None or instructed_amount.text is None:
                    continue
                parsed_amount = cls._parse_decimal(instructed_amount.text.strip())
                if parsed_amount is None:
                    continue
                total_amount += parsed_amount
                amount_found = True
                if not instructed_currency:
                    instructed_currency = instructed_amount.attrib.get("Ccy", "").strip()

        return Pain001Metadata(
            message_id=cls._text_from_child(group_header, "MsgId") or "UNKNOWN",
            creation_date_time=cls._text_from_child(group_header, "CreDtTm") or None,
            number_of_transactions=cls._parse_int(cls._text_from_child(group_header, "NbOfTxs")),
            control_sum=cls._parse_decimal(cls._text_from_child(group_header, "CtrlSum")),
            payment_information_count=len(payment_information_blocks),
            payment_method=cls._text_from_child(first_payment_information, "PmtMtd") or None,
            requested_execution_date=cls._text_from_child(first_payment_information, "ReqdExctnDt") or None,
            batch_booking=cls._parse_bool(cls._text_from_child(first_payment_information, "BtchBookg")),
            initiating_party_name=cls._text_from_path(group_header, ["InitgPty", "Nm"]) or None,
            initiating_party_id=(
                cls._text_from_path(group_header, ["InitgPty", "Id", "OrgId", "Othr", "Id"])
                or cls._text_from_path(group_header, ["InitgPty", "Id", "PrvtId", "Othr", "Id"])
                or None
            ),
            debtor_name=cls._text_from_child(
                cls._find_child_by_local_name(first_payment_information, "Dbtr")
                if first_payment_information is not None
                else None,
                "Nm",
            ) or None,
            debtor_account_iban=cls._text_from_path(first_payment_information, ["DbtrAcct", "Id", "IBAN"]) or None,
            debtor_account_other_id=cls._text_from_path(first_payment_information, ["DbtrAcct", "Id", "Othr", "Id"]) or None,
            debtor_agent_bic=(
                cls._text_from_path(first_payment_information, ["DbtrAgt", "FinInstnId", "BICFI"])
                or cls._text_from_path(first_payment_information, ["DbtrAgt", "FinInstnId", "BIC"])
                or None
            ),
            charge_bearer=cls._text_from_child(first_payment_information, "ChrgBr") or None,
            service_level_code=cls._text_from_path(first_payment_information, ["PmtTpInf", "SvcLvl", "Cd"]) or None,
            local_instrument_code=cls._text_from_path(first_payment_information, ["PmtTpInf", "LclInstrm", "Cd"]) or None,
            category_purpose_code=cls._text_from_path(first_payment_information, ["PmtTpInf", "CtgyPurp", "Cd"]) or None,
            instructed_currency=instructed_currency or None,
            total_instructed_amount=total_amount if amount_found else None,
        )

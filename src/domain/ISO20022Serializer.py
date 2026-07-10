from __future__ import annotations

from dataclasses import dataclass

from domain.ISO20022Pain001Parser import Pain001ParseResult
from utilities.DBHelper import DBHelper


@dataclass(frozen=True)
class ISO20022SerializationResult:
    """Represents the result of persisting pain.001 metadata."""

    stored: bool
    duplicate_message_id: bool = False
    reason: str = ""


class ISO20022Serializer:
    """Persist validated pain.001 metadata to PostgreSQL."""

    _TABLE_NAME = "paytrace_iso2022simulator.oftl_iso20022_simulator"

    @classmethod
    def serialize(cls, parse_result: Pain001ParseResult) -> ISO20022SerializationResult:
        metadata = parse_result.metadata
        if not parse_result.is_valid or metadata is None:
            return ISO20022SerializationResult(
                stored=False,
                reason="pain.001 metadata is unavailable for persistence",
            )

        if cls._message_exists(metadata.message_id):
            return ISO20022SerializationResult(
                stored=False,
                duplicate_message_id=True,
                reason=f"duplicate message id detected: {metadata.message_id}",
            )

        DBHelper.execute_insert(
            f"""
            INSERT INTO {cls._TABLE_NAME} (
                message_id,
                message_name_id,
                creation_date_time,
                number_of_transactions,
                control_sum,
                payment_information_count,
                payment_method,
                requested_execution_date,
                batch_booking,
                initiating_party_name,
                initiating_party_id,
                debtor_name,
                debtor_account_iban,
                debtor_account_other_id,
                debtor_agent_bic,
                charge_bearer,
                service_level_code,
                local_instrument_code,
                category_purpose_code,
                instructed_currency,
                total_instructed_amount,
                processing_status
            ) VALUES (
                :message_id,
                :message_name_id,
                :creation_date_time,
                :number_of_transactions,
                :control_sum,
                :payment_information_count,
                :payment_method,
                :requested_execution_date,
                :batch_booking,
                :initiating_party_name,
                :initiating_party_id,
                :debtor_name,
                :debtor_account_iban,
                :debtor_account_other_id,
                :debtor_agent_bic,
                :charge_bearer,
                :service_level_code,
                :local_instrument_code,
                :category_purpose_code,
                :instructed_currency,
                :total_instructed_amount,
                :processing_status
            )
            """,
            params={
                "message_id": metadata.message_id,
                "message_name_id": metadata.message_name_id,
                "creation_date_time": metadata.creation_date_time,
                "number_of_transactions": metadata.number_of_transactions,
                "control_sum": metadata.control_sum,
                "payment_information_count": metadata.payment_information_count,
                "payment_method": metadata.payment_method,
                "requested_execution_date": metadata.requested_execution_date,
                "batch_booking": metadata.batch_booking,
                "initiating_party_name": metadata.initiating_party_name,
                "initiating_party_id": metadata.initiating_party_id,
                "debtor_name": metadata.debtor_name,
                "debtor_account_iban": metadata.debtor_account_iban,
                "debtor_account_other_id": metadata.debtor_account_other_id,
                "debtor_agent_bic": metadata.debtor_agent_bic,
                "charge_bearer": metadata.charge_bearer,
                "service_level_code": metadata.service_level_code,
                "local_instrument_code": metadata.local_instrument_code,
                "category_purpose_code": metadata.category_purpose_code,
                "instructed_currency": metadata.instructed_currency,
                "total_instructed_amount": metadata.total_instructed_amount,
                "processing_status": "VALIDATED",
            },
        )

        return ISO20022SerializationResult(stored=True)

    @classmethod
    def _message_exists(cls, message_id: str) -> bool:
        rows = DBHelper.execute_select(
            f"SELECT 1 FROM {cls._TABLE_NAME} WHERE message_id = :message_id LIMIT 1",
            params={"message_id": message_id},
        )
        return bool(rows)

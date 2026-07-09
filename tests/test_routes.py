import asyncio
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from src.main import app
from src.domain.ISO20022Serializer import ISO20022SerializationResult
from src.utilities.ConfigLoader import ConfigLoader
from src.utilities.DBHelper import DBHelper


client = TestClient(app)
safe_client = TestClient(app, raise_server_exceptions=False)
ROOT_PATH = str(app.url_path_for("post_pain001"))


VALID_HEADERS = {
    "Authorization": "Bearer token",
    "X-Transaction-Id": "123e4567-e89b-12d3-a456-426614174000",
    "X-Correlation-Id": "123e4567-e89b-12d3-a456-426614174001",
    "Accept-Language": "en-US",
    "Accept": "application/xml",
    "Idempotency-Key": "123e4567-e89b-12d3-a456-426614174002",
    "Content-Type": "application/xml",
}
VALID_GET_HEADERS = {
    "Authorization": "Bearer token",
    "X-Transaction-Id": "123e4567-e89b-12d3-a456-426614174000",
    "X-Correlation-Id": "123e4567-e89b-12d3-a456-426614174001",
    "Accept-Language": "en-US",
    "Accept": "application/json",
}

VALID_PAIN_001_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-001</MsgId>
    </GrpHdr>
  </CstmrCdtTrfInitn>
</Document>
"""

DB_REQUIRED_ENV_KEYS = (
    "OFTL_POSTGRESDB_USERNAME",
    "OFTL_POSTGRESDB_PASSWORD",
    "OFTL_POSTGRESDB_HOST",
    "OFTL_POSTGRESDB_PORT",
    "OFTL_POSTGRESDB_NAME",
)
SIMULATOR_TABLE_NAME = "paytrace_iso2022simulator.oftl_iso20022_simulator"


def _is_database_configured() -> bool:
    return all(ConfigLoader.get(key) for key in DB_REQUIRED_ENV_KEYS)


def _ensure_simulator_table_exists() -> None:
    ddl_path = Path(__file__).resolve().parents[1] / "sql" / "001_create_oftl_iso20022_simulator.sql"
    ddl_statements = [statement.strip() for statement in ddl_path.read_text().split(";") if statement.strip()]
    if DBHelper._engine is None:
        raise RuntimeError("Database engine is not initialized.")

    with DBHelper._engine.begin() as connection:
        for statement in ddl_statements:
            connection.execute(text(statement))


def test_post_pain001_returns_acceptance_report_for_valid_xml(monkeypatch):
    monkeypatch.setattr(
        "src.routes.Routes.ISO20022Serializer.serialize",
        lambda parse_result: ISO20022SerializationResult(stored=True),
    )

    response = client.post(ROOT_PATH, content=VALID_PAIN_001_XML, headers=VALID_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<GrpSts>ACCP</GrpSts>" in response.text
    assert "pain.001 message accepted." in response.text


def test_post_pain001_persists_message_metadata_and_cleans_up():
    if not _is_database_configured():
        pytest.skip("Database configuration is required for persistence route test.")

    if not DBHelper.initialize_connection():
        pytest.skip("Database connection could not be initialized for persistence route test.")

    _ensure_simulator_table_exists()

    unique_message_id = f"MSG-{uuid.uuid4()}"
    payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>{unique_message_id}</MsgId>
      <CreDtTm>2026-03-28T10:15:30Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>150.25</CtrlSum>
      <InitgPty>
        <Nm>Open Fintech Lab</Nm>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtMtd>TRF</PmtMtd>
      <BtchBookg>true</BtchBookg>
      <ReqdExctnDt>2026-03-29</ReqdExctnDt>
      <Dbtr>
        <Nm>Acme Corp</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <IBAN>DE89370400440532013000</IBAN>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <BICFI>DEUTDEFF</BICFI>
        </FinInstnId>
      </DbtrAgt>
      <ChrgBr>SLEV</ChrgBr>
      <CdtTrfTxInf>
        <Amt>
          <InstdAmt Ccy="EUR">150.25</InstdAmt>
        </Amt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""

    try:
        response = client.post(ROOT_PATH, content=payload, headers=VALID_HEADERS)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")
        assert "<GrpSts>ACCP</GrpSts>" in response.text

        rows = DBHelper.execute_select(
            f"""
            SELECT message_id, processing_status, debtor_name, instructed_currency
            FROM {SIMULATOR_TABLE_NAME}
            WHERE message_id = :message_id
            """,
            params={"message_id": unique_message_id},
        )

        assert len(rows) == 1
        assert rows[0]["message_id"] == unique_message_id
        assert rows[0]["processing_status"] == "VALIDATED"
        assert rows[0]["debtor_name"] == "Acme Corp"
        assert rows[0]["instructed_currency"] == "EUR"
    finally:
        if DBHelper.initialize_connection():
            DBHelper.execute_delete(
                f"DELETE FROM {SIMULATOR_TABLE_NAME} WHERE message_id = :message_id",
                params={"message_id": unique_message_id},
            )


def test_healthz_status_code_is_success():
    response = client.get("/_healthz")
    assert response.status_code in {200, 201}
    assert response.json() == {
        "result": {
            "code": "PT-0200",
            "description": "Resource retrieved successfully",
        },
        "payload": {
            "status": "ok",
        },
    }


def test_probe_status_code_is_success():
    response = client.get("/_probe")
    assert response.status_code in {200, 201}
    assert response.json() == {
        "result": {
            "code": "PT-0200",
            "description": "Resource retrieved successfully",
        },
        "payload": {
            "status": "ok",
        },
    }


def test_post_pain001_rejects_request_when_required_headers_are_missing():
    response = client.post(ROOT_PATH, content=VALID_PAIN_001_XML)

    assert response.status_code == 400
    payload = response.json()
    assert payload["result"]["code"] == "PT-1401"
    assert payload["result"]["description"] == "Missing required field"
    assert isinstance(payload["errors"], list)
    assert payload["errors"]


def test_post_pain001_returns_rejection_report_for_invalid_xml():
    invalid_xml = "<Document><Broken></Document>"

    response = client.post(ROOT_PATH, content=invalid_xml, headers=VALID_HEADERS)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/xml")
    assert "<GrpSts>RJCT</GrpSts>" in response.text
    assert "syntax validation failed" in response.text


def test_post_pain001_rejects_duplicate_message_id(monkeypatch):
    monkeypatch.setattr(
        "src.routes.Routes.ISO20022Serializer.serialize",
        lambda parse_result: ISO20022SerializationResult(
            stored=False,
            duplicate_message_id=True,
            reason="duplicate message id detected: MSG-001",
        ),
    )

    response = client.post(ROOT_PATH, content=VALID_PAIN_001_XML, headers=VALID_HEADERS)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/xml")
    assert "<GrpSts>RJCT</GrpSts>" in response.text
    assert "duplicate message id detected: MSG-001" in response.text


def test_missing_route_returns_paytrace_standard_404_message():
    response = client.get("/missing-route", headers=VALID_GET_HEADERS)

    assert response.status_code == 404
    assert response.json() == {
        "result": {
            "code": "PT-1802",
            "description": "Resource not found",
        },
        "errors": [
            {
                "code": "PT-1802",
                "description": "Not Found",
                "field": "request.path",
                "severity": "ERROR",
            }
        ],
    }


def test_unhandled_exception_returns_paytrace_standard_500_message():
    def force_error():
        raise RuntimeError("boom")

    app.add_api_route("/__test_error_500", force_error, methods=["GET"])

    response = safe_client.get("/__test_error_500", headers=VALID_GET_HEADERS)

    assert response.status_code == 500
    assert response.json() == {
        "result": {
            "code": "PT-1900",
            "description": "Internal processing error",
        },
        "errors": [
            {
                "code": "PT-1900",
                "description": "An unexpected error occurred while processing the request.",
                "field": "request",
                "severity": "ERROR",
            }
        ],
    }


def test_request_timeout_returns_500(monkeypatch):
    async def slow_route():
        await asyncio.sleep(0.05)
        return {"status": "ok"}

    monkeypatch.setattr(
        "utilities.RequestTimeoutMiddleware.ConfigLoader.get",
        lambda key, default=None: "0.01" if key == "OFTL_SCA_SERVER_TIMEOUT" else default,
    )

    if not any(route.path == "/__test_timeout_500" for route in app.routes):
        app.add_api_route("/__test_timeout_500", slow_route, methods=["GET"])

    response = safe_client.get("/__test_timeout_500", headers=VALID_GET_HEADERS)

    assert response.status_code == 500
    assert response.json() == {
        "result": {
            "code": "PT-1900",
            "description": "Internal processing error",
        },
        "errors": [
            {
                "code": "PT-1900",
                "description": "Request processing timed out.",
                "field": "request",
                "severity": "ERROR",
            }
        ],
    }

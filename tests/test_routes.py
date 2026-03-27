from fastapi.testclient import TestClient

from src.main import app


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


def test_post_pain001_returns_acceptance_report_for_valid_xml():
    response = client.post(ROOT_PATH, content=VALID_PAIN_001_XML, headers=VALID_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<GrpSts>ACCP</GrpSts>" in response.text
    assert "pain.001 message accepted." in response.text


def test_post_pain001_returns_rejection_report_for_invalid_xml():
    invalid_xml = "<Document><Broken></Document>"

    response = client.post(ROOT_PATH, content=invalid_xml, headers=VALID_HEADERS)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/xml")
    assert "<GrpSts>RJCT</GrpSts>" in response.text
    assert "syntax validation failed" in response.text


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

from src.domain.ISO20022Pain001Parser import ISO20022Pain001Parser
from src.domain.ISO20022Serializer import ISO20022Serializer


VALID_PAIN_001_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-001</MsgId>
      <CreDtTm>2026-03-28T10:15:30Z</CreDtTm>
    </GrpHdr>
    <PmtInf>
      <PmtMtd>TRF</PmtMtd>
      <Dbtr>
        <Nm>Acme Corp</Nm>
      </Dbtr>
      <CdtTrfTxInf>
        <Amt>
          <InstdAmt Ccy="EUR">150.25</InstdAmt>
        </Amt>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""


def test_serialize_persists_metadata_for_new_message(monkeypatch):
    parse_result = ISO20022Pain001Parser.parse(VALID_PAIN_001_XML)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "src.domain.ISO20022Serializer.DBHelper.execute_select",
        lambda query, params=None: [],
    )
    monkeypatch.setattr(
        "src.domain.ISO20022Serializer.DBHelper.execute_insert",
        lambda query, params=None: captured.update({"query": query, "params": params}) or 1,
    )

    result = ISO20022Serializer.serialize(parse_result)

    assert result.stored is True
    assert result.duplicate_message_id is False
    assert captured["params"]["message_id"] == "MSG-001"
    assert captured["params"]["payment_method"] == "TRF"
    assert captured["params"]["debtor_name"] == "Acme Corp"
    assert captured["params"]["instructed_currency"] == "EUR"
    assert str(captured["params"]["total_instructed_amount"]) == "150.25"
    assert captured["params"]["processing_status"] == "VALIDATED"


def test_serialize_rejects_duplicate_message_id(monkeypatch):
    parse_result = ISO20022Pain001Parser.parse(VALID_PAIN_001_XML)

    monkeypatch.setattr(
        "src.domain.ISO20022Serializer.DBHelper.execute_select",
        lambda query, params=None: [{"exists": 1}],
    )

    result = ISO20022Serializer.serialize(parse_result)

    assert result.stored is False
    assert result.duplicate_message_id is True
    assert result.reason == "duplicate message id detected: MSG-001"

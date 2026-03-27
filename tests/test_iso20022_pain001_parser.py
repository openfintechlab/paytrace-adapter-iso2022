from xml.etree import ElementTree

from src.domain.ISO20022Pain001Parser import ISO20022Pain001Parser, Pain001ParseResult


VALID_PAIN_001_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-001</MsgId>
    </GrpHdr>
  </CstmrCdtTrfInitn>
</Document>
"""


def test_parse_returns_message_id_for_valid_pain001_xml():
    result = ISO20022Pain001Parser.parse(VALID_PAIN_001_XML)

    assert result.is_valid is True
    assert result.reason == ""
    assert result.original_message_id == "MSG-001"


def test_parse_rejects_invalid_pain001_xml():
    result = ISO20022Pain001Parser.parse(b"<Document><Broken></Document>")

    assert result.is_valid is False
    assert "mismatched tag" in result.reason
    assert result.original_message_id == "UNKNOWN"


def test_build_pain002_response_contains_expected_fields():
    parse_result = Pain001ParseResult(is_valid=True, original_message_id="MSG-001")

    response_xml = ISO20022Pain001Parser.build_pain002_response(parse_result)
    root = ElementTree.fromstring(response_xml)

    assert root.tag == "{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}Document"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlMsgId").text == "MSG-001"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlMsgNmId").text == "pain.001.001.03"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}GrpSts").text == "ACCP"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}AddtlInf").text == "pain.001 message accepted."

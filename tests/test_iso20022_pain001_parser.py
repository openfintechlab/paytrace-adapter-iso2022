from xml.etree import ElementTree

from src.domain.ISO20022Pain001Parser import ISO20022Pain001Parser, Pain001ParseResult


VALID_PAIN_001_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-001</MsgId>
      <CreDtTm>2026-03-28T10:15:30Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <CtrlSum>150.25</CtrlSum>
      <InitgPty>
        <Nm>Open Fintech Lab</Nm>
        <Id>
          <OrgId>
            <Othr>
              <Id>INIT-001</Id>
            </Othr>
          </OrgId>
        </Id>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtMtd>TRF</PmtMtd>
      <BtchBookg>true</BtchBookg>
      <ReqdExctnDt>2026-03-29</ReqdExctnDt>
      <PmtTpInf>
        <SvcLvl>
          <Cd>SEPA</Cd>
        </SvcLvl>
        <LclInstrm>
          <Cd>INST</Cd>
        </LclInstrm>
        <CtgyPurp>
          <Cd>SALA</Cd>
        </CtgyPurp>
      </PmtTpInf>
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


def test_parse_returns_message_id_for_valid_pain001_xml():
    result = ISO20022Pain001Parser.parse(VALID_PAIN_001_XML)

    assert result.is_valid is True
    assert result.reason == ""
    assert result.original_message_id == "MSG-001"
    assert result.metadata is not None
    assert result.metadata.creation_date_time == "2026-03-28T10:15:30Z"
    assert result.metadata.number_of_transactions == 1
    assert str(result.metadata.control_sum) == "150.25"
    assert result.metadata.payment_information_count == 1
    assert result.metadata.payment_method == "TRF"
    assert result.metadata.batch_booking is True
    assert result.metadata.initiating_party_name == "Open Fintech Lab"
    assert result.metadata.initiating_party_id == "INIT-001"
    assert result.metadata.debtor_name == "Acme Corp"
    assert result.metadata.debtor_account_iban == "DE89370400440532013000"
    assert result.metadata.debtor_agent_bic == "DEUTDEFF"
    assert result.metadata.instructed_currency == "EUR"
    assert str(result.metadata.total_instructed_amount) == "150.25"


def test_parse_rejects_invalid_pain001_xml():
    result = ISO20022Pain001Parser.parse(b"<Document><Broken></Document>")

    assert result.is_valid is False
    assert "mismatched tag" in result.reason
    assert result.original_message_id == "UNKNOWN"
    assert result.metadata is None


def test_build_pain002_response_contains_expected_fields():
    parse_result = Pain001ParseResult(is_valid=True, original_message_id="MSG-001")

    response_xml = ISO20022Pain001Parser.build_pain002_response(parse_result)
    root = ElementTree.fromstring(response_xml)

    assert root.tag == "{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}Document"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlMsgId").text == "MSG-001"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}OrgnlMsgNmId").text == "pain.001.001.03"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}GrpSts").text == "ACCP"
    assert root.find(".//{urn:iso:std:iso:20022:tech:xsd:pain.002.001.03}AddtlInf").text == "pain.001 message accepted."

CREATE SCHEMA IF NOT EXISTS paytrace_iso2022simulator;

CREATE TABLE IF NOT EXISTS paytrace_iso2022simulator.oftl_iso20022_simulator (
    iso20022_simulator_id      BIGSERIAL PRIMARY KEY,
    message_id                 VARCHAR(70) NOT NULL,
    message_name_id            VARCHAR(35) NOT NULL DEFAULT 'pain.001.001.03',
    creation_date_time         TIMESTAMPTZ NULL,
    number_of_transactions     INTEGER NULL,
    control_sum                NUMERIC(18, 2) NULL,
    payment_information_count  INTEGER NULL,
    payment_method             VARCHAR(10) NULL,
    requested_execution_date   DATE NULL,
    batch_booking              BOOLEAN NULL,
    initiating_party_name      VARCHAR(140) NULL,
    initiating_party_id        VARCHAR(70) NULL,
    debtor_name                VARCHAR(140) NULL,
    debtor_account_iban        VARCHAR(34) NULL,
    debtor_account_other_id    VARCHAR(70) NULL,
    debtor_agent_bic           VARCHAR(11) NULL,
    charge_bearer              VARCHAR(4) NULL,
    service_level_code         VARCHAR(35) NULL,
    local_instrument_code      VARCHAR(35) NULL,
    category_purpose_code      VARCHAR(35) NULL,
    instructed_currency        CHAR(3) NULL,
    total_instructed_amount    NUMERIC(18, 2) NULL,
    processing_status          VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
    received_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_oftl_iso20022_simulator_message_id UNIQUE (message_id),
    CONSTRAINT chk_oftl_iso20022_simulator_transaction_count
        CHECK (number_of_transactions IS NULL OR number_of_transactions >= 0),
    CONSTRAINT chk_oftl_iso20022_simulator_payment_info_count
        CHECK (payment_information_count IS NULL OR payment_information_count >= 0),
    CONSTRAINT chk_oftl_iso20022_simulator_control_sum
        CHECK (control_sum IS NULL OR control_sum >= 0),
    CONSTRAINT chk_oftl_iso20022_simulator_total_amount
        CHECK (total_instructed_amount IS NULL OR total_instructed_amount >= 0),
    CONSTRAINT chk_oftl_iso20022_simulator_processing_status
        CHECK (
            processing_status IN (
                'RECEIVED',
                'VALIDATED',
                'REJECTED',
                'PROCESSED'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_oftl_iso20022_simulator_received_at
    ON paytrace_iso2022simulator.oftl_iso20022_simulator (received_at);

CREATE INDEX IF NOT EXISTS idx_oftl_iso20022_simulator_requested_execution_date
    ON paytrace_iso2022simulator.oftl_iso20022_simulator (requested_execution_date);

CREATE INDEX IF NOT EXISTS idx_oftl_iso20022_simulator_processing_status
    ON paytrace_iso2022simulator.oftl_iso20022_simulator (processing_status);

COMMENT ON TABLE paytrace_iso2022simulator.oftl_iso20022_simulator IS
    'Stores pain.001 message-level metadata for the ISO 20022 simulator without persisting raw XML.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.message_id IS
    'Unique GrpHdr/MsgId from the inbound pain.001 message.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.message_name_id IS
    'ISO 20022 message definition identifier, typically pain.001.001.03.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.creation_date_time IS
    'GrpHdr/CreDtTm from the inbound pain.001 message.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.number_of_transactions IS
    'GrpHdr/NbOfTxs from the inbound pain.001 message.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.control_sum IS
    'GrpHdr/CtrlSum from the inbound pain.001 message.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.payment_information_count IS
    'Number of PmtInf blocks detected in the inbound pain.001 message.';

COMMENT ON COLUMN paytrace_iso2022simulator.oftl_iso20022_simulator.total_instructed_amount IS
    'Aggregate of CdtTrfTxInf/Amt/InstdAmt values across the message when available.';

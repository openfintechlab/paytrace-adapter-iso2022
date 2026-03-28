# PayTrace ISO 20022 Adapter

## Introduction

This service is a FastAPI-based PayTrace ISO 20022 adapter. It includes:

- Service bootstrap with FastAPI lifecycle hooks
- Centralized configuration loading from environment variables and `.env`
- PostgreSQL connection initialization through SQLAlchemy
- Schema-aware PostgreSQL startup configuration through `DBHelper`
- Header validation middleware for inbound API requests
- Base versioned, health, and probe routes
- Test scaffolding with `pytest`

## Project Structure

```text
src/
  main.py                 # Service entrypoint and startup lifecycle
  routes/Routes.py        # API route registration and default endpoints
  utilities/ConfigLoader.py
  utilities/DBHelper.py
  utilities/HeaderValidationMiddleware.py
  utilities/Logging.py
sql/
  001_create_oftl_iso20022_simulator.sql  # pain.001 metadata table DDL
tests/
  test_config_loader.py
  test_db_helper.py
  test_routes.py
```

## Prerequisites

- Python 3.11+ (recommended)
- `uv` installed
- PostgreSQL available for runtime startup checks

## Quick Start

### 1. Create local environment file

Copy the template environment file and edit values:

```bash
cp .env.example .env
```

Essential variables should be copied from `.env.example` and updated for your environment.

### 2. Fetch dependencies with `uv`

From the repository root:

```bash
uv sync
```

If you want to install as an editable package instead:

```bash
uv pip install -e .
```

### 3. Run the service

```bash
uv run python src/main.py
```

## Environment Variables

The adapter runtime uses the following environment variables.

### Service Routing

- `OFTL_SCA_CONTEXT_ROOT`: Base API path. Example: `/sca`
- `OFTL_SCA_VERSION`: API version segment. Example: `1`, exposed as `/v1`
- `OFTL_SCA_HOST`: Uvicorn bind host. Default fallback in code: `0.0.0.0`
- `OFTL_SCA_PORT`: Uvicorn bind port. Default fallback in code: `8081`

Final route prefix:

```text
${OFTL_SCA_CONTEXT_ROOT}/v${OFTL_SCA_VERSION}
```

Default example:

```text
/sca/v1
```

### Logging

- `OFTL_LOG_LEVEL`: Application/Uvicorn log level. Example: `INFO`
- `OFTL_LOG_FORMAT`: Python logging format string

### Database

Required for successful startup:

- `OFTL_POSTGRESDB_USERNAME`: PostgreSQL username
- `OFTL_POSTGRESDB_PASSWORD`: PostgreSQL password
- `OFTL_POSTGRESDB_HOST`: PostgreSQL hostname
- `OFTL_POSTGRESDB_PORT`: PostgreSQL port
- `OFTL_POSTGRESDB_NAME`: PostgreSQL database name

Optional:

- `OFTL_POSTGRESDB_SCHEMA`: PostgreSQL schema/search path. Default: `default`
- `OFTL_POSTGRESDB_POOLSIZE`: SQLAlchemy pool size. Default: `10`

### ISO 20022 metadata table

The repository includes PostgreSQL DDL for storing `pain.001` message metadata without persisting the raw XML payload:

```text
sql/001_create_oftl_iso20022_simulator.sql
```

The script creates:

- schema: `paytrace_iso2022simulator`
- table: `oftl_iso20022_simulator`

Design notes:

- `message_id` is enforced as unique to prevent duplicate ingestion of the same `GrpHdr/MsgId`.
- The table stores message-level metadata only, such as creation timestamp, transaction counts, control sum, debtor and initiator details, payment method, and aggregate instructed amount.
- The raw `pain.001` XML document is intentionally not stored in this table.

Reference `.env.example`:

```dotenv
OFTL_SCA_CONTEXT_ROOT="/sca"
OFTL_SCA_VERSION="1"
OFTL_SCA_HOST="0.0.0.0"
OFTL_SCA_PORT="8081"

OFTL_LOG_LEVEL="INFO"
OFTL_LOG_FORMAT="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"

OFTL_POSTGRESDB_USERNAME="admin"
OFTL_POSTGRESDB_PASSWORD="[CHANGE ME]"
OFTL_POSTGRESDB_HOST="localhost"
OFTL_POSTGRESDB_PORT="5432"
OFTL_POSTGRESDB_NAME="paytrace"
OFTL_POSTGRESDB_SCHEMA="default"
OFTL_POSTGRESDB_POOLSIZE="10"
```

No additional `OFTL_` runtime variables are referenced by this adapter codebase today.

## Run with Docker

### 1. Build the container image

From the repository root:

```bash
docker build -t pytrace-unittest-cimage:latest .
```

### 2. Run the container

Use the following command pattern to run the service with required environment variables:

```bash
docker run -d \
  --name paytrace-unittest-cimage01 \
  -p 8081:8081 \
  -e OFTL_SCA_CONTEXT_ROOT="/sca" \
  -e OFTL_SCA_VERSION="1" \
  -e OFTL_SCA_HOST="0.0.0.0" \
  -e OFTL_SCA_PORT="8081" \
  -e OFTL_LOG_LEVEL="INFO" \
  -e OFTL_LOG_FORMAT="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s" \
  -e OFTL_POSTGRESDB_USERNAME="admin" \
  -e OFTL_POSTGRESDB_PASSWORD="[CHANGE ME]" \
  -e OFTL_POSTGRESDB_HOST="host.docker.internal" \
  -e OFTL_POSTGRESDB_PORT="5432" \
  -e OFTL_POSTGRESDB_NAME="paytrace" \
  -e OFTL_POSTGRESDB_SCHEMA="default" \
  -e OFTL_POSTGRESDB_POOLSIZE="10" \
  pytrace-unittest-cimage:latest
```

Or use a `.env` file with `--env-file`:

```bash
docker run -d \
  --name paytrace-unittest-cimage01 \
  -p 8081:8081 \
  --env-file .env \
  pytrace-unittest-cimage:latest
```

### 3. Verify container and endpoints

```bash
docker logs -f paytrace-unittest-cimage01
curl http://localhost:8081/sca/v1/
curl http://localhost:8081/_healthz
curl http://localhost:8081/_probe
```

## Default Routes

Registered in `src/routes/Routes.py`:

- `POST /` under the versioned service prefix (for example: `POST /sca/v1/`)
- `GET /_healthz` (public)
- `GET /_probe` (public)

The JSON endpoints follow the PayTrace standard response envelope:

```json
{
  "result": {
    "code": "PT-0200",
    "description": "Resource retrieved successfully"
  },
  "payload": {
    "status": "ok"
  }
}
```

The middleware in `src/utilities/HeaderValidationMiddleware.py` enforces these request headers for non-exempt routes:

- `Authorization`
- `X-Transaction-Id`
- `X-Correlation-Id`
- `Accept-Language`
- `Accept`

For `POST`, `PUT`, and `PATCH`, it also requires:

- `Idempotency-Key`
- `Content-Type`

Quick check:

```bash
curl -X POST http://localhost:8081/sca/v1/ \
  -H 'Authorization: Bearer token' \
  -H 'X-Transaction-Id: 123e4567-e89b-12d3-a456-426614174000' \
  -H 'X-Correlation-Id: 123e4567-e89b-12d3-a456-426614174001' \
  -H 'Accept-Language: en-US' \
  -H 'Accept: application/xml' \
  -H 'Idempotency-Key: 123e4567-e89b-12d3-a456-426614174002' \
  -H 'Content-Type: application/xml' \
  --data-binary @pain001.xml
curl http://localhost:8081/_healthz
curl http://localhost:8081/_probe
```

### pain.001 Validation Endpoint

`POST ${OFTL_SCA_CONTEXT_ROOT}/v${OFTL_SCA_VERSION}/`

- Accepts a raw `pain.001` XML document in the request body.
- Returns a `pain.002` XML status report.
- If the XML is malformed or the root structure is not a `Document` containing `CstmrCdtTrfInitn`, the service responds with HTTP `400` and a rejection report (`GrpSts=RJCT`).
- If the inbound XML passes the basic syntax check, the service responds with HTTP `200` and an acceptance report (`GrpSts=ACCP`).

## Create a New Route

Add new route handlers inside `Routes._register_routes` in `src/routes/Routes.py`.

Example:

```python
@self.router.get("/transactions/ping")
async def transactions_ping() -> dict[str, str]:
    return {"service": "transactions", "status": "ok"}
```

With `OFTL_SCA_CONTEXT_ROOT=/sca` and `OFTL_SCA_VERSION=1`, this route becomes:

```text
GET /sca/v1/transactions/ping
```

## Testing

Run all tests:

```bash
uv run pytest tests -v
```

Run specific tests:

```bash
uv run pytest tests/test_config_loader.py -v
uv run pytest tests/test_db_helper.py -v
uv run pytest tests/test_routes.py -v
```

## Database Structure(s)

Please refer to the DDL script in `sql/001_create_oftl_iso20022_simulator.sql` for the PostgreSQL schema and table structure used for storing `pain.001` message metadata.

## Major Libraries Used

- `fastapi`: API framework
- `uvicorn`: ASGI server
- `pydantic`: data validation (FastAPI ecosystem)
- `environs`: environment variable parsing/loading
- `sqlalchemy`: database engine and ORM utilities
- `psycopg2-binary`: PostgreSQL driver
- `pytest`: test framework
- `httpx`: HTTP client used in test/runtime scenarios

# Threat model

## What this project does and where untrusted input enters

The Arthur Engine is a self-hosted service for guardrailing, tracing and evaluating LLM and ML
applications. Operators deploy it next to their own applications (Docker Compose, Helm or
CloudFormation templates under `deployment/`).

- `genai-engine/` is a FastAPI service backed by PostgreSQL. Its REST API (`src/routers/`) is called
  by applications with API keys and by users of the bundled UI. Untrusted input enters as:
  - prompts, model responses and context sent for guardrail validation (`validate_routes.py`), which
    are end-user text and must be treated as attacker-controlled;
  - OpenTelemetry / OpenInference traces ingested from instrumented applications
    (`trace_api_routes.py`, `legacy_span_routes.py`);
  - task, rule, prompt, dataset, notebook and experiment definitions created through the API;
  - model provider and RAG provider settings, including endpoints and API keys that the engine later
    calls (`model_provider_routes.py`, `rag_*_routes.py`, `secrets_routes.py`).
- `ml-engine/` is a job agent that polls for work and reads customer datasets through connectors
  (`src/ml_engine/connectors/`: object stores, warehouses, ODBC). Dataset contents are untrusted.
- `arthur-observability-sdk/` is a client library embedded in customer applications.
- `integrations/` holds tracers and skills for coding agents, and `endpoint-ai-discovery`, a script
  that runs as root on managed endpoints and reads local files.

## Components that matter most / least

Most:
- authentication and authorisation: API keys, roles, per-task access and multi-tenant isolation
  (`genai-engine/src/auth/`, `src/dependencies.py`, `src/repositories/api_key_repository.py`);
- secret storage and anything that returns or logs provider credentials
  (`src/repositories/secrets_repository.py`, `src/db_models/secret_storage_models.py`);
- outbound requests to operator-supplied URLs (model providers, RAG providers): SSRF;
- the rules engine and scorers that process prompts and responses (`src/rules_engine.py`,
  `src/scorer/`): injection into templates, queries or code paths;
- trace ingestion and querying: injection, cross-task data exposure;
- `integrations/endpoint-ai-discovery/`: privilege escalation or command injection on endpoints.

Least:
- `genai-engine/tests/`, `ml-engine/tests/`, `docs/`, notebooks and example code;
- the accuracy of guardrail models (a missed PII span or prompt injection is a quality issue, not a
  vulnerability in this code).

## How to exercise it

- Python environments are already installed: `uv run --no-sync --directory genai-engine ...`,
  `uv run --no-sync --directory ml-engine ...`.
- Unit tests: `uv run --no-sync --directory genai-engine pytest -m unit_tests` and
  `uv run --no-sync --directory ml-engine pytest tests/unit`. Tests that load Hugging Face guardrail
  models need a network and fail in the scan image; that is expected.
- `genai-engine/routes_security_check.py` reports API routes that have neither `@permission_checker`
  nor `@public_endpoint`.

## How you rate severity

- Critical: unauthenticated remote code execution; authentication bypass; reading or modifying
  another tenant's or task's data without credentials.
- High: remote code execution or SQL injection needing a valid API key; privilege escalation between
  roles; disclosure of stored provider secrets; SSRF reaching internal services; local privilege
  escalation through `endpoint-ai-discovery`.
- Medium: stored XSS in the UI; cross-task data exposure within one tenant by an authenticated user;
  denial of service from a single small request.
- Low: issues needing an administrator's credentials, information leaks without secrets, and denial
  of service that needs sustained high-volume traffic.

## Anything to leave alone

- Vulnerabilities in third-party dependencies and base images; we track those separately under
  `security/`.
- Default credentials in the local development templates under `deployment/docker-compose/`
  (`.env.template` files) that operators are expected to change.

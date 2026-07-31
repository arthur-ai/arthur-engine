# ML Engine

Job-based evaluation engine (Python 3.13). Polls the Arthur Platform for jobs, loads data through source connectors (S3, GCS, BigQuery, Snowflake, ODBC databases), and computes metrics. Flow: `job_agent.py` (polling) → `job_runner.py` (thread/process runners) → `job_executor.py` → `job_executors/*`.

## Commands

```bash
# The GenAI Engine client is generated, not committed — required before uv sync
cd scripts && ./openapi_client_utils.sh generate python && ./openapi_client_utils.sh install python && cd ..
./scripts/install_db_dependencies.sh     # ODBC / Oracle drivers

uv sync --group dev --group linters
uv run python src/ml_engine/job_agent.py
uv run pytest tests/unit
uv run mypy src/ml_engine
./scripts/lint.sh
```

Needs `ARTHUR_API_HOST`, `ARTHUR_CLIENT_ID`, `ARTHUR_CLIENT_SECRET` to talk to the platform.

## Gotchas

- Regenerate the GenAI Engine client whenever the GenAI Engine API changes.
- Job executors should be stateless and idempotent where possible.
- Health check endpoints must respond quickly — slow responses cause container restarts.

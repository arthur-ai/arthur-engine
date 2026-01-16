---
name: setup-genai-dev
description: Set up the GenAI Engine development environment. Use when starting work on the project for the first time, or when environment needs to be reset. Handles Poetry, PostgreSQL, migrations, and environment variables.
allowed-tools: Bash, Read, Write
---

# Setup GenAI Engine Development Environment

## Prerequisites Check

Before setup, verify these are installed:
1. Python 3.12 (`python3 --version`)
2. Docker is running (`docker ps`)
3. Poetry (`poetry --version`)

If any are missing, inform the user and stop.

## Setup Steps

Execute these steps in order:

### 1. Navigate to Project Directory
```bash
cd ./genai-engine
```

### 2. Configure Poetry Environment
```bash
poetry env use 3.12
poetry install --with dev,linters
```

### 3. Start PostgreSQL Database
```bash
docker compose up -d db
```

Wait for healthy status:
```bash
sleep 5
docker compose ps
```

### 4. Set Environment Variables

Export ALL of these environment variables:
```bash
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=changeme_pg_password
export POSTGRES_URL=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=arthur_genai_engine
export POSTGRES_USE_SSL=false
export PYTHONPATH="src:$PYTHONPATH"
export GENAI_ENGINE_SECRET_STORE_KEY="some_test_key"
export GENAI_ENGINE_ENVIRONMENT=local
export GENAI_ENGINE_ADMIN_KEY=test-admin-key
export GENAI_ENGINE_INGRESS_URI=http://localhost:3030
export GENAI_ENGINE_ENABLE_PERSISTENCE=enabled
export ALLOW_ADMIN_KEY_GENERAL_ACCESS=enabled
```

### 5. Run Database Migrations
```bash
cd ./genai-engine
poetry run alembic upgrade head
```

### 6. Verify Setup
Check database is running:
```bash
docker compose ps
```

Check migrations applied:
```bash
poetry run alembic current
```

## Output

Report success/failure for each step. If OpenAI/Azure credentials are needed for LLM features, ask the user to provide them:

- For OpenAI: `OPENAI_API_KEY`
- For Azure: `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS`

## Troubleshooting

- If Docker fails: ensure Docker Desktop is running
- If Poetry fails: try `poetry env remove 3.12` then retry
- If migrations fail: check PostgreSQL is healthy with `docker compose logs db`

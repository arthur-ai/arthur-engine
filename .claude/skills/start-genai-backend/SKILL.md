---
name: start-genai-backend
description: Start the GenAI Engine backend server and frontend UI. Use when you need to launch the API server at localhost:3030 and the frontend at localhost:3000.
allowed-tools: Bash, Read
---

# Start GenAI Engine Backend Server

## Pre-flight Checks

### 1. Verify PostgreSQL is running
```bash
cd ./genai-engine
docker compose ps db
```

If not running or unhealthy, start it:
```bash
docker compose up -d db
sleep 3
docker compose ps db
```

## Environment Variables

Set ALL of these environment variables before starting:

```bash
# Database
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=changeme_pg_password
export POSTGRES_URL=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=arthur_genai_engine
export POSTGRES_USE_SSL=false

# Application
export PYTHONPATH="src:$PYTHONPATH"
export GENAI_ENGINE_SECRET_STORE_KEY="some_test_key"
export GENAI_ENGINE_ENVIRONMENT=local
export GENAI_ENGINE_ADMIN_KEY=changeme123
export GENAI_ENGINE_INGRESS_URI=http://localhost:3030
export GENAI_ENGINE_ENABLE_PERSISTENCE=enabled
export ALLOW_ADMIN_KEY_GENERAL_ACCESS=enabled
```

## LLM Provider Configuration

Load LLM configuration from the `.env` file:
```bash
source ./genai-engine/.env
export OPENAI_API_KEY
export GENAI_ENGINE_OPENAI_PROVIDER
export GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
```

If `OPENAI_API_KEY` is not set in `.env`, inform the user they need to add it for LLM features to work.

## Start Backend Server

Run the server in the background so it doesn't block:
```bash
cd ./genai-engine
poetry run serve
```

Server will be available at:
- **API**: `http://localhost:3030`
- **Swagger Docs**: `http://localhost:3030/docs`
- **Health Check**: `http://localhost:3030/health`

## Start Frontend
```bash
cd ./genai-engine/ui
yarn install
yarn dev
```

Frontend will be available at: `http://localhost:3000`

## Authentication

To make API requests, use the admin key as a Bearer token:
```
Authorization: Bearer changeme123
```

## Verification

After starting, verify the server is running:
```bash
curl -s -H "Authorization: Bearer changeme123" http://localhost:3030/health
```

If successful, report the server is ready. If it fails, check the server logs for errors.

## Troubleshooting

- If port 3030 is in use: `lsof -i :3030` to find the process
- If database connection fails: verify PostgreSQL is running with `docker compose ps`
- If import errors: ensure `PYTHONPATH` includes `src`

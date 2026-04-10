---
name: start-genai-backend
description: Start the GenAI Engine backend server and frontend UI. Use when you need to launch the API server and the frontend locally.
allowed-tools: Bash, Read, Task
---

# Start GenAI Engine Backend Server

## Step 1 — GPT Key Gate

Use the Read tool to read `./genai-engine/.env`.

Check that `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS` is present and has a non-empty value (not just `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=` with nothing after the `=`).

If the value is missing or empty:
- **STOP immediately. Do not proceed to Step 2.**
- Tell the user: "Setup cannot continue. Please open `genai-engine/.env` and set `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS` using the format: `MODEL_NAME::ENDPOINT_URL::API_KEY` (e.g. `gpt-4o::https://api.openai.com/::sk-...`). Run the skill again once the key is set."

## Step 2 — Delegate Startup to Bash Sub-Agent

Only proceed here if Step 1 passed. Spawn a Task sub-agent with subagent_type="Bash" and the following self-contained prompt:

---
Start the GenAI Engine backend and frontend. Report success or failure for each step.

**Step 1 — Verify PostgreSQL is running:**
```bash
cd genai-engine && docker compose ps db
```
If not running or unhealthy, start it:
```bash
cd genai-engine && docker compose up -d db && sleep 3
```

**Step 2 — Start the backend server in the background:**
```bash
cd genai-engine && \
set -a && source .env && set +a && \
export POSTGRES_USER=postgres \
  POSTGRES_PASSWORD=changeme_pg_password \
  POSTGRES_URL=localhost \
  POSTGRES_PORT=5432 \
  POSTGRES_DB=arthur_genai_engine \
  POSTGRES_USE_SSL=false \
  PYTHONPATH="src:$PYTHONPATH" \
  GENAI_ENGINE_SECRET_STORE_KEY="some_test_key" \
  GENAI_ENGINE_ENVIRONMENT=local \
  GENAI_ENGINE_ADMIN_KEY=changeme123 \
  GENAI_ENGINE_ENABLE_PERSISTENCE=enabled \
  ALLOW_ADMIN_KEY_GENERAL_ACCESS=enabled && \
uv run serve &
```

**Step 3 — Wait for the backend to become healthy:**
```bash
sleep 5 && curl -s -H "Authorization: Bearer changeme123" http://localhost:3030/health
```

**Step 4 — Start the frontend and capture the URL:**
```bash
cd genai-engine/ui && yarn install && yarn dev 2>&1 | tee /tmp/vite-fe.log &
sleep 3 && grep -m1 "Local:" /tmp/vite-fe.log
```

Report the following when done:
- Backend API: the health check URL with `/docs` appended
- Frontend: the Local URL that Vite printed
- Auth header: `Authorization: Bearer changeme123`
---

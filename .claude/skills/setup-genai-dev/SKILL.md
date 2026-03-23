---
name: setup-genai-dev
description: Set up the GenAI Engine development environment. Use when starting work on the project for the first time, or when environment needs to be reset. Handles Poetry, PostgreSQL, migrations, and environment variables.
allowed-tools: Bash, Read, Task
---

# Setup GenAI Engine Development Environment

## Step 1 — GPT Key Gate

Use the Read tool to read `./genai-engine/.env`.

Check that `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS` is present and has a non-empty value (not just `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=` with nothing after the `=`).

If the value is missing or empty:
- **STOP immediately. Do not proceed to Step 2.**
- Tell the user: "Setup cannot continue. Please open `genai-engine/.env` and set `GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS` using the format: `MODEL_NAME::ENDPOINT_URL::API_KEY` (e.g. `gpt-4o::https://api.openai.com/::sk-...`). Run the skill again once the key is set."

## Step 2 — Delegate Setup to Bash Sub-Agent

Only proceed here if Step 1 passed. Spawn a Task sub-agent with subagent_type="Bash" and the following self-contained prompt:

---
Run the following setup steps for the GenAI Engine development environment. Report success or failure for each step and stop immediately if any step fails.

**Step 1 — Prerequisites check:**
```bash
python3 --version && docker ps && poetry --version
```
If any fail, report which tool is missing and stop.

**Step 2 — Configure Poetry and install dependencies:**
```bash
cd genai-engine && poetry env use 3.12 && poetry install --with dev,linters
```

**Step 3 — Start PostgreSQL:**
```bash
cd genai-engine && docker compose up -d db && sleep 5 && docker compose ps
```

**Step 4 — Run database migrations with all required env vars:**
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
poetry run alembic upgrade head && poetry run alembic current
```

Report the final migration revision that is current after running these steps.
---

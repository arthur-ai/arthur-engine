---
name: generate-client
description: Regenerate the arthur_genai_client package from the GenAI Engine OpenAPI spec. Use when the GenAI Engine API has changed, or when src/arthur_genai_client/ is missing after a fresh clone.
allowed-tools: Bash, Read
---

# Regenerate the Arthur GenAI API Client

The `arthur_genai_client` package under `src/` is auto-generated and gitignored.
It must be present before running tests, linting (mypy), or using prompt management features.

## Steps

### 1. Check prerequisites

```bash
node --version   # needs Node.js (any recent LTS)
java -version    # needs Java 11+
```

If either is missing, tell the user to install them and stop.

### 2. Generate and install

From the `arthur-observability-sdk/` directory:

```bash
./scripts/generate_openapi_client.sh generate python
./scripts/generate_openapi_client.sh install python
```

`generate python` will:
- Install / update `openapi-generator-cli` via npm if needed
- Read `genai-engine/staging.openapi.json`
- Write the generated package to `src/arthur_genai_client/`

`install python` runs `poetry install` to register the generated package in the venv.

### 3. Verify

```bash
python -c "from arthur_genai_client.models.agentic_prompt import AgenticPrompt; print('OK')"
```

If that prints `OK`, the client is ready. If it errors, re-run step 2.

## Notes

- Do **not** hand-edit any file inside `src/arthur_genai_client/` — changes will be lost on the next regeneration.
- The generator requires the GenAI Engine spec at `genai-engine/staging.openapi.json`. If that file is missing, update it from the running GenAI Engine: `curl http://localhost:3030/openapi.json > ../genai-engine/staging.openapi.json`

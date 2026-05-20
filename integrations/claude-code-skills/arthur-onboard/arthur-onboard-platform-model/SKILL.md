---
name: arthur-onboard-platform-model
description: Arthur onboarding sub-skill — Platform Step 5: Gate on application type, create an Agentic Model on Arthur Platform, and retrieve GenAI Engine task connection info. Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write
---

# Arthur Onboard — Platform Step 5: Create Agentic Model

**Goal:** Gate on application type; for Agentic applications, create a Project and Agentic Model on the platform, then retrieve GenAI Engine task connection info to establish `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, and `ARTHUR_TASK_ID` in `.arthur-engine.env` — the same variables consumed by all downstream reused sub-skills (instrument, prompts, verify, eval-provider, evals).

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_PLATFORM_URL`, `ARTHUR_PLATFORM_TOKEN`, `ARTHUR_PLATFORM_WORKSPACE_ID`, `ARTHUR_PLATFORM_ENGINE_ID`, `ARTHUR_PLATFORM_PROJECT_ID`, `ARTHUR_PLATFORM_MODEL_ID`, `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID` from the output.

**State write helper:**
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_TASK_ID=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_TASK_ID=$TASK_ID" >> "$STATE_FILE"
```

---

## Ensure Token is Valid

Platform tokens expire after ~5 minutes. Before making any platform API calls, verify and auto-refresh if needed (all in one Bash call):

```bash
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
ARTHUR_PLATFORM_TOKEN=$(grep '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

TOKEN_CHECK=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
echo "TOKEN_CHECK=$TOKEN_CHECK"

if [ "$TOKEN_CHECK" != "200" ]; then
  CLIENT_ID=$(grep '^ARTHUR_PLATFORM_CLIENT_ID=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
  CLIENT_SECRET=$(grep '^ARTHUR_PLATFORM_CLIENT_SECRET=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
  if [ -z "$CLIENT_SECRET" ]; then
    echo "TOKEN_REFRESH=MISSING_CREDENTIALS"
  else
    TOKEN_ENDPOINT=$(curl -s "${ARTHUR_PLATFORM_URL}/api/v1/auth/oidc/.well-known/openid-configuration" | \
      python3 -c "import sys,json; print(json.load(sys.stdin).get('token_endpoint',''))" 2>/dev/null)
    NEW_TOKEN=$(curl -s -X POST "$TOKEN_ENDPOINT" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data-urlencode "grant_type=client_credentials" \
      --data-urlencode "client_id=$CLIENT_ID" \
      --data-urlencode "client_secret=$CLIENT_SECRET" \
      --data-urlencode "scope=openid email profile" | \
      python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
    if [ -n "$NEW_TOKEN" ]; then
      grep -v '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp .arthur-engine.env
      echo "ARTHUR_PLATFORM_TOKEN=$NEW_TOKEN" >> .arthur-engine.env
      echo "TOKEN_REFRESH=OK"
    else
      echo "TOKEN_REFRESH=FAILED"
    fi
  fi
fi
```

If `TOKEN_REFRESH=MISSING_CREDENTIALS` or `TOKEN_REFRESH=FAILED`: re-invoke `arthur-onboard-platform-access` to re-authenticate, then resume this skill.

---

## If ARTHUR_ENGINE_URL + ARTHUR_API_KEY + ARTHUR_TASK_ID All Exist

All downstream state is already set. Confirm reuse with user ("Use existing task `<ARTHUR_TASK_ID>`?") and exit this skill.

---

## Gate: Determine Application Type

Ask the user:
> "What type of application are you onboarding?
>
> **A) Agentic application** — LLM-powered agents, chatbots, RAG systems, or any app that emits traces. Creates an **Agentic Model** on the platform.
> **B) ML Model** — classification, regression, or tabular data models
> **C) GenAI Model** — LLM completions or generative models (non-agentic)"

> **Note:** "Agentic Model" and "GenAI Model" are distinct model types on the Arthur Platform. This skill creates **Agentic Models** only. GenAI Models are a separate platform type and must be onboarded through the platform UI.

**For B or C:**
> "For ML and GenAI Models, please log in to **<ARTHUR_PLATFORM_URL>**, navigate to **Applications**, and follow the platform UI wizard to onboard your model. The platform provides a guided onboarding flow for these model types."
>
> "Exiting — this skill handles Agentic applications only."

Exit this skill without modifying state.

**For A:** Continue below.

---

## Select or Create a Project

An Agentic Model belongs to a Project within a Workspace. List existing projects:

```bash
PROJECTS_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/workspaces/${ARTHUR_PLATFORM_WORKSPACE_ID}/projects")
PROJECT_LIST=$(echo "$PROJECTS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
projects = d.get('resources') or d.get('data') or d.get('projects') or (d if isinstance(d, list) else [])
for p in projects:
    print(f'  {p[\"id\"]}: {p[\"name\"]}')
if not projects:
    print('  (no projects yet)')
" 2>/dev/null || echo "  (error parsing response)")
echo "$PROJECT_LIST"
```

If `ARTHUR_PLATFORM_PROJECT_ID` exists in state, confirm reuse or allow re-selection.

Show the list and ask the user to select an existing project or create a new one.

**To create a new project:**
```bash
PROJECT_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$PROJECT_NAME\"}" \
  "${ARTHUR_PLATFORM_URL}/api/v1/workspaces/${ARTHUR_PLATFORM_WORKSPACE_ID}/projects")
PROJECT_ID=$(echo "$PROJECT_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "PROJECT_ID=$PROJECT_ID"
```

Save `ARTHUR_PLATFORM_PROJECT_ID` to state:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_PROJECT_ID=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_PROJECT_ID=$PROJECT_ID" >> "$STATE_FILE"
```

---

## List Existing Models in the Project

```bash
MODELS_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/projects/${PROJECT_ID}/models")
MODEL_LIST=$(echo "$MODELS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
models = d.get('resources') or d.get('data') or d.get('models') or (d if isinstance(d, list) else [])
for m in models:
    print(f'  {m[\"id\"]}: {m[\"name\"]}')
if not models:
    print('  (no models yet)')
" 2>/dev/null || echo "  (error parsing response)")
echo "$MODEL_LIST"
```

Show the list and ask: "Select an existing model to instrument, or create a new one?"

If the user selects an existing model, skip to "Poll for Task Connection Info" with the selected `MODEL_ID`.

---

## Create Agentic Model

Ask the user for the model name (e.g., "Customer Support Bot", "Code Assistant").

> **No connector setup needed.** When an Agentic Model is created on the platform, an implicit connector is configured automatically — do not create a connector explicitly. The "Shield connector" visible in the platform UI is for the Arthur Shield product (a separate use case) and must **not** be created here.

```bash
MODEL_PAYLOAD=$(python3 -c "
import json
print(json.dumps({
  'name': '$MODEL_NAME',
  'data_plane_id': '$ARTHUR_PLATFORM_ENGINE_ID'
}))
")
MODEL_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$MODEL_PAYLOAD" \
  "${ARTHUR_PLATFORM_URL}/api/v1/projects/${PROJECT_ID}/models")
MODEL_ID=$(echo "$MODEL_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "MODEL_ID=$MODEL_ID"
```

If `MODEL_ID` is empty: show the raw response; check if the endpoint or payload schema has changed by reviewing `<ARTHUR_PLATFORM_URL>/api/docs`. Try the alternate endpoint `/api/v1/workspaces/${ARTHUR_PLATFORM_WORKSPACE_ID}/models` if `/api/v1/projects/{id}/models` returns 404.

Save `ARTHUR_PLATFORM_MODEL_ID` to state:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_MODEL_ID=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_MODEL_ID=$MODEL_ID" >> "$STATE_FILE"
```

---

## Poll for Task Connection Info

The platform dispatches an async job to the registered engine to create the underlying GenAI Engine task. Poll for the task connection info — make **individual Bash calls one per check cycle**. Because tokens expire in ~5 minutes, each call reads the token fresh from the state file and refreshes it automatically if needed:

```bash
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
ARTHUR_PLATFORM_TOKEN=$(grep '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
MODEL_ID=$(grep '^ARTHUR_PLATFORM_MODEL_ID=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

# Auto-refresh token if expired
TOKEN_CHECK=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
if [ "$TOKEN_CHECK" != "200" ]; then
  CLIENT_SECRET=$(grep '^ARTHUR_PLATFORM_CLIENT_SECRET=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
  TOKEN_ENDPOINT=$(curl -s "${ARTHUR_PLATFORM_URL}/api/v1/auth/oidc/.well-known/openid-configuration" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token_endpoint',''))" 2>/dev/null)
  ARTHUR_PLATFORM_TOKEN=$(curl -s -X POST "$TOKEN_ENDPOINT" -H "Content-Type: application/x-www-form-urlencoded" --data-urlencode "grant_type=client_credentials" --data-urlencode "client_id=$(grep '^ARTHUR_PLATFORM_CLIENT_ID=' .arthur-engine.env | cut -d= -f2-)" --data-urlencode "client_secret=$CLIENT_SECRET" --data-urlencode "scope=openid email profile" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
  grep -v '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp .arthur-engine.env
  echo "ARTHUR_PLATFORM_TOKEN=$ARTHUR_PLATFORM_TOKEN" >> .arthur-engine.env
fi

CONN_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/models/${MODEL_ID}/task/connection_info")
CONN_STATUS=$(echo "$CONN_RESPONSE" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
print('OK' if d.get('api_host') else 'WAITING')
" 2>/dev/null || echo "WAITING")
echo "CONN_STATUS=$CONN_STATUS"
```

Retry every 10 seconds, up to 30 times (~5 minutes). Stop when `CONN_STATUS=OK`.

If still `WAITING` after 30 attempts:
- Guide the user to the platform UI: **Applications → <model name> → Task** tab to check for provisioning errors
- Ask the user if they can see a task ID in the UI and enter it manually (as a fallback)

Extract the connection info fields:
```bash
TASK_ID=$(echo "$CONN_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task_id',''))" 2>/dev/null)
ENGINE_URL=$(echo "$CONN_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('api_host',''))" 2>/dev/null)
ENGINE_API_KEY=$(echo "$CONN_RESPONSE" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
vk = d.get('validation_key') or {}
print(vk.get('key',''))
" 2>/dev/null)
echo "TASK_ID=$TASK_ID"
echo "ENGINE_URL=$ENGINE_URL"
echo "HAS_KEY=$([ -n "$ENGINE_API_KEY" ] && echo 'yes' || echo 'no')"
```

If any of the three values are empty after receiving `CONN_STATUS=OK`: show the full raw response and ask the user to identify the correct field names from the response JSON (the field names may differ across platform versions).

---

## Verify Engine API Key

Confirm the connection info works against the GenAI Engine:
```bash
VERIFY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ENGINE_API_KEY" \
  "${ENGINE_URL}/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
echo "ENGINE_API_VERIFY=$VERIFY_STATUS"
```

- `200` → all good
- `401` → API key is wrong; check connection info
- anything else → engine may not be reachable at `ENGINE_URL`; verify the engine is running and the URL is correct

---

## Save All Downstream State

```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_ENGINE_URL=\|^ARTHUR_API_KEY=\|^ARTHUR_TASK_ID=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_ENGINE_URL=$ENGINE_URL" >> "$STATE_FILE"
echo "ARTHUR_API_KEY=$ENGINE_API_KEY" >> "$STATE_FILE"
echo "ARTHUR_TASK_ID=$TASK_ID" >> "$STATE_FILE"
```

Tell the user:
> "Agentic model created and connected to the engine.
>
>   Engine URL:  <ENGINE_URL>
>   Task ID:     <TASK_ID>
>
> These have been saved to `.arthur-engine.env`. The next steps will instrument your code to send traces to this engine."

Exit this skill.

---
name: arthur-onboard-oss-engine
description: Arthur onboarding sub-skill — Step 2: Ensure Arthur GenAI Engine is available (local install or remote). Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write, Edit, Task
---

# Arthur Onboard — Step 2: Ensure Arthur GenAI Engine Is Available

**Goal:** Establish `ARTHUR_ENGINE_URL` and `ARTHUR_API_KEY` in `.arthur-engine.env`.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL` and `ARTHUR_API_KEY` from the output.

**State write helper** — use this pattern to update individual values without clobbering others:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_ENGINE_URL=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo 'ARTHUR_ENGINE_URL=http://localhost:3030' >> "$STATE_FILE"
```

---

## If Both Values Exist — Verify Reachability

```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
echo "HTTP_STATUS=$HTTP_STATUS"
```

- `200` → confirm reuse with user, then exit this skill (engine step done)
- `401` → engine reachable but key is wrong; ask user to re-enter API key, update state, then exit
- anything else → engine unreachable; proceed to setup below

---

## Set Up Engine (No Config or Unreachable)

Ask the user: "How would you like to connect to Arthur GenAI Engine?"
- **A) Install locally on this machine (requires Docker)**
- **B) Connect to a remote Arthur Engine**

---

### Option A — Local Install

Detect OS:
```bash
OS_TYPE=$(uname -s 2>/dev/null || echo "Windows_NT")
echo "OS_TYPE=$OS_TYPE"
```
`Darwin` = Mac, `Linux` = Linux, anything else = Windows.

Ask the user for OpenAI/Azure OpenAI config for guardrails:
> "Do you have an OpenAI or Azure OpenAI API key to configure for Arthur Engine guardrails?
> This is used for hallucination and sensitive data checks. You can skip and add it manually to
> `~/.arthur-engine/local-stack/genai-engine/.env` later."

If yes, collect:
1. Provider — `OpenAI` or `Azure` (default: `OpenAI`)
2. Model name (default: `gpt-4o-mini-2024-07-18`)
3. Endpoint — required for Azure; leave blank for standard OpenAI
4. API key — show the user this message and wait for their confirmation before proceeding (do **not** ask them to type the key in chat; do **not** run getpass via the Bash tool — it has no TTY):
   > To keep your API key secure, please run this command directly in your terminal (the `!` prefix runs it in your shell where input is masked):
   >
   > `! python3 -c "import getpass, os, stat; p=os.path.expanduser('~/.ae_tmp_key'); key=getpass.getpass('OpenAI API key (hidden): '); open(p,'w').write(key); os.chmod(p, 0o600); print('Key saved.')"`
   >
   > Let me know once you've run it and I'll continue.

   After the user confirms, use `~/.ae_tmp_key` as `<KEY_FILE_PATH>` in the sub-agent prompt below.

If no, set `SETUP_SKIP_OPENAI=true`.

**Note:** This key goes into the Docker `.env` and configures the engine's built-in guardrails.
It is **separate** from the eval model provider in Step 8, which is configured via the Arthur Engine API.

Before launching the sub-agent, tell the user:
> "Starting the Arthur GenAI Engine installer now. **Note:** the first time the engine starts, it needs to download several AI models (this can take 10–15 minutes depending on your connection). I'll keep you updated as it boots."

Then run this to capture a timestamp before the installer starts (you'll use it later to display startup logs):
```bash
date -u "+%Y-%m-%dT%H:%M:%SZ"
```
Remember this value as `PRE_INSTALL_TIME`.

Now delegate to a sub-agent using the Agent tool. **IMPORTANT: set `run_in_background=false` (the default) — do NOT background this agent.** Fill in the values collected above:

**Mac/Linux sub-agent prompt:**
```
Run the Arthur GenAI Engine local installer.

Step 1 — Run the installer non-interactively (takes 2-3 minutes).
Replace <VALUES> with the actual values collected from the user:

SETUP_NON_INTERACTIVE=true \
SETUP_SKIP_OPENAI=<true_if_no_openai|false> \
GENAI_ENGINE_OPENAI_PROVIDER=<provider> \
GENAI_ENGINE_OPENAI_GPT_NAME=<model_name> \
GENAI_ENGINE_OPENAI_GPT_ENDPOINT=<endpoint_or_empty> \
GENAI_ENGINE_OPENAI_GPT_API_KEY=$(cat "<KEY_FILE_PATH>" && rm -f "<KEY_FILE_PATH>") \
bash <(curl -sSL https://get-genai-engine.arthur.ai/mac)

Step 2 — Extract the admin API key:
cat "$HOME/.arthur-engine/local-stack/genai-engine/.env" 2>/dev/null | grep -E "GENAI_ENGINE_ADMIN_KEY|ARTHUR_API_KEY" | head -1

Report: installer exit code (0=success), the API key found (full value or "NOT_FOUND"), any errors.
```

**Windows sub-agent prompt:**
```
Run the Arthur GenAI Engine local Windows installer.

Step 1 — Run the installer non-interactively via PowerShell (takes 2-3 minutes).
Replace <VALUES> with the actual values collected from the user:

powershell.exe -Command "
  \$env:SETUP_NON_INTERACTIVE = 'true'
  \$env:SETUP_SKIP_OPENAI = '<true_if_no_openai|false>'
  \$env:GENAI_ENGINE_OPENAI_PROVIDER = '<provider>'
  \$env:GENAI_ENGINE_OPENAI_GPT_NAME = '<model_name>'
  \$env:GENAI_ENGINE_OPENAI_GPT_ENDPOINT = '<endpoint_or_empty>'
  \$env:GENAI_ENGINE_OPENAI_GPT_API_KEY = (Get-Content -Path '<KEY_FILE_PATH>' -Raw).Trim(); Remove-Item -Path '<KEY_FILE_PATH>' -Force
  irm https://get-genai-engine.arthur.ai/win | iex
"

Step 2 — Extract the admin API key (try bash path first, fall back to PowerShell):
cat "$USERPROFILE/.arthur-engine/local-stack/genai-engine/.env" 2>/dev/null | grep -E "GENAI_ENGINE_ADMIN_KEY|ARTHUR_API_KEY" | head -1 || \
powershell.exe -Command "Get-Content (Join-Path \$env:USERPROFILE '.arthur-engine\local-stack\genai-engine\.env') | Select-String 'GENAI_ENGINE_ADMIN_KEY|ARTHUR_API_KEY' | Select-Object -First 1"

Report: installer exit code (0=success), the API key found (full value or "NOT_FOUND"), any errors.
```

After sub-agent:
- Set `ARTHUR_API_KEY` to extracted key (or ask user if not found)
- Set `ARTHUR_ENGINE_URL=http://localhost:3030`
- Save both to state file

Then poll for engine readiness by making **individual Bash calls — one per check cycle, NOT a single long loop**. Each completed call's output is immediately visible in the conversation. Make calls roughly 10 seconds apart until the engine is ready or 10 minutes have elapsed.

Use `PRE_INSTALL_TIME` (captured before the installer ran) as the initial `--since` value so the first check shows all startup logs. Each call prints `NEXT_LOG_SINCE` — use that as `--since` for the next call.

**Each individual Bash call (Mac/Linux):**
```bash
COMPOSE_DIR="$HOME/.arthur-engine/local-stack/genai-engine"
sleep 10
if [ -f "$COMPOSE_DIR/docker-compose.yml" ]; then
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" logs --no-color \
    --since="<LAST_LOG_SINCE>" 2>&1 || true
fi
echo "NEXT_LOG_SINCE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:3030/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
echo "ENGINE_STATUS=$STATUS"
```

Replace `<LAST_LOG_SINCE>` with `PRE_INSTALL_TIME` on the first call, then with `NEXT_LOG_SINCE` from the previous call on each subsequent call.

**Each individual Bash call (Windows):**
```bash
COMPOSE_FILE=$(wslpath "$USERPROFILE/.arthur-engine/local-stack/genai-engine/docker-compose.yml" \
  2>/dev/null || echo "$USERPROFILE/.arthur-engine/local-stack/genai-engine/docker-compose.yml")
sleep 10
if [ -f "$COMPOSE_FILE" ]; then
  docker compose -f "$COMPOSE_FILE" logs --no-color --since="<LAST_LOG_SINCE>" 2>&1 || true
fi
echo "NEXT_LOG_SINCE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:3030/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
echo "ENGINE_STATUS=$STATUS"
```

Stop when `ENGINE_STATUS=200` or `ENGINE_STATUS=401`. Max 60 calls (~10 min). If not ready after 60 calls: inform the user and ask if they want to keep waiting.

---

### Option B — Remote

Ask user for URL and API key. Verify:
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $USER_API_KEY" \
  "$USER_URL/api/v2/tasks?page=0&page_size=1"
```
`200` → save to state file. Other → report error and ask user to recheck.

---
name: arthur-onboard
description: Onboard an agentic application to Arthur GenAI Engine. Guides through engine connection, task setup, code instrumentation, trace verification, and eval configuration. Invoke from any agentic application repository.
allowed-tools: Bash, Read, Write, Edit, Task
---

# Onboard to Arthur GenAI Engine

You are guiding the user through the complete Arthur GenAI Engine onboarding workflow. Work through each step in order. Be conversational — ask the user before making changes to their code or configuration.

**Target repository:** The current working directory, unless the user specifies a different path.

---

## State File

Persist all state to `.arthur-engine.env` in the root of the target repository. This file is per-project and should be gitignored.

**Before starting:** Read the state file:
```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse existing values for `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`.

If all three exist, display them and ask:
> "Found existing Arthur Engine configuration. Continue with these settings, or start fresh?"

**Writing state:** Use this pattern to update individual values without clobbering others:
```bash
STATE_FILE=".arthur-engine.env"
# Remove old value then append new one:
grep -v '^ARTHUR_ENGINE_URL=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo 'ARTHUR_ENGINE_URL=http://localhost:3030' >> "$STATE_FILE"
```

Also ensure the file is gitignored:
```bash
grep -qxF '.arthur-engine.env' .gitignore 2>/dev/null || echo '.arthur-engine.env' >> .gitignore
```

---

## Step 1/10 — Pre-flight Checks

Check git status in the target repo:
```bash
git status --porcelain
```
- Unstaged/untracked changes → warn the user (do NOT block — staged changes are fine)
- Not a git repo → note it but continue

Skip Claude Code auth check — the user is already authenticated (they are talking to you right now).

---

## Step 2/10 — Ensure Arthur GenAI Engine Is Available

**Goal:** Establish `ARTHUR_ENGINE_URL` and `ARTHUR_API_KEY` in the state file.

### If state has both values — verify reachability:
```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
echo "HTTP_STATUS=$HTTP_STATUS"
```
- `200` → confirm reuse with user, then proceed to Step 3
- `401` → engine reachable but key is wrong; ask user to re-enter API key
- anything else → engine unreachable; proceed to setup below

### Set up engine (if no existing config or unreachable):

Ask the user: "How would you like to connect to Arthur GenAI Engine?"
- **A) Install locally on this machine (requires Docker)**
- **B) Connect to a remote Arthur Engine**

**Option A — Local install:**

First, detect the OS:
```bash
OS_TYPE=$(uname -s 2>/dev/null || echo "Windows_NT")
echo "OS_TYPE=$OS_TYPE"
```
`Darwin` = Mac, `Linux` = Linux, anything else = Windows.

Next, ask the user for OpenAI/Azure OpenAI config for guardrails:
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

Now delegate to a Task sub-agent with `subagent_type="Bash"`, filling in the values collected above:

**Mac/Linux sub-agent prompt:**
```
Run the Arthur GenAI Engine local installer and wait until the engine is ready.

Step 1 — Run the installer non-interactively (takes 2-3 minutes).
Replace <VALUES> with the actual values collected from the user:

SETUP_NON_INTERACTIVE=true \
SETUP_SKIP_OPENAI=<true_if_no_openai|false> \
GENAI_ENGINE_OPENAI_PROVIDER=<provider> \
GENAI_ENGINE_OPENAI_GPT_NAME=<model_name> \
GENAI_ENGINE_OPENAI_GPT_ENDPOINT=<endpoint_or_empty> \
GENAI_ENGINE_OPENAI_GPT_API_KEY=$(cat "<KEY_FILE_PATH>" && rm -f "<KEY_FILE_PATH>") \
bash <(curl -sSL https://get-genai-engine.arthur.ai/mac)

Step 2 — Poll until ready (max 15 minutes). The first startup downloads AI models and takes
significantly longer than subsequent starts. Print a status line every 30 seconds so the user
knows progress is being made.

echo "Engine starting up — first-time launch downloads AI models and may take 10-15 minutes..."
ELAPSED=0
for i in $(seq 1 180); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3030/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
    echo "ENGINE_READY=true STATUS=$STATUS elapsed=${ELAPSED}s"; break
  fi
  ELAPSED=$((i * 5))
  MINS=$((ELAPSED / 60))
  SECS=$((ELAPSED % 60))
  # Print an update every 30 seconds (every 6th iteration)
  if [ $((i % 6)) -eq 0 ]; then
    echo "Still starting up... ${MINS}m${SECS}s elapsed (models may still be downloading)"
  fi
  sleep 5
done
if [ "$STATUS" != "200" ] && [ "$STATUS" != "401" ]; then
  echo "ENGINE_READY=false — timed out after 15 minutes"
fi

Step 3 — Extract the admin API key:
cat "$HOME/.arthur-engine/local-stack/genai-engine/.env" 2>/dev/null | grep -E "GENAI_ENGINE_ADMIN_KEY|ARTHUR_API_KEY" | head -1

Report: engine ready (yes/no), total elapsed time, the API key found (full value or "NOT_FOUND"), any errors.
```

**Windows sub-agent prompt:**
```
Run the Arthur GenAI Engine local Windows installer and wait until the engine is ready.

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

Step 2 — Poll until ready (max 15 minutes). The first startup downloads AI models and takes
significantly longer than subsequent starts. Print a status line every 30 seconds so the user
knows progress is being made.

echo "Engine starting up — first-time launch downloads AI models and may take 10-15 minutes..."
ELAPSED=0
for i in $(seq 1 180); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3030/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
    echo "ENGINE_READY=true STATUS=$STATUS elapsed=${ELAPSED}s"; break
  fi
  ELAPSED=$((i * 5))
  MINS=$((ELAPSED / 60))
  SECS=$((ELAPSED % 60))
  # Print an update every 30 seconds (every 6th iteration)
  if [ $((i % 6)) -eq 0 ]; then
    echo "Still starting up... ${MINS}m${SECS}s elapsed (models may still be downloading)"
  fi
  sleep 5
done
if [ "$STATUS" != "200" ] && [ "$STATUS" != "401" ]; then
  echo "ENGINE_READY=false — timed out after 15 minutes"
fi

Step 3 — Extract the admin API key (try bash path first, fall back to PowerShell):
cat "$USERPROFILE/.arthur-engine/local-stack/genai-engine/.env" 2>/dev/null | grep -E "GENAI_ENGINE_ADMIN_KEY|ARTHUR_API_KEY" | head -1 || \
powershell.exe -Command "Get-Content (Join-Path \$env:USERPROFILE '.arthur-engine\local-stack\genai-engine\.env') | Select-String 'GENAI_ENGINE_ADMIN_KEY|ARTHUR_API_KEY' | Select-Object -First 1"

Report: engine ready (yes/no), total elapsed time, the API key found (full value or "NOT_FOUND"), any errors.
```

After sub-agent:
- Set `ARTHUR_ENGINE_URL=http://localhost:3030`
- Set `ARTHUR_API_KEY` to extracted key (or ask user if not found)
- Save to state file

**Option B — Remote:**

Ask user for URL and API key. Verify:
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $USER_API_KEY" \
  "$USER_URL/api/v2/tasks?page=0&page_size=1"
```
`200` → save to state file. Other → report error and ask user to recheck.

---

## Step 3/10 — Set Up Arthur Task

**Goal:** Establish `ARTHUR_TASK_ID` in the state file.

If state has `ARTHUR_TASK_ID`, confirm reuse and proceed.

Otherwise, list existing tasks:
```bash
curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v2/tasks" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
tasks = d.get('tasks') or d.get('data') or []
tasks = [t for t in tasks if not t.get('is_system_task')]
for t in tasks:
    print(f'  {t[\"id\"]}: {t[\"name\"]}')
"
```

Show the list and ask: "Select an existing task, or create a new one?"

To create a task:
```bash
TASK_ID=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$TASK_NAME\"}" \
  "$ARTHUR_ENGINE_URL/api/v2/tasks" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "TASK_ID=$TASK_ID"
```

Save the task ID to the state file.

---

## Step 4/10 — Analyze Repository

Detect language, framework, and existing instrumentation by examining the repo:

```bash
# Language detection
[ -f requirements.txt ] || [ -f pyproject.toml ] && echo "PYTHON=yes"
[ -f tsconfig.json ] || [ -f package.json ] && echo "NODE=yes"

# Framework detection
grep -r --include="*.py" --include="*.ts" --include="*.js" -l \
  "mastra\|langchain\|openai\|anthropic\|crewai\|autogen" . 2>/dev/null | head -5

# Existing instrumentation
grep -r --include="*.py" --include="*.ts" --include="*.js" -l \
  "arthur\.instrument\|arthur_observability\|ArthurExporter\|openinference" . 2>/dev/null | head -3
```

Also read `requirements.txt`, `pyproject.toml`, `package.json`, and the likely entry point (`main.py`, `app.py`, `src/mastra/index.ts`, `src/index.ts`, etc.).

Determine:
- **language**: `python` | `typescript` | `javascript` | `unknown`
- **framework**: `mastra` | `langchain` | `openai` | `anthropic` | `crewai` | `other` | `unknown`
- **isInstrumented**: true if Arthur SDK, `@mastra/arthur`, or `openinference` already present

---

## Step 5/10 — Instrument Code

**If already instrumented:** Tell the user, skip this step.

**If not instrumented:** Based on detection results, choose the approach:
- Python app → `arthur-sdk` (preferred)
- Mastra TypeScript → `mastra-arthur`
- Other TypeScript/JavaScript or Python without arthur-sdk → `openinference`

Show the planned changes and ask user to confirm before proceeding.

**Delegate instrumentation to a Task sub-agent** (full claude agent). Replace `<PLACEHOLDERS>` with actual values from the state file and analysis.

---

### Python — arthur-sdk instrumentation task prompt:

```
You are an expert Python developer. Instrument the agentic application at: <REPO_PATH>

Arthur Engine URL: <ARTHUR_ENGINE_URL>
Arthur Task ID: <ARTHUR_TASK_ID>

RULES:
- Never hardcode API keys. Always read from env vars.
- Add to .env (create if missing; ensure .env is gitignored):
    ARTHUR_API_KEY=$ARTHUR_API_KEY
    ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
    ARTHUR_TASK_ID=<ARTHUR_TASK_ID>
- Add placeholders to .env.example.
- Smallest possible changes — instrument, don't refactor.
- Print final JSON on the last line: {"success":true,"testsPassed":true,"summary":"<one sentence>"}

STEP 1 — ANALYSIS:
- Read requirements.txt / pyproject.toml (note package manager: pip/uv/poetry)
- Find the entry point (main.py, app.py, __main__.py, or similar)
- Identify the LLM framework in use. Match it to one of the supported SDK extras below.
- Check if arthur_observability_sdk already installed (skip STEP 2 if yes)

STEP 2 — IMPLEMENTATION:

PART A — SDK SETUP:

  Supported framework extras and their instrument methods — pick the one that matches:
    openai              → instrument_openai()
    langchain           → instrument_langchain()
    anthropic           → instrument_anthropic()
    crewai              → instrument_crewai()
    autogen             → instrument_autogen()
    autogen-agentchat   → instrument_autogen_agentchat()
    llama-index         → instrument_llama_index()
    bedrock             → instrument_bedrock()
    vertexai            → instrument_vertexai()
    google-genai        → instrument_google_genai()
    google-adk          → instrument_google_adk()
    mistralai           → instrument_mistralai()
    groq                → instrument_groq()
    litellm             → instrument_litellm()
    pydantic-ai         → instrument_pydantic_ai()
    openai-agents       → instrument_openai_agents()
    claude-agent-sdk    → instrument_claude_agent_sdk()
    haystack            → instrument_haystack()
    dspy                → instrument_dspy()
    smolagents          → instrument_smolagents()
    strands-agents      → instrument_strands_agents()
    mcp                 → instrument_mcp()
    (others: agno, agentspec, agent-framework, beeai, guardrails, instructor,
             monkai-agent, openlit, openllmetry, pipecat, portkey)

  If the framework is not in the list, fall back to the OpenInference instrumentation
  approach instead (see the OpenInference task prompt).

  Add "arthur-observability-sdk[<extra>]" to requirements.txt / pyproject.toml.
  Use "arthur-observability-sdk[all]" if unsure or if multiple frameworks are used.

  In the entry point, add Arthur initialization (after any existing imports):
    from arthur_observability_sdk import Arthur
    import os

    # Arthur raises ValueError if none of task_id / task_name / service_name is given.
    # NOTE: ARTHUR_TASK_ID env var is NOT read automatically — must be passed explicitly.
    # NOTE: ARTHUR_BASE_URL and ARTHUR_API_KEY ARE read automatically from env.
    arthur = Arthur(
        api_key=os.environ.get("ARTHUR_API_KEY"),        # auto-read, but explicit is cleaner
        base_url=os.environ.get("ARTHUR_BASE_URL", "<ARTHUR_ENGINE_URL>"),  # auto-read
        task_id=os.environ.get("ARTHUR_TASK_ID", "<ARTHUR_TASK_ID>"),       # NOT auto-read
        service_name="<app-name>",
        # resource_attributes: arthur.task is set automatically from task_id — don't add it
    )
    arthur.instrument_<framework>()   # call once; patches the framework's HTTP client

  At process exit / application teardown, flush pending spans:
    arthur.shutdown()

PART B — SESSION + USER CONTEXT (CRITICAL — without this each LLM call is a separate trace):

  The preferred way to tag spans with session and user is arthur.attributes(), which
  works as both a context manager and a decorator:

    import uuid
    session_id = <derive from app state, or str(uuid.uuid4())>

    # Context manager form (use around the full request handler body):
    with arthur.attributes(session_id=session_id, user_id=<user_id_or_None>):
        # all existing processing code here — LLM calls are recorded automatically

    # Decorator form:
    @arthur.attributes(session_id=session_id)
    def handle_request(message):
        ...

  Session-only: use arthur.session(session_id) as context manager or decorator.
  User-only:    use arthur.user(user_id)        as context manager or decorator.

  For streaming/generator handlers (yield), use explicit OTel attach/detach because
  Python context managers cannot straddle yield points.
  IMPORTANT: use otel_set_value to store session_id in the OTel context (not just as a
  span attribute) — otherwise child auto-instrumented spans won't inherit session.id:
    from opentelemetry import trace, context as otel_ctx
    from opentelemetry.trace import set_span_in_context
    from opentelemetry.context import set_value as otel_set_value
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues

    tracer = trace.get_tracer(__name__)

    def streaming_handler(message, session_id, ...):
        root_span = tracer.start_span("handler_name")
        root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                OpenInferenceSpanKindValues.CHAIN.value)
        root_span.set_attribute(SpanAttributes.INPUT_VALUE, message)
        # Build context with root span as parent AND session_id in OTel context
        # so that all child auto-instrumented spans inherit both correctly:
        ctx = otel_set_value(SpanAttributes.SESSION_ID, session_id,
                             context=set_span_in_context(root_span))
        token = otel_ctx.attach(ctx)
        try:
            for chunk in <inner_generator>:
                otel_ctx.detach(token)
                yield chunk
                token = otel_ctx.attach(ctx)
            root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <final_response>)
        finally:
            root_span.end()
            otel_ctx.detach(token)

  For non-streaming handlers that need a root CHAIN span (e.g., to group multiple LLM
  calls into one trace), add an explicit root span inside the arthur.attributes() block:
    from opentelemetry import trace
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
    import json

    tracer = trace.get_tracer(__name__)

    with arthur.attributes(session_id=session_id):
        with tracer.start_as_current_span("<handler_name>") as root_span:
            root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                    OpenInferenceSpanKindValues.CHAIN.value)
            root_span.set_attribute(SpanAttributes.INPUT_VALUE, <user_input>)
            # all existing processing code here
            root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <response>)

PART C — TOOL SPANS (if app uses LLM tool-calling):
    with tracer.start_as_current_span("<tool_name>") as tool_span:
        tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                OpenInferenceSpanKindValues.TOOL.value)
        tool_span.set_attribute(SpanAttributes.TOOL_NAME, "<tool_name>")
        tool_span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(<tool_input>))
        result = <execute_tool(tool_input)>
        tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE,
                                json.dumps(result) if not isinstance(result, str) else result)

PART D — RETRIEVER SPANS (if app does RAG/vector search):
    with tracer.start_as_current_span("retrieval") as ret_span:
        ret_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                               OpenInferenceSpanKindValues.RETRIEVER.value)
        ret_span.set_attribute(SpanAttributes.INPUT_VALUE, <search_query>)
        docs = <execute_retrieval(query)>
        retrieved = []
        for i, doc in enumerate(docs):
            doc_text = <doc_content>
            ret_span.set_attribute(f"retrieval.documents.{i}.document.content", doc_text)
            entry = {"document_content": doc_text}
            if <score_available>:
                score = float(<doc_score>)
                ret_span.set_attribute(f"retrieval.documents.{i}.document.score", score)
                entry["score"] = score
            retrieved.append(entry)
        # REQUIRED: set output.value so retrieved docs appear in Arthur Engine UI
        ret_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(retrieved))

STEP 3 — VALIDATION:
  Install: pip install 'arthur-observability-sdk[<extra>]' (or: uv sync)
  Check: python -c "from arthur_observability_sdk import Arthur; print('import OK')"
  Run existing test suite if present; fix any new failures you introduced.
  Print final JSON result on the last line.
```

---

### Mastra TypeScript instrumentation task prompt:

```
You are an expert TypeScript developer. Instrument the Mastra app at: <REPO_PATH>

Arthur Engine URL: <ARTHUR_ENGINE_URL>
Arthur Task ID: <ARTHUR_TASK_ID>

RULES: no hardcoded API keys; add env vars to .env and .env.example; smallest possible changes.
Print final JSON on the last line: {"success":true,"testsPassed":true,"summary":"<one sentence>"}

STEP 1 — Find the Mastra instance file (usually src/mastra/index.ts). Check if @mastra/arthur
already installed (skip if yes).

STEP 2 — Implementation:
  Install: npm install @mastra/arthur

  In the Mastra instance file:
    import { Mastra } from '@mastra/core'
    import { Observability } from '@mastra/observability'
    import { ArthurExporter } from '@mastra/arthur'

    export const mastra = new Mastra({
      observability: new Observability({
        configs: {
          arthur: {
            serviceName: '<app-name>',
            exporters: [new ArthurExporter()],
          },
        },
      }),
    })

  The ArthurExporter reads these env vars automatically (no constructor args needed):
    ARTHUR_API_KEY, ARTHUR_BASE_URL, ARTHUR_TASK_ID

  Add to .env (gitignored):
    ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
    ARTHUR_API_KEY=$ARTHUR_API_KEY
    ARTHUR_TASK_ID=<ARTHUR_TASK_ID>
  Add placeholders to .env.example.

STEP 3 — Validation:
  Run: npm install (or yarn/pnpm)
  Run: npx tsc --noEmit
  Run existing tests if present; fix new failures.
  Print final JSON result.
```

---

### OpenInference instrumentation task prompt (Python/TypeScript, other frameworks):

```
You are an expert developer. Instrument the agentic application at: <REPO_PATH>
using OpenInference / OpenTelemetry for Arthur GenAI Engine.

Reference: https://github.com/arthur-ai/arthur-engine/tree/dev/genai-engine/examples/agents

Arthur Engine URL: <ARTHUR_ENGINE_URL>
Arthur Task ID: <ARTHUR_TASK_ID>

RULES: no hardcoded keys; add env vars to .env and .env.example; smallest possible changes.
Print final JSON: {"success":true,"testsPassed":true,"summary":"<one sentence>"}

STEP 1 — Detect language (Python/TypeScript) and LLM framework.

STEP 2 — Python implementation:

PART A — OTel setup:
  Add to requirements.txt:
    opentelemetry-sdk
    opentelemetry-exporter-otlp-proto-http
    openinference-instrumentation-<framework>
    openinference-semantic-conventions

  In entry point:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from openinference.instrumentation.<framework> import <Framework>Instrumentor
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
    import os, json, uuid

    provider = TracerProvider()
    exporter = OTLPSpanExporter(
        endpoint="<ARTHUR_ENGINE_URL>/api/v1/traces",
        headers={"Authorization": f"Bearer {os.environ.get('ARTHUR_API_KEY', '')}"},
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    <Framework>Instrumentor().instrument()
    tracer = trace.get_tracer(__name__)

PART B — ROOT CHAIN SPAN + SESSION (CRITICAL — same reason as arthur-sdk approach):
  from openinference.instrumentation import using_session

  session_id = <from app state or str(uuid.uuid4())>
  with using_session(session_id=session_id):
      with tracer.start_as_current_span("<handler_name>") as root_span:
          root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                  OpenInferenceSpanKindValues.CHAIN.value)
          root_span.set_attribute(SpanAttributes.INPUT_VALUE, <input>)
          # all existing code here
          root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <output>)

PART C — TOOL SPANS: wrap each tool execution (same pattern as arthur-sdk above).
PART D — RETRIEVER SPANS: wrap each retrieval call (same pattern as arthur-sdk above).

STEP 2 (TypeScript) — Follow OTel OTLP exporter pattern pointing to
<ARTHUR_ENGINE_URL>/api/v1/traces with Authorization: Bearer $ARTHUR_API_KEY header.
Add root span around the request handler.

STEP 3 — Install deps, run import check, run tests, print JSON result.
```

---

After the instrumentation sub-agent completes:
- Show the user a summary of changes
- If `"success": false`: warn the user to review changes manually
- If tests failed: note it may be pre-existing failures unrelated to the instrumentation

---

## Step 6/10 — Extract & Register Prompts

Delegate to a Task sub-agent (full claude agent) to find prompts in the repo:

```
Analyze the agentic application at: <REPO_PATH>

Use Read, Glob (find), and Grep to find all prompt definitions:
- System prompt strings assigned to variables (any language)
- User prompt templates with variables
- Multi-turn message arrays in OpenAI format ([{"role": "system", ...}])
- Prompt files (.txt, .md, .jinja2)
- Agent instruction strings passed to agent/chain initialization

Also detect the LLM model and provider used (from API call patterns, imports, env var names
like OPENAI_API_KEY, model= parameters, etc.).

Return ONLY a raw JSON object with no markdown, no explanation:
{
  "prompts": [
    {
      "name": "kebab-case-unique-name",
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
      ],
      "model_name": "gpt-4o" | null,
      "model_provider": "openai" | "anthropic" | "gemini" | "bedrock" | "vertex_ai" | null
    }
  ],
  "detected_model_name": "<model>" | null,
  "detected_model_provider": "<provider>" | null
}

Rules:
- Only include prompts with substantive content (skip empty strings and test fixtures)
- Convert template variables to {{double_brace}} format regardless of source syntax
- Names: unique, lowercase, kebab-case, descriptive
- If nothing found: {"prompts": [], "detected_model_name": null, "detected_model_provider": null}
```

After extraction:
- **No prompts found:** tell the user, proceed to Step 7
- **Prompts found:** show the list and ask for confirmation

For each confirmed prompt, register via:
```bash
curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PROMPT_JSON" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/prompts/$PROMPT_NAME"
```

Where `$PROMPT_JSON` = `{"messages": [...], "model_name": "...", "model_provider": "..."}`.

This step is non-blocking — log a warning and continue if it errors.

---

## Step 7/10 — Verify Instrumentation

Tell the user to run their application. Show the required env vars for their platform:

```
# Mac / Linux:
  export ARTHUR_API_KEY=<ARTHUR_API_KEY>
  export ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
  export ARTHUR_TASK_ID=<ARTHUR_TASK_ID>

# Windows PowerShell:
  $env:ARTHUR_API_KEY  = "<ARTHUR_API_KEY>"
  $env:ARTHUR_BASE_URL = "<ARTHUR_ENGINE_URL>"
  $env:ARTHUR_TASK_ID  = "<ARTHUR_TASK_ID>"

# Windows CMD:
  set ARTHUR_API_KEY=<ARTHUR_API_KEY>
  set ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
  set ARTHUR_TASK_ID=<ARTHUR_TASK_ID>
```

Once the user confirms they've run the app, poll for traces (up to 60 seconds):
```bash
for i in $(seq 1 20); do
  COUNT=$(curl -s \
    -H "Authorization: Bearer $ARTHUR_API_KEY" \
    "$ARTHUR_ENGINE_URL/api/v1/traces?task_ids=$ARTHUR_TASK_ID&page_size=5" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('traces') or d.get('data') or []))
" 2>/dev/null || echo "0")
  if [ "$COUNT" -gt "0" ]; then
    echo "TRACES_FOUND=$COUNT"; break
  fi
  echo "No traces yet... attempt $i/20"
  sleep 3
done
```

**Traces found:** Confirm success and move on.

**No traces after 60s:** Provide troubleshooting guidance:
1. Check env vars are set correctly in the app
2. Confirm the app made actual LLM calls during the test run
3. Verify Arthur Engine is running: `curl $ARTHUR_ENGINE_URL/health`
4. Check the app logs for errors related to OpenTelemetry or Arthur SDK

Offer to retry. This step is non-blocking.

---

## Step 8/10 — Configure Eval Model Provider

List configured providers:
```bash
curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/model_providers" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('providers', []):
    print(f'{p[\"provider\"]}: enabled={p[\"enabled\"]}')
"
```

**If an enabled provider exists:** Use it (prefer OpenAI > Anthropic > Gemini > Bedrock > Vertex AI). Note the selection.

**If none enabled:** Ask user to choose a provider:
- `openai` → model `gpt-4o`
- `anthropic` → model `claude-3-5-haiku-20241022`
- `gemini` → model `gemini-1.5-flash`
- `bedrock` → model `anthropic.claude-3-haiku-20240307-v1:0`
- `vertex_ai` → model `gemini-1.5-flash`
- Skip → configure in the Arthur Engine UI later

If a provider is chosen, show the user this message and wait for their confirmation (do **not** ask them to type the key in chat; do **not** run getpass via the Bash tool — it has no TTY):
> Please run this to securely enter your `<Provider>` API key (replace `<Provider>` with the actual provider name in the prompt):
>
> `! python3 -c "import getpass, os, stat; p=os.path.expanduser('~/.ae_tmp_key'); key=getpass.getpass('<Provider> API key (hidden): '); open(p,'w').write(key); os.chmod(p, 0o600); print('Key saved.')"`
>
> Let me know when done.

Then read the key from the temp file and configure:
```bash
PROVIDER_API_KEY=$(cat ~/.ae_tmp_key && rm -f ~/.ae_tmp_key)
curl -s -X PUT \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\": \"$PROVIDER_API_KEY\"}" \
  "$ARTHUR_ENGINE_URL/api/v1/model_providers/$PROVIDER"
```

---

## Step 9/10 — Recommend & Configure Continuous Evals

**Skip if:** No eval model provider was configured in Step 8.

### Check existing evals:
```bash
curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/continuous_evals?page=0&page_size=100" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
evals = d.get('evals', [])
for e in evals:
    print(f'  • {e[\"name\"]}')
print(f'COUNT={len(evals)}')
"
```

If evals already exist, show them and ask if the user wants additional recommendations.

### Fetch a trace for analysis:
```bash
TRACE_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/traces?task_ids=$ARTHUR_TASK_ID&page_size=5")

TRACE_ID=$(echo "$TRACE_RESPONSE" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
traces = d.get('traces') or d.get('data') or []
print(traces[0]['trace_id'] if traces else '')
" 2>/dev/null)

if [ -n "$TRACE_ID" ]; then
  curl -s \
    -H "Authorization: Bearer $ARTHUR_API_KEY" \
    "$ARTHUR_ENGINE_URL/api/v1/traces/$TRACE_ID"
fi
```

### Recommend evals (Claude native reasoning):

Using the trace input/output content, recommend 2-4 continuous evals. Choose based on what the trace reveals about the application:

| Application type | Good eval choices |
|-----------------|-------------------|
| Customer support | Relevance, tone, task completion |
| RAG / Q&A | Faithfulness (only if retrieval spans found), relevance |
| Code assistant | Correctness, clarity |
| General chat | Relevance, toxicity |
| Agentic workflows | Task completion, relevance |

**Important:** Only recommend a faithfulness/hallucination eval if the trace contains retrieval spans (span_kind=RETRIEVER or span name matches retrieve/search/document/rag).

For each recommendation, write specific Jinja2-format instructions:
```
Evaluate the following LLM interaction for <quality dimension>:

Input: {{ input }}
Output: {{ output }}

<scoring criteria specific to the dimension>

Return a JSON object: {"score": <0.0-1.0 where 1.0 = fully passes>, "reason": "<brief explanation>"}
```

Show the recommendations with rationale and ask for user approval.

### Create evals (if approved):

For each recommended eval, create the LLM eval rule:
```bash
curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model_name\": \"$EVAL_MODEL\", \"model_provider\": \"$EVAL_PROVIDER\", \"instructions\": \"$INSTRUCTIONS\"}" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/llm_evals/$SLUG"
```

After all LLM evals are created, create one shared transform:
```bash
TRANSFORM_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Arthur — Input/Output Extractor\",
    \"definition\": {
      \"variables\": [
        {\"variable_name\": \"input\", \"span_name\": \"$ROOT_SPAN_NAME\", \"attribute_path\": \"attributes.input.value\", \"fallback\": \"\"},
        {\"variable_name\": \"output\", \"span_name\": \"$ROOT_SPAN_NAME\", \"attribute_path\": \"attributes.output.value\", \"fallback\": \"\"}
      ]
    }
  }" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/traces/transforms")

TRANSFORM_ID=$(echo "$TRANSFORM_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
```

Then create a continuous eval for each LLM eval:
```bash
curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$DISPLAY_NAME\",
    \"llm_eval_name\": \"$SLUG\",
    \"llm_eval_version\": \"latest\",
    \"transform_id\": \"$TRANSFORM_ID\",
    \"transform_variable_mapping\": [
      {\"transform_variable\": \"input\", \"eval_variable\": \"input\"},
      {\"transform_variable\": \"output\", \"eval_variable\": \"output\"}
    ],
    \"enabled\": true
  }" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/continuous_evals"
```

This step is non-blocking — log a warning and continue if it errors.

---

## Step 10/10 — Done

Provide a completion summary:

```
Onboarding complete!

  Arthur Engine:     <ARTHUR_ENGINE_URL>
  Task:              <task_name> (<ARTHUR_TASK_ID>)
  Continuous evals:  <N> monitoring your application

Next: Run your application with the Arthur env vars set to start seeing traces and eval scores.
```

Note any steps that were skipped or require manual follow-up (e.g., model provider configuration, prompt registration, trace verification).

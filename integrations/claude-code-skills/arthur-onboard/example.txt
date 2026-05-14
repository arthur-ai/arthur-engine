# Example — agents-from-scratch

This file is a companion to the `/arthur-onboard` skill, which wires Arthur GenAI Engine
to your agentic app in a 10-step workflow. This walkthrough uses LangChain's
**agents-from-scratch** repo as the sample app — specifically what to set up and what to run
when the skill reaches **Step 7 (trace verification)**.

---

## 1. Clone and enter the repo

```bash
git clone https://github.com/langchain-ai/agents-from-scratch
cd agents-from-scratch
```

## 2. Set up the app

```bash
pip install uv
uv sync --extra dev
source .venv/bin/activate
cp .env.example .env
```

Edit `.env` — set the top vars yourself; the Arthur vars are filled in by `/arthur-onboard`:

```
# Set this yourself:
OPENAI_API_KEY=<your valid OpenAI API key>
LANGSMITH_TRACING=false

# Set automatically by `/arthur-onboard` (Steps 2–3):
ARTHUR_API_KEY=<set by `/arthur-onboard`>
ARTHUR_BASE_URL=<set by `/arthur-onboard`>
ARTHUR_TASK_ID=<set by `/arthur-onboard`>
```

---

## 3. Run the agent for trace verification

When `/arthur-onboard` reaches **Step 7**, run this from the **root** of `agents-from-scratch`
(where `pyproject.toml` / `uv` expects to run):

```bash
uv run python -c "
from src.email_assistant.email_assistant import email_assistant
from src.email_assistant.eval.email_dataset import email_inputs, email_names

for name, email in zip(email_names, email_inputs):
    result = email_assistant.invoke({'email_input': email})
    print(f'{name}: {result[\"classification_decision\"]}')
"
```

This runs 5 sample emails through the LangChain email-assistant agent. Each invocation
makes one or more LLM calls, which the Arthur SDK captures as traces and forwards to
your Arthur Engine instance.

**Expected output** (exact decisions may vary by model):

```
email_1: respond
email_2: ignore
email_3: respond
email_4: notify
email_5: ignore
```

If you see five lines like the above, the agent ran successfully. Errors or a blank
classification field usually indicate a missing `OPENAI_API_KEY` or an env issue.

---

## 4. Verify traces arrived in Arthur

After the run completes, confirm traces landed in Arthur Engine before returning to
the `/arthur-onboard` skill.

**Option A — Arthur Engine UI**

Open `$ARTHUR_BASE_URL` in a browser (e.g., `http://localhost:3030`), navigate to your
Task, and check the **Traces** tab. You should see 5 new traces, one per email.

**Option B — API**

```bash
curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_BASE_URL/api/v1/traces?task_ids=$ARTHUR_TASK_ID&page_size=5" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
traces = d.get('traces') or d.get('data') or []
print(f'{len(traces)} trace(s) found')
"
```

A result of `5 trace(s) found` confirms successful delivery. Return to `/arthur-onboard` —
it will poll for traces automatically and advance once they appear.

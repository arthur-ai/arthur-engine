---
name: arthur-insights-evals
description: Arthur Insights sub-skill — Step 4: Run the onboarding-generated LLM evals over the simulated fake traces and collect scores. Writes .arthur/insights/eval_results.json.
allowed-tools: Bash, Read, Write
version: 1.0.0
---

# Arthur Insights — Step 4: Run Evals over Fake Traces

**Goal:** Score every simulated trace with every LLM eval the onboarding skill created, using
the engine's eval completions API. The score matrix is the core quantitative evidence for the
final insights.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`. Load
`.arthur/insights/scenarios.json` — if missing, run `arthur-insights-simulate` first.

---

## List the Task's LLM Evals

```bash
source .arthur-engine.env
curl -s -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/llm_evals" \
  > /tmp/arthur-llm-evals.json
python3 -c "
import json
d = json.load(open('/tmp/arthur-llm-evals.json'))
evals = d.get('evals') or d.get('llm_evals') or d.get('data') or []
for e in evals: print(e.get('name'))
"
```

**No evals:** offer to run the `arthur-onboard-evals` skill now, or skip this step. If
skipped, write `{"skipped": true, "reason": "no evals configured"}` to
`.arthur/insights/eval_results.json` and exit — Step 5 will work from qualitative evidence
only and flag the missing eval coverage.

For each eval, fetch its latest version to read its instructions and discover its template
variables (Jinja2 `{{ variable }}` references):

```bash
source .arthur-engine.env
curl -s -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/llm_evals/$EVAL_NAME/versions/latest"
```

Extract the variable names from the instructions (e.g. `input`, `output`, `context`).

---

## Confirm Cost, Then Run the Matrix

Each run is one LLM call. With E evals and S scenarios that's E×S calls. Tell the user the
count and the eval model (`ARTHUR_EVAL_MODEL`) and **ask for confirmation before running**.

For each scenario × eval, map variables from the scenario:

| Eval variable | Scenario field |
|---|---|
| `input` | `user_input` |
| `output` | `final_output` |
| `context` / `documents` | retrieved documents from the trace plan, joined as text |

If a scenario can't supply a required variable (e.g. a faithfulness eval's `context` for a
scenario with no retrieval), skip that cell and record `"skipped: missing <variable>"`.

```bash
source .arthur-engine.env
curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"variables\": [
        {\"name\": \"input\",  \"value\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$SCENARIO_INPUT")},
        {\"name\": \"output\", \"value\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$SCENARIO_OUTPUT")}
      ]}" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/llm_evals/$EVAL_NAME/versions/latest/completions"
```

The response is `{"score": <int>, "reason": "<explanation>", "cost": "<usd>"}`.

Prefer batching this loop in a single python3 script over many individual curl calls — read
`scenarios.json` and `/tmp/arthur-llm-evals.json`, iterate, and tolerate per-cell failures
(record `"error": "<detail>"` and continue; this step is non-blocking).

---

## Save and Summarize

Write `.arthur/insights/eval_results.json`:

```json
{
  "session_id": "simulated-<ts>",
  "eval_model": "<ARTHUR_EVAL_MODEL>",
  "results": [
    {"scenario_id": "...", "trace_id": "...", "eval_name": "...",
     "score": 0, "reason": "...", "cost": "...", "expected_quality": "good|flawed: ..."}
  ]
}
```

Show the user a scenario × eval score matrix, flagging:
- **Low scores on scenarios expected to be "good"** → possible real weakness in the app's prompts/logic, or a miscalibrated eval
- **High scores on scenarios expected to be "flawed"** → the eval failed to catch a planted flaw → eval coverage gap
- **Skipped cells** → variable/coverage mismatches between evals and the app's trace shapes

These calibration observations are first-class input to Step 5.

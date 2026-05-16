---
name: arthur-onboard-evals
description: Arthur onboarding sub-skill — Step 9: Recommend and configure continuous LLM evals for the Arthur task. Reads credentials and eval provider from .arthur-engine.env.
allowed-tools: Bash, Read
---

# Arthur Onboard — Step 9: Recommend & Configure Continuous Evals

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`, `ARTHUR_EVAL_PROVIDER`, `ARTHUR_EVAL_MODEL`.

**Skip if** `ARTHUR_EVAL_PROVIDER` is empty or `none` — no eval model was configured in Step 8. Exit this skill.

---

## Check Existing Evals

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

---

## Fetch a Trace for Analysis

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

---

## Recommend Evals

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

---

## Create Evals (If Approved)

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

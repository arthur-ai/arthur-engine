---
name: arthur-insights-scan
description: Arthur Insights sub-skill — Step 2: Scan an agentic application's code as a black box, extracting prompts, tools, business logic, and model configuration. Writes .arthur/insights/scan.json.
allowed-tools: Bash, Read, Write, Task
version: 1.0.0
---

# Arthur Insights — Step 2: Black-Box Scan

**Goal:** Build a complete picture of the agent's externally observable behavior — what goes
in, what comes out, and what it can do in between — without judging implementation quality.
This scan drives trace simulation (Step 3) and the final insights (Step 5).

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
mkdir -p .arthur/insights
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`.

---

## Fetch Registered Prompts from Arthur

The onboarding skill migrated the app's prompts into Arthur's prompt-management service.
Fetch them so the scan can cross-reference code against what is registered:

```bash
source .arthur-engine.env
curl -s -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/prompts" \
  > .arthur/insights/registered_prompts.json
python3 -c "
import json
d = json.load(open('.arthur/insights/registered_prompts.json'))
prompts = d.get('prompts') or d.get('data') or []
print(f'{len(prompts)} registered prompt(s):', ', '.join(p.get('name','?') for p in prompts))
"
```

---

## Scan the Code via Sub-agent

Delegate to a Task sub-agent (full claude agent). Replace `<REPO_PATH>` with the target repo.

```
Analyze the agentic application at: <REPO_PATH>

Treat the agent as a BLACK BOX whose interface you are documenting: inputs, outputs, prompts,
tools, and the business logic that connects them. Use Read, Glob (find), and Grep. Ignore
generated code, lockfiles, vendored dependencies, and test fixtures. Do NOT review code
quality — document behavior.

Extract:

1. PROMPTS — every system prompt, user prompt template, and agent instruction string.
   Convert template variables to {{double_brace}} format. Record the file and line where
   each is defined.

2. TOOLS — every tool/function the LLM can call (native tool-calling, MCP servers, LangChain
   tools, Mastra tools, manual dispatch). For each: name, description shown to the LLM,
   parameter schema, what it actually does (side effects: reads data / writes data / calls
   external API), and how errors from it are handled (retried, surfaced to LLM, swallowed,
   crashes).

3. BUSINESS LOGIC — the orchestration around the LLM:
   - Entry points (HTTP handler, CLI, queue consumer) and the shape of user input
   - Control flow: single-shot, agent loop (max iterations?), multi-agent, RAG pipeline
   - Retrieval details if RAG: source, top-k, filtering, how docs are injected into prompts
   - Guardrails/validation on input or output, fallback behavior, retry logic
   - Conversation memory/history handling
   - Anything hardcoded that shapes behavior (truncation limits, temperature, stop conditions)

4. MODELS — every model used, its provider, and invocation parameters.

5. RISK SURFACE — behaviors a simulation should exercise: ambiguous inputs the routing
   could mis-handle, tools whose failure is unhandled, prompts with no constraint against
   off-topic/adversarial use, unbounded loops, missing citations in RAG answers, etc.
   These are observations for test design, not judgments.

Return ONLY a raw JSON object, no markdown, no explanation:
{
  "app_name": "<short name>",
  "entry_points": [{"name": "...", "kind": "http|cli|queue|other", "input_shape": "...", "file": "path:line"}],
  "prompts": [{"name": "kebab-case", "role_messages": [{"role": "system", "content": "..."}],
               "variables": ["..."], "file": "path:line"}],
  "tools": [{"name": "...", "description": "...", "parameters": {...}, "side_effects": "...",
             "error_handling": "...", "file": "path:line"}],
  "business_logic": {"control_flow": "...", "retrieval": "...|null", "guardrails": "...",
                     "memory": "...", "notable_constants": ["..."]},
  "models": [{"model_name": "...", "provider": "...", "parameters": {...}}],
  "risk_surface": [{"area": "prompt|tool|flow|retrieval|safety", "observation": "...", "file": "path:line"}],
  "files_scanned": <int>
}
```

---

## Save and Summarize

Write the sub-agent's JSON to `.arthur/insights/scan.json`.

Compare extracted prompts against `registered_prompts.json` — note any prompt found in code
but not registered with Arthur (or vice versa, suggesting code drift since onboarding). Record
mismatches in the scan JSON under a `"prompt_registry_drift"` key.

Report a short summary to the user before exiting:

```
Scan complete:
  Prompts:        <N> in code, <M> registered with Arthur (<drift note>)
  Tools:          <K> (<names>)
  Control flow:   <one line>
  Risk surface:   <R> observations to exercise in simulation
  Saved to:       .arthur/insights/scan.json
```

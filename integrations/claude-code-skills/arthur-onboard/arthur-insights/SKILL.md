---
name: arthur-insights
description: Generate improvement insights for an agentic application already onboarded to Arthur. Scans the agent's code as a black box, simulates realistic fake traces, runs the onboarding-generated evals over them, and produces 5 evidence-backed improvement insights. Run after /arthur-onboard-oss or /arthur-onboard-platform.
allowed-tools: Bash, Read, Write, Task, Skill
version: 1.0.0
---

# Arthur Insights — Simulate, Evaluate, Improve

You are guiding the user through the Arthur Insights workflow. It runs **after** onboarding
(`/arthur-onboard-oss` or `/arthur-onboard-platform`) and assumes onboarding already:

1. Instrumented the application with OTEL/Arthur tracing
2. Built an example eval set (LLM evals + continuous evals on the task)
3. Migrated the application's prompts into Arthur's prompt-management service

**What this skill does (5-step workflow):**

| Step | Sub-skill | Purpose |
|---|---|---|
| 1 | (this skill) | Pre-flight: verify onboarding state, prepare workspace |
| 2 | `arthur-insights-scan` | Scan the agent's code as a black box (prompts, tools, business logic) |
| 3 | `arthur-insights-simulate` | Generate realistic fake traces and send them to Arthur Engine |
| 4 | `arthur-insights-evals` | Run the onboarding-generated evals over the fake traces |
| 5 | `arthur-insights-report` | Synthesize 5 improvement insights from all the evidence |

**Target repository:** The current working directory, unless the user specifies a different path.

Be conversational — explain what each step will do, and ask before sending data to the engine
or making LLM eval calls (they cost money).

---

## Step 0 — Check for skill updates

Invoke the `arthur-skills-upgrade` skill (it covers `arthur-insights-*` skills too). If it is
not installed, skip this step silently. Report any version transitions the same way the
onboarding orchestrator does.

---

## Step 1/5 — Pre-flight

### Read onboarding state

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`, `ARTHUR_EVAL_PROVIDER`, `ARTHUR_EVAL_MODEL`.

**If `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, or `ARTHUR_TASK_ID` is missing:** this repo has not
been onboarded. Tell the user to run `/arthur-onboard-oss` (or `/arthur-onboard-platform`)
first, then exit this skill.

### Verify the engine is reachable and onboarding artifacts exist

```bash
source .arthur-engine.env

curl -s "$ARTHUR_ENGINE_URL/health" | head -c 200; echo ""

echo "--- Registered prompts ---"
curl -s -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/prompts" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
prompts = d.get('prompts') or d.get('data') or []
for p in prompts: print(f'  • {p.get(\"name\")}')
print(f'PROMPT_COUNT={len(prompts)}')
" 2>/dev/null || echo "PROMPT_COUNT=0"

echo "--- LLM evals ---"
curl -s -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/llm_evals" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
evals = d.get('evals') or d.get('llm_evals') or d.get('data') or []
for e in evals: print(f'  • {e.get(\"name\")}')
print(f'EVAL_COUNT={len(evals)}')
" 2>/dev/null || echo "EVAL_COUNT=0"
```

- **Engine unreachable** → troubleshoot with the user (is Docker running? correct URL?), do not continue until reachable.
- **`EVAL_COUNT=0`** → warn the user: Step 4 needs evals from onboarding. Offer to run the
  `arthur-onboard-evals` skill now (it requires `ARTHUR_EVAL_PROVIDER` to be set; if that is
  also missing, `arthur-onboard-eval-provider` first). If the user declines, continue — Step 4
  will be skipped and Step 5 will note the gap.
- **`PROMPT_COUNT=0`** → note it; the scan step will still extract prompts from code.

### Prepare the workspace

All artifacts from this run are written under `.arthur/insights/` so the user can inspect them
and so each step can read the previous step's output:

```bash
mkdir -p .arthur/insights
grep -qxF '.arthur/' .gitignore 2>/dev/null || echo '.arthur/' >> .gitignore
```

| Artifact | Written by | Contents |
|---|---|---|
| `.arthur/insights/scan.json` | Step 2 | Black-box scan: prompts, tools, business logic, models |
| `.arthur/insights/scenarios.json` | Step 3 | Simulated scenarios + the trace IDs sent to Arthur |
| `.arthur/insights/eval_results.json` | Step 4 | Eval scores and reasons per scenario × eval |
| `.arthur/insights/INSIGHTS.md` | Step 5 | The final 5 improvement insights |

---

## Steps 2–5: Modular Sub-skills

Invoke in order using the Skill tool. Each sub-skill reads `.arthur-engine.env` for credentials
and reads/writes the artifacts above, so state flows automatically between steps.

1. **Step 2** — `arthur-insights-scan`
   Treats the agent as a black box and extracts its interface: prompts, tools, business logic,
   model configuration. Writes `.arthur/insights/scan.json`.

2. **Step 3** — `arthur-insights-simulate`
   Designs realistic scenarios from the scan, generates fake OpenInference traces, and sends
   them to Arthur Engine via OTLP. Writes `.arthur/insights/scenarios.json`.

3. **Step 4** — `arthur-insights-evals`
   Runs each onboarding-generated LLM eval over each fake trace via the engine's eval
   completions API. Writes `.arthur/insights/eval_results.json`. Skipped if no evals exist.

4. **Step 5** — `arthur-insights-report`
   Synthesizes exactly 5 improvement insights from (1) the static code scan, (2) the registered
   prompts + evals, (3) the fake traces, and (4) the eval results. Writes
   `.arthur/insights/INSIGHTS.md` and presents it.

> **Sub-skill not found?** Ask the user to install all `arthur-insights-*` skills alongside
> this one (see README.md in the arthur-onboard skills directory).

---

## Done

After all sub-skills complete, summarize:

```
Arthur Insights complete!

  Scanned:          <N> prompts, <M> tools, <K> source files
  Simulated:        <S> fake traces sent to task <ARTHUR_TASK_ID>
  Evals run:        <E> evals × <S> traces (<P> passed, <F> flagged)
  Insights:         .arthur/insights/INSIGHTS.md

View the simulated traces and eval scores in the Arthur UI, filtered by
session ID prefix "simulated-".
```

Offer follow-ups: apply one of the recommended fixes, register an improved prompt version with
Arthur, or add evals that cover the gaps found in Step 5.

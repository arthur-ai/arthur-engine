---
name: arthur-insights-report
description: Arthur Insights sub-skill — Step 5: Synthesize exactly 5 evidence-backed improvement insights from the code scan, prompts + evals, simulated traces, and eval results. Writes .arthur/insights/INSIGHTS.md.
allowed-tools: Bash, Read, Write
version: 1.0.0
---

# Arthur Insights — Step 5: Generate Improvement Insights

**Goal:** Produce exactly **5 insights** that capture improvements the user could make to
their agent. Every insight must be grounded in the evidence gathered by the previous steps —
no generic LLM-app advice.

## Load All Evidence

```bash
cat .arthur-engine.env 2>/dev/null
ls -la .arthur/insights/
```

Read all four evidence sources in full:

1. **Static code scan** — `.arthur/insights/scan.json` (prompts, tools, business logic, risk surface, prompt-registry drift)
2. **Prompts + evals** — `.arthur/insights/registered_prompts.json` and the task's LLM evals (`/tmp/arthur-llm-evals.json`, or re-fetch from `$ARTHUR_ENGINE_URL/api/v1/tasks/$ARTHUR_TASK_ID/llm_evals`)
3. **Fake traces** — `.arthur/insights/scenarios.json` (scenarios, trace plans, trace IDs)
4. **Eval results** — `.arthur/insights/eval_results.json` (score matrix, reasons, calibration flags)

If a source is missing (e.g. evals were skipped), proceed with what exists and let the gap
itself inform an insight.

---

## Synthesize 5 Insights

Rules:

- **Exactly 5.** Pick the 5 highest-impact findings; fold lesser observations into related insights or drop them.
- **Cross-reference sources.** The strongest insights connect evidence: a `risk_surface`
  observation from the scan that a simulated scenario then triggered and an eval then scored
  low is one insight, not three.
- **Cite evidence.** Each insight names its sources concretely: `file:line` from the scan,
  scenario IDs/trace IDs, eval names + scores + the judge's reason.
- **Be diverse.** Cover at least three of these categories across the 5: prompt design, tool
  design/error handling, orchestration/business logic, retrieval quality, eval & monitoring
  coverage, safety/adversarial robustness. At least one insight should draw on the eval score
  matrix (or on its absence, if evals were skipped) and at least one on the static scan.
- **Recommend, concretely.** Each recommendation states the specific change — e.g. the exact
  sentence to add to a system prompt, the tool whose errors need a fallback branch, the eval
  to add with suggested instructions. Where it's a prompt change, offer to register the
  improved version with Arthur's prompt service so it's versioned.
- **Don't overclaim.** The traces are simulated; phrase eval-based findings as "in simulation"
  and recommend verifying against real production traces where it matters.

Common patterns to look for (use only those the evidence supports):

| Pattern | Typical evidence trail |
|---|---|
| System prompt lacks constraints | adversarial/off-topic scenario produced compliant-but-wrong output; no guardrail in scan |
| Unhandled tool failure | scan `error_handling: swallowed/crashes` + tool-failure scenario's trace |
| Ambiguous routing | ambiguous scenario picked a defensible-but-wrong tool; tool descriptions overlap in scan |
| Unfaithful RAG answers | flawed scenario scored low on faithfulness; or no faithfulness eval despite retrieval |
| Eval blind spot | a planted flaw that every eval scored highly; or scenario shapes evals can't ingest |
| Prompt registry drift | code prompts ≠ registered prompts from the scan's drift check |
| Missing observability | scan found branches/tools that produce no spans, so production traces can't show them |

---

## Write the Report

Write `.arthur/insights/INSIGHTS.md`:

```markdown
# Arthur Insights — <app_name>
_Generated <date> · task <ARTHUR_TASK_ID> · <S> simulated traces · <E> evals_

## Summary
<2–3 sentences: overall health and the dominant theme of the findings>

## Insight 1 — <imperative title, e.g. "Add an out-of-scope refusal to the system prompt">
**Category:** <category> · **Severity:** high|medium|low · **Effort:** small|medium|large

**Evidence**
- <code citation `file:line` — what the scan found>
- <scenario `<id>` (trace `<trace_id>`) — what the simulation showed>
- <eval `<name>` scored <score>: "<judge reason excerpt>">

**Why it matters**
<1–2 sentences on user-facing or operational impact>

**Recommendation**
<the concrete change, with the suggested prompt text / code sketch / eval instructions>

## Insight 2 — ...
...

## Insight 5 — ...

---
_All traces in this run are tagged `simulated` (session `<session_id>`). Findings based on
simulated traffic — validate high-severity items against production traces._
```

---

## Present and Offer Next Steps

Show the 5 insight titles with severity/effort in chat, point the user at
`.arthur/insights/INSIGHTS.md` for the full report, and offer to:

1. Apply one of the recommended code/prompt changes now
2. Register an improved prompt version with Arthur's prompt-management service
3. Create the recommended additional evals (via the `arthur-onboard-evals` skill or directly)
4. Re-run `arthur-insights-simulate` + `arthur-insights-evals` after changes to compare scores

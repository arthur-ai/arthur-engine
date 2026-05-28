---
name: arthur-onboard-oss
description: Onboard an agentic application to Arthur GenAI Engine. Guides through engine connection, task setup, code instrumentation, trace verification, and eval configuration. Invoke from any agentic application repository.
allowed-tools: Bash, Read, Write, Edit, Task, Skill
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

## Steps 2–9: Modular Sub-skills

Each remaining step is handled by a dedicated sub-skill. Invoke them in sequence using the Skill tool. Each sub-skill reads its inputs from `.arthur-engine.env` and writes its outputs back to the same file, so state flows automatically between steps.

**Invoke in order:**

1. **Step 2** — `arthur-onboard-oss-engine`
   Ensures Arthur GenAI Engine is available (local Docker install or remote connection).
   Establishes `ARTHUR_ENGINE_URL` and `ARTHUR_API_KEY` in the state file.

2. **Step 3** — `arthur-onboard-task`
   Creates or selects an Arthur Task.
   Establishes `ARTHUR_TASK_ID` in the state file.

3. **Step 4** — `arthur-onboard-analyze`
   Analyzes the target repository for language, framework, and existing instrumentation.
   Writes `ARTHUR_DETECTED_LANGUAGE`, `ARTHUR_DETECTED_FRAMEWORK`, `ARTHUR_IS_INSTRUMENTED` to state.

4. **Step 5** — `arthur-onboard-instrument`
   Instruments the application code (Python SDK, Mastra TS, or OpenInference).
   Reads detection results from the state file.

5. **Step 6** — `arthur-onboard-prompts`
   Extracts prompt definitions from the repo and registers them with Arthur Engine.

6. **Step 7** — `arthur-onboard-verify`
   Asks the user to run the app, then polls for traces to confirm instrumentation is working.

7. **Step 8** — `arthur-onboard-eval-provider`
   Configures an LLM model provider for continuous evals.
   Writes `ARTHUR_EVAL_PROVIDER` and `ARTHUR_EVAL_MODEL` to state.

8. **Step 9** — `arthur-onboard-evals`
   Recommends and creates continuous LLM evals for the task.

> **Sub-skill not found?** If a sub-skill isn't installed, its step instructions appear in the
> system's available-skills list. If missing, ask the user to install all `arthur-onboard-*`
> skills alongside this one (see README.md).

---

## Step 10/10 — Done

After all sub-skills complete, read the final state:
```bash
cat .arthur-engine.env 2>/dev/null
```

Provide a completion summary:

```
Onboarding complete!

  Arthur Engine:     <ARTHUR_ENGINE_URL>
  Task:              <task_name> (<ARTHUR_TASK_ID>)
  Continuous evals:  <N> monitoring your application

Next: Run your application with the Arthur env vars set to start seeing traces and eval scores.
```

Note any steps that were skipped or require manual follow-up (e.g., model provider configuration, prompt registration, trace verification).

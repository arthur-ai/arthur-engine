---
name: arthur-onboard-platform
description: Onboard an agentic application to the Arthur SaaS Platform (platform.arthur.ai). Guides through authentication, workspace selection, engine deployment, model creation, code instrumentation, trace verification, and eval configuration.
allowed-tools: Bash, Read, Write, Edit, Task, Skill
version: 1.0.0
---

# Onboard to Arthur Platform

You are guiding the user through the complete Arthur Platform onboarding workflow. Work through each step in order. Be conversational — ask the user before making changes to their code or configuration.

**Target repository:** The current working directory, unless the user specifies a different path.

---

## Step 0 — Check for skill updates

Invoke the `arthur-skills-upgrade` skill. It will check all installed `arthur-onboard-*` and `arthur-skills-upgrade` skills against GitHub main and prompt the user only if stale ones are found. If the skill is not installed, skip this step silently.

---

## State File

Persist all state to `.arthur-engine.env` in the root of the target repository. This file is per-project and should be gitignored.

**Before starting:** Read the state file:
```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse existing values for `ARTHUR_PLATFORM_URL`, `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`.

If `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, and `ARTHUR_TASK_ID` all exist, display them and ask:
> "Found existing Arthur Platform configuration. Continue with these settings, or start fresh?"

**Writing state:** Use this pattern to update individual values without clobbering others:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_URL=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo 'ARTHUR_PLATFORM_URL=https://platform.arthur.ai' >> "$STATE_FILE"
```

Also ensure the file is gitignored:
```bash
grep -qxF '.arthur-engine.env' .gitignore 2>/dev/null || echo '.arthur-engine.env' >> .gitignore
```

---

## Step 1/13 — Pre-flight Checks + Identify Platform

Check git status in the target repo:
```bash
git status --porcelain
```
- Unstaged/untracked changes → warn the user (do NOT block — staged changes are fine)
- Not a git repo → note it but continue

Skip Claude Code auth check — the user is already authenticated (they are talking to you right now).

**Identify Arthur Platform URL:** Ask the user:
> "Are you onboarding to the Arthur SaaS Platform at **https://platform.arthur.ai**?
> Or do you have a self-hosted Arthur Platform at a different URL?"

Default to `https://platform.arthur.ai` if the user confirms. Save `ARTHUR_PLATFORM_URL` to state.

Verify the platform is reachable:
```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "${ARTHUR_PLATFORM_URL}/api/v1/auth/oidc/.well-known/openid-configuration" 2>/dev/null || echo "000")
echo "PLATFORM_REACHABLE=$HTTP_STATUS"
```

- `200` → proceed
- anything else → warn the user ("Platform not reachable at <ARTHUR_PLATFORM_URL>"); ask to check the URL or network before continuing

---

## Steps 2–7: Platform Sub-skills

Each step is handled by a dedicated sub-skill. Invoke them in sequence using the Skill tool. Each sub-skill reads its inputs from `.arthur-engine.env` and writes its outputs back to the same file.

**Invoke in order:**

1. **Step 2** — `arthur-onboard-platform-access`
   Guides service account creation, collects credentials, acquires an OAuth2 token.
   Establishes `ARTHUR_PLATFORM_CLIENT_ID` and `ARTHUR_PLATFORM_TOKEN` in state.

2. **Step 3** — `arthur-onboard-platform-workspace`
   Lists or creates a workspace.
   Establishes `ARTHUR_PLATFORM_WORKSPACE_ID` and `ARTHUR_PLATFORM_WORKSPACE_NAME` in state.

3. **Step 4** — `arthur-onboard-platform-engine`
   Lists registered engines (data planes) or deploys a new one (Docker Compose, CloudFormation, or Kubernetes).
   Establishes `ARTHUR_PLATFORM_ENGINE_ID` and `ARTHUR_PLATFORM_ENGINE_URL` in state.

4. **Step 5–7** — `arthur-onboard-platform-model`
   Gates on application type (Agentic only continues; ML/GenAI models are routed to the platform UI).
   Creates a Project and Agentic Model on the platform, then retrieves task connection info.
   Establishes `ARTHUR_PLATFORM_PROJECT_ID`, `ARTHUR_PLATFORM_MODEL_ID`, `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, and `ARTHUR_TASK_ID` in state.

---

## Steps 8–13: Reused Sub-skills

After the platform setup is complete, the remaining steps are identical to the OSS onboarding flow. Each sub-skill reads `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, and `ARTHUR_TASK_ID` from state — exactly as set by `arthur-onboard-platform-model`.

**Invoke in order:**

5. **Step 8** — `arthur-onboard-analyze`
   Analyzes the target repository for language, framework, and existing instrumentation.
   Writes `ARTHUR_DETECTED_LANGUAGE`, `ARTHUR_DETECTED_FRAMEWORK`, `ARTHUR_IS_INSTRUMENTED` to state.

6. **Step 9** — `arthur-onboard-instrument`
   Instruments the application code (Python arthur-sdk, Mastra TypeScript, or OpenInference/OTel).

7. **Step 10** — `arthur-onboard-prompts`
   Extracts prompt definitions from the repo and registers them with Arthur Engine.

8. **Step 11** — `arthur-onboard-verify`
   Asks the user to run the app, then polls for traces to confirm instrumentation is working.

9. **Step 12** — `arthur-onboard-eval-provider`
   Configures an LLM model provider for continuous evals.
   Writes `ARTHUR_EVAL_PROVIDER` and `ARTHUR_EVAL_MODEL` to state.

10. **Step 13** — `arthur-onboard-evals`
    Recommends and creates continuous LLM evals for the task.

> **Sub-skill not found?** If a sub-skill is not installed, its step instructions appear in the
> system's available-skills list. If missing entirely, ask the user to install all `arthur-onboard-*`
> and `arthur-onboard-platform-*` skills alongside this one (see README.md for install commands).

---

## Step 13/13 — Done

After all sub-skills complete, read the final state:
```bash
cat .arthur-engine.env 2>/dev/null
```

Provide a completion summary:

```
Onboarding complete!

  Arthur Platform:    <ARTHUR_PLATFORM_URL>
  Workspace:          <ARTHUR_PLATFORM_WORKSPACE_NAME> (<ARTHUR_PLATFORM_WORKSPACE_ID>)
  Engine:             <ARTHUR_PLATFORM_ENGINE_ID>
  Engine URL:         <ARTHUR_ENGINE_URL>
  Model:              <ARTHUR_PLATFORM_MODEL_ID>
  Task:               <ARTHUR_TASK_ID>
  Continuous evals:   <N> monitoring your application

Next: Run your application with the Arthur env vars set to start seeing traces and
eval scores in the Arthur Platform UI at <ARTHUR_PLATFORM_URL>.
```

Note any steps that were skipped or require manual follow-up (e.g., model provider configuration not set, prompts not registered, trace verification pending).

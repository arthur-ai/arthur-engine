---
name: arthur-onboard-analyze
description: Arthur onboarding sub-skill — Step 4: Analyze the target repository (language, framework, existing instrumentation). Writes detection results to .arthur-engine.env.
allowed-tools: Bash, Read
---

# Arthur Onboard — Step 4: Analyze Repository

**Goal:** Detect language, framework, and existing instrumentation. Write results to `.arthur-engine.env`.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

---

## Detection

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

## Write Results to State

```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_DETECTED_LANGUAGE=\|^ARTHUR_DETECTED_FRAMEWORK=\|^ARTHUR_IS_INSTRUMENTED=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_DETECTED_LANGUAGE=<language>" >> "$STATE_FILE"
echo "ARTHUR_DETECTED_FRAMEWORK=<framework>" >> "$STATE_FILE"
echo "ARTHUR_IS_INSTRUMENTED=<true|false>" >> "$STATE_FILE"
```

Report the detected values to the user before exiting.

# `/arthur-onboard` — Arthur GenAI Engine Onboarding Skill for Claude Code

A Claude Code skill that onboards any agentic application to [Arthur GenAI Engine](https://github.com/arthur-ai/arthur-engine) — connecting it to observability, evaluation, and governance tooling.

This skill runs directly inside Claude Code CLI using your existing authentication.

**What it does (10-step workflow):**
1. Pre-flight check (git status)
2. Connect to Arthur GenAI Engine (local Docker install or remote)
3. Create or select an Arthur Task
4. Analyze your repository (language, framework, existing instrumentation)
5. Instrument your code (Python arthur-sdk, Mastra TypeScript, or OpenInference/OTel)
6. Extract and register prompts
7. Verify traces are flowing
8. Configure a model provider for evaluations
9. Recommend and create continuous evals
10. Done — traces and evals are live

---

## Architecture

The skill is modularized into a main orchestrator + 8 step sub-skills. The main `/arthur-onboard` skill sequences them; each sub-skill can also be invoked standalone if you need to re-run a specific step.

| Skill | Step | Purpose |
|---|---|---|
| `arthur-onboard-oss` | Orchestrator | Runs steps 1 & 10, sequences the rest |
| `arthur-onboard-oss-engine` | Step 2 | Connect to Arthur Engine (local or remote) |
| `arthur-onboard-task` | Step 3 | Create or select an Arthur Task |
| `arthur-onboard-analyze` | Step 4 | Detect language, framework, existing instrumentation |
| `arthur-onboard-instrument` | Step 5 | Instrument code (Python SDK, Mastra TS, or OpenInference) |
| `arthur-onboard-prompts` | Step 6 | Extract & register prompts |
| `arthur-onboard-verify` | Step 7 | Verify traces are flowing |
| `arthur-onboard-eval-provider` | Step 8 | Configure LLM eval model provider |
| `arthur-onboard-evals` | Step 9 | Recommend & create continuous evals |

---

## Quick start (no install)

Paste this prompt directly into Claude Code — no installation needed:

```
For each skill name in this list — arthur-onboard-oss, arthur-onboard-oss-engine, arthur-onboard-task, arthur-onboard-analyze, arthur-onboard-instrument, arthur-onboard-prompts, arthur-onboard-verify, arthur-onboard-eval-provider, arthur-onboard-evals — fetch https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/integrations/claude-code-skills/arthur-onboard/<skill-name>/SKILL.md and save it to ~/.claude/skills/<skill-name>/SKILL.md (create the directory if it doesn't exist). Once all skills are saved, read ~/.claude/skills/arthur-onboard-oss/SKILL.md and follow its instructions.
```

---

## Installation

Skills live in a `.claude/skills/` directory. Claude Code loads them from two places:

| Location | Scope |
|---|---|
| `~/.claude/skills/arthur-onboard*/` | **Global** — available in every project on your machine |
| `.claude/skills/arthur-onboard*/` | **Project** — committed to a repo, shared with your team |

### Global install (recommended)

Install all skills with one script:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
for skill in arthur-onboard-oss arthur-onboard-oss-engine arthur-onboard-task arthur-onboard-analyze \
             arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify \
             arthur-onboard-eval-provider arthur-onboard-evals; do
  mkdir -p ~/.claude/skills/$skill
  curl -sSLf "$BASE/$skill/SKILL.md" > ~/.claude/skills/$skill/SKILL.md
done
```

### Project install

Add to a specific repository so your team gets it automatically when they open Claude Code:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
for skill in arthur-onboard-oss arthur-onboard-oss-engine arthur-onboard-task arthur-onboard-analyze \
             arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify \
             arthur-onboard-eval-provider arthur-onboard-evals; do
  mkdir -p .claude/skills/$skill
  curl -sSLf "$BASE/$skill/SKILL.md" > .claude/skills/$skill/SKILL.md
done
git add .claude/skills/arthur-onboard*/
git commit -m "Add Arthur GenAI Engine onboarding skills"
```

### Manual install

Download the `SKILL.md` from each sub-directory in this repo and place each at:
- `~/.claude/skills/<skill-name>/SKILL.md` (global), or
- `.claude/skills/<skill-name>/SKILL.md` in your project root

### Update to latest

Re-run the same install script — it overwrites files in place.

---

## Usage

Open Claude Code CLI in your agentic application's repository and run:

```
/arthur-onboard-oss
```

Claude will guide you through each step interactively, asking for confirmation before making any changes to your code.

---

## Prerequisites

- [Claude Code CLI](https://github.com/anthropics/claude-code) installed and authenticated
- Git repository (recommended — the skill warns if your repo has uncommitted changes)
- **For local Arthur Engine install:** Docker Desktop running on macOS
- **For remote Arthur Engine:** URL and API key for your deployment

---

## State file

The skill persists connection details (engine URL, API key, task ID) to `.arthur-engine.env` in your project root. This file is automatically added to `.gitignore` — it contains credentials and should never be committed.

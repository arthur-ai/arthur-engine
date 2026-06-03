# Arthur Onboarding Skills for Claude Code

Two Claude Code skills for onboarding agentic applications to Arthur — one for the open-source engine, one for the Arthur SaaS Platform.

| Skill | Target | Jump to |
|---|---|---|
| `/arthur-onboard-oss` | Self-hosted Arthur GenAI Engine (local Docker or remote) | [OSS skill →](#arthur-onboard-oss--arthur-oss-genai-engine-onboarding-skill-for-claude-code) |
| `/arthur-onboard-platform` | Arthur SaaS Platform (platform.arthur.ai) | [Platform skill →](#arthur-onboard-platform--arthur-platform-saas-onboarding-skill) |

---

# `/arthur-onboard-oss` — Arthur OSS GenAI Engine Onboarding Skill for Claude Code

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

The skill is modularized into a main orchestrator + 8 step sub-skills. The main `/arthur-onboard-oss` skill sequences them; each sub-skill can also be invoked standalone if you need to re-run a specific step.

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
For each skill name in this list — arthur-onboard-oss, arthur-onboard-oss-engine, arthur-onboard-task, arthur-onboard-analyze, arthur-onboard-instrument, arthur-onboard-prompts, arthur-onboard-verify, arthur-onboard-eval-provider, arthur-onboard-evals, arthur-skills-upgrade — fetch https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/integrations/claude-code-skills/arthur-onboard/<skill-name>/SKILL.md and save it to ~/.claude/skills/<skill-name>/SKILL.md (create the directory if it doesn't exist). Also fetch https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/integrations/claude-code-skills/arthur-onboard/arthur-onboard-instrument/EXAMPLES.md and save it to ~/.claude/skills/arthur-onboard-instrument/EXAMPLES.md. Once all files are saved, read ~/.claude/skills/arthur-onboard-oss/SKILL.md and follow its instructions.
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
             arthur-onboard-eval-provider arthur-onboard-evals arthur-skills-upgrade; do
  mkdir -p ~/.claude/skills/$skill
  curl -sSLf "$BASE/$skill/SKILL.md" > ~/.claude/skills/$skill/SKILL.md \
    || { echo "FAILED: $skill"; rm -f ~/.claude/skills/$skill/SKILL.md; }
done
# Also install the instrumentation examples reference
curl -sSLf "$BASE/arthur-onboard-instrument/EXAMPLES.md" > ~/.claude/skills/arthur-onboard-instrument/EXAMPLES.md \
  || { echo "FAILED: arthur-onboard-instrument/EXAMPLES.md"; rm -f ~/.claude/skills/arthur-onboard-instrument/EXAMPLES.md; }
```

### Project install

Add to a specific repository so your team gets it automatically when they open Claude Code:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
for skill in arthur-onboard-oss arthur-onboard-oss-engine arthur-onboard-task arthur-onboard-analyze \
             arthur-onboard-instrument arthur-onboard-prompts arthur-onboard-verify \
             arthur-onboard-eval-provider arthur-onboard-evals arthur-skills-upgrade; do
  mkdir -p .claude/skills/$skill
  curl -sSLf "$BASE/$skill/SKILL.md" > .claude/skills/$skill/SKILL.md \
    || { echo "FAILED: $skill"; rm -f .claude/skills/$skill/SKILL.md; }
done
# Also install the instrumentation examples reference
curl -sSLf "$BASE/arthur-onboard-instrument/EXAMPLES.md" > .claude/skills/arthur-onboard-instrument/EXAMPLES.md \
  || { echo "FAILED: arthur-onboard-instrument/EXAMPLES.md"; rm -f .claude/skills/arthur-onboard-instrument/EXAMPLES.md; }
git add .claude/skills/arthur-onboard*/
git commit -m "Add Arthur GenAI Engine onboarding skills"
```

### Manual install

Download the `SKILL.md` from each sub-directory in this repo and place each at:
- `~/.claude/skills/<skill-name>/SKILL.md` (global), or
- `.claude/skills/<skill-name>/SKILL.md` in your project root

### Keeping skills up to date

Run `/arthur-skills-upgrade` at any time to check versions and install updates:

```
/arthur-skills-upgrade
```

This reads the `version` field from each installed skill, compares it against the latest
on GitHub main, and updates only the stale ones after confirmation.

**First-time upgrade (installed before versioning was introduced):**
If you installed skills before version fields were added, run this one-liner to bootstrap
the upgrade skill, then run `/arthur-skills-upgrade` to bring everything else current:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
mkdir -p ~/.claude/skills/arthur-skills-upgrade
curl -sSLf "$BASE/arthur-skills-upgrade/SKILL.md" > ~/.claude/skills/arthur-skills-upgrade/SKILL.md
```

Alternatively, re-run the full install script above — it overwrites all files in place.

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

---

---

# `/arthur-onboard-platform` — Arthur Platform (SaaS) Onboarding Skill

A Claude Code skill that onboards agentic applications to the [Arthur SaaS Platform](https://platform.arthur.ai) — handling authentication, workspace selection, engine deployment, model creation, code instrumentation, trace verification, and eval configuration.

**What it does (13-step workflow):**
1. Pre-flight check (git status) + identify platform URL
2. Authenticate via service account (OAuth2 client credentials)
3. Select or create a workspace
4. Ensure an Arthur Engine is registered (or deploy one)
5. Determine application type (Agentic only; ML/GenAI → platform UI)
6. Create a Project and Agentic Model on the platform
7. Retrieve GenAI Engine task connection info
8. Analyze your repository (language, framework, existing instrumentation)
9. Instrument your code (Python arthur-sdk, Mastra TypeScript, or OpenInference/OTel)
10. Extract and register prompts
11. Verify traces are flowing
12. Configure a model provider for evaluations
13. Recommend and create continuous evals

---

## Architecture

The platform skill uses the same modular design as the OSS skill. Four new platform-specific sub-skills handle the SaaS setup; the remaining six sub-skills are **shared** with the OSS skill.

| Skill | Step | Purpose |
|---|---|---|
| `arthur-onboard-platform` | Orchestrator | Runs steps 1 & 13, sequences the rest |
| `arthur-onboard-platform-access` | Step 2 | Authenticate with service account (OAuth2) |
| `arthur-onboard-platform-workspace` | Step 3 | Select or create workspace |
| `arthur-onboard-platform-engine` | Step 4 | Register or deploy Arthur Engine (data plane) |
| `arthur-onboard-platform-model` | Steps 5–7 | Gate on type; create Agentic Model; get task connection info |
| `arthur-onboard-platform-token` | Helper | Refresh OAuth2 token via `arthur_client` *(used by Steps 2–7)* |
| `arthur-onboard-analyze` | Step 8 | Detect language, framework, existing instrumentation *(shared)* |
| `arthur-onboard-instrument` | Step 9 | Instrument code *(shared)* |
| `arthur-onboard-prompts` | Step 10 | Extract & register prompts *(shared)* |
| `arthur-onboard-verify` | Step 11 | Verify traces are flowing *(shared)* |
| `arthur-onboard-eval-provider` | Step 12 | Configure LLM eval model provider *(shared)* |
| `arthur-onboard-evals` | Step 13 | Recommend & create continuous evals *(shared)* |

---

## Quick start (no install)

Paste this prompt directly into Claude Code — no installation needed:

```
For each skill name in this list — arthur-onboard-platform, arthur-onboard-platform-access, arthur-onboard-platform-workspace, arthur-onboard-platform-engine, arthur-onboard-platform-model, arthur-onboard-platform-token, arthur-onboard-analyze, arthur-onboard-instrument, arthur-onboard-prompts, arthur-onboard-verify, arthur-onboard-eval-provider, arthur-onboard-evals, arthur-skills-upgrade — fetch https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/integrations/claude-code-skills/arthur-onboard/<skill-name>/SKILL.md and save it to ~/.claude/skills/<skill-name>/SKILL.md (create the directory if it doesn't exist). Also fetch https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/integrations/claude-code-skills/arthur-onboard/arthur-onboard-instrument/EXAMPLES.md and save it to ~/.claude/skills/arthur-onboard-instrument/EXAMPLES.md. Once all files are saved, read ~/.claude/skills/arthur-onboard-platform/SKILL.md and follow its instructions.
```

---

## Installation

### Global install (recommended)

Install all platform skills (including the shared sub-skills) with one script:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
for skill in arthur-onboard-platform arthur-onboard-platform-access arthur-onboard-platform-workspace \
             arthur-onboard-platform-engine arthur-onboard-platform-model arthur-onboard-platform-token \
             arthur-onboard-analyze arthur-onboard-instrument arthur-onboard-prompts \
             arthur-onboard-verify arthur-onboard-eval-provider arthur-onboard-evals \
             arthur-skills-upgrade; do
  mkdir -p ~/.claude/skills/$skill
  curl -sSLf "$BASE/$skill/SKILL.md" > ~/.claude/skills/$skill/SKILL.md \
    || { echo "FAILED: $skill"; rm -f ~/.claude/skills/$skill/SKILL.md; }
done
# Also install the instrumentation examples reference
curl -sSLf "$BASE/arthur-onboard-instrument/EXAMPLES.md" > ~/.claude/skills/arthur-onboard-instrument/EXAMPLES.md \
  || { echo "FAILED: arthur-onboard-instrument/EXAMPLES.md"; rm -f ~/.claude/skills/arthur-onboard-instrument/EXAMPLES.md; }
```

### Project install

Add to a specific repository so your team gets it automatically:

```bash
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard"
for skill in arthur-onboard-platform arthur-onboard-platform-access arthur-onboard-platform-workspace \
             arthur-onboard-platform-engine arthur-onboard-platform-model arthur-onboard-platform-token \
             arthur-onboard-analyze arthur-onboard-instrument arthur-onboard-prompts \
             arthur-onboard-verify arthur-onboard-eval-provider arthur-onboard-evals \
             arthur-skills-upgrade; do
  mkdir -p .claude/skills/$skill
  curl -sSLf "$BASE/$skill/SKILL.md" > .claude/skills/$skill/SKILL.md \
    || { echo "FAILED: $skill"; rm -f .claude/skills/$skill/SKILL.md; }
done
# Also install the instrumentation examples reference
curl -sSLf "$BASE/arthur-onboard-instrument/EXAMPLES.md" > .claude/skills/arthur-onboard-instrument/EXAMPLES.md \
  || { echo "FAILED: arthur-onboard-instrument/EXAMPLES.md"; rm -f .claude/skills/arthur-onboard-instrument/EXAMPLES.md; }
git add .claude/skills/arthur-onboard*/
git commit -m "Add Arthur Platform onboarding skills"
```

---

## Usage

Open Claude Code CLI in your agentic application's repository and run:

```
/arthur-onboard-platform
```

---

## Prerequisites

- [Claude Code CLI](https://github.com/anthropics/claude-code) installed and authenticated
- An [Arthur Platform](https://platform.arthur.ai) account with permission to create service accounts
- Git repository (recommended)
- **For Docker Compose engine deployment:** Docker Desktop running on your machine
- **For an existing engine:** the engine must have been deployed with platform-issued data plane credentials (not OSS credentials)

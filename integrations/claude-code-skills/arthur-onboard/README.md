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

## Quick start (no install)

Paste this prompt directly into Claude Code — no installation needed:

```
Fetch https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/integrations/claude-code-skills/arthur-onboard/SKILL.md, save it to ~/.claude/skills/arthur-onboard/SKILL.md (create the directory if it doesn't exist), read the saved file, and follow its instructions.
```

This fetches the skill on the fly and runs it immediately.

---

## Installation

Skills live in a `.claude/skills/` directory. Claude Code loads them from two places:

| Location | Scope |
|---|---|
| `~/.claude/skills/arthur-onboard/` | **Global** — available in every project on your machine |
| `.claude/skills/arthur-onboard/` | **Project** — committed to a repo, shared with your team |

### Global install (recommended)

One-liner — installs the skill for all your projects:

```bash
mkdir -p ~/.claude/skills/arthur-onboard && \
  curl -sSLf https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard/SKILL.md \
  > ~/.claude/skills/arthur-onboard/SKILL.md
```

### Project install

Add to a specific repository so your team gets it automatically when they open Claude Code:

```bash
mkdir -p .claude/skills/arthur-onboard && \
  curl -sSLf https://raw.githubusercontent.com/arthur-ai/arthur-engine/main/integrations/claude-code-skills/arthur-onboard/SKILL.md \
  > .claude/skills/arthur-onboard/SKILL.md
git add .claude/skills/arthur-onboard/SKILL.md
git commit -m "Add Arthur GenAI Engine onboarding skill"
```

### Manual install

Download [SKILL.md](./SKILL.md) and place it at:
- `~/.claude/skills/arthur-onboard/SKILL.md` (global), or
- `.claude/skills/arthur-onboard/SKILL.md` in your project root

### Update to latest

Re-run the same install command — it overwrites the file in place.

---

## Usage

Open Claude Code CLI in your agentic application's repository and run:

```
/arthur-onboard
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

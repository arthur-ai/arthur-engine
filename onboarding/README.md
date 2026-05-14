# Buzz — Arthur GenAI Engine Onboarding Agent

Buzz is an interactive CLI wizard that connects your agentic application to [Arthur GenAI Engine](https://arthur.ai) in minutes. It analyzes your codebase, installs the right instrumentation, and verifies that traces are flowing — all without leaving your terminal.

## Requirements

| Dependency | Version | Notes |
|---|---|---|
| Node.js | ≥ 20 | |
| Claude Code | latest | `npm install -g @anthropic-ai/claude-code` |
| Git | any | Your repo must have a clean working tree |
| macOS | any | Required for local Arthur Engine installation only |

You also need an Anthropic API key set in your environment (`ANTHROPIC_API_KEY`), or Claude Code authenticated via `claude auth login`.

## Quickstart

Run Buzz from the root of your agentic application:

```bash
npx @arthur-ai/buzz
```

Or install globally:

```bash
npm install -g @arthur-ai/buzz
buzz
```

> **Your repository must have no uncommitted changes before running Buzz.** Commit or stash your work first.

## Local Development

After making changes to the Buzz source code, rebuild and reinstall globally to test them:

```bash
npm run build && npm install -g .
```

This compiles the TypeScript source and replaces the globally installed `buzz` binary with your local build.

## What Buzz does

Buzz walks you through 7 steps automatically:

**Step 1 — Pre-flight check**
Verifies git is clean, Claude Code is installed and authenticated.

**Step 2 — Arthur GenAI Engine**
Connects to Arthur Engine. If you don't have one, Buzz can install it locally on Mac (requires Docker) or connect to an existing remote deployment. Credentials are saved so you don't have to re-enter them on subsequent runs.

**Step 3 — Task setup**
Creates or selects an Arthur Task — the logical grouping for your application's traces and evaluations.

**Step 4–6 — Instrumentation**
Buzz analyzes your codebase and applies the right instrumentation automatically using Claude:

| App type | What gets added |
|---|---|
| Python (LangChain, OpenAI, CrewAI, etc.) | `arthur-observability-sdk` + framework-specific instrumentation |
| Mastra (TypeScript) | `@mastra/arthur` package + `ArthurExporter` registered in your Mastra instance |
| Other (any framework) | OpenInference / OpenTelemetry instrumentation |

All API keys stay in environment variables — never hardcoded. A `.env.example` entry is added for `ARTHUR_API_KEY`, `ARTHUR_BASE_URL`, and `ARTHUR_TASK_ID`.

**Step 7 — Verification**
Prompts you to run your application, then polls Arthur Engine for incoming traces. Confirms live data is flowing.

## How instrumentation works

Buzz uses the [Claude Agent SDK](https://github.com/anthropic-ai/claude-agent-sdk) to drive Claude Code programmatically inside your repository. Claude reads your code, installs dependencies, edits the right files, runs your existing test suite, and fixes any failures it introduces — then reports a structured result back to Buzz.

Claude operates with `acceptEdits` permission mode, meaning it can read and write files but will not run arbitrary shell commands without them being explicitly listed (`npm install`, `tsc`, your test runner).

## Environment variables set by Buzz

After running Buzz your application needs these environment variables to send traces:

```
ARTHUR_API_KEY=<your-arthur-api-key>
ARTHUR_BASE_URL=<your-engine-url>      # e.g. http://localhost:3030
ARTHUR_TASK_ID=<your-task-id>
```

Buzz adds these to `.env.example` in your repo. Set them in your shell or `.env` before running your app.

## Re-running Buzz

Buzz is idempotent. It detects existing configuration (Arthur Engine URL, API key, task ID) and existing instrumentation, and skips steps that are already complete. Run it again at any time to reconfigure or re-verify.

## Local Arthur Engine (Mac)

If you choose to install Arthur Engine locally, Buzz runs the official install script:

```bash
bash <(curl -sSL https://get-genai-engine.arthur.ai/mac)
```

This installs Docker (if needed) and starts Arthur Engine at `http://localhost:3030`. Buzz waits up to 2 minutes for the engine to become ready before proceeding.

## Troubleshooting

**"Git repository has uncommitted changes"**
Commit or stash your changes: `git stash` then re-run Buzz.

**"Claude Code is not installed"**
```bash
npm install -g @anthropic-ai/claude-code
```

**"Claude Code is not authenticated"**
```bash
export ANTHROPIC_API_KEY=your-key-here
# or
claude auth login
```

**"Engine at … is not reachable"**
Check that Arthur Engine is running and the URL is correct. For local installs, ensure Docker is running.

**No traces detected after instrumentation**
1. Did your application run and make at least one LLM call?
2. Is `ARTHUR_API_KEY` set in your shell?
3. Is `ARTHUR_BASE_URL` pointing to the correct engine URL?
4. Is `ARTHUR_TASK_ID` set correctly?
5. Check your application logs for OpenTelemetry export errors.

For local installs, find your admin API key with:
```bash
grep GENAI_ENGINE_ADMIN_KEY ~/genai-engine/.env
```

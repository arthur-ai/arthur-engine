# Claude Code → Arthur Engine Integration

Traces Claude Code sessions as OpenInference spans in Arthur Engine. Every user prompt becomes a trace containing the tool calls Claude made and the LLM API calls it used to respond.

## How it works

The tracer hooks into Claude Code's `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, and `Stop` events. `UserPromptSubmit` fires before Claude starts processing each prompt, giving accurate turn start times and the exact prompt text. Tool failures are captured as error spans so they're visible in traces.

```
Trace: "claude-code-turn"              ← one per user prompt
├── LLM  claude/claude-sonnet-4-6     ← from transcript (actual timestamps)
├── TOOL Read                          ← PostToolUse (success)
├── TOOL Edit [ERROR]                  ← PostToolUseFailure (failure)
├── RETRIEVER WebSearch                ← PostToolUse, web retrieval
├── RETRIEVER WebFetch                 ← PostToolUse, web retrieval
└── AGENT Task                         ← PostToolUse, sub-agent call
```

Traces are linked to a task in Arthur Engine via the `arthur.task` resource attribute and share a `arthur.session` attribute so you can filter by session across traces.

---

## Local setup

The installer supports two modes. Use **global** to trace all your Claude Code sessions with one install, or **per-project** to scope tracing to a specific project with its own credentials.

---

### Option A — Global install (trace all projects)

```bash
cd integrations/claude-code

# Optional but recommended: add credentials so the installer writes the config for you
cp .env.example .env   # or create .env manually (see below)

./install.sh
```

What this does:

1. `pip install -r requirements.txt`
2. Copies tracer to `~/.claude/hooks/`
3. Registers hooks in `~/.claude/settings.json` (fires in every Claude Code session)
4. Writes `~/.claude/arthur_config.json` from `.env` (if present)

Restart Claude Code after the first install.

---

### Option B — Per-project install (scoped to one project)

```bash
cd integrations/claude-code
./install.sh --project-dir path/to/your/project
```

What this does:

1. `pip install -r requirements.txt`
2. Copies tracer to `<project>/.claude/hooks/`
3. Registers hooks in `<project>/.claude/settings.local.json` (gitignored — fires only in this project)
4. Writes `<project>/.claude/arthur_config.json` from `.env` (project dir or this dir)
5. Adds `.claude/arthur_config.json` to `<project>/.gitignore`

Restart Claude Code after the first install.

> **Note:** `settings.local.json` uses `$CLAUDE_PROJECT_DIR` to locate the tracer at runtime, so the same hook registration also works in CI (as long as the tracer is copied into the project — the install step handles this).

---

### Credentials

Populate `.env` in this directory before running `install.sh` and the config file will be written automatically:

```bash
# integrations/claude-code/.env
GENAI_ENGINE_API_KEY=<your-api-key>
GENAI_ENGINE_TASK_ID=<your-task-id>
GENAI_ENGINE_TRACE_ENDPOINT=https://<your-arthur-engine-host>/api/v1/traces
```

The tracer resolves credentials in this priority order:

1. Environment variables (`GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TASK_ID`, `GENAI_ENGINE_TRACE_ENDPOINT`)
2. `<project>/.claude/arthur_config.json`
3. `~/.claude/arthur_config.json`

You can also write either config file manually:

```json
{
  "api_key": "<your-api-key>",
  "task_id": "<your-task-id>",
  "endpoint": "https://<your-arthur-engine-host>/api/v1/traces"
}
```

If none of the above are configured, the tracer silently does nothing — safe to install in shared projects.

---

### Re-running install.sh

`install.sh` is idempotent. Re-running updates the tracer binary and config without duplicating hook entries.

---

## GitHub Actions setup

Add a setup step before the Claude Code action in your workflow. The tracer is copied into `.claude/hooks/` in the checkout, and credentials are passed via the `env:` block.

**Interactive Claude (`@claude` mentions):**

```yaml
- name: Setup Arthur Engine tracing
  run: |
    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
    mkdir -p .claude/hooks
    cp integrations/claude-code/claude_code_tracer.py .claude/hooks/claude_code_tracer.py

- name: Run Claude Code
  uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    settings: |
      {
        "hooks": {
          "UserPromptSubmit":  [{"matcher": "", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py\" user_prompt_submit"}]}],
          "PreToolUse":        [{"matcher": "", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py\" pre_tool"}]}],
          "PostToolUse":       [{"matcher": "", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py\" post_tool"}]}],
          "PostToolUseFailure":[{"matcher": "", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py\" post_tool_failure"}]}],
          "Stop":              [{"matcher": "", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py\" stop"}]}]
        }
      }
  env:
    GENAI_ENGINE_API_KEY: ${{ secrets.GENAI_ENGINE_API_KEY }}
    GENAI_ENGINE_TASK_ID: ${{ vars.GENAI_ENGINE_TASK_ID }}
    GENAI_ENGINE_TRACE_ENDPOINT: ${{ vars.GENAI_ENGINE_TRACE_ENDPOINT }}
```

**Automated PR review:**

```yaml
- name: Setup Arthur Engine tracing
  run: ./integrations/claude-code/install.sh

- name: Run Claude Code Review
  uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    plugin_marketplaces: 'https://github.com/anthropics/claude-code.git'
    plugins: 'code-review@claude-code-plugins'
    prompt: '/code-review:code-review --comment https://github.com/${{ github.repository }}/pull/${{ github.event.pull_request.number }}'
  env:
    GENAI_ENGINE_API_KEY: ${{ secrets.GENAI_ENGINE_API_KEY }}
    GENAI_ENGINE_TASK_ID: ${{ vars.GENAI_ENGINE_TASK_ID }}
    GENAI_ENGINE_TRACE_ENDPOINT: ${{ vars.GENAI_ENGINE_TRACE_ENDPOINT }}
```

**GitHub repo configuration:**

| Type | Name | Value |
|------|------|-------|
| Secret | `GENAI_ENGINE_API_KEY` | Arthur Engine API key |
| Variable | `GENAI_ENGINE_TASK_ID` | Task UUID in Arthur Engine |
| Variable | `GENAI_ENGINE_TRACE_ENDPOINT` | `https://<host>/api/v1/traces` |

Set these under **Settings → Secrets and variables → Actions**.

---

## Testing

Unit tests cover config discovery, transcript parsing, turn detection, LLM span extraction, all five hook handlers, RETRIEVER span kind routing, and error span emission. No credentials or running services are required — OTLP export is mocked.

```bash
cd integrations/claude-code
pip install pytest
python3 -m pytest test_tracer.py -v
```

---

## Files

| File | Purpose |
|------|---------|
| `claude_code_tracer.py` | Hook script — handles `user_prompt_submit`, `pre_tool`, `post_tool`, `post_tool_failure`, `stop` |
| `test_tracer.py` | Unit tests (pytest, no credentials needed) |
| `install.sh` | Local dev installer |
| `requirements.txt` | Python dependencies |
| `workflow-claude-code.yml` | Copy-paste template for interactive Claude workflows |
| `workflow-claude-code-review.yml` | Copy-paste template for automated PR review workflows |
| `.env` | Local credentials (not committed) |

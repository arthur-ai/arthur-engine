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

**1. Install**

```bash
cd integrations/claude-code
./install.sh --project-dir path/to/project
```

This installs the OTel dependencies, copies the tracer to `~/.claude/hooks/`, registers the hooks in `~/.claude/settings.json`, and (if `.env` exists in the project or this folder) writes `.claude/arthur_config.json` in your project directory.

Restart Claude Code after running for the first time.

**Troubleshooting:** If you see `pyenv: cannot rehash` or pip errors, install dependencies yourself then re-run the script: `python3 -m pip install -r requirements.txt` (or use a virtualenv), then run `./install.sh --project-dir path/to/project` again.

**2. Configure credentials**

The tracer picks up credentials in this priority order:

1. Environment variables
2. `<project>/.claude/arthur_config.json`
3. `~/.claude/arthur_config.json`

The easiest approach is to populate `.env` in this folder before running `install.sh`:

```bash
# integrations/claude-code/.env
GENAI_ENGINE_API_KEY=<your-api-key>
GENAI_ENGINE_TASK_ID=<your-task-id>
GENAI_ENGINE_TRACE_ENDPOINT=https://<your-arthur-engine-host>/api/v1/traces
```

Or write the config manually:

```json
// .claude/arthur_config.json  (project-level)
// ~/.claude/arthur_config.json  (global)
{
  "api_key": "<your-api-key>",
  "task_id": "<your-task-id>",
  "endpoint": "https://<your-arthur-engine-host>/api/v1/traces"
}
```

If none of the above are configured, the tracer silently does nothing — safe to install in shared projects.

**3. Re-run install.sh to update**

`install.sh` is idempotent. Re-running it updates the tracer binary and refreshes the project config without duplicating hook entries.

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

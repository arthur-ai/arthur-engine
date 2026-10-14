# Codex → Arthur Engine Integration

Exports local Codex turns as OpenInference traces in Arthur Engine. Each user
prompt becomes one `codex.turn` trace containing the final assistant response,
the model's responses and tool-call requests, tool spans, model metadata, token
usage, and Codex session and turn IDs.

## How it works

Codex starts command hooks at defined points in its lifecycle. The integration
registers seven of them in Codex's `hooks.json`: `SessionStart`,
`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `SubagentStart`,
`SubagentStop`, and `Stop`. Each hook starts
`arthur-engine/integrations/codex-observability/codex_hook_tracer.py`, which
updates short-lived per-turn state or exports spans directly to Arthur Engine.
There is no background daemon or local OTLP listener.

Each handler has a five-second Codex timeout. The OTLP export has a two-second
timeout that bounds the whole export, retries included (this needs
`opentelemetry-exporter-otlp-proto-http` 1.35 or later), so an unreachable
Engine costs a hook about four seconds. `Stop` reads only the current turn from
the end of the transcript and stops after 32 MB, so a long session can't push it
past the timeout either. The generated command always exits successfully,
including when the Python runtime, tracer, configuration, or Engine is
unavailable. Observability therefore cannot fail a Codex prompt or tool call; an
unreachable Engine slows each hook by up to the export timeout.

```text
Codex lifecycle hook
    → codex_hook_tracer.py
    → OTLP/HTTP protobuf with arthur.task
    → Arthur Engine /api/v1/traces
```

`SessionStart` records a local activation marker without exporting conversation
content. `UserPromptSubmit` supplies the exact prompt and start time.
`PostToolUse` supplies tool input and output. `Stop` supplies the final assistant
message and completes the root span. `SubagentStart` and `SubagentStop` connect
thread-spawned child work to its parent as an OpenInference `AGENT` span:

```text
parent codex.turn
    └── codex.agent
        └── child codex.turn
            └── child tool spans
```

Codex reports the parent session ID on subagent hooks. The tracer correlates
the parent's `spawn_agent` result with the child lifecycle events using the
shared `agent_id`.

The tracer reads token counts from the current Codex session transcript; no
historical sessions are scanned or backfilled.

## Global installation

Use a global install to trace supported Codex lifecycle events in trusted
projects:

```bash
cd arthur-engine/integrations/codex-observability
cp .env.example .env
# Fill .env with the target Arthur Engine values.
./install.sh
```

The installer:

1. Creates an Arthur-owned Python environment under
   `~/.codex/hooks/.arthur-venv`, isolated from other hook integrations.
2. Installs the dependencies from
   `arthur-engine/integrations/codex-observability/requirements.txt`.
3. Copies the tracer to `~/.codex/hooks/codex_hook_tracer.py`.
4. Merges seven Arthur handlers into `~/.codex/hooks.json` without replacing
   other hook definitions. Reinstalling replaces older definitions of these
   Arthur handlers instead of accumulating duplicates. If `hooks.json` can't be
   parsed, the installer stops and leaves it unchanged.
5. Writes `~/.codex/arthur_config.json` with mode `0600` when a complete `.env`
   or complete `GENAI_ENGINE_*` environment configuration is present.

Open `/hooks` in Codex, review the exact command definitions, and trust them.
Restart Codex after the first install. Codex skips new or changed non-managed
hooks until their current definitions are trusted.

Codex binds hook runtimes to tasks. After installing, upgrading, or trusting a
changed hook definition, start a new task and verify that
`~/.codex/tracer/activation/` receives a fresh mode-`0600` marker. Existing
Desktop tasks may keep stale hook state until Codex refreshes their runtime.
Arthur cannot export an event that Codex did not dispatch.

Codex exposes `SubagentStart` and `SubagentStop` only for thread-spawned
subagents. Internal or synthetic Codex agents that do not expose user lifecycle
hooks cannot be observed by this integration.

## Project-scoped installation

Use a project install when only one repository should export traces:

```bash
cd arthur-engine/integrations/codex-observability
./install.sh --project-dir /absolute/path/to/project
```

This installs the runtime under `<project>/.codex/hooks/`, registers it in
`<project>/.codex/hooks.json`, and adds `<project>/.codex/arthur_config.json`,
`hooks.json`, the venv and the tracer copy to the project's `.gitignore`: they
hold the API key or this machine's paths, so each developer runs the installer.
Codex loads project hooks only for trusted projects.

## Configuration

The tracer resolves configuration in this order:

1. `GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TASK_ID`, and
   `GENAI_ENGINE_TRACE_ENDPOINT` environment variables.
2. `<hook-payload-cwd>/.codex/arthur_config.json`.
3. `~/.codex/arthur_config.json`.

The installer also accepts the three environment variables directly and writes
their values to the mode-`0600` config without echoing them. This avoids a
temporary `.env` when credentials already come from a secure local provider.

The JSON format is:

```json
{
  "api_key": "<your-api-key>",
  "task_id": "<your-task-id>",
  "endpoint": "https://<your-arthur-engine-host>/api/v1/traces"
}
```

When no complete configuration exists, hook commands exit successfully without
exporting. API keys are used only in the outgoing `Authorization` header and are
never added to span attributes or logs.

The tracer sends prompt text, assistant output, tool input and output, model
metadata, token counts, timestamps, and Codex session and turn identifiers to
the configured Engine. Treat the destination as sensitive telemetry storage and
choose a task and retention policy appropriate for the repositories being
traced.

Exports are synchronous and have no durable retry queue. A turn or tool span
emitted while the Engine is unavailable can be lost after the bounded request
fails; Codex continues normally.

## Trace shape

```text
codex.turn                         OpenInference CHAIN root
├── codex/<model>                  OpenInference LLM (response, tool-call request)
├── Bash                           OpenInference TOOL
├── codex/<model>                  OpenInference LLM
├── apply_patch                    OpenInference TOOL
└── codex/<model>                  OpenInference LLM (final answer)
```

The root includes:

- `input.value` (the prompt) and `output.value` (the final answer)
- `session.id`, `codex.thread.id`, and `codex.turn.id`
- `llm.model_name`
- start and end timestamps from the hook lifecycle

The LLM spans are read from the turn's part of the rollout transcript and carry
the prompt, completion, cached-input, reasoning, and total token counts. If the
transcript has usage for the turn but no model output, the counts go on the root.
If the turn can't be read (no transcript, or the turn is larger than 32 MB), the
trace has the root and tool spans only, with the answer from the `Stop` payload.

Tool spans carry no status: `PostToolUse` gives the tool's model-facing output
but no exit code, so a failed command can't be told apart.

Codex currently exposes tool completion through `PostToolUse`; it does not
provide the separate `PostToolUseFailure` lifecycle event used by the Claude
Code integration.

## Testing

The tests use temporary homes and mocked exporter boundaries; they do not need
credentials or a running Engine.

```bash
cd arthur-engine
uv run --no-project --with pytest \
  --with-requirements integrations/codex-observability/requirements.txt \
  python -m pytest \
  integrations/codex-observability/test_tracer.py \
  integrations/codex-observability/test_install.py \
  integrations/codex-observability/test_model_extraction.py \
  integrations/codex-observability/test_spend_breaker.py -v
```

For a live test, configure a disposable Arthur task, submit a harmless marked
prompt in a new Codex session, and verify the actual content through
`GET /api/v1/traces?task_ids=<task-id>&include_spans=true`.

## Spend circuit breaker (optional)

`codex_spend_breaker.py` pauses Codex once model spend in the last five minutes
reaches a cap. It is the Codex counterpart of the Claude Code circuit breaker in
`../claude-code-observability`, and uses the same `breaker override` / `breaker
reset` / `breaker status` prompts. It needs nothing from Arthur Engine: it
prices each model response from the session's rollout file, where Codex writes a
`token_usage_record` as soon as the response finishes and before any tool it
asked for runs.

Codex hooks cannot end a turn, so the breaker does what Codex honours:

| Hook | While over the cap |
|---|---|
| `UserPromptSubmit` | `{"decision": "block"}`: the prompt never reaches the model |
| `PreToolUse` | `permissionDecision: "deny"` with a reason telling the model to stop |

Two limits follow from that. After a deny the model makes one more call to say
it stopped. Hosted tools such as web search never reach `PreToolUse`. The reply
never carries `continue`: Codex treats a `PreToolUse` reply that contains it as
invalid and runs the tool.

To enable it, add the script to both events in Codex's `hooks.json`, beside the
tracer's entries:

```json
{"hooks": {
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 /path/to/codex_spend_breaker.py", "timeout": 10}]}],
  "PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /path/to/codex_spend_breaker.py", "timeout": 10}]}]
}}
```

| Variable | Default | Meaning |
|---|---|---|
| `ARTHUR_BREAKER_CAP_USD` | `0.10` | USD allowed per five-minute window |
| `ARTHUR_BREAKER_STATE` | `$CODEX_HOME/spend_breaker_state.json` | Spend ledger and override, shared by all sessions |
| `ARTHUR_BREAKER_RATES_JSON` | built-in rows | Extra or replacement prices, `{"model": {"input": 2.0, "cached": 0.2, "output": 8.0}}` in USD per million tokens |
| `ARTHUR_BREAKER_LOG` | unset | Append one line per hook call |

A model without a price row is priced at the most expensive row, not at zero.
Any error in the hook lets Codex carry on.

## Uninstall

```bash
cd arthur-engine/integrations/codex-observability
./uninstall.sh
```

For a project-scoped installation:

```bash
./uninstall.sh --project-dir /absolute/path/to/project
```

The uninstaller removes only handlers that invoke this integration's tracer. It
preserves other Codex hooks and leaves `arthur_config.json` in place so removing
the runtime does not silently delete credentials or task selection.

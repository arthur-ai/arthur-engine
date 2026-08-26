# Codex → Arthur Engine Integration

Exports local Codex turns as OpenInference traces in Arthur Engine. Each user
prompt becomes one `codex.turn` trace containing the final assistant response,
tool spans, model metadata, token usage, and Codex session and turn IDs.

## How it works

Codex starts command hooks at defined points in its lifecycle. The integration
registers `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop` in Codex's
`hooks.json`. Each hook starts
`arthur-engine/integrations/codex-observability/codex_hook_tracer.py`, which
updates short-lived per-turn state or exports spans directly to Arthur Engine.
There is no background daemon or local OTLP listener.

Each handler has a five-second Codex timeout, while the outgoing OTLP request
has a shorter four-second timeout. The generated command always exits
successfully, including when the Python runtime, tracer, configuration, or
Engine is unavailable. Observability therefore cannot block a Codex prompt or
tool call.

```text
Codex lifecycle hook
    → codex_hook_tracer.py
    → OTLP/HTTP protobuf with arthur.task
    → Arthur Engine /api/v1/traces
```

`UserPromptSubmit` supplies the exact prompt and start time. `PostToolUse`
supplies tool input and output. `Stop` supplies the final assistant message and
completes the root span. The tracer reads token counts from the current Codex
session transcript; no historical sessions are scanned or backfilled.

## Global installation

Use a global install to trace Codex sessions in every trusted project:

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
4. Merges four Arthur handlers into `~/.codex/hooks.json` without replacing
   other hook definitions. Reinstalling replaces older definitions of these
   Arthur handlers instead of accumulating duplicates.
5. Writes `~/.codex/arthur_config.json` with mode `0600` when a complete `.env`
   or complete `GENAI_ENGINE_*` environment configuration is present.

Open `/hooks` in Codex, review the exact command definitions, and trust them.
Restart Codex after the first install. Codex skips new or changed non-managed
hooks until their current definitions are trusted.

## Project-scoped installation

Use a project install when only one repository should export traces:

```bash
cd arthur-engine/integrations/codex-observability
./install.sh --project-dir /absolute/path/to/project
```

This installs the runtime under `<project>/.codex/hooks/`, registers it in
`<project>/.codex/hooks.json`, and keeps `<project>/.codex/arthur_config.json`
out of version control. Codex loads project hooks only for trusted projects.

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
codex.turn                         OpenInference LLM root
├── Bash                           OpenInference TOOL
├── apply_patch                    OpenInference TOOL
└── mcp__server__tool              OpenInference TOOL
```

The root includes:

- `input.value` and `output.value`
- `session.id`, `codex.thread.id`, and `codex.turn.id`
- `llm.model_name`
- prompt, completion, cached-input, reasoning, and total token counts when the
  current transcript provides them
- start and end timestamps from the hook lifecycle

Codex currently exposes tool completion through `PostToolUse`; it does not
provide the separate `PostToolUseFailure` lifecycle event used by the Claude
Code integration.

## Testing

The tests use temporary homes and mocked exporter boundaries; they do not need
credentials or a running Engine.

```bash
cd arthur-engine
uv run --with pytest python -m pytest \
  integrations/codex-observability/test_tracer.py \
  integrations/codex-observability/test_install.py -v
```

For a live test, configure a disposable Arthur task, submit a harmless marked
prompt in a new Codex session, and verify the actual content through
`GET /api/v1/traces?task_ids=<task-id>&include_spans=true`.

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

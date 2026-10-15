#!/usr/bin/env bash
# install.sh — Install claude_code_tracer.py as Claude Code hooks
#
# Usage:
#   ./install.sh                          # Global: hooks + config for all projects
#   ./install.sh --project-dir DIR        # Per-project: hooks + config scoped to DIR
#   ./install.sh --with-circuit-breaker   # Also install the burn-rate circuit breaker
#
# Global mode (no --project-dir):
#   1. pip install -r requirements.txt
#   2. Copy tracer to ~/.claude/hooks/
#   3. Merge hooks into ~/.claude/settings.json
#   4. Write ~/.claude/arthur_config.json from .env (if present in this dir)
#
# Per-project mode (--project-dir DIR):
#   1. pip install -r requirements.txt
#   2. Copy tracer to DIR/.claude/hooks/
#   3. Merge hooks into DIR/.claude/settings.local.json (gitignored)
#   4. Write DIR/.claude/arthur_config.json from .env (project dir or this dir)
#   5. Add .claude/arthur_config.json to DIR/.gitignore
#
# --with-circuit-breaker (either mode) additionally:
#   - Copies claude_code_circuit_breaker.py next to the tracer
#   - Registers its UserPromptSubmit / PreToolUse / SessionStart hooks
#   - Writes a default arthur_circuit_breaker.json next to arthur_config.json
#     if one does not exist yet (tune budget/scope there)
#   - Checks the engine key can read spend (GENAI_ENGINE_READ_API_KEY in .env
#     becomes read_api_key for a tracing key that can only write) and exits
#     non-zero if the engine refuses it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR=""
WITH_BREAKER=0

TRACER_EVENTS="UserPromptSubmit:user_prompt_submit,PreToolUse:pre_tool,PostToolUse:post_tool,PostToolUseFailure:post_tool_failure,SubagentStop:subagent_stop,Stop:stop"
BREAKER_EVENTS="UserPromptSubmit:user_prompt_submit,PreToolUse:pre_tool,SessionStart:session_start"
# The breaker makes one short engine call; cap it well under the hook default
# so a hung engine cannot stall the session.
BREAKER_TIMEOUT=15

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        --with-circuit-breaker)
            WITH_BREAKER=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

TRACER_SRC="$SCRIPT_DIR/claude_code_tracer.py"
BREAKER_SRC="$SCRIPT_DIR/claude_code_circuit_breaker.py"
if [[ ! -f "$TRACER_SRC" ]]; then
    echo "Error: tracer not found at $TRACER_SRC" >&2
    echo "Run this script from the repo, e.g. ./integrations/claude-code-observability/install.sh" >&2
    exit 1
fi
if [[ "$WITH_BREAKER" == "1" && ! -f "$BREAKER_SRC" ]]; then
    echo "Error: circuit breaker not found at $BREAKER_SRC" >&2
    exit 1
fi

echo "==> Installing Python dependencies..."
if ! python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
    echo "Warning: pip install failed. If dependencies are already installed, you can continue." >&2
    echo "         Otherwise run: python3 -m pip install -r $SCRIPT_DIR/requirements.txt" >&2
fi

# ---------------------------------------------------------------------------
# Helper: merge hook entries into a settings JSON file.
# Args: <settings_path> <command_prefix> <events_spec> [timeout_seconds]
# The command_prefix is the python3 invocation up to (but not including)
# the event argument, e.g.:
#   'python3 "$HOME/.claude/hooks/claude_code_tracer.py"'
#   'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py"'
# events_spec is "HookEvent:script_arg,HookEvent:script_arg,...".
# ---------------------------------------------------------------------------
merge_hooks() {
    local settings_path="$1"
    local cmd_prefix="$2"
    local events_spec="$3"
    local timeout="${4:-}"
    python3 - "$settings_path" "$cmd_prefix" "$events_spec" "$timeout" <<'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
cmd_prefix = sys.argv[2]
events = [tuple(pair.split(":", 1)) for pair in sys.argv[3].split(",") if pair]
timeout = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None

settings_path.parent.mkdir(parents=True, exist_ok=True)

if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        settings = {}
else:
    settings = {}

if "hooks" not in settings:
    settings["hooks"] = {}

for event, arg in events:
    cmd = f"{cmd_prefix} {arg}"
    hook = {"type": "command", "command": cmd}
    if timeout is not None:
        hook["timeout"] = timeout
    new_hook = {"matcher": "", "hooks": [hook]}

    existing = settings["hooks"].get(event, [])
    already = any(
        any(h.get("command", "") == cmd for h in e.get("hooks", []))
        for e in existing
        if isinstance(e, dict)
    )
    if not already:
        existing.append(new_hook)
    settings["hooks"][event] = existing

settings_path.write_text(json.dumps(settings, indent=2))
print(f"  Updated {settings_path}")
PYEOF
}

# ---------------------------------------------------------------------------
# Helper: write arthur_config.json from a .env file.
# Args: <out_path> <env_file>
# ---------------------------------------------------------------------------
write_config() {
    local out_path="$1"
    local env_file="$2"
    python3 - "$out_path" "$env_file" <<'PYEOF'
import json
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
env_file = Path(sys.argv[2])

env_vars = {}
for line in env_file.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, val = line.partition("=")
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        val = val[1:-1]
    env_vars[key.strip()] = val

config = {
    "api_key": env_vars.get("GENAI_ENGINE_API_KEY", ""),
    "task_id": env_vars.get("GENAI_ENGINE_TASK_ID", ""),
    "endpoint": env_vars.get("GENAI_ENGINE_TRACE_ENDPOINT", ""),
}

if not all(config.values()):
    missing = [k for k, v in {"GENAI_ENGINE_API_KEY": config["api_key"], "GENAI_ENGINE_TASK_ID": config["task_id"], "GENAI_ENGINE_TRACE_ENDPOINT": config["endpoint"]}.items() if not v]
    print(f"  Warning: .env missing keys: {', '.join(missing)} — skipping config write", file=sys.stderr)
else:
    # Optional: the circuit breaker reads spend with this key when the
    # tracer's key can only write traces.
    if env_vars.get("GENAI_ENGINE_READ_API_KEY"):
        config["read_api_key"] = env_vars["GENAI_ENGINE_READ_API_KEY"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(config, indent=2))
    out_path.chmod(0o600)
    print(f"  Wrote {out_path}")
PYEOF
}

# ---------------------------------------------------------------------------
# Helper: install the circuit breaker next to the tracer.
# Args: <hooks_dir> <settings_path> <command_prefix> <breaker_config_path>
# ---------------------------------------------------------------------------
install_breaker() {
    local hooks_dir="$1"
    local settings_path="$2"
    local cmd_prefix="$3"
    local breaker_config="$4"

    echo "==> Copying circuit breaker to $hooks_dir/..."
    cp "$BREAKER_SRC" "$hooks_dir/claude_code_circuit_breaker.py"
    chmod +x "$hooks_dir/claude_code_circuit_breaker.py"

    echo "==> Merging circuit breaker hooks into $settings_path..."
    merge_hooks "$settings_path" "$cmd_prefix" "$BREAKER_EVENTS" "$BREAKER_TIMEOUT"

    if [[ -f "$breaker_config" ]]; then
        echo "  Keeping existing $breaker_config"
    else
        echo "==> Writing default $breaker_config..."
        python3 - "$BREAKER_SRC" "$breaker_config" <<'PYEOF'
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("breaker", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
out_path = Path(sys.argv[2])
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(module.DEFAULT_CONFIG, indent=2) + "\n")
print(f"  Wrote {out_path} (edit budget_usd / scope / rules to taste)")
PYEOF
    fi
}

# ---------------------------------------------------------------------------
# Helper: check the installed breaker can read spend from the engine.
# Args: <breaker_path> <project_dir_for_config_lookup>
# A key that cannot read traces would leave the breaker failing open on every
# hook, so that stops the install; an unreachable engine only warns.
# ---------------------------------------------------------------------------
check_breaker() {
    local breaker="$1"
    local project_dir="$2"
    echo "==> Checking the circuit breaker can read spend from Arthur Engine..."
    local rc=0
    CLAUDE_PROJECT_DIR="$project_dir" python3 "$breaker" check || rc=$?
    case "$rc" in
        0) ;;
        1) echo "  Skipped: no engine credentials yet; the breaker stays inactive until they are configured." ;;
        2)
            echo "" >&2
            echo "ERROR: the circuit breaker is installed but cannot read spend, so it would never trip." >&2
            echo "       Add a read key (GENAI_ENGINE_READ_API_KEY in .env, or read_api_key in" >&2
            echo "       arthur_config.json), then re-run this installer or: python3 \"$breaker\" check" >&2
            exit 1
            ;;
        *) echo "  Warning: could not reach Arthur Engine; check later with: python3 \"$breaker\" check" >&2 ;;
    esac
}

# ---------------------------------------------------------------------------
# Global install (no --project-dir)
# ---------------------------------------------------------------------------
if [[ -z "$PROJECT_DIR" ]]; then
    echo "==> Copying tracer to ~/.claude/hooks/..."
    mkdir -p "$HOME/.claude/hooks"
    cp "$TRACER_SRC" "$HOME/.claude/hooks/claude_code_tracer.py"
    chmod +x "$HOME/.claude/hooks/claude_code_tracer.py"

    echo "==> Merging hooks into ~/.claude/settings.json..."
    merge_hooks "$HOME/.claude/settings.json" 'python3 "$HOME/.claude/hooks/claude_code_tracer.py"' "$TRACER_EVENTS"

    if [[ "$WITH_BREAKER" == "1" ]]; then
        install_breaker "$HOME/.claude/hooks" "$HOME/.claude/settings.json" \
            'python3 "$HOME/.claude/hooks/claude_code_circuit_breaker.py"' \
            "$HOME/.claude/arthur_circuit_breaker.json"
    fi

    ENV_FILE="$SCRIPT_DIR/.env"
    if [[ -f "$ENV_FILE" ]]; then
        echo "==> Writing ~/.claude/arthur_config.json from .env..."
        write_config "$HOME/.claude/arthur_config.json" "$ENV_FILE"
    else
        echo "Note: No .env found in $SCRIPT_DIR — skipping ~/.claude/arthur_config.json."
        echo "      Populate .env or write the config manually (see README)."
    fi

    if [[ "$WITH_BREAKER" == "1" ]]; then
        # $HOME as the project dir: only the global config applies.
        check_breaker "$HOME/.claude/hooks/claude_code_circuit_breaker.py" "$HOME"
    fi

    echo ""
    echo "Done! Restart Claude Code for hooks to take effect."
    echo ""
    echo "Hooks registered in: ~/.claude/settings.json (all projects)"
    if [[ "$WITH_BREAKER" == "1" ]]; then
        echo "Circuit breaker config: ~/.claude/arthur_circuit_breaker.json"
    fi
    echo ""
    echo "To configure credentials, populate .env in this directory and re-run:"
    echo "  GENAI_ENGINE_API_KEY=..."
    echo "  GENAI_ENGINE_TASK_ID=..."
    echo "  GENAI_ENGINE_TRACE_ENDPOINT=https://<host>/api/v1/traces"
    echo "Or write ~/.claude/arthur_config.json manually."
    exit 0
fi

# ---------------------------------------------------------------------------
# Per-project install (--project-dir DIR)
# ---------------------------------------------------------------------------
echo "==> Copying tracer to $PROJECT_DIR/.claude/hooks/..."
mkdir -p "$PROJECT_DIR/.claude/hooks"
cp "$TRACER_SRC" "$PROJECT_DIR/.claude/hooks/claude_code_tracer.py"
chmod +x "$PROJECT_DIR/.claude/hooks/claude_code_tracer.py"

echo "==> Merging hooks into $PROJECT_DIR/.claude/settings.local.json..."
merge_hooks "$PROJECT_DIR/.claude/settings.local.json" 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py"' "$TRACER_EVENTS"

if [[ "$WITH_BREAKER" == "1" ]]; then
    install_breaker "$PROJECT_DIR/.claude/hooks" "$PROJECT_DIR/.claude/settings.local.json" \
        'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_circuit_breaker.py"' \
        "$PROJECT_DIR/.claude/arthur_circuit_breaker.json"
fi

# Prefer .env in project dir, then in this integration dir
ENV_FILE="$PROJECT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    ENV_FILE="$SCRIPT_DIR/.env"
fi
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Warning: .env not found at $PROJECT_DIR/.env or $SCRIPT_DIR/.env — skipping arthur_config.json" >&2
else
    echo "==> Writing $PROJECT_DIR/.claude/arthur_config.json from .env..."
    write_config "$PROJECT_DIR/.claude/arthur_config.json" "$ENV_FILE"

    # Keep arthur_config.json out of git
    GITIGNORE="$PROJECT_DIR/.gitignore"
    GITIGNORE_ENTRY=".claude/arthur_config.json"
    if [[ -f "$GITIGNORE" ]] && grep -qF "$GITIGNORE_ENTRY" "$GITIGNORE"; then
        echo "  .gitignore already contains $GITIGNORE_ENTRY"
    else
        echo "" >> "$GITIGNORE"
        echo "$GITIGNORE_ENTRY" >> "$GITIGNORE"
        echo "  Added $GITIGNORE_ENTRY to $GITIGNORE"
    fi
fi

if [[ "$WITH_BREAKER" == "1" ]]; then
    check_breaker "$PROJECT_DIR/.claude/hooks/claude_code_circuit_breaker.py" "$PROJECT_DIR"
fi

echo ""
echo "Done! Restart Claude Code for hooks to take effect."
echo ""
echo "Hooks registered in: $PROJECT_DIR/.claude/settings.local.json (this project only)"
echo "Config written to:   $PROJECT_DIR/.claude/arthur_config.json"
if [[ "$WITH_BREAKER" == "1" ]]; then
    echo "Circuit breaker config: $PROJECT_DIR/.claude/arthur_circuit_breaker.json"
fi

#!/usr/bin/env bash
# install.sh — Install claude_code_tracer.py as Claude Code hooks
#
# Usage:
#   ./install.sh                          # Global: hooks + config for all projects
#   ./install.sh --project-dir DIR        # Per-project: hooks + config scoped to DIR
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

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

TRACER_SRC="$SCRIPT_DIR/claude_code_tracer.py"
if [[ ! -f "$TRACER_SRC" ]]; then
    echo "Error: tracer not found at $TRACER_SRC" >&2
    echo "Run this script from the repo, e.g. ./integrations/claude-code-observability/install.sh" >&2
    exit 1
fi

echo "==> Installing Python dependencies..."
if ! python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
    echo "Warning: pip install failed. If dependencies are already installed, you can continue." >&2
    echo "         Otherwise run: python3 -m pip install -r $SCRIPT_DIR/requirements.txt" >&2
fi

# ---------------------------------------------------------------------------
# Helper: merge hook entries into a settings JSON file.
# Args: <settings_path> <tracer_command_prefix>
# The tracer_command_prefix is the python3 invocation up to (but not including)
# the event argument, e.g.:
#   'python3 "$HOME/.claude/hooks/claude_code_tracer.py"'
#   'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py"'
# ---------------------------------------------------------------------------
merge_hooks() {
    local settings_path="$1"
    local cmd_prefix="$2"
    python3 - "$settings_path" "$cmd_prefix" <<'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
cmd_prefix = sys.argv[2]

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

for event, arg in [
    ("UserPromptSubmit", "user_prompt_submit"),
    ("PreToolUse", "pre_tool"),
    ("PostToolUse", "post_tool"),
    ("PostToolUseFailure", "post_tool_failure"),
    ("Stop", "stop"),
]:
    cmd = f"{cmd_prefix} {arg}"
    new_hook = {"matcher": "", "hooks": [{"type": "command", "command": cmd}]}

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
    env_vars[key.strip()] = val.strip()

config = {
    "api_key": env_vars.get("GENAI_ENGINE_API_KEY", ""),
    "task_id": env_vars.get("GENAI_ENGINE_TASK_ID", ""),
    "endpoint": env_vars.get("GENAI_ENGINE_TRACE_ENDPOINT", ""),
}

if not all(config.values()):
    missing = [k for k, v in {"GENAI_ENGINE_API_KEY": config["api_key"], "GENAI_ENGINE_TASK_ID": config["task_id"], "GENAI_ENGINE_TRACE_ENDPOINT": config["endpoint"]}.items() if not v]
    print(f"  Warning: .env missing keys: {', '.join(missing)} — skipping config write", file=sys.stderr)
else:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(config, indent=2))
    out_path.chmod(0o600)
    print(f"  Wrote {out_path}")
PYEOF
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
    merge_hooks "$HOME/.claude/settings.json" 'python3 "$HOME/.claude/hooks/claude_code_tracer.py"'

    ENV_FILE="$SCRIPT_DIR/.env"
    if [[ -f "$ENV_FILE" ]]; then
        echo "==> Writing ~/.claude/arthur_config.json from .env..."
        write_config "$HOME/.claude/arthur_config.json" "$ENV_FILE"
    else
        echo "Note: No .env found in $SCRIPT_DIR — skipping ~/.claude/arthur_config.json."
        echo "      Populate .env or write the config manually (see README)."
    fi

    echo ""
    echo "Done! Restart Claude Code for hooks to take effect."
    echo ""
    echo "Hooks registered in: ~/.claude/settings.json (all projects)"
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
merge_hooks "$PROJECT_DIR/.claude/settings.local.json" 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py"'

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

echo ""
echo "Done! Restart Claude Code for hooks to take effect."
echo ""
echo "Hooks registered in: $PROJECT_DIR/.claude/settings.local.json (this project only)"
echo "Config written to:   $PROJECT_DIR/.claude/arthur_config.json"

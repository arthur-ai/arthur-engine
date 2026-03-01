#!/usr/bin/env bash
# install.sh — Install claude_code_tracer.py as global Claude Code hooks
#
# Usage:
#   ./install.sh                          # Install hooks globally
#   ./install.sh --project-dir DIR        # Also write .claude/arthur_config.json from .env
#
# What this does:
#   1. pip install -r requirements.txt
#   2. Copy tracer to ~/.claude/hooks/ (and to PROJECT_DIR/.claude/hooks/ if --project-dir set)
#   3. Merge PreToolUse/PostToolUse/Stop hooks into ~/.claude/settings.json
#   4. (Optional) With --project-dir: write .claude/arthur_config.json from .env (project or this dir)

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
    echo "Run this script from the repo, e.g. ./integrations/claude-code/install.sh" >&2
    exit 1
fi

echo "==> Installing Python dependencies..."
if ! python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
    echo "Warning: pip install failed. If dependencies are already installed, you can continue. Otherwise run: python3 -m pip install -r $SCRIPT_DIR/requirements.txt" >&2
fi

echo "==> Copying tracer to ~/.claude/hooks/..."
mkdir -p "$HOME/.claude/hooks"
cp "$TRACER_SRC" "$HOME/.claude/hooks/claude_code_tracer.py"
chmod +x "$HOME/.claude/hooks/claude_code_tracer.py"

echo "==> Merging hooks into ~/.claude/settings.json..."
python3 - <<'PYEOF'
import json
import os
from pathlib import Path

settings_path = Path.home() / ".claude" / "settings.json"
settings_path.parent.mkdir(parents=True, exist_ok=True)

# Load existing settings
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        settings = {}
else:
    settings = {}

# Ensure hooks key exists
if "hooks" not in settings:
    settings["hooks"] = {}

tracer_cmd = 'python3 "$HOME/.claude/hooks/claude_code_tracer.py" {event}'

hook_entry = {
    "matcher": "",
    "hooks": [{"type": "command", "command": ""}]
}

for event, arg in [
    ("UserPromptSubmit", "user_prompt_submit"),
    ("PreToolUse", "pre_tool"),
    ("PostToolUse", "post_tool"),
    ("PostToolUseFailure", "post_tool_failure"),
    ("Stop", "stop"),
]:
    cmd = f'python3 "$HOME/.claude/hooks/claude_code_tracer.py" {arg}'
    new_hook = {"matcher": "", "hooks": [{"type": "command", "command": cmd}]}

    existing = settings["hooks"].get(event, [])
    # Check if already installed (by command string)
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

# When --project-dir set: copy tracer into project and optionally write arthur_config.json from .env
if [[ -n "$PROJECT_DIR" ]]; then
    echo "==> Copying tracer to $PROJECT_DIR/.claude/hooks/..."
    mkdir -p "$PROJECT_DIR/.claude/hooks"
    cp "$TRACER_SRC" "$PROJECT_DIR/.claude/hooks/claude_code_tracer.py"
    chmod +x "$PROJECT_DIR/.claude/hooks/claude_code_tracer.py"

    # Prefer .env in project dir, then in this integration dir
    ENV_FILE="$PROJECT_DIR/.env"
    if [[ ! -f "$ENV_FILE" ]]; then
        ENV_FILE="$SCRIPT_DIR/.env"
    fi
    if [[ ! -f "$ENV_FILE" ]]; then
        echo "Warning: .env not found at $PROJECT_DIR/.env or $SCRIPT_DIR/.env, skipping arthur_config.json creation" >&2
    else
        echo "==> Writing $PROJECT_DIR/.claude/arthur_config.json from .env..."
        python3 - "$PROJECT_DIR" "$ENV_FILE" <<'PYEOF'
import json
import sys
from pathlib import Path

project_dir = Path(sys.argv[1])
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

out_dir = project_dir / ".claude"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "arthur_config.json"
out_path.write_text(json.dumps(config, indent=2))
print(f"  Wrote {out_path}")
PYEOF
    fi
fi

echo ""
echo "Done! Restart Claude Code for hooks to take effect."
echo ""
echo "To configure Arthur Engine credentials, either:"
echo "  - Set env vars: GENAI_ENGINE_API_KEY, GENAI_ENGINE_TASK_ID, GENAI_ENGINE_TRACE_ENDPOINT"
echo "  - Or run: ./install.sh --project-dir <your-project-dir>  (reads from .env)"
echo "  - Or write ~/.claude/arthur_config.json manually:"
echo '    {"api_key": "...", "task_id": "...", "endpoint": "..."}'

#!/usr/bin/env bash
# uninstall.sh — Remove claude_code_tracer.py hooks installed by install.sh
#
# Usage:
#   ./uninstall.sh                          # Global: undo global install
#   ./uninstall.sh --project-dir DIR        # Per-project: undo per-project install

set -euo pipefail

PROJECT_DIR=""

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

# ---------------------------------------------------------------------------
# Helper: remove arthur hook entries from a settings JSON file.
# Args: <settings_path> <tracer_command_prefix>
# ---------------------------------------------------------------------------
remove_hooks() {
    local settings_path="$1"
    local cmd_prefix="$2"
    python3 - "$settings_path" "$cmd_prefix" <<'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
cmd_prefix = sys.argv[2]

if not settings_path.exists():
    print(f"  {settings_path} not found — nothing to remove")
    sys.exit(0)

try:
    settings = json.loads(settings_path.read_text())
except (json.JSONDecodeError, OSError):
    print(f"  Could not parse {settings_path} — skipping")
    sys.exit(0)

hooks = settings.get("hooks", {})
changed = False

for event, arg in [
    ("UserPromptSubmit", "user_prompt_submit"),
    ("PreToolUse", "pre_tool"),
    ("PostToolUse", "post_tool"),
    ("PostToolUseFailure", "post_tool_failure"),
    ("Stop", "stop"),
]:
    cmd = f"{cmd_prefix} {arg}"
    existing = hooks.get(event, [])
    filtered = [
        e for e in existing
        if not (
            isinstance(e, dict)
            and any(h.get("command", "") == cmd for h in e.get("hooks", []))
        )
    ]
    if len(filtered) != len(existing):
        changed = True
    if filtered:
        hooks[event] = filtered
    elif event in hooks:
        del hooks[event]
        changed = True

if not hooks:
    settings.pop("hooks", None)

if changed:
    settings_path.write_text(json.dumps(settings, indent=2))
    print(f"  Updated {settings_path}")
else:
    print(f"  No arthur hooks found in {settings_path}")
PYEOF
}

# ---------------------------------------------------------------------------
# Helper: remove a line from a file (gitignore entry).
# Args: <file_path> <entry>
# ---------------------------------------------------------------------------
remove_gitignore_entry() {
    local file="$1"
    local entry="$2"
    if [[ ! -f "$file" ]]; then
        return
    fi
    python3 - "$file" "$entry" <<'PYEOF'
import sys
from pathlib import Path

path = Path(sys.argv[1])
entry = sys.argv[2]

lines = path.read_text().splitlines(keepends=True)
# Remove the entry line and any immediately preceding blank line added with it
new_lines = []
skip_next_blank = False
for i, line in enumerate(lines):
    stripped = line.rstrip("\n").rstrip("\r")
    if stripped == entry:
        # Also remove a preceding blank line if present
        if new_lines and new_lines[-1].strip() == "":
            new_lines.pop()
        print(f"  Removed '{entry}' from {path}")
        continue
    new_lines.append(line)

path.write_text("".join(new_lines))
PYEOF
}

# ---------------------------------------------------------------------------
# Global uninstall
# ---------------------------------------------------------------------------
if [[ -z "$PROJECT_DIR" ]]; then
    TRACER="$HOME/.claude/hooks/claude_code_tracer.py"
    CONFIG="$HOME/.claude/arthur_config.json"
    SETTINGS="$HOME/.claude/settings.json"

    echo "==> Removing hooks from $SETTINGS..."
    remove_hooks "$SETTINGS" 'python3 "$HOME/.claude/hooks/claude_code_tracer.py"'

    if [[ -f "$TRACER" ]]; then
        echo "==> Removing tracer at $TRACER..."
        rm "$TRACER"
        echo "  Removed $TRACER"
        # Remove hooks dir if now empty
        rmdir "$HOME/.claude/hooks" 2>/dev/null && echo "  Removed empty hooks dir" || true
    else
        echo "  Tracer not found at $TRACER — skipping"
    fi

    if [[ -f "$CONFIG" ]]; then
        echo "==> Removing $CONFIG..."
        rm "$CONFIG"
        echo "  Removed $CONFIG"
    else
        echo "  Config not found at $CONFIG — skipping"
    fi

    echo ""
    echo "Done! Restart Claude Code for changes to take effect."
    exit 0
fi

# ---------------------------------------------------------------------------
# Per-project uninstall
# ---------------------------------------------------------------------------
TRACER="$PROJECT_DIR/.claude/hooks/claude_code_tracer.py"
CONFIG="$PROJECT_DIR/.claude/arthur_config.json"
SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

echo "==> Removing hooks from $SETTINGS..."
remove_hooks "$SETTINGS" 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/claude_code_tracer.py"'

if [[ -f "$TRACER" ]]; then
    echo "==> Removing tracer at $TRACER..."
    rm "$TRACER"
    echo "  Removed $TRACER"
    rmdir "$PROJECT_DIR/.claude/hooks" 2>/dev/null && echo "  Removed empty hooks dir" || true
else
    echo "  Tracer not found at $TRACER — skipping"
fi

if [[ -f "$CONFIG" ]]; then
    echo "==> Removing $CONFIG..."
    rm "$CONFIG"
    echo "  Removed $CONFIG"
else
    echo "  Config not found at $CONFIG — skipping"
fi

echo "==> Cleaning up .gitignore..."
remove_gitignore_entry "$PROJECT_DIR/.gitignore" ".claude/arthur_config.json"

echo ""
echo "Done! Restart Claude Code for changes to take effect."

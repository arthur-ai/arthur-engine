#!/usr/bin/env bash
# Remove only the Arthur Codex hook tracer and its hook registrations.

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

if [[ -n "$PROJECT_DIR" ]]; then
    CODEX_ROOT="$PROJECT_DIR/.codex"
else
    CODEX_ROOT="$HOME/.codex"
fi

HOOK_DIR="$CODEX_ROOT/hooks"
TRACER_PATH="$HOOK_DIR/codex_hook_tracer.py"
HOOKS_FILE="$CODEX_ROOT/hooks.json"

if [[ -f "$HOOKS_FILE" ]]; then
    python3 - "$HOOKS_FILE" "$TRACER_PATH" <<'PY'
import json
import sys
from pathlib import Path

hooks_path = Path(sys.argv[1])
tracer_path = sys.argv[2]
try:
    settings = json.loads(hooks_path.read_text())
except (json.JSONDecodeError, OSError):
    raise SystemExit(0)

events = settings.get("hooks", {})
for event in list(events):
    retained_groups = []
    for group in events[event]:
        if not isinstance(group, dict):
            retained_groups.append(group)
            continue
        handlers = [
            handler
            for handler in group.get("hooks", [])
            if not (
                isinstance(handler, dict)
                and tracer_path in handler.get("command", "")
            )
        ]
        if handlers:
            retained = dict(group)
            retained["hooks"] = handlers
            retained_groups.append(retained)
    if retained_groups:
        events[event] = retained_groups
    else:
        del events[event]

hooks_path.write_text(json.dumps(settings, indent=2) + "\n")
PY
fi

rm -f "$TRACER_PATH"
rm -rf "$HOOK_DIR/.arthur-venv"
echo "Removed Arthur Codex tracer registrations from $HOOKS_FILE"

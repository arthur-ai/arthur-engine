#!/usr/bin/env bash
# Install the Arthur Codex hook tracer globally or into one trusted project.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
VENV_DIR="$HOOK_DIR/.arthur-venv"
TRACER_SOURCE="$SCRIPT_DIR/codex_hook_tracer.py"
TRACER_DEST="$HOOK_DIR/codex_hook_tracer.py"
HOOKS_FILE="$CODEX_ROOT/hooks.json"
PYTHON_COMMAND="${PYTHON_COMMAND:-python3}"

if [[ ! -f "$TRACER_SOURCE" ]]; then
    echo "Tracer not found: $TRACER_SOURCE" >&2
    exit 1
fi

mkdir -p "$HOOK_DIR"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    "$PYTHON_COMMAND" -m venv "$VENV_DIR"
fi

if [[ "${CODEX_OBSERVABILITY_SKIP_DEPENDENCIES:-0}" != "1" ]]; then
    "$VENV_DIR/bin/python" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi

cp "$TRACER_SOURCE" "$TRACER_DEST"
chmod 755 "$TRACER_DEST"

"$VENV_DIR/bin/python" - "$HOOKS_FILE" "$VENV_DIR/bin/python" "$TRACER_DEST" <<'PY'
import json
import shlex
import sys
from pathlib import Path

hooks_path = Path(sys.argv[1])
python_path = sys.argv[2]
tracer_path = sys.argv[3]
try:
    settings = json.loads(hooks_path.read_text()) if hooks_path.exists() else {}
except (json.JSONDecodeError, OSError):
    settings = {}

hooks = settings.setdefault("hooks", {})
for event, argument, matcher in (
    ("UserPromptSubmit", "user_prompt_submit", None),
    ("PreToolUse", "pre_tool", ""),
    ("PostToolUse", "post_tool", ""),
    ("Stop", "stop", None),
):
    command = " ".join(
        (
            "[",
            "-x",
            shlex.quote(python_path),
            "]",
            "&&",
            "[",
            "-f",
            shlex.quote(tracer_path),
            "]",
            "&&",
            shlex.quote(python_path),
            shlex.quote(tracer_path),
            argument + ";",
            "true",
        )
    )
    groups = hooks.setdefault(event, [])
    retained_groups = []
    for group in groups:
        if not isinstance(group, dict):
            retained_groups.append(group)
            continue
        retained_handlers = [
            handler
            for handler in group.get("hooks", [])
            if not (
                isinstance(handler, dict)
                and tracer_path in handler.get("command", "")
            )
        ]
        if retained_handlers:
            retained_group = dict(group)
            retained_group["hooks"] = retained_handlers
            retained_groups.append(retained_group)
    group = {
        "hooks": [
            {"type": "command", "command": command, "timeout": 5}
        ]
    }
    if matcher is not None:
        group["matcher"] = matcher
    retained_groups.append(group)
    hooks[event] = retained_groups

hooks_path.parent.mkdir(parents=True, exist_ok=True)
hooks_path.write_text(json.dumps(settings, indent=2) + "\n")
PY

ENV_FILE="$SCRIPT_DIR/.env"
if [[ -n "$PROJECT_DIR" && -f "$PROJECT_DIR/.env" ]]; then
    ENV_FILE="$PROJECT_DIR/.env"
fi
if [[ -n "${GENAI_ENGINE_API_KEY:-}" && -n "${GENAI_ENGINE_TASK_ID:-}" && -n "${GENAI_ENGINE_TRACE_ENDPOINT:-}" ]]; then
    "$VENV_DIR/bin/python" - "$CODEX_ROOT/arthur_config.json" <<'PY'
import json
import os
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
config = {
    "api_key": os.environ["GENAI_ENGINE_API_KEY"],
    "task_id": os.environ["GENAI_ENGINE_TASK_ID"],
    "endpoint": os.environ["GENAI_ENGINE_TRACE_ENDPOINT"],
}
output_path.write_text(json.dumps(config, indent=2) + "\n")
output_path.chmod(0o600)
PY
elif [[ -f "$ENV_FILE" ]]; then
    "$VENV_DIR/bin/python" - "$CODEX_ROOT/arthur_config.json" "$ENV_FILE" <<'PY'
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
env_path = Path(sys.argv[2])
values = {}
for raw_line in env_path.read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip("'\"")

config = {
    "api_key": values.get("GENAI_ENGINE_API_KEY", ""),
    "task_id": values.get("GENAI_ENGINE_TASK_ID", ""),
    "endpoint": values.get("GENAI_ENGINE_TRACE_ENDPOINT", ""),
}
if all(config.values()):
    output_path.write_text(json.dumps(config, indent=2) + "\n")
    output_path.chmod(0o600)
else:
    print("Arthur .env is incomplete; config was not written", file=sys.stderr)
PY
fi

if [[ -n "$PROJECT_DIR" ]]; then
    GITIGNORE="$PROJECT_DIR/.gitignore"
    if [[ ! -f "$GITIGNORE" ]] || ! grep -qF '.codex/arthur_config.json' "$GITIGNORE"; then
        printf '\n.codex/arthur_config.json\n' >> "$GITIGNORE"
    fi
fi

echo "Installed Codex tracer: $TRACER_DEST"
echo "Registered lifecycle hooks: $HOOKS_FILE"
echo "Review and trust the new hook definition with /hooks, then restart Codex."

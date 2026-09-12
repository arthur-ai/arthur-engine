"""Black-box tests for the Codex observability installer and uninstaller."""

import json
import os
import subprocess
from pathlib import Path

INTEGRATION_DIR = Path(__file__).parent
EXAMPLE_ENDPOINT = "https://engine.example.com/api/v1/traces"


def _run(script: str, home: Path, extra_env=None):
    env = {
        **os.environ,
        "HOME": str(home),
        "CODEX_OBSERVABILITY_SKIP_DEPENDENCIES": "1",
        **(extra_env or {}),
    }
    return subprocess.run(
        ["bash", str(INTEGRATION_DIR / script)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_global_install_is_idempotent_and_preserves_existing_hooks(tmp_path):
    """Break caught: install duplicates or replaces another global Codex hook."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    hooks_path = codex_dir / "hooks.json"
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {"hooks": [{"type": "command", "command": "/usr/bin/true"}]}
                    ]
                }
            }
        )
    )

    first = _run("install.sh", tmp_path)
    second = _run("install.sh", tmp_path)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert (codex_dir / "hooks" / "codex_hook_tracer.py").is_file()
    assert (codex_dir / "hooks" / ".arthur-venv" / "bin" / "python").is_file()
    hooks = json.loads(hooks_path.read_text())["hooks"]
    assert hooks["SessionStart"][0]["hooks"][0]["command"] == "/usr/bin/true"
    for event in (
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "SubagentStart",
        "SubagentStop",
        "Stop",
    ):
        arthur_handlers = [
            hook
            for group in hooks[event]
            for hook in group.get("hooks", [])
            if "codex_hook_tracer.py" in hook.get("command", "")
        ]
        assert len(arthur_handlers) == 1
        assert arthur_handlers[0]["timeout"] == 5
        assert arthur_handlers[0]["command"].endswith("; true")


def test_reinstall_replaces_previous_arthur_handler_definition(tmp_path):
    """Break caught: an upgraded command is appended beside its stale definition."""
    codex_dir = tmp_path / ".codex"
    tracer_path = codex_dir / "hooks" / "codex_hook_tracer.py"
    codex_dir.mkdir()
    hooks_path = codex_dir / "hooks.json"
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": f"python3 {tracer_path} old-stop",
                                    "timeout": 600,
                                },
                                {"type": "command", "command": "/usr/bin/true"},
                            ]
                        }
                    ]
                }
            }
        )
    )

    result = _run("install.sh", tmp_path)

    assert result.returncode == 0, result.stderr
    stop_groups = json.loads(hooks_path.read_text())["hooks"]["Stop"]
    handlers = [hook for group in stop_groups for hook in group["hooks"]]
    arthur_handlers = [
        hook for hook in handlers if str(tracer_path) in hook.get("command", "")
    ]
    assert len(arthur_handlers) == 1
    assert arthur_handlers[0]["timeout"] == 5
    assert arthur_handlers[0]["command"].endswith(" stop; true")
    assert {hook["command"] for hook in handlers if hook not in arthur_handlers} == {
        "/usr/bin/true"
    }


def test_generated_commands_fail_open_for_crashing_or_missing_runtime(tmp_path):
    """Break caught: an auxiliary tracer failure prevents a Codex lifecycle event."""
    result = _run("install.sh", tmp_path)
    assert result.returncode == 0, result.stderr
    codex_dir = tmp_path / ".codex"
    hooks = json.loads((codex_dir / "hooks.json").read_text())["hooks"]
    command = next(
        hook["command"]
        for group in hooks["Stop"]
        for hook in group["hooks"]
        if "codex_hook_tracer.py" in hook.get("command", "")
    )
    tracer_path = codex_dir / "hooks" / "codex_hook_tracer.py"
    tracer_path.write_text("raise SystemExit(9)\n")

    crashed = subprocess.run(
        command,
        shell=True,
        executable="/bin/sh",
        input="{}",
        text=True,
        capture_output=True,
        check=False,
    )
    assert crashed.returncode == 0

    (codex_dir / "hooks" / ".arthur-venv" / "bin" / "python").unlink()
    missing = subprocess.run(
        command,
        shell=True,
        executable="/bin/sh",
        input="{}",
        text=True,
        capture_output=True,
        check=False,
    )
    assert missing.returncode == 0


def test_uninstall_removes_only_arthur_hook_commands(tmp_path):
    """Break caught: uninstall deletes another tool's Codex lifecycle hook."""
    installed = _run("install.sh", tmp_path)
    assert installed.returncode == 0, installed.stderr
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks = json.loads(hooks_path.read_text())
    hooks["hooks"]["Stop"][0]["hooks"].append(
        {"type": "command", "command": "/usr/bin/true"}
    )
    hooks_path.write_text(json.dumps(hooks))

    removed = _run("uninstall.sh", tmp_path)

    assert removed.returncode == 0, removed.stderr
    hooks = json.loads(hooks_path.read_text())["hooks"]
    assert hooks["Stop"][0]["hooks"] == [
        {"type": "command", "command": "/usr/bin/true"}
    ]
    serialized = json.dumps(hooks)
    assert "codex_hook_tracer.py" not in serialized
    assert not (tmp_path / ".codex" / "hooks" / "codex_hook_tracer.py").exists()


def test_install_writes_mode_0600_config_from_environment_without_echoing_key(tmp_path):
    """Break caught: safe non-file credentials are ignored or exposed in installer output."""
    result = _run(
        "install.sh",
        tmp_path,
        {
            "GENAI_ENGINE_API_KEY": "example-test-key",
            "GENAI_ENGINE_TASK_ID": "00000000-0000-0000-0000-000000000123",
            "GENAI_ENGINE_TRACE_ENDPOINT": EXAMPLE_ENDPOINT,
        },
    )

    assert result.returncode == 0, result.stderr
    assert "example-test-key" not in result.stdout + result.stderr
    config_path = tmp_path / ".codex" / "arthur_config.json"
    assert config_path.stat().st_mode & 0o777 == 0o600
    assert json.loads(config_path.read_text()) == {
        "api_key": "example-test-key",
        "task_id": "00000000-0000-0000-0000-000000000123",
        "endpoint": EXAMPLE_ENDPOINT,
    }

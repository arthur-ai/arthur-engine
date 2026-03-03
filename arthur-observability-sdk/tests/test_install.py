"""
Install + telemetry smoke tests.

These tests build the SDK wheel into a fresh venv, verify all imports work,
then confirm that OTLP spans actually reach an HTTP collector.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

SDK_ROOT = Path(__file__).parent.parent  # arthur-observability-sdk/


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def built_wheel() -> Path:
    """Build the SDK wheel and return its path."""
    result = subprocess.run(
        ["poetry", "build", "-q", "--format", "wheel"],
        cwd=SDK_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"poetry build failed:\n{result.stderr}"
    dist_dir = SDK_ROOT / "dist"
    wheels = sorted(dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    assert wheels, "No wheel found in dist/ after build"
    return wheels[0]


@pytest.fixture(scope="module")
def sdk_venv(built_wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a fresh venv and install the wheel (plus test extras)."""
    venv_dir = tmp_path_factory.mktemp("install_venv")
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
    )
    pip = venv_dir / "bin" / "pip"
    subprocess.run(
        [
            str(pip),
            "install",
            "-q",
            str(built_wheel),
            "openinference-instrumentation-openai",
            "openai",
        ],
        check=True,
        capture_output=True,
    )
    return venv_dir


@pytest.fixture()
def mock_server() -> Any:
    """
    Start an HTTPServer on a random free port that acts as:
      POST /v1/traces           → OTLP collector (records raw bodies)
      POST /v1/chat/completions → mock OpenAI API (returns fake completion JSON)
    """
    received: list[bytes] = []

    _FAKE_COMPLETION = json.dumps(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "pong"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        }
    ).encode()

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            if self.path == "/v1/traces":
                received.append(body)
                self.send_response(200)
                self.end_headers()
            elif self.path == "/v1/chat/completions":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(_FAKE_COMPLETION)))
                self.end_headers()
                self.wfile.write(_FAKE_COMPLETION)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args: Any) -> None:  # suppress access log noise
            pass

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield {"url": f"http://127.0.0.1:{port}", "received": received}

    server.shutdown()
    thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run(venv: Path, code: str, **kwargs: Any) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    python = venv / "bin" / "python"
    return subprocess.run(
        [str(python), "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=30,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_imports_in_fresh_venv(sdk_venv: Path) -> None:
    """All expected SDK imports work from the freshly installed wheel."""
    result = _run(
        sdk_venv,
        """
        from arthur_observability_sdk import Arthur
        import arthur_genai_client
        from arthur_genai_client.api_client import ApiClient
        from arthur_genai_client.configuration import Configuration
        from arthur_genai_client.api.prompts_api import PromptsApi
        from arthur_genai_client.models.variable_template_value import VariableTemplateValue
        import dateutil
        import urllib3
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        print("OK")
        """,
    )
    assert (
        result.returncode == 0
    ), f"imports failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    assert "OK" in result.stdout


def test_telemetry_reaches_collector(sdk_venv: Path, mock_server: dict) -> None:
    """OTLP HTTP export actually delivers a span to the mock collector."""
    url = mock_server["url"]
    result = _run(
        sdk_venv,
        f"""
        from arthur_observability_sdk import Arthur
        from opentelemetry import trace

        arthur = Arthur(
            service_name="smoke-test",
            otlp_endpoint="{url}/v1/traces",
        )
        tracer = trace.get_tracer("smoke")
        with tracer.start_as_current_span("test-span"):
            pass
        arthur.shutdown()
        print("OK")
        """,
    )
    assert (
        result.returncode == 0
    ), f"subprocess failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    assert mock_server["received"], "No OTLP data received by mock collector"


def test_openai_instrumentation_sends_span(sdk_venv: Path, mock_server: dict) -> None:
    """OpenAI instrumentation emits an LLM span that is OTLP-exported."""
    url = mock_server["url"]
    result = _run(
        sdk_venv,
        f"""
        from arthur_observability_sdk import Arthur
        import openai

        arthur = Arthur(
            service_name="smoke-openai",
            otlp_endpoint="{url}/v1/traces",
        )
        arthur.instrument_openai()
        client = openai.OpenAI(api_key="test", base_url="{url}/v1")
        client.chat.completions.create(
            model="gpt-4o",
            messages=[{{"role": "user", "content": "ping"}}],
        )
        arthur.shutdown()
        print("OK")
        """,
    )
    assert (
        result.returncode == 0
    ), f"subprocess failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    assert mock_server["received"], "No OTLP span received after OpenAI instrumentation"

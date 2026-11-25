"""The control API, served for real on a free port against a fake agent."""

import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

import pytest
import requests

from standalone import control
from standalone.agent import ConfigStatus, ScanState
from standalone.control import ControlServer, control_from_env

TOKEN = "t" * 40
STARTED = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def state(status: str = "waiting", config_name: str = "c") -> ScanState:
    return ScanState(
        source_id="src-1",
        source_name="vertex",
        vendor="gcp_vertex",
        config_name=config_name,
        status=status,  # type: ignore[arg-type]
        last_started_at=STARTED,
        next_due_at=None,
    )


class FakeAgent:
    def __init__(self) -> None:
        self.asked: list[tuple[str, Optional[str]]] = []
        self.applied = 0

    def config_status(self) -> ConfigStatus:
        return ConfigStatus(
            path="/etc/deckard/discovery.yaml",
            loaded_at=STARTED,
            error="Discovery config is invalid",
            restart_required=("schedule",),
        )

    def configured_scans(self) -> list[Any]:
        return []

    def apply_config_now(self) -> tuple[ConfigStatus, list[ScanState]]:
        self.applied += 1
        return self.config_status(), [state("running")]

    def scan_states(self) -> list[ScanState]:
        return [state("scheduled")]

    def run_now(self, source_id: str, config_name: Optional[str] = None) -> list[Any]:
        self.asked.append((source_id, config_name))
        return [state()] if source_id == "src-1" else []


@pytest.fixture
def fake() -> FakeAgent:
    return FakeAgent()


@pytest.fixture
def base(fake: FakeAgent) -> Iterator[str]:
    server = ControlServer(fake, TOKEN, host="127.0.0.1", port=0)  # type: ignore[arg-type]
    server.start()
    yield f"http://127.0.0.1:{server.port}"
    server.stop()


AUTH = {"Authorization": f"Bearer {TOKEN}"}


def test_lists_every_scan(base: str) -> None:
    response = requests.get(f"{base}/scans", headers=AUTH, timeout=5)

    assert response.status_code == 200
    assert response.json() == {
        "scans": [
            {
                "source_id": "src-1",
                "source_name": "vertex",
                "vendor": "gcp_vertex",
                "config_name": "c",
                "status": "scheduled",
                "last_started_at": "2026-01-01T12:00:00Z",
                "next_due_at": None,
            },
        ],
    }


def test_runs_a_source_now(base: str, fake: FakeAgent) -> None:
    response = requests.post(
        f"{base}/scans/run",
        headers=AUTH,
        json={"source_id": "src-1", "config_name": "c"},
        timeout=5,
    )

    assert response.status_code == 202
    assert response.json()["scans"][0]["status"] == "waiting"
    assert fake.asked == [("src-1", "c")]


def test_a_source_not_configured_is_not_found(base: str) -> None:
    response = requests.post(
        f"{base}/scans/run", headers=AUTH, json={"source_id": "other"}, timeout=5
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {},
        {"source_id": ""},
        {"source_id": 7},
        {"source_id": "x" * 201},
        {"source_id": "src-1", "config_name": ""},
    ],
)
def test_a_malformed_request_is_refused(base: str, fake: FakeAgent, body: Any) -> None:
    response = requests.post(f"{base}/scans/run", headers=AUTH, json=body, timeout=5)

    assert response.status_code == 400
    assert fake.asked == []


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer wrong"},
        {"Authorization": f"Basic {TOKEN}"},
        {"Authorization": f"Bearer {TOKEN}x"},
    ],
)
def test_every_route_needs_the_token(
    base: str, fake: FakeAgent, headers: dict[str, str]
) -> None:
    listed = requests.get(f"{base}/scans", headers=headers, timeout=5)
    ran = requests.post(
        f"{base}/scans/run", headers=headers, json={"source_id": "src-1"}, timeout=5
    )

    applied = requests.post(f"{base}/config/reload", headers=headers, timeout=5)

    assert (listed.status_code, ran.status_code, applied.status_code) == (401, 401, 401)
    assert "src-1" not in listed.text
    assert fake.asked == [] and fake.applied == 0


def test_off_without_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ML_ENGINE_CONTROL_TOKEN", raising=False)

    assert control_from_env(FakeAgent()) is None  # type: ignore[arg-type]


def test_on_with_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ML_ENGINE_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("ML_ENGINE_CONTROL_PORT", "7600")

    server = control_from_env(FakeAgent())  # type: ignore[arg-type]

    assert server is not None and (server.host, server.port) == ("0.0.0.0", 7600)


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("ML_ENGINE_CONTROL_TOKEN", "short", "at least 32 characters"),
        ("ML_ENGINE_CONTROL_PORT", "http", "must be a port number"),
        ("ML_ENGINE_CONTROL_PORT", "70000", "must be a port number"),
    ],
)
def test_a_bad_setting_stops_the_engine_naming_it_not_its_value(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str, message: str
) -> None:
    monkeypatch.setenv("ML_ENGINE_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv(variable, value)

    with pytest.raises(SystemExit) as stopped:
        control_from_env(FakeAgent())  # type: ignore[arg-type]

    assert message in str(stopped.value) and value not in str(stopped.value)


def test_reads_the_token_from_a_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "token"
    path.write_text(TOKEN + "\n")
    monkeypatch.delenv("ML_ENGINE_CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("ML_ENGINE_CONTROL_TOKEN_FILE", str(path))

    server = control_from_env(FakeAgent())  # type: ignore[arg-type]

    assert server is not None and server._token == TOKEN.encode()


@pytest.mark.parametrize(
    ("contents", "message"),
    [(None, "Cannot read"), ("", "is empty"), ("short", "at least 32 characters")],
)
def test_a_token_file_that_cannot_be_used_stops_the_engine(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    contents: Optional[str],
    message: str,
) -> None:
    path = tmp_path / "token"
    if contents is not None:
        path.write_text(contents)
    monkeypatch.delenv("ML_ENGINE_CONTROL_TOKEN", raising=False)
    monkeypatch.setenv("ML_ENGINE_CONTROL_TOKEN_FILE", str(path))

    with pytest.raises(SystemExit) as stopped:
        control_from_env(FakeAgent())  # type: ignore[arg-type]

    assert message in str(stopped.value)
    assert "short" not in str(stopped.value)


def test_a_token_and_a_token_file_are_refused_together(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ML_ENGINE_CONTROL_TOKEN", TOKEN)
    monkeypatch.setenv("ML_ENGINE_CONTROL_TOKEN_FILE", str(tmp_path / "token"))

    with pytest.raises(SystemExit, match="not both"):
        control_from_env(FakeAgent())  # type: ignore[arg-type]


def test_reports_the_config_it_runs(base: str) -> None:
    response = requests.get(f"{base}/config", headers=AUTH, timeout=5)

    assert response.json() == {
        "path": "/etc/deckard/discovery.yaml",
        "loaded_at": "2026-01-01T12:00:00Z",
        "error": "Discovery config is invalid",
        "restart_required": ["schedule"],
    }


def test_applies_the_config_now(base: str, fake: FakeAgent) -> None:
    response = requests.post(f"{base}/config/reload", headers=AUTH, timeout=5)

    assert response.status_code == 200
    assert fake.applied == 1
    body = response.json()
    assert body["config"]["error"] == "Discovery config is invalid"
    assert [s["status"] for s in body["scans"]] == ["running"]


def test_serves_each_vendors_form(base: str) -> None:
    response = requests.get(f"{base}/source-types", headers=AUTH, timeout=5)

    vendors = {entry["vendor"] for entry in response.json()["source_types"]}
    assert {"wiz", "jamf_pro", "local"} <= vendors


def test_tests_a_source(base: str, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    def fake(
        raw: Any, config_name: Any, configured: Any, keep: Any, validate_only: bool
    ) -> Any:
        seen.append((raw, config_name, keep, validate_only))
        return {"outcome": "succeeded"}

    monkeypatch.setattr(control, "try_source", fake)
    body = {"source": {"name": "w"}, "config_name": "c", "keep_secrets_from": "w"}

    response = requests.post(f"{base}/sources/test", headers=AUTH, json=body, timeout=5)

    assert response.status_code == 200 and response.json() == {"outcome": "succeeded"}
    assert seen == [({"name": "w"}, "c", "w", False)]


def test_a_scan_request_over_4_kb_is_refused(base: str, fake: FakeAgent) -> None:
    body = {"source_id": "src-1", "padding": "x" * 5000}

    response = requests.post(f"{base}/scans/run", headers=AUTH, json=body, timeout=5)

    assert response.status_code == 413
    assert fake.asked == []


def test_a_source_test_may_be_larger_than_a_scan_request(
    base: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(control, "try_source", lambda *a, **k: {"outcome": "succeeded"})
    body = {"source": {"name": "w", "key": "k" * 20_000}}

    response = requests.post(f"{base}/sources/test", headers=AUTH, json=body, timeout=5)

    assert response.status_code == 200


def test_a_source_that_cannot_be_tested_says_why(base: str) -> None:
    body = {"source": {"name": "w", "vendor": "no-such-vendor"}}

    response = requests.post(f"{base}/sources/test", headers=AUTH, json=body, timeout=5)

    assert response.status_code == 400
    assert "is not a discovery vendor" in response.json()["error"]


def test_an_idle_connection_is_closed(
    monkeypatch: pytest.MonkeyPatch, fake: FakeAgent
) -> None:
    monkeypatch.setattr(control._RequestHandler, "timeout", 0.2)
    server = ControlServer(fake, TOKEN, host="127.0.0.1", port=0)  # type: ignore[arg-type]
    server.start()
    try:
        with socket.create_connection(("127.0.0.1", server.port), timeout=5) as idle:
            assert idle.recv(1) == b""  # closed by the server, not timed out here
    finally:
        server.stop()

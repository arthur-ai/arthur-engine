"""The standalone `local` source: one machine's collector output, read from a folder.

Most tests write the folder by hand, in the shape the collector publishes. One runs the
real collector from `integrations/endpoint-ai-discovery` into a temporary folder and
reads it back, and is skipped where osquery or that tree is absent.
"""

import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import (
    EndpointAgentCreationSource,
    Platform,
    RunsOn,
)

from discovery import source_connectors, standalone_connectors
from discovery.endpoint.envelope import MAX_DECOMPRESSED_BYTES
from discovery.endpoint.local.connector import (
    INVENTORY_FILE,
    VENDOR,
    LocalConnector,
    LocalInventoryError,
)
from discovery.endpoint.local.machine import MACHINE_FILE
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)
from tests.fakes.catalog import agent, document

SCAN_AT = 1790100381
SCANNED = datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
LOG = logging.getLogger("discovery-test")
DEVICE_ID = "6F1A2B3C-0000-4000-8000-0123456789AB"
MACHINE = {"device_id": DEVICE_ID, "hostname": "nadia-mbp", "platform": "darwin"}
CATALOG = document(
    agent(
        "codex-cli",
        "Codex CLI",
        "Coding agent",
        platforms=["darwin", "linux"],
        npm=["@openai/codex"],
        binaries=["~/.local/bin/codex"],
    ),
)
ENDPOINT_TREE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "integrations"
    / "endpoint-ai-discovery"
)


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


def scan_row(branch: str, extra: str = "ok") -> dict[str, str]:
    return row("scan", branch, ver=str(SCAN_AT), extra=extra)


def config(query: str = CATALOG) -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id="src",
        name="this-machine",
        vendor=VENDOR,
        query=query,
        query_language="none",
        lookback_window_seconds=0,
    )


def folder(
    tmp_path: pathlib.Path,
    rows: Optional[list[dict[str, str]]] = None,
    *,
    machine: Any = MACHINE,
    inventory: Optional[str] = None,
) -> pathlib.Path:
    """A folder as the collector and its script leave it. `None` leaves a file out."""
    out = tmp_path / "local-scan"
    out.mkdir()
    if inventory is None and rows is not None:
        inventory = json.dumps(rows, separators=(",", ":"))
    if inventory is not None:
        (out / INVENTORY_FILE).write_text(inventory)
    if machine is not None:
        text = machine if isinstance(machine, str) else json.dumps(machine)
        (out / MACHINE_FILE).write_text(text)
    return out


def scan(
    inventory_dir: Any,
    connector: Optional[LocalConnector] = None,
    query: str = CATALOG,
    lookback_hours: int = 0,
) -> list[Any]:
    connector = connector or LocalConnector()
    fields = {} if inventory_dir is None else {"inventory_dir": str(inventory_dir)}
    batches = connector.scan(config(query), lookback_hours, {}, fields, LOG)
    return [record for batch in batches for record in batch]


# --- Registration --------------------------------------------------------------------


def test_local_is_a_standalone_source_and_not_a_platform_one() -> None:
    assert standalone_connectors()[VENDOR] is LocalConnector
    assert VENDOR not in source_connectors()


def test_local_has_no_secrets() -> None:
    assert LocalConnector.SENSITIVE_FIELDS == frozenset()


# --- What a scan publishes -----------------------------------------------------------


def test_a_scan_publishes_one_record_per_agent_on_the_machine(
    tmp_path: pathlib.Path,
) -> None:
    out = folder(
        tmp_path,
        [
            row("npm", "@openai/codex", ver="0.5.0"),
            row("file", "/Users/n/.local/bin/codex", loc="/Users/n/.local/bin/codex"),
            row("app", "com.example.notes"),
            scan_row("packages"),
            scan_row("filesystem"),
        ],
    )
    connector = LocalConnector()

    records = scan(out, connector)

    assert len(records) == 1, "two routes, one agent, one record"
    record = records[0]
    assert record.external_id == f"{DEVICE_ID}:codex-cli"
    assert record.name == "Codex CLI"
    assert record.last_seen == SCANNED, "dated by the scan, not by the read"
    assert record.runs_on is RunsOn.ENDPOINT
    assert record.platform is Platform.DARWIN
    source = record.creation_source
    assert isinstance(source, EndpointAgentCreationSource)
    assert source.vendor == "local"
    assert source.address.instance == DEVICE_ID
    assert source.observations.version == "0.5.0"
    assert source.observations.host_name == "nadia-mbp"
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (coverage.devices_read, coverage.devices_decoded) == (1, 1)


def test_a_machine_without_agents_publishes_nothing_and_counts_as_decoded(
    tmp_path: pathlib.Path,
) -> None:
    connector = LocalConnector()

    assert scan(folder(tmp_path, [row("app", "x"), scan_row("apps")]), connector) == []
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (coverage.devices_decoded, coverage.devices_unreadable) == (1, 0)


def test_the_shipped_catalog_is_used_when_the_query_is_empty(
    tmp_path: pathlib.Path,
) -> None:
    # Claude Code's npm package is in the vendored floor catalog.
    out = folder(tmp_path, [row("npm", "@anthropic-ai/claude-code"), scan_row("x")])

    assert [r.external_id for r in scan(out, query="")] == [f"{DEVICE_ID}:claude-code"]


def test_only_device_id_is_required_of_the_machine(tmp_path: pathlib.Path) -> None:
    out = folder(
        tmp_path,
        [row("npm", "@openai/codex"), scan_row("packages")],
        machine={"device_id": "a-linux-box"},
    )

    [record] = scan(out)

    assert record.external_id == "a-linux-box:codex-cli"
    assert record.platform is None
    assert record.creation_source.observations.host_name is None


# --- A Windows machine ---------------------------------------------------------------

WINDOWS_ID = "4C4C4544-0042-3510-8051-B4C04F4B4E32"
WINDSURF_KEY = "{5A8B7D94-9B5F-4D1F-93FC-5609F7159349}_is1"
CLAUDE_DESKTOP = r"C:\Program Files\WindowsApps\Claude_3.6556.2.0_x64__pzs8sxrjxfjjc"
# Rows as upstream's discovery-windows.sql writes them: a package family name, an Uninstall
# key named by its last segment, a home dot-directory, and the containers marker, which is
# the composed query's only scan row and so the only date the payload carries.
WINDOWS_ROWS = [
    row(
        "msix",
        "Claude_pzs8sxrjxfjjc",
        ver="3.6556.2.0",
        loc=CLAUDE_DESKTOP,
        extra="Anthropic",
    ),
    row(
        "uninstall",
        WINDSURF_KEY,
        ver="1.12.21",
        loc="HKEY_USERS\\S-1-5-21-1004336348-1177238915-682003330-1001\\Software\\"
        "Microsoft\\Windows\\CurrentVersion\\Uninstall\\" + WINDSURF_KEY,
        extra="Windsurf",
    ),
    row("file", "C:\\Users\\nadia\\.claude\\", loc="C:\\Users\\nadia\\.claude\\"),
    row(
        "scan",
        "containers",
        ver=str(SCAN_AT),
        loc="\\\\.\\pipe\\docker_engine",
        extra="unreadable:docker",
    ),
]


def test_a_windows_machine_is_read_with_its_platform(tmp_path: pathlib.Path) -> None:
    """Upstream's Windows query against the shipped catalog: the MSIX and Uninstall routes
    exist only there, and the containers marker is enough to date the scan."""
    out = folder(
        tmp_path,
        WINDOWS_ROWS,
        machine={
            "device_id": WINDOWS_ID,
            "hostname": "NADIA-LAPTOP",
            "platform": "windows",
            "os_version": "Microsoft Windows 11 Pro 10.0.26100",
        },
    )

    records = {r.external_id: r for r in scan(out, query="")}

    assert set(records) == {
        f"{WINDOWS_ID}:claude-desktop",
        f"{WINDOWS_ID}:windsurf",
        f"{WINDOWS_ID}:claude-code",
    }
    for record in records.values():
        assert record.platform is Platform.WINDOWS
        assert record.last_seen == SCANNED
        assert record.creation_source.observations.host_name == "NADIA-LAPTOP"
        assert (
            record.creation_source.observations.os_version
            == "Microsoft Windows 11 Pro 10.0.26100"
        )
    desktop = records[f"{WINDOWS_ID}:claude-desktop"].creation_source.observations
    assert (desktop.install_path, desktop.version) == (CLAUDE_DESKTOP, "3.6556.2.0")
    # An Uninstall key's loc is a registry key, which is not a path on disk.
    windsurf = records[f"{WINDOWS_ID}:windsurf"].creation_source.observations
    assert (windsurf.install_path, windsurf.version) == (None, "1.12.21")


# --- Staleness -----------------------------------------------------------------------


def test_a_scan_older_than_the_lookback_fails_rather_than_reading_current(
    tmp_path: pathlib.Path,
) -> None:
    out = folder(tmp_path, [row("npm", "@openai/codex"), scan_row("packages")])
    connector = LocalConnector(clock=lambda: SCANNED + timedelta(hours=48))

    with pytest.raises(LocalInventoryError, match="before this source's 24h lookback"):
        scan(out, connector, lookback_hours=24)

    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"not-reported-in-window": 1}
    assert coverage.devices_decoded == 0


def test_a_scan_inside_the_lookback_is_published(tmp_path: pathlib.Path) -> None:
    out = folder(tmp_path, [row("npm", "@openai/codex"), scan_row("packages")])
    connector = LocalConnector(clock=lambda: SCANNED + timedelta(hours=23))

    assert len(scan(out, connector, lookback_hours=24)) == 1


def test_no_lookback_publishes_a_scan_of_any_age(tmp_path: pathlib.Path) -> None:
    out = folder(tmp_path, [row("npm", "@openai/codex"), scan_row("packages")])
    connector = LocalConnector(clock=lambda: SCANNED + timedelta(days=365))

    [record] = scan(out, connector, lookback_hours=0)

    assert record.last_seen == SCANNED


def test_a_payload_with_no_scan_time_is_refused_rather_than_dated_to_the_read(
    tmp_path: pathlib.Path,
) -> None:
    connector = LocalConnector()

    with pytest.raises(LocalInventoryError, match="no-scan-time"):
        scan(folder(tmp_path, [row("npm", "@openai/codex")]), connector)

    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"no-scan-time": 1}


# --- The folder ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,message",
    [
        (None, "missing required field inventory_dir"),
        ("local-scan", "must be an absolute path"),
        ("/nonexistent/arthur-local-scan", "not a directory"),
    ],
)
def test_the_folder_must_be_given_absolute_and_exist(
    value: Optional[str],
    message: str,
) -> None:
    connector = LocalConnector()

    with pytest.raises(DiscoveryConfigurationError, match=message) as raised:
        scan(value, connector)

    assert failure_code(raised.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert connector.device_coverage() is None


def test_an_empty_folder_says_to_run_the_collector(tmp_path: pathlib.Path) -> None:
    connector = LocalConnector()

    with pytest.raises(DiscoveryConfigurationError, match="ARTHUR_OUT_DIR") as raised:
        scan(folder(tmp_path), connector)

    assert failure_code(raised.value) is DiscoveryErrorCode.NOT_CONFIGURED
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"never-reported": 1}
    assert [d.device_key for d in coverage.unreadable_devices] == [DEVICE_ID]


@pytest.mark.parametrize(
    "inventory",
    ["[\n\n", '{"kind": "app"}', '[{"kind": "app"}]'],
    ids=["truncated", "not-an-array", "row-without-id"],
)
def test_a_payload_that_does_not_decode_fails_rather_than_reading_clean(
    tmp_path: pathlib.Path,
    inventory: str,
) -> None:
    connector = LocalConnector()

    with pytest.raises(LocalInventoryError, match="could not be read") as raised:
        scan(folder(tmp_path, inventory=inventory), connector)

    assert failure_code(raised.value) is DiscoveryErrorCode.PROVIDER_ERROR
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"malformed": 1}


def test_an_oversized_payload_is_refused_without_reading_it_all(
    tmp_path: pathlib.Path,
) -> None:
    out = folder(tmp_path, inventory="[" + " " * MAX_DECOMPRESSED_BYTES + "]")

    with pytest.raises(LocalInventoryError, match="byte bound"):
        scan(out)


# --- machine.json --------------------------------------------------------------------


@pytest.mark.parametrize(
    "machine,message",
    [
        (None, "machine.json does not exist"),
        ("{not json", "not valid JSON"),
        ('["a"]', "must be a JSON object"),
        ({"hostname": "h"}, "has no device_id"),
        ({"device_id": "  "}, "has no device_id"),
        ({"device_id": 7}, "device_id must be a string"),
        ({"device_id": "d", "platform": "macos"}, "darwin, linux or windows"),
        ({"device_id": "d", "platform": "win32"}, "darwin, linux or windows"),
    ],
)
def test_a_machine_file_that_does_not_name_the_machine_fails_the_scan(
    tmp_path: pathlib.Path,
    machine: Any,
    message: str,
) -> None:
    out = folder(tmp_path, [scan_row("apps")], machine=machine)
    connector = LocalConnector()

    with pytest.raises(DiscoveryConfigurationError, match=message):
        scan(out, connector)

    assert connector.device_coverage() is None


# --- The collector it reads ----------------------------------------------------------


@pytest.mark.skipif(not ENDPOINT_TREE.is_dir(), reason="endpoint tree not present")
def test_the_collector_still_publishes_the_file_this_reads() -> None:
    """The file name is the collector's. A collector that stops publishing it, or
    renames it, leaves every local scan reading an empty folder."""
    driver = (ENDPOINT_TREE / "tools" / "build-collector.py").read_text()
    assert "for f in inventory.json status.txt inventory.ea; do" in driver


def _osqueryi() -> bool:
    return shutil.which("osqueryi") is not None or os.path.exists(
        "/opt/osquery/lib/osquery.app/Contents/MacOS/osqueryi",
    )


@pytest.mark.skipif(not ENDPOINT_TREE.is_dir(), reason="endpoint tree not present")
@pytest.mark.skipif(not _osqueryi(), reason="osquery is not installed")
@pytest.mark.skipif(
    sys.platform not in ("darwin", "linux"),
    reason="the collector is darwin and linux",
)
def test_the_real_collectors_output_reads_back(
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """What ships, run: the built collector writes the folder, and it decodes.

    No assertion about which agents are here -- that depends on the machine, and what a
    query finds is upstream's to test. This asserts that the collector's output is what
    this source reads: a payload that decodes, is dated, and counts this machine.
    """
    out = tmp_path / "local-scan"
    out.mkdir()
    collector = (
        ENDPOINT_TREE
        / "dist"
        / ("collect.sh" if sys.platform == "darwin" else "collect-linux.sh")
    )
    run = subprocess.run(
        ["bash", str(collector)],
        env={**os.environ, "ARTHUR_OUT_DIR": str(out), "TMPDIR": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert run.returncode == 0, run.stderr[-2000:]
    (out / MACHINE_FILE).write_text(json.dumps({"device_id": "real-collector"}))
    connector = LocalConnector()

    with caplog.at_level(logging.INFO):
        records = scan(out, connector, query="", lookback_hours=1)

    coverage = connector.device_coverage()
    assert coverage is not None
    assert (coverage.devices_read, coverage.devices_decoded) == (1, 1)
    assert all(r.external_id.startswith("real-collector:") for r in records)
    [summary] = [m for m in caplog.messages if m.startswith("Local scan from")]
    assert int(summary.split()[4]) > 0, "a real machine has at least its scan rows"

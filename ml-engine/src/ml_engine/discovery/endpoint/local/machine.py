"""`machine.json`: who the scanned machine is, as the script that scanned it says.

A carrier knows the device's id, name and OS from its own record. A folder has no
record, and the engine reading it is usually in a container, whose own machine id and
hostname belong to the container -- a new one each time it is recreated, which mints a
duplicate of every agent. So the script that ran the collector on the host writes the
host's identity beside the payload, and nothing here falls back to the engine's own.

    {"device_id": "8915B3AB-...", "hostname": "my-laptop", "platform": "darwin"}

`device_id` is required and is the left half of every `external_id`, so it must stay the
same while the machine does: macOS's platform UUID, Linux's `/etc/machine-id`, or
Windows' `MachineGuid`. Never the hostname, which follows the network on a laptop. The
rest is optional.
"""

import json
from pathlib import Path
from typing import Any, Optional

from arthur_common.models.agent_governance_schemas import Platform, RunsOn

from discovery.endpoint.device import ManagedDevice
from job_executors.discovery_scan import DiscoveryConfigurationError

MACHINE_FILE = "machine.json"

# A few short strings. Anything larger is not this file.
MAX_MACHINE_FILE_BYTES = 64 * 1024

DEVICE_ID_KEY = "device_id"
HOSTNAME_KEY = "hostname"
PLATFORM_KEY = "platform"
OS_VERSION_KEY = "os_version"


def read_machine(folder: Path) -> ManagedDevice:
    """The device every record from this folder is addressed to."""
    path = folder / MACHINE_FILE
    try:
        with path.open("rb") as f:
            raw = f.read(MAX_MACHINE_FILE_BYTES + 1)
    except FileNotFoundError:
        raise DiscoveryConfigurationError(
            f"{path} does not exist. The script that ran the collector writes it beside "
            f"the inventory, naming the machine it scanned; without it the scan cannot "
            f"say which machine the agents are on.",
        ) from None
    except OSError as e:
        raise DiscoveryConfigurationError(
            f"Cannot read {path}: {e.strerror}",
        ) from None
    if len(raw) > MAX_MACHINE_FILE_BYTES:
        raise DiscoveryConfigurationError(
            f"{path} is larger than {MAX_MACHINE_FILE_BYTES} bytes",
        )
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
        raise DiscoveryConfigurationError(f"{path} is not valid JSON") from None
    if not isinstance(doc, dict):
        raise DiscoveryConfigurationError(f"{path} must be a JSON object")

    device_id = _string(doc, DEVICE_ID_KEY, path)
    if not device_id:
        raise DiscoveryConfigurationError(
            f"{path} has no {DEVICE_ID_KEY}: the machine's stable id, its platform UUID "
            f"on macOS, /etc/machine-id on Linux, or MachineGuid on Windows",
        )
    return ManagedDevice(
        device_key=device_id,
        name=_string(doc, HOSTNAME_KEY, path),
        os_version=_string(doc, OS_VERSION_KEY, path),
        platform=_platform(_string(doc, PLATFORM_KEY, path), path),
        # The machine someone ran the script on, which is the one in front of them.
        runs_on=RunsOn.ENDPOINT,
    )


def _string(doc: dict[str, Any], key: str, path: Path) -> Optional[str]:
    value = doc.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise DiscoveryConfigurationError(f"{path}: {key} must be a string")
    return value.strip() or None


def _platform(value: Optional[str], path: Path) -> Optional[Platform]:
    """darwin, linux or windows, the three a scan is built for; absent is allowed, a
    misspelling is not, since it would land the agent under no platform filter."""
    if value is None:
        return None
    try:
        platform = Platform(value.lower())
    except ValueError:
        platform = None
    if platform not in (Platform.DARWIN, Platform.LINUX, Platform.WINDOWS):
        raise DiscoveryConfigurationError(
            f"{path}: {PLATFORM_KEY} must be darwin, linux or windows",
        )
    return platform

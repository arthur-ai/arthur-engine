"""One machine's inventory, read from a folder: standalone engines only.

Arthur's endpoint collector (`integrations/endpoint-ai-discovery`, `dist/collect.sh` on a
Mac, `dist/collect-linux.sh` on Linux) writes its scan into `$ARTHUR_OUT_DIR`. On Windows,
which has no collector, the same rows come from upstream's `dist/discovery-windows.sql`
run through osqueryi. Every other endpoint source reads that scan after a carrier has
brought it back -- a Jamf attribute, a guest attribute, SSM inventory. This one reads the
folder itself, mounted into the engine, so a person can scan their own machine and see
what it finds without an MDM or a cloud. The rows go to `discovery.endpoint.records`, so
matching, dating and addressing are the same as for a Mac a Jamf scan read.

THE FOLDER IS A CONTRACT WITH WHATEVER FILLS IT, and it holds two files:

    inventory.json   the collector's readable payload: the evidence rows, unframed
    machine.json     who the machine is -- see `machine`

`inventory.json` and not `inventory.ea`: the framed value is sized for a carrier's
attribute, and over that budget the collector writes `ERROR:oversize` in its place. A
folder has no such limit, and the readable payload is published beside it whenever a
scan succeeds.

NOT A PLATFORM SOURCE. A Platform-dispatched engine has no folder anyone filled for it,
and the Platform has no vendor for this. It is registered in
`discovery.standalone_connectors()` only.

ONE MACHINE, SO ONE FAILURE IS THE SCAN'S. Where a fleet scan counts an unreadable
device and reads on, here the device is the whole scope: an empty folder, a payload that
does not decode, or one older than the lookback fails the scan with the reason, rather
than succeeding with nothing -- which a destination reads as a machine without agents.

A FAILED RE-SCAN LEAVES THE LAST GOOD ONE IN PLACE. The collector keeps its previous
payload when a run cannot collect, so the folder never says whether the latest run
worked. The payload dates itself, so the records are dated by when the machine was
scanned, never by when this read it, and a lookback bounds how old a scan may be and
still be published.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.catalog import Matcher
from discovery.cloud.vm_inventory import NOT_REPORTED_IN_WINDOW
from discovery.endpoint.envelope import MAX_DECOMPRESSED_BYTES, read_document
from discovery.endpoint.local.machine import read_machine
from discovery.endpoint.records import UnreadableReason, records_from_rows
from job_executors.discovery_scan import DeviceCoverage, DiscoveryConfigurationError

VENDOR = "local"

# Non-sensitive source field, required: the folder the collector wrote into.
INVENTORY_DIR_FIELD = "inventory_dir"

INVENTORY_FILE = "inventory.json"


class LocalInventoryError(RuntimeError):
    """The folder held a scan this source cannot use: the collector's, not the config's."""


class LocalConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `ReportsDeviceCoverage`.

    Holds one scan's coverage, which is safe only because a connector is built fresh for
    every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._coverage: Optional[DeviceCoverage] = None
        self._clock = clock

    def device_coverage(self) -> Optional[DeviceCoverage]:
        """None if the scan failed before it knew which machine the folder is."""
        return self._coverage

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """A lookback of zero or less publishes the folder's scan however old it is."""
        folder = _folder_from(source_fields)
        device = read_machine(folder)
        matcher = Matcher.from_source(
            catalog_json=config.query or None,
            logger=logger,
        )
        logger.info(
            "Local scan reading %s for %s (%s), catalog %s, %s agent(s)",
            folder,
            device.name,
            device.device_key,
            matcher.catalog_sha,
            matcher.agent_count,
        )

        coverage = self._coverage = DeviceCoverage(devices_read=1, devices_in_scope=1)

        def unreadable(reason: str, error: Exception) -> Exception:
            coverage.count_unreadable(reason, device.unreadable(reason))
            return error

        payload = _read_payload(folder / INVENTORY_FILE)
        if payload is None:
            raise unreadable(
                UnreadableReason.NEVER_REPORTED.value,
                DiscoveryConfigurationError(
                    f"{folder / INVENTORY_FILE} does not exist: the collector has not "
                    f"written a scan into {folder}, or its first run failed. Run it "
                    f"with ARTHUR_OUT_DIR set to this folder.",
                ),
            )
        envelope = read_document(payload)
        if not envelope.ok:
            raise unreadable(
                UnreadableReason.MALFORMED.value,
                LocalInventoryError(
                    f"{folder / INVENTORY_FILE} could not be read: {envelope.detail}",
                ),
            )
        read = records_from_rows(
            device,
            envelope.rows,
            matcher,
            VENDOR,
            logger,
            ignored=envelope.ignored,
        )
        if read.unreadable is not None:
            raise unreadable(
                read.unreadable.value,
                LocalInventoryError(
                    f"{folder / INVENTORY_FILE} could not be used "
                    f"({read.unreadable.value})",
                ),
            )

        # records_from_rows dates every decoded payload; a device with no report date
        # and no scan row is the NO_SCAN_TIME refusal above.
        assert read.last_seen is not None
        if lookback_hours > 0:
            since = self._clock() - timedelta(hours=lookback_hours)
            if read.last_seen < since:
                raise unreadable(
                    NOT_REPORTED_IN_WINDOW,
                    LocalInventoryError(
                        f"The scan in {folder} was taken {read.last_seen.isoformat()}, "
                        f"before this source's {lookback_hours}h lookback. Run the "
                        f"collector again to refresh it.",
                    ),
                )

        coverage.devices_decoded = 1
        logger.info(
            "Local scan from %s: %s row(s), %s agent(s)",
            read.last_seen.isoformat(),
            len(envelope.rows),
            len(read.records),
        )
        if read.records:
            yield read.records


def _folder_from(source_fields: Mapping[str, str]) -> Path:
    """The folder, absolute, because a relative path would resolve against wherever the
    engine happened to start, which in a container is nowhere anyone mounted."""
    value = (source_fields.get(INVENTORY_DIR_FIELD) or "").strip()
    if not value:
        raise DiscoveryConfigurationError(
            f"Local source is missing required field {INVENTORY_DIR_FIELD}: the folder "
            f"the endpoint collector wrote its scan into.",
        )
    folder = Path(value)
    if not folder.is_absolute():
        raise DiscoveryConfigurationError(
            f"Local source's {INVENTORY_DIR_FIELD} must be an absolute path",
        )
    if not folder.is_dir():
        raise DiscoveryConfigurationError(
            f"Local source's {INVENTORY_DIR_FIELD} {folder} is not a directory this "
            f"engine can see. In a container, mount the collector's folder there.",
        )
    return folder


def _read_payload(path: Path) -> Optional[bytes]:
    """The file's bytes, None if it is absent, and at most one byte past the bound so
    `read_document` refuses an oversized file without it all being read."""
    try:
        with path.open("rb") as f:
            return f.read(MAX_DECOMPRESSED_BYTES + 1)
    except FileNotFoundError:
        return None
    except OSError as e:
        raise LocalInventoryError(f"Cannot read {path}: {e.strerror}") from None

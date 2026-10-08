"""Staged connectors for the A&G vision demo (UP-5124). DEMO BRANCH ONLY.

CrowdStrike Falcon, Google SecOps and Compute Engine (osquery) have no live connector
yet (D-20, D-30, D-32/D-33). These return what each would report about a staged fleet,
so a scan against those sources completes instead of failing with `unsupported_vendor`.

The records come from a JSON file named by `ARTHUR_ENGINE_STAGED_DISCOVERY_RECORDS`,
written by arthur-scope's `demos/ag_discovery_demo/seed.py export-records`:

    {"generated_at": "<iso>", "records": {"<vendor>": [<DiscoveredAgentRecord>, ...]}}

A record whose `last_seen` is the file's `generated_at` is restamped to now, so the
staged fleet stays fresh however old the file is. Any other `last_seen` is a one-off
sighting and is kept as it is.

Every record carries `observations.service_names` = "<vm>/<finding>", so GenAI Engine's
resolver lands the three sources' records for one finding on one task.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from job_executors.discovery_scan import DiscoveryConfigurationError

STAGED_RECORDS_ENV_VAR = "ARTHUR_ENGINE_STAGED_DISCOVERY_RECORDS"

FALCON_VENDOR = "crowdstrike_falcon"
SECOPS_VENDOR = "google_secops"
COMPUTE_ENGINE_VENDOR = "gcp_compute_engine"
STAGED_VENDORS = (FALCON_VENDOR, SECOPS_VENDOR, COMPUTE_ENGINE_VENDOR)

BATCH_SIZE = 100


def load_staged_records(path: Path) -> dict[str, Any]:
    with open(path) as f:
        staged: dict[str, Any] = json.load(f)
    return staged


def staged_records_for(
    staged: Mapping[str, Any],
    vendor: str,
    now: datetime,
) -> list[DiscoveredAgentRecord]:
    generated_at = staged.get("generated_at")
    records = []
    for raw in staged["records"].get(vendor, []):
        record = dict(raw)
        if record.get("last_seen") == generated_at:
            record["last_seen"] = now.isoformat()
        records.append(DiscoveredAgentRecord.model_validate(record))
    return records


class StagedConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`."""

    vendor: str

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        path = self._path or _path_from_env()
        records = staged_records_for(
            load_staged_records(path),
            self.vendor,
            datetime.now(timezone.utc),
        )
        logger.info(
            "%s: staged demo connector returning %s record(s) from %s",
            self.vendor,
            len(records),
            path.name,
        )
        for start in range(0, len(records), BATCH_SIZE):
            yield records[start : start + BATCH_SIZE]


def _path_from_env() -> Path:
    value = os.environ.get(STAGED_RECORDS_ENV_VAR)
    if not value:
        raise DiscoveryConfigurationError(
            f"this engine has no staged records: set {STAGED_RECORDS_ENV_VAR} to the "
            "file `seed.py export-records` wrote",
        )
    path = Path(value).expanduser()
    if not path.is_file():
        raise DiscoveryConfigurationError(
            f"{STAGED_RECORDS_ENV_VAR} names {path}, which is not a file"
        )
    return path


class StagedFalconConnector(StagedConnector):
    vendor = FALCON_VENDOR


class StagedSecOpsConnector(StagedConnector):
    vendor = SECOPS_VENDOR


class StagedComputeEngineConnector(StagedConnector):
    vendor = COMPUTE_ENGINE_VENDOR

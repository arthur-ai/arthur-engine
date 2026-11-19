"""What a dashboard needs to add a source to a standalone engine's config: each vendor's
form, and Test Connection.

THE FORMS ARE THE PLATFORM'S. Each vendor's fields -- names, descriptions, which are
secret, which are optional -- are the Platform's discovery source types, snapshotted
into `source_types.json` by `scripts/snapshot_discovery_source_types.py` for the vendors
this engine has a connector for, so a dashboard renders the same form the Platform does.

A TEST TAKES VALUES, NEVER REFERENCES. The source it is given is validated as a config
file's source is, but nothing in it is read as `${NAME}` or `{file: path}`, so a caller
can only test with credentials it already holds -- never point a test at a host of its
choosing with one of this engine's secrets. The one exception is asked for by name: a
secret left out may be taken from the configured source of that name and vendor, which
is what a form editing that source does when its secrets are left as they were.
"""

import json
import logging
from functools import cache
from pathlib import Path
from typing import Any, Optional

from discovery import standalone_connectors
from job_executors.discovery_source_test_executor import preview_source
from standalone.discovery_config import (
    ResolvedScan,
    StandaloneConfigError,
    resolve_source,
    sensitive_fields,
    source_from_values,
)

SOURCE_TYPES_FILE = Path(__file__).with_name("source_types.json")
# Rows a test shows: enough to see the source answered with agents in it.
PREVIEW_LIMIT = 20


@cache
def source_types() -> list[dict[str, Any]]:
    """Every vendor this engine can scan, with its form, by display name."""
    snapshot = json.loads(SOURCE_TYPES_FILE.read_text(encoding="utf-8"))
    available = standalone_connectors().keys()
    return sorted(
        (
            entry
            for vendor, entry in snapshot["source_types"].items()
            if vendor in available
        ),
        key=lambda entry: str(entry["display_name"]).lower(),
    )


def try_source(
    raw: Any,
    config_name: Optional[str],
    configured: list[ResolvedScan],
    keep_secrets_from: Optional[str] = None,
    validate_only: bool = False,
) -> dict[str, Any]:
    """Run Test Connection on `raw`, a source as a config file's `sources` entry holds
    one but with plain values, and return its result as JSON.

    `keep_secrets_from` names a configured source of the same vendor whose credentials
    fill the secret fields `raw` leaves out. With `validate_only`, the source is checked
    as a config file's would be and no connector runs. Raises StandaloneConfigError when the source
    cannot be tested as given.
    """
    if not isinstance(raw, dict):
        raise StandaloneConfigError("The source must be a JSON object")
    raw = {**raw, "fields": list(raw.get("fields") or [])}
    vendor = raw.get("vendor")
    if keep_secrets_from is not None:
        kept = next(
            (
                scan
                for scan in configured
                if scan.source_name == keep_secrets_from
                and scan.config.vendor == vendor
            ),
            None,
        )
        if kept is None:
            raise StandaloneConfigError(
                f"No configured {vendor} source is named '{keep_secrets_from}'",
            )
        given = {
            f.get("key")
            for f in raw["fields"]
            if isinstance(f, dict) and f.get("value") not in (None, "")
        }
        raw["fields"] = [
            f
            for f in raw["fields"]
            if not (isinstance(f, dict) and f.get("value") in (None, ""))
        ] + [
            {"key": key, "value": value}
            for key, value in kept.credentials.items()
            if key not in given and value is not None
        ]
    source = source_from_values(raw)
    scans = resolve_source(source)
    if config_name is not None:
        scans = [scan for scan in scans if scan.config.name == config_name]
        if not scans:
            raise StandaloneConfigError(f"The source has no config '{config_name}'")
    if validate_only:
        return {"outcome": "valid"}
    scan = scans[0]
    logger = logging.getLogger(f"standalone.test.{scan.source_name}")
    result = preview_source(
        scan.config,
        scan.lookback_hours,
        scan.credentials,
        logger,
        preview_limit=PREVIEW_LIMIT,
        connectors=standalone_connectors(),
    )
    return {
        "secret_fields": sorted(sensitive_fields(source.vendor) or ()),
        **result.model_dump(mode="json"),
    }

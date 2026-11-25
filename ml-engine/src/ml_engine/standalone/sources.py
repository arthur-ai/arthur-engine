"""What a dashboard needs to add a source to a standalone engine's config: each vendor's
form, and Test Connection.

THE FORMS ARE THE PLATFORM'S. Each vendor's fields -- names, descriptions, which are
secret, which are optional -- are the Platform's discovery source types, snapshotted
into `source_types.json` by `scripts/snapshot_discovery_source_types.py` for the vendors
this engine has a connector for, so a dashboard renders the same form the Platform does.

A TEST TAKES VALUES, NEVER REFERENCES. The source it is given is validated as a config
file's source is, but nothing in it is read as `${NAME}` or `{file: path}`, so a caller
can only test with credentials it already holds -- never point a test at a host of its
choosing with one of this engine's secrets.

THE ONE EXCEPTION IS ASKED FOR BY NAME, AND KEPT WHERE IT WAS SENT. `keep_secrets_from`
names a configured source of the same vendor: a secret the test leaves blank takes that
source's value, and so does any field given as null, which is what a form editing that
source does with what it was not shown or did not change. A kept secret goes only where
the configured source sends it: when a field that decides that -- a URL, a CA, whether
TLS is checked (`SECRET_DESTINATION_FIELDS`) -- differs, the test is refused until the
secret is given again.

A SOURCE WITH NO SECRETS MAY RUN AS THE ENGINE ITSELF. Where the operator opts in, a
cloud connector given no key uses the engine's own identity, and with it assumes the
`role_arn` the source names. So a test with none of its vendor's secrets runs only when
a configured source of that vendor has none either and the same settings: the operator
chose that one. Anything else is saved and scanned, or tested with keys.
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

# For each vendor, the fields that decide where its connector sends its secrets, or
# whether it trusts the host it sends them to. A vendor whose secrets only ever go to its
# own fixed endpoints has none. Every connector is listed (a test checks); one missing
# here is treated as if every field it has decided that.
SECRET_DESTINATION_FIELDS: dict[str, frozenset[str]] = {
    "aws_bedrock": frozenset(),
    "aws_containers": frozenset(),
    "aws_ec2": frozenset(),
    "aws_network": frozenset(),
    # The token is acquired from the tenant's authority and sent to the project.
    "azure_ai_foundry": frozenset({"project_endpoint", "tenant_id"}),
    "elastic_security": frozenset(
        {"elasticsearch_url", "ca_certificate", "tls_verification"}
    ),
    "gcp_compute_engine": frozenset(),
    "gcp_containers": frozenset(),
    "gcp_network": frozenset(),
    "gcp_vertex": frozenset(),
    "jamf_pro": frozenset({"base_url"}),
    "litellm": frozenset({"base_url", "ca_certificate", "tls_verification"}),
    "local": frozenset(),
    "splunk_enterprise": frozenset({"base_url", "ca_certificate", "tls_verification"}),
    "vercel_ai": frozenset(),
    "wiz": frozenset({"api_endpoint_url", "auth_environment"}),
}


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

    `keep_secrets_from` names a configured source of the same vendor whose values fill
    the secrets `raw` leaves blank and the fields it gives as null. With `validate_only`,
    the source is checked as a config file's would be and no connector runs. Raises
    StandaloneConfigError when the source cannot be tested as given.
    """
    if not isinstance(raw, dict):
        raise StandaloneConfigError("The source must be a JSON object")
    fields = raw.get("fields")
    fields = [] if fields is None else fields
    # Checked before the secrets are merged in, which reads each field's key.
    if not isinstance(fields, list) or not all(
        isinstance(f, dict) and isinstance(f.get("key"), str) for f in fields
    ):
        raise StandaloneConfigError(
            "The source's fields must be a list of {key, value} objects",
        )
    raw = {**raw, "fields": list(fields)}
    if keep_secrets_from is not None:
        raw["fields"] = _keep(raw, configured, keep_secrets_from)
    source = source_from_values(raw)
    scans = resolve_source(source)
    if config_name is not None:
        scans = [scan for scan in scans if scan.config.name == config_name]
        if not scans:
            raise StandaloneConfigError(f"The source has no config '{config_name}'")
    if validate_only:
        return {"outcome": "valid"}
    scan = scans[0]
    _refuse_keyless(scan, configured)
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


def _keep(
    raw: dict[str, Any],
    configured: list[ResolvedScan],
    name: str,
) -> list[dict[str, Any]]:
    """`raw`'s fields with the named configured source's values in its blank secrets and
    its null fields, or raise if a kept secret would go somewhere that source's doesn't.
    """
    vendor = raw.get("vendor")
    kept = next(
        (s for s in configured if s.source_name == name and s.config.vendor == vendor),
        None,
    )
    if kept is None:
        raise StandaloneConfigError(f"No configured {vendor} source is named '{name}'")
    secret_keys = sensitive_fields(str(vendor)) or frozenset()
    fields: list[dict[str, Any]] = []
    for f in raw["fields"]:
        key, value = f["key"], f.get("value")
        if key in secret_keys and value in (None, ""):
            continue  # filled below
        if value is None:
            if _filled(kept.source_fields.get(key)):
                fields.append({"key": key, "value": kept.source_fields[key]})
            continue
        if value == "":
            continue
        fields.append(f)
    given = {f["key"] for f in fields}
    taken = sorted(
        key
        for key, value in kept.credentials.items()
        if key not in given and _filled(value)
    )
    if taken:
        now = {f["key"]: f.get("value") for f in fields if f["key"] not in secret_keys}
        before = kept.source_fields
        deciding = SECRET_DESTINATION_FIELDS.get(
            str(vendor), now.keys() | before.keys()
        )
        changed = sorted(
            k for k in deciding if _text(now.get(k)) != _text(before.get(k))
        )
        if changed:
            raise StandaloneConfigError(
                f"{', '.join(changed)} changed, so the configured "
                f"{', '.join(taken)} is not sent to it: enter {', '.join(taken)} "
                f"again",
            )
    return fields + [{"key": key, "value": kept.credentials[key]} for key in taken]


def _refuse_keyless(scan: ResolvedScan, configured: list[ResolvedScan]) -> None:
    """Refuse a test with none of its vendor's secrets unless the operator configured a
    source just like it, since without them a connector may run as the engine itself."""
    vendor = scan.config.vendor
    secret_keys = sensitive_fields(vendor) or frozenset()
    if not secret_keys or any(_filled(v) for v in scan.credentials.values()):
        return
    settings = _settings(scan.source_fields)
    if any(
        c.config.vendor == vendor
        and not any(_filled(v) for v in c.credentials.values())
        and _settings(c.source_fields) == settings
        for c in configured
    ):
        return
    raise StandaloneConfigError(
        f"This source has none of {', '.join(sorted(secret_keys))}, so it would run as "
        f"this engine's own identity, which a test may use only for a source configured "
        f"that way already. Enter its credentials to test it, or save it and use Scan now",
    )


def _filled(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _settings(fields: dict[str, str]) -> dict[str, str]:
    return {k: _text(v) for k, v in fields.items() if _filled(v)}

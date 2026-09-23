"""Turning one device's payload into findings. Nothing here knows which MDM.

Finds the `arthur1.` payload among a device's attributes, matches the rows against the
catalog, and emits one record per (device, agent). An MDM package supplies the device and
the vendor tag.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    EndpointAgentCreationSource,
    SourceAddress,
)

from discovery.catalog import Finding, Matcher
from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.envelope import (
    FRAME_PREFIX,
    NO_CACHE,
    OVERSIZE_PREFIX,
    EnvelopeOutcome,
    read,
)

# `loc` and `ver` mean different things per kind, and two of those meanings are not what
# `AgentObservations` names. Measured on a real Mac: aider matched through `images`, whose
# `loc` is the image digest -- reported as `install_path`, that is a filesystem path that
# exists nowhere. `container` is worse in the other column: its `ver` is the container
# STATE ("running"), so a version field would read "running" as though it were one.
#
# Listed as what DOES carry each meaning rather than what does not, so a kind added
# upstream is absent until someone says otherwise rather than silently mis-mapped.
PATH_IN_LOC = frozenset(
    {
        "app",
        "brew",
        "daemon",
        "ext",
        "nmh",
        "npm",
        "file",
        "vscodeext",
        "port",
        "desktop",
        "unit",
    },
)
VERSION_IN_VER = frozenset({"app", "brew", "ext", "npm", "vscodeext", "deb", "rpm"})


def _inventory_value(
    device: ManagedDevice,
    log: logging.Logger,
) -> tuple[Optional[str], Optional[str]]:
    """The device's payload, found by the payload's own prefix.

    WHAT THE ADMIN CALLED THE ATTRIBUTE IS NOT AN INPUT. `arthur1.` is a magic prefix so
    that a reader can recognize the value without being told where to look; requiring the
    display name as well would mean the format identifies itself and we ask anyway. A
    fleet that renames its attributes keeps working, and no vendor schema carries a field
    for it.

    `no-cache` cannot identify the payload -- the status attribute carries the same
    sentinel, so a device in that state matches twice -- and an unpopulated attribute
    carries nothing to match at all. Both are read as a reason of last resort rather than
    as the payload, which is what they are: a device we cannot speak for either way.
    """
    framed: Optional[tuple[str, str]] = None
    oversize: Optional[tuple[str, str]] = None
    stale_cache = False
    duplicates = 0

    for name, raw in device.attributes.items():
        text = (raw or "").strip()
        if text.startswith(FRAME_PREFIX):
            if framed is None:
                framed = (name, text)
            else:
                duplicates += 1
        elif text.startswith(OVERSIZE_PREFIX):
            oversize = oversize or (name, text)
        elif text == NO_CACHE:
            stale_cache = True

    if duplicates:
        # Two framed values are two collectors, or one attribute duplicated. Reporting
        # the first is a guess about which is current, so say so rather than pick quietly.
        log.warning(
            "%s: %s attribute(s) carry a framed payload; reading %r",
            device.device_key,
            duplicates + 1,
            framed[0] if framed else None,
        )

    if framed is not None:
        return framed
    if oversize is not None:
        return oversize
    if stale_cache:
        return None, NO_CACHE
    return None, None


def records_for(
    device: ManagedDevice,
    matcher: Matcher,
    vendor: str,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[DiscoveredAgentRecord]]:
    """One device's findings, or None when its payload could not be read.

    None and [] are different answers: [] is a device that scanned and matched nothing,
    None a device we cannot speak for.
    """
    log = logger or logging.getLogger(__name__)
    carrier, value = _inventory_value(device, log)
    envelope = read(value)

    if envelope.outcome is not EnvelopeOutcome.OK:
        # A named reason, never an absence.
        log.warning(
            "%s: no usable payload from %s (%s%s)",
            device.device_key,
            f"attribute {carrier!r}" if carrier else "any attribute",
            envelope.outcome.value,
            f": {envelope.detail}" if envelope.detail else "",
        )
        return None

    if not device.device_key.strip():
        # external_id is f"{device_key}:{agent_id}", so a blank half reads as
        # ":codex-cli" -- not blank, so every later guard passes it, while collapsing
        # every device with an unreadable id onto one identity.
        log.warning(
            "a device record carried no id; skipped, because a blank device key silently "
            "merges devices rather than failing",
        )
        return None

    result = matcher.match(envelope.rows)

    if result.dropped:
        log.warning(
            "%s: %s row(s) dropped by the matcher; a route is missing from routes.yaml",
            device.device_key,
            result.dropped,
        )

    if not result.complete:
        # Reported, not suppressed: the findings are real, but more may sit behind the
        # branch that could not look.
        log.info(
            "%s: %s branch(es) could not look (%s)",
            device.device_key,
            len(result.gaps),
            ", ".join(f"{g['id']}={g['extra']}" for g in result.gaps),
        )

    last_seen = _last_seen(result.scanned_at, device.last_reported)
    if last_seen is None:
        log.warning(
            "%s: payload carries no scan timestamp and the MDM reported no date; skipped, "
            "because last_seen is required and inventing one would date the finding to "
            "the poll",
            device.device_key,
        )
        return None

    return [
        DiscoveredAgentRecord(
            external_id=f"{device.device_key}:{finding.agent_id}",
            name=finding.name,
            last_seen=last_seen,
            creation_source=_source_for(finding, device, vendor),
        )
        for finding in result.findings
    ]


def _source_for(
    finding: Finding,
    device: ManagedDevice,
    vendor: str,
) -> EndpointAgentCreationSource:
    """What this sensor saw, in the shape every discovery category reports.

    The address names the EVIDENCE; `external_id` names the AGENT. `external_id` is
    (device, agent), so uninstalling one of an agent's several routes does not churn its
    identity. The address is (device, primary route), because its job is finding the thing
    again on the machine -- a bundle id you can look up, not a catalog key you cannot.

    `service_names` stays empty: a one-shot sweep sees installation, not behaviour.
    """
    return EndpointAgentCreationSource(
        vendor=vendor,
        address=SourceAddress(
            instance=device.device_key,
            resource_kind=finding.primary_kind,
            resource_id=finding.primary_id,
        ),
        observations=AgentObservations(
            install_path=(
                finding.install_path if finding.primary_kind in PATH_IN_LOC else None
            ),
            version=finding.version if finding.primary_kind in VERSION_IN_VER else None,
            permissions=list(finding.permissions),
            classification=finding.classification or None,
            host_name=device.name,
            host_group=device.group,
            os_version=device.os_version,
            assigned_user=device.assigned_user,
        ),
    )


def _last_seen(
    scanned_at: Optional[int],
    reported_at: Optional[str],
) -> Optional[datetime]:
    """When the evidence was observed -- the scan's own timestamp, not the poll's.

    The payload dates itself so that redeploying the file does not reset the answer. The
    MDM's report date is a weaker fallback: it says when the device last submitted
    inventory, which is later than when it scanned.
    """
    if scanned_at is not None:
        try:
            return datetime.fromtimestamp(scanned_at, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            # A `ver` outside the representable range is unusable, not fatal. Falling
            # through to the MDM's date -- and then to the skip-with-warning path -- keeps
            # one device's bad payload from ending the scan for every device behind it.
            pass
    if reported_at:
        try:
            return datetime.fromisoformat(reported_at.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None

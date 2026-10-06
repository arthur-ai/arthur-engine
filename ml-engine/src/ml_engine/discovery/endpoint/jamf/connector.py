"""Jamf Pro's side of a DISCOVER_AGENTS scan.

Pages computer inventory out of Jamf and hands each device to
`discovery.endpoint.records`, which does everything that is not Jamf-specific. What is
left here is the vendor tag, reading this source's fields, resolving its device-group
scope against the tenant's computer groups, and turning `lookback_hours` into the filter
Jamf's API wants.

BATCHED PER DEVICE, BECAUSE THAT IS THE UNIT THAT CAN FAIL. A Mac with an unreadable
payload is reported and skipped; the nine thousand behind it are unaffected. D-07
publishes each batch as it arrives, so a scan that dies on page 40 keeps pages 1-39.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator, Mapping, Optional, Sequence
from urllib.parse import urlsplit

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.catalog import Matcher
from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.jamf.client import JamfClient, JamfSettings
from discovery.endpoint.records import records_for
from discovery.endpoint.scope import DeviceScope, parse_group_names
from job_executors.discovery_scan import DeviceCoverage, DiscoveryConfigurationError

VENDOR = "jamf_pro"

# Non-sensitive source fields: comma-separated Jamf computer group names.
INCLUDE_GROUPS_FIELD = "include_groups"
EXCLUDE_GROUPS_FIELD = "exclude_groups"


class JamfConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeviceCoverage` and `AcceptsStopCheck`.

    Holds one scan's coverage and stop check, which is safe only because a connector is
    built fresh for every scan -- see `DiscoveryConnectorFactory`.
    """

    def __init__(self) -> None:
        self._coverage: Optional[DeviceCoverage] = None
        self._should_stop: Callable[[], bool] = lambda: False
        self._stopped_early = False

    def device_coverage(self) -> Optional[DeviceCoverage]:
        """None if the scan failed before reading a device, including on its scope."""
        return self._coverage

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked after every device, so a stop never waits on another page.

        This is what bounds a test on a fleet with few agents: Jamf yields only for a
        device that has records, so without it a scan could page through the whole
        inventory before the caller saw a single batch or got a chance to stop it.
        """
        self._should_stop = should_stop

    def _until_stopped(
        self,
        devices: Iterator[ManagedDevice],
    ) -> Iterator[ManagedDevice]:
        """`devices`, ending as soon as the stop check answers True.

        Asked after a device is handled and before the next is pulled, because pulling
        the next is what requests the next page from Jamf.
        """
        for device in devices:
            yield device
            if self._should_stop():
                self._stopped_early = True
                return

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """`logger` is the JOB's, so what this reports reaches the Platform job log.

        A module logger would put every unreadable device and every gap on process
        stdout and nowhere else, which makes "reported, not suppressed" untrue.
        """
        settings = _settings_from(credentials, source_fields)
        matcher = Matcher.from_source(
            catalog_yaml=config.query or None,
            logger=logger,
        )
        client = JamfClient(settings, logger=logger)

        # Resolved before a single device is read, so a scope that cannot be applied
        # fails the scan instead of scanning Macs it was meant to leave out.
        scope = DeviceScope.everything()
        if settings.scoped_to_groups:
            scope = DeviceScope.resolve(
                settings.include_groups,
                settings.exclude_groups,
                client.computer_groups(),
            )
        coverage = self._coverage = scope.new_coverage()

        logger.info(
            "Jamf scan starting against %s, catalog %s, %s agent(s), lookback %sh, "
            "scope: %s",
            settings.base_url,
            matcher.catalog_sha,
            matcher.agent_count,
            lookback_hours,
            scope.describe(),
        )

        for device in self._until_stopped(client.devices_since(_since(lookback_hours))):
            # Before the payload is decoded: an out-of-scope device contributes counts
            # and nothing else.
            if not scope.admit(device, coverage):
                continue
            read = records_for(device, matcher, VENDOR, logger)
            if read.unreadable is not None:
                coverage.count_unreadable(read.unreadable.value)
                continue
            coverage.devices_decoded += 1
            if read.records:
                yield read.records

        if self._stopped_early:
            logger.info(
                "Jamf scan stopped early on request after %s device(s)",
                coverage.devices_read,
            )

        # The denominator, also on the run outcome as `device_coverage`. Without it, "12
        # machines have agents" cannot be told from "12 of 4,000, and 900 have not
        # reported in a week" -- different reports about the same fleet.
        logger.info(
            "Jamf scan read %s device(s): %s decoded, %s unreadable",
            coverage.devices_read,
            coverage.devices_decoded,
            coverage.devices_unreadable,
        )
        if scope.is_restricted:
            logger.info(
                "Jamf scan scope kept %s of %s device(s); excluded %s%s",
                coverage.devices_in_scope,
                coverage.devices_read,
                coverage.devices_excluded,
                _breakdown(coverage.excluded_by_group),
            )
            if scope.include:
                logger.info(
                    "Jamf scan scope: %s device(s) in none of the included groups; "
                    "in scope%s",
                    coverage.devices_outside_included_groups,
                    _breakdown(coverage.included_by_group),
                )
            if coverage.devices_read and not coverage.devices_in_scope:
                # Every device read was left out. Possibly right for a narrow window, but
                # also exactly what a scope that no longer matches the fleet looks like,
                # and it publishes the same nothing as a fleet without agents.
                logger.warning(
                    "Jamf scan left all %s device(s) it read out of scope (%s). If "
                    "that is not intended, check the source's include_groups and "
                    "exclude_groups.",
                    coverage.devices_read,
                    scope.describe(),
                )

        seen, reporting = coverage.devices_in_scope, coverage.devices_decoded
        if seen and not reporting:
            # A SCAN THAT READ DEVICES AND DECODED NONE IS NOT A FLEET WITHOUT AGENTS,
            # and publishing nothing makes the two identical in the only output anyone
            # looks at. Every cause below is a deployment or configuration fault that
            # someone has to act on, so it goes to the job log rather than being left
            # for a reader to infer from a zero.
            #
            # Not an exception: a fleet whose collector was deployed an hour ago is in
            # this state legitimately, and failing a scheduled job forever is the wrong
            # answer to "not yet".
            logger.warning(
                "Jamf scan decoded 0 of %s device(s). This reads as a clean fleet and "
                "is almost never one: the collector may not be installed, its "
                "Extension Attribute may not be scoped to these devices, or no Mac has "
                "run `jamf recon` since it was deployed.",
                seen,
            )


def _settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> JamfSettings:
    """The tenant's address from the source's fields, its credentials from the secrets.

    `base_url` is not a secret and does not arrive with them. Taking it from the
    non-sensitive fields is also what keeps it out of the scrub set, so a failure can say
    which host did not answer instead of which [redacted] did not.
    """
    base_url = (source_fields.get("base_url") or "").strip()
    missing = [k for k in ("client_id", "client_secret") if not credentials.get(k)]
    if not base_url:
        missing.insert(0, "base_url")
    if missing:
        raise DiscoveryConfigurationError(
            f"Jamf source is missing required field(s): {', '.join(missing)}. "
            f"base_url is a source field; client_id and client_secret are secrets.",
        )
    if not base_url.lower().startswith("https://"):
        # client_secret travels in the token request's BODY. Over http it is in cleartext,
        # and a scheme check here is the only place it can be refused before it is sent.
        raise DiscoveryConfigurationError(
            f"Jamf base_url must be https, got "
            f"{base_url.split('://', 1)[0] or base_url!r}. "
            f"The token request carries client_secret in its body.",
        )
    if not _is_usable_address(base_url):
        # https alone is not an address. A bad port, an unclosed "[" or no host at all
        # passes the check above and then fails inside requests as InvalidURL -- a
        # ValueError, not a transport error -- which a scan would report as Jamf failing.
        raise DiscoveryConfigurationError(
            f"Jamf base_url {base_url!r} is not a valid URL: it needs a host, and a "
            f"port, if given, must be a number from 0 to 65535.",
        )
    return JamfSettings(
        base_url=base_url,
        client_id=str(credentials["client_id"]),
        client_secret=str(credentials["client_secret"]),
        include_groups=parse_group_names(source_fields.get(INCLUDE_GROUPS_FIELD)),
        exclude_groups=parse_group_names(source_fields.get(EXCLUDE_GROUPS_FIELD)),
    )


def _is_usable_address(base_url: str) -> bool:
    """Whether `base_url` parses to a host and, if it names one, a valid port.

    Answers rather than raises, so the caller's DiscoveryConfigurationError is raised
    outside this parse and does not carry the ValueError as its __context__.
    """
    try:
        parts = urlsplit(base_url)
        parts.port  # raises ValueError on a non-numeric or out-of-range port
    except ValueError:
        return False
    return bool(parts.hostname)


def _breakdown(by_group: Mapping[str, int]) -> str:
    """` (Contractors: 5, Executives: 2)`, or nothing when no groups are configured."""
    if not by_group:
        return ""
    return (
        " (" + ", ".join(f"{name}: {count}" for name, count in by_group.items()) + ")"
    )


def _since(lookback_hours: int) -> Optional[str]:
    """The filter bound, or None for a full enumeration.

    A lookback of zero or less asks for the whole roster deliberately: that is the only
    thing that answers which Macs have stopped reporting at all, which a custom attribute
    cannot answer by construction.
    """
    if lookback_hours <= 0:
        return None
    bound = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return bound.strftime("%Y-%m-%dT%H:%M:%SZ")

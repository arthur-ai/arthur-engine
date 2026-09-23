"""Jamf Pro's side of a DISCOVER_AGENTS scan.

Pages computer inventory out of Jamf and hands each device to
`discovery.endpoint.records`, which does everything that is not Jamf-specific. What is
left here is the vendor tag, reading this source's fields, and turning `lookback_hours`
into the filter Jamf's API wants.

BATCHED PER DEVICE, BECAUSE THAT IS THE UNIT THAT CAN FAIL. A Mac with an unreadable
payload is reported and skipped; the nine thousand behind it are unaffected. D-07
publishes each batch as it arrives, so a scan that dies on page 40 keeps pages 1-39.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord

from discovery.catalog import Matcher
from discovery.endpoint.jamf.client import JamfClient, JamfSettings
from discovery.endpoint.records import DEFAULT_INVENTORY_ATTRIBUTE, records_for

VENDOR = "jamf_pro"


class JamfScanner:
    """Implements `job_executors.discovery_scan.DiscoverySourceScanner`."""

    def __init__(self, attribute_name: str = DEFAULT_INVENTORY_ATTRIBUTE) -> None:
        self._attribute = attribute_name

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

        logger.info(
            "Jamf scan starting against %s, catalog %s, %s agent(s), lookback %sh",
            settings.base_url,
            matcher.catalog_sha,
            matcher.agent_count,
            lookback_hours,
        )

        seen = reporting = unreadable = 0

        for device in client.devices_since(_since(lookback_hours)):
            seen += 1
            records = records_for(
                device,
                matcher,
                VENDOR,
                self._attribute,
                logger,
            )
            if records is None:
                unreadable += 1
                continue
            reporting += 1
            if records:
                yield records

        # The denominator, which the run outcome has no field for yet. Without it, "12
        # machines have agents" cannot be told from "12 of 4,000, and 900 have not
        # reported in a week" -- different reports about the same fleet.
        logger.info(
            "Jamf scan read %s device(s): %s decoded, %s unreadable",
            seen,
            reporting,
            unreadable,
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
        raise ValueError(
            f"Jamf source is missing required field(s): {', '.join(missing)}. "
            f"base_url is a source field; client_id and client_secret are secrets.",
        )
    if not base_url.lower().startswith("https://"):
        # client_secret travels in the token request's BODY. Over http it is in cleartext,
        # and a scheme check here is the only place it can be refused before it is sent.
        raise ValueError(
            f"Jamf base_url must be https, got "
            f"{base_url.split('://', 1)[0] or base_url!r}. "
            f"The token request carries client_secret in its body.",
        )
    return JamfSettings(
        base_url=base_url,
        client_id=str(credentials["client_id"]),
        client_secret=str(credentials["client_secret"]),
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

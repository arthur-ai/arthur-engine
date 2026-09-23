"""Reading computer inventory out of Jamf Pro.

Read-only, and outbound only. Nothing is installed on a device, nothing is executed on
one, and no policy is written back -- the Mac already talks to Jamf and to nothing else,
so the fleet needs no new route, no firewall rule and no device-held credential. The
privilege this needs is *Read Computers* and nothing more.

TWO THINGS HERE ARE NOT OPTIONAL, AND BOTH COME FROM HOW reportDate BEHAVES.

`general.reportDate` is assigned at check-in, so records shift between pages while a scan
is paginating. Sorting ascending on the same field being filtered is what keeps a shifting
record from being skipped rather than merely repeated, and the framework's lookback window
supplies the overlap that makes a repeat harmless -- resolution downstream is idempotent on
external_id, so re-delivery costs a row and loses nothing. The failure this avoids is the
classic one for the pattern: advance a watermark to `now()`, and devices that checked in
during the page you were reading are never seen again.

Pages are fetched one at a time. Jamf publishes a ceiling of five concurrent connections
and no server-side throttling, so the limit is a courtesy rather than an error -- exceeding
it degrades the customer's Jamf Pro rather than failing this job, which is the wrong way
round for a tool nobody asked to have installed. A hundred sequential pages for a
10,000-Mac fleet is well inside an hourly schedule.
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional
from urllib.parse import quote, urljoin

import requests

from discovery.endpoint.device import ManagedDevice

# What the collector needs and nothing else. GENERAL carries `reportDate`, which is the
# roster and the freshness signal; EXTENSION_ATTRIBUTES carries the payload. The other two
# name the device and its owner for the observation fields.
SECTIONS = (
    "GENERAL",
    "HARDWARE",
    "OPERATING_SYSTEM",
    "USER_AND_LOCATION",
    "EXTENSION_ATTRIBUTES",
)

# Jamf's own published guidance is at most five concurrent connections. One page at a time
# is deliberate; see the module docstring.
PAGE_SIZE = 100

# Refreshed at 80% of its life rather than on expiry, so a long scan does not discover the
# token died between two pages.
TOKEN_REFRESH_RATIO = 0.8

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_CAP_SECONDS = 30.0


class JamfError(RuntimeError):
    """A Jamf call failed in a way retrying will not fix."""


@dataclass(frozen=True)
class JamfSettings:
    """Where the Jamf tenant is and how to authenticate to it."""

    base_url: str
    client_id: str
    client_secret: str
    page_size: int = PAGE_SIZE
    timeout_seconds: float = 30.0
    verify_ssl: bool = True


class JamfClient:
    """A Jamf Pro session that knows how to page inventory.

    Holds one OAuth token and refreshes it in place, so a caller iterating pages does not
    have to think about token lifetime.
    """

    def __init__(
        self,
        settings: JamfSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._http = session or requests.Session()
        self._sleep = sleep
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    # --- auth ---------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return urljoin(self._s.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _bearer(self) -> str:
        if self._token is not None and time.monotonic() < self._token_expires_at:
            return self._token

        resp = self._http.post(
            self._url("/api/oauth/token"),
            data={
                "grant_type": "client_credentials",
                "client_id": self._s.client_id,
                "client_secret": self._s.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._s.timeout_seconds,
            verify=self._s.verify_ssl,
        )
        if resp.status_code != 200:
            # Deliberately does not echo the body: a failed token call is the one response
            # most likely to quote the request it failed on.
            raise JamfError(f"Jamf token request failed with HTTP {resp.status_code}")

        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise JamfError("Jamf token response carried no access_token")

        expires_in = float(payload.get("expires_in") or 0)
        self._token = str(token)
        self._token_expires_at = time.monotonic() + expires_in * TOKEN_REFRESH_RATIO
        return self._token

    # --- transport ----------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        last: Optional[str] = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            resp = self._http.get(
                self._url(path),
                params=params,
                headers={
                    "Authorization": f"Bearer {self._bearer()}",
                    "Accept": "application/json",
                },
                timeout=self._s.timeout_seconds,
                verify=self._s.verify_ssl,
            )

            if resp.status_code == 200:
                body: dict[str, Any] = resp.json()
                return body

            if resp.status_code == 401 and attempt < MAX_ATTEMPTS:
                # The token died mid-scan despite the 80% refresh. Drop it and retry once
                # against a fresh one rather than failing a scan for a solvable reason.
                self._token = None
                last = "HTTP 401"
                continue

            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(self._backoff(attempt, resp.headers.get("Retry-After")))
                last = f"HTTP {resp.status_code}"
                continue

            raise JamfError(f"Jamf GET {path} failed with HTTP {resp.status_code}")

        raise JamfError(
            f"Jamf GET {path} still failing after {MAX_ATTEMPTS} attempts ({last})",
        )

    @staticmethod
    def _backoff(attempt: int, retry_after: Optional[str]) -> float:
        """Honour Retry-After when Jamf sends one, else exponential with jitter.

        Jittered because a fleet-wide job retrying on a fixed schedule is a thundering
        herd against the customer's own Jamf Pro.
        """
        if retry_after:
            try:
                return min(float(retry_after), BACKOFF_CAP_SECONDS)
            except ValueError:
                pass
        window = min(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), BACKOFF_CAP_SECONDS)
        return random.uniform(0, window)

    # --- inventory ----------------------------------------------------------------

    def devices_since(self, since_iso: Optional[str]) -> Iterator[ManagedDevice]:
        """Yield every computer whose inventory was reported since `since_iso`.

        Sorted ascending on the field being filtered, which is what makes a record that
        shifts during pagination repeat rather than vanish. `since_iso` of None asks for
        the whole roster -- the enumeration that answers which Macs have stopped
        reporting at all, which no Extension Attribute can answer by construction.
        """
        page = 0
        seen = 0
        total: Optional[int] = None

        while True:
            params: dict[str, Any] = {
                "section": list(SECTIONS),
                "page": page,
                "page-size": self._s.page_size,
                "sort": "general.reportDate:asc",
            }
            if since_iso:
                params["filter"] = (
                    f'general.reportDate=gt="{quote(since_iso, safe="")}"'
                )

            body = self._get("/api/v1/computers-inventory", params)
            results = body.get("results") or []
            if total is None:
                total = body.get("totalCount")
                self._log.info("Jamf reports %s computer(s) in scope", total)

            if not results:
                return

            for record in results:
                seen += 1
                yield _to_device(record)

            page += 1
            if total is not None and seen >= int(total):
                return


def _to_device(record: dict[str, Any]) -> ManagedDevice:
    general = record.get("general") or {}
    os_block = record.get("operatingSystem") or {}
    user = record.get("userAndLocation") or {}
    hardware = record.get("hardware") or {}

    attributes: dict[str, Optional[str]] = {}
    # Extension attributes arrive in several sections depending on where they are scoped.
    # Merging them is deliberate: the collector addresses them by display name, which is
    # what a Jamf admin sees and what the runbook names, not by which section carried them.
    for section in (record, general, os_block, user, hardware):
        for attribute in (section or {}).get("extensionAttributes") or []:
            name = attribute.get("name")
            if not name:
                continue
            values = attribute.get("values") or []
            attributes[str(name)] = str(values[0]) if values else None

    return ManagedDevice(
        # managementId is Jamf's own stable id. The serial is deliberately not used: see
        # ManagedDevice.device_key.
        device_key=str(general.get("managementId") or record.get("id") or ""),
        last_reported=general.get("reportDate"),
        name=general.get("name"),
        group=user.get("department") or user.get("building"),
        os_version=os_block.get("version"),
        assigned_user=user.get("username"),
        attributes=attributes,
    )

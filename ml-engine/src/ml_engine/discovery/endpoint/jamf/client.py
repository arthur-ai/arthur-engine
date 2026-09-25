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
from urllib.parse import urljoin

import requests
from arthur_common.models.agent_governance_schemas import Platform

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

# Jamf's `operatingSystem.name`, lowercased. Jamf Pro inventories Macs, and has called
# their OS each of these over the years.
_DARWIN_OS_NAMES = frozenset({"macos", "mac os x", "os x"})

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
            # The secret is in the BODY. requests follows redirects by default and on a
            # 307/308 resends method and body to the Location host, stripping only the
            # Authorization header -- so a redirect would hand client_secret to whatever
            # host it names.
            allow_redirects=False,
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
            try:
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
            except (requests.ConnectionError, requests.Timeout) as exc:
                # The most common failure on a hundred-page fleet scan, and it was
                # escaping on the first occurrence: one reset on page 40 ended the scan.
                if attempt == MAX_ATTEMPTS:
                    raise JamfError(f"Jamf GET {path} unreachable: {exc}") from exc
                last = type(exc).__name__
                self._sleep(self._backoff(attempt, None))
                continue

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
        """Yield computers whose inventory was reported since `since_iso`.

        `since_iso` of None asks for the whole roster -- the enumeration that answers
        which Macs have stopped reporting at all, which no custom attribute can answer.

        OFFSET PAGING CANNOT BE USED ON A FIELD THAT MUTATES. Sorting ascending on
        `reportDate` saves the record that checks in mid-scan -- it moves to the end and
        is read again -- but every record behind it shifts DOWN one position, and at a
        page boundary one of them moves back into a page already read. With a=b=c=d and
        page size 2: page 0 returns (a, b); `a` checks in, so the order becomes
        (b, c, d, a); page 1 returns (d, a) and `c` is never returned at all.

        So the two cases page differently, and neither uses an offset over reportDate.
        """
        if since_iso is None:
            yield from self._enumerate_by_id()
        else:
            yield from self._keyset_by_report_date(since_iso)

    def _enumerate_by_id(self) -> Iterator[ManagedDevice]:
        """The full roster, keyset on `id`.

        A keyset over `reportDate` cannot serve this case: filtering on it at all drops
        devices that have never reported, and those are exactly what a full enumeration
        is for. `id` never changes for a device -- but an OFFSET over it still slips when
        a device is DELETED mid-scan, because every id after it moves down one position
        and one falls back into a page already read. A keyset does not care.
        """
        last_id: Optional[Any] = None
        while True:
            params: dict[str, Any] = {
                "section": list(SECTIONS),
                "page": 0,
                "page-size": self._s.page_size,
                "sort": "id:asc",
            }
            if last_id is not None:
                params["filter"] = f"id=gt={last_id}"

            body = self._get("/api/v1/computers-inventory", params)
            results = body.get("results") or []
            if not results:
                return
            for record in results:
                yield _to_device(record)

            tail_id = results[-1].get("id")
            if tail_id is None:
                self._log.warning(
                    "Jamf returned a record with no id; ending the roster walk rather "
                    "than repeating the same filter",
                )
                return
            last_id = tail_id

    def _keyset_by_report_date(self, since_iso: str) -> Iterator[ManagedDevice]:
        """The incremental window, paged by keyset rather than by offset.

        Each page restarts at page 0 with a filter strictly after the last
        `(reportDate, id)` read, so a record that checks in mid-scan moves ahead of the
        cursor and is read again rather than displacing one behind it. `id` breaks ties:
        `reportDate` has second resolution and a fleet check-in puts many devices on the
        same value, which a cursor on the date alone would either skip or re-read forever.

        Stops on an empty page. A `totalCount` captured from the first page counts a
        fleet that is still changing, and re-reads make `seen` reach it early.
        """
        last_date, last_id = since_iso, None

        while True:
            # NOT pre-quoted: requests percent-encodes the param, so quoting here too
            # means Jamf decodes once and gets `2026-09-22T09%3A00%3A00Z` inside the RSQL
            # rather than a timestamp -- rejected with a 400, which is not retryable.
            if last_id is None:
                where = f'general.reportDate=gt="{last_date}"'
            else:
                # RSQL: `,` is OR and `;` is AND -- after this date, or on it with a
                # higher id.
                where = (
                    f'general.reportDate=gt="{last_date}",'
                    f'(general.reportDate=="{last_date}";id=gt={last_id})'
                )

            body = self._get(
                "/api/v1/computers-inventory",
                {
                    "section": list(SECTIONS),
                    "page": 0,
                    "page-size": self._s.page_size,
                    "sort": "general.reportDate:asc,id:asc",
                    "filter": where,
                },
            )
            results = body.get("results") or []
            if not results:
                return

            for record in results:
                yield _to_device(record)

            tail = results[-1]
            tail_date = (tail.get("general") or {}).get("reportDate")
            tail_id = tail.get("id")
            if not tail_date or tail_id is None:
                # Without both halves the cursor cannot advance, and repeating the same
                # filter would loop forever. Stop and let the next run's window cover it.
                self._log.warning(
                    "Jamf returned a record with no reportDate or id; ending this page "
                    "walk rather than repeating the same filter",
                )
                return
            last_date, last_id = str(tail_date), tail_id


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
        platform=_platform(os_block.get("name")),
        assigned_user=user.get("username"),
        attributes=attributes,
    )


def _platform(os_name: Any) -> Optional[Platform]:
    """The platform Jamf's OS name stands for, or None for one this does not know."""
    if not isinstance(os_name, str):
        return None
    return Platform.DARWIN if os_name.strip().lower() in _DARWIN_OS_NAMES else None

#!/usr/bin/env python
"""Read-only smoke test of the Jamf connector against a real tenant.

RUN THIS BEFORE A TENANT'S FIRST SCAN. A fake built from an API's documentation can
only confirm the code matches somebody's reading of it; what it cannot know is what
this tenant actually serves and what its admins named things. Both defects found so
far in this connector were of the second kind and were invisible to the unit suite.

Drives the SHIPPED JamfClient rather than a second implementation, so what passes here
is what a scan does. The exception is step 0, which probes both documented token paths
deliberately -- Jamf's docs give /api/oauth/token and jamf-pro-sdk-python uses
/api/v1/oauth/token, and only a tenant can say which it serves.

Nothing is written: one POST to mint a token, then GETs. Needs `Read Computers` and
nothing more.

Credentials come from the environment, are registered as scrub targets, and are never
printed:

    JAMF_BASE_URL  JAMF_CLIENT_ID  JAMF_CLIENT_SECRET

    cd ml-engine
    set -a; . ~/.jamf-smoke.env; set +a
    uv run python scripts/jamf_smoke.py --page-size 2

`--page-size` small forces both cursors to advance across real pages; at the default a
small fleet fits in one page and the paging is never exercised.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "ml_engine"),
)

from discovery.catalog import Matcher  # noqa: E402
from discovery.endpoint.envelope import FRAME_PREFIX, OVERSIZE_PREFIX  # noqa: E402
from discovery.endpoint.jamf.client import (  # noqa: E402
    SECTIONS,
    JamfClient,
    JamfSettings,
)
from discovery.endpoint.records import records_for  # noqa: E402
from log_redaction import redact_secrets  # noqa: E402

SECRETS: list[str] = []
FAILURES: list[str] = []


def safe(text: object) -> str:
    return redact_secrets(str(text), SECRETS)


def check(name: str, ok: bool, detail: str = "") -> bool:
    FAILURES.append(name) if not ok else None
    print(
        f"  [{'PASS' if ok else 'FAIL'}] {name}{(' -- ' + safe(detail)) if detail else ''}",
    )
    return ok


def head(title: str) -> None:
    print(f"\n=== {title} ===")


def probe_token_paths(base: str, client_id: str, client_secret: str) -> Optional[str]:
    """Which token path does this tenant serve?

    Jamf's docs give /api/oauth/token; jamf-pro-sdk-python uses /api/v1/oauth/token.
    The connector picked the first. This is the one thing a fake cannot settle.
    """
    served = None
    for path in ("/api/oauth/token", "/api/v1/oauth/token"):
        try:
            resp = requests.post(
                base.rstrip("/") + path,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
                allow_redirects=False,
            )
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR ] {path}: {type(e).__name__}: {safe(e)}")
            continue
        got_token = resp.status_code == 200 and bool(
            (resp.json() or {}).get("access_token"),
        )
        print(
            f"  [{'OK  ' if got_token else 'no  '}] {path} -> HTTP {resp.status_code}",
        )
        if got_token and served is None:
            served = path
    return served


def shape(value: Any, depth: int = 0) -> Any:
    """Keys and types only -- never values, which carry inventory."""
    if isinstance(value, dict):
        if depth >= 2:
            return f"<dict:{len(value)} keys>"
        return {k: shape(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(value[0], depth + 1), "..."] if value else []
    return type(value).__name__


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="devices to pull per walk")
    ap.add_argument("--lookback-hours", type=int, default=168)
    ap.add_argument(
        "--dump-record",
        action="store_true",
        help="print one raw record's shape",
    )
    # Small by default so the cursor walk is actually exercised. Production pages at 100,
    # but a tenant with fewer devices than that returns everything in one page and the
    # paging assertions below would never run -- on a small fleet the default that matches
    # production is the default that tests nothing.
    ap.add_argument(
        "--page-size",
        type=int,
        default=2,
        help="pages to fetch in; small values force the cursor to advance",
    )
    args = ap.parse_args()

    base = (os.environ.get("JAMF_BASE_URL") or "").strip()
    client_id = (os.environ.get("JAMF_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("JAMF_CLIENT_SECRET") or "").strip()
    if not (base and client_id and client_secret):
        print("Set JAMF_BASE_URL, JAMF_CLIENT_ID, JAMF_CLIENT_SECRET.", file=sys.stderr)
        return 2
    # BEFORE ANYTHING SENDS THE SECRET. The token request carries client_secret in its
    # body, so over http it is on the wire in cleartext -- and step 0 posts directly rather
    # than through JamfSettings, which is where the connector makes this check.
    if not base.lower().startswith("https://"):
        print(
            f"JAMF_BASE_URL must be https, got {base.split('://', 1)[0]!r}. "
            f"The token request carries the client secret in its body.",
            file=sys.stderr,
        )
        return 2
    SECRETS.extend([client_secret, client_id])

    logging.basicConfig(level=logging.INFO, format="  log | %(message)s")
    log = logging.getLogger("jamf-smoke")

    print(f"Tenant: {base}")

    head("0. Which token path does this tenant serve?")
    served = probe_token_paths(base, client_id, client_secret)
    check(
        "the connector's token path (/api/oauth/token) is served",
        served == "/api/oauth/token",
        f"tenant serves {served}" if served else "neither path returned a token",
    )
    if served is None:
        print("\nNo token: nothing below can run.")
        return 1

    settings = JamfSettings(
        base_url=base,
        client_id=client_id,
        client_secret=client_secret,
        page_size=args.page_size,
    )
    client = JamfClient(settings, logger=log)

    head("1. The shipped client can authenticate")
    try:
        token = client._bearer()
        SECRETS.append(token)
        check("JamfClient._bearer() minted a token", bool(token))
    except Exception as e:  # noqa: BLE001
        check("JamfClient._bearer() minted a token", False, f"{type(e).__name__}: {e}")
        return 1

    head("2. One inventory page, with the params a scan sends")
    try:
        body = client._get(
            "/api/v1/computers-inventory",
            {
                "section": list(SECTIONS),
                "page": 0,
                "page-size": args.limit,
                "sort": "id:asc",
            },
        )
    except Exception as e:  # noqa: BLE001
        check("GET /api/v1/computers-inventory", False, f"{type(e).__name__}: {e}")
        return 1
    results = body.get("results") or []
    check(
        "GET /api/v1/computers-inventory returned results",
        bool(results),
        f"totalCount={body.get('totalCount')}, this page={len(results)}",
    )
    if not results:
        return 1

    record = results[0]
    if args.dump_record:
        print("  raw record shape:")
        print("   ", json.dumps(shape(record), indent=2).replace("\n", "\n    "))

    head("3. The fields the connector reads are present")
    general = record.get("general") or {}
    check("general.managementId present", bool(general.get("managementId")))
    check(
        "general.reportDate present",
        bool(general.get("reportDate")),
        f"e.g. {general.get('reportDate')}",
    )
    check("operatingSystem section present", "operatingSystem" in record)
    check("userAndLocation section present", "userAndLocation" in record)

    ea_sections = [
        name
        for name, block in (
            ("<root>", record),
            ("general", general),
            ("operatingSystem", record.get("operatingSystem") or {}),
            ("userAndLocation", record.get("userAndLocation") or {}),
            ("hardware", record.get("hardware") or {}),
        )
        if (block or {}).get("extensionAttributes")
    ]
    check(
        "extensionAttributes found in at least one section",
        bool(ea_sections),
        f"sections: {', '.join(ea_sections) or 'none'}",
    )

    sample_ea = None
    for block in (
        record,
        general,
        record.get("operatingSystem") or {},
        record.get("userAndLocation") or {},
        record.get("hardware") or {},
    ):
        for ea in (block or {}).get("extensionAttributes") or []:
            sample_ea = ea
            break
        if sample_ea:
            break
    if sample_ea is not None:
        check("an extension attribute carries 'name'", "name" in sample_ea)
        check(
            "an extension attribute carries 'values' as a list",
            isinstance(sample_ea.get("values"), list),
            f"got {type(sample_ea.get('values')).__name__}; keys: {sorted(sample_ea)}",
        )

    head("4. Keyset paging on id (full enumeration)")
    try:
        devices = []
        for device in client.devices_since(None):
            devices.append(device)
            if len(devices) >= args.limit:
                break
        check(
            "devices_since(None) yielded devices",
            bool(devices),
            f"{len(devices)} read",
        )
        keyed = [d for d in devices if d.device_key]
        check(
            "every device got a device_key",
            len(keyed) == len(devices),
            f"{len(devices) - len(keyed)} blank",
        )
        if len(devices) > args.page_size:
            check(
                "the id cursor advanced across pages",
                True,
                f"read {len(devices)} at page-size {args.page_size}",
            )
        else:
            # Not a failure: a walk that fits in one page never asks the cursor for a
            # second. Reporting it as one would be an assertion that fails where the code
            # is right, which is worse than not making it.
            print(
                f"  [SKIP] the id cursor advanced across pages -- read "
                f"{len(devices)} at page-size {args.page_size}, so one page covered it; "
                f"raise --limit or lower --page-size to exercise it",
            )
        check(
            "no device was returned twice",
            len({d.device_key for d in devices}) == len(devices),
            f"{len(devices) - len({d.device_key for d in devices})} duplicate(s)",
        )
    except Exception as e:  # noqa: BLE001
        check("devices_since(None)", False, f"{type(e).__name__}: {e}")
        devices = []

    head(f"5. RSQL filter + two-key sort (incremental, {args.lookback_hours}h)")
    since = (
        datetime.now(timezone.utc) - timedelta(hours=args.lookback_hours)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        recent = []
        for device in client.devices_since(since):
            recent.append(device)
            if len(recent) >= args.limit:
                break
        check(
            f"devices_since('{since}') was accepted",
            True,
            f"{len(recent)} device(s)",
        )
        if len(recent) > args.page_size:
            check(
                "the reportDate cursor advanced across pages",
                True,
                f"read {len(recent)} at page-size {args.page_size}",
            )
        else:
            print(
                f"  [SKIP] the reportDate cursor advanced across pages -- read "
                f"{len(recent)} in the window at page-size {args.page_size}; "
                f"widen --lookback-hours or lower --page-size to exercise it",
            )
    except Exception as e:  # noqa: BLE001
        check(
            f"devices_since('{since}') was accepted",
            False,
            f"{type(e).__name__}: {e}",
        )
        recent = []

    head("6. The payload is found by its own prefix, and decodes")
    pool = recent or devices

    def carries(device: Any) -> bool:
        return any(
            (v or "").strip().startswith((FRAME_PREFIX, OVERSIZE_PREFIX))
            for v in device.attributes.values()
        )

    carrying = [d for d in pool if carries(d)]
    check(
        "a device carries a framed payload under some attribute",
        bool(carrying),
        f"{len(carrying)}/{len(pool)} of the devices read; attribute names seen: "
        f"{sorted({k for d in pool for k in d.attributes})}",
    )

    if carrying:
        matcher = Matcher.from_source(catalog_yaml=None, logger=log)
        print(f"  catalog {matcher.catalog_sha}, {matcher.agent_count} agent(s)")
        decoded = 0
        for device in carrying:
            records = records_for(device, matcher, "jamf_pro", log)
            if records is None:
                continue
            decoded += 1
            print(
                f"  {device.device_key[:8]}...: {len(records)} finding(s)"
                + (
                    f" -- {', '.join(sorted({r.name for r in records}))}"
                    if records
                    else ""
                ),
            )
        check("at least one payload decoded", decoded > 0, f"{decoded}/{len(carrying)}")

    head("Summary")
    if FAILURES:
        print(f"  {len(FAILURES)} failed:")
        for name in FAILURES:
            print(f"    - {name}")
        return 1
    print("  every assumption held.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

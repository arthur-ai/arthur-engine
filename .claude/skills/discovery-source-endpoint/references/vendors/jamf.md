# Jamf Pro

Reference connector: `ml-engine/src/ml_engine/discovery/endpoint/jamf/` (client and connector).

| Requirement | Jamf Pro |
|---|---|
| Run a script as root on a schedule | package policy + LaunchDaemon |
| Per-device string attribute | Extension Attribute |
| Inventory API by report date | `/api/v1/computers-inventory`, filtered and sorted on `general.reportDate` |
| Stable device id | `general.managementId`; never the serial |

- Lookback: `_since` turns `lookback_hours` into a `general.reportDate` filter.
- Paging: incremental scans keyset on `(reportDate, id)`; the full roster keysets on `id`, because filtering on `reportDate` at all drops devices that never reported. Never offset-page: `reportDate` changes at check-in and shifts records between pages.
- `reportDate` has one-second resolution, so a fleet check-in puts many devices on one value; the keyset tie-breaks on `id`.
- Token: OAuth client credentials at `/api/oauth/token`, with the secret in the body and `allow_redirects=False` (a 307/308 would resend the body to another host). The inventory GETs do not set it; new carriers set it on every call that carries a token.
- `PAGE_SIZE = 100`.

---
name: discovery-source-endpoint
description: The Endpoint source-class contract for Shadow Agent Discovery (an endpoint collector runs on each machine and a carrier such as an MDM, Compute Engine guest attributes or EC2 hands its per-device `arthur1.` string back over an API; e.g. Jamf Pro, Intune, Kandji, Compute Engine, EC2, CrowdStrike). Use once a vendor is classified `endpoint`, or when adding a carrier, reviewing an endpoint connector under ml-engine/src/ml_engine/discovery/endpoint/ or changing device scoping. It says what an endpoint record carries, what a carrier must provide, how lookback, coverage and Test Connection behave, what to copy, and which tests prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Endpoint source class

This skill owns what is true of every **endpoint** source in the engine (`ml-engine/` and `integrations/endpoint-ai-discovery/`). Platform and UI steps are covered by Arthur's internal discovery integration process skill.

## 1. What an endpoint source is

On each machine, the endpoint collector (`integrations/endpoint-ai-discovery`, `dist/collect.sh` / `collect-linux.sh`, vendored osquery-ai-discovery) finds AI software and writes one `arthur1.` string (base64 of gzip of six-column rows). A **carrier** gets that script onto the machine on a schedule and hands the string back as a per-device attribute over its API. The engine connector is only the carrier's API client: the payload, the matching and the record shape live in `discovery/endpoint/` and do not change per vendor.

So a new endpoint vendor is "a runbook plus an API client per carrier" (`integrations/endpoint-ai-discovery/docs/mdm/README.md`). Before writing code, check the carrier meets the four requirements:

| Requirement | Why | Jamf Pro | Compute Engine |
|---|---|---|---|
| Run a script as root on a schedule | the collector must run | package policy + LaunchDaemon | OS policy + systemd timer |
| A per-device string attribute large enough (evidence reaches ~24 KB; budget 256 KB) | the string must arrive untruncated | Extension Attribute | guest attribute (cap 262,144 bytes) |
| An inventory API filterable and sortable by a report date | incremental scans that do not lose devices mid-page | `/api/v1/computers-inventory` | none: full enumeration every run |
| A stable device id from the carrier, never the hardware serial or a reusable name | `external_id` stability | `general.managementId` | the instance's numeric `id` |

A vendor that cannot run a script (a pure EDR/DLP inventory such as CrowdStrike or Nightfall exposing only their own detections) is not this shape: decide in intake whether it is an endpoint carrier, a SIEM query over its events, or a new class, and record that decision with the Platform catalog change.

## 2. The record contract

Build nothing by hand: `discovery/endpoint/records.py:records_for(device, findings, ...)` turns a `ManagedDevice` (`endpoint/device.py`) plus decoded findings into records.

| Part | Rule |
|---|---|
| Creation source | `EndpointAgentCreationSource`: `DETECTION=OBSERVED`, `VISIBILITY_CEILING=LIMITED`, the widest `OBSERVABLE_FIELDS` (install_path, version, host_name, host_group, os_version, assigned_user, permissions, classification) |
| `external_id` | `f"{device.device_key}:{finding.agent_id}"`; `device_key` is the carrier's stable id |
| `address.instance` | `device_key` (the machine) |
| `address.resource_kind` / `resource_id` | the evidence route (kind + id of the primary finding) |
| `runs_on` / `platform` | `RunsOn.ENDPOINT` and the device OS (`darwin`/`linux`/`windows`) |
| `observations` | from the carrier's device record (name, group, os_version, assigned_user) and the collector rows; `install_path` and `version` only for kinds that carry them |
| `service_names` | empty |

The connector's own job is to produce `ManagedDevice` values: carrier id, `last_reported`, name, group, OS, assigned user, group ids, and the attribute string.

## 3. Connection and credentials

- Fields (the Platform catalog entry; model it on Jamf Pro's): `base_url` non-sensitive and must be https; client credentials sensitive; optional `include_groups` / `exclude_groups` parsed by `endpoint/scope.py` (`DeviceScope`, `parse_group_names`). Cloud-hosted carriers (GCE, EC2) swap `base_url` for the account locator and a service credential, like a cloud source.
- `SENSITIVE_FIELDS: ClassVar[frozenset[str]]` on the connector names the credential keys. Standalone mode refuses a connector without it (`tests/unit/standalone/test_discovery_config.py:test_every_registered_connector_declares_its_secrets`), and its contents must equal the catalog entry's secret fields. Nothing in this repo checks that equality; the process skill's cross-repo invariant check does.
- Resolve device scope (groups) **before** reading any device; an unknown group name is a config error naming the group.
- `allow_redirects=False` on every call that carries a token (Jamf sets it only on the token POST; new code sets it on inventory GETs too).
- Least privilege: read-only on computer inventory and the two attributes.

## 4. Lookback, paging, coverage

- **Lookback is an incremental window on the carrier's report date** (Jamf `_since` → `reportDate` filter). `lookback_hours <= 0` means the full roster. A carrier with no report date enumerates fully every run and says so in the docs section.
- Keyset-page on `(report_date, id)` so devices that report mid-scan are not skipped; `PAGE_SIZE = 100`; retries via `discovery/retry.py`; refresh tokens before expiry and drop the token on 401.
- Yield one batch per device: a mid-scan failure keeps what was published.
- Implement **`ReportsDeviceCoverage.device_coverage()`** (devices seen, decoded, missing/stale attribute): the scan asks it in `finally` and the UI reports coverage. Implement `AcceptsStopCheck.stop_when(should_stop)` and ask after every device. Both are structural (`job_executors/discovery_scan.py`; do not import the Protocols); the stop check is handed in before `scan`, and when it answers True you `return` cleanly. Test Connection's 120 s deadline (`PREVIEW_DEADLINE_SECONDS` in `job_executors/discovery_source_test_executor.py`) relies on it.
- Zero decoded devices is a warning, not an error (the collector may not be deployed yet).
- `config.query` is a catalog override (YAML) for the matcher, not a query language: keep the catalog's query language `none`.

## 5. Errors and Test Connection

The shared error model, which both the scan and Test Connection read:

| Situation | Raise | Scan `failure_code` / Test Connection category |
|---|---|---|
| Missing field, `http://` URL, bad URL, unknown group | `DiscoveryConfigurationError` (a `ValueError`) | `not_configured` / `configuration` |
| Carrier answered non-2xx | `<Vendor>Error(msg, status_code=n)` | 401 `authentication_failed` / `authentication`; 403 `permission_denied` / `authorization`; else `provider_error` / `vendor_error` |
| 200 whose body is not the carrier's shape | `<Vendor>Error(..., status_code=200)` | `provider_error` / `vendor_error` |
| TLS handshake refused | `DiscoveryConfigurationError(...) from exc` | `not_configured` / `configuration` |
| Host unreachable or timed out | the same type: `raise type(exc)(msg) from exc` | `provider_error` / `network` or `timeout` |

Never raise a plain `ValueError` for a config fault: it reads as `configuration` in Test Connection but as `provider_error` on a scan. Error text names the field and the fix, never the value. Endpoint-specific: a malformed `arthur1.` string on one device is a per-device warning counted in coverage, never a scan failure; never log attribute contents.

## 6. What to copy (arthur-engine `ml-engine/` and `integrations/endpoint-ai-discovery/`)

Verified on 2026-10-12 against arthur-engine `dev` `4de52ab4` and arthur-common `main` `600a527f`. Paths drift: if a file named here is missing, find the symbol, then update this line. The process skill's cross-repo invariant check is the guard that the engine and Platform halves agree.

Copy `ml-engine/src/ml_engine/discovery/endpoint/jamf/` (client + connector). Files:

- `discovery/endpoint/<vendor>/{__init__,client,connector}.py`.
- The registry: in `discovery/__init__.py:source_connectors()` import `VENDOR as <X>_VENDOR` and the connector class, add the dict entry, add both names to `__all__`.
- `tests/unit/discovery/test_<vendor>_connector.py`.
- The standalone docs section in `docs/standalone-discovery.md`.
- **A carrier runbook** `integrations/endpoint-ai-discovery/docs/mdm/<vendor>.md` linked from `docs/mdm/README.md` (how to deploy the collector, create the attributes, and grant the API role). Changes under `integrations/endpoint-ai-discovery/**` may be CODEOWNERS-gated; check before promising a merge.

## 7. Checklist

- [ ] Carrier meets the four requirements, or the gap (no report date) is documented.
- [ ] Connector produces `ManagedDevice`; records only via `records_for`; `device_key` is the carrier's stable id.
- [ ] Device scope resolved before reading devices; group errors name the group.
- [ ] Report-date window and keyset paging; `<= 0` is full roster.
- [ ] `ReportsDeviceCoverage` and `AcceptsStopCheck` implemented.
- [ ] Runbook added and linked; `SENSITIVE_FIELDS` == the catalog's secret fields.
- [ ] Platform catalog entry: class endpoint, query language none, availability preview.

## 8. Tests that prove it

Copy the Jamf themes: registration; token flow and refresh; keyset paging with a device that reports mid-scan; report-date window from lookback and full roster at `<= 0`; group scope resolution and unknown group refusal; `arthur1.` decode to records with the expected `external_id` and address; malformed attribute counted in coverage and not fatal; `device_coverage()` totals; stop check after each device; 401/403 status; http URL refused; credentials and attribute contents never logged.

## 9. Proving it end to end

Follow the process skill's local end-to-end recipe. Endpoint needs a device carrying a real `arthur1.` string: use a captured attribute from the collector (`dist/collect.sh` on a test machine) served by a fake carrier, or a sandbox tenant. Check the Agents tab shows the records with the device name and the endpoint mark, and the scan shows coverage.

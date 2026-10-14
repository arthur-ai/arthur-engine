---
name: discovery-source-endpoint
description: States the Endpoint source-class contract for Shadow Agent Discovery, where an endpoint collector runs on each machine and a carrier (an MDM such as Jamf Pro, Intune or Kandji, or a cloud host such as Compute Engine or EC2) hands its per-device `arthur1.` string back over an API. Use when a vendor is classified `endpoint`, when adding a carrier, reviewing a connector under ml-engine/src/ml_engine/discovery/endpoint/, or changing device scoping. Covers carrier requirements, the record, lookback, coverage, errors, Test Connection, what to copy and the tests that prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Endpoint source class

The gates already refuse the mechanical mistakes: a connector missing from the registry or without `SENSITIVE_FIELDS` (`ml-engine/tests/unit/standalone/test_discovery_config.py`), an executor registry that disagrees with it (`ml-engine/tests/unit/job_executors/test_discover_agents_executor.py`), a record outside the output contract (`ml-engine/src/ml_engine/job_executors/discovery_output_contract.py`), and engine and Platform halves that disagree (the process skill's cross-repo invariant check). This skill is for what they cannot see: whether a carrier can carry the collector's string at all, whether its device id is stable, and whether paging loses a device that reports mid-scan.

Read the source of truth rather than a restatement here:

- arthur-common `src/arthur_common/models/agent_governance_schemas.py`: `EndpointAgentCreationSource` and `SourceAddress`.
- `ml-engine/src/ml_engine/discovery/endpoint/records.py:records_for` and `endpoint/device.py:ManagedDevice`: the record is built there, never by hand.
- `ml-engine/src/ml_engine/discovery/endpoint/scope.py`: `DeviceScope`, `parse_group_names`.
- `ml-engine/src/ml_engine/discovery/__init__.py:source_connectors()`: the registry.
- `ml-engine/src/ml_engine/job_executors/discovery_scan.py`: the scan Protocol, `AcceptsStopCheck`, `ReportsDeviceCoverage`, `DiscoveryConfigurationError` and `failure_code`.
- `ml-engine/src/ml_engine/job_executors/discovery_source_test_executor.py`: how Test Connection classifies an exception, and its `PREVIEW_DEADLINE_SECONDS`.
- `integrations/endpoint-ai-discovery/docs/mdm/README.md`: what a carrier runbook covers.

Platform and UI steps belong to Arthur's internal discovery integration process skill.

## Carriers

- Jamf Pro, the reference connector (`ml-engine/src/ml_engine/discovery/endpoint/jamf/`): read [references/vendors/jamf.md](references/vendors/jamf.md) when building or changing Jamf or another MDM.
- Compute Engine: read [references/vendors/compute-engine.md](references/vendors/compute-engine.md) when building a cloud-host carrier.

## Workflow

```
- [ ] 1. The carrier meets the four requirements (or the gap is documented)
- [ ] 2. The connector produces ManagedDevice values; records only via records_for
- [ ] 3. Connection, scope resolved before devices, least privilege
- [ ] 4. Report-date window, keyset paging, coverage, stop check
- [ ] 5. Errors and Test Connection
- [ ] 6. Register, document, write the carrier runbook
- [ ] 7. Tests: run, fix, repeat until green
- [ ] 8. A scan end to end
```

## 1. What an endpoint source is

On each machine the collector (`integrations/endpoint-ai-discovery/dist/collect.sh` and `collect-linux.sh`) finds AI software and writes one `arthur1.` string. A **carrier** runs it on a schedule and hands the string back as a per-device attribute over its API. The connector is only the carrier's API client: payload, matching and record shape live in `discovery/endpoint/`. Check the carrier before writing code:

| Requirement | Why |
|---|---|
| Runs a script as root on a schedule | the collector must run |
| A per-device string attribute large enough (evidence reaches ~24 KB; budget 256 KB) | the string must arrive untruncated |
| An inventory API filterable and sortable by a report date | incremental scans that do not lose devices mid-page |
| A stable device id from the carrier, never the hardware serial or a reusable name | `external_id` stability |

A vendor with no way to run a script (an EDR or DLP inventory exposing only its own detections) is not this shape: decide in intake whether it is a carrier, a SIEM query over its events, or a new class.

## 2. The record

`records_for(device, findings, ...)` builds every record: `external_id` is `{device_key}:{agent_id}`, `address.instance` is the device, the address kind and id are the primary finding's route, `runs_on` is `RunsOn.ENDPOINT`, `service_names` is empty. The connector's job is to produce `ManagedDevice` values: carrier id, `last_reported`, name, group, OS, assigned user, group ids and the attribute string.

**Trace-identity invariant (every class).** A record becomes a GenAI Engine task; the customer's traces land on it only if the record's join keys (`observations.service_names`, `address.resource_id`) equal what the vendor's own telemetry puts on a real span. Endpoint records leave `service_names` empty; keep it so unless a captured span proves a key.

## 3. Connection and credentials

- Fields: `base_url` (must be https) and client credentials (sensitive), or, for a cloud-host carrier, the account locator and a service credential as a cloud source takes; optional `include_groups` / `exclude_groups` parsed by `parse_group_names`. `SENSITIVE_FIELDS` equals the catalog's secret fields.
- Resolve device scope **before** reading any device; an unknown group is a config error naming it.
- `allow_redirects=False` on every call that carries a token or secret.
- Least privilege: read-only on computer inventory and the attributes the collector writes.

## 4. Lookback, paging, coverage

- **Lookback is an incremental window on the carrier's report date**; `lookback_hours <= 0` is the full roster. A carrier with no report date enumerates fully every run and says so in the docs.
- Keyset-page on `(report_date, id)` so a device that reports mid-scan is not skipped; the full roster keysets on `id`. Retries via `discovery/retry.py`; refresh tokens before expiry, drop on 401.
- Yield one batch per device, so a mid-scan failure keeps what was published.
- Implement `ReportsDeviceCoverage.device_coverage()` (devices seen, decoded, missing or stale attribute; the scan asks it in `finally`) and `AcceptsStopCheck.stop_when`, asked after every device. Both are structural; do not import the Protocols.
- Zero decoded devices is a warning (the collector may not be deployed yet).
- `config.query` is a catalog override (YAML) for the matcher, not a query language: keep the catalog's query language `none`.

## 5. Errors and Test Connection

- Config faults (missing field, `http://`, bad URL, unknown group) raise `DiscoveryConfigurationError`, never a plain `ValueError`: that reads as configuration in Test Connection but `provider_error` on a scan.
- Non-2xx, or a 200 that is not the carrier's shape: `<Vendor>Error(msg, status_code=n)`.
- TLS refused: `DiscoveryConfigurationError(...) from exc`. Unreachable: `raise type(exc)(msg) from exc`.
- A malformed `arthur1.` string on one device is a per-device warning counted in coverage, never a scan failure. Never log attribute contents. Error text names the field and the fix, never the value.

## 6. Files

`discovery/endpoint/<vendor>/{__init__,client,connector}.py`, registered in `source_connectors()`; `tests/unit/discovery/test_<vendor>_connector.py`; a section in `ml-engine/docs/standalone-discovery.md`; and a carrier runbook `integrations/endpoint-ai-discovery/docs/mdm/<vendor>.md` linked from that directory's `README.md` (deploy the collector, create the attributes, grant the API role). Changes under `integrations/endpoint-ai-discovery/` may be CODEOWNERS-gated. Platform catalog entry: class endpoint, query language none, availability preview.

## 7. Tests

Run `uv run pytest tests/unit/discovery/test_<vendor>_connector.py` from `ml-engine/`, fix, repeat. Follow `tests/unit/discovery/test_jamf_connector.py`: registration; token flow and refresh; keyset paging with a device that reports mid-scan; report-date window from lookback and full roster at `<= 0`; group scope resolution and unknown-group refusal; `arthur1.` decode to records with the expected `external_id` and address; a malformed attribute counted in coverage and not fatal; `device_coverage()` totals; stop check after each device; 401/403 status; http URL refused; credentials and attribute contents never logged.

- Build fixtures in the generated clients' shapes: enum members, not plain strings. `str()` and f-strings of a `(str, Enum)` member give its qualified name on Python 3.11+, so convert with `.value`.

## 8. End to end

Follow the process skill's local end-to-end recipe with a device carrying a real `arthur1.` string (a captured attribute from `dist/collect.sh` on a test machine served by a fake carrier, or a sandbox tenant). Check the Agents tab shows the records with the device name and the endpoint mark, and the scan reports coverage.
